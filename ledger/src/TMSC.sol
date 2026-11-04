// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {
    ErrorCode,
    Rejected,
    Profile,
    HMBCHash,
    RoleCertificate,
    SignedRoleCertificate,
    RevocationList,
    TemporalAcl,
    TempAclEntry,
    CredentialBundle,
    CredentialRecord,
    TemporalClaim,
    CREDENTIAL_LONG_TERM,
    CREDENTIAL_TEMPORAL,
    ANCHOR_CRL,
    ANCHOR_TEMP_ACL,
    MUT_NO_VERSION_MONOTONE,
    mutationsAllowed,
    isRepaired
} from "./types/ProtocolTypes.sol";
import {SigLib} from "./lib/SigLib.sol";
import {Bootstrapped} from "./lib/Bootstrapped.sol";
import {LSC} from "./LSC.sol";

/// Trust Management Smart Contract on the PBC (HMBC2020 III-D1, Fig. 4, Table 2).
///
/// Authority identity = the address of the authority's root signing key (CERT_X). Root keys and
/// CA-Admin accounts are fixed at deployment; addCA/removeCA/root refresh need majorityConsent
/// (Table 2) and are phase-F governance.
///
/// Trust lists are stored in full (small synthetic fixtures) because III-D1c validates
/// credentials against the latest lists on chain. Each accepted update starts a new
/// `generation` (the Fig. 4 linked-list head). Profiles:
///  - PAPER_STRICT: issuer-scoped CA-Admin caller AND list signed by the issuer root key;
///    the latest *appended* list is current (no version ordering, no list expiry: unspecified).
///  - PAPER_MINIMAL: issuer-scoped CA-Admin caller; list signature not verified on chain.
///  - REPAIRED_E: as strict, plus strictly increasing versions and list validity at use.
contract TMSC is Bootstrapped {
    struct AuthorityConfig {
        address authority;
        address[] admins;
    }

    struct AnchorState {
        bool published;
        uint64 version;
        uint64 validUntil;
        uint64 generation;
        bytes32 contentDigest; // EIP-712 digest of the list
        uint64 blockNumber;
        uint64 prevBlockNumber; // Fig. 4: pointer to the previous block holding this anchor
    }

    struct TempWindow {
        bool present;
        uint64 validFrom;
        uint64 validUntil;
    }

    Profile public immutable profile;
    uint256 public immutable mutations;
    uint256 public immutable pbcChainId;
    LSC public immutable lsc;
    address public psc;
    address public rsc;

    mapping(address => bool) public isAuthority;
    address[] internal _authorities;
    mapping(address => mapping(address => bool)) public isCaAdmin;
    mapping(address => AnchorState) internal _crl;
    mapping(address => AnchorState) internal _acl;
    mapping(bytes32 => bool) internal _revoked; // keccak(authority, generation, serial)
    mapping(bytes32 => TempWindow) internal _temp; // keccak(authority, generation, gid, role)

    /// Incremented by every accepted trust-anchor update; witnesses copy it into checkpoints.
    uint64 public authEpoch;

    event TrustAnchorUpdated(
        address indexed authority,
        uint8 indexed kind,
        uint64 version,
        uint64 validUntil,
        uint64 generation,
        bytes32 contentDigest,
        uint64 prevBlockNumber,
        uint64 authEpoch,
        address submitter
    );

    /// The PBC chain id is the chain this contract is deployed on.
    constructor(Profile profile_, uint256 mutations_, LSC lsc_, AuthorityConfig[] memory authorities_) {
        if (!mutationsAllowed(profile_, mutations_)) {
            revert Rejected(ErrorCode.MALFORMED);
        }
        profile = profile_;
        mutations = mutations_;
        pbcChainId = block.chainid;
        lsc = lsc_;
        for (uint256 i = 0; i < authorities_.length; i++) {
            address a = authorities_[i].authority;
            if (a == address(0) || isAuthority[a]) revert Rejected(ErrorCode.MALFORMED);
            isAuthority[a] = true;
            _authorities.push(a);
            for (uint256 j = 0; j < authorities_[i].admins.length; j++) {
                isCaAdmin[a][authorities_[i].admins[j]] = true;
            }
        }
    }

    function wire(address psc_, address rsc_) external onlyBootstrap {
        psc = psc_;
        rsc = rsc_;
    }

    function _checkWiring() internal view override {
        if (psc == address(0) || rsc == address(0)) revert Rejected(ErrorCode.MALFORMED);
    }

    // ------------------------------------------------------------------ updateTrustAnchors

    /// Table 2 updateTrustAnchors (new CRL). Actuator: a CA-Admin *of the list's authority*.
    function updateRevocationList(RevocationList calldata list, bytes calldata issuerSignature)
        external
        whenSealed
        returns (uint64 generation)
    {
        RevocationList memory m = list;
        bytes32 digest = HMBCHash.revocationListDigest(m, pbcChainId, address(this));
        _authorizeUpdate(m.authority, digest, issuerSignature);
        for (uint256 i = 1; i < m.revokedSerials.length; i++) {
            if (m.revokedSerials[i] <= m.revokedSerials[i - 1]) revert Rejected(ErrorCode.MALFORMED);
        }
        AnchorState storage st = _crl[m.authority];
        _checkFreshness(st, m.version, m.validUntil);
        generation = st.generation + 1;
        for (uint256 i = 0; i < m.revokedSerials.length; i++) {
            _revoked[keccak256(abi.encode(m.authority, generation, m.revokedSerials[i]))] = true;
        }
        _advance(st, ANCHOR_CRL, m.authority, m.version, m.validUntil, generation, digest);
    }

    /// Table 2 updateTrustAnchors (new TempACL). Actuator: a CA-Admin *of the list's authority*.
    function updateTemporalAcl(TemporalAcl calldata acl, bytes calldata issuerSignature)
        external
        whenSealed
        returns (uint64 generation)
    {
        TemporalAcl memory m = acl;
        bytes32 digest = HMBCHash.temporalAclDigest(m, pbcChainId, address(this));
        _authorizeUpdate(m.authority, digest, issuerSignature);
        AnchorState storage st = _acl[m.authority];
        _checkFreshness(st, m.version, m.validUntil);
        generation = st.generation + 1;
        for (uint256 i = 0; i < m.entries.length; i++) {
            TempAclEntry memory e = m.entries[i];
            if (i > 0) {
                TempAclEntry memory p = m.entries[i - 1];
                if (e.gid < p.gid || (e.gid == p.gid && e.role <= p.role)) revert Rejected(ErrorCode.MALFORMED);
            }
            if (e.gid == address(0) || e.validFrom >= e.validUntil) revert Rejected(ErrorCode.MALFORMED);
            _temp[keccak256(abi.encode(m.authority, generation, e.gid, e.role))] =
                TempWindow(true, e.validFrom, e.validUntil);
        }
        _advance(st, ANCHOR_TEMP_ACL, m.authority, m.version, m.validUntil, generation, digest);
    }

    /// Table 2 addCA / removeCA require majorityConsent: phase-F governance.
    function addCA(bytes calldata) external pure {
        revert Rejected(ErrorCode.NOT_IMPLEMENTED_IN_PHASE);
    }

    function removeCA(bytes calldata) external pure {
        revert Rejected(ErrorCode.NOT_IMPLEMENTED_IN_PHASE);
    }

    function _authorizeUpdate(address authority, bytes32 digest, bytes calldata issuerSignature) internal view {
        if (!isAuthority[authority]) revert Rejected(ErrorCode.UNKNOWN_AUTHORITY);
        if (!isCaAdmin[authority][msg.sender]) revert Rejected(ErrorCode.UNAUTHORIZED_CALLER);
        if (profile != Profile.PAPER_MINIMAL && !SigLib.isValid(digest, issuerSignature, authority)) {
            revert Rejected(ErrorCode.BAD_SIGNATURE);
        }
    }

    function _checkFreshness(AnchorState storage st, uint64 version, uint64 validUntil) internal view {
        if (!isRepaired(profile)) return;
        if (st.published && version <= st.version && mutations & MUT_NO_VERSION_MONOTONE == 0) {
            revert Rejected(ErrorCode.STALE_ANCHOR);
        }
        if (block.timestamp >= validUntil) revert Rejected(ErrorCode.STALE_ANCHOR);
    }

    function _advance(
        AnchorState storage st,
        uint8 kind,
        address authority,
        uint64 version,
        uint64 validUntil,
        uint64 generation,
        bytes32 digest
    ) internal {
        uint64 prev = st.blockNumber;
        st.published = true;
        st.version = version;
        st.validUntil = validUntil;
        st.generation = generation;
        st.contentDigest = digest;
        st.prevBlockNumber = prev;
        st.blockNumber = uint64(block.number);
        authEpoch += 1;
        lsc.updateLog(
            keccak256(abi.encode(authority, kind)),
            abi.encode(authority, kind, version, validUntil, generation, digest, msg.sender)
        );
        emit TrustAnchorUpdated(authority, kind, version, validUntil, generation, digest, prev, authEpoch, msg.sender);
    }

    // ------------------------------------------------------------------ validation

    /// Table 2 getUserValidation. Actuator: PSC. Returns the verified attributes.
    function getUserValidation(address gid, CredentialBundle calldata bundle)
        external
        view
        whenSealed
        returns (ErrorCode code, CredentialRecord[] memory records)
    {
        if (msg.sender != psc) revert Rejected(ErrorCode.UNAUTHORIZED_CALLER);
        return checkCredentials(gid, bundle, uint64(block.timestamp));
    }

    /// Public read of the same check, for witnesses that must recompute decisions independently.
    /// A transparent ledger cannot hide this computation; the Table 2 actuator restriction is
    /// kept on getUserValidation, which is the step used by the request flow.
    function checkCredentials(address gid, CredentialBundle calldata bundle, uint64 atTime)
        public
        view
        returns (ErrorCode code, CredentialRecord[] memory records)
    {
        uint256 n = bundle.temporalClaims.length;
        for (uint256 i = 0; i < bundle.certificates.length; i++) {
            n += bundle.certificates[i].cert.roles.length;
        }
        if (n == 0) return (ErrorCode.MALFORMED, records);
        records = new CredentialRecord[](n);
        uint256 k = 0;
        address previousIssuer = address(0);
        for (uint256 i = 0; i < bundle.certificates.length; i++) {
            RoleCertificate memory c = bundle.certificates[i].cert;
            if (c.issuer <= previousIssuer) return (ErrorCode.MALFORMED, new CredentialRecord[](0));
            previousIssuer = c.issuer;
            if (c.gid != gid) return (ErrorCode.WRONG_SUBJECT, new CredentialRecord[](0));
            (ErrorCode certCode, uint64 crlVersion, uint64 validUntil) =
                _checkCertificate(c, bundle.certificates[i].signature, atTime);
            if (certCode != ErrorCode.NONE) return (certCode, new CredentialRecord[](0));
            if (c.roles.length == 0) return (ErrorCode.MALFORMED, new CredentialRecord[](0));
            for (uint256 j = 0; j < c.roles.length; j++) {
                if (j > 0 && c.roles[j] <= c.roles[j - 1]) return (ErrorCode.MALFORMED, new CredentialRecord[](0));
                records[k++] = CredentialRecord(c.issuer, c.roles[j], CREDENTIAL_LONG_TERM, c.serial, crlVersion, validUntil);
            }
        }
        for (uint256 i = 0; i < bundle.temporalClaims.length; i++) {
            TemporalClaim calldata t = bundle.temporalClaims[i];
            if (i > 0) {
                TemporalClaim calldata p = bundle.temporalClaims[i - 1];
                if (t.authority < p.authority || (t.authority == p.authority && t.role <= p.role)) {
                    return (ErrorCode.MALFORMED, new CredentialRecord[](0));
                }
            }
            (ErrorCode tCode, uint64 aclVersion, uint64 validUntil) = _checkTemporal(gid, t, atTime);
            if (tCode != ErrorCode.NONE) return (tCode, new CredentialRecord[](0));
            records[k++] = CredentialRecord(t.authority, t.role, CREDENTIAL_TEMPORAL, 0, aclVersion, validUntil);
        }
        return (ErrorCode.NONE, records);
    }

    /// Certificate check used by RSC registration and by checkCredentials.
    function validateCertificate(SignedRoleCertificate calldata signed, uint64 atTime)
        external
        view
        returns (ErrorCode code, bytes32 certDigest)
    {
        RoleCertificate memory c = signed.cert;
        certDigest = HMBCHash.roleCertificateDigest(c, pbcChainId, address(this));
        (code,,) = _checkCertificate(c, signed.signature, atTime);
    }

    function _checkCertificate(RoleCertificate memory c, bytes memory signature, uint64 atTime)
        internal
        view
        returns (ErrorCode, uint64 crlVersion, uint64 validUntil)
    {
        if (!isAuthority[c.issuer]) return (ErrorCode.UNKNOWN_AUTHORITY, 0, 0);
        if (c.validFrom >= c.validUntil) return (ErrorCode.MALFORMED, 0, 0); // never-valid interval
        bytes32 digest = HMBCHash.roleCertificateDigest(c, pbcChainId, address(this));
        if (!SigLib.isValid(digest, signature, c.issuer)) return (ErrorCode.BAD_SIGNATURE, 0, 0);
        if (atTime < c.validFrom || atTime >= c.validUntil) return (ErrorCode.EXPIRED, 0, 0);
        AnchorState storage st = _crl[c.issuer];
        validUntil = c.validUntil;
        if (isRepaired(profile)) {
            if (!st.published || atTime >= st.validUntil) return (ErrorCode.STALE_ANCHOR, 0, 0);
            if (st.validUntil < validUntil) validUntil = st.validUntil;
        }
        if (st.published && _revoked[keccak256(abi.encode(c.issuer, st.generation, c.serial))]) {
            return (ErrorCode.REVOKED, 0, 0);
        }
        return (ErrorCode.NONE, st.version, validUntil);
    }

    /// A claimed temporal role absent from the latest TempACL (removed or never assigned) is REVOKED.
    function _checkTemporal(address gid, TemporalClaim calldata t, uint64 atTime)
        internal
        view
        returns (ErrorCode, uint64 aclVersion, uint64 validUntil)
    {
        if (!isAuthority[t.authority]) return (ErrorCode.UNKNOWN_AUTHORITY, 0, 0);
        AnchorState storage st = _acl[t.authority];
        if (isRepaired(profile) && (!st.published || atTime >= st.validUntil)) {
            return (ErrorCode.STALE_ANCHOR, 0, 0);
        }
        if (!st.published) return (ErrorCode.REVOKED, 0, 0);
        TempWindow storage w = _temp[keccak256(abi.encode(t.authority, st.generation, gid, t.role))];
        if (!w.present) return (ErrorCode.REVOKED, 0, 0);
        if (atTime < w.validFrom || atTime >= w.validUntil) return (ErrorCode.EXPIRED, 0, 0);
        validUntil = w.validUntil;
        if (isRepaired(profile) && st.validUntil < validUntil) validUntil = st.validUntil;
        return (ErrorCode.NONE, st.version, validUntil);
    }

    // ------------------------------------------------------------------ views

    function authorities() external view returns (address[] memory) {
        return _authorities;
    }

    function revocationListState(address authority) external view returns (AnchorState memory) {
        return _crl[authority];
    }

    function temporalAclState(address authority) external view returns (AnchorState memory) {
        return _acl[authority];
    }

    function isRevoked(address authority, uint64 serial) external view returns (bool) {
        AnchorState storage st = _crl[authority];
        return st.published && _revoked[keccak256(abi.encode(authority, st.generation, serial))];
    }

    function temporalWindow(address authority, address gid, bytes32 role) external view returns (TempWindow memory) {
        AnchorState storage st = _acl[authority];
        if (!st.published) return TempWindow(false, 0, 0);
        return _temp[keccak256(abi.encode(authority, st.generation, gid, role))];
    }
}
