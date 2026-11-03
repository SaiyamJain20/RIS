# F0 witness signing rules (R6) — proposal for review

Author: agent 2. Date: 2026-11-03 (revision 6, 2026-11-04, after A3-0062; there is no revision 4 of this file: revision 4 of the F0 set left it unchanged). Phase: F0 planning. **PROPOSAL, NOT ACKED, NOT IMPLEMENTED, NOT FROZEN.**
Revision 6 (2026-11-04, after A3-0062) changes **only section 8** again: items 8 to 10 are rewritten for R4 (an inconsistent reporter is excluded) and R5 (the decision is taken once on a snapshot and late reports never cancel or create it), the recovery-scheduling branches are pre-registered, and one limitation is stated plainly (adoption cannot erase a live signature). Sections 0 to 7, 9 and 10 stay byte-identical to revision 3. Revision 5 (2026-11-04, after A3-0061, the pool-retry amendment) changed **only section 8**: items 7 to 10 (retained proposal, recorded-value reports, adoption, re-proposal) and the paragraph after the list. Sections 0 to 7, 9 and 10 are byte-identical to revision 3 (file sha256 `c982ec8a..`), checked by text comparison. Revision 3 (2026-11-04, after A3-0058) maps `CONFLICT` and `QUORUM_UNAVAILABLE` onto existing v1 codes with reasons (`SUCCESSOR-WIRE.md`), says that a same-value renewal never extends a request or a grant, points the tripwire's FAULTED response and recovery to `SUCCESSOR-WIRE.md` section 4, lists what the bounded check does **not** check, and records agent 3's O1-O6 recommendations as recommendations (not ACKs). Revision 2 (commit 09dbb5b, sha256 `85887e38..`) took A1-0094 C1 (wording of the decision-expiry bound) and C2 (scope of the monotone-timestamp assumption) and added A1's ledger-side notes on DENY decisions and on governance pre-validation. Revision 1 is commit 39af20f (file sha256 `3d5ca717..`).
Paper-derived reconstruction, symbolic adapter, synthetic data. Nothing here changes interface v1, E pins or any production byte.
Claim classes used below: **[src]** read from current source (file:line, not executed here); **[prop]** a proposed rule; **[model]** result of the
bounded check in `model/` (design check only); **[untested]** a prediction that no run has touched.

Answers: A3-0054 / A3-0055 / A3-0056 / A3-0057 (R6, deterministic expiry, independent validation, persistence, restart, signature filtering) and the
agent-2 questions in A1-0088 (D-a, D-b, D-d2, D-e2). Ledger bindings are taken from A1's design revision 2.1 (`ledger/f0/A-F1-DESIGN.md`, sha256 `0d66f89a..`,
origin/agent-1 4b35ad3) section 9; if that design changes, these rules change with it.

## 0. What the E code does today (so the F change is visible) [src]

- `protocol/hmbc_protocol/witness.py` is **stateless**. It has no durable record, no retry counter, and signs on every call.
  - `checkpoint()` (lines 54-67): sequence = DBC current + 1, head = PBC `latest`, `expiresAt = dbc.now() + ttl`. Two calls before the DBC accepts the first give two
    differently-signed checkpoints for the same sequence (different `expiresAt`, and a different head if a PBC block was mined in between).
  - `decide()` (lines 100-142): `expiresAt = min(request.expiresAt, checkpoint.expiresAt, dbc_now + DECISION_TTL)`. The third term depends on the witness's own clock.
  - `attest_grant()` (lines 145-162): `dbcBlockNumber/Hash` = the DBC `latest` block at the time of the call (line 151, 160). The PSC never checks either field
    (`ledger/src/PSC.sol:_checkReceipt`), so the receipt bytes depend on when the witness was asked.
- With q = 1 of 1 and one trusted witness none of this matters. With q = 3 of 4 every one of the three signers must sign **byte-identical** structs, and "honest
  witnesses sign at most one conflicting value per key" (SPEC section 5) must be something the code enforces, not a convention. E's README already says this
  (A31 is caller-side discipline, the witness does not enforce it).
