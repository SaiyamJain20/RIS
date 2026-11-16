// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {CREDENTIAL_LONG_TERM, CREDENTIAL_TEMPORAL} from "../src/types/ProtocolTypes.sol";
import {ACSC} from "../src/ACSC.sol";

/// Synthetic E fixture shared by tests, vector export and local deployment.
/// Every key is TEST-ONLY: privateKey = keccak256("hmbc-e0-synthetic-key:" || label).
library FixtureConfig {
    uint256 internal constant PBC_CHAIN_ID = 18545;
    uint256 internal constant DBC_CHAIN_ID = 28545;
    uint64 internal constant POLICY_VERSION = 1;
    uint64 internal constant REQUEST_TTL = 30; // interfaces v0: request/decision <= 30 s
    uint64 internal constant CHECKPOINT_TTL = 60; // interfaces v0: checkpoint <= 60 s
    uint64 internal constant GRANT_TTL = 30; // paper-profile grant bound (project fill)
    uint64 internal constant WITNESS_SET_VERSION = 1;

    // REPAIRED_F (A-F1, interfaces/v2): four witnesses `witness-1..4`, q = 3 (q = 2 in mutant-f-q2),
    // witness-set version 2, and the governance bounds of `fixture.governance`.
    uint64 internal constant F_WITNESS_SET_VERSION = 2;
    uint256 internal constant F_WITNESS_COUNT = 4;
    uint256 internal constant F_THRESHOLD = 3;
    uint64 internal constant GOVERNANCE_MAX_TTL = 120;

    function witnessLabel(uint256 index) internal pure returns (string memory) {
        return string.concat("witness-", string(abi.encodePacked(bytes1(uint8(49 + index)))));
    }

    bytes32 internal constant ROLE_DOCTOR = keccak256("HMBC.role.Doctor");
    bytes32 internal constant ROLE_ON_DUTY = keccak256("HMBC.role.OnDuty");
    bytes32 internal constant ROLE_RESEARCHER = keccak256("HMBC.role.Researcher");
    bytes32 internal constant DATA_P1 = keccak256("HMBC.data.P1.MHR"); // owned by H2

    function key(string memory label) internal pure returns (uint256) {
        return uint256(keccak256(abi.encodePacked("hmbc-e0-synthetic-key:", label)));
    }

    /// Fig. 5 / Rule 2, conservative reading of III-C4: OnDuty must be issued by the same authority
    /// as the Doctor role. The literal "*"/"*" reading would use IssuerMode.ANY for both.
    function emergencyPolicy() internal pure returns (ACSC.Requirement[][] memory clauses) {
        clauses = new ACSC.Requirement[][](1);
        clauses[0] = new ACSC.Requirement[](2);
        clauses[0][0] = ACSC.Requirement(ROLE_DOCTOR, CREDENTIAL_LONG_TERM, ACSC.IssuerMode.ANY);
        clauses[0][1] = ACSC.Requirement(ROLE_ON_DUTY, CREDENTIAL_TEMPORAL, ACSC.IssuerMode.SAME_AS_FIRST);
    }
}
