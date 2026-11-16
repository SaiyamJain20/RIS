// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {TestBase} from "./TestBase.sol";
import {
    Profile,
    LogDetailMode,
    ErrorCode,
    HMBCHash,
    Registration,
    RoleCertificate,
    SignedRoleCertificate,
    RevocationList,
    TemporalAcl,
    TempAclEntry,
    AccessRequest,
    TemporalClaim,
    CredentialBundle,
    CredentialRecord,
    AccessDecision,
    DecisionCertificate,
    StateCheckpoint,
    ForwardedRequest,
    GrantReceipt,
    GovernanceAction,
    isRepaired,
    ACTION_READ,
    CREDENTIAL_LONG_TERM,
    CREDENTIAL_TEMPORAL
} from "../../src/types/ProtocolTypes.sol";
import {LSC} from "../../src/LSC.sol";
import {TMSC} from "../../src/TMSC.sol";
import {RSC} from "../../src/RSC.sol";
import {PSC} from "../../src/PSC.sol";
import {KSSC} from "../../src/KSSC.sol";
import {ACSC} from "../../src/ACSC.sol";
import {Governance} from "../../src/Governance.sol";
import {FixtureConfig} from "../../script/FixtureConfig.sol";

/// Synthetic E fixture. All keys are derived from public labels and are TEST-ONLY.
/// Two chains are simulated in one EVM: contracts check block.chainid only at construction
/// and otherwise use their configured chain ids, so deploying each side under vm.chainId(...)
/// reproduces the two-chain domain separation.
abstract contract HMBCFixture is TestBase {
    uint256 internal constant PBC_CHAIN_ID = FixtureConfig.PBC_CHAIN_ID;
    uint256 internal constant DBC_CHAIN_ID = FixtureConfig.DBC_CHAIN_ID;
    uint64 internal constant POLICY_VERSION = FixtureConfig.POLICY_VERSION;
    uint64 internal constant REQUEST_TTL = FixtureConfig.REQUEST_TTL;
    uint64 internal constant CHECKPOINT_TTL = FixtureConfig.CHECKPOINT_TTL;
    uint64 internal constant GRANT_TTL = FixtureConfig.GRANT_TTL;
    uint64 internal constant WITNESS_SET_VERSION = FixtureConfig.WITNESS_SET_VERSION;
    uint64 internal constant T0 = 1_800_000_000;

    bytes32 internal constant ROLE_DOCTOR = FixtureConfig.ROLE_DOCTOR;
    bytes32 internal constant ROLE_ON_DUTY = FixtureConfig.ROLE_ON_DUTY;
    bytes32 internal constant ROLE_RESEARCHER = FixtureConfig.ROLE_RESEARCHER;
    bytes32 internal constant DATA_P1 = FixtureConfig.DATA_P1;
    bytes32 internal constant ALICE_RECIPIENT_KEY_HASH = keccak256("HMBC.recipient-key.alice");
    bytes32 internal constant BOB_RECIPIENT_KEY_HASH = keccak256("HMBC.recipient-key.bob");
    uint64 internal constant ALICE_SERIAL = 101;
    uint64 internal constant BOB_SERIAL = 201;

    uint256 internal h1Pk;
    uint256 internal h2Pk;
    uint256 internal h3Pk;
    uint256 internal h4Pk;
    uint256 internal h1AdminPk;
    uint256 internal h2AdminPk;
    uint256 internal h3AdminPk;
    uint256 internal h4AdminPk;
    uint256 internal alicePk;
    uint256 internal bobPk;
    uint256 internal malloryPk;
    uint256 internal witnessPk;
    uint256 internal relayPk;

    address internal h1;
    address internal h2;
    address internal h3;
    address internal h4;
    address internal h1Admin;
    address internal h2Admin;
    address internal h3Admin;
    address internal h4Admin;
    address internal alice;
    address internal bob;
    address internal mallory;
    address internal witness;
    address internal relay;

    LSC internal lsc;
    TMSC internal tmsc;
    RSC internal rsc;
    PSC internal psc;
    KSSC internal kssc;
    ACSC internal acsc;
    Governance internal gov; // REPAIRED_F only
    uint256[] internal witnessPks; // REPAIRED_F: witness-1..4 (witness-1 is witnessPk)

    uint64 internal checkpointSequence;

    function profile() internal pure virtual returns (Profile);

    /// Non-zero only in test-mutants/ suites (mutant-* deployments of REPAIRED_E).
    function mutations() internal pure virtual returns (uint256) {
        return 0;
    }

    function logDetailMode() internal pure virtual returns (LogDetailMode) {
        return LogDetailMode.COMPLETE_DETAILS;
    }

    /// Witness-set parameters (A-F1 design 2.2 section 7.3): E has one witness, version 1, q = 1;
    /// REPAIRED_F has witness-1..4, version 2, q = 3 (mutant-f-q2 overrides threshold to 2).
    function witnessSetVersion() internal pure virtual returns (uint64) {
        return profile() == Profile.REPAIRED_F ? FixtureConfig.F_WITNESS_SET_VERSION : WITNESS_SET_VERSION;
    }

    function threshold() internal pure virtual returns (uint256) {
        return profile() == Profile.REPAIRED_F ? FixtureConfig.F_THRESHOLD : 1;
    }

    function witnessAddresses() internal view virtual returns (address[] memory ws) {
        if (profile() != Profile.REPAIRED_F) return one(witness);
        ws = new address[](witnessPks.length);
        for (uint256 i = 0; i < ws.length; i++) {
            ws[i] = vm.addr(witnessPks[i]);
        }
    }

    function setUp() public virtual {
        vm.warp(T0);
        vm.roll(1000);
        _keys();
        _deploy(profile(), logDetailMode());
    }

    // ------------------------------------------------------------------ identities

    function syntheticKey(string memory label) internal pure returns (uint256) {
        return FixtureConfig.key(label);
    }

    function _keys() internal {
        h1Pk = syntheticKey("H1-root");
        h2Pk = syntheticKey("H2-root");
        h3Pk = syntheticKey("H3-root");
        h4Pk = syntheticKey("H4-root");
        h1AdminPk = syntheticKey("H1-ca-admin");
        h2AdminPk = syntheticKey("H2-ca-admin");
        h3AdminPk = syntheticKey("H3-ca-admin");
        h4AdminPk = syntheticKey("H4-ca-admin");
        alicePk = syntheticKey("alice");
        bobPk = syntheticKey("bob");
        malloryPk = syntheticKey("mallory");
        witnessPk = syntheticKey("witness-1");
        relayPk = syntheticKey("relay");
        delete witnessPks;
        for (uint256 i = 0; i < FixtureConfig.F_WITNESS_COUNT; i++) {
            witnessPks.push(syntheticKey(FixtureConfig.witnessLabel(i)));
        }
        h1 = vm.addr(h1Pk);
        h2 = vm.addr(h2Pk);
        h3 = vm.addr(h3Pk);
        h4 = vm.addr(h4Pk);
        h1Admin = vm.addr(h1AdminPk);
        h2Admin = vm.addr(h2AdminPk);
        h3Admin = vm.addr(h3AdminPk);
        h4Admin = vm.addr(h4AdminPk);
        alice = vm.addr(alicePk);
        bob = vm.addr(bobPk);
        mallory = vm.addr(malloryPk);
        witness = vm.addr(witnessPk);
        relay = vm.addr(relayPk);
    }

    // ------------------------------------------------------------------ deployment

    function _deploy(Profile p, LogDetailMode mode) internal {
        vm.chainId(PBC_CHAIN_ID);
        lsc = new LSC(mode);
        tmsc = new TMSC(p, mutations(), lsc, _authorityConfig());
        rsc = new RSC(PBC_CHAIN_ID, tmsc, lsc);
        address[] memory ws = witnessAddresses();
        psc = new PSC(
            PSC.Config(
                p, mutations(), rsc, tmsc, lsc, relay, POLICY_VERSION, REQUEST_TTL, witnessSetVersion(), ws, threshold()
            )
        );
        if (p == Profile.REPAIRED_F) {
            gov = new Governance(
                Governance.Config(
                    address(tmsc), witnessSetVersion(), ws, threshold(), FixtureConfig.GOVERNANCE_MAX_TTL, mutations()
                )
            );
        }

        vm.chainId(DBC_CHAIN_ID);
        kssc = new KSSC(
            KSSC.Config(
                p, mutations(), DBC_CHAIN_ID, PBC_CHAIN_ID, address(psc), witnessSetVersion(), ws, threshold(), CHECKPOINT_TTL
            )
        );
        acsc = new ACSC(p, mutations(), DBC_CHAIN_ID, PBC_CHAIN_ID, address(psc), POLICY_VERSION, GRANT_TTL);
        kssc.wire(address(acsc));
        acsc.wire(kssc, relay);
        uint256 policyId = acsc.addPolicy(emergencyPolicy());
        acsc.registerData(DATA_P1, h2, policyId);
        kssc.seal();
        acsc.seal();

        vm.chainId(PBC_CHAIN_ID);
        lsc.wire(address(rsc), address(tmsc), address(psc));
        tmsc.wire(address(psc), address(rsc));
        if (p == Profile.REPAIRED_F) tmsc.wireGovernance(address(gov));
        psc.configureDestination(DBC_CHAIN_ID, address(kssc));
        lsc.seal();
        tmsc.seal();
        rsc.seal();
        psc.seal();
    }

    function _authorityConfig() internal view returns (TMSC.AuthorityConfig[] memory cfg) {
        cfg = new TMSC.AuthorityConfig[](4);
        address[4] memory roots = [h1, h2, h3, h4];
        address[4] memory admins = [h1Admin, h2Admin, h3Admin, h4Admin];
        for (uint256 i = 0; i < 4; i++) {
            address[] memory a = new address[](1);
            a[0] = admins[i];
            cfg[i] = TMSC.AuthorityConfig(roots[i], a);
        }
    }

    function emergencyPolicy() internal pure returns (ACSC.Requirement[][] memory) {
        return FixtureConfig.emergencyPolicy();
    }

    // ------------------------------------------------------------------ signing helpers

    function sig(uint256 pk, bytes32 digest) internal pure returns (bytes memory) {
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pk, digest);
        return abi.encodePacked(r, s, v);
    }

    function roleCert(address issuer, uint256 issuerPk, address gid, bytes32 role, uint64 serial)
        internal
        view
        returns (SignedRoleCertificate memory sc)
    {
        bytes32[] memory roles = new bytes32[](1);
        roles[0] = role;
        RoleCertificate memory c = RoleCertificate(issuer, gid, roles, serial, T0 - 3600, T0 + 365 days);
        sc = SignedRoleCertificate(c, sig(issuerPk, HMBCHash.roleCertificateDigest(c, PBC_CHAIN_ID, address(tmsc))));
    }

    function aliceCert() internal view returns (SignedRoleCertificate memory) {
        return roleCert(h1, h1Pk, alice, ROLE_DOCTOR, ALICE_SERIAL);
    }

    function bobCert() internal view returns (SignedRoleCertificate memory) {
        return roleCert(h2, h2Pk, bob, ROLE_RESEARCHER, BOB_SERIAL);
    }

    function register(uint256 userPk, SignedRoleCertificate memory cert, bytes32 recipientKeyHash) internal {
        address gid = vm.addr(userPk);
        Registration memory reg = Registration(
            gid, HMBCHash.roleCertificateDigest(cert.cert, PBC_CHAIN_ID, address(tmsc)), recipientKeyHash, T0 + 600
        );
        bytes memory possession = sig(userPk, HMBCHash.registrationDigest(reg, PBC_CHAIN_ID, address(rsc)));
        vm.prank(gid);
        rsc.register(reg, possession, cert);
    }

    function registerAlice() internal {
        register(alicePk, aliceCert(), ALICE_RECIPIENT_KEY_HASH);
    }

    function registerBob() internal {
        register(bobPk, bobCert(), BOB_RECIPIENT_KEY_HASH);
    }

    function revocationList(address authority, uint64 version, uint64[] memory serials)
        internal
        pure
        returns (RevocationList memory)
    {
        return RevocationList(authority, version, T0 + 1 days, serials);
    }

    function signCrl(RevocationList memory l, uint256 signerPk) internal view returns (bytes memory) {
        return sig(signerPk, HMBCHash.revocationListDigest(l, PBC_CHAIN_ID, address(tmsc)));
    }

    function publishCrl(address authority, uint256 rootPk, address admin, uint64 version, uint64[] memory serials)
        internal
    {
        RevocationList memory l = revocationList(authority, version, serials);
        bytes memory s = signCrl(l, rootPk);
        vm.prank(admin);
        tmsc.updateRevocationList(l, s);
    }

    function onDutyAcl(address authority, uint64 version, address[] memory gids)
        internal
        pure
        returns (TemporalAcl memory acl)
    {
        acl.authority = authority;
        acl.version = version;
        acl.validUntil = T0 + 1 days;
        acl.entries = new TempAclEntry[](gids.length);
        for (uint256 i = 0; i < gids.length; i++) {
            acl.entries[i] = TempAclEntry(gids[i], ROLE_ON_DUTY, T0 - 60, T0 + 8 hours);
        }
    }

    function signAcl(TemporalAcl memory acl, uint256 signerPk) internal view returns (bytes memory) {
        return sig(signerPk, HMBCHash.temporalAclDigest(acl, PBC_CHAIN_ID, address(tmsc)));
    }

    function publishAcl(TemporalAcl memory acl, uint256 rootPk, address admin) internal {
        bytes memory s = signAcl(acl, rootPk);
        vm.prank(admin);
        tmsc.updateTemporalAcl(acl, s);
    }

    /// H1 and H2 publish empty CRLs v1; H1 publishes TempACL v1 putting `onDuty` on duty.
    /// REPAIRED_E checks the issuer's current CRL already at registration, so tests publish first.
    function publishTrustLists(address[] memory onDuty) internal {
        publishCrl(h1, h1Pk, h1Admin, 1, new uint64[](0));
        publishCrl(h2, h2Pk, h2Admin, 1, new uint64[](0));
        publishAcl(onDutyAcl(h1, 1, onDuty), h1Pk, h1Admin);
    }

    function one(address a) internal pure returns (address[] memory xs) {
        xs = new address[](1);
        xs[0] = a;
    }

    // ------------------------------------------------------------------ requests

    function accessRequest(address gid, bytes32 recipientKeyHash, uint256 nonce)
        internal
        view
        returns (AccessRequest memory)
    {
        return AccessRequest(
            PBC_CHAIN_ID,
            DBC_CHAIN_ID,
            address(psc),
            address(kssc),
            gid,
            DATA_P1,
            ACTION_READ,
            POLICY_VERSION,
            tmsc.authEpoch(),
            0,
            nonce,
            uint64(block.timestamp) + REQUEST_TTL,
            recipientKeyHash
        );
    }

    function aliceRequest(uint256 nonce) internal view returns (AccessRequest memory) {
        return accessRequest(alice, ALICE_RECIPIENT_KEY_HASH, nonce);
    }

    function signRequest(AccessRequest memory r, uint256 pk) internal pure returns (bytes memory) {
        return sig(pk, HMBCHash.accessRequestDigest(r));
    }

    /// Alice presents her H1 Doctor certificate and claims H1 OnDuty.
    function aliceBundle() internal view returns (CredentialBundle memory b) {
        b.certificates = new SignedRoleCertificate[](1);
        b.certificates[0] = aliceCert();
        b.temporalClaims = new TemporalClaim[](1);
        b.temporalClaims[0] = TemporalClaim(h1, ROLE_ON_DUTY);
    }

    function bobBundle() internal view returns (CredentialBundle memory b) {
        b.certificates = new SignedRoleCertificate[](1);
        b.certificates[0] = bobCert();
        b.temporalClaims = new TemporalClaim[](0);
    }

    function submit(AccessRequest memory r, bytes memory userSig, CredentialBundle memory b)
        internal
        returns (bytes32 digest, ErrorCode code)
    {
        vm.prank(relay);
        return psc.requestAccess(r, userSig, b);
    }

    function verifiedRecords(address gid, CredentialBundle memory b) internal view returns (CredentialRecord[] memory) {
        (ErrorCode code, CredentialRecord[] memory recs) = tmsc.checkCredentials(gid, b, uint64(block.timestamp));
        assertCode(code, ErrorCode.NONE, "fixture credentials verify");
        return recs;
    }

    // ------------------------------------------------------------------ witness (repaired profiles)

    /// Under REPAIRED_F, signing as `witnessPk` means the quorum: the first `threshold()` of
    /// witness-1..4, sorted by address (design 2.2 section 7.4). Any other key signs alone, which
    /// keeps the E non-witness negative tests valid.
    function witnessSigs(uint256 pk, bytes32 digest) internal view returns (bytes[] memory sigs) {
        if (profile() != Profile.REPAIRED_F || pk != witnessPk) {
            sigs = new bytes[](1);
            sigs[0] = sig(pk, digest);
            return sigs;
        }
        uint256[] memory pks = new uint256[](threshold());
        for (uint256 i = 0; i < pks.length; i++) {
            pks[i] = witnessPks[i];
        }
        return sortedSigs(pks, digest);
    }

    /// Signatures by `pks` over `digest`, ordered by ascending signer address (QuorumLib order).
    function sortedSigs(uint256[] memory pks, bytes32 digest) internal pure returns (bytes[] memory sigs) {
        uint256 n = pks.length;
        uint256[] memory order = new uint256[](n);
        for (uint256 i = 0; i < n; i++) {
            order[i] = pks[i];
        }
        for (uint256 i = 1; i < n; i++) {
            for (uint256 j = i; j > 0 && vm.addr(order[j]) < vm.addr(order[j - 1]); j--) {
                (order[j], order[j - 1]) = (order[j - 1], order[j]);
            }
        }
        sigs = new bytes[](n);
        for (uint256 i = 0; i < n; i++) {
            sigs[i] = sig(order[i], digest);
        }
    }

    function checkpointNow() internal returns (StateCheckpoint memory cp) {
        checkpointSequence += 1;
        cp = StateCheckpoint(
            checkpointSequence,
            tmsc.authEpoch(),
            POLICY_VERSION,
            0,
            witnessSetVersion(),
            PBC_CHAIN_ID,
            address(psc),
            block.number,
            keccak256(abi.encode("synthetic-pbc-block", block.number)),
            uint64(block.timestamp) + CHECKPOINT_TTL
        );
    }

    function signCheckpoint(StateCheckpoint memory cp, uint256 pk) internal view returns (bytes[] memory sigs) {
        return witnessSigs(pk, HMBCHash.stateCheckpointDigest(cp, DBC_CHAIN_ID, address(kssc)));
    }

    function acceptCheckpoint() internal returns (StateCheckpoint memory cp) {
        cp = checkpointNow();
        kssc.acceptState(cp, signCheckpoint(cp, witnessPk));
    }

    function decisionFor(AccessRequest memory r, uint8 result, CredentialRecord[] memory recs, StateCheckpoint memory cp)
        internal
        view
        returns (AccessDecision memory)
    {
        return AccessDecision(
            HMBCHash.accessRequestDigest(r),
            result,
            HMBCHash.hashCredentialRecords(recs),
            cp.sequence,
            witnessSetVersion(),
            cp.sourceBlockNumber,
            cp.sourceBlockHash,
            uint64(block.timestamp) + REQUEST_TTL
        );
    }

    function certify(AccessDecision memory d, uint256 pk) internal view returns (DecisionCertificate memory c) {
        c.decision = d;
        c.signatures = witnessSigs(pk, HMBCHash.accessDecisionDigest(d, DBC_CHAIN_ID, address(kssc)));
    }

    // -------------------------------------------------------------- delivery (profile-specific)

    /// Carries a PBC-forwarded request to the DBC the way this profile does. Returns the grant id
    /// (zero for a logged denial).
    function deliver(AccessRequest memory r, CredentialRecord[] memory recs, bytes32 requestDigest, uint8 witnessResult)
        internal
        returns (bytes32 grantId)
    {
        if (isRepaired(profile())) {
            StateCheckpoint memory cp = acceptCheckpoint();
            DecisionCertificate memory c = certify(decisionFor(r, witnessResult, recs, cp), witnessPk);
            vm.prank(relay);
            return acsc.consumeDecision(r, c, recs);
        }
        vm.prank(relay);
        (, grantId) = acsc.policyEnf(ForwardedRequest(requestDigest, r.gid, r.dataId, r.action), recs);
    }

    function aliceForwarded(uint256 nonce)
        internal
        returns (AccessRequest memory r, bytes32 digest, CredentialRecord[] memory recs)
    {
        r = aliceRequest(nonce);
        ErrorCode code;
        (digest, code) = submit(r, signRequest(r, alicePk), aliceBundle());
        assertCode(code, ErrorCode.NONE, "PBC accepts Alice");
        recs = verifiedRecords(alice, aliceBundle());
    }

    // ------------------------------------------------------------------ grant receipts (A1-0008)

    /// The witness duty (A2-0002): copy KSSC.getGrant(grantId) for an allowed grant at an observed block.
    function receiptFor(bytes32 grantId) internal view returns (GrantReceipt memory g) {
        (bytes32 req, bytes32 dataId, address gid, uint64 keyEpoch, uint64 expiresAt, bool allowed) = kssc.getGrant(grantId);
        assertTrue(allowed, "fixture witness only attests allowed grants");
        g = GrantReceipt(
            req,
            grantId,
            gid,
            dataId,
            keyEpoch,
            expiresAt,
            witnessSetVersion(),
            DBC_CHAIN_ID,
            address(kssc),
            block.number,
            keccak256(abi.encode("synthetic-dbc-block", block.number))
        );
    }

    function signReceipt(GrantReceipt memory g, uint256 pk) internal view returns (bytes[] memory sigs) {
        return witnessSigs(pk, HMBCHash.grantReceiptDigest(g, PBC_CHAIN_ID, address(psc)));
    }

    /// Records the outcome the way this profile does: paper = unattested relay report;
    /// repaired-e = relay report carrying the witness-signed GrantReceipt.
    function reportOutcomeFor(bytes32 digest, bytes32 grantId, bytes32 outcome) internal returns (uint256 logId) {
        if (isRepaired(profile())) {
            GrantReceipt memory g = receiptFor(grantId);
            bytes[] memory sigs = signReceipt(g, witnessPk);
            vm.prank(relay);
            return psc.reportAttestedOutcome(digest, outcome, g, sigs);
        }
        vm.prank(relay);
        return psc.reportOutcome(digest, grantId, outcome);
    }
}
