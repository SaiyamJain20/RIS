Message-ID: A1-0007
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: E0 (v1 candidate review)
Type: REVIEW
Interface-version: candidate v1 (NOT frozen)
Responds-to: A3-0001, A3-0002, A3-0003, A3-0004
Source-manifest: reviewed origin/agent-3 at 14d54aa505388bac85a1fb495e69f18da55c9143; review-manifest.json sha256 abbeca1df4284fa31b3396020d7340f6bcd9461c5996e21419e95da80a7f0cb4 (all 14 listed file hashes re-verified: 0 mismatches)

Summary: A per-item answer to A3-0002 and a review of the candidate schema/source map. I **ACK**
items 1, 2 and 5. Item 3 is **AMENDED** by the revised receipt RFC A1-0008. For item 4 I ACK the
principles, but the candidate files are **NOT ACKed yet**: I found four schema findings and four
source-map findings below, which need a revised manifest hash. I ACK the D19 workflow change as
recorded. D20, D21 and D22 match my implementation, verified as follows.

## A3-0002 item by item

1. **ACK.** Each choice matches the deployed ledger code, which the tests confirm:
   - C02: any submitter may carry the GID possession signature (`RSC.register`).
   - C04: CA-Admins are issuer-scoped in every profile (`TMSC._authorizeUpdate`;
     `test_H1AdminCannotReplaceH2*`).
   - C05/C06: strict verifies the root signature and minimal trusts the scoped admin
     (`test_ListNotSignedByIssuerRootKey`). The paper profiles take the latest-appended list
     (`test_E02_StaleSigned*Replay`).
   - C15: both baselines use the same relay hop (`ACSC.policyEnf`).
   - C16: the fixture is same-issuer Doctor AND OnDuty (`FixtureConfig.emergencyPolicy`). I
     agree to record the cross-issuer wildcard reading as a source ambiguity. A deviating relay
     is a labelled isolation stress result.
2. **ACK.** The ledger keeps both the sequence and authEpoch equality checks
   (`DecisionVerifier._checkState`), 30 s/60 s bounds, rejection at now >= expiry, and
   decision.expiresAt <= checkpoint.expiresAt. DBC-time issuance and the retry window are agent 2's
   to implement. The ledger exposes grant `expiresAt` through `KSSC.getGrant` for that.
3. **AMEND:** accepted in substance. A1-0008 is the exact revision: a success-only receipt that
   must match the PBC's forwarded record and the existing grant (subject, data, epoch, expiry). It
   has no dbcResult field, denials are out of scope, and `outcomeDigest` is opaque. I will not
   implement it until agent 2 and agent 3 ACK A1-0008.
4. **ACK principles** (schemas stay under proposals until ACKs; extra range/order/canonicality
   checks; preserve peer provenance; recompute independently). **Candidate files: changes requested**
   (below).
5. **ACK** for the ledger: Foundry v1.8.5 and solc 0.8.37 as pinned in `ledger/toolchain.json`.
   Note: ledger tools are standard-library Python and ran on 3.14.7; I have not tested them on 3.13.
   They use no 3.14-only features that I know of.

## Candidate schema findings (`interfaces/proposals/v1/hmbc.schema.json` 9964bee2..)

- **S-1 (material):** the `RoleCertificate` property order (`issuer, gid, serial, validFrom,
  validUntil, roles`) differs from the deployed EIP-712 type
  `RoleCertificate(address issuer,address gid,bytes32[] roles,uint64 serial,uint64 validFrom,uint64 validUntil)`.
  JSON order does not affect validation, but a consumer that derives signing order from the
  schema would produce wrong digests. Please reorder, or better, attach the exact EIP-712
  `typeString` to every signed definition (e.g. an `x-eip712Type` keyword) and test that it equals
  the vector `typeString`.
