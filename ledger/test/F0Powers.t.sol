// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {HMBCFixture} from "./utils/Fixture.sol";
import {
    Profile,
    ErrorCode,
    HMBCHash,
    Registration,
    SignedRoleCertificate,
    RevocationList,
    AccessRequest,
    TemporalClaim,
    CredentialBundle,
    CredentialRecord,
    DecisionCertificate,
    StateCheckpoint,
    RESULT_ALLOW,
    CREDENTIAL_LONG_TERM,
    CREDENTIAL_TEMPORAL
} from "../src/types/ProtocolTypes.sol";

/// F0 characterization of the E ledger (pin 933d2a7): which ledger states one faulty organization
/// can change with the keys it holds. These tests assert CURRENT behaviour; a pass is a measured
/// power, not a property the ledger is claimed to enforce. No production source is changed. Each
/// expectation was written before the first run (evidence/f0-powers/first-run.txt). See
/// ledger/f0/README.md for the matrix these tests support.
abstract contract F0PowersBase is HMBCFixture {
    uint64 internal constant MALLORY_SERIAL = 301;
    bytes32 internal constant MALLORY_RECIPIENT_KEY_HASH = keccak256("HMBC.recipient-key.mallory");

    /// P-AUTH-1. Expect: grant in every profile. One authority (H3) alone issues a Doctor certificate
    /// and an OnDuty entry to a GID it controls; the emergency policy (Doctor from ANY issuer, OnDuty
    /// from the same issuer) is then satisfied for H2's record. No second organization is involved.
    function test_F0_OneAuthorityAloneAuthorizesItsOwnGidForAnotherHospitalsRecord() public {
        publishCrl(h3, h3Pk, h3Admin, 1, new uint64[](0));
        publishAcl(onDutyAcl(h3, 1, one(mallory)), h3Pk, h3Admin);
        SignedRoleCertificate memory cert = roleCert(h3, h3Pk, mallory, ROLE_DOCTOR, MALLORY_SERIAL);
        register(malloryPk, cert, MALLORY_RECIPIENT_KEY_HASH);

        CredentialBundle memory b;
        b.certificates = new SignedRoleCertificate[](1);
        b.certificates[0] = cert;
        b.temporalClaims = new TemporalClaim[](1);
        b.temporalClaims[0] = TemporalClaim(h3, ROLE_ON_DUTY);
        AccessRequest memory r = accessRequest(mallory, MALLORY_RECIPIENT_KEY_HASH, 1);
        (bytes32 digest, ErrorCode code) = submit(r, signRequest(r, malloryPk), b);
        assertCode(code, ErrorCode.NONE, "PBC forwards: H3 credentials are genuinely valid");

        bytes32 g = deliver(r, verifiedRecords(mallory, b), digest, RESULT_ALLOW);
        (,, address gid,,, bool allowed) = kssc.getGrant(g);
        assertTrue(allowed, "grant issued on H3's credentials alone");
        assertEq(gid, mallory, "grant subject is H3's own GID");
        assertEq(acsc.dataEntry(DATA_P1).owner, h2, "record belongs to H2, not to the issuing authority");
    }

    /// P-AUTH-2. Expect: the serial is revoked after list 2 and valid again after list 3. A CRL
    /// replaces the previous list wholesale (new generation), so an authority un-revokes a serial by
    /// omitting it. Repaired-e only requires the version to increase.
    function test_F0_AuthorityUnrevokesBySerialOmission() public {
        publishTrustLists(one(alice));
        registerAlice();
        publishCrl(h1, h1Pk, h1Admin, 2, _serials(ALICE_SERIAL));
        assertTrue(tmsc.isRevoked(h1, ALICE_SERIAL), "revoked by list 2");
        (ErrorCode revokedCode,) = tmsc.checkCredentials(alice, aliceBundle(), uint64(block.timestamp));
        assertCode(revokedCode, ErrorCode.REVOKED, "credential check fails while revoked");

        publishCrl(h1, h1Pk, h1Admin, 3, new uint64[](0));
        assertFalse(tmsc.isRevoked(h1, ALICE_SERIAL), "omitted from list 3: no longer revoked");
        (ErrorCode code,) = tmsc.checkCredentials(alice, aliceBundle(), uint64(block.timestamp));
        assertCode(code, ErrorCode.NONE, "credential valid again");
    }

    /// P-USER-1. Expect: GID stays registered after its certificate is revoked; a second
    /// registration for the same GID (new recipient key) rejects ALREADY_REGISTERED.
    function test_F0_RegistrationIsPermanentAndRecipientKeyWriteOnce() public {
        publishTrustLists(one(alice));
        registerAlice();
        publishCrl(h1, h1Pk, h1Admin, 2, _serials(ALICE_SERIAL));
        assertTrue(rsc.isRegistered(alice), "revocation does not deregister the GID");

        SignedRoleCertificate memory cert = aliceCert();
        Registration memory reg = Registration(
            alice,
            HMBCHash.roleCertificateDigest(cert.cert, PBC_CHAIN_ID, address(tmsc)),
            keccak256("HMBC.recipient-key.alice-2"),
            T0 + 600
        );
        bytes memory possession = sig(alicePk, HMBCHash.registrationDigest(reg, PBC_CHAIN_ID, address(rsc)));
        expectRejected(ErrorCode.ALREADY_REGISTERED);
        rsc.register(reg, possession, cert);
        assertEq(rsc.recipientKeyHash(alice), ALICE_RECIPIENT_KEY_HASH, "recipient key unchanged");
    }

    /// P-ANY-1. Expect: an arbitrary account appends a PBC request log entry and a denial for a
    /// request it cannot sign; no forwardable record is created (V-A5: every request is logged).
    function test_F0_AnyAccountAppendsRequestLogEntries() public {
        publishTrustLists(one(alice));
        registerAlice();
        AccessRequest memory r = aliceRequest(1);
        uint256 before = lsc.logCount();
        vm.prank(mallory);
        (bytes32 digest, ErrorCode code) = psc.requestAccess(r, signRequest(r, malloryPk), aliceBundle());
        assertCode(code, ErrorCode.BAD_SIGNATURE, "denied: not Alice's signature");
        assertEq(lsc.logCount(), before + 1, "request logged anyway");
        assertEq(psc.denialCount(digest), 1, "denial counted");
        assertEq(uint256(psc.getRequest(digest).status), 0, "no forwardable record");
    }

    /// P-DEP-1. Expect: after sealing, the deployer can change no wiring, policy, data registration or
    /// destination; every bootstrap entry point rejects UNAUTHORIZED_CALLER.
    function test_F0_DeployerPowerEndsAtSeal() public {
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        acsc.addPolicy(emergencyPolicy());
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        acsc.registerData(keccak256("HMBC.data.new"), h2, 0);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        acsc.wire(kssc, mallory);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        kssc.wire(mallory);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        psc.configureDestination(99, mallory);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        tmsc.wire(mallory, mallory);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        lsc.wire(mallory, mallory, mallory);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        rsc.seal();
        assertEq(tmsc.deployer(), address(this), "this test contract is the deployer");
    }

    function _serials(uint64 s) internal pure returns (uint64[] memory xs) {
        xs = new uint64[](1);
        xs[0] = s;
    }
}

