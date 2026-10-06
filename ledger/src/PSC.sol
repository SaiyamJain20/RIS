// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {
    ErrorCode,
    Rejected,
    Profile,
    HMBCHash,
    AccessRequest,
    CredentialBundle,
    CredentialRecord,
    ACTION_READ
} from "./types/ProtocolTypes.sol";
import {SigLib} from "./lib/SigLib.sol";
import {Bootstrapped} from "./lib/Bootstrapped.sol";
import {LSC} from "./LSC.sol";
import {TMSC} from "./TMSC.sol";
import {RSC} from "./RSC.sol";

/// Proxy Smart Contract on the PBC (HMBC2020 III-D3, Fig. 6, Table 2 requestAccess/validateUser).
///
/// requestAccess follows Table 2's order: requestLog FIRST, then getUserValidation, then forward.
/// (III-D3 prose lists credential verification before logging; Table 2, Fig. 6 and V-A5
/// "any access request (successful or not) ... will be logged" put the log first.)
/// A denied request therefore does not revert: the request log and the denial persist, and no
/// forwardable request record is created.
///
/// "Forwarding to the DBC" (Table 2) is the AccessForwarded event, which the off-chain
/// inter-blockchain relay (IV-A, Fig. 7/8) carries to the DBC. The relay is also the outcome
/// reporter: it brings the DBC response back to PSC, which logs it in LSC (III-D3 ii).
contract PSC is Bootstrapped {
    enum RequestStatus {
        NONE,
        FORWARDED,
        OUTCOME_RECORDED
    }

    struct RequestRecord {
        RequestStatus status;
        address gid;
        bytes32 dataId;
        uint256 destinationChainId;
        address kssc;
        bytes32 credentialDigest;
        uint64 decidedAt;
        uint64 expiresAt;
        uint256 requestLogId;
        uint256 outcomeLogId;
    }

    Profile public immutable profile;
    uint256 public immutable pbcChainId;
    RSC public immutable rsc;
    TMSC public immutable tmsc;
    LSC public immutable lsc;
    address public immutable relay;
    uint64 public immutable policyVersion;
    uint64 public immutable maxRequestTtl;

    mapping(uint256 => address) public ksscForChain;
    uint256 public destinationCount;
    mapping(bytes32 => RequestRecord) internal _requests;
    mapping(bytes32 => uint256) public denialCount;

    /// PBC_DECIDED (allow): everything the relay/witness needs to act on the DBC.
    event AccessForwarded(
        bytes32 indexed requestDigest,
        address indexed gid,
        bytes32 indexed dataId,
        uint256 destinationChainId,
        address kssc,
        bytes32 credentialDigest,
        CredentialRecord[] verifiedAttributes,
        uint64 expiresAt,
        uint256 requestLogId
    );
    /// PBC_DECIDED (deny). `claimedGid` is unauthenticated when code is BAD_SIGNATURE.
    event AccessDenied(bytes32 indexed requestDigest, address indexed claimedGid, ErrorCode code, uint256 requestLogId);
    event OutcomeRecorded(bytes32 indexed requestDigest, bytes32 indexed grantId, bytes32 outcomeDigest, uint256 logId);

    constructor(
        Profile profile_,
        uint256 pbcChainId_,
        RSC rsc_,
        TMSC tmsc_,
        LSC lsc_,
        address relay_,
        uint64 policyVersion_,
        uint64 maxRequestTtl_
    ) {
        if (pbcChainId_ != block.chainid) revert Rejected(ErrorCode.WRONG_DESTINATION);
        if (relay_ == address(0) || maxRequestTtl_ == 0) revert Rejected(ErrorCode.MALFORMED);
        profile = profile_;
        pbcChainId = pbcChainId_;
        rsc = rsc_;
        tmsc = tmsc_;
        lsc = lsc_;
        relay = relay_;
        policyVersion = policyVersion_;
        maxRequestTtl = maxRequestTtl_;
    }

    /// Registers the KSSC of a Domain Blockchain (one Hospital DBC in this study).
    function configureDestination(uint256 destinationChainId, address kssc) external onlyBootstrap {
        if (kssc == address(0) || ksscForChain[destinationChainId] != address(0)) revert Rejected(ErrorCode.MALFORMED);
        ksscForChain[destinationChainId] = kssc;
        destinationCount += 1;
    }

    function _checkWiring() internal view override {
        if (destinationCount == 0) revert Rejected(ErrorCode.MALFORMED);
    }

    // ------------------------------------------------------------------ requestAccess

    /// Table 2 requestAccess. Actuator: User, authenticated by the EIP-712 AccessRequest signature
    /// (the user API may submit it). Returns the request digest and the PBC decision code.
    function requestAccess(AccessRequest calldata req, bytes calldata userSignature, CredentialBundle calldata bundle)
        external
        whenSealed
        returns (bytes32 requestDigest, ErrorCode code)
    {
        AccessRequest memory r = req;
        requestDigest = HMBCHash.accessRequestDigest(r);
        uint256 logId = lsc.requestLog(requestDigest, _requestDetails(r, msg.sender));

        CredentialRecord[] memory records;
        code = _precheck(r, requestDigest, userSignature);
        if (code == ErrorCode.NONE) (code, records) = tmsc.getUserValidation(r.gid, bundle);
        if (code != ErrorCode.NONE) {
            denialCount[requestDigest] += 1;
            emit AccessDenied(requestDigest, r.gid, code, logId);
            return (requestDigest, code);
        }

        bytes32 credentialDigest = HMBCHash.hashCredentialRecords(records);
        _requests[requestDigest] = RequestRecord(
            RequestStatus.FORWARDED,
            r.gid,
            r.dataId,
            r.destinationChainId,
            r.kssc,
            credentialDigest,
            uint64(block.timestamp),
            r.expiresAt,
            logId,
            0
        );
        emit AccessForwarded(
            requestDigest, r.gid, r.dataId, r.destinationChainId, r.kssc, credentialDigest, records, r.expiresAt, logId
        );
    }

    /// Checks before credential validation. Order fixes which code wins when several fail.
    function _precheck(AccessRequest memory r, bytes32 requestDigest, bytes calldata userSignature)
        internal
        view
        returns (ErrorCode)
    {
        if (r.sourceChainId != pbcChainId || r.psc != address(this)) return ErrorCode.WRONG_DESTINATION;
        if (r.kssc == address(0) || ksscForChain[r.destinationChainId] != r.kssc) return ErrorCode.WRONG_DESTINATION;
        if (r.action != ACTION_READ) return ErrorCode.MALFORMED;
        if (!SigLib.isValid(requestDigest, userSignature, r.gid)) return ErrorCode.BAD_SIGNATURE;
        if (block.timestamp >= r.expiresAt) return ErrorCode.EXPIRED;
        if (r.expiresAt > block.timestamp + maxRequestTtl) return ErrorCode.MALFORMED;
        if (!rsc.isRegistered(r.gid)) return ErrorCode.NOT_REGISTERED;
        if (rsc.recipientKeyHash(r.gid) != r.recipientKeyHash) return ErrorCode.WRONG_SUBJECT;
        if (_requests[requestDigest].status != RequestStatus.NONE) return ErrorCode.REPLAY;
        if (r.keyEpoch != 0) return ErrorCode.WRONG_EPOCH;
        if (r.policyVersion != policyVersion) return ErrorCode.STALE_STATE;
        if (profile == Profile.REPAIRED_E && r.authEpoch != tmsc.authEpoch()) return ErrorCode.STALE_STATE;
        return ErrorCode.NONE;
    }

    function _requestDetails(AccessRequest memory r, address submitter) internal pure returns (bytes memory) {
        return abi.encode(r.gid, r.dataId, r.action, r.destinationChainId, r.kssc, r.nonce, r.expiresAt, submitter);
    }

    // ------------------------------------------------------------------ response / outcome

    /// III-D3 (ii): the DBC response comes back through the relay; PSC logs it via LSC.
    /// Actuator: the configured relay (inter-blockchain API). One outcome per forwarded request.
    function reportOutcome(bytes32 requestDigest, bytes32 grantId, bytes32 outcomeDigest)
        external
        whenSealed
        returns (uint256 logId)
    {
        if (msg.sender != relay) revert Rejected(ErrorCode.UNAUTHORIZED_CALLER);
        RequestRecord storage rec = _requests[requestDigest];
        if (rec.status == RequestStatus.NONE) revert Rejected(ErrorCode.WRONG_SUBJECT);
        if (rec.status == RequestStatus.OUTCOME_RECORDED) revert Rejected(ErrorCode.REPLAY);
        if (grantId != HMBCHash.grantId(requestDigest, rec.kssc, rec.destinationChainId)) {
            revert Rejected(ErrorCode.WRONG_DESTINATION);
        }
        logId = lsc.outcomeLog(requestDigest, abi.encode(requestDigest, grantId, outcomeDigest, msg.sender));
        rec.status = RequestStatus.OUTCOME_RECORDED;
        rec.outcomeLogId = logId;
        emit OutcomeRecorded(requestDigest, grantId, outcomeDigest, logId);
    }

    // ------------------------------------------------------------------ other Table 2 rows

    /// Table 2 validateUser: actuator User (msg.sender is the GID); triggers getUserValidation.
    function validateUser(CredentialBundle calldata bundle)
        external
        view
        whenSealed
        returns (ErrorCode code, CredentialRecord[] memory records)
    {
        return tmsc.getUserValidation(msg.sender, bundle);
    }

    /// Table 2 majorityConsent (signed challenges from authorities): phase-F governance.
    function majorityConsent(bytes calldata) external pure returns (bool) {
        revert Rejected(ErrorCode.NOT_IMPLEMENTED_IN_PHASE);
    }

    function getRequest(bytes32 requestDigest) external view returns (RequestRecord memory) {
        return _requests[requestDigest];
    }
}
