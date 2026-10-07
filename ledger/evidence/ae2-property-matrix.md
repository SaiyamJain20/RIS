# A-E2 ledger case-to-property matrix (agent 1)

**Scope.** Ledger unit evidence from `forge test --root ledger`, single EVM, synthetic fixture. Run
2026-10-07 on agent 1's machine with Foundry v1.8.5 and solc 0.8.37. This is **not** integrated
E-gate evidence: agent 3's independent oracle and the two-chain integration run decide the RQ1
classification.

**Test-first record.** I wrote the expected per-profile outcomes into the tests before the first run.
The first-run output is saved verbatim in `ae2-first-run.txt`: 63/63 matched, with no edits after
observing results. The E03 outcome-evidence repair was first a failing control (`pending-first-run.txt`,
`pending-run.txt`). It was implemented later as A1-0008 revision 2 (ACK A3-0005 and A2-0002): the
tests were written against a reverting stub and seen failing (`receipt-first-run.txt`, 11 failures)
before the implementation passed them.

**Prerequisite skipped.** PLAN schedules A-E2 after E1 integration. I did this while waiting for
agents 2/3 (independent same-RQ work), so it may need revision after the v1 freeze.

Legend: **HOLDS** = property enforced; **VIOLATED** = the attack/condition succeeds (observed
SPEC_GAP for paper profiles); **WINDOW** = allowed by the documented pre-barrier rule;
**BOUNDARY** = holds only under a stated trust assumption; **PENDING** = desired repair not
implemented. "Mutant" names the `mutant-*` deployment that the test detects
(`check_mutants.py`, `ae2-mutants.txt`).

## E01 decision provenance and replay (`test/DecisionBinding.t.sol`)

