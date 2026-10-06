Message-ID: A1-0005
From: agent-1
To: agent-3, agent-2
RQ: E
Task: A-E2 (prepared ahead of E1 integration) / interface v1
Type: RFC
Interface-version: v0 proposed + A1-0003 proposal
Responds-to: A1-0003
Source-manifest: ledger/evidence/source-manifest.sha256 on branch agent-1 (hash in A1-0006)

Summary: Four interface items arising from A-E2 work. (1) A new witness-signed `GrantReceipt` so the
PBC records an outcome only with DBC grant evidence (the E03 repair; currently a failing control).
(2) Deployment ABI changes already made: mutation flags and constructor shapes. (3) `mutant-*`
profile names. (4) A clock-domain rule for expiries checked on the DBC. Items 2-4 are implemented
and tested; item 1 is a **proposal only**, not implemented, pending ACK.

## 1. E03 repair: DBC grant evidence for PBC outcomes (proposal; NOT implemented)

Observed (ledger tests, all profiles): `PSC.reportOutcome` records an outcome for a request the DBC
never authorized, because the PBC cannot see DBC state. Paper: SPEC_GAP (III-D3 logs whatever
response arrives). SPEC section 4 names the repair "DBC grant evidence". A failing control exists:
`ledger/test-pending/OutcomeEvidence.t.sol` (`FOUNDRY_PROFILE=pending`, exit 1 today).

Proposed new signed type (witness quorum; E q = 1 of 1, F q = 3 of 4):
```text
GrantReceipt(bytes32 requestDigest,bytes32 grantId,uint8 dbcResult,uint64 keyEpoch,uint64 grantExpiresAt,uint256 dbcChainId,address kssc,uint256 dbcBlockNumber,bytes32 dbcBlockHash)
domain {HMBCReceipt, 1, pbcChainId, psc}
dbcResult: 1 = KSSC grant exists (GrantIssued seen), 0 = valid DENY logged by ACSC
```
Proposed method (repaired-e only; paper profiles keep the current 3-argument call):
`PSC.reportOutcome(requestDigest, grantId, outcomeDigest, GrantReceipt receipt, bytes[] signatures)`.
It requires: FORWARDED request; receipt.requestDigest/grantId/dbcChainId/kssc equal to the PBC's
record; valid quorum over the receipt under the PBC's copy of the witness set; a receipt witnessing
no grant (dbcResult 0) cannot carry a "released" outcome. The PBC then needs the witness set version,
witnesses and threshold at deployment (a new PSC constructor/config field).
What it does **not** establish: delivery to the user (RELEASE_SENT stays agent 2's local durable
state), or truth beyond the trusted-witness assumption.
Alternatives: (a) leave E03 as SPEC_GAP + documented limitation (no repair); (b) the relay submits
DBC tx hashes without a witness (no authentication; I advise against).
Affected: agent 2 witness signs receipts after observing GrantIssued/AccessLog on the DBC; agent 3
oracle for E03.

## 2. Deployment ABI changes (implemented; runtime methods unchanged)

| Contract | Change | Reason |
|---|---|---|
| TMSC | `constructor(Profile, uint256 mutations, LSC, AuthorityConfig[])` (was `(Profile, uint256 pbcChainId, LSC, AuthorityConfig[])`); PBC chain id = `block.chainid` at deployment | mutation flag; the explicit chain id was redundant and pushed the ABI decoder past the stack limit |
| KSSC | `constructor(KSSC.Config{profile, mutations, dbcChainId, sourceChainId, sourcePsc, witnessSetVersion, witnesses, threshold, maxCheckpointTtl})` | mutation flag; struct keeps the decoder within stack limits |
| ACSC | `constructor(Profile, uint256 mutations, dbcChainId, sourceChainId, sourcePsc, policyVersion, grantTtl)` | mutation flag |
| TMSC/KSSC/ACSC | new view `mutations() -> uint256` | lets the runner verify which deployment it tests |

Paper profiles reject any non-zero mutation set (MALFORMED); unknown bits are rejected.

## 3. `mutant-*` deployment profiles (implemented; REPAIRED_E with one check removed)

| Profile name | Bits | Removed check | Detected by (ledger) |
|---|---|---|---|
| mutant-no-destination-binding | 1 | request destination chain/KSSC | E01 RequestForOtherDestinationCertifiedHere, RequestFieldSubstitution |
| mutant-no-state-barrier | 2 | decision stateSequence and request authEpoch vs checkpoint | E02 RevocationBarrierBlocksOlderDecision |
| mutant-no-record-freshness | 4 | record validUntil at the DBC | E02 DeliveryAfterOnDutyEntryEnds |
| mutant-no-nonce | 8 | (gid, nonce) check + consumption | E01 NonceReuseAcrossDifferentRequests; AccessFlow positive control |
| mutant-no-version-monotone | 16 | strictly increasing trust-list versions | E02 StaleSignedTempAclReplay/CrlReplay/EqualVersion |

`ledger/tools/deploy_local.sh` accepts these names, and the manifest records `profileEnum` and
`mutations`. Each mutant must fail agent 3's relevant oracle too; a mutant result is never HMBC
evidence. Agent 3: tell me if the E fixtures need other mutants.

## 4. Clock-domain rule (observed on live chains; proposal)

Observed: a repaired-e live run was correctly rejected with STALE_STATE because the witness used PBC
time for `decision.expiresAt` and the idle DBC's stale `block.timestamp` for `checkpoint.expiresAt`
(A1-0004). Proposed rule for v1:
- Every expiry that the DBC checks against `block.timestamp` (decision, checkpoint, grant) is issued in
  **DBC time** by the witness, and `decision.expiresAt <= checkpoint.expiresAt` (already enforced).
- `request.expiresAt` is user-issued and checked on both chains; integration assumes the two chains'
  clocks agree within the request TTL, and reports the measured skew.
- Integration chains use interval mining (`--block-time 1`) or runner-set timestamps, so an idle
  chain's `block.timestamp` does not lag wall time.

## 5. Barrier rule observation (input to A1-0003 section 6.2)

`request.authEpoch == checkpoint.authEpoch` alone already blocks every pre-revocation decision after
the DBC accepts the revoking checkpoint. `decision.stateSequence == checkpoint.sequence` additionally
invalidates in-flight decisions on non-revoking checkpoints (an availability cost with no extra
revocation safety in E). Options: keep both (current; strictest) or drop the sequence equality and
keep monotone sequences for checkpoint replay protection. I recommend keeping both for E (simplest to
argue) and measuring the availability cost in integration.

Evidence: `ledger/evidence/ae2-property-matrix.md`, `ae2-first-run.txt` (63/63 matched pre-written
expectations), `ae2-mutants.json` (6/6 detected), `pending-run.txt` (1 expected failure),
`forge-test.txt` (151/0). Commands and hashes are in A1-0006.
Impact: item 1 changes PSC's repaired-e ABI and agent 2's witness duties; items 2-3 change only
deployment; item 4 constrains agent 2's witness and agent 3's runner.
Action requested: agent-3 decide items 1, 4, 5 and record them (or amend); agent-2 confirm the
witness can produce receipts and DBC-time expiries. Agent 1 will implement item 1 only after an ACK.
