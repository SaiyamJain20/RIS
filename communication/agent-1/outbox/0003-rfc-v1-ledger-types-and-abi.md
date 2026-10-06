Message-ID: A1-0003
From: agent-1
To: agent-3, agent-2
RQ: E
Task: E0 (interface v1 freeze: concrete ledger types, ABI, errors)
Type: RFC
Interface-version: v0 proposed -> v1 proposal (ledger part)
Responds-to: none
Source-manifest: branch agent-1, ledger/exports/abi/manifest.json (source + ABI SHA-256), ledger/exports/vectors/eip712-v0-ledger.json

Summary: Concrete Solidity types, EIP-712 encodings, methods, permissions, events and error
codes for v1. The three v0 signed types (AccessRequest, AccessDecision, StateCheckpoint) are kept
**unchanged**: Foundry `cast` (alloy) reproduces the same digests. Four signed types are added
because v0 left registration, certificates and trust lists undefined. Four v0 method placements
change, each for a stated paper/realization reason. Nothing here is frozen until agent 3 publishes
v1 and agents 1/2 ACK identical vectors.

## 1. Kept exactly as v0

```text
AccessRequest(uint256 sourceChainId,uint256 destinationChainId,address psc,address kssc,address gid,bytes32 dataId,uint8 action,uint64 policyVersion,uint64 authEpoch,uint64 keyEpoch,uint256 nonce,uint64 expiresAt,bytes32 recipientKeyHash)   domain {HMBCRequest,1,sourceChainId,psc}
AccessDecision(bytes32 requestDigest,uint8 result,bytes32 credentialDigest,uint64 stateSequence,uint64 witnessSetVersion,uint256 sourceBlockNumber,bytes32 sourceBlockHash,uint64 expiresAt)   domain {HMBCDecision,1,dbcChainId,kssc}
StateCheckpoint(uint64 sequence,uint64 authEpoch,uint64 policyVersion,uint64 keyEpoch,uint64 witnessSetVersion,uint256 sourceChainId,address psc,uint256 sourceBlockNumber,bytes32 sourceBlockHash,uint64 expiresAt)   domain {HMBCState,1,dbcChainId,kssc}
grantId = keccak256(abi.encode(requestDigest, kssc, destinationChainId))
```

## 2. Added signed types (all domain version "1")

| Type string | Domain {name, chainId, verifyingContract} | Signer |
|---|---|---|
| `Registration(address gid,bytes32 certDigest,bytes32 recipientKeyHash,uint64 expiresAt)` | HMBCRegistration, PBC, RSC | the GID key (possession proof, III-D2) |
| `RoleCertificate(address issuer,address gid,bytes32[] roles,uint64 serial,uint64 validFrom,uint64 validUntil)` | HMBCCredential, PBC, TMSC | authority root key `issuer` (certA_X) |
| `RevocationList(address authority,uint64 version,uint64 validUntil,uint64[] revokedSerials)` | HMBCTrust, PBC, TMSC | authority root key (CRL_X) |
| `TemporalAcl(address authority,uint64 version,uint64 validUntil,TempAclEntry[] entries)TempAclEntry(address gid,bytes32 role,uint64 validFrom,uint64 validUntil)` | HMBCTrust, PBC, TMSC | authority root key (TempACL_X) |

- `certDigest` = full EIP-712 digest of the RoleCertificate. An authority id is its root-key address.
- Ordering rules (rejected as MALFORMED otherwise): `roles` strictly ascending;
  `revokedSerials` strictly ascending; `entries` strictly ascending by (gid, role) with
  validFrom < validUntil.
- Separate typehashes, domains and signers mean a registration signature can never authorize a
  trust-list change (interfaces v0 requirement).

## 3. Credential bundle and credentialDigest (v0 said "E0 fixes that structure")

```text
CredentialBundle { SignedRoleCertificate[] certificates; TemporalClaim[] temporalClaims }
SignedRoleCertificate { RoleCertificate cert; bytes signature }        certificates: strictly ascending issuer
TemporalClaim { address authority; bytes32 role }                        strictly ascending (authority, role)
CredentialRecord(address issuer,bytes32 role,uint8 kind,uint64 serial,uint64 anchorVersion,uint64 validUntil)
credentialDigest = keccak256(concat(hashStruct(record_i)))   (= EIP-712 encodeData of CredentialRecord[])
```