- `QuorumLib.verify` (`ledger/src/lib/SigLib.sol`) returns `BAD_SIGNATURE` for the **whole** certificate if any single supplied signature does not recover to a
  member of the witness set (it returns at the first bad one), and requires signatures sorted by signer address. A collector that blindly forwards replies can be
  defeated by one Byzantine reply [src]. The collector rules in section 8 follow from this.

## 1. Conflict key, effect value, liveness field [prop]

For each of the four signed object types:

| Type | EIP-712 domain (name, chain, verifier) | Key field in `K` | Effect value `V` (everything except the liveness field) | Liveness field `e` |
|---|---|---|---|---|
| AccessDecision | HMBCDecision, DBC, KSSC | `requestDigest` | result, credentialDigest, stateSequence, witnessSetVersion, sourceBlockNumber, sourceBlockHash | `expiresAt`, **deterministic** (section 4) |
| StateCheckpoint | HMBCState, DBC, KSSC | `sequence` | authEpoch, policyVersion, keyEpoch, witnessSetVersion, sourceChainId, psc, sourceBlockNumber, sourceBlockHash | `expiresAt`, proposer-chosen inside a window (section 4) |
| GrantReceipt | HMBCReceipt, PBC, PSC | `requestDigest` | all fields; `dbcBlockNumber/Hash` canonicalised (section 5) | none (the ledger has no receipt expiry) |
| GovernanceAction | HMBCGovernance, PBC, Governance | `nonce` | action, root, admins, witnessSetVersion | `expiresAt`, proposer-chosen inside a window (section 4) |

`K = (type, domainSeparator32, witnessSetVersion, keyField)`. The 32-byte EIP-712 **domain separator** (name, version, chainId, verifyingContract) is part of `K`, which
resolves the `(chainId, nonce)` shorthand in A1-0088: two Governance deployments on one chain id, or a PBC and a DBC with equal chain ids, cannot collide because the
verifying contract differs. `witnessSetVersion` follows SPEC section 5. Core F never changes the set, so the version never differs inside one deployment; it stays in
`K` so that a later set change cannot silently inherit an old record.

`V` is stored as canonical JSON (sorted keys, decimal strings for integers, lowercase 0x hex, `expiresAt` removed) plus its sha256 `vHash`. Equality of effect is equality of `vHash`
**and** of the stored JSON. `digest` is the full EIP-712 digest including `e`.

## 2. The signing rule [prop]

An honest witness executes the following inside one SQLite `BEGIN IMMEDIATE ... COMMIT` (journal WAL, `synchronous=FULL`, the discipline `worker.py` already uses), and
**returns the signature only after the commit succeeded**:

1. **Validate independently** (section 3). On failure: refuse, write nothing.
2. Read the record for `K`.
   - none: insert `(K, V, digest, e, observation)`.
   - exists and `vHash` equal: insert the new `digest` if it is not already present (same effect, possibly another expiry). **Idempotent re-sign.** The signature is deterministic
     (RFC 6979), the stored one is returned for a digest already signed.
   - exists and `vHash` differs: allowed only if **every digest recorded under K is dead** (section 6) under an observation taken **after** this request arrived. Then move the old
     record to an append-only `superseded` table (with the death evidence: chain, block number, block hash, block timestamp) and insert the new one. Otherwise refuse with reason `CONFLICT_PINNED` (an internal reason on the existing code `STALE_STATE`; `SUCCESSOR-WIRE.md` section 1).
3. Commit. Only then sign and return.

A crash before the commit signs nothing; a crash after the commit and before the reply leaves a record that makes the retry idempotent. A restarted witness has no in-memory
state to lose. [prop; the restart behaviour is untested]

## 3. Independent validation (what an honest witness recomputes) [prop]

The witness never signs a field it did not derive from its **own** RPC view of the ledgers. The proposal is only a candidate for comparison, never the source of a value.
The ledger does not backstop every item, so the item is also a duty:

