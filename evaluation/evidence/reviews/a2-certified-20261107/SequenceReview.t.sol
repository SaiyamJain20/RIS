// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {HMBCFixture} from "owner/test/utils/Fixture.sol";
import {Profile, StateCheckpoint, ErrorCode} from "owner/src/types/ProtocolTypes.sol";

/// Evaluator-owned isolated proof harness. Owner sources and assertions remain untouched.
/// Three synthetic quorum keys are deliberately controlled: outside the f=1 model.
contract SequenceReview is HMBCFixture {
    function profile() internal pure override returns (Profile) { return Profile.REPAIRED_F; }

    function install(uint64 sequence) internal returns (StateCheckpoint memory cp) {
        cp = checkpointNow();
        cp.sequence = sequence;
        kssc.acceptState(cp, signCheckpoint(cp, witnessPk));
        (bool exists, StateCheckpoint memory current) = kssc.currentCheckpoint();
        assertTrue(exists, "checkpoint installed");
        assertEq(current.sequence, sequence, "exact sequence installed");
    }

    function test_FirstFiveThenSevenAccepted() public {
        install(5);
        install(7);
    }

    function test_LowerAndReplayRefuse() public {
        install(7);
        StateCheckpoint memory cp = checkpointNow();
        cp.sequence = 3;
        bytes[] memory signatures = signCheckpoint(cp, witnessPk);
        expectRejected(ErrorCode.STALE_STATE);
        kssc.acceptState(cp, signatures);
        cp.sequence = 7;
        signatures = signCheckpoint(cp, witnessPk);
        expectRejected(ErrorCode.STALE_STATE);
        kssc.acceptState(cp, signatures);
        (, StateCheckpoint memory current) = kssc.currentCheckpoint();
        assertEq(current.sequence, 7, "rejections preserve checkpoint");
    }

    function test_TwoSignaturesCannotInstallMaximum() public {
        StateCheckpoint memory cp = checkpointNow();
        cp.sequence = type(uint64).max;
        bytes[] memory all = signCheckpoint(cp, witnessPk);
        assertEq(all.length, 3, "fixture produces q=3");
        bytes[] memory two = new bytes[](2);
        two[0] = all[0]; two[1] = all[1];
        expectRejected(ErrorCode.INSUFFICIENT_QUORUM);
        kssc.acceptState(cp, two);
        (bool exists,) = kssc.currentCheckpoint();
        assertFalse(exists, "insufficient quorum writes nothing");
        install(1); // Reject-everything cannot satisfy the control.
    }

    function test_MaximumAcceptedThenBoundaryValuesRefuse() public {
        install(type(uint64).max);
        rejectAfterMaximum(0);
        rejectAfterMaximum(1);
        rejectAfterMaximum(type(uint64).max - 1);
        rejectAfterMaximum(type(uint64).max);
    }

    function testFuzz_NoRepresentableSuccessorAfterMaximum(uint64 sequence) public {
        install(type(uint64).max);
        rejectAfterMaximum(sequence);
    }

    function rejectAfterMaximum(uint64 sequence) internal {
        StateCheckpoint memory cp = checkpointNow();
        cp.sequence = sequence;
        bytes[] memory signatures = signCheckpoint(cp, witnessPk);
        expectRejected(ErrorCode.STALE_STATE);
        kssc.acceptState(cp, signatures);
        (, StateCheckpoint memory current) = kssc.currentCheckpoint();
        assertEq(current.sequence, type(uint64).max, "maximum remains installed");
    }
}
