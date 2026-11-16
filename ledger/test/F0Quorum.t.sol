// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {HMBCFixture} from "./utils/Fixture.sol";
import {
    Profile,
    ErrorCode,
    HMBCHash,
    AccessRequest,
    CredentialRecord,
    DecisionCertificate,
    StateCheckpoint,
    RESULT_ALLOW
} from "../src/types/ProtocolTypes.sol";
import {KSSC} from "../src/KSSC.sol";

/// F0 characterization of the EXISTING QuorumLib (src/lib/SigLib.sol) under the planned F witness
/// configuration n = 4, q = 3. A test-only KSSC is constructed with four witnesses; no production
/// source changes, and this is not A-F1 work. These tests measure what the E code already does, so the
/// F0 matrix can pre-register FL-2..FL-7 on evidence. Decisions (DecisionVerifier) and receipts (PSC)
/// call the same QuorumLib.verify; only the checkpoint path is exercised here. Expectations were written
/// before the first run (evidence/f0-powers/quorum-first-run.txt).
contract F0QuorumRepairedTest is HMBCFixture {
    uint256 internal constant N = 4;
    uint256 internal constant Q = 3;

    KSSC internal kssc4;
    uint256[N] internal wPk;
    uint64 internal seq4;

    function profile() internal pure override returns (Profile) {
        return Profile.REPAIRED_E;
    }

    function setUp() public override {
        super.setUp();
        address[] memory ws = new address[](N);
        for (uint256 i = 0; i < N; i++) {
            wPk[i] = syntheticKey(string.concat("witness-", vm.toString(i + 1)));
            ws[i] = vm.addr(wPk[i]);
        }
        vm.chainId(DBC_CHAIN_ID);
        kssc4 = new KSSC(
            KSSC.Config(
                Profile.REPAIRED_E, 0, DBC_CHAIN_ID, PBC_CHAIN_ID, address(psc), WITNESS_SET_VERSION, ws, Q, CHECKPOINT_TTL
            )
        );
        kssc4.wire(address(acsc));
        kssc4.seal();
        vm.chainId(PBC_CHAIN_ID);
    }

    function cp4() internal returns (StateCheckpoint memory cp) {
        seq4 += 1;
        cp = StateCheckpoint(
            seq4,
            tmsc.authEpoch(),
            POLICY_VERSION,
            0,
            WITNESS_SET_VERSION,
            PBC_CHAIN_ID,
            address(psc),
            block.number,
            keccak256(abi.encode("synthetic-pbc-block", block.number)),
            uint64(block.timestamp) + CHECKPOINT_TTL
        );
    }

    /// Signatures by `pks` over `cp` for kssc4, in the given order (callers sort or deliberately do not).
    function signWith(StateCheckpoint memory cp, uint256[] memory pks) internal view returns (bytes[] memory sigs) {
        bytes32 digest = HMBCHash.stateCheckpointDigest(cp, DBC_CHAIN_ID, address(kssc4));
        sigs = new bytes[](pks.length);
        for (uint256 i = 0; i < pks.length; i++) {
            sigs[i] = sig(pks[i], digest);
        }
    }

    /// Keys of witnesses `idx` sorted by ascending signer address (QuorumLib's required order).
    function sorted(uint256[] memory idx) internal view returns (uint256[] memory pks) {
        pks = new uint256[](idx.length);
        for (uint256 i = 0; i < idx.length; i++) {
            pks[i] = wPk[idx[i]];
        }
        for (uint256 i = 1; i < pks.length; i++) {
            for (uint256 j = i; j > 0 && vm.addr(pks[j]) < vm.addr(pks[j - 1]); j--) {
                (pks[j], pks[j - 1]) = (pks[j - 1], pks[j]);
            }
        }
    }

    function ids(uint256 a, uint256 b) internal pure returns (uint256[] memory xs) {
        xs = new uint256[](2);
        (xs[0], xs[1]) = (a, b);
    }

    function ids(uint256 a, uint256 b, uint256 c) internal pure returns (uint256[] memory xs) {
        xs = new uint256[](3);
        (xs[0], xs[1], xs[2]) = (a, b, c);
    }

    function ids(uint256 a, uint256 b, uint256 c, uint256 d) internal pure returns (uint256[] memory xs) {
        xs = new uint256[](4);
        (xs[0], xs[1], xs[2], xs[3]) = (a, b, c, d);
    }

    function currentSequence() internal view returns (uint64) {
        (, StateCheckpoint memory cur) = kssc4.currentCheckpoint();
        return cur.sequence;
    }

    /// FL-2. Expect: accepted. Any 3 distinct witnesses of 4 suffice (one withholding witness).
    function test_F0Q_ThreeOfFourAccepted() public {
        for (uint256 missing = 0; missing < N; missing++) {
            uint256[] memory three = new uint256[](3);
            uint256 k = 0;
            for (uint256 i = 0; i < N; i++) {
                if (i != missing) three[k++] = i;
            }
            StateCheckpoint memory cp = cp4();
            kssc4.acceptState(cp, signWith(cp, sorted(three)));
            assertEq(currentSequence(), cp.sequence, "3 of 4 accepted");
        }
    }

    /// Control for FL-3. Expect: accepted with all four.
    function test_F0Q_FourOfFourAccepted() public {
        StateCheckpoint memory cp = cp4();
        kssc4.acceptState(cp, signWith(cp, sorted(ids(0, 1, 2, 3))));
        assertEq(currentSequence(), cp.sequence, "4 of 4 accepted");
    }

    /// FL-3. Expect: INSUFFICIENT_QUORUM and no state change (two withholding witnesses).
    function test_F0Q_TwoOfFourInsufficient() public {
        StateCheckpoint memory cp = cp4();
        bytes[] memory s = signWith(cp, sorted(ids(0, 1)));
        expectRejected(ErrorCode.INSUFFICIENT_QUORUM);
        kssc4.acceptState(cp, s);
        assertFalse(kssc4.hasCheckpoint(), "nothing accepted");
    }

    /// FL-4. Expect: DUPLICATE_SIGNER. One witness's signature repeated cannot make up the third vote.
    function test_F0Q_DuplicateSignerRejected() public {
        StateCheckpoint memory cp = cp4();
        uint256[] memory two = sorted(ids(0, 1));
        uint256[] memory pks = new uint256[](3);
        (pks[0], pks[1], pks[2]) = (two[0], two[1], two[1]);
        bytes[] memory s = signWith(cp, pks);
        expectRejected(ErrorCode.DUPLICATE_SIGNER);
        kssc4.acceptState(cp, s);
        assertFalse(kssc4.hasCheckpoint(), "nothing accepted");
    }

    /// FL-5 and L12. Expect: BAD_SIGNATURE. An unknown signer anywhere rejects the whole certificate,
    /// even when three valid witness signatures are also present; the submitter must filter.
    function test_F0Q_UnknownSignerRejectsWholeCertificate() public {
        StateCheckpoint memory cp = cp4();
        uint256[] memory three = sorted(ids(0, 1, 2));
        uint256[] memory pks = new uint256[](4);
        (pks[0], pks[1], pks[2], pks[3]) = (three[0], three[1], three[2], malloryPk);
        bytes[] memory s = signWith(cp, pks);
        expectRejected(ErrorCode.BAD_SIGNATURE);
        kssc4.acceptState(cp, s);
        assertFalse(kssc4.hasCheckpoint(), "valid quorum present but certificate rejected");
    }

    /// QuorumLib ordering rule. Expect: MALFORMED for three distinct witnesses out of order, and
    /// DUPLICATE_SIGNER when the out-of-order signer already appeared earlier.
    function test_F0Q_UnsortedSignaturesRejected() public {
        StateCheckpoint memory cp = cp4();
        uint256[] memory three = sorted(ids(0, 1, 2));
        uint256[] memory rev = new uint256[](3);
        (rev[0], rev[1], rev[2]) = (three[2], three[1], three[0]);
        bytes[] memory s1 = signWith(cp, rev);
        expectRejected(ErrorCode.MALFORMED);
        kssc4.acceptState(cp, s1);

        uint256[] memory dup = new uint256[](3);
        (dup[0], dup[1], dup[2]) = (three[0], three[1], three[0]);
        bytes[] memory s2 = signWith(cp, dup);
        expectRejected(ErrorCode.DUPLICATE_SIGNER);
        kssc4.acceptState(cp, s2);
        assertFalse(kssc4.hasCheckpoint(), "nothing accepted");
    }

    /// FL-6. Expect: STALE_STATE for a checkpoint naming another witness-set version, even with 4 signatures.
    function test_F0Q_OtherWitnessSetVersionRejected() public {
        StateCheckpoint memory cp = cp4();
        cp.witnessSetVersion = WITNESS_SET_VERSION + 1;
        bytes[] memory s = signWith(cp, sorted(ids(0, 1, 2, 3)));
        expectRejected(ErrorCode.STALE_STATE);
        kssc4.acceptState(cp, s);
    }

    /// FL-7. Expect: INSUFFICIENT_QUORUM. One faulty witness alone cannot install a poison checkpoint
    /// under q = 3 (contrast test_F0_PoisonCheckpointSequenceBlocksTheDbc at q = 1); state unchanged.
    function test_F0Q_SingleWitnessCannotPoison() public {
        StateCheckpoint memory honest = cp4();
        kssc4.acceptState(honest, signWith(honest, sorted(ids(0, 1, 2))));
        StateCheckpoint memory poison = cp4();
        poison.sequence = type(uint64).max;
        uint256[] memory one_ = new uint256[](1);
        one_[0] = wPk[3];
        bytes[] memory s = signWith(poison, one_);
        expectRejected(ErrorCode.INSUFFICIENT_QUORUM);
        kssc4.acceptState(poison, s);
        assertEq(currentSequence(), honest.sequence, "honest checkpoint still current");
    }

    /// FL-7 boundary. Expect: accepted. Three signers (one faulty plus two honest witnesses that fail
    /// to validate the field) do install the poison checkpoint: q = 3 moves the trust to honest-witness
    /// field validation (agent 2, B-F1); the ledger itself has no bound.
    function test_F0Q_ThreeSignersCanPoison() public {
        StateCheckpoint memory poison = cp4();
        poison.sequence = type(uint64).max;
        kssc4.acceptState(poison, signWith(poison, sorted(ids(0, 1, 3))));
        StateCheckpoint memory next = cp4();
        bytes[] memory s = signWith(next, sorted(ids(0, 1, 2, 3)));
        expectRejected(ErrorCode.STALE_STATE);
        kssc4.acceptState(next, s);
    }
}

