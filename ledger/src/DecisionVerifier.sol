// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {
    ErrorCode,
    HMBCHash,
    AccessRequest,
    AccessDecision,
    DecisionCertificate,
    CredentialRecord,
    StateCheckpoint,
    ACTION_READ,
    RESULT_ALLOW,
    RESULT_DENY
} from "./types/ProtocolTypes.sol";
import {QuorumLib} from "./lib/SigLib.sol";

/// REPAIRED_E decision-certificate verification (project extension, not HMBC).
/// Check order is fixed so that a certificate with several defects always yields the same code:
///  1 source binding           WRONG_DESTINATION
///  2 destination binding      WRONG_DESTINATION
///  3 action                   MALFORMED
///  4 request binding          WRONG_SUBJECT  (decision.requestDigest != digest(request))
///  5 witness-set version      STALE_STATE
///  6 quorum signatures        BAD_SIGNATURE | DUPLICATE_SIGNER | INSUFFICIENT_QUORUM | MALFORMED
///  7 decision result value    MALFORMED
///  8 credential binding       WRONG_SUBJECT  (credentialDigest != hash(records))
///  9 request/decision expiry  EXPIRED        (now >= expiresAt rejects)
/// 10 checkpoint present/fresh, same sequence, decision not outliving it   STALE_STATE
/// 11 authEpoch / policyVersion equal to the checkpoint                    STALE_STATE
/// 12 keyEpoch equal to the checkpoint                                     WRONG_EPOCH
/// 13 every verified record still valid at now                             EXPIRED
library DecisionVerifier {
    struct Context {
        uint256 sourceChainId;
        address sourcePsc;
        uint256 dbcChainId;
        address kssc;
        uint64 policyVersion;
        uint64 witnessSetVersion;
        uint256 threshold;
        address[] witnesses;
        bool hasCheckpoint;
        StateCheckpoint checkpoint;
        uint64 now_;
    }

    function verify(
        Context memory ctx,
        AccessRequest memory r,
        DecisionCertificate memory c,
        CredentialRecord[] memory records
    ) internal pure returns (ErrorCode code, bytes32 requestDigest) {
        requestDigest = HMBCHash.accessRequestDigest(r);
        AccessDecision memory d = c.decision;
        if (r.sourceChainId != ctx.sourceChainId || r.psc != ctx.sourcePsc) return (ErrorCode.WRONG_DESTINATION, requestDigest);
        if (r.destinationChainId != ctx.dbcChainId || r.kssc != ctx.kssc) return (ErrorCode.WRONG_DESTINATION, requestDigest);
        if (r.action != ACTION_READ) return (ErrorCode.MALFORMED, requestDigest);
        if (d.requestDigest != requestDigest) return (ErrorCode.WRONG_SUBJECT, requestDigest);
        if (d.witnessSetVersion != ctx.witnessSetVersion) return (ErrorCode.STALE_STATE, requestDigest);
        code = QuorumLib.verify(
            HMBCHash.accessDecisionDigest(d, ctx.dbcChainId, ctx.kssc), c.signatures, ctx.witnesses, ctx.threshold
        );
        if (code != ErrorCode.NONE) return (code, requestDigest);
        if (d.result != RESULT_ALLOW && d.result != RESULT_DENY) return (ErrorCode.MALFORMED, requestDigest);
        if (HMBCHash.hashCredentialRecords(records) != d.credentialDigest) return (ErrorCode.WRONG_SUBJECT, requestDigest);
        if (ctx.now_ >= d.expiresAt || ctx.now_ >= r.expiresAt) return (ErrorCode.EXPIRED, requestDigest);
        return (_checkState(ctx, r, d, records), requestDigest);
    }

    function _checkState(
        Context memory ctx,
        AccessRequest memory r,
        AccessDecision memory d,
        CredentialRecord[] memory records
    ) private pure returns (ErrorCode) {
        StateCheckpoint memory cp = ctx.checkpoint;
        if (!ctx.hasCheckpoint || ctx.now_ >= cp.expiresAt) return ErrorCode.STALE_STATE;
        if (d.stateSequence != cp.sequence || d.expiresAt > cp.expiresAt) return ErrorCode.STALE_STATE;
        if (r.authEpoch != cp.authEpoch) return ErrorCode.STALE_STATE;
        if (r.policyVersion != cp.policyVersion || r.policyVersion != ctx.policyVersion) return ErrorCode.STALE_STATE;
        if (r.keyEpoch != cp.keyEpoch) return ErrorCode.WRONG_EPOCH;
        for (uint256 i = 0; i < records.length; i++) {
            if (ctx.now_ >= records[i].validUntil) return ErrorCode.EXPIRED;
        }
        return ErrorCode.NONE;
    }
}
