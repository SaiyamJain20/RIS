// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {HMBCFixture} from "./utils/Fixture.sol";
import {Vm} from "./utils/Vm.sol";
import {
    Profile,
    ErrorCode,
    HMBCHash,
    GovernanceAction,
    SignedRoleCertificate,
    AccessRequest,
    CredentialRecord,
    StateCheckpoint,
    DecisionCertificate,
    GOV_ADD_AUTHORITY,
    GOV_REMOVE_AUTHORITY,
    GOV_SET_CA_ADMINS,
    RESULT_ALLOW,
    MUT_NO_GOV_NONCE
} from "../src/types/ProtocolTypes.sol";
import {LSC} from "../src/LSC.sol";
import {TMSC} from "../src/TMSC.sol";
import {Governance} from "../src/Governance.sol";
import {FixtureConfig} from "../script/FixtureConfig.sol";

/// A-F1 slice 2: quorum governance of the authority set (design 2.2 sections 2-3; FL-10, F-28).
/// REPAIRED_F fixture: witness-1..4, q = 3, witness-set version 2, maxGovernanceTtl 120 s.
contract GovernanceTest is HMBCFixture {
    uint256 internal h5Pk;
    uint256 internal h5AdminPk;
    address internal h5;
    address internal h5Admin;
    address internal newAdmin;

    bytes32 internal constant ADDED_TOPIC = keccak256("AuthorityAdded(uint64,address,address[],uint64)");
    bytes32 internal constant REMOVED_TOPIC = keccak256("AuthorityRemoved(uint64,address,uint64)");
    bytes32 internal constant SET_TOPIC = keccak256("CaAdminsSet(uint64,address,address[],uint64)");
    bytes32 internal constant APPLIED_TOPIC = keccak256("GovernanceApplied(uint64,uint8,address,bytes32,address)");

    function profile() internal pure virtual override returns (Profile) {
        return Profile.REPAIRED_F;
    }

    function setUp() public virtual override {
        super.setUp();
        h5Pk = syntheticKey("H5-root");
        h5AdminPk = syntheticKey("H5-ca-admin");
        h5 = vm.addr(h5Pk);
        h5Admin = vm.addr(h5AdminPk);
        newAdmin = vm.addr(syntheticKey("H1-ca-admin-2"));
    }

    // ------------------------------------------------------------------ helpers

    function action(uint8 kind, address root, address[] memory admins, uint64 nonce)
        internal
        view
        returns (GovernanceAction memory)
    {
        return GovernanceAction(kind, root, admins, nonce, witnessSetVersion(), uint64(block.timestamp) + 60);
    }

    function govDigest(GovernanceAction memory a) internal view returns (bytes32) {
        return HMBCHash.governanceActionDigest(a, PBC_CHAIN_ID, address(gov));
    }

    function quorum(GovernanceAction memory a) internal view returns (bytes[] memory) {
        return witnessSigs(witnessPk, govDigest(a));
    }

    /// Anyone may submit: the submitter is mallory, who holds no role.
    function execute(GovernanceAction memory a, bytes[] memory sigs) internal {
        vm.prank(mallory);
        gov.execute(a, sigs);
    }

    function none() internal pure returns (address[] memory) {
        return new address[](0);
    }

    function contains(address[] memory xs, address x) internal pure returns (bool) {
        for (uint256 i = 0; i < xs.length; i++) {
            if (xs[i] == x) return true;
        }
        return false;
    }

    function countTopic(Vm.Log[] memory logs, address emitter, bytes32 topic) internal pure returns (uint256 n) {
        for (uint256 i = 0; i < logs.length; i++) {
            if (logs[i].emitter == emitter && logs[i].topics.length > 0 && logs[i].topics[0] == topic) n++;
        }
    }

    struct Snapshot {
        uint64 nonce;
        uint64 epoch;
        bytes32 authorities;
        bytes32 h1Admins;
        bytes32 h3Admins;
        bool h3Removed;
        uint256 logCount;
    }

    function snap() internal view returns (Snapshot memory s) {
        s.nonce = gov.governanceNonce();
        s.epoch = tmsc.authEpoch();
        s.authorities = keccak256(abi.encode(tmsc.authorities()));
        s.h1Admins = keccak256(abi.encode(tmsc.caAdmins(h1)));
        s.h3Admins = keccak256(abi.encode(tmsc.caAdmins(h3)));
        s.h3Removed = tmsc.removedAuthority(h3);
        s.logCount = lsc.logCount();
    }

    function assertUnchanged(Snapshot memory a, Snapshot memory b, string memory what) internal pure {
        assertEq(a.nonce, b.nonce, string.concat(what, ": governanceNonce"));
        assertEq(a.epoch, b.epoch, string.concat(what, ": authEpoch"));
        assertEq(a.authorities, b.authorities, string.concat(what, ": authorities"));
        assertEq(a.h1Admins, b.h1Admins, string.concat(what, ": H1 admins"));
        assertEq(a.h3Admins, b.h3Admins, string.concat(what, ": H3 admins"));
        assertTrue(a.h3Removed == b.h3Removed, string.concat(what, ": H3 tombstone"));
        assertEq(a.logCount, b.logCount, string.concat(what, ": LSC log count"));
    }

    // ------------------------------------------------------------------ deployment and wiring

    function test_AF1G_DeploymentReportsTheConfiguredGetters() public view {
        assertEq(gov.target(), address(tmsc), "target is the TMSC");
        assertEq(gov.governanceChainId(), PBC_CHAIN_ID, "governanceChainId");
        assertEq(gov.witnessSetVersion(), 2, "witnessSetVersion");
        assertEq(gov.threshold(), 3, "threshold");
        assertEq(gov.maxGovernanceTtl(), 120, "maxGovernanceTtl");
        assertEq(gov.mutations(), 0, "mutations");
        assertEq(gov.governanceNonce(), 0, "nonce starts at 0");
        address[] memory ws = gov.witnesses();
        assertEq(ws.length, 4, "four witnesses");
        for (uint256 i = 0; i < 4; i++) {
            assertEq(ws[i], vm.addr(witnessPks[i]), "witness order is the fixture order");
        }
        assertEq(tmsc.governance(), address(gov), "TMSC trusts this Governance");
    }

    function test_AF1G_ConstructorRejectsMalformedConfig() public {
        address[] memory ws = witnessAddresses();
        expectRejected(ErrorCode.MALFORMED);
        new Governance(Governance.Config(address(0), 2, ws, 3, 120, 0));
        expectRejected(ErrorCode.MALFORMED);
        new Governance(Governance.Config(address(tmsc), 2, ws, 0, 120, 0));
        expectRejected(ErrorCode.MALFORMED);
        new Governance(Governance.Config(address(tmsc), 2, ws, 5, 120, 0));
        expectRejected(ErrorCode.MALFORMED);
        new Governance(Governance.Config(address(tmsc), 2, ws, 3, 0, 0));
        expectRejected(ErrorCode.MALFORMED);
        new Governance(Governance.Config(address(tmsc), 2, ws, 3, 120, 1 << 9));
        address[] memory zero = witnessAddresses();
        zero[1] = address(0);
        expectRejected(ErrorCode.MALFORMED);
        new Governance(Governance.Config(address(tmsc), 2, zero, 3, 120, 0));
        address[] memory dup = witnessAddresses();
        dup[2] = dup[0];
        expectRejected(ErrorCode.DUPLICATE_SIGNER);
        new Governance(Governance.Config(address(tmsc), 2, dup, 3, 120, 0));
        // positive controls: q2 and the full F mask deploy
        new Governance(Governance.Config(address(tmsc), 2, ws, 2, 120, 0));
        new Governance(Governance.Config(address(tmsc), 2, ws, 3, 120, (1 << 9) - 1));
    }

    function test_AF1G_TmscRequiresGovernanceWiringOnlyUnderF() public {
        TMSC f = new TMSC(Profile.REPAIRED_F, 0, lsc, new TMSC.AuthorityConfig[](0));
        f.wire(address(psc), address(rsc));
        expectRejected(ErrorCode.MALFORMED);
        f.seal();
        f.wireGovernance(address(gov));
        f.seal();
        TMSC e = new TMSC(Profile.REPAIRED_E, 0, lsc, new TMSC.AuthorityConfig[](0));
        e.wire(address(psc), address(rsc));
        expectRejected(ErrorCode.WRONG_PROFILE);
        e.wireGovernance(address(gov));
        e.seal();
        assertEq(e.governance(), address(0), "E TMSC has no governance");
    }

    function test_AF1G_CaAdminsViewListsConstructorAdmins() public view {
        address[] memory a = tmsc.caAdmins(h1);
        assertEq(a.length, 1, "H1 has one constructor admin");
        assertEq(a[0], h1Admin, "H1 admin");
        assertEq(tmsc.caAdmins(h5).length, 0, "unknown root has none");
    }

    // ------------------------------------------------------------------ the three actions

    function test_AF1G_AddAuthorityByQuorum() public {
        uint64 epoch = tmsc.authEpoch();
        uint256 logs = lsc.logCount();
        GovernanceAction memory a = action(GOV_ADD_AUTHORITY, h5, one(h5Admin), 1);
        vm.recordLogs();
        execute(a, quorum(a));
        Vm.Log[] memory rec = vm.getRecordedLogs();
        assertTrue(tmsc.isAuthority(h5), "H5 is an authority");
        assertTrue(contains(tmsc.authorities(), h5), "authorities() lists H5");
        assertEq(tmsc.authorities().length, 5, "five authorities");
        assertTrue(tmsc.isCaAdmin(h5, h5Admin), "H5 admin flag");
        assertEq(tmsc.caAdmins(h5).length, 1, "H5 admin list");
        assertEq(tmsc.authEpoch(), epoch + 1, "authEpoch +1");
        assertEq(gov.governanceNonce(), 1, "nonce advanced");
        assertEq(lsc.logCount(), logs + 1, "one LSC entry");
        assertEq(countTopic(rec, address(tmsc), ADDED_TOPIC), 1, "AuthorityAdded");
        assertEq(countTopic(rec, address(gov), APPLIED_TOPIC), 1, "GovernanceApplied");
    }

    function test_AF1G_RemoveAuthorityByQuorum() public {
        uint64 epoch = tmsc.authEpoch();
        GovernanceAction memory a = action(GOV_REMOVE_AUTHORITY, h3, none(), 1);
        vm.recordLogs();
        execute(a, quorum(a));
        Vm.Log[] memory rec = vm.getRecordedLogs();
        assertFalse(tmsc.isAuthority(h3), "H3 removed");
        assertTrue(tmsc.removedAuthority(h3), "H3 tombstoned");
        address[] memory as_ = tmsc.authorities();
        assertEq(as_.length, 3, "three authorities");
        assertFalse(contains(as_, h3), "authorities() no longer lists H3");
        assertTrue(contains(as_, h1) && contains(as_, h2) && contains(as_, h4), "others kept");
        assertEq(tmsc.caAdmins(h3).length, 0, "H3 admin list cleared");
        assertFalse(tmsc.isCaAdmin(h3, h3Admin), "H3 admin flag cleared");
        assertEq(tmsc.authEpoch(), epoch + 1, "authEpoch +1");
        assertEq(countTopic(rec, address(tmsc), REMOVED_TOPIC), 1, "AuthorityRemoved");
    }

    function test_AF1G_SetCaAdminsByQuorum() public {
        GovernanceAction memory a = action(GOV_SET_CA_ADMINS, h1, one(newAdmin), 1);
        vm.recordLogs();
        execute(a, quorum(a));
        assertEq(countTopic(vm.getRecordedLogs(), address(tmsc), SET_TOPIC), 1, "CaAdminsSet");
        assertFalse(tmsc.isCaAdmin(h1, h1Admin), "old admin cleared");
        assertTrue(tmsc.isCaAdmin(h1, newAdmin), "new admin set");
        address[] memory list = tmsc.caAdmins(h1);
        assertEq(list.length, 1, "one admin");
        assertEq(list[0], newAdmin, "the new admin");
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        this.publishCrlAs(h1Admin, 1);
        this.publishCrlAs(newAdmin, 1);
        assertTrue(tmsc.revocationListState(h1).published, "the new admin publishes");
    }

    function test_AF1G_SetCaAdminsEmptySuspendsPublishing() public {
        GovernanceAction memory a = action(GOV_SET_CA_ADMINS, h1, none(), 1);
        execute(a, quorum(a));
        assertEq(tmsc.caAdmins(h1).length, 0, "no admins");
        assertTrue(tmsc.isAuthority(h1), "H1 is still an authority");
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        this.publishCrlAs(h1Admin, 1);
    }

    /// External so a test can expect its revert.
    function publishCrlAs(address admin, uint64 version) external {
        publishCrl(h1, h1Pk, admin, version, new uint64[](0));
    }

    // ------------------------------------------------------------------ TMSC preconditions and the tombstone

    function test_AF1G_AddExistingAuthorityIsMalformed() public {
        GovernanceAction memory a = action(GOV_ADD_AUTHORITY, h1, one(h1Admin), 1);
        bytes[] memory s = quorum(a);
        expectRejected(ErrorCode.MALFORMED);
        execute(a, s);
        assertEq(gov.governanceNonce(), 0, "nonce rolled back");
    }

    function test_AF1G_RemovedRootCannotBeReAdded() public {
        GovernanceAction memory r = action(GOV_REMOVE_AUTHORITY, h3, none(), 1);
        execute(r, quorum(r));
        GovernanceAction memory a = action(GOV_ADD_AUTHORITY, h3, one(h3Admin), 2);
        bytes[] memory s = quorum(a);
        expectRejected(ErrorCode.MALFORMED);
        execute(a, s);
        assertEq(gov.governanceNonce(), 1, "re-add rolled back");
        assertFalse(tmsc.isAuthority(h3), "H3 stays removed");
    }

    function test_AF1G_RemoveOrSetUnknownRootIsUnknownAuthority() public {
        GovernanceAction memory r = action(GOV_REMOVE_AUTHORITY, h5, none(), 1);
        bytes[] memory s = quorum(r);
        expectRejected(ErrorCode.UNKNOWN_AUTHORITY);
        execute(r, s);
        GovernanceAction memory a = action(GOV_SET_CA_ADMINS, h5, one(h5Admin), 1);
        s = quorum(a);
        expectRejected(ErrorCode.UNKNOWN_AUTHORITY);
        execute(a, s);
    }

    function test_AF1G_FreshRootStartsUnpublishedThenValidatesAfterItsCrl() public {
        GovernanceAction memory a = action(GOV_ADD_AUTHORITY, h5, one(h5Admin), 1);
        execute(a, quorum(a));
        SignedRoleCertificate memory c = roleCert(h5, h5Pk, alice, ROLE_DOCTOR, 501);
        (ErrorCode code,) = tmsc.validateCertificate(c, uint64(block.timestamp));
        assertCode(code, ErrorCode.STALE_ANCHOR, "fresh root has no CRL yet");
        publishCrl(h5, h5Pk, h5Admin, 1, new uint64[](0));
        (code,) = tmsc.validateCertificate(c, uint64(block.timestamp));
        assertCode(code, ErrorCode.NONE, "valid after its first CRL");
    }

    function test_AF1G_RemovedRootCertificatesAndAdminsAreRejected() public {
        publishCrl(h3, h3Pk, h3Admin, 1, new uint64[](0));
        SignedRoleCertificate memory c = roleCert(h3, h3Pk, alice, ROLE_DOCTOR, 301);
        (ErrorCode code,) = tmsc.validateCertificate(c, uint64(block.timestamp));
        assertCode(code, ErrorCode.NONE, "control: H3 certificate valid before removal");
        GovernanceAction memory r = action(GOV_REMOVE_AUTHORITY, h3, none(), 1);
        execute(r, quorum(r));
        (code,) = tmsc.validateCertificate(c, uint64(block.timestamp));
        assertCode(code, ErrorCode.UNKNOWN_AUTHORITY, "removed root's certificate");
        expectRejected(ErrorCode.UNKNOWN_AUTHORITY);
        this.publishH3CrlAs(h3Admin, 2);
        assertTrue(tmsc.revocationListState(h3).published, "history view still returns the old CRL");
    }

    function publishH3CrlAs(address admin, uint64 version) external {
        publishCrl(h3, h3Pk, admin, version, new uint64[](0));
    }

    // ------------------------------------------------------------------ check order (design 2.2 section 2 table)

    function test_AF1G_WrongWitnessSetVersionIsStaleStateFirst() public {
        GovernanceAction memory a = action(9, address(0), none(), 0);
        a.witnessSetVersion = 1;
        a.expiresAt = uint64(block.timestamp);
        expectRejected(ErrorCode.STALE_STATE);
        execute(a, new bytes[](0));
    }

    function test_AF1G_UnknownActionIsMalformed() public {
        for (uint8 k = 0; k <= 4; k += 4) {
            GovernanceAction memory a = action(k, h1, none(), 1);
            bytes[] memory s = quorum(a);
            expectRejected(ErrorCode.MALFORMED);
            execute(a, s);
        }
    }

    function test_AF1G_StructuralRulesAreMalformed() public {
        address[] memory nine = new address[](9);
        for (uint256 i = 0; i < 9; i++) {
            nine[i] = address(uint160(0x1000 + i));
        }
        address[] memory zeroAdmin = new address[](2);
        zeroAdmin[1] = h5Admin;
        address[] memory dup = new address[](2);
        (dup[0], dup[1]) = (h5Admin, h5Admin);
        address[] memory desc = new address[](2);
        (desc[0], desc[1]) = (address(0x2002), address(0x2001));
        GovernanceAction[7] memory bad = [
            action(GOV_ADD_AUTHORITY, address(0), one(h5Admin), 1),
            action(GOV_ADD_AUTHORITY, h5, none(), 1),
            action(GOV_ADD_AUTHORITY, h5, nine, 1),
            action(GOV_SET_CA_ADMINS, h1, zeroAdmin, 1),
            action(GOV_SET_CA_ADMINS, h1, dup, 1),
            action(GOV_SET_CA_ADMINS, h1, desc, 1),
            action(GOV_REMOVE_AUTHORITY, h3, one(h3Admin), 1)
        ];
        for (uint256 i = 0; i < bad.length; i++) {
            bytes[] memory s = quorum(bad[i]);
            expectRejected(ErrorCode.MALFORMED);
            execute(bad[i], s);
        }
        // positive control: eight ascending admins are accepted
        address[] memory eight = new address[](8);
        for (uint256 i = 0; i < 8; i++) {
            eight[i] = address(uint160(0x1000 + i));
        }
        GovernanceAction memory ok = action(GOV_SET_CA_ADMINS, h1, eight, 1);
        execute(ok, quorum(ok));
        assertEq(tmsc.caAdmins(h1).length, 8, "eight admins set");
    }

    function test_AF1G_NonceReplayAndGap() public {
        GovernanceAction memory stale = action(GOV_SET_CA_ADMINS, h1, none(), 0);
        bytes[] memory s = quorum(stale);
        expectRejected(ErrorCode.REPLAY);
        execute(stale, s);
        GovernanceAction memory gap = action(GOV_SET_CA_ADMINS, h1, none(), 2);
        s = quorum(gap);
        expectRejected(ErrorCode.MALFORMED);
        execute(gap, s);
    }

    function test_AF1G_ExpiryBounds() public {
        GovernanceAction memory a = action(GOV_SET_CA_ADMINS, h1, none(), 1);
        a.expiresAt = uint64(block.timestamp);
        bytes[] memory s = quorum(a);
        expectRejected(ErrorCode.EXPIRED);
        execute(a, s);
        a.expiresAt = uint64(block.timestamp) + 121;
        s = quorum(a);
        expectRejected(ErrorCode.MALFORMED);
        execute(a, s);
        a.expiresAt = uint64(block.timestamp) + 120;
        execute(a, quorum(a));
        assertEq(gov.governanceNonce(), 1, "now + maxGovernanceTtl is accepted");
    }

    function test_AF1G_QuorumFailures() public {
        GovernanceAction memory a = action(GOV_SET_CA_ADMINS, h1, none(), 1);
        bytes32 d = govDigest(a);
        bytes[] memory three = quorum(a);
        bytes[] memory two = new bytes[](2);
        (two[0], two[1]) = (three[0], three[1]);
        expectRejected(ErrorCode.INSUFFICIENT_QUORUM);
        execute(a, two);
        expectRejected(ErrorCode.INSUFFICIENT_QUORUM);
        execute(a, new bytes[](0));
        bytes[] memory dup = new bytes[](3);
        (dup[0], dup[1], dup[2]) = (three[0], three[0], three[1]);
        expectRejected(ErrorCode.DUPLICATE_SIGNER);
        execute(a, dup);
        bytes[] memory outsider = new bytes[](3);
        (outsider[0], outsider[1], outsider[2]) = (sig(malloryPk, d), three[1], three[2]);
        expectRejected(ErrorCode.BAD_SIGNATURE);
        execute(a, outsider);
        bytes[] memory unsorted = new bytes[](3);
        (unsorted[0], unsorted[1], unsorted[2]) = (three[2], three[0], three[1]);
        expectRejected(ErrorCode.MALFORMED);
        execute(a, unsorted);
        assertEq(gov.governanceNonce(), 0, "nothing executed");
    }

    function test_AF1G_CheckOrderStructureNonceExpirySignatures() public {
        // structure (3) before nonce (4)
        GovernanceAction memory a = action(GOV_REMOVE_AUTHORITY, h3, one(h3Admin), 0);
        expectRejected(ErrorCode.MALFORMED);
        execute(a, new bytes[](0));
        // nonce (4) before expiry (5)
        a = action(GOV_SET_CA_ADMINS, h1, none(), 0);
        a.expiresAt = uint64(block.timestamp);
        expectRejected(ErrorCode.REPLAY);
        execute(a, new bytes[](0));
        // expiry (5) before signatures (6)
        a.nonce = 1;
        expectRejected(ErrorCode.EXPIRED);
        execute(a, new bytes[](0));
    }

    // ------------------------------------------------------------------ FL-10 baselines (bits 6 and 7 clear)

    /// A certificate signed over SET_CA_ADMINS(H1, []) submitted as REMOVE_AUTHORITY(H1, []).
    function test_AF1G_SetCertificateSubmittedAsRemoveIsBadSignature() public {
        GovernanceAction memory set = action(GOV_SET_CA_ADMINS, h1, none(), 1);
        bytes[] memory s = quorum(set);
        // A separate struct: assigning `set` would alias the same memory (first run, slice2-green-run1).
        GovernanceAction memory asRemove =
            GovernanceAction(GOV_REMOVE_AUTHORITY, set.root, set.admins, set.nonce, set.witnessSetVersion, set.expiresAt);
        Snapshot memory before = snap();
        expectRejected(ErrorCode.BAD_SIGNATURE);
        execute(asRemove, s);
        assertUnchanged(before, snap(), "substituted action");
        assertTrue(tmsc.isAuthority(h1), "H1 not removed");
        // positive control: the matching action executes
        execute(set, s);
        assertEq(tmsc.caAdmins(h1).length, 0, "SET executed");
    }

    /// Replay of an executed, repeatable SET_CA_ADMINS certificate.
    function test_AF1G_ReplayedSetIsReplayWithNoSecondEffect() public {
        GovernanceAction memory a = action(GOV_SET_CA_ADMINS, h1, one(newAdmin), 1);
        bytes[] memory s = quorum(a);
        execute(a, s);
        Snapshot memory before = snap();
        vm.recordLogs();
        expectRejected(ErrorCode.REPLAY);
        execute(a, s);
        assertEq(vm.getRecordedLogs().length, 0, "no event on replay");
        assertUnchanged(before, snap(), "replay");
        // positive control: a fresh nonce executes
        GovernanceAction memory next = action(GOV_SET_CA_ADMINS, h1, one(newAdmin), 2);
        execute(next, quorum(next));
        assertEq(gov.governanceNonce(), 2, "fresh nonce N+1 executes");
        assertEq(tmsc.authEpoch(), before.epoch + 1, "one more epoch");
    }

    // ------------------------------------------------------------------ R3 rollback and log binding

    function test_AF1G_FailedExecuteLeavesNoTrace() public {
        GovernanceAction memory r = action(GOV_REMOVE_AUTHORITY, h3, none(), 1);
        execute(r, quorum(r));
        Snapshot memory before = snap();
        GovernanceAction memory a = action(GOV_ADD_AUTHORITY, h3, one(h3Admin), 2);
        bytes[] memory s = quorum(a);
        vm.recordLogs();
        expectRejected(ErrorCode.MALFORMED);
        execute(a, s);
        assertEq(vm.getRecordedLogs().length, 0, "no event from the failed execute");
        assertUnchanged(before, snap(), "failed TMSC precondition");
    }

    function test_AF1G_UpdateLogBindsActionNonceAndAdmins() public {
        address[] memory admins = one(h5Admin);
        GovernanceAction memory a = action(GOV_ADD_AUTHORITY, h5, admins, 1);
        execute(a, quorum(a));
        (LSC.LogEntry memory e, bytes memory details) = lsc.getLog(lsc.logCount());
        assertEq(e.subject, keccak256(abi.encode(h5, GOV_ADD_AUTHORITY, "HMBC.governance")), "subject");
        bytes memory want = abi.encode(GOV_ADD_AUTHORITY, uint64(1), h5, admins, address(gov));
        assertEq(keccak256(details), keccak256(want), "details bind action, signed nonce, root, admins, Governance");
        assertEq(e.detailsHash, keccak256(want), "details hash");
        assertTrue(e.kind == LSC.LogKind.TRUST_UPDATE, "a trust update entry");
    }

    function test_AF1G_EventsCarryTheSignedNonce() public {
        GovernanceAction memory a = action(GOV_SET_CA_ADMINS, h1, one(newAdmin), 1);
        vm.recordLogs();
        execute(a, quorum(a));
        Vm.Log[] memory rec = vm.getRecordedLogs();
        bool sawSet;
        bool sawApplied;
        for (uint256 i = 0; i < rec.length; i++) {
            if (rec[i].emitter == address(tmsc) && rec[i].topics[0] == SET_TOPIC) {
                sawSet = true;
                assertEq(uint256(rec[i].topics[1]), 1, "CaAdminsSet governanceNonce");
                assertEq(address(uint160(uint256(rec[i].topics[2]))), h1, "CaAdminsSet root");
            }
            if (rec[i].emitter == address(gov) && rec[i].topics[0] == APPLIED_TOPIC) {
                sawApplied = true;
                assertEq(uint256(rec[i].topics[1]), 1, "GovernanceApplied nonce");
                assertEq(uint256(rec[i].topics[2]), GOV_SET_CA_ADMINS, "GovernanceApplied action");
                (bytes32 structHash, address submitter) = abi.decode(rec[i].data, (bytes32, address));
                assertEq(structHash, HMBCHash.hashGovernanceAction(a), "structHash");
                assertEq(submitter, mallory, "submitter");
            }
        }
        assertTrue(sawSet && sawApplied, "both events");
    }

    // ------------------------------------------------------------------ direct TMSC calls

    function test_AF1G_OnlyGovernanceMayCallTmscMutators() public {
        vm.prank(mallory);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        tmsc.govAddAuthority(1, h5, one(h5Admin));
        vm.prank(h1Admin);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        tmsc.govRemoveAuthority(1, h3);
        vm.prank(address(psc));
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        tmsc.govSetCaAdmins(1, h1, none());
    }

    function test_AF1G_MutatorsRejectNonFProfilesAndUnsealed() public {
        TMSC e = new TMSC(Profile.REPAIRED_E, 0, lsc, new TMSC.AuthorityConfig[](0));
        expectRejected(ErrorCode.NOT_COMMITTED);
        e.govAddAuthority(1, h5, one(h5Admin));
        e.wire(address(psc), address(rsc));
        e.seal();
        expectRejected(ErrorCode.WRONG_PROFILE);
        e.govAddAuthority(1, h5, one(h5Admin));
        expectRejected(ErrorCode.WRONG_PROFILE);
        e.govRemoveAuthority(1, h1);
        expectRejected(ErrorCode.WRONG_PROFILE);
        e.govSetCaAdmins(1, h1, none());
    }

    // ------------------------------------------------------------------ F-28: removal across the checkpoint barrier

    struct Barrier {
        AccessRequest r;
        CredentialRecord[] recs;
        StateCheckpoint cp1;
        DecisionCertificate c;
    }

    /// Alice's request is accepted at the PBC and a decision is certified on checkpoint cp1;
    /// then governance removes H1, the issuer of her Doctor certificate.
    function removeH1AfterCertifiedDecision() internal returns (Barrier memory b) {
        publishTrustLists(one(alice));
        registerAlice();
        (b.r,, b.recs) = aliceForwarded(1);
        b.cp1 = acceptCheckpoint();
        b.c = certify(decisionFor(b.r, RESULT_ALLOW, b.recs, b.cp1), witnessPk);
        uint64 before = tmsc.authEpoch();
        GovernanceAction memory a = action(GOV_REMOVE_AUTHORITY, h1, none(), 1);
        execute(a, quorum(a));
        assertEq(tmsc.authEpoch(), before + 1, "removal advances authEpoch");
    }

    function test_AF1G_F28_PbcRefusesTheRemovedRootImmediately() public {
        removeH1AfterCertifiedDecision();
        (ErrorCode code,) = tmsc.validateCertificate(aliceCert(), uint64(block.timestamp));
        assertCode(code, ErrorCode.UNKNOWN_AUTHORITY, "certificate check");
        AccessRequest memory r2 = aliceRequest(2);
        (, ErrorCode c2) = submit(r2, signRequest(r2, alicePk), aliceBundle());
        assertCode(c2, ErrorCode.UNKNOWN_AUTHORITY, "new request at the PBC");
    }

    function test_AF1G_F28_DbcPreBarrierStillGrants() public {
        Barrier memory b = removeH1AfterCertifiedDecision();
        (bool has, StateCheckpoint memory cur) = kssc.currentCheckpoint();
        assertTrue(has && cur.sequence == b.cp1.sequence, "DBC still holds the pre-removal checkpoint");
        vm.prank(relay);
        bytes32 grantId = acsc.consumeDecision(b.r, b.c, b.recs);
        assertTrue(grantId != bytes32(0), "the old-epoch decision grants inside the window");
    }

    function test_AF1G_F28_DbcPostBarrierIsStaleState() public {
        Barrier memory b = removeH1AfterCertifiedDecision();
        StateCheckpoint memory cp2 = acceptCheckpoint();
        assertEq(cp2.authEpoch, b.cp1.authEpoch + 1, "the new checkpoint carries the new epoch");
        vm.prank(relay);
        expectRejected(ErrorCode.STALE_STATE);
        acsc.consumeDecision(b.r, b.c, b.recs);
    }
}
