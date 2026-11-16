// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {
    ErrorCode,
    Rejected,
    HMBCHash,
    GovernanceAction,
    GOV_ADD_AUTHORITY,
    GOV_REMOVE_AUTHORITY,
    GOV_SET_CA_ADMINS,
    GOV_MAX_ADMINS,
    MUT_NO_GOV_ACTION_BINDING,
    MUT_NO_GOV_NONCE,
    MUT_ALL
} from "./types/ProtocolTypes.sol";
import {QuorumLib} from "./lib/SigLib.sol";
import {TMSC} from "./TMSC.sol";

/// Quorum governance of the PBC authority set (A-F1 design 2.2 section 2; REPAIRED_F only).
///
/// Project extension, not HMBC: the paper leaves addCA/removeCA to an unspecified majorityConsent
/// (Table 2). Here the witness set signs a typed EIP-712 GovernanceAction and any account may
/// submit it with q signatures; Governance then calls the TMSC mutators. Authorization binds the
/// decoded values through the struct hash; raw calldata is not claimed to be canonical.
contract Governance {
    struct Config {
        address target;
        uint64 witnessSetVersion;
        address[] witnesses;
        uint256 threshold;
        uint64 maxGovernanceTtl;
        uint256 mutations;
    }

    address public immutable target;
    uint256 public immutable governanceChainId;
    uint64 public immutable witnessSetVersion;
    uint256 public immutable threshold;
    uint64 public immutable maxGovernanceTtl;
    /// The deployment's full mutation mask (A1-0105 M4); only bits 6 and 7 act here.
    uint256 public immutable mutations;
    address[] internal _witnesses;
    uint64 public governanceNonce;

    event GovernanceApplied(
        uint64 indexed nonce, uint8 indexed action, address indexed root, bytes32 structHash, address submitter
    );

    constructor(Config memory c) {
        if (
            c.target == address(0) || c.threshold == 0 || c.threshold > c.witnesses.length || c.maxGovernanceTtl == 0
                || c.mutations & ~MUT_ALL != 0
        ) revert Rejected(ErrorCode.MALFORMED);
        for (uint256 i = 0; i < c.witnesses.length; i++) {
            if (c.witnesses[i] == address(0)) revert Rejected(ErrorCode.MALFORMED);
            for (uint256 j = 0; j < i; j++) {
                if (c.witnesses[j] == c.witnesses[i]) revert Rejected(ErrorCode.DUPLICATE_SIGNER);
            }
        }
        target = c.target;
        governanceChainId = block.chainid;
        witnessSetVersion = c.witnessSetVersion;
        threshold = c.threshold;
        maxGovernanceTtl = c.maxGovernanceTtl;
        mutations = c.mutations;
        _witnesses = c.witnesses;
    }

    function witnesses() external view returns (address[] memory) {
        return _witnesses;
    }

    /// Any caller may submit. The first failing step wins and the whole call reverts, which also
    /// restores the nonce if the TMSC call fails (design 2.2 section 2, steps 1-9).
    function execute(GovernanceAction calldata a, bytes[] calldata signatures) external {
        GovernanceAction memory m = a;
        if (m.witnessSetVersion != witnessSetVersion) revert Rejected(ErrorCode.STALE_STATE);
        if (m.action < GOV_ADD_AUTHORITY || m.action > GOV_SET_CA_ADMINS) revert Rejected(ErrorCode.MALFORMED);
        _checkStructure(m);
        bool nonceBound = mutations & MUT_NO_GOV_NONCE == 0;
        if (nonceBound) {
            if (m.nonce <= governanceNonce) revert Rejected(ErrorCode.REPLAY);
            if (m.nonce > governanceNonce + 1) revert Rejected(ErrorCode.MALFORMED);
        }
        if (block.timestamp >= m.expiresAt) revert Rejected(ErrorCode.EXPIRED);
        if (m.expiresAt > block.timestamp + maxGovernanceTtl) revert Rejected(ErrorCode.MALFORMED);

        uint8 dispatched = m.action;
        if (mutations & MUT_NO_GOV_ACTION_BINDING != 0) m.action = 0;
        bytes32 structHash = HMBCHash.hashGovernanceAction(m);
        bytes32 digest = HMBCHash.toTypedDigest(
            HMBCHash.domainSeparator(HMBCHash.GOVERNANCE_DOMAIN, governanceChainId, address(this)), structHash
        );
        ErrorCode q = QuorumLib.verify(digest, signatures, _witnesses, threshold);
        if (q != ErrorCode.NONE) revert Rejected(q);

        if (nonceBound) governanceNonce = m.nonce;
        TMSC t = TMSC(target);
        if (dispatched == GOV_ADD_AUTHORITY) {
            t.govAddAuthority(m.nonce, m.root, m.admins);
        } else if (dispatched == GOV_REMOVE_AUTHORITY) {
            t.govRemoveAuthority(m.nonce, m.root);
        } else {
            t.govSetCaAdmins(m.nonce, m.root, m.admins);
        }
        emit GovernanceApplied(m.nonce, dispatched, m.root, structHash, msg.sender);
    }

    /// Step 3: root non-zero; ADD 1..8 admins, REMOVE none, SET 0..8; admins non-zero and strictly
    /// ascending (which excludes duplicates).
    function _checkStructure(GovernanceAction memory m) internal pure {
        if (m.root == address(0)) revert Rejected(ErrorCode.MALFORMED);
        uint256 n = m.admins.length;
        if (m.action == GOV_REMOVE_AUTHORITY) {
            if (n != 0) revert Rejected(ErrorCode.MALFORMED);
            return;
        }
        if (n > GOV_MAX_ADMINS || (m.action == GOV_ADD_AUTHORITY && n == 0)) revert Rejected(ErrorCode.MALFORMED);
        for (uint256 i = 0; i < n; i++) {
            if (m.admins[i] == address(0) || (i > 0 && m.admins[i] <= m.admins[i - 1])) {
                revert Rejected(ErrorCode.MALFORMED);
            }
        }
    }
}