| Test | Property | paper-strict | paper-minimal | repaired-e | Mutant |
|---|---|---|---|---|---|
| RelaySubjectSubstitution | DBC grant subject = PBC-verified subject | VIOLATED (Bob granted with Alice's attributes) | VIOLATED | relay entry disabled; subject bound by request digest (RequestFieldSubstitution, gid -> WRONG_SUBJECT) | |
| RelayFabricatedRequest | grant implies a PBC decision | VIOLATED (grant; no PBC log) | VIOLATED | non-witness certificate -> BAD_SIGNATURE (AccessFlow `RejectedCertificateChangesNoState`) | |
| RelayReplayUnderNewReference | one grant per PBC decision | VIOLATED (second grant) | VIOLATED | (gid, nonce) consumed once (NonceReuseAcrossDifferentRequests) | no-nonce |
| RelayDeliveryAfterRequestExpiry | no grant after request expiry | VIOLATED | VIOLATED | EXPIRED (RequestExpiryAtDbc) | |
| RequestFieldSubstitution (13 fields) | every request field bound | - | - | HOLDS: 4 destination fields -> WRONG_DESTINATION, action -> MALFORMED, 8 others -> WRONG_SUBJECT; no state | no-destination-binding |
| DecisionFieldSubstitution (8 fields) | decision integrity | - | - | HOLDS: requestDigest -> WRONG_SUBJECT, witnessSetVersion -> STALE_STATE, 6 others -> BAD_SIGNATURE | |
| RecordSubstitution | attributes bound to decision | - | - | HOLDS (WRONG_SUBJECT) | |
| DecisionDomainBinding | decision bound to this KSSC/chain | - | - | HOLDS (BAD_SIGNATURE) | |
| RequestForOtherDestinationCertifiedHere | request's own destination enforced | - | - | HOLDS (WRONG_DESTINATION) | no-destination-binding |
| SignatureEncodings | canonical, distinct, quorum | - | - | HOLDS (duplicate -> DUPLICATE_SIGNER, empty -> INSUFFICIENT_QUORUM, high-s / 64-byte -> BAD_SIGNATURE) | |
| NonceReuseAcrossDifferentRequests | (gid, nonce) single use | - | - | HOLDS (REPLAY) | no-nonce |
| DecisionExpiryBoundary, RequestExpiryAtDbc | now >= expiresAt rejects | - | - | HOLDS (EXPIRED at equality; one second earlier succeeds) | |

Interpretation: the paper specifies no PBC->DBC binding (A1-0002 C15), so a deviating relay can
substitute, fabricate, replay or delay forwarded decisions. HMBC assumes isolation (V-A1), so these
are **SPEC_GAP results under a violated isolation assumption (stress)**. They are not counterexamples
to the paper's claims under its own model.

## E02 trust-anchor freshness (`test/Freshness.t.sol`)

| Test | Property | paper-strict | paper-minimal | repaired-e | Mutant |
|---|---|---|---|---|---|
| StaleSignedTempAclReplay | an older signed TempACL cannot become current | VIOLATED (OnDuty revocation undone) | VIOLATED | HOLDS (STALE_ANCHOR; Alice stays REVOKED) | no-version-monotone |
| StaleSignedCrlReplay | an older signed CRL cannot become current | VIOLATED (cert revocation undone) | VIOLATED | HOLDS | no-version-monotone |
| EqualVersionDifferentContent | one list per version | VIOLATED | VIOLATED | HOLDS | no-version-monotone |
| ExpiredListInstall | expired list not installed | VIOLATED | VIOLATED | HOLDS | |
| ListExpiryAtUse | list validity enforced at use | VIOLATED | VIOLATED | HOLDS (STALE_ANCHOR) | |
| DelayedDeliveryAcrossPbcRevocationBeforeBarrier | no new grant after PBC revocation | VIOLATED (no DBC barrier at all) | VIOLATED | WINDOW: grant until the DBC accepts a newer checkpoint (interfaces v0 rule) | |
| DeliveryAfterOnDutyEntryEnds | attribute validity re-checked at the DBC | VIOLATED | VIOLATED | HOLDS (EXPIRED) | no-record-freshness |
| RevocationBarrierBlocksOlderDecision | barrier closes the window | - | - | HOLDS (STALE_STATE, no nonce/grant) | no-state-barrier |
| CheckpointMonotonicityAndFreshness | rollback/replay/epoch decrease/TTL/expiry/foreign signer rejected | - | - | HOLDS | |
| DecisionMayNotOutliveCheckpoint | decision.expiresAt <= checkpoint.expiresAt | - | - | HOLDS | |

Interpretation: the "latest appended list" reading of III-D/Fig. 4 (A1-0002 C06) lets an authorized
CA-Admin submission of an older, correctly signed list roll back a revocation. That needs a delayed or
duplicated submission by an authorized submitter, or a compromised admin account. Classification:
SPEC_GAP (the paper defines no list version or freshness). The pre-barrier WINDOW in repaired-e is a
designed limit: its size is the PBC->DBC checkpoint lag, which only integration can measure.

Observation: the barrier has two independent checks, `decision.stateSequence == checkpoint.sequence`
and `request.authEpoch == checkpoint.authEpoch`. I first planned a mutant that removed only the
sequence check, but the authEpoch check alone still blocks old decisions after any trust-list update.
So `mutant-no-state-barrier` removes both. Implication for A1-0003 section 6.2: authEpoch equality
alone already enforces revocation, and sequence equality additionally invalidates decisions on every
non-revoking checkpoint (availability cost).

## E03 audit correspondence (`test/Audit.t.sol`, `test/OutcomeEvidence.t.sol`)

| Test | Property | paper-strict | paper-minimal | repaired-e |
|---|---|---|---|---|
| DroppedOutcomeStaysVisiblyPending | a granted request with no outcome is visibly pending | HOLDS | HOLDS | HOLDS. Reconciliation needs an honest reporter; nothing times it out. |
| OutcomeWithoutDbcGrant (+ `OutcomeEvidence.t.sol`) | PBC outcome implies DBC authorization | VIOLATED | VIOLATED | HOLDS (A1-0008): the unattested path is disabled (WRONG_PROFILE); a witness-signed GrantReceipt must match the forwarded record and the grant (10 field substitutions rejected with stable codes; signature/quorum/caller/replay checks); late reconciliation allowed. Mutant: no-receipt-binding |
| EventsCorrelateWithPbcRequest | DBC GrantIssued/AccessLog carry the logged PBC digest | HOLDS for an honest relay (reference is relay-supplied) | same | HOLDS (digest recomputed from the user-signed request) |
| LogDetailMode (complete + hash-only suites) | III-D4 vs V-B3 content | stored details match encoding / only hash | same | same |
| TrustedWitnessBoundaryUnloggedRequest | DBC grant implies PBC request log | (paper: VIOLATED via RelayFabricatedRequest) | same | BOUNDARY: a witness-signed decision for a never-submitted request is granted; correspondence rests on the trusted witness (E: 1 witness; F: q = 3 of 4) |

Not ledger evidence and not covered here: RELEASE_INTENT / RELEASE_SENT durability and crash
recovery (agent 2), and cross-module correspondence over real runs (agent 3).

## Commands (repository root)

```bash
forge test --root ledger                                   # 162 passed, 0 failed (current tree)
python3 -I ledger/tools/check_mutants.py ledger/evidence/ae2-mutants.json   # 7/7 mutant suites detected
```
