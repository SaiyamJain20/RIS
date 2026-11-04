// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {HMBCFixture} from "./utils/Fixture.sol";
import {Profile, ErrorCode, CREDENTIAL_LONG_TERM, CREDENTIAL_TEMPORAL} from "../src/types/ProtocolTypes.sol";
import {ACSC} from "../src/ACSC.sol";

/// Policy encoding agreed in candidate v1 revision 4 (A3-0011 BOUNDARY.md, A32): Requirement tuples
/// (bytes32 role, uint8 kind, uint8 issuerMode) with ANY=0, DATA_OWNER=1, SAME_AS_FIRST=2; OR of
/// AND-clauses; SAME_AS_FIRST is rejected in a clause's first position. Written before the ACSC change.
abstract contract PolicyBase is HMBCFixture {
    /// keccak256(abi.encode(Requirement[][])) of the registered emergency policy, computed
    /// independently with `cast abi-encode "f((bytes32,uint8,uint8)[][])"` + `cast keccak`.
    bytes32 internal constant EMERGENCY_POLICY_DIGEST =
        0x4bd063e1a4c348bf656f983104839fec2594aaee710b4627e9e46368ba1abc3a;

    function test_RegisteredPolicyDigestMatchesBoundaryEncoding() public view {
        ACSC.DataEntry memory e = acsc.dataEntry(DATA_P1);
        assertEq(keccak256(abi.encode(acsc.policy(e.policyId))), EMERGENCY_POLICY_DIGEST, "policyDigest");
        assertEq(e.owner, h2, "record owner");
    }

    function test_SameAsFirstInFirstPositionIsMalformed() public {
        vm.chainId(DBC_CHAIN_ID);
        ACSC fresh = new ACSC(profile(), 0, DBC_CHAIN_ID, PBC_CHAIN_ID, address(psc), POLICY_VERSION, GRANT_TTL);
        ACSC.Requirement[][] memory clauses = new ACSC.Requirement[][](1);
        clauses[0] = new ACSC.Requirement[](2);
        clauses[0][0] = ACSC.Requirement(ROLE_ON_DUTY, CREDENTIAL_TEMPORAL, ACSC.IssuerMode.SAME_AS_FIRST);
        clauses[0][1] = ACSC.Requirement(ROLE_DOCTOR, CREDENTIAL_LONG_TERM, ACSC.IssuerMode.ANY);
        expectRejected(ErrorCode.MALFORMED);
        fresh.addPolicy(clauses);
        assertEq(fresh.policyCount(), 0, "no policy stored");

        // A later clause starting with SAME_AS_FIRST is rejected too (first position of any clause).
        ACSC.Requirement[][] memory two = new ACSC.Requirement[][](2);
        two[0] = new ACSC.Requirement[](1);
        two[0][0] = ACSC.Requirement(ROLE_DOCTOR, CREDENTIAL_LONG_TERM, ACSC.IssuerMode.ANY);
        two[1] = new ACSC.Requirement[](1);
        two[1][0] = ACSC.Requirement(ROLE_ON_DUTY, CREDENTIAL_TEMPORAL, ACSC.IssuerMode.SAME_AS_FIRST);
        expectRejected(ErrorCode.MALFORMED);
        fresh.addPolicy(two);
    }
}

contract PolicyPaperStrictTest is PolicyBase {
    function profile() internal pure override returns (Profile) {
        return Profile.PAPER_STRICT;
    }
}

contract PolicyRepairedTest is PolicyBase {
    function profile() internal pure virtual override returns (Profile) {
        return Profile.REPAIRED_E;
    }
}
