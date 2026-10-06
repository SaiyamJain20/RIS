// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {Vm, VM_ADDRESS} from "./Vm.sol";
import {ErrorCode, Rejected} from "../../src/types/ProtocolTypes.sol";

/// Small assertion base. A failed assertion reverts, which Forge reports as a failing test.
abstract contract TestBase {
    Vm internal constant vm = Vm(VM_ADDRESS);

    function assertTrue(bool condition, string memory what) internal pure {
        if (!condition) revert(string.concat("assertTrue failed: ", what));
    }

    function assertFalse(bool condition, string memory what) internal pure {
        if (condition) revert(string.concat("assertFalse failed: ", what));
    }

    function assertEq(uint256 got, uint256 want, string memory what) internal pure {
        if (got != want) {
            revert(string.concat("assertEq(uint) failed: ", what, " got=", vm.toString(got), " want=", vm.toString(want)));
        }
    }

    function assertEq(bytes32 got, bytes32 want, string memory what) internal pure {
        if (got != want) {
            revert(string.concat("assertEq(bytes32) failed: ", what, " got=", vm.toString(got), " want=", vm.toString(want)));
        }
    }

    function assertEq(address got, address want, string memory what) internal pure {
        if (got != want) {
            revert(string.concat("assertEq(address) failed: ", what, " got=", vm.toString(got), " want=", vm.toString(want)));
        }
    }

    function assertNotEq(bytes32 a, bytes32 b, string memory what) internal pure {
        if (a == b) revert(string.concat("assertNotEq(bytes32) failed: ", what));
    }

    function assertCode(ErrorCode got, ErrorCode want, string memory what) internal pure {
        if (got != want) {
            revert(
                string.concat(
                    "assertCode failed: ", what, " got=", vm.toString(uint256(got)), " want=", vm.toString(uint256(want))
                )
            );
        }
    }

    /// The next call must revert with Rejected(code).
    function expectRejected(ErrorCode code) internal {
        vm.expectRevert(abi.encodeWithSelector(Rejected.selector, code));
    }
}
