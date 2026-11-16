// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {HMBCFixture} from "./utils/Fixture.sol";
import {
    Profile,
    ErrorCode,
    HMBCHash,
    AccessRequest,
    CredentialRecord,
    StateCheckpoint,
    AccessDecision,
    DecisionCertificate,
    GrantReceipt,
    RESULT_ALLOW
} from "../src/types/ProtocolTypes.sol";

/// A-F1 slice 3 (design 2.2 sections 4 and 7): q = 3 of 4 on all three witness-signed paths
/// (checkpoint at KSSC, decision at ACSC, receipt at PSC) and the KSSC policy pin (the P-WIT-4
/// analogue). The quorum cases are characterization of the reused QuorumLib, expected to pass on
/// first run; the policy-pin case is the red-green test of this slice.
contract QuorumTest is HMBCFixture {
    bytes32 internal constant OUTCOME = keccak256("synthetic-outcome");

    function profile() internal pure virtual override returns (Profile) {
        return Profile.REPAIRED_F;
    }

    // ------------------------------------------------------------------ helpers

    function pks(uint256 a, uint256 b, uint256 c) internal view returns (uint256[] memory xs) {
        xs = new uint256[](3);
        (xs[0], xs[1], xs[2]) = (witnessPks[a], witnessPks[b], witnessPks[c]);
    }

    function pks2(uint256 a, uint256 b) internal view returns (uint256[] memory xs) {
        xs = new uint256[](2);
        (xs[0], xs[1]) = (witnessPks[a], witnessPks[b]);
    }

    /// The malformed signature lists every path must reject, from a valid sorted three-of-four list.
    function badLists(bytes32 d) internal view returns (bytes[][4] memory bad, ErrorCode[4] memory want) {
        bytes[] memory three = sortedSigs(pks(0, 1, 2), d);
        bad[0] = sortedSigs(pks2(0, 1), d);
        want[0] = ErrorCode.INSUFFICIENT_QUORUM;
        bad[1] = new bytes[](3);
        (bad[1][0], bad[1][1], bad[1][2]) = (three[0], three[0], three[1]);
        want[1] = ErrorCode.DUPLICATE_SIGNER;
        bad[2] = new bytes[](4);
        (bad[2][0], bad[2][1], bad[2][2], bad[2][3]) = (sig(malloryPk, d), three[0], three[1], three[2]);
        want[2] = ErrorCode.BAD_SIGNATURE;
        bad[3] = new bytes[](3);
        (bad[3][0], bad[3][1], bad[3][2]) = (three[2], three[0], three[1]);
        want[3] = ErrorCode.MALFORMED;
    }

    function cpDigest(StateCheckpoint memory cp) internal view returns (bytes32) {
        return HMBCHash.stateCheckpointDigest(cp, DBC_CHAIN_ID, address(kssc));
    }

    // ------------------------------------------------------------------ checkpoints (KSSC)

    function test_AF1Q_CheckpointAnyThreeOfFourAndFourOfFour() public {
        uint256[3][4] memory subsets = [[uint256(0), 1, 2], [uint256(1), 2, 3], [uint256(0), 2, 3], [uint256(0), 1, 3]];
        for (uint256 i = 0; i < subsets.length; i++) {
            StateCheckpoint memory cp = checkpointNow();
            kssc.acceptState(cp, sortedSigs(pks(subsets[i][0], subsets[i][1], subsets[i][2]), cpDigest(cp)));
        }
        StateCheckpoint memory all = checkpointNow();
        kssc.acceptState(all, sortedSigs(witnessPks, cpDigest(all)));
        (, StateCheckpoint memory cur) = kssc.currentCheckpoint();
        assertEq(cur.sequence, 5, "five checkpoints accepted");
    }

    function test_AF1Q_CheckpointRejectsBadQuorumLists() public {
        StateCheckpoint memory cp = checkpointNow();
        (bytes[][4] memory bad, ErrorCode[4] memory want) = badLists(cpDigest(cp));
        for (uint256 i = 0; i < 4; i++) {
            expectRejected(want[i]);
            kssc.acceptState(cp, bad[i]);
        }
        assertFalse(kssc.hasCheckpoint(), "nothing accepted");
    }

    /// One Byzantine witness signs a poison checkpoint (FL-7): one signature is not a quorum.
    function test_AF1Q_SingleWitnessCannotPoisonTheDbc() public {
        StateCheckpoint memory cp = checkpointNow();
        cp.sequence = type(uint64).max - 1;
        cp.authEpoch = type(uint64).max - 1;
        bytes[] memory one_ = new bytes[](1);
        one_[0] = sig(witnessPks[3], cpDigest(cp));
        expectRejected(ErrorCode.INSUFFICIENT_QUORUM);
        kssc.acceptState(cp, one_);
    }

    function test_AF1Q_CheckpointWithTheEWitnessSetVersionIsStaleState() public {
        StateCheckpoint memory cp = checkpointNow();
        cp.witnessSetVersion = 1;
        bytes[] memory s = sortedSigs(pks(0, 1, 2), cpDigest(cp));
        expectRejected(ErrorCode.STALE_STATE);
        kssc.acceptState(cp, s);
    }

    /// P-WIT-4 analogue (design 2.2 section 4): a q-signed checkpoint whose policyVersion is not
    /// the DBC's current one is refused, so it cannot block later decisions.
    function test_AF1Q_PolicyPinRejectsAForeignPolicyVersion() public {
        uint64[2] memory foreign = [POLICY_VERSION + 1, POLICY_VERSION - 1];
        for (uint256 i = 0; i < 2; i++) {
            StateCheckpoint memory cp = checkpointNow();
            cp.policyVersion = foreign[i];
            bytes[] memory s = sortedSigs(pks(0, 1, 2), cpDigest(cp));
            expectRejected(ErrorCode.STALE_STATE);
            kssc.acceptState(cp, s);
        }
        assertFalse(kssc.hasCheckpoint(), "no checkpoint accepted");
        // positive control: the DBC's own policy version is accepted
        StateCheckpoint memory ok = checkpointNow();
        assertEq(ok.policyVersion, acsc.policyVersion(), "fixture uses the ACSC policy version");
        kssc.acceptState(ok, sortedSigs(pks(0, 1, 2), cpDigest(ok)));
        assertTrue(kssc.hasCheckpoint(), "accepted");
    }

    // ------------------------------------------------------------------ decisions (ACSC)

    function certifiedAliceDecision()
        internal
        returns (AccessRequest memory r, CredentialRecord[] memory recs, AccessDecision memory d)
    {
        publishTrustLists(one(alice));
        registerAlice();
        (r,, recs) = aliceForwarded(1);
        StateCheckpoint memory cp = acceptCheckpoint();
        d = decisionFor(r, RESULT_ALLOW, recs, cp);
    }

    function test_AF1Q_DecisionThreeOfFourGrants() public {
        (AccessRequest memory r, CredentialRecord[] memory recs, AccessDecision memory d) = certifiedAliceDecision();
        DecisionCertificate memory c;
        c.decision = d;
        c.signatures = sortedSigs(pks(1, 2, 3), HMBCHash.accessDecisionDigest(d, DBC_CHAIN_ID, address(kssc)));
        vm.prank(relay);
        bytes32 grantId = acsc.consumeDecision(r, c, recs);
        assertTrue(grantId != bytes32(0), "witness-2..4 grant");
    }

    function test_AF1Q_DecisionRejectsBadQuorumLists() public {
        (AccessRequest memory r, CredentialRecord[] memory recs, AccessDecision memory d) = certifiedAliceDecision();
        (bytes[][4] memory bad, ErrorCode[4] memory want) =
            badLists(HMBCHash.accessDecisionDigest(d, DBC_CHAIN_ID, address(kssc)));
        DecisionCertificate memory c;
        c.decision = d;
        for (uint256 i = 0; i < 4; i++) {
            c.signatures = bad[i];
            vm.prank(relay);
            expectRejected(want[i]);
            acsc.consumeDecision(r, c, recs);
        }
    }

    // ------------------------------------------------------------------ receipts (PSC)

    function grantedAlice() internal returns (bytes32 digest, GrantReceipt memory g) {
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory r, bytes32 d, CredentialRecord[] memory recs) = aliceForwarded(1);
        bytes32 grantId = deliver(r, recs, d, RESULT_ALLOW);
        assertTrue(grantId != bytes32(0), "fixture grant");
        return (d, receiptFor(grantId));
    }

    function test_AF1Q_ReceiptThreeOfFourRecordsTheOutcome() public {
        (bytes32 digest, GrantReceipt memory g) = grantedAlice();
        bytes[] memory s = sortedSigs(pks(0, 2, 3), HMBCHash.grantReceiptDigest(g, PBC_CHAIN_ID, address(psc)));
        vm.prank(relay);
        uint256 logId = psc.reportAttestedOutcome(digest, OUTCOME, g, s);
        assertTrue(logId != 0, "outcome recorded");
    }

    function test_AF1Q_ReceiptRejectsBadQuorumLists() public {
        (bytes32 digest, GrantReceipt memory g) = grantedAlice();
        (bytes[][4] memory bad, ErrorCode[4] memory want) =
            badLists(HMBCHash.grantReceiptDigest(g, PBC_CHAIN_ID, address(psc)));
        for (uint256 i = 0; i < 4; i++) {
            vm.prank(relay);
            expectRejected(want[i]);
            psc.reportAttestedOutcome(digest, OUTCOME, g, bad[i]);
        }
    }
}
