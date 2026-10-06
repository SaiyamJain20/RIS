// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {HMBCFixture} from "./utils/Fixture.sol";
import {
    Profile,
    ErrorCode,
    HMBCHash,
    Registration,
    SignedRoleCertificate,
    AccessRequest,
    CredentialBundle,
    CredentialRecord,
    DecisionCertificate,
    StateCheckpoint,
    ForwardedRequest,
    TemporalClaim,
    ACTION_READ,
    RESULT_ALLOW,
    RESULT_DENY
} from "../src/types/ProtocolTypes.sol";
import {LSC} from "../src/LSC.sol";
import {PSC} from "../src/PSC.sol";
import {KSSC} from "../src/KSSC.sol";

/// A-E1: legitimate access flow and the basic denials, run once per profile.
abstract contract AccessFlowBase is HMBCFixture {
    // -------------------------------------------------------------- positive control

    function test_AliceRegisteredDoctorOnDutyGetsGrant() public {
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory r, bytes32 digest, CredentialRecord[] memory recs) = aliceForwarded(1);

        PSC.RequestRecord memory pr = psc.getRequest(digest);
        assertTrue(pr.status == PSC.RequestStatus.FORWARDED, "PBC request forwarded");
        assertEq(pr.credentialDigest, HMBCHash.hashCredentialRecords(recs), "PBC binds verified attributes");
        assertEq(recs.length, 2, "Doctor + OnDuty records");

        bytes32 grantId = deliver(r, recs, digest, RESULT_ALLOW);
        assertEq(grantId, HMBCHash.grantId(digest, address(kssc), DBC_CHAIN_ID), "v0 grantId formula");
        (bytes32 gReq, bytes32 gData, address gGid, uint64 gEpoch, uint64 gExp, bool allowed) = kssc.getGrant(grantId);
        assertTrue(allowed, "grant allowed");
        assertEq(gReq, digest, "grant bound to request digest");
        assertEq(gData, DATA_P1, "grant bound to data");
        assertEq(gGid, alice, "grant bound to subject");
        assertEq(gEpoch, 0, "keyEpoch 0 in E");
        assertTrue(gExp > block.timestamp, "grant unexpired");
        assertEq(acsc.accessLogCount(), 1, "one ACSC accessLog");
        if (profile() == Profile.REPAIRED_E) {
            assertTrue(kssc.nonceConsumed(alice, 1), "nonce consumed with grant");
            assertEq(kssc.grantDetails(grantId).recipientKeyHash, ALICE_RECIPIENT_KEY_HASH, "recipient bound");
        } else {
            assertFalse(kssc.nonceConsumed(alice, 1), "paper profiles do not track nonces");
        }

        vm.prank(relay);
        uint256 outcomeLog = psc.reportOutcome(digest, grantId, keccak256("synthetic-outcome:released"));
        assertTrue(outcomeLog > lsc.firstRequestLogId(digest), "outcome logged after request");
        assertTrue(psc.getRequest(digest).status == PSC.RequestStatus.OUTCOME_RECORDED, "PBC outcome recorded");
    }

    // -------------------------------------------------------------- denials

    function test_BobWithoutDoctorRoleIsDeniedAndGetsNoGrant() public {
        publishTrustLists(one(alice));
        registerBob();
        AccessRequest memory r = accessRequest(bob, BOB_RECIPIENT_KEY_HASH, 7);
        (bytes32 digest, ErrorCode code) = submit(r, signRequest(r, bobPk), bobBundle());
        assertCode(code, ErrorCode.NONE, "Bob's own credentials are valid; policy is enforced on the DBC");
        CredentialRecord[] memory recs = verifiedRecords(bob, bobBundle());

        bytes32 grantId = deliver(r, recs, digest, RESULT_DENY);
        assertEq(grantId, bytes32(0), "no grant id");
        (,,,,, bool allowed) = kssc.getGrant(HMBCHash.grantId(digest, address(kssc), DBC_CHAIN_ID));
        assertFalse(allowed, "no grant state for Bob");
        assertEq(acsc.accessLogCount(), 1, "denial is logged on the DBC");
        assertFalse(kssc.nonceConsumed(bob, 7), "denial consumes no nonce");
    }

    function test_TemporalRoleWithoutLongTermDoctorIsDenied() public {
        publishTrustLists(one(bob)); // Bob is "on duty" at H1 but holds no Doctor certificate
        registerBob();
        CredentialBundle memory b = bobBundle();
        b.temporalClaims = new TemporalClaim[](1);
        b.temporalClaims[0] = TemporalClaim(h1, ROLE_ON_DUTY);
        AccessRequest memory r = accessRequest(bob, BOB_RECIPIENT_KEY_HASH, 8);
        (bytes32 digest, ErrorCode code) = submit(r, signRequest(r, bobPk), b);
        assertCode(code, ErrorCode.NONE, "credentials valid");
        bytes32 grantId = deliver(r, verifiedRecords(bob, b), digest, RESULT_DENY);
        assertEq(grantId, bytes32(0), "temporal-only access denied (III-C4)");
    }

    function test_UnregisteredUserIsDeniedAtPbcButRequestIsLogged() public {
        publishTrustLists(one(alice));
        AccessRequest memory r = aliceRequest(1);
        uint256 before = lsc.logCount();
        (bytes32 digest, ErrorCode code) = submit(r, signRequest(r, alicePk), aliceBundle());
        assertCode(code, ErrorCode.NOT_REGISTERED, "unregistered");
        assertEq(lsc.logCount(), before + 1, "request logged before validation (Table 2 order)");
        assertTrue(lsc.firstRequestLogId(digest) != 0, "request log persists after denial");
        assertTrue(psc.getRequest(digest).status == PSC.RequestStatus.NONE, "no forwardable record");
        assertEq(psc.denialCount(digest), 1, "denial counted");
    }

    function test_RequestSignedByAnotherKeyIsDenied() public {
        publishTrustLists(one(alice));
        registerAlice();
        AccessRequest memory r = aliceRequest(1);
        (bytes32 digest, ErrorCode code) = submit(r, signRequest(r, malloryPk), aliceBundle());
        assertCode(code, ErrorCode.BAD_SIGNATURE, "subject must sign");
        assertTrue(psc.getRequest(digest).status == PSC.RequestStatus.NONE, "nothing forwarded");
    }

    function test_RequestAtExactExpiryIsDenied() public {
        publishTrustLists(one(alice));
        registerAlice();
        AccessRequest memory r = aliceRequest(1);
        bytes memory s = signRequest(r, alicePk);
        vm.warp(r.expiresAt);
        (, ErrorCode code) = submit(r, s, aliceBundle());
        assertCode(code, ErrorCode.EXPIRED, "now == expiresAt rejects");
    }

    function test_DuplicateForwardedRequestIsReplayAndBothAreLogged() public {
        publishTrustLists(one(alice));
        registerAlice();
        AccessRequest memory r = aliceRequest(1);
        bytes memory s = signRequest(r, alicePk);
        (bytes32 digest,) = submit(r, s, aliceBundle());
        uint256 before = lsc.logCount();
        (bytes32 digest2, ErrorCode code) = submit(r, s, aliceBundle());
        assertEq(digest2, digest, "same digest");
        assertCode(code, ErrorCode.REPLAY, "duplicate request");
        assertEq(lsc.logCount(), before + 1, "duplicate submission is still logged");
    }

    function test_WrongDestinationRequestIsDenied() public {
        publishTrustLists(one(alice));
        registerAlice();
        AccessRequest memory r = aliceRequest(1);
        r.kssc = address(0xBEEF);
        (, ErrorCode code) = submit(r, signRequest(r, alicePk), aliceBundle());
        assertCode(code, ErrorCode.WRONG_DESTINATION, "unknown destination KSSC");
    }

    function test_RecipientKeyMustMatchRegistration() public {
        publishTrustLists(one(alice));
        registerAlice();
        AccessRequest memory r = aliceRequest(1);
        r.recipientKeyHash = BOB_RECIPIENT_KEY_HASH;
        (, ErrorCode code) = submit(r, signRequest(r, alicePk), aliceBundle());
        assertCode(code, ErrorCode.WRONG_SUBJECT, "recipient key not registered for gid");
    }

    // -------------------------------------------------------------- registration

    function test_RegistrationWithoutGidPossessionFails() public {
        SignedRoleCertificate memory cert = aliceCert();
        Registration memory reg = Registration(
            alice, HMBCHash.roleCertificateDigest(cert.cert, PBC_CHAIN_ID, address(tmsc)), ALICE_RECIPIENT_KEY_HASH, T0 + 600
        );
        bytes memory forged = sig(malloryPk, HMBCHash.registrationDigest(reg, PBC_CHAIN_ID, address(rsc)));
        uint256 before = lsc.logCount();
        expectRejected(ErrorCode.BAD_SIGNATURE);
        rsc.register(reg, forged, cert);
        assertFalse(rsc.isRegistered(alice), "not registered");
        assertEq(lsc.logCount(), before, "no registration log");
    }

    function test_RegistrationWithAnotherUsersCertificateFails() public {
        SignedRoleCertificate memory cert = bobCert(); // certificate subject is Bob
        Registration memory reg = Registration(
            alice, HMBCHash.roleCertificateDigest(cert.cert, PBC_CHAIN_ID, address(tmsc)), ALICE_RECIPIENT_KEY_HASH, T0 + 600
        );
        bytes memory possession = sig(alicePk, HMBCHash.registrationDigest(reg, PBC_CHAIN_ID, address(rsc)));
        expectRejected(ErrorCode.WRONG_SUBJECT);
        rsc.register(reg, possession, cert);
    }

    function test_RegistrationWithUnknownIssuerFails() public {
        SignedRoleCertificate memory cert = roleCert(mallory, malloryPk, alice, ROLE_DOCTOR, 999);
        Registration memory reg = Registration(
            alice, HMBCHash.roleCertificateDigest(cert.cert, PBC_CHAIN_ID, address(tmsc)), ALICE_RECIPIENT_KEY_HASH, T0 + 600
        );
        bytes memory possession = sig(alicePk, HMBCHash.registrationDigest(reg, PBC_CHAIN_ID, address(rsc)));
        expectRejected(ErrorCode.UNKNOWN_AUTHORITY);
        rsc.register(reg, possession, cert);
    }

    function test_DuplicateRegistrationFails() public {
        publishTrustLists(one(alice)); // repaired-e needs H1's current CRL to register
        registerAlice();
        SignedRoleCertificate memory cert = aliceCert();
        Registration memory reg = Registration(
            alice, HMBCHash.roleCertificateDigest(cert.cert, PBC_CHAIN_ID, address(tmsc)), BOB_RECIPIENT_KEY_HASH, T0 + 600
        );
        bytes memory possession = sig(alicePk, HMBCHash.registrationDigest(reg, PBC_CHAIN_ID, address(rsc)));
        expectRejected(ErrorCode.ALREADY_REGISTERED);
        rsc.register(reg, possession, cert);
        assertEq(rsc.recipientKeyHash(alice), ALICE_RECIPIENT_KEY_HASH, "original binding kept");
    }

    // -------------------------------------------------------------- outcome

    function test_OutcomeRequiresRelayForwardedRequestAndMatchingGrant() public {
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory r, bytes32 digest, CredentialRecord[] memory recs) = aliceForwarded(1);
        bytes32 grantId = deliver(r, recs, digest, RESULT_ALLOW);
        bytes32 outcome = keccak256("synthetic-outcome:released");

        vm.prank(mallory);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        psc.reportOutcome(digest, grantId, outcome);

        vm.prank(relay);
        expectRejected(ErrorCode.WRONG_SUBJECT);
        psc.reportOutcome(keccak256("unknown-request"), grantId, outcome);

        vm.prank(relay);
        expectRejected(ErrorCode.WRONG_DESTINATION);
        psc.reportOutcome(digest, keccak256("other-grant"), outcome);

        vm.prank(relay);
        psc.reportOutcome(digest, grantId, outcome);
        vm.prank(relay);
        expectRejected(ErrorCode.REPLAY);
        psc.reportOutcome(digest, grantId, outcome);
    }

    // -------------------------------------------------------------- actuators (Tables 2/3)

    function test_TableActuatorRestrictions() public {
        vm.prank(mallory);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        lsc.requestLog(bytes32(0), "");

        vm.prank(mallory);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        lsc.updateLog(bytes32(0), "");

        vm.prank(mallory);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        lsc.registrationLog(bytes32(0), "");

        CredentialBundle memory b = aliceBundle();
        vm.prank(mallory);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        tmsc.getUserValidation(alice, b);

        vm.prank(mallory);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        kssc.requestData(KSSC.GrantParams(bytes32(uint256(1)), DATA_P1, mallory, 0, T0 + 30, bytes32(0), false, 0));

        if (profile() != Profile.REPAIRED_E) {
            vm.prank(mallory);
            expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
            acsc.policyEnf(ForwardedRequest(bytes32(uint256(1)), mallory, DATA_P1, ACTION_READ), new CredentialRecord[](0));
        }
    }

    function test_OmittedFunctionsFailExplicitly() public {
        expectRejected(ErrorCode.NOT_IMPLEMENTED_IN_PHASE);
        lsc.retrieveLog(0, "");
        expectRejected(ErrorCode.NOT_IMPLEMENTED_IN_PHASE);
        tmsc.addCA("");
        expectRejected(ErrorCode.NOT_IMPLEMENTED_IN_PHASE);
        tmsc.removeCA("");
        expectRejected(ErrorCode.NOT_IMPLEMENTED_IN_PHASE);
        psc.majorityConsent("");
    }

    function test_ConfigurationIsSealed() public {
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        psc.configureDestination(99, address(0xBEEF));
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        acsc.registerData(keccak256("other"), h1, 0);
        expectRejected(ErrorCode.UNAUTHORIZED_CALLER);
        kssc.wire(mallory);
    }
}