| Type | Checks (all must pass; first failure refuses with the interface's error class) |
|---|---|
| AccessDecision | (a) request and bundle recovered from the PBC `AccessForwarded` log and the direct-to-PSC `requestAccess` calldata, request digest recomputed, PSC record equal (E logic, `witness.py:70-98`). (b) DBC checkpoint exists, `now < cp.expiresAt`, names a real PBC block with the stated hash and authEpoch, `forwardedAt <= cp.sourceBlockNumber`, request authEpoch/policyVersion/keyEpoch equal the checkpoint, destination and KSSC equal, `(gid, nonce)` not consumed, request not expired on either chain's clock (E logic). (c) `result` and `credentialDigest` equal the witness's own evaluation at the checkpoint block. (d) **`stateSequence`, `sourceBlockNumber`, `sourceBlockHash` equal the DBC's current checkpoint fields: `DecisionVerifier` compares only `stateSequence` to the checkpoint, so an unchecked block reference is a gap the ledger does not close** [src: `DecisionVerifier.sol:_checkState`]. (e) `expiresAt` equals the deterministic value of section 4. |
| StateCheckpoint | (a) `sequence == DBC.current.sequence + 1` (or 1). The ledger accepts any larger sequence (`KSSC.sol:153`), so this pin is a validation duty; it blocks the unbounded-sequence poison that needs q=3 colluders. (b) `sourceChainId`, `psc` equal the deployment. (c) The PBC block `sourceBlockNumber` exists, its hash equals `sourceBlockHash`, it is not after the witness's own PBC head, and `sourceBlockNumber >= DBC.current.sourceBlockNumber`. (d) `authEpoch`, `policyVersion`, `keyEpoch` (= 0) and `witnessSetVersion` equal the witness's own reads at that block (**all fields recomputed**; this is the FL-7 / F-24 refusal). (e) **Freshness is semantic, not a block lag:** the snapshot's `authEpoch` and `policyVersion` must equal the values the witness reads at its own PBC head. An older snapshot that lacks a revocation it can already see is refused (stale-view refusal). No numeric lag is invented. (f) `expiresAt` inside the window of section 4. |
| GrantReceipt | (a) the DBC grant exists and is `allowed` (E logic, `witness.py:151-157`), PBC record `status == 1` and `(gid, dataId)` equal. (b) every field recomputed from ledger state; `dbcBlockNumber/Hash` canonical (section 5). |
| GovernanceAction | (a) typed-field rules of A1 section 2 (action in {1,2,3}, root non-zero, admins strictly ascending/non-zero/at most MAX_ADMINS, REMOVE with empty admins). (b) `nonce == Governance.governanceNonce() + 1`. (c) `witnessSetVersion` equals its own. (d) **The TMSC preconditions of A1 section 3 hold now** (ADD: root neither authority nor tombstoned; REMOVE and SET: root is an authority). A certified action that fails a TMSC precondition reverts the whole transaction, leaves the nonce unchanged, and would pin `K` until expiry: the witness must refuse it up front. Agent 1 adds why the check is exact (A1-0094): every TMSC precondition (`isAuthority`, `removedAuthority`) is written only by governance and nonces are strictly sequential, so pre-validation at `nonce == governanceNonce + 1` sees exactly the state at execution; a doomed action cannot reach q = 3 while two honest witnesses pre-validate (f = 1). (e) the witness's **local approval** (below). (f) `expiresAt` inside the window of section 4. |

**Governance approval is a specification gap, not a discovered vulnerability.** The paper says membership changes need consent ("signed challenges from authorities",
Table 2 majorityConsent) but gives no rule for what makes a hospital's witness agree. A1's b1 makes the four witnesses the signers, so something must decide. Proposal for
the experiment: each honest witness holds a TEST-ONLY allow-list of `(action, root, admins)` tuples injected by the runner; it signs a governance action iff the action is on its own
list and passes the checks above; a Byzantine witness signs anything. That models "one hospital's witness decides locally" and makes FL-10 / F-12 / F-29 expressible. It is a
reconstruction choice with a trust consequence: a q=3 coalition of approving hospitals can change authorities, which is exactly what the matrix says quorum authority means.

## 4. Deterministic expiry [prop]

- **AccessDecision:** `expiresAt = min(request.expiresAt, checkpoint.expiresAt)`: a pure function of ledger state. The E term `dbc_now + DECISION_TTL` is dropped under the F profile.
  Check against E bounds: the fixture request TTL is at most 30 s and the decision TTL 30 s (`fixture.ttlSeconds`), so on ledgers that share a clock the dropped term never bound in E.
  That is an argument from fixture values, not a measurement; a runner that skews the two chains can make it bind, and the dropped term is then a behaviour change to state in the F report.
  The ledger accepts any `d.expiresAt <= checkpoint.expiresAt` that is in the future (`DecisionVerifier.sol:_checkState`), including a value above `request.expiresAt` (it checks `now < r.expiresAt` separately, line 74), and the grant expiry is `min(d.expiresAt, r.expiresAt)` (`ACSC.sol:190`). So `min(request, checkpoint)` is **effect-equivalent** to the largest accepted value `checkpoint.expiresAt`: the same grant expiry and the same acceptance window. It is not "the largest acceptable value" (A1-0094 C1); it is the deterministic one among values with the same effect.
- **StateCheckpoint and GovernanceAction:** `expiresAt` is a liveness choice by the proposer, so it cannot be a pure function. The witness accepts it iff
  `obs.timestamp < expiresAt <= obs.timestamp + maxTtl`, with `obs` its own latest-block observation of the **target** ledger and `maxTtl` the ledger's bound
  (`maxCheckpointTtl`, fixture 60 s; `maxGovernanceTtl`, 120 s proposed by A1). The upper bound is conservative: the ledger checks it against the including block's timestamp, which is not earlier than `obs`.
  The proposer should choose **30 s (checkpoint) and 60 s (governance)** after its own observation so that witnesses whose observations differ by up to half the window still agree.
  These two numbers are **proposed defaults, not measured**; they only affect availability. If delivery is slower than the window the proposal is re-issued with a later `expiresAt`:
  the effect value is unchanged, so section 2 allows it (idempotent re-sign). Without this a late proposal would wedge the key until it expired. [model: P2 vs P5]
  **A same-value renewal is permission to sign a new digest for the same effect; it is not permission to extend an `AccessRequest` or an already issued grant** (A3-0058). A decision's `expiresAt` is deterministic and bounded by the request and the checkpoint, so a renewal cannot lengthen it; a checkpoint or governance renewal changes only when that one certificate may still be submitted.
- **GrantReceipt:** no expiry field; the ledger allows late reconciliation (`PSC.sol:reportAttestedOutcome` comment).

## 5. Receipt equivalence [prop]

The PSC checks the receipt's request/grant ids, destination, key epoch, `grantExpiresAt`, set version and signatures, and does **not** check `dbcBlockNumber` or `dbcBlockHash` [src].
In E they are "the DBC head when asked", so two witnesses asked at different times sign different receipts. Rule for the F profile only (the E profile and its pinned bytes stay as they are):

- `dbcBlockNumber/Hash` = the block that contains the unique `GrantIssued(grantId, ...)` log of the KSSC (`KSSC.sol:74`), found by `eth_getLogs` with the grant id topic. Exactly one log, else refuse.
- All other receipt fields come from the grant and the PSC record, as in E. The receipt is then a pure function of ledger state: one `K`, one `V`, one digest.
  Two receipts for one request differ only if a witness deviates; the PSC records one outcome per request, so equivalence means "the same bytes", not "any acceptable receipt".
- A witness that has not yet seen the grant block refuses `NOT_COMMITTED` and the collector retries.
- A receipt carries evidence of DBC authorization only, never of release or delivery (unchanged from E).

## 6. When an earlier digest is dead (re-signing needs this) [prop]

Wall-clock time is **never** used. For each recorded digest the witness takes one fresh observation `obs = (chainId, blockNumber, blockHash, timestamp)` of the **target** ledger's `latest` block
(DBC for decision and checkpoint, PBC for governance and receipt) from its own RPC and requires one of:

| Kind | Dead when | Valid because |
|---|---|---|
| Expiry (all types with `e`) | `obs.timestamp >= e` | every ledger check is `block.timestamp < expiresAt` (`KSSC.sol:148`, `DecisionVerifier.sol`: `ctx.now_ >= d.expiresAt` gives EXPIRED; Governance step 5, A1 section 2); block timestamps do not decrease, so no later block can accept it |
| Overtaken, Checkpoint | `DBC.current.sequence >= sequence` | acceptance needs `sequence > current` (`KSSC.sol:153`), `current.sequence` only grows **if there is no reset (D-e1 yes, D-e2 no)** |
| Overtaken, Governance | `Governance.governanceNonce >= nonce` | step 4 rejects `nonce <= governanceNonce` (A1 section 2) |
| Overtaken, Decision | `DBC.current.sequence > stateSequence`, or (ALLOW only) a grant exists for the request | `DecisionVerifier` requires `stateSequence == current.sequence`; `KSSC.requestData` rejects a second grant. A DENY decision consumes nothing (`ACSC.sol:185-187`), so only the sequence or expiry predicate kills it; re-submitting a DENY only logs again (A1-0094) |
| Executed, Receipt | PSC request `status == OUTCOME_RECORDED` | one outcome per request |

Numeric observation parameters (the bounds A3-0056/0057 asked for), all **proposed**:

- **Confirmation depth k = 0**: observation is the `latest` block. This is only sound because core F assumes **safe ledgers** (a single local Anvil per chain, no reorganisation) **whose block timestamps are non-decreasing on the live chain**. Forge's `vm.warp` in unit tests is not a ledger and is outside this assumption (A1-0094 C2).
  With a ledger that can reorganise, `latest - k` replaces `latest` and k is its finality depth; k is then a ledger property, not a witness choice.
- **Staleness is safe**: an observation older than the real head only delays re-signing. [model: P5, observations may lag]
- **No clock-skew bound is needed for safety.** Each type's death uses only its own target ledger's timestamps, compared with a number signed into the digest by that same ledger's clock domain.
  Skew between the PBC and DBC clocks (E measured uncorrected skew) changes availability (a request can look expired on one chain), not agreement.
- **A mined block is required.** `Chain.now()` in E returns `max(latest, pending)` (`chain.py:125`), which is right for refusing (conservative) and **wrong for declaring death**: a pending timestamp
  is not a committed block. On an idle auto-mining Anvil `latest` stands still (E measured this, A2-0025), so no death is observable and the key stays pinned: a **liveness** stall, never a safety loss.
  The runner must provide a block producer (Anvil `--block-time`, or explicit mining) or accept the stall as the F-29 measurement.
- **Tripwire** [prop]: the witness stores its last observation per chain and refuses to sign (state FAULTED until an operator clears it) when `latest.number` or `latest.timestamp` decreases or the stored
  hash for the stored number changed. This turns a violated monotone-clock / no-reorg assumption into a refusal instead of silent unsafety. It cannot detect a violation that never shows up in its own observations. The FAULTED response (`ADAPTER_UNAVAILABLE` with reason `WITNESS_FAULTED`), its persistence and the operator clear that keeps all signing history and leaves the interval **outside** the safe-ledger assumption are defined in `SUCCESSOR-WIRE.md` section 4.

## 7. Safety argument and what the bounded check shows

Claim (agreement over simultaneously live values): with n = 4, q = 3, at most one Byzantine witness, no two formed certificates with different effect values for one `K` are live at the same ledger time.
Argument [prop]: two certificates of three signers each from four share at least two signers, at least one of them honest. That honest signer signed `V1` for `K`; it signs `V2 != V1` only after observing every
earlier digest dead. A digest that is dead stays dead (monotone clock, no reset), so the first certificate was never live later; reversing the order gives the same result. The argument fails exactly where the assumptions fail:
two Byzantine witnesses, q = 2, a wiped durable record, or a ledger clock that moves back. The bounded model checks the argument in an abstraction and finds each of those failures [model]:

| Rule | Result (`evidence/MODEL-RUNS.md`) |
|---|---|
| no persistence (N0) | violated: positive control |
| permanent single-signing (N1) | safe, but a **stall** is reachable (17820 of 25024 prefix states cannot recover): matches the F-29 concern |
| wall-clock re-signing with skew 1 (N2) | violated: why local wall-clock expiry alone is unsafe |
| ledger-observed death (R-new) | safe at f = 0 and f = 1; no stall reachable (25024 of 25024 recover) |
| R-new at f = 2, at q = 2, with a wiped durable record, with one clock regression | violated: F-17, F-18, F-27, and the monotone-clock assumption |

The bounded check shares the rule with this document only; agent 3's TLC model must state the same lifetime rule (A3-0055). **Both are design checks; neither is the implementation.**
The first run of the check mis-modelled rollback (prediction P9 failed); that defect, its fix and the unchanged other nine verdicts are recorded in `evidence/MODEL-RUNS.md`.

**What the bounded check does not check** (agent 3's review, which I confirm): it models expiry-death only, not the state predicates (overtaken sequence or nonce, grant exists, outcome recorded); it has no receipt lifetime and no governance preconditions; it replaces independent validation by adversarial proposals of any value; and its recovery check asks whether, after every old digest expired, a fresh digest can still be signed by three honest witnesses. That is an existence check, **not a temporal liveness proof**. The C-F1 model should additionally distinguish emitted signatures from durable records, expiry-death from state-overtaking, certificates from accepted effects, and independent validation from the adversarial-value abstraction.

## 8. Collector (pool) rules: filtering and continued collection [prop]

The collector holds no witness key and signs nothing. For one proposal it sends the same proposal to all four witnesses and, per reply:

1. Parse strictly. A reply whose struct differs from the proposal is a **dissent**: kept as evidence, never counted.
2. Recompute the digest itself, recover the signer, require `signer ==` the replying witness's configured address and membership in the set. Anything else is an **invalid reply**: recorded (witness id, reason), not counted, **not forwarded**.
3. Deduplicate by signer address (first valid reply wins; duplicates are recorded, they never raise the count).
4. Continue collecting after an invalid reply until q = 3 distinct valid signers or the deadline.
5. Submit exactly q signatures sorted by signer address (`QuorumLib` requires it); never alter the signed value.
6. At the deadline report a classified timeout (reason `QUORUM_UNAVAILABLE` on the existing code `ADAPTER_UNAVAILABLE`; deliberately **not** `INSUFFICIENT_QUORUM`, which is the ledger's rejection of a submitted certificate) with the per-witness outcomes (signed, refused with its code, invalid, silent, dissent, duplicate-only). Never report a denial for a missing quorum. Exact envelopes: `SUCCESSOR-WIRE.md` sections 1-2.

7. **Retain the proposal (revision 5).** Within one collection derive the proposal **once**, keep its bytes, resend it verbatim on a retry to the witnesses that have not returned `signed`, and never re-derive it from a newer head. A witness that already signed that exact digest returns its stored signature (the idempotent re-sign of section 2).
8. **Recorded value on a pinned refusal (StateCheckpoint only).** A witness that refuses a checkpoint proposal with reason `CONFLICT_PINNED` returns the checkpoint it recorded for that sequence (the digest with the latest `expiresAt` it signed) together with **the signature it already issued** for it. It is public data and needs no new signing. The pool counts a report only if it came from that witness over its supervised channel, is for the proposal's sequence, and its signature recovers, over the digest the pool computes itself under the HMBCState domain, to that witness's address.
9. **Adoption (revision 6: R4 and R5).** (a) **Inconsistent reporter:** a witness whose valid reports in the snapshot contain two or more **different** values is excluded from adoption (repeats of the same value are not inconsistency); its values and signatures are kept as evidence. (b) **Rule:** among the consistent witnesses, adopt iff **exactly one value** has at least **two distinct** witnesses reporting it; with none, or with two or more such values, adopt nothing and keep collecting until the deadline. (c) **Decision snapshot:** the snapshot closes at the first of "all four witnesses replied" or "the 5 s per-witness reply timeout elapsed"; the decision is taken **once**, on the snapshot only. Reports arriving later are **late reports**: evidence only, they neither cancel nor create an adoption. The same reports can therefore adopt different values in different arrival orders; each adopted value was recorded by an honest witness (f <= 1), so either is safe. Rule, projection and policy are pinned by `vectors/pool_adoption.py` and `vectors/test_pool_adoption.py` (28 expectations, exhaustive over 3456 assignments for one Byzantine witness sending any subset of reports, 10 of 10 mutants detected); the wire evidence is checked against the reference's own classification by `vectors/check_wire_examples.py` (18 of 18 corruptions detected).
10. **Re-proposal.** After adopting, re-propose the adopted value **verbatim with its recorded `expiresAt`** to every witness that has not signed it, in a second round with its own 5 s per-witness timeout **inside the original collection deadline** min(10 s, remaining - 2 s); replies after that deadline are ignored and nothing is extended. Each witness validates it independently (section 3) and applies the conflict rule (section 2), both unchanged: an expired value is refused `EXPIRED`, a stale one `STALE_STATE`, a value that conflicts with a live record `CONFLICT_PINNED`. At most once per collection; skipped when the adopted value has 2 s or less of validity left; no new proposal window; no signature or death bypass.

Scope and argument for items 7 to 10 (wire shape and examples: `SUCCESSOR-WIRE.md` section 2). Two valid checkpoint values can exist for one sequence **inside** the assumptions: any PBC block mined between two proposals changes `sourceBlockNumber/Hash` and leaves the epochs equal. A collection restarted by deriving a newer head is then refused `CONFLICT_PINNED` by every witness that already signed the earlier value until that digest dies (an availability cost, never a safety loss). Only checkpoints can pin themselves this way: a decision is a pure function of the request and the current checkpoint (an advanced checkpoint kills the old decision by the state predicate of section 6), a receipt of the `GrantIssued` block, and a governance action is supplied whole by the caller. **Safety:** the pool is untrusted and keyless, the witness rule is untouched, and no witness signs a value it did not validate itself, so adoption only converges the pool onto a value honest witnesses already hold; with at most one Byzantine witness an adopted value was recorded, and independently validated, by an honest witness (exhaustive in the abstraction above, which models the adoption decision only, not signatures or the rest of the protocol; the exclusion of inconsistent reporters only removes adoption options, so it cannot weaken this). With two Byzantine witnesses agreeing on a fake value the fake value is adopted (control A4 of the vectors); honest witnesses still validate it, so the cost is availability. **Liveness is a design argument and is untested:** the collection completes if three honest witnesses can validate the adopted value; if the honest witnesses split, nothing is adopted and the sequence stays pinned until the earlier digests die, at most the 60 s checkpoint maximum.

**What adoption cannot do, and the two schedules to pre-register (A3-0062).** Adoption never erases a live signature. Suppose witnesses 0 and 1 signed value A in an earlier collection and witnesses 2 and 3 never saw a proposal for this sequence. A **restarted** pool has lost its retained proposal and derives a newer value B. If it delivers B to all four witnesses at once, witnesses 2 and 3 are unpinned, **validate B and sign it**; witnesses 0 and 1 then report A. The snapshot adopts A, but re-proposing A to witnesses 2 and 3 is refused `CONFLICT_PINNED`: A has two signatures, B has two, and nothing reaches q = 3 until both digests are observed dead. That is an availability cost, bounded by the checkpoint lifetime (at most 60 s), and **not** a safety failure (no two q = 3 certificates exist). The recovery therefore depends on delivery order, and a generic concurrent broadcast must not be credited with it. Two controlled schedules, with their ordering stated:
 - **Branch (a), unpinned positive.** Setup: witnesses 0 and 1 hold stored signatures S0 and S1 for A; witnesses 2 and 3 are unpinned. A restarted pool derives B. A TEST-ONLY **delivery hold** in the pool transport (the H6 family, outside `adapter.json`) delivers B to witnesses 0 and 1 and **holds** the writes to witnesses 2 and 3 until the snapshot closes. Witnesses 0 and 1 refuse `CONFLICT_PINNED` and report A with S0 and S1. The snapshot closes at the reply timeout with reports from 0 and 1 only, so A is adopted; the held writes of B are **cancelled and never sent**; the pool sends A verbatim to witnesses 2 and 3 (and to 0 and 1, which return S0 and S1 unchanged). Witnesses 2 and 3 validate A, which is still live, and sign it. Certificate: S0, S1 and one new signature (S2), exactly three; **stored** signatures S0, S1; **newly emitted** S2 and S3 (witness 3's is not needed). Late reports: none.
 - **Branch (b), pinned availability.** The same setup, but B is delivered to all four witnesses at once with no hold. Witnesses 2 and 3 sign B; witnesses 0 and 1 report A; the snapshot adopts A; A is re-proposed and refused by 2 and 3. Outcome: `QUORUM_UNAVAILABLE`, nothing submitted, no certificate for either value, the sequence released only after both digests are observed dead. **Expected, not a defect.**
 Both branches record every proposal, every delivery and cancellation, every reply, and every stored and newly emitted signature. The actual schedule, the hold placement and the timings stay unmeasured and must be frozen before execution.

**Rejected alternative, offered for later.** A **probe-first** step (a read-only query for the recorded value before any signing request) would let a restarted pool learn A before delivering B and would make branch (a) the default. It needs a new read-only witness operation and a successor-schema entry, and its benefit is availability only; I have not specified it and do not ask for it now.

Why: one invalid signature in the array fails the whole certificate (section 0), so a collector without these rules turns one Byzantine reply into a denial of service (FL-5, F-22). The ledger-side negative
controls (FL-4 duplicate, FL-5 unknown signer, F-23 unsorted) need the runner to craft raw certificates from per-witness signatures; the witness service therefore returns one signature per call and the runner assembles.

## 9. Open points that need a decision, not an assumption

| # | Point | Owner (and agent 3's recommendation, A3-0058: a recommendation, not an ACK) |
|---|---|---|
| O1 | Governance approval policy (section 3). The allow-list is a modelling choice. | agent 3 with the human, since it defines "who decides". **Recommended:** a TEST-ONLY per-witness allowed-action fixture plus the structural and TMSC checks; every witness's fixture and dissent is published. This is a bounded synthetic experiment: it chooses no real hospital's policy and does not reconstruct the paper's consent algorithm, so no human policy decision is needed for it |
| O2 | D-e2 (checkpoint reset). Reset breaks the Checkpoint "overtaken" predicate (a lower sequence becomes acceptable again). Under e2 only the expiry predicate stays valid and K needs a reset-generation in its key. Agent 2 can sign a reset action under the single-signing rule only after that rewrite; the answer to A1-0088 is **conditional yes**. | agent 3 chooses; agent 1 then specifies the generation field **Recommended:** retain e1 (no reset) as the core and defer e2 with its generation migration; overtaking is usable only with monotone, non-reset state. |
| O3 | D-d2 (user signature on the DBC). The `signed` object that `Relay.deliver(signed, ...)` already receives is what `prepare_request` returned and contains the user's signature (`relay.py:46` uses it for the PBC call; `deliver` does not forward it), so carrying it to the DBC is a one-argument change on the relay side; witnesses do not need it. Answer to A1-0088: **yes, no protocol obstacle**. It matters only in the f = 2 boundary run. | agent 3 **Recommended:** retain d1 and label the f = 2 request-authenticity residual; defer d2. |
| O4 | The F-profile receipt canonicalisation (section 5) and the dropped decision TTL term (section 4) change witness bytes under repaired-f only. | agents 1 and 3 **Recommended:** carry `min(request, checkpoint)` and the unique `GrantIssued` block into repaired-f only, preserve E pins, and require three-signer byte-equality controls. |
| O5 | Numeric defaults of section 4 (30 s / 60 s) and k = 0. | agent 3, in the matrix' numeric plan **Recommended:** k = 0 under safe no-reorg ledgers, proposer windows 30 s (checkpoint) and 60 s (governance), bounds 60 s and 120 s, MAX_ADMINS 8, as explicit proposed values; finite collection and inclusion deadlines, block cadence and measured delivery bounds stay unresolved. |
| O6 | Whether the pool lives inside the adapter process or the four witnesses are separate OS processes (isolation differs). See `INVENTORY.md` section 5. | agent 3 **Recommended:** four supervised witness processes with separate state and locks under one adapter command; same-user, same-host and public-synthetic-key correlation stay explicit. |

## 10. Not claimed

No liveness under arbitrary delay; no validation-code correctness (that is what the future tests are for); no cryptographic or ABE claim; no independence of hosts; no real-network
finality; no statement about the ledger code beyond the lines cited; nothing about gate F. All scenario rows stay NOT_RUN.