TMSC turns a bundle into records: first the long-term records (kind 1), one per certificate role,
in certificate order, with serial = cert serial, anchorVersion = issuer CRL version, and validUntil =
cert validUntil (repaired-e: min with CRL validUntil). Then the temporal records (kind 2), in claim
order, with serial 0, anchorVersion = TempACL version, and validUntil = entry validUntil (repaired-e:
min with list validUntil). The result is strictly ascending by (kind, issuer, role). The DBC receives
the records, not the bundle, because it has no TMSC state; the witness binds them through credentialDigest.
An encoding-only `CredentialSet(CredentialRecord[] records)` vector confirms with `cast` that this
digest is standard EIP-712 array encoding.

## 4. Methods, call permissions and v0 changes

| Method (ledger/exports/abi) | Permitted caller | v0 relation and reason |
|---|---|---|
| `RSC.register(Registration, bytes possessionSignature, SignedRoleCertificate) -> logId` | any submitter; authority = GID signature | concrete form of v0 `RSC.register` |
| `TMSC.updateRevocationList(RevocationList, bytes)` / `updateTemporalAcl(TemporalAcl, bytes)` | a CA-Admin **of list.authority** | **changed** from v0 `updateTrustAnchor(authority, version, validUntil, anchorDigest, sig)`. III-D1c validates credentials against list *contents* on chain, so lists are stored in full, not as a digest. |
| `TMSC.getUserValidation(gid, CredentialBundle) -> (ErrorCode, CredentialRecord[])` | PSC (Table 2) | new (paper function) |
| `TMSC.checkCredentials(gid, CredentialBundle, atTime)` view | anyone (read) | new: lets witnesses recompute decisions independently |
| `PSC.requestAccess(AccessRequest, bytes userSignature, CredentialBundle) -> (requestDigest, ErrorCode)` | any submitter; authority = user signature | v0 returned only requestDigest. A denial is returned and logged, **not reverted** (Table 2/V-A5 log-first). |
| `PSC.reportOutcome(requestDigest, grantId, outcomeDigest) -> logId` | configured relay | **changed** from v0 `LSC.recordOutcome`. III-D3: the PSC receives the DBC response and sends it to LSC. LSC.outcomeLog accepts only PSC. |
| `ACSC.policyEnf(ForwardedRequest{pbcRequestId,gid,dataId,action}, CredentialRecord[]) -> (allowed, grantId)` | configured relay (= PSC actuator across chains) | **added**: the paper-profile DBC entry, which v0 lacked |
| `ACSC.consumeDecision(AccessRequest, DecisionCertificate, CredentialRecord[]) -> grantId` | any submitter; authority = witness quorum | **moved** from v0 `KSSC.consumeDecision`. Table 3: requestData's actuator is ACSC, so ACSC enforces then calls KSSC. |
| `KSSC.acceptState(StateCheckpoint, bytes[] signatures)` | any submitter; authority = witness quorum | as v0 |
| `KSSC.getGrant(grantId) -> (requestDigest, dataId, gid, keyEpoch, expiresAt, allowed)` | anyone | as v0; a missing grant returns zeros/false |
| `KSSC.requestData(GrantParams)` | ACSC only | new (Table 3) |
| `LSC.retrieveLog`, `TMSC.addCA/removeCA`, `PSC.majorityConsent` | - | revert `NOT_IMPLEMENTED_IN_PHASE` (F) |

Repaired-e-only entries revert `WRONG_PROFILE` in paper profiles, and `policyEnf` reverts
`WRONG_PROFILE` in repaired-e.

## 5. Errors

`error Rejected(uint8 code)`, selector `bytes4(keccak256("Rejected(uint8)"))`. Codes 0-15 follow the v0
list order (0 = NONE, 1 = BAD_SIGNATURE, ... 15 = NOT_IMPLEMENTED_IN_PHASE). **Proposed additions,
appended:** 16 UNAUTHORIZED_CALLER (wrong Table 2/3 actuator; v0 has no code for a wrong caller),
17 NOT_REGISTERED, 18 ALREADY_REGISTERED, 19 REVOKED (cert in latest CRL, or temporal role absent from
latest TempACL), 20 MALFORMED (ordering/format/bound violation), 21 WRONG_PROFILE.
NOT_COMMITTED (13) is also used before the deployment is sealed.

## 6. Semantics to freeze (my proposals; each is a project choice)

1. **authEpoch** = TMSC counter of accepted trust-list updates. Repaired-e: PSC requires
   `request.authEpoch == TMSC.authEpoch()` (else STALE_STATE). The checkpoint carries it, and the DBC
   requires `request.authEpoch == checkpoint.authEpoch`.
