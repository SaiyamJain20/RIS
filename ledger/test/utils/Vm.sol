// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

/// Minimal Forge cheatcode interface (the subset this module uses). Declared locally instead of
/// vendoring forge-std so the ledger has no third-party Solidity dependency or Git submodule.
/// Signatures match Foundry's cheatcode ABI; an unknown cheatcode fails loudly at runtime.
interface Vm {
    struct Log {
        bytes32[] topics;
        bytes data;
        address emitter;
    }

    function warp(uint256 newTimestamp) external;
    function roll(uint256 newHeight) external;
    function chainId(uint256 newChainId) external;
    function prank(address msgSender) external;
    function startPrank(address msgSender) external;
    function stopPrank() external;
    function deal(address account, uint256 newBalance) external;
    function addr(uint256 privateKey) external pure returns (address keyAddr);
    function sign(uint256 privateKey, bytes32 digest) external pure returns (uint8 v, bytes32 r, bytes32 s);
    function expectRevert(bytes calldata revertData) external;
    function expectRevert() external;
    function recordLogs() external;
    function getRecordedLogs() external returns (Log[] memory logs);
    function load(address target, bytes32 slot) external view returns (bytes32 data);

    function toString(address value) external pure returns (string memory);
    function toString(bytes32 value) external pure returns (string memory);
    function toString(uint256 value) external pure returns (string memory);
    function toString(bytes calldata value) external pure returns (string memory);

    function readFile(string calldata path) external view returns (string memory data);
    function writeFile(string calldata path, string calldata data) external;
    function parseBytes(string calldata stringifiedValue) external pure returns (bytes memory parsedValue);
    function serializeString(string calldata objectKey, string calldata valueKey, string calldata value)
        external
        returns (string memory json);
    function serializeJson(string calldata objectKey, string calldata value) external returns (string memory json);
    function writeJson(string calldata json, string calldata path) external;

    function envOr(string calldata name, uint256 defaultValue) external view returns (uint256 value);
    function envOr(string calldata name, string calldata defaultValue) external view returns (string memory value);
    function envOr(string calldata name, string calldata delim, uint256[] calldata defaultValue)
        external
        view
        returns (uint256[] memory value);
    function envOr(string calldata name, string calldata delim, string[] calldata defaultValue)
        external
        view
        returns (string[] memory value);
    function envUint(string calldata name) external view returns (uint256 value);
    function envString(string calldata name) external view returns (string memory value);
    function envAddress(string calldata name) external view returns (address value);
    function startBroadcast(uint256 privateKey) external;
    function stopBroadcast() external;
}

address constant VM_ADDRESS = address(uint160(uint256(keccak256("hevm cheat code"))));
