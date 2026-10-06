// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {
    MUT_NO_DESTINATION_BINDING,
    MUT_NO_STATE_BARRIER,
    MUT_NO_RECORD_FRESHNESS,
    MUT_NO_NONCE,
    MUT_NO_VERSION_MONOTONE
} from "../src/types/ProtocolTypes.sol";
import {DecisionBindingRepairedTest} from "../test/DecisionBinding.t.sol";
import {FreshnessRepairedTest} from "../test/Freshness.t.sol";
import {AccessFlowRepairedTest} from "../test/AccessFlow.t.sol";

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
