// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {ErrorCode, Rejected} from "../types/ProtocolTypes.sol";

/// One-time deployment wiring. The deployer may set cross-contract addresses and fixture
/// configuration until `seal()`; afterwards nobody can change them and every operational
/// entry point requires the sealed state. This stands in for HMBC's collaborative initial
/// configuration (III-C1, III-E). Post-deployment changes are governance (phase F), not E.
abstract contract Bootstrapped {
    address public immutable deployer;
    bool public configured;

    event Sealed(address indexed by);

    constructor() {
        deployer = msg.sender;
    }

    modifier onlyBootstrap() {
        if (msg.sender != deployer || configured) revert Rejected(ErrorCode.UNAUTHORIZED_CALLER);
        _;
    }

    /// Operational calls before sealing fail with NOT_COMMITTED (configuration not committed).
    modifier whenSealed() {
        if (!configured) revert Rejected(ErrorCode.NOT_COMMITTED);
        _;
    }

    function seal() external onlyBootstrap {
        _checkWiring();
        configured = true;
        emit Sealed(msg.sender);
    }

    /// Each contract reverts here if a required address is still unset.
    function _checkWiring() internal view virtual;
}
