// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

// Paper-derived reconstruction of HMBC2020 (Malamas, Kotzanikolaou, Dasaklis, Burmester,
// IEEE Access 8, 2020). These types are the project's interface (interfaces/README.md),
// not wire formats specified by the paper. Status: interface v0 proposed by agent 1.

/// @dev Deployment profile. Fixed at construction; never switchable at runtime.
enum Profile {
    PAPER_STRICT, // paper actuators, signed issuer-scoped lists, latest-appended list wins
    PAPER_MINIMAL, // as strict, but list signatures are not verified on chain (admin caller trusted)
    REPAIRED_E // signed decisions, checkpoints, nonces, monotone versions (project extension)
}

/// @dev Stable rejection classes. Indices 0-15 follow interfaces/README.md v0 order;
/// 16+ are agent-1 proposals (A1 RFC) appended so v0 indices never move.
enum ErrorCode {
    NONE,
    BAD_SIGNATURE,
    WRONG_SUBJECT,
    WRONG_DESTINATION,
    UNKNOWN_AUTHORITY,
    STALE_ANCHOR,
    STALE_STATE,
    EXPIRED,
    REPLAY,
    POLICY_DENIED,
    INSUFFICIENT_QUORUM,
    DUPLICATE_SIGNER,
    WRONG_EPOCH,
    NOT_COMMITTED,
    ADAPTER_UNAVAILABLE,
    NOT_IMPLEMENTED_IN_PHASE,
    UNAUTHORIZED_CALLER,
    NOT_REGISTERED,
    ALREADY_REGISTERED,
    REVOKED,
    MALFORMED,
    WRONG_PROFILE
}

/// @dev Every ledger rejection uses this error so tests assert a reason class, not text.
error Rejected(ErrorCode code);

enum LogDetailMode {
    HASH_ONLY, // V-B3: "only the transaction hash is stored in the PBC"
    COMPLETE_DETAILS // III-D4: "the LSC will store the complete transaction details in the PBC"
}

uint8 constant ACTION_READ = 1;
uint8 constant RESULT_DENY = 0;
uint8 constant RESULT_ALLOW = 1;
uint8 constant CREDENTIAL_LONG_TERM = 1;
uint8 constant CREDENTIAL_TEMPORAL = 2;
uint8 constant ANCHOR_CRL = 1;
uint8 constant ANCHOR_TEMP_ACL = 2;

// Deliberate check removals for `mutant-*` deployments (REPAIRED_E only). They exist to show that
// tests and the evaluation oracle detect a missing check; a mutant result is never evidence about
// HMBC. Paper profiles reject any non-zero mutation set.
uint256 constant MUT_NO_DESTINATION_BINDING = 1 << 0; // DecisionVerifier step 2 skipped
uint256 constant MUT_NO_STATE_BARRIER = 1 << 1; // stateSequence and authEpoch vs checkpoint skipped
uint256 constant MUT_NO_RECORD_FRESHNESS = 1 << 2; // DecisionVerifier step 13 skipped
uint256 constant MUT_NO_NONCE = 1 << 3; // KSSC neither checks nor consumes (gid, nonce)
uint256 constant MUT_NO_VERSION_MONOTONE = 1 << 4; // TMSC accepts non-increasing list versions
uint256 constant MUT_ALL = (1 << 5) - 1;

/// Possession proof signed by the GID key (III-D2 "signed challenge"; GID = address, IV-D).
struct Registration {
    address gid;
    bytes32 certDigest;
    bytes32 recipientKeyHash;
    uint64 expiresAt;
}

/// Long-term role certificate certA_X, signed by authority X's root key (III-C5).
struct RoleCertificate {
    address issuer;
    address gid;
    bytes32[] roles;
    uint64 serial;
    uint64 validFrom;
    uint64 validUntil;
}

struct SignedRoleCertificate {
    RoleCertificate cert;
    bytes signature;
}

/// Signed CRL_X (III-C5, III-D). Serials strictly ascending.
struct RevocationList {
    address authority;
    uint64 version;
    uint64 validUntil;
    uint64[] revokedSerials;
}

/// One TempACL_X entry: GID, temporal role and effective period (III-C6).
struct TempAclEntry {
    address gid;
    bytes32 role;
    uint64 validFrom;
    uint64 validUntil;
}

/// Signed TempACL_X (III-C5/C6). Entries strictly ascending by (gid, role).
struct TemporalAcl {
    address authority;
    uint64 version;
    uint64 validUntil;
    TempAclEntry[] entries;
}