/// Closes README L8's untested field: sourceBlockNumber is monotone and unbounded like sequence, in the
/// E fixture (q = 1 of 1). DecisionVerifier never compares a decision's sourceBlockNumber with the
/// checkpoint, so decisions keep passing until the poisoned checkpoint expires; then the DBC is blocked.
contract F0SourceBlockPoisonRepairedTest is HMBCFixture {
    function profile() internal pure override returns (Profile) {
        return Profile.REPAIRED_E;
    }

    /// P-WIT-5. Expect: accepted; a grant still passes while it is fresh; the honest next checkpoint
    /// rejects STALE_STATE; after expiry every decision rejects STALE_STATE.
    function test_F0_PoisonCheckpointSourceBlockNumberBlocksTheDbc() public {
        publishTrustLists(one(alice));
        registerAlice();
        StateCheckpoint memory poison = checkpointNow();
        poison.sourceBlockNumber = type(uint256).max;
        kssc.acceptState(poison, signCheckpoint(poison, witnessPk));

        (AccessRequest memory r1,, CredentialRecord[] memory recs1) = aliceForwarded(1);
        DecisionCertificate memory c1 = certify(decisionFor(r1, RESULT_ALLOW, recs1, poison), witnessPk);
        acsc.consumeDecision(r1, c1, recs1);

        StateCheckpoint memory next = checkpointNow();
        bytes[] memory s = signCheckpoint(next, witnessPk);
        expectRejected(ErrorCode.STALE_STATE);
        kssc.acceptState(next, s);

        vm.warp(poison.expiresAt);
        (AccessRequest memory r2,, CredentialRecord[] memory recs2) = aliceForwarded(2);
        DecisionCertificate memory c2 = certify(decisionFor(r2, RESULT_ALLOW, recs2, poison), witnessPk);
        expectRejected(ErrorCode.STALE_STATE);
        acsc.consumeDecision(r2, c2, recs2);
    }
}
