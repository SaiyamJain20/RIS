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
    GrantReceipt,
    ACTION_READ,
    mutationsAllowed,
    isRepaired,
    MUT_NO_RECEIPT_BINDING
} from "./types/ProtocolTypes.sol";
import {SigLib, QuorumLib} from "./lib/SigLib.sol";
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

    /// Deployment configuration. The witness set (repaired-e) verifies GrantReceipts (A1-0008).
    struct Config {
        Profile profile;
        uint256 mutations;
        RSC rsc;
        TMSC tmsc;
        LSC lsc;
        address relay;
        uint64 policyVersion;
        uint64 maxRequestTtl;
        uint64 witnessSetVersion;
        address[] witnesses;
        uint256 threshold;
    }

    Profile public immutable profile;
    uint256 public immutable mutations;
    uint256 public immutable pbcChainId;
    RSC public immutable rsc;
    TMSC public immutable tmsc;
    LSC public immutable lsc;
    address public immutable relay;
    uint64 public immutable policyVersion;
    uint64 public immutable maxRequestTtl;
    uint64 public immutable witnessSetVersion;
    uint256 public immutable threshold;
    address[] internal _witnesses;

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
    /// OUTCOME_RECORDED with witness-attested DBC grant evidence (repaired-e).
    event AttestedOutcomeRecorded(
        bytes32 indexed requestDigest, bytes32 indexed grantId, bytes32 outcomeDigest, uint256 dbcBlockNumber, uint256 logId
    );

    /// The PBC chain id is the chain this contract is deployed on.
    constructor(Config memory c) {
        if (c.relay == address(0) || c.maxRequestTtl == 0) revert Rejected(ErrorCode.MALFORMED);
        if (!mutationsAllowed(c.profile, c.mutations)) {
            revert Rejected(ErrorCode.MALFORMED);
        }
        if (isRepaired(c.profile)) {
            if (c.threshold == 0 || c.threshold > c.witnesses.length) revert Rejected(ErrorCode.MALFORMED);
            for (uint256 i = 0; i < c.witnesses.length; i++) {
                if (c.witnesses[i] == address(0)) revert Rejected(ErrorCode.MALFORMED);
                for (uint256 j = 0; j < i; j++) {
                    if (c.witnesses[j] == c.witnesses[i]) revert Rejected(ErrorCode.DUPLICATE_SIGNER);
                }
            }
        }
        profile = c.profile;
        mutations = c.mutations;
        pbcChainId = block.chainid;
        rsc = c.rsc;
        tmsc = c.tmsc;
        lsc = c.lsc;
        relay = c.relay;
        policyVersion = c.policyVersion;
        maxRequestTtl = c.maxRequestTtl;
        witnessSetVersion = c.witnessSetVersion;
        _witnesses = c.witnesses;
        threshold = c.threshold;
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
        if (isRepaired(profile) && r.authEpoch != tmsc.authEpoch()) return ErrorCode.STALE_STATE;
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
        // Repaired-e records outcomes only with DBC grant evidence (reportAttestedOutcome, A1-0008).
        if (isRepaired(profile)) revert Rejected(ErrorCode.WRONG_PROFILE);
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

    /// A1-0008 revision 2 (repaired-e): record an outcome only with a witness-signed GrantReceipt that
    /// matches this PBC's forwarded record and attests an existing allowed DBC grant. The receipt is
    /// evidence of DBC authorization, not of release or delivery; `outcomeDigest` stays opaque.
    /// Late reconciliation after grant expiry is allowed; one outcome per request.
    function reportAttestedOutcome(
        bytes32 requestDigest,
        bytes32 outcomeDigest,
        GrantReceipt calldata receipt,
        bytes[] calldata signatures
    ) external whenSealed returns (uint256 logId) {
        if (!isRepaired(profile)) revert Rejected(ErrorCode.WRONG_PROFILE);
        if (msg.sender != relay) revert Rejected(ErrorCode.UNAUTHORIZED_CALLER);
        RequestRecord storage rec = _requests[requestDigest];
        if (rec.status == RequestStatus.NONE) revert Rejected(ErrorCode.WRONG_SUBJECT);
        if (rec.status == RequestStatus.OUTCOME_RECORDED) revert Rejected(ErrorCode.REPLAY);
        GrantReceipt memory g = receipt;
        ErrorCode code = _checkReceipt(requestDigest, rec, g, signatures);
        if (code != ErrorCode.NONE) revert Rejected(code);
        logId = lsc.outcomeLog(requestDigest, abi.encode(requestDigest, outcomeDigest, g, msg.sender));
        rec.status = RequestStatus.OUTCOME_RECORDED;
        rec.outcomeLogId = logId;
        emit AttestedOutcomeRecorded(requestDigest, g.grantId, outcomeDigest, g.dbcBlockNumber, logId);
    }

    /// A1-0008 steps 4-9 (first failing check wins).
    function _checkReceipt(
        bytes32 requestDigest,
        RequestRecord storage rec,
        GrantReceipt memory g,
        bytes[] calldata signatures
    ) internal view returns (ErrorCode) {
        if (
            mutations & MUT_NO_RECEIPT_BINDING == 0
                && (g.requestDigest != requestDigest || g.gid != rec.gid || g.dataId != rec.dataId)
        ) return ErrorCode.WRONG_SUBJECT;
        if (
            g.dbcChainId != rec.destinationChainId || g.kssc != rec.kssc
                || g.grantId != HMBCHash.grantId(requestDigest, rec.kssc, rec.destinationChainId)
        ) return ErrorCode.WRONG_DESTINATION;
        if (g.keyEpoch != 0) return ErrorCode.WRONG_EPOCH;
        if (g.grantExpiresAt == 0 || g.grantExpiresAt > rec.expiresAt) return ErrorCode.MALFORMED;
        if (g.witnessSetVersion != witnessSetVersion) return ErrorCode.STALE_STATE;
        return QuorumLib.verify(
            HMBCHash.grantReceiptDigest(g, pbcChainId, address(this)), signatures, _witnesses, threshold
        );
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

    function witnesses() external view returns (address[] memory) {
        return _witnesses;
    }
}