contract F0PowersPaperStrictTest is F0PowersBase {
    function profile() internal pure override returns (Profile) {
        return Profile.PAPER_STRICT;
    }
}

contract F0PowersPaperMinimalTest is F0PowersBase {
    function profile() internal pure override returns (Profile) {
        return Profile.PAPER_MINIMAL;
    }
}

contract F0PowersRepairedTest is F0PowersBase {
    function profile() internal pure override returns (Profile) {
        return Profile.REPAIRED_E;
    }

    /// P-AUTH-3. Expect: STALE_STATE twice. Every accepted list update by ANY authority increments the
    /// single global TMSC.authEpoch. An unrelated authority (H3, H4) therefore invalidates Alice's
    /// signed request at the PBC, and her already-forwarded request at the DBC once a checkpoint
    /// carries the new epoch. A legitimate update right doubles as an availability lever over all users.
    function test_F0_UnrelatedAuthorityUpdateInvalidatesOtherUsersRequests() public {
        publishTrustLists(one(alice));
        registerAlice();
        AccessRequest memory r = aliceRequest(1);
        bytes memory s = signRequest(r, alicePk);
        publishCrl(h3, h3Pk, h3Admin, 1, new uint64[](0));
        (, ErrorCode code) = submit(r, s, aliceBundle());
        assertCode(code, ErrorCode.STALE_STATE, "PBC: Alice's request was signed at the previous authEpoch");

        (AccessRequest memory r2,, CredentialRecord[] memory recs) = aliceForwarded(2);
        publishCrl(h4, h4Pk, h4Admin, 1, new uint64[](0));
        StateCheckpoint memory cp = acceptCheckpoint();
        DecisionCertificate memory c = certify(decisionFor(r2, RESULT_ALLOW, recs, cp), witnessPk);
        expectRejected(ErrorCode.STALE_STATE);
        acsc.consumeDecision(r2, c, recs);
    }

    /// P-AUTH-4. Expect: accepted. Repaired-e rejects an already-expired list but sets no maximum
    /// lifetime, so the bounded-validity repair holds only if the issuing authority chooses a short one.
    function test_F0_AuthorityListValidityHasNoUpperBound() public {
        RevocationList memory l = RevocationList(h3, 1, T0 + 100 * 365 days, new uint64[](0));
        bytes memory s = signCrl(l, h3Pk);
        vm.prank(h3Admin);
        tmsc.updateRevocationList(l, s);
        assertEq(tmsc.revocationListState(h3).validUntil, T0 + 100 * 365 days, "century-long list installed");
    }

    /// P-WIT-1. Expect: grant. In E (q = 1 of 1) one witness key alone attests credential records the
    /// PBC never verified (Bob is a Researcher); the DBC evaluates the signed records only.
    function test_F0_SingleWitnessAttestsFabricatedRecords() public {
        publishTrustLists(one(alice));
        registerBob();
        AccessRequest memory r = accessRequest(bob, BOB_RECIPIENT_KEY_HASH, 1);
        (bytes32 digest, ErrorCode code) = submit(r, signRequest(r, bobPk), bobBundle());
        assertCode(code, ErrorCode.NONE, "PBC forwards: Bob's Researcher certificate is valid");

        CredentialRecord[] memory fake = new CredentialRecord[](2);
        fake[0] = CredentialRecord(h1, ROLE_DOCTOR, CREDENTIAL_LONG_TERM, 999, 1, T0 + 1 days);
        fake[1] = CredentialRecord(h1, ROLE_ON_DUTY, CREDENTIAL_TEMPORAL, 0, 1, T0 + 1 days);
        StateCheckpoint memory cp = acceptCheckpoint();
        DecisionCertificate memory c = certify(decisionFor(r, RESULT_ALLOW, fake, cp), witnessPk);
        bytes32 g = acsc.consumeDecision(r, c, fake);
        (,, address gid,,, bool allowed) = kssc.getGrant(g);
        assertTrue(allowed && gid == bob, "Bob granted on fabricated Doctor/OnDuty records");
        assertNotEq(
            psc.getRequest(digest).credentialDigest, c.decision.credentialDigest, "PBC-verified records differ"
        );
    }

    /// P-WIT-2. Expect: STALE_STATE for every later checkpoint and for every decision after expiry.
    /// One quorum-signed checkpoint with sequence = max uint64 is accepted (monotone, unbounded) and
    /// leaves no strictly greater sequence; nothing in the E ledger can reset it.
    function test_F0_PoisonCheckpointSequenceBlocksTheDbc() public {
        publishTrustLists(one(alice));
        registerAlice();
        StateCheckpoint memory poison = checkpointNow();
        poison.sequence = type(uint64).max;
        kssc.acceptState(poison, signCheckpoint(poison, witnessPk));

        StateCheckpoint memory next = checkpointNow();
        bytes[] memory s = signCheckpoint(next, witnessPk);
        expectRejected(ErrorCode.STALE_STATE);
        kssc.acceptState(next, s);

        vm.warp(poison.expiresAt);
        (AccessRequest memory r,, CredentialRecord[] memory recs) = aliceForwarded(1);
        DecisionCertificate memory c = certify(decisionFor(r, RESULT_ALLOW, recs, poison), witnessPk);
        expectRejected(ErrorCode.STALE_STATE);
        acsc.consumeDecision(r, c, recs);
    }

    /// P-WIT-3. Expect: STALE_STATE for the honest request and for the honest catch-up checkpoint. A
    /// checkpoint with authEpoch above the PBC's real value is accepted; requests carry the real
    /// authEpoch (PSC enforces it), so none can match, and the real value can never be re-accepted.
    function test_F0_PoisonCheckpointAuthEpochBlocksTheDbc() public {
        publishTrustLists(one(alice));
        registerAlice();
        StateCheckpoint memory poison = checkpointNow();
        poison.authEpoch = tmsc.authEpoch() + 1_000_000;
        kssc.acceptState(poison, signCheckpoint(poison, witnessPk));

        (AccessRequest memory r,, CredentialRecord[] memory recs) = aliceForwarded(1);
        DecisionCertificate memory c = certify(decisionFor(r, RESULT_ALLOW, recs, poison), witnessPk);
        expectRejected(ErrorCode.STALE_STATE);
        acsc.consumeDecision(r, c, recs);

        StateCheckpoint memory honest = checkpointNow();
        bytes[] memory s = signCheckpoint(honest, witnessPk);
        expectRejected(ErrorCode.STALE_STATE);
        kssc.acceptState(honest, s);
    }

    /// P-WIT-4. Expect: as P-WIT-3 for policyVersion. ACSC.policyVersion is immutable (1), the poison
    /// checkpoint carries 2, and checkpoints may not decrease it, so no decision can pass again.
    function test_F0_PoisonCheckpointPolicyVersionBlocksTheDbc() public {
        publishTrustLists(one(alice));
        registerAlice();
        StateCheckpoint memory poison = checkpointNow();
        poison.policyVersion = POLICY_VERSION + 1;
        kssc.acceptState(poison, signCheckpoint(poison, witnessPk));

        (AccessRequest memory r,, CredentialRecord[] memory recs) = aliceForwarded(1);
        DecisionCertificate memory c = certify(decisionFor(r, RESULT_ALLOW, recs, poison), witnessPk);
        expectRejected(ErrorCode.STALE_STATE);
        acsc.consumeDecision(r, c, recs);

        StateCheckpoint memory honest = checkpointNow();
        bytes[] memory s = signCheckpoint(honest, witnessPk);
        expectRejected(ErrorCode.STALE_STATE);
        kssc.acceptState(honest, s);
    }

    /// P-ANY-2. Expect: grant. Neither acceptState nor consumeDecision restricts the caller; an
    /// arbitrary account submits a valid checkpoint and certificate. All authority is in the signatures,
    /// so withholding, delaying or ordering valid certificates is open to anyone holding them.
    function test_F0_AnyAccountSubmitsCheckpointAndCertificate() public {
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory r,, CredentialRecord[] memory recs) = aliceForwarded(1);
        StateCheckpoint memory cp = checkpointNow();
        bytes[] memory s = signCheckpoint(cp, witnessPk);
        vm.prank(mallory);
        kssc.acceptState(cp, s);
        DecisionCertificate memory c = certify(decisionFor(r, RESULT_ALLOW, recs, cp), witnessPk);
        vm.prank(mallory);
        bytes32 g = acsc.consumeDecision(r, c, recs);
        (,, address gid,,, bool allowed) = kssc.getGrant(g);
        assertTrue(allowed && gid == alice, "grant for Alice, submitted by an unrelated account");
    }
}
