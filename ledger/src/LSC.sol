// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {ErrorCode, Rejected, LogDetailMode} from "./types/ProtocolTypes.sol";
import {Bootstrapped} from "./lib/Bootstrapped.sol";

/// Logging Smart Contract on the PBC (HMBC2020 III-D4, Table 2).
/// Actuators (Table 2): requestLog <- PSC, updateLog <- TMSC, registrationLog <- RSC,
/// retrieveLog <- Auditor with majorityConsent (not implemented in E; see below).
/// The outcome log is the III-D3/III-D4 "store the complete transaction details" step; its
/// actuator is PSC, which receives the DBC response (Fig. 6 steps 9-10).
contract LSC is Bootstrapped {
    enum LogKind {
        NONE,
        REGISTRATION,
        TRUST_UPDATE,
        REQUEST,
        OUTCOME
    }

    struct LogEntry {
        LogKind kind;
        bytes32 subject; // gid key, anchor key or requestDigest
        bytes32 detailsHash; // keccak256(details)
        uint64 blockNumber;
        uint64 timestamp;
    }

    LogDetailMode public immutable detailMode;
    address public rsc;
    address public tmsc;
    address public psc;

    LogEntry[] internal _entries; // logId = index + 1; 0 means "not logged"
    mapping(uint256 => bytes) internal _details; // COMPLETE_DETAILS only
    mapping(bytes32 => uint256) public firstRequestLogId;
    mapping(bytes32 => uint256) public outcomeLogId;

    /// `details` is empty in HASH_ONLY mode.
    event LogRecorded(
        uint256 indexed logId, LogKind indexed kind, bytes32 indexed subject, bytes32 detailsHash, bytes details
    );

    constructor(LogDetailMode mode) {
        detailMode = mode;
    }

    function wire(address rsc_, address tmsc_, address psc_) external onlyBootstrap {
        rsc = rsc_;
        tmsc = tmsc_;
        psc = psc_;
    }

    function _checkWiring() internal view override {
        if (rsc == address(0) || tmsc == address(0) || psc == address(0)) revert Rejected(ErrorCode.MALFORMED);
    }

    modifier onlyFrom(address expected) {
        if (msg.sender != expected) revert Rejected(ErrorCode.UNAUTHORIZED_CALLER);
        _;
    }

    /// Table 2: triggered by RSC. Returns the logging verification variable (log id).
    function registrationLog(bytes32 subject, bytes calldata details)
        external
        whenSealed
        onlyFrom(rsc)
        returns (uint256)
    {
        return _append(LogKind.REGISTRATION, subject, details);
    }

    /// Table 2: triggered by TMSC on trust-anchor updates.
    function updateLog(bytes32 subject, bytes calldata details) external whenSealed onlyFrom(tmsc) returns (uint256) {
        return _append(LogKind.TRUST_UPDATE, subject, details);
    }

    /// Table 2: triggered by PSC when a request is made, before user validation.
    /// Every submission is logged, including duplicates and later-denied requests (V-A5).
    function requestLog(bytes32 requestDigest, bytes calldata details)
        external
        whenSealed
        onlyFrom(psc)
        returns (uint256 logId)
    {
        logId = _append(LogKind.REQUEST, requestDigest, details);
        if (firstRequestLogId[requestDigest] == 0) firstRequestLogId[requestDigest] = logId;
    }

    /// Completion log (III-D3 ii, III-D4). Requires a preceding request log; one per request.
    function outcomeLog(bytes32 requestDigest, bytes calldata details)
        external
        whenSealed
        onlyFrom(psc)
        returns (uint256 logId)
    {
        if (firstRequestLogId[requestDigest] == 0) revert Rejected(ErrorCode.WRONG_SUBJECT);
        if (outcomeLogId[requestDigest] != 0) revert Rejected(ErrorCode.REPLAY);
        logId = _append(LogKind.OUTCOME, requestDigest, details);
        outcomeLogId[requestDigest] = logId;
    }

    /// Table 2 retrieveLog needs majorityConsent (a threshold of authorities). Threshold
    /// authorization is phase F. Note: EVM state and events are readable by every node, so
    /// read access control on a transparent ledger cannot provide log confidentiality.
    function retrieveLog(uint256, bytes calldata) external pure returns (bytes memory) {
        revert Rejected(ErrorCode.NOT_IMPLEMENTED_IN_PHASE);
    }

    function logCount() external view returns (uint256) {
        return _entries.length;
    }

    function getLog(uint256 logId) external view returns (LogEntry memory entry, bytes memory details) {
        if (logId == 0 || logId > _entries.length) revert Rejected(ErrorCode.MALFORMED);
        return (_entries[logId - 1], _details[logId]);
    }

    function _append(LogKind kind, bytes32 subject, bytes calldata details) internal returns (uint256 logId) {
        bytes32 detailsHash = keccak256(details);
        _entries.push(LogEntry(kind, subject, detailsHash, uint64(block.number), uint64(block.timestamp)));
        logId = _entries.length;
        if (detailMode == LogDetailMode.COMPLETE_DETAILS) {
            _details[logId] = details;
            emit LogRecorded(logId, kind, subject, detailsHash, details);
        } else {
            emit LogRecorded(logId, kind, subject, detailsHash, "");
        }
    }
}
