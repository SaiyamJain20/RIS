// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;
// Agent 1 SCRATCH test (not part of the ledger module; run on a git-archive copy of 85c59f5).
// Question (A3-0144 wording): under REPAIRED_F, after a compromised quorum (3 of 4) installs a checkpoint
// with authEpoch or sourceBlockNumber saturated, can HONEST operation continue? An honest checkpoint
// carries the PBC's real values (checkpointNow()), which are below the saturated ones.
// Classification: tested reconstruction result OUTSIDE the f=1 bound.
import {HMBCFixture} from "./utils/Fixture.sol";
import {Profile, HMBCHash, AccessRequest, CredentialRecord, StateCheckpoint, AccessDecision,
    DecisionCertificate, RESULT_ALLOW, ErrorCode, Rejected} from "../src/types/ProtocolTypes.sol";

contract QuorumSaturateF is HMBCFixture {
    function profile() internal pure override returns (Profile) { return Profile.REPAIRED_F; }

    function pks(uint256 a, uint256 b, uint256 c) internal view returns (uint256[] memory xs) {
        xs = new uint256[](3); xs[0] = witnessPks[a]; xs[1] = witnessPks[b]; xs[2] = witnessPks[c];
    }

    function sigsFor(StateCheckpoint memory cp, uint256[] memory k) internal view returns (bytes[] memory) {
        return sortedSigs(k, HMBCHash.stateCheckpointDigest(cp, DBC_CHAIN_ID, address(kssc)));
    }

    function certFor(AccessDecision memory d, uint256[] memory k) internal view returns (DecisionCertificate memory c) {
        c.decision = d;
        c.signatures = sortedSigs(k, HMBCHash.accessDecisionDigest(d, DBC_CHAIN_ID, address(kssc)));
    }

    /// authEpoch saturated: (1) Alice's honest request (real authEpoch) is STALE_STATE even while the
    /// poisoned checkpoint is fresh; (2) the next honest checkpoint (real, lower authEpoch) is STALE_STATE.
    function test_saturated_authEpoch_blocks_honest_decisions_and_checkpoints() public {
        publishTrustLists(one(alice));
        registerAlice();
        StateCheckpoint memory poison = checkpointNow();
        poison.authEpoch = type(uint64).max;
        kssc.acceptState(poison, sigsFor(poison, pks(0, 1, 2)));

        (AccessRequest memory r,, CredentialRecord[] memory recs) = aliceForwarded(1);
        DecisionCertificate memory c = certFor(decisionFor(r, RESULT_ALLOW, recs, poison), pks(0, 1, 2));
        vm.expectRevert(abi.encodeWithSelector(Rejected.selector, ErrorCode.STALE_STATE));
        acsc.consumeDecision(r, c, recs);

        StateCheckpoint memory honest = checkpointNow();
        bytes[] memory hs = sigsFor(honest, pks(0, 2, 3));
        vm.expectRevert(abi.encodeWithSelector(Rejected.selector, ErrorCode.STALE_STATE));
        kssc.acceptState(honest, hs);
    }

    /// sourceBlockNumber saturated: the next honest checkpoint (real block number) is STALE_STATE;
    /// once the poisoned checkpoint expires, Alice's honest decision is STALE_STATE.
    function test_saturated_sourceBlockNumber_blocks_honest_checkpoints_then_decisions() public {
        publishTrustLists(one(alice));
        registerAlice();
        StateCheckpoint memory poison = checkpointNow();
        poison.sourceBlockNumber = type(uint256).max;
        kssc.acceptState(poison, sigsFor(poison, pks(0, 1, 2)));

        StateCheckpoint memory honest = checkpointNow();
        bytes[] memory hs = sigsFor(honest, pks(0, 2, 3));
        vm.expectRevert(abi.encodeWithSelector(Rejected.selector, ErrorCode.STALE_STATE));
        kssc.acceptState(honest, hs);

        vm.warp(poison.expiresAt);
        (AccessRequest memory r,, CredentialRecord[] memory recs) = aliceForwarded(1);
        DecisionCertificate memory c = certFor(decisionFor(r, RESULT_ALLOW, recs, poison), pks(0, 2, 3));
        vm.expectRevert(abi.encodeWithSelector(Rejected.selector, ErrorCode.STALE_STATE));
        acsc.consumeDecision(r, c, recs);
    }

    /// Control: the same honest checkpoint sequence is accepted when nothing was poisoned.
    function test_control_honest_checkpoints_advance_without_poison() public {
        StateCheckpoint memory a = checkpointNow();
        kssc.acceptState(a, sigsFor(a, pks(0, 1, 2)));
        StateCheckpoint memory b = checkpointNow();
        kssc.acceptState(b, sigsFor(b, pks(0, 2, 3)));
        (bool has, StateCheckpoint memory cur) = kssc.currentCheckpoint();
        assertTrue(has && cur.sequence == b.sequence, "honest checkpoint installed");
    }
}
