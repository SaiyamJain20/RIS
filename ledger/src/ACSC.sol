// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {
    ErrorCode,
    Rejected,
    Profile,
    HMBCHash,
    AccessRequest,
    DecisionCertificate,
    CredentialRecord,
    StateCheckpoint,
    ForwardedRequest,
    ACTION_READ,
    RESULT_ALLOW,
    mutationsAllowed,
    isRepaired
} from "./types/ProtocolTypes.sol";
import {Bootstrapped} from "./lib/Bootstrapped.sol";
import {DecisionVerifier} from "./DecisionVerifier.sol";
import {KSSC} from "./KSSC.sol";

/// Access Control Smart Contract on the Hospital DBC (HMBC2020 III-E1, Fig. 6, Table 3).
///
/// Paper profiles: policyEnf (Table 3, actuator PSC). PSC lives on another chain, so the PSC
/// actuator is realized as the configured inter-blockchain relay account (IV-A, Fig. 7/8),
/// carrying the Fig. 6 step (4) tuple [GID, verified attributes, data_id]. The paper gives no
/// PBC->DBC message authentication beyond the actuator, so the attributes are taken as verified.
///
/// REPAIRED_E: consumeDecision verifies a witness-signed AccessDecision bound to the user-signed
/// AccessRequest, the accepted checkpoint and the credential records, then calls
/// KSSC.requestData, which consumes (gid, nonce) atomically with the grant.
///
/// Both paths keep Table 3's order: ACSC enforces policy, logs (accessLog), then KSSC.requestData.
contract ACSC is Bootstrapped {
    enum IssuerMode {
        ANY, // literal "*" of Rule 2 / Fig. 5
        DATA_OWNER, // the authority that owns the record (Rule 1 "hospital X")
        SAME_AS_FIRST // same issuer as the clause's first requirement ("temporal bound to long-term")
    }

    struct Requirement {
        bytes32 role;
        uint8 kind; // CREDENTIAL_LONG_TERM or CREDENTIAL_TEMPORAL
        IssuerMode issuerMode;
    }

    struct DataEntry {
        bool exists;
        address owner;
        uint256 policyId;
    }

    Profile public immutable profile;
    uint256 public immutable mutations;
    uint256 public immutable dbcChainId;
    uint256 public immutable sourceChainId;
    address public immutable sourcePsc;
    uint64 public immutable policyVersion;
    uint64 public immutable grantTtl; // paper profiles only: Fig. 6 has no expiry; bounded fill

    KSSC public kssc;
    address public pscRelay;
    Requirement[][][] internal _policies; // policyId -> clauses -> requirements
    mapping(bytes32 => DataEntry) internal _data;
    uint256 public accessLogCount;

    /// Table 3 accessLog: one entry per policy enforcement, allowed or denied.
    event AccessLog(
        uint256 indexed accessLogId,
        bytes32 indexed requestRef,
        address indexed gid,
        bytes32 dataId,
        bool allowed,
        ErrorCode code,
        bytes32 credentialDigest,
        bytes32 grantId,
        address submitter
    );

    constructor(
        Profile profile_,
        uint256 mutations_,
        uint256 dbcChainId_,
        uint256 sourceChainId_,
        address sourcePsc_,
        uint64 policyVersion_,
        uint64 grantTtl_
    ) {
        if (dbcChainId_ != block.chainid) revert Rejected(ErrorCode.WRONG_DESTINATION);
        if (sourcePsc_ == address(0) || grantTtl_ == 0) revert Rejected(ErrorCode.MALFORMED);
        if (!mutationsAllowed(profile_, mutations_)) {
            revert Rejected(ErrorCode.MALFORMED);
        }
        profile = profile_;
        mutations = mutations_;
        dbcChainId = dbcChainId_;
        sourceChainId = sourceChainId_;
        sourcePsc = sourcePsc_;
        policyVersion = policyVersion_;
        grantTtl = grantTtl_;
    }

    function wire(KSSC kssc_, address pscRelay_) external onlyBootstrap {
        kssc = kssc_;
        pscRelay = pscRelay_;
    }

    /// Bootstrap policy (III-C4 agreed domain policy). A policy is an OR of AND-clauses.
    function addPolicy(Requirement[][] calldata clauses) external onlyBootstrap returns (uint256 policyId) {
        if (clauses.length == 0) revert Rejected(ErrorCode.MALFORMED);
        policyId = _policies.length;
        _policies.push();
        for (uint256 i = 0; i < clauses.length; i++) {
            if (clauses[i].length == 0) revert Rejected(ErrorCode.MALFORMED);
            // SAME_AS_FIRST needs an anchor: it cannot be a clause's first requirement (A32).
            if (clauses[i][0].issuerMode == IssuerMode.SAME_AS_FIRST) revert Rejected(ErrorCode.MALFORMED);
            _policies[policyId].push();
            for (uint256 j = 0; j < clauses[i].length; j++) {
                _policies[policyId][i].push(clauses[i][j]);
            }
        }
    }

    function registerData(bytes32 dataId, address owner, uint256 policyId) external onlyBootstrap {
        if (_data[dataId].exists || owner == address(0) || policyId >= _policies.length) {
            revert Rejected(ErrorCode.MALFORMED);
        }
        _data[dataId] = DataEntry(true, owner, policyId);
    }

    function _checkWiring() internal view override {
        if (address(kssc) == address(0)) revert Rejected(ErrorCode.MALFORMED);
        if (!isRepaired(profile) && pscRelay == address(0)) revert Rejected(ErrorCode.MALFORMED);
    }

    // ------------------------------------------------------------------ paper profiles

    /// Table 3 policyEnf. Actuator: PSC, realized as the configured relay account.
    /// A policy denial is logged and returns (false, 0); it does not revert.
    function policyEnf(ForwardedRequest calldata fwd, CredentialRecord[] calldata verifiedAttributes)
        external
        whenSealed
        returns (bool allowed, bytes32 grantId)
    {
        if (isRepaired(profile)) revert Rejected(ErrorCode.WRONG_PROFILE);
        if (msg.sender != pscRelay) revert Rejected(ErrorCode.UNAUTHORIZED_CALLER);
        if (fwd.action != ACTION_READ || fwd.gid == address(0)) revert Rejected(ErrorCode.MALFORMED);
        if (!_data[fwd.dataId].exists) revert Rejected(ErrorCode.MALFORMED);
        CredentialRecord[] memory attrs = verifiedAttributes;
        allowed = evaluate(fwd.dataId, attrs);
        if (allowed) {
            grantId = kssc.requestData(
                KSSC.GrantParams(
                    fwd.pbcRequestId, fwd.dataId, fwd.gid, 0, uint64(block.timestamp) + grantTtl, bytes32(0), false, 0
                )
            );
        }
        _accessLog(
            fwd.pbcRequestId,
            fwd.gid,
            fwd.dataId,
            allowed,
            allowed ? ErrorCode.NONE : ErrorCode.POLICY_DENIED,
            HMBCHash.hashCredentialRecords(attrs),
            grantId
        );
    }

    // ------------------------------------------------------------------ REPAIRED_E

    /// Verifies the decision certificate and policy, then asks KSSC for the grant. Any failed
    /// check reverts with no state change. A valid DENY decision is logged and returns 0.
    /// Replay of an accepted certificate rejects with REPLAY (use KSSC.getGrant to read it).
    function consumeDecision(
        AccessRequest calldata request,
        DecisionCertificate calldata certificate,
        CredentialRecord[] calldata records
    ) external whenSealed returns (bytes32 grantId) {
        if (!isRepaired(profile)) revert Rejected(ErrorCode.WRONG_PROFILE);
        AccessRequest memory r = request;
        DecisionCertificate memory c = certificate;
        CredentialRecord[] memory recs = records;
        (ErrorCode code, bytes32 requestDigest) = DecisionVerifier.verify(_context(), r, c, recs);
        if (code != ErrorCode.NONE) revert Rejected(code);
        if (c.decision.result != RESULT_ALLOW) {
            _accessLog(requestDigest, r.gid, r.dataId, false, ErrorCode.POLICY_DENIED, c.decision.credentialDigest, 0);
            return 0;
        }
        if (!evaluate(r.dataId, recs)) revert Rejected(ErrorCode.POLICY_DENIED);
        uint64 expiresAt = c.decision.expiresAt < r.expiresAt ? c.decision.expiresAt : r.expiresAt;
        grantId = kssc.requestData(
            KSSC.GrantParams(requestDigest, r.dataId, r.gid, r.keyEpoch, expiresAt, r.recipientKeyHash, true, r.nonce)
        );
        _accessLog(requestDigest, r.gid, r.dataId, true, ErrorCode.NONE, c.decision.credentialDigest, grantId);
    }

    function _context() internal view returns (DecisionVerifier.Context memory ctx) {
        (bool has, StateCheckpoint memory cp) = kssc.currentCheckpoint();
        ctx = DecisionVerifier.Context(
            sourceChainId,
            sourcePsc,
            dbcChainId,
            address(kssc),
            policyVersion,
            kssc.witnessSetVersion(),
            kssc.threshold(),
            kssc.witnesses(),
            has,
            cp,
            uint64(block.timestamp),
            mutations
        );
    }

    // ------------------------------------------------------------------ policy

    /// True if some clause of the record's policy is satisfied by the given attributes.
    /// Attribute freshness is not checked here (the paper's ACSC trusts verified attributes);
    /// REPAIRED_E checks record validity in DecisionVerifier before calling this.
    function evaluate(bytes32 dataId, CredentialRecord[] memory attrs) public view returns (bool) {
        DataEntry storage d = _data[dataId];
        if (!d.exists) return false;
        Requirement[][] storage clauses = _policies[d.policyId];
        for (uint256 i = 0; i < clauses.length; i++) {
            if (_clauseSatisfied(clauses[i], attrs, d.owner)) return true;
        }
        return false;
    }

    function _clauseSatisfied(Requirement[] storage reqs, CredentialRecord[] memory attrs, address owner)
        internal
        view
        returns (bool)
    {
        for (uint256 i = 0; i < attrs.length; i++) {
            if (!_matches(reqs[0], attrs[i], owner, address(0))) continue;
            address anchor = attrs[i].issuer;
            bool all = true;
            for (uint256 r = 1; r < reqs.length && all; r++) {
                bool found = false;
                for (uint256 j = 0; j < attrs.length && !found; j++) {
                    found = _matches(reqs[r], attrs[j], owner, anchor);
                }
                all = found;
            }
            if (all) return true;
        }
        return false;
    }

    function _matches(Requirement storage q, CredentialRecord memory a, address owner, address anchor)
        internal
        view
        returns (bool)
    {
        if (a.role != q.role || a.kind != q.kind) return false;
        if (q.issuerMode == IssuerMode.DATA_OWNER) return a.issuer == owner;
        if (q.issuerMode == IssuerMode.SAME_AS_FIRST) return a.issuer == anchor; // anchored (addPolicy)
        return true;
    }

    function _accessLog(
        bytes32 requestRef,
        address gid,
        bytes32 dataId,
        bool allowed,
        ErrorCode code,
        bytes32 credentialDigest,
        bytes32 grantId
    ) internal {
        accessLogCount += 1;
        emit AccessLog(accessLogCount, requestRef, gid, dataId, allowed, code, credentialDigest, grantId, msg.sender);
    }

    // ------------------------------------------------------------------ views

    function dataEntry(bytes32 dataId) external view returns (DataEntry memory) {
        return _data[dataId];
    }

    function policyCount() external view returns (uint256) {
        return _policies.length;
    }

    function policy(uint256 policyId) external view returns (Requirement[][] memory) {
        return _policies[policyId];
    }
}
