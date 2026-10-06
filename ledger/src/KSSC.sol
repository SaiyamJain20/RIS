// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {ErrorCode, Rejected, Profile, HMBCHash, StateCheckpoint} from "./types/ProtocolTypes.sol";
import {QuorumLib} from "./lib/SigLib.sol";
import {Bootstrapped} from "./lib/Bootstrapped.sol";

/// Key Store Smart Contract on the Hospital DBC (HMBC2020 III-E2, Fig. 5, Table 3 requestData).
///
/// Realization (SPEC section 3): HMBC stores temporal ABE keys "in the KSSC" and relies on
/// isolation (V-A4). EVM storage is not secret, so this contract holds only authorization
/// state. An off-chain key worker holds the temporal keys and performs partial decryption
/// for a committed grant. That is a deliberate change from the paper's assumed isolated
/// in-contract execution. It is not a claim about HMBC.
///
/// requestData (Table 3, actuator ACSC) creates a grant = permission to release a partial
/// decryption (DBC_AUTHORIZED), not evidence of delivery. GrantIssued is the Table 3 keystoreLog
/// for the authorized partial-decryption request; release intent/sent states belong to the worker.
///
/// acceptState / witness set are the REPAIRED_E checkpoint barrier. In E: q = 1 of 1 witness.
contract KSSC is Bootstrapped {
    struct Grant {
        bool exists;
        bool allowed;
        bytes32 requestDigest;
        bytes32 dataId;
        address gid;
        uint64 keyEpoch;
        uint64 expiresAt;
        bytes32 recipientKeyHash;
        uint64 issuedAt;
    }

    struct GrantParams {
        bytes32 requestDigest; // PBC request digest (repaired) or relay request reference (paper)
        bytes32 dataId;
        address gid;
        uint64 keyEpoch;
        uint64 expiresAt;
        bytes32 recipientKeyHash; // zero in paper profiles: Fig. 6 tuple carries no recipient key
        bool consumeNonce;
        uint256 nonce;
    }

    Profile public immutable profile;
    uint256 public immutable dbcChainId;
    uint256 public immutable sourceChainId;
    address public immutable sourcePsc;
    uint64 public immutable maxCheckpointTtl;
    uint64 public immutable witnessSetVersion;
    uint256 public immutable threshold;
    address[] internal _witnesses;

    address public acsc;
    bool public hasCheckpoint;
    StateCheckpoint internal _checkpoint;
    mapping(bytes32 => Grant) internal _grants;
    mapping(address => mapping(uint256 => bool)) public nonceConsumed;

    event StateAccepted(
        uint64 indexed sequence,
        uint64 authEpoch,
        uint64 policyVersion,
        uint64 keyEpoch,
        uint64 witnessSetVersion,
        uint256 sourceBlockNumber,
        bytes32 sourceBlockHash,
        uint64 expiresAt
    );
    /// DBC_AUTHORIZED.
    event GrantIssued(
        bytes32 indexed grantId,
        bytes32 indexed requestDigest,
        address indexed gid,
        bytes32 dataId,
        uint64 keyEpoch,
        uint64 expiresAt,
        bytes32 recipientKeyHash,
        bool nonceConsumed,
        uint256 nonce
    );

    constructor(
        Profile profile_,
        uint256 dbcChainId_,
        uint256 sourceChainId_,
        address sourcePsc_,
        uint64 witnessSetVersion_,
        address[] memory witnesses_,
        uint256 threshold_,
        uint64 maxCheckpointTtl_
    ) {
        if (dbcChainId_ != block.chainid) revert Rejected(ErrorCode.WRONG_DESTINATION);
        if (sourcePsc_ == address(0) || sourceChainId_ == dbcChainId_) revert Rejected(ErrorCode.MALFORMED);
        if (profile_ == Profile.REPAIRED_E) {
            if (threshold_ == 0 || threshold_ > witnesses_.length || maxCheckpointTtl_ == 0) {
                revert Rejected(ErrorCode.MALFORMED);
            }
            for (uint256 i = 0; i < witnesses_.length; i++) {
                if (witnesses_[i] == address(0)) revert Rejected(ErrorCode.MALFORMED);
                for (uint256 j = 0; j < i; j++) {
                    if (witnesses_[j] == witnesses_[i]) revert Rejected(ErrorCode.DUPLICATE_SIGNER);
                }
            }
        }
        profile = profile_;
        dbcChainId = dbcChainId_;
        sourceChainId = sourceChainId_;
        sourcePsc = sourcePsc_;
        witnessSetVersion = witnessSetVersion_;
        _witnesses = witnesses_;
        threshold = threshold_;
        maxCheckpointTtl = maxCheckpointTtl_;
    }

    function wire(address acsc_) external onlyBootstrap {
        acsc = acsc_;
    }

    function _checkWiring() internal view override {
        if (acsc == address(0)) revert Rejected(ErrorCode.MALFORMED);
    }

    // ------------------------------------------------------------------ checkpoints (REPAIRED_E)

    /// Accepts a witness-signed view of PBC state. Revocation takes effect for new grants
    /// when the checkpoint containing it is accepted here (interfaces v0).
    function acceptState(StateCheckpoint calldata cp, bytes[] calldata signatures) external whenSealed {
        if (profile != Profile.REPAIRED_E) revert Rejected(ErrorCode.WRONG_PROFILE);
        StateCheckpoint memory c = cp;
        if (c.sourceChainId != sourceChainId || c.psc != sourcePsc) revert Rejected(ErrorCode.WRONG_DESTINATION);
        if (c.witnessSetVersion != witnessSetVersion) revert Rejected(ErrorCode.STALE_STATE);
        ErrorCode q = QuorumLib.verify(
            HMBCHash.stateCheckpointDigest(c, dbcChainId, address(this)), signatures, _witnesses, threshold
        );
        if (q != ErrorCode.NONE) revert Rejected(q);
        if (block.timestamp >= c.expiresAt) revert Rejected(ErrorCode.EXPIRED);
        if (c.expiresAt > block.timestamp + maxCheckpointTtl) revert Rejected(ErrorCode.MALFORMED);
        if (c.keyEpoch != 0) revert Rejected(ErrorCode.WRONG_EPOCH);
        if (hasCheckpoint) {
            StateCheckpoint storage cur = _checkpoint;
            if (c.sequence <= cur.sequence) revert Rejected(ErrorCode.STALE_STATE);
            if (
                c.authEpoch < cur.authEpoch || c.policyVersion < cur.policyVersion || c.keyEpoch < cur.keyEpoch
                    || c.sourceBlockNumber < cur.sourceBlockNumber
            ) revert Rejected(ErrorCode.STALE_STATE);
        }
        _checkpoint = c;
        hasCheckpoint = true;
        emit StateAccepted(
            c.sequence,
            c.authEpoch,
            c.policyVersion,
            c.keyEpoch,
            c.witnessSetVersion,
            c.sourceBlockNumber,
            c.sourceBlockHash,
            c.expiresAt
        );
    }

    // ------------------------------------------------------------------ requestData

    /// Table 3 requestData. Actuator: ACSC only. Creates the grant atomically with the nonce
    /// consumption (REPAIRED_E); a duplicate grant or consumed nonce rejects with REPLAY.
    function requestData(GrantParams calldata p) external whenSealed returns (bytes32 grantId) {
        if (msg.sender != acsc) revert Rejected(ErrorCode.UNAUTHORIZED_CALLER);
        grantId = HMBCHash.grantId(p.requestDigest, address(this), dbcChainId);
        if (_grants[grantId].exists) revert Rejected(ErrorCode.REPLAY);
        if (p.consumeNonce) {
            if (nonceConsumed[p.gid][p.nonce]) revert Rejected(ErrorCode.REPLAY);
            nonceConsumed[p.gid][p.nonce] = true;
        }
        _grants[grantId] = Grant(
            true,
            true,
            p.requestDigest,
            p.dataId,
            p.gid,
            p.keyEpoch,
            p.expiresAt,
            p.recipientKeyHash,
            uint64(block.timestamp)
        );
        emit GrantIssued(
            grantId, p.requestDigest, p.gid, p.dataId, p.keyEpoch, p.expiresAt, p.recipientKeyHash, p.consumeNonce, p.nonce
        );
    }

    // ------------------------------------------------------------------ views

    /// interfaces v0: getGrant(grantId) -> (requestDigest, dataId, gid, keyEpoch, expiresAt, allowed).
    /// A missing grant returns zeros and allowed = false.
    function getGrant(bytes32 grantId)
        external
        view
        returns (bytes32 requestDigest, bytes32 dataId, address gid, uint64 keyEpoch, uint64 expiresAt, bool allowed)
    {
        Grant storage g = _grants[grantId];
        return (g.requestDigest, g.dataId, g.gid, g.keyEpoch, g.expiresAt, g.allowed);
    }

    function grantDetails(bytes32 grantId) external view returns (Grant memory) {
        return _grants[grantId];
    }

    function currentCheckpoint() external view returns (bool exists, StateCheckpoint memory checkpoint) {
        return (hasCheckpoint, _checkpoint);
    }

    function witnesses() external view returns (address[] memory) {
        return _witnesses;
    }
}