contract AccessFlowPaperStrictTest is AccessFlowBase {
    function profile() internal pure override returns (Profile) {
        return Profile.PAPER_STRICT;
    }

    function test_PaperRelayDuplicateForwardIsReplay() public {
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory r, bytes32 digest, CredentialRecord[] memory recs) = aliceForwarded(1);
        deliver(r, recs, digest, RESULT_ALLOW);
        uint256 logs = acsc.accessLogCount();
        vm.prank(relay);
        expectRejected(ErrorCode.REPLAY);
        acsc.policyEnf(ForwardedRequest(digest, alice, DATA_P1, ACTION_READ), recs);
        assertEq(acsc.accessLogCount(), logs, "reverted duplicate leaves no access log");
    }

    function test_RepairedEntryPointsAreDisabled() public {
        StateCheckpoint memory cp = checkpointNow();
        bytes[] memory sigs = signCheckpoint(cp, witnessPk);
        expectRejected(ErrorCode.WRONG_PROFILE);
        kssc.acceptState(cp, sigs);
    }
}

contract AccessFlowPaperMinimalTest is AccessFlowBase {
    function profile() internal pure override returns (Profile) {
        return Profile.PAPER_MINIMAL;
    }
}

contract AccessFlowRepairedTest is AccessFlowBase {
    function profile() internal pure override returns (Profile) {
        return Profile.REPAIRED_E;
    }

    function test_PaperRelayEntryIsDisabled() public {
        vm.prank(relay);
        expectRejected(ErrorCode.WRONG_PROFILE);
        acsc.policyEnf(ForwardedRequest(bytes32(uint256(1)), alice, DATA_P1, ACTION_READ), new CredentialRecord[](0));
    }

    function test_RejectedCertificateChangesNoState() public {
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory r,, CredentialRecord[] memory recs) = aliceForwarded(1);
        StateCheckpoint memory cp = acceptCheckpoint();
        DecisionCertificate memory c = certify(decisionFor(r, RESULT_ALLOW, recs, cp), malloryPk);
        expectRejected(ErrorCode.BAD_SIGNATURE);
        acsc.consumeDecision(r, c, recs);
        assertFalse(kssc.nonceConsumed(alice, 1), "nonce untouched");
        assertEq(acsc.accessLogCount(), 0, "no access log");
        (,,,,, bool allowed) = kssc.getGrant(HMBCHash.grantId(HMBCHash.accessRequestDigest(r), address(kssc), DBC_CHAIN_ID));
        assertFalse(allowed, "no grant");
    }

    function test_ReplayedCertificateIsRejected() public {
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory r,, CredentialRecord[] memory recs) = aliceForwarded(1);
        StateCheckpoint memory cp = acceptCheckpoint();
        DecisionCertificate memory c = certify(decisionFor(r, RESULT_ALLOW, recs, cp), witnessPk);
        bytes32 grantId = acsc.consumeDecision(r, c, recs);
        expectRejected(ErrorCode.REPLAY);
        acsc.consumeDecision(r, c, recs);
        (,,,,, bool allowed) = kssc.getGrant(grantId);
        assertTrue(allowed, "first grant still readable");
        assertEq(acsc.accessLogCount(), 1, "one access log");
    }

    function test_WitnessAllowForPolicyDeniedSubjectIsRejected() public {
        publishTrustLists(one(alice));
        registerBob();
        AccessRequest memory r = accessRequest(bob, BOB_RECIPIENT_KEY_HASH, 7);
        submit(r, signRequest(r, bobPk), bobBundle());
        CredentialRecord[] memory recs = verifiedRecords(bob, bobBundle());
        StateCheckpoint memory cp = acceptCheckpoint();
        DecisionCertificate memory c = certify(decisionFor(r, RESULT_ALLOW, recs, cp), witnessPk);
        expectRejected(ErrorCode.POLICY_DENIED);
        acsc.consumeDecision(r, c, recs);
        assertFalse(kssc.nonceConsumed(bob, 7), "nonce untouched");
    }
}
