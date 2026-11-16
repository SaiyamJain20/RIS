// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {Profile} from "../src/types/ProtocolTypes.sol";
import {AuditRepairedTest, AuditRepairedHashOnlyTest} from "./Audit.t.sol";
import {AccessFlowRepairedTest} from "./AccessFlow.t.sol";
import {DecisionBindingRepairedTest} from "./DecisionBinding.t.sol";
import {FreshnessRepairedTest} from "./Freshness.t.sol";
import {OutcomeEvidenceRepairedTest} from "./OutcomeEvidence.t.sol";
import {PolicyRepairedTest} from "./Policy.t.sol";
import {TrustAnchorsRepairedTest} from "./TrustAnchors.t.sol";

/// A-F1 slice 4 (design 2.2 section 7): the repaired-e property suites rerun unchanged under
/// REPAIRED_F (q = 3 of 4, witness-set version 2, Governance wired, policy pin on). Each subclass
/// changes only the profile; every assertion, expected code and message is inherited. A difference
/// from the repaired-e result is a regression to explain, not an expected outcome.

contract AuditRepairedFTest is AuditRepairedTest {
    function profile() internal pure override returns (Profile) {
        return Profile.REPAIRED_F;
    }
}

contract AuditRepairedHashOnlyFTest is AuditRepairedHashOnlyTest {
    function profile() internal pure override returns (Profile) {
        return Profile.REPAIRED_F;
    }
}

contract AccessFlowRepairedFTest is AccessFlowRepairedTest {
    function profile() internal pure override returns (Profile) {
        return Profile.REPAIRED_F;
    }
}

contract DecisionBindingRepairedFTest is DecisionBindingRepairedTest {
    function profile() internal pure override returns (Profile) {
        return Profile.REPAIRED_F;
    }
}

contract FreshnessRepairedFTest is FreshnessRepairedTest {
    function profile() internal pure override returns (Profile) {
        return Profile.REPAIRED_F;
    }
}

contract OutcomeEvidenceRepairedFTest is OutcomeEvidenceRepairedTest {
    function profile() internal pure override returns (Profile) {
        return Profile.REPAIRED_F;
    }
}

contract PolicyRepairedFTest is PolicyRepairedTest {
    function profile() internal pure override returns (Profile) {
        return Profile.REPAIRED_F;
    }
}

contract TrustAnchorsRepairedFTest is TrustAnchorsRepairedTest {
    function profile() internal pure override returns (Profile) {
        return Profile.REPAIRED_F;
    }
}
