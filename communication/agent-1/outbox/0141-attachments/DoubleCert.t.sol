// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;
// Agent 1 SCRATCH test (not part of the ledger module; run on a git-archive copy of 85c59f5).
// Question: outside f=1 (two Byzantine witnesses sign both values), what do two conflicting
// quorum certificates for ONE slot do on the ledger? Witnesses w0,w1 play Byzantine (sign both);
// w2 signs only value X, w3 only value Y. Classification: tested reconstruction result OUTSIDE the
// fault bound; nothing here is reachable with f<=1 from a single decision slot.
import {HMBCFixture} from "./utils/Fixture.sol";
import {Profile, HMBCHash, AccessRequest, CredentialRecord, StateCheckpoint, AccessDecision,
    DecisionCertificate, RESULT_ALLOW, RESULT_DENY, ErrorCode, Rejected} from "../src/types/ProtocolTypes.sol";

contract DoubleCertF is HMBCFixture {
    function profile() internal pure override returns (Profile) { return Profile.REPAIRED_F; }

    function pk3(uint256 a, uint256 b, uint256 c) internal view returns (uint256[] memory xs) {
        xs = new uint256[](3); xs[0] = witnessPks[a]; xs[1] = witnessPks[b]; xs[2] = witnessPks[c];
    }

    function cert(AccessDecision memory d, uint256[] memory pks) internal view returns (DecisionCertificate memory c) {
        c.decision = d;
        c.signatures = sortedSigs(pks, HMBCHash.accessDecisionDigest(d, DBC_CHAIN_ID, address(kssc)));
    }

    function setupRequest() internal returns (AccessRequest memory r, CredentialRecord[] memory recs, StateCheckpoint memory cp) {
        publishTrustLists(one(alice));
        registerAlice();
        (r,, recs) = aliceForwarded(1);
        cp = checkpointNow();
        kssc.acceptState(cp, sortedSigs(pk3(0, 1, 2), HMBCHash.stateCheckpointDigest(cp, DBC_CHAIN_ID, address(kssc))));
    }

    /// Two conflicting checkpoints with the same sequence: the first lands, the second is STALE_STATE.
    function test_conflicting_checkpoints_same_sequence_second_is_stale() public {
        StateCheckpoint memory a = checkpointNow();
        StateCheckpoint memory b = a;
        b.sourceBlockHash = keccak256("conflicting view");
        kssc.acceptState(a, sortedSigs(pk3(0, 1, 2), HMBCHash.stateCheckpointDigest(a, DBC_CHAIN_ID, address(kssc))));
        bytes[] memory sb = sortedSigs(pk3(0, 1, 3), HMBCHash.stateCheckpointDigest(b, DBC_CHAIN_ID, address(kssc)));
        vm.expectRevert(abi.encodeWithSelector(Rejected.selector, ErrorCode.STALE_STATE));
        kssc.acceptState(b, sb);
    }

    /// DENY certificate consumed, then a conflicting ALLOW certificate for the same request: both are
    /// accepted (denial consumes no nonce, an E0 design choice), so one request shows a denial AND a grant.
    function test_deny_then_conflicting_allow_both_consumed() public {
        (AccessRequest memory r, CredentialRecord[] memory recs, StateCheckpoint memory cp) = setupRequest();
        DecisionCertificate memory deny = cert(decisionFor(r, RESULT_DENY, recs, cp), pk3(0, 1, 2));
        DecisionCertificate memory allow = cert(decisionFor(r, RESULT_ALLOW, recs, cp), pk3(0, 1, 3));
        vm.prank(relay);
        assertEq(acsc.consumeDecision(r, deny, recs), bytes32(0), "deny consumed, no grant");
        vm.prank(relay);
        bytes32 g = acsc.consumeDecision(r, allow, recs);
        assertTrue(g != bytes32(0), "conflicting allow also consumed: grant created");
        assertEq(acsc.accessLogCount(), 2, "two access-log entries for one request");
    }

    /// Two different ALLOW certificates for the same request: the second is REPLAY (one grant per request).
    function test_two_allow_certificates_second_is_replay() public {
        (AccessRequest memory r, CredentialRecord[] memory recs, StateCheckpoint memory cp) = setupRequest();
        AccessDecision memory d1 = decisionFor(r, RESULT_ALLOW, recs, cp);
        AccessDecision memory d2 = d1;
        d2.expiresAt = d1.expiresAt - 1; // a different signed decision, same request
        DecisionCertificate memory c1 = cert(d1, pk3(0, 1, 2));
        DecisionCertificate memory c2 = cert(d2, pk3(0, 1, 3));
        vm.prank(relay);
        acsc.consumeDecision(r, c1, recs);
        vm.prank(relay);
        vm.expectRevert(abi.encodeWithSelector(Rejected.selector, ErrorCode.REPLAY));
        acsc.consumeDecision(r, c2, recs);
    }

    /// ALLOW consumed, then a conflicting DENY: the DENY is still accepted and logged after the grant.
    function test_allow_then_conflicting_deny_both_consumed() public {
        (AccessRequest memory r, CredentialRecord[] memory recs, StateCheckpoint memory cp) = setupRequest();
        DecisionCertificate memory allow = cert(decisionFor(r, RESULT_ALLOW, recs, cp), pk3(0, 1, 2));
        DecisionCertificate memory deny = cert(decisionFor(r, RESULT_DENY, recs, cp), pk3(0, 1, 3));
        vm.prank(relay);
        assertTrue(acsc.consumeDecision(r, allow, recs) != bytes32(0), "grant");
        vm.prank(relay);
        assertEq(acsc.consumeDecision(r, deny, recs), bytes32(0), "deny after grant is accepted and logged");
        assertEq(acsc.accessLogCount(), 2, "two access-log entries for one request");
    }
}
