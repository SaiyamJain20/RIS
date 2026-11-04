// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {
    MUT_NO_DESTINATION_BINDING,
    MUT_NO_STATE_BARRIER,
    MUT_NO_RECORD_FRESHNESS,
    MUT_NO_NONCE,
    MUT_NO_VERSION_MONOTONE,
    MUT_NO_RECEIPT_BINDING,
    MUT_NO_GOV_ACTION_BINDING,
    MUT_NO_GOV_NONCE,
    MUT_NO_POLICY_PIN,
    ErrorCode,
    HMBCHash,
    GovernanceAction,
    AccessRequest,
    CredentialRecord,
    StateCheckpoint,
    DecisionCertificate,
    GOV_SET_CA_ADMINS,
    GOV_REMOVE_AUTHORITY,
    RESULT_ALLOW
} from "../src/types/ProtocolTypes.sol";
import {DecisionBindingRepairedTest} from "../test/DecisionBinding.t.sol";
import {FreshnessRepairedTest} from "../test/Freshness.t.sol";
import {AccessFlowRepairedTest} from "../test/AccessFlow.t.sol";
import {OutcomeEvidenceRepairedTest} from "../test/OutcomeEvidence.t.sol";
import {GovernanceTest} from "../test/Governance.t.sol";
import {QuorumTest} from "../test/Quorum.t.sol";
import {Vm} from "../test/utils/Vm.sol";

/// mutant-* deployments: REPAIRED_E with exactly one check removed. Each suite re-runs the repaired
/// property tests against the mutant; the named property tests are EXPECTED TO FAIL (that is the
/// detection). Expectations are in tools/check_mutants.py. Run:
///   FOUNDRY_PROFILE=mutants forge test --root ledger      (or python3 -I ledger/tools/check_mutants.py)

contract MutantNoDestinationBindingTest is DecisionBindingRepairedTest {
    function mutations() internal pure override returns (uint256) {
        return MUT_NO_DESTINATION_BINDING;
    }
}

contract MutantNoStateBarrierTest is FreshnessRepairedTest {
    function mutations() internal pure override returns (uint256) {
        return MUT_NO_STATE_BARRIER;
    }
}

contract MutantNoRecordFreshnessTest is FreshnessRepairedTest {
    function mutations() internal pure override returns (uint256) {
        return MUT_NO_RECORD_FRESHNESS;
    }
}

contract MutantNoNonceDecisionBindingTest is DecisionBindingRepairedTest {
    function mutations() internal pure override returns (uint256) {
        return MUT_NO_NONCE;
    }
}

contract MutantNoNonceAccessFlowTest is AccessFlowRepairedTest {
    function mutations() internal pure override returns (uint256) {
        return MUT_NO_NONCE;
    }
}

contract MutantNoVersionMonotoneTest is FreshnessRepairedTest {
    function mutations() internal pure override returns (uint256) {
        return MUT_NO_VERSION_MONOTONE;
    }
}

contract MutantNoReceiptBindingTest is OutcomeEvidenceRepairedTest {
    function mutations() internal pure override returns (uint256) {
        return MUT_NO_RECEIPT_BINDING;
    }
}

// ------------------------------------------------------------------ A-F1 F mutants (design 2.2 section 6)
// REPAIRED_F with exactly one check removed (bits 6-8), plus the mutant-f-q2 configuration. The
// inherited property tests listed in tools/check_mutants.py are EXPECTED TO FAIL; each suite also
// carries one test that shows the mutant's effect directly and is expected to PASS.

contract MutantNoGovActionBindingTest is GovernanceTest {
    function mutations() internal pure override returns (uint256) {
        return MUT_NO_GOV_ACTION_BINDING;
    }

    /// FL-10 bit 6: a certificate for SET_CA_ADMINS(H1, []) executes as REMOVE_AUTHORITY(H1, []).
    function test_MutantF_Bit6SetCertificateExecutesAsRemove() public {
        GovernanceAction memory set = action(GOV_SET_CA_ADMINS, h1, none(), 1);
        bytes[] memory s = quorum(set);
        GovernanceAction memory asRemove =
            GovernanceAction(GOV_REMOVE_AUTHORITY, set.root, set.admins, set.nonce, set.witnessSetVersion, set.expiresAt);
        uint64 epoch = tmsc.authEpoch();
        assertTrue(tmsc.isAuthority(h1), "before: H1 is an authority");
        execute(asRemove, s);
        assertFalse(tmsc.isAuthority(h1), "after: H1 removed by a SET certificate");
        assertTrue(tmsc.removedAuthority(h1), "after: H1 tombstoned");
        assertEq(tmsc.authEpoch(), epoch + 1, "after: authEpoch +1");
        assertEq(gov.governanceNonce(), 1, "after: nonce 1");
    }
}