/// interfaces/README.md v0 AccessRequest, exact field order.
struct AccessRequest {
    uint256 sourceChainId;
    uint256 destinationChainId;
    address psc;
    address kssc;
    address gid;
    bytes32 dataId;
    uint8 action;
    uint64 policyVersion;
    uint64 authEpoch;
    uint64 keyEpoch;
    uint256 nonce;
    uint64 expiresAt;
    bytes32 recipientKeyHash;
}

/// A temporal role the user claims; TMSC looks it up in the latest TempACL of `authority`.
struct TemporalClaim {
    address authority;
    bytes32 role;
}

/// What the user presents to PSC.requestAccess (Table 2 input "userCert").
struct CredentialBundle {
    SignedRoleCertificate[] certificates;
    TemporalClaim[] temporalClaims;
}

/// One verified attribute produced by TMSC ("verified attributes", Fig. 6 step 4).
/// Canonical order: strictly ascending by (kind, issuer, role).
struct CredentialRecord {
    address issuer;
    bytes32 role;
    uint8 kind;
    uint64 serial;
    uint64 anchorVersion;
    uint64 validUntil;
}

/// interfaces/README.md v0 AccessDecision.
struct AccessDecision {
    bytes32 requestDigest;
    uint8 result;
    bytes32 credentialDigest;
    uint64 stateSequence;
    uint64 witnessSetVersion;
    uint256 sourceBlockNumber;
    bytes32 sourceBlockHash;
    uint64 expiresAt;
}

struct DecisionCertificate {
    AccessDecision decision;
    bytes[] signatures;
}

/// interfaces/README.md v0 StateCheckpoint.
struct StateCheckpoint {
    uint64 sequence;
    uint64 authEpoch;
    uint64 policyVersion;
    uint64 keyEpoch;
    uint64 witnessSetVersion;
    uint256 sourceChainId;
    address psc;
    uint256 sourceBlockNumber;
    bytes32 sourceBlockHash;
    uint64 expiresAt;
}

/// Paper-profile relay tuple: Fig. 6 step (4) [GID, verified attributes, data_id] plus the PBC
/// request reference (Fig. 6 step (9) carries trans_hash). Not signed: the paper specifies no
/// PBC->DBC message authentication beyond the PSC actuator.
struct ForwardedRequest {
    bytes32 pbcRequestId;
    address gid;
    bytes32 dataId;
    uint8 action;
}

