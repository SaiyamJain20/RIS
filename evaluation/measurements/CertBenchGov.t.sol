// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;
// MEASUREMENT HARNESS by agent 3 (scratch copy of ledger 85c59f5; not part of the ledger module).
import {GovernanceTest} from "./Governance.t.sol";
import {GovernanceAction, GOV_ADD_AUTHORITY, GOV_REMOVE_AUTHORITY, GOV_SET_CA_ADMINS} from "../src/types/ProtocolTypes.sol";

contract GovBench is GovernanceTest {
    event Measure(string name, uint256 sigs, uint256 gas, uint256 calldataBytes);

    function run(string memory name, GovernanceAction memory a, uint256 n) internal {
        bytes[] memory s = n == 4 ? sortedSigs(witnessPks, govDigest(a)) : quorum(a);
        uint256 cd = abi.encodeCall(gov.execute, (a, s)).length;
        vm.prank(mallory);
        uint256 g = gasleft();
        gov.execute(a, s);
        g -= gasleft();
        emit Measure(name, s.length, g, cd);
    }

    function test_gov_add_3() public { run("execute:AddAuthority", action(GOV_ADD_AUTHORITY, h5, one(h5Admin), 1), 3); }
    function test_gov_add_4() public { run("execute:AddAuthority", action(GOV_ADD_AUTHORITY, h5, one(h5Admin), 1), 4); }
    function test_gov_remove_3() public { run("execute:RemoveAuthority", action(GOV_REMOVE_AUTHORITY, h3, none(), 1), 3); }
    function test_gov_remove_4() public { run("execute:RemoveAuthority", action(GOV_REMOVE_AUTHORITY, h3, none(), 1), 4); }
    function test_gov_set_3() public { run("execute:SetCaAdmins", action(GOV_SET_CA_ADMINS, h1, one(newAdmin), 1), 3); }
    function test_gov_set_4() public { run("execute:SetCaAdmins", action(GOV_SET_CA_ADMINS, h1, one(newAdmin), 1), 4); }
}