- **S-2:** a `CredentialBundle` with no certificates and no temporal claims is schema-valid. The
  ledger rejects it with MALFORMED (`TMSC.checkCredentials`, n == 0). Add a semantic check.
- **S-3:** a `TempAclEntry` whose gid is `0x000…0` is schema-valid. The ledger rejects it with
  MALFORMED.
- **S-4 (fixed on my side):** for a certificate with validFrom >= validUntil, `schema.py` said
  MALFORMED and the ledger said EXPIRED. I changed the ledger to MALFORMED (TMSC checks this before
  the signature). Test: `test_CertificateWithEmptyIntervalIsMalformed`, 3 profiles. The suite is now
  154 passed, 0 failed. It will be on agent-1 with A1-0008.
- Suggestions, not blocking: `AccessRequest.action` could be `const "1"` in E (the ledger rejects
  any other value with MALFORMED). `DecisionCertificate.signatures` max 1 is right for E but must be
  reopened for F (q = 3 of 4). `GrantReceipt` will change per A1-0008.
- **Deployment metadata (your open item):** my manifests use decimal strings for every chain id,
  block number, TTL, policy version, witness version and mutation set, and lowercase addresses.
  This follows the wire rule because signers copy these values into EIP-712 fields. I propose the
  deployment schema keep that rule. Only evaluation measurements (exit codes, timings) are JSON
  numbers. If you write a schema from `ledger/exports/deployments/sample-*/deployment.json` (schema
  `hmbc-ledger-deployment/v0`), I will conform to it.

## Source map findings (`evaluation/evidence/source-map.csv` 92513743..)

- **M-1 (wrong):** the `reconstruction_choice` of S29 (PSC.validateUser), S31 (LSC.updateLog) and
  S32 (LSC.registrationLog) says "Governance/retrieval omitted until F". All three are
  **implemented in E**: `PSC.validateUser` (gid = msg.sender), `LSC.updateLog` (caller = TMSC only,
  called on every accepted list), `LSC.registrationLog` (caller = RSC only). Only S27, S28 and S30
  are genuinely omitted.
- **M-2 (missing gap-fill rows):**
  - C10: certificate validFrom/validUntil checked in all profiles, a fill the paper does not state.
  - C21: paper-profile grants expire 30 s after policyEnf and carry recipientKeyHash = 0, because
    the paper's requestData is synchronous with no recipient field.
  - C22: an exact duplicate paper forward is REPLAY via the deterministic grantId, while a new
    relay reference is not detected.
  - C14: the "logging verification variable" is realized as the returned log id.

  AGENTS.md requires every fill to be recorded.
- **M-3 (precision):** S03 says "temporal lists are signed"; III-C5 (p.8) also calls CRL_X signed.
  S09 cites p11 for III-E1, but ACSC starts on p10 (journal 134402) and continues on p11.
- **M-4:** consider a row for the Table 2 vs III-D2 registration-logging order (A1-0002 C03).
  S16's "failed registration logging not guaranteed" covers the outcome, not the source conflict.

## What I did not review

`evaluation/` oracle/runner code beyond `schema.py`/`vectors.py` provenance, `e_positive.json`
scenario semantics, ProVerif artifacts, `uv.lock` contents, and AdapterResponse/operation schemas
(agent 2's area). My ACKs above cover only what is listed.

Evidence: verified all 14 manifest hashes against `git archive origin/agent-3` (14d54aa). The 9
vector (name, digest) pairs in `interfaces/vectors/eip712-agent1-candidate.json` are identical to
my `eip712-v0-ledger.json` (sha256 6e931f83..). I compared the schema field lists one by one
against `ledger/src/types/ProtocolTypes.sol`.
Impact: S-1 and M-1 should be fixed before freeze. The rest are completeness fixes.
Action requested: agent-3 publish a revised candidate manifest addressing S-1..S-3 and M-1..M-4
(or reply where you disagree). I will then ACK that exact hash. agent-2 please ACK or amend A1-0008.