/// EIP-712 hashing for every signed project type. Domain version is always "1".
library HMBCHash {
    bytes32 internal constant DOMAIN_TYPEHASH =
        keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");

    string internal constant REGISTRATION_DOMAIN = "HMBCRegistration"; // chain PBC, contract RSC
    string internal constant CREDENTIAL_DOMAIN = "HMBCCredential"; // chain PBC, contract TMSC
    string internal constant TRUST_DOMAIN = "HMBCTrust"; // chain PBC, contract TMSC
    string internal constant REQUEST_DOMAIN = "HMBCRequest"; // chain source(PBC), contract PSC
    string internal constant DECISION_DOMAIN = "HMBCDecision"; // chain destination(DBC), contract KSSC
    string internal constant STATE_DOMAIN = "HMBCState"; // chain destination(DBC), contract KSSC

    bytes32 internal constant REGISTRATION_TYPEHASH =
        keccak256("Registration(address gid,bytes32 certDigest,bytes32 recipientKeyHash,uint64 expiresAt)");
    bytes32 internal constant ROLE_CERTIFICATE_TYPEHASH = keccak256(
        "RoleCertificate(address issuer,address gid,bytes32[] roles,uint64 serial,uint64 validFrom,uint64 validUntil)"
    );
    bytes32 internal constant REVOCATION_LIST_TYPEHASH =
        keccak256("RevocationList(address authority,uint64 version,uint64 validUntil,uint64[] revokedSerials)");
    bytes32 internal constant TEMP_ACL_ENTRY_TYPEHASH =
        keccak256("TempAclEntry(address gid,bytes32 role,uint64 validFrom,uint64 validUntil)");
    bytes32 internal constant TEMPORAL_ACL_TYPEHASH = keccak256(
        "TemporalAcl(address authority,uint64 version,uint64 validUntil,TempAclEntry[] entries)"
        "TempAclEntry(address gid,bytes32 role,uint64 validFrom,uint64 validUntil)"
    );
    bytes32 internal constant ACCESS_REQUEST_TYPEHASH = keccak256(
        "AccessRequest(uint256 sourceChainId,uint256 destinationChainId,address psc,address kssc,address gid,"
        "bytes32 dataId,uint8 action,uint64 policyVersion,uint64 authEpoch,uint64 keyEpoch,uint256 nonce,"
        "uint64 expiresAt,bytes32 recipientKeyHash)"
    );
    bytes32 internal constant CREDENTIAL_RECORD_TYPEHASH = keccak256(
        "CredentialRecord(address issuer,bytes32 role,uint8 kind,uint64 serial,uint64 anchorVersion,uint64 validUntil)"
    );
    bytes32 internal constant ACCESS_DECISION_TYPEHASH = keccak256(
        "AccessDecision(bytes32 requestDigest,uint8 result,bytes32 credentialDigest,uint64 stateSequence,"
        "uint64 witnessSetVersion,uint256 sourceBlockNumber,bytes32 sourceBlockHash,uint64 expiresAt)"
    );
    bytes32 internal constant STATE_CHECKPOINT_TYPEHASH = keccak256(
        "StateCheckpoint(uint64 sequence,uint64 authEpoch,uint64 policyVersion,uint64 keyEpoch,"
        "uint64 witnessSetVersion,uint256 sourceChainId,address psc,uint256 sourceBlockNumber,"
        "bytes32 sourceBlockHash,uint64 expiresAt)"
    );

    function domainSeparator(string memory name, uint256 chainId, address verifyingContract)
        internal
        pure
        returns (bytes32)
    {
        return keccak256(abi.encode(DOMAIN_TYPEHASH, keccak256(bytes(name)), keccak256("1"), chainId, verifyingContract));
    }

    function toTypedDigest(bytes32 domainSep, bytes32 structHash) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked("\x19\x01", domainSep, structHash));
    }

    function hashRegistration(Registration memory r) internal pure returns (bytes32) {
        return keccak256(abi.encode(REGISTRATION_TYPEHASH, r.gid, r.certDigest, r.recipientKeyHash, r.expiresAt));
    }

    function hashRoleCertificate(RoleCertificate memory c) internal pure returns (bytes32) {
        return keccak256(
            abi.encode(
                ROLE_CERTIFICATE_TYPEHASH,
                c.issuer,
                c.gid,
                keccak256(abi.encodePacked(c.roles)),
                c.serial,
                c.validFrom,
                c.validUntil
            )
        );
    }

    /// EIP-712 encoding of uint64[]: keccak256 of the 32-byte-padded elements.
    function hashUint64Array(uint64[] memory xs) internal pure returns (bytes32) {
        bytes memory packed = new bytes(32 * xs.length);
        for (uint256 i = 0; i < xs.length; i++) {
            uint256 word = xs[i];
            assembly ("memory-safe") {
                mstore(add(add(packed, 32), mul(i, 32)), word)
            }
        }
        return keccak256(packed);
    }

    function hashRevocationList(RevocationList memory l) internal pure returns (bytes32) {
        return keccak256(
            abi.encode(REVOCATION_LIST_TYPEHASH, l.authority, l.version, l.validUntil, hashUint64Array(l.revokedSerials))
        );
    }

    function hashTempAclEntry(TempAclEntry memory e) internal pure returns (bytes32) {
        return keccak256(abi.encode(TEMP_ACL_ENTRY_TYPEHASH, e.gid, e.role, e.validFrom, e.validUntil));
    }

    function hashTemporalAcl(TemporalAcl memory a) internal pure returns (bytes32) {
        bytes32[] memory hs = new bytes32[](a.entries.length);
        for (uint256 i = 0; i < hs.length; i++) {
            hs[i] = hashTempAclEntry(a.entries[i]);
        }
        return keccak256(
            abi.encode(TEMPORAL_ACL_TYPEHASH, a.authority, a.version, a.validUntil, keccak256(abi.encodePacked(hs)))
        );
    }

    function hashAccessRequest(AccessRequest memory r) internal pure returns (bytes32) {
        // Two static abi.encode halves concatenate to the single 14-word encoding (avoids stack limits).
        bytes memory head = abi.encode(
            ACCESS_REQUEST_TYPEHASH, r.sourceChainId, r.destinationChainId, r.psc, r.kssc, r.gid, r.dataId
        );
        bytes memory tail = abi.encode(
            r.action, r.policyVersion, r.authEpoch, r.keyEpoch, r.nonce, r.expiresAt, r.recipientKeyHash
        );
        return keccak256(bytes.concat(head, tail));
    }

    function hashCredentialRecord(CredentialRecord memory c) internal pure returns (bytes32) {
        return keccak256(
            abi.encode(CREDENTIAL_RECORD_TYPEHASH, c.issuer, c.role, c.kind, c.serial, c.anchorVersion, c.validUntil)
        );
    }

    /// credentialDigest = EIP-712 encoding of CredentialRecord[] (keccak of concatenated struct hashes).
    function hashCredentialRecords(CredentialRecord[] memory cs) internal pure returns (bytes32) {
        bytes32[] memory hs = new bytes32[](cs.length);
        for (uint256 i = 0; i < hs.length; i++) {
            hs[i] = hashCredentialRecord(cs[i]);
        }
        return keccak256(abi.encodePacked(hs));
    }

    function hashAccessDecision(AccessDecision memory d) internal pure returns (bytes32) {
        return keccak256(
            abi.encode(
                ACCESS_DECISION_TYPEHASH,
                d.requestDigest,
                d.result,
                d.credentialDigest,
                d.stateSequence,
                d.witnessSetVersion,
                d.sourceBlockNumber,
                d.sourceBlockHash,
                d.expiresAt
            )
        );
    }

    function hashStateCheckpoint(StateCheckpoint memory s) internal pure returns (bytes32) {
        bytes memory head = abi.encode(
            STATE_CHECKPOINT_TYPEHASH, s.sequence, s.authEpoch, s.policyVersion, s.keyEpoch, s.witnessSetVersion
        );
        bytes memory tail = abi.encode(s.sourceChainId, s.psc, s.sourceBlockNumber, s.sourceBlockHash, s.expiresAt);
        return keccak256(bytes.concat(head, tail));
    }

    // ---- full typed digests (domain + struct) ----

    function registrationDigest(Registration memory r, uint256 pbcChainId, address rsc)
        internal
        pure
        returns (bytes32)
    {
        return toTypedDigest(domainSeparator(REGISTRATION_DOMAIN, pbcChainId, rsc), hashRegistration(r));
    }

    function roleCertificateDigest(RoleCertificate memory c, uint256 pbcChainId, address tmsc)
        internal
        pure
        returns (bytes32)
    {
        return toTypedDigest(domainSeparator(CREDENTIAL_DOMAIN, pbcChainId, tmsc), hashRoleCertificate(c));
    }

    function revocationListDigest(RevocationList memory l, uint256 pbcChainId, address tmsc)
        internal
        pure
        returns (bytes32)
    {
        return toTypedDigest(domainSeparator(TRUST_DOMAIN, pbcChainId, tmsc), hashRevocationList(l));
    }

    function temporalAclDigest(TemporalAcl memory a, uint256 pbcChainId, address tmsc)
        internal
        pure
        returns (bytes32)
    {
        return toTypedDigest(domainSeparator(TRUST_DOMAIN, pbcChainId, tmsc), hashTemporalAcl(a));
    }

    /// v0: domain {HMBCRequest, 1, sourceChainId, psc} taken from the request's own fields.
    function accessRequestDigest(AccessRequest memory r) internal pure returns (bytes32) {
        return toTypedDigest(domainSeparator(REQUEST_DOMAIN, r.sourceChainId, r.psc), hashAccessRequest(r));
    }

    function accessDecisionDigest(AccessDecision memory d, uint256 dbcChainId, address kssc)
        internal
        pure
        returns (bytes32)
    {
        return toTypedDigest(domainSeparator(DECISION_DOMAIN, dbcChainId, kssc), hashAccessDecision(d));
    }

    function stateCheckpointDigest(StateCheckpoint memory s, uint256 dbcChainId, address kssc)
        internal
        pure
        returns (bytes32)
    {
        return toTypedDigest(domainSeparator(STATE_DOMAIN, dbcChainId, kssc), hashStateCheckpoint(s));
    }

    /// grantId = keccak256(abi.encode(requestDigest, kssc, destinationChainId)) (v0).
    function grantId(bytes32 requestDigest, address kssc, uint256 destinationChainId) internal pure returns (bytes32) {
        return keccak256(abi.encode(requestDigest, kssc, destinationChainId));
    }
}