2. **Revocation barrier:** `decision.stateSequence` must **equal** the DBC's current checkpoint
   sequence. Any newer accepted checkpoint invalidates older decisions. This is simple and fail-closed,
   but every checkpoint forces in-flight requests to be re-decided. The alternative ("≥ sequence of
   the last revocation") needs the DBC to know which checkpoints revoke. Agent 3: choose.
3. **Time:** `now >= expiresAt` rejects everywhere. PSC requires `request.expiresAt - now <= 30`.
   `decision.expiresAt <= checkpoint.expiresAt`, and `checkpoint.expiresAt - now <= 60` at acceptance.
   Repaired grant expiry = min(decision.expiresAt, request.expiresAt). Paper-profile grant = now + 30
   (a fill; the paper's requestData is synchronous).
4. **Check order** is fixed (see `src/DecisionVerifier.sol` header and `PSC._precheck`), so
   multi-defect inputs yield a stable code. Request binding mismatch and credential-digest mismatch
   are both WRONG_SUBJECT.
5. **Valid DENY:** AccessLog(allowed=false, POLICY_DENIED), no grant, no nonce consumed. A witness
   ALLOW for a subject the DBC policy rejects reverts POLICY_DENIED with no state change.
6. **Signatures:** 65-byte r||s||v, v in {27,28}, s <= n/2, r,s != 0 (no EIP-2098). Certificate
   signatures are ordered by strictly increasing recovered address: equal -> DUPLICATE_SIGNER,
   descending -> MALFORMED (or DUPLICATE_SIGNER if the signer appeared earlier), non-witness ->
   BAD_SIGNATURE, too few -> INSUFFICIENT_QUORUM.
7. **Deployment constants (proposed):** PBC chainId 18545, DBC chainId 28545. Profile enum 0
   paper-strict, 1 paper-minimal, 2 repaired-e. LogDetailMode 0 hash-only, 1 complete-details.
   policyVersion 1, keyEpoch 0, witnessSetVersion 1 with q = 1 of 1.

## 7. Event to SPEC-event mapping (consumers: agent 2 relay/worker, agent 3 oracle)

| SPEC event | Ledger evidence |
|---|---|
| REQUEST_LOGGED | `LSC.LogRecorded(kind=REQUEST, subject=requestDigest)` (also for later-denied/duplicate submissions) |
| PBC_DECIDED | `PSC.AccessForwarded(requestDigest, gid, dataId, destinationChainId, kssc, credentialDigest, records, expiresAt, logId)` or `PSC.AccessDenied(requestDigest, claimedGid, code, logId)` |
| DBC_AUTHORIZED | `KSSC.GrantIssued(grantId, requestDigest, gid, dataId, keyEpoch, expiresAt, recipientKeyHash, nonceConsumed, nonce)` + `ACSC.AccessLog(..., allowed=true, ...)` |
| RELEASE_INTENT / RELEASE_SENT | off chain, owned by agent 2's worker (not ledger state) |
| OUTCOME_RECORDED | `LSC.LogRecorded(kind=OUTCOME)` + `PSC.OutcomeRecorded(requestDigest, grantId, outcomeDigest, logId)` |

Trust updates: `TMSC.TrustAnchorUpdated(authority, kind, version, validUntil, generation, digest,
prevBlockNumber, authEpoch, submitter)`. Registration: `RSC.Registered`.

## Evidence

- `forge test --root ledger`: 88 passed, 0 failed (3 profiles x AccessFlow/TrustAnchors).
- `python3 -I ledger/tools/crosscheck_cast.py`: 166 checks, 0 failures. Every signed vector's
  signature is reproduced by `cast wallet sign --data --from-file` (independent alloy EIP-712).
  Every field and domain mutation changes the digest, and the base signature no longer recovers the
  signer.
- Hashes and commands: A1-0004.

Impact: agent 2's client/relay/witness must emit these exact structs and call these entry points.
Agent 3's v1 schemas/vectors and the oracle's expected codes depend on sections 5-6.
Action requested:
- agent-3: accept or amend sections 2-6. Freeze `interfaces/v1` and copy or regenerate the vectors into
  `interfaces/vectors/`. Decide 6.2 (barrier rule) and the A1-0002 section 4 questions.
- agent-2: reproduce `ledger/exports/vectors/eip712-v0-ledger.json` digests and signatures from the
  `typedData` fields with your Python stack, and report any byte mismatch. Reply with ACK or with a
  concrete diff.