contract MutantNoGovNonceTest is GovernanceTest {
    function mutations() internal pure override returns (uint256) {
        return MUT_NO_GOV_NONCE;
    }

    /// FL-10 bit 7: replaying an executed SET_CA_ADMINS certificate repeats every effect.
    function test_MutantF_Bit7ReplayRepeatsTheEffects() public {
        GovernanceAction memory a = action(GOV_SET_CA_ADMINS, h1, one(newAdmin), 1);
        bytes[] memory s = quorum(a);
        execute(a, s);
        uint64 epoch = tmsc.authEpoch();
        uint256 logs = lsc.logCount();
        vm.recordLogs();
        execute(a, s);
        Vm.Log[] memory rec = vm.getRecordedLogs();
        assertEq(tmsc.authEpoch(), epoch + 1, "replay advanced authEpoch again");
        assertEq(lsc.logCount(), logs + 1, "replay wrote a second LSC entry");
        assertEq(countTopic(rec, address(tmsc), SET_TOPIC), 1, "replay emitted a second CaAdminsSet");
        assertEq(gov.governanceNonce(), 0, "the nonce never advanced");
    }
}

contract MutantNoPolicyPinTest is QuorumTest {
    function mutations() internal pure override returns (uint256) {
        return MUT_NO_POLICY_PIN;
    }

    /// P-WIT-4 under bit 8: a q-signed checkpoint with another policy version is accepted and then
    /// blocks the DBC: decisions on it fail, and the honest version can no longer be checkpointed.
    function test_MutantF_Bit8ForeignPolicyCheckpointBlocksTheDbc() public {
        publishTrustLists(one(alice));
        registerAlice();
        (AccessRequest memory r,, CredentialRecord[] memory recs) = aliceForwarded(1);
        StateCheckpoint memory poison = checkpointNow();
        poison.policyVersion = POLICY_VERSION + 1;
        kssc.acceptState(poison, sortedSigs(pks(0, 1, 2), cpDigest(poison)));
        DecisionCertificate memory c = certify(decisionFor(r, RESULT_ALLOW, recs, poison), witnessPk);
        vm.prank(relay);
        expectRejected(ErrorCode.STALE_STATE);
        acsc.consumeDecision(r, c, recs);
        StateCheckpoint memory honest = checkpointNow();
        bytes[] memory hs = sortedSigs(pks(0, 1, 2), cpDigest(honest));
        expectRejected(ErrorCode.STALE_STATE);
        kssc.acceptState(honest, hs);
    }
}

contract MutantFQ2QuorumTest is QuorumTest {
    function threshold() internal pure override returns (uint256) {
        return 2;
    }

    /// F-18: two witnesses suffice on every signed path of a q2 deployment.
    function test_MutantF_Q2TwoWitnessesSufficeAtKssc() public {
        StateCheckpoint memory cp = checkpointNow();
        kssc.acceptState(cp, sortedSigs(pks2(2, 3), cpDigest(cp)));
        assertTrue(kssc.hasCheckpoint(), "two signatures accepted");
        assertEq(kssc.threshold(), 2, "KSSC threshold 2");
        assertEq(psc.threshold(), 2, "PSC threshold 2");
    }
}

contract MutantFQ2GovernanceTest is GovernanceTest {
    function threshold() internal pure override returns (uint256) {
        return 2;
    }

    function test_MutantF_Q2TwoWitnessesExecuteGovernance() public {
        GovernanceAction memory a = action(GOV_SET_CA_ADMINS, h1, none(), 1);
        uint256[] memory two = new uint256[](2);
        (two[0], two[1]) = (witnessPks[1], witnessPks[3]);
        execute(a, sortedSigs(two, govDigest(a)));
        assertEq(gov.governanceNonce(), 1, "two signatures executed");
        assertEq(gov.threshold(), 2, "Governance threshold 2");
    }
}
