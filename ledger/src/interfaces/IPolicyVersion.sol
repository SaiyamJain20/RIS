// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

/// The DBC policy version KSSC pins checkpoints to under REPAIRED_F (A-F1 design 2.2 section 4).
/// ACSC's public `policyVersion` getter implements it.
interface IPolicyVersion {
    function policyVersion() external view returns (uint64);
}
