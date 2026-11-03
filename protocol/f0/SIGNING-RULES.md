# F0 witness signing rules (R6) — proposal for review

Author: agent 2. Date: 2026-11-03. Phase: F0 planning. **PROPOSAL, NOT ACKED, NOT IMPLEMENTED, NOT FROZEN.**
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
     record to an append-only `superseded` table (with the death evidence: chain, block number, block hash, block timestamp) and insert the new one. Otherwise refuse `CONFLICT`.
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
| GovernanceAction | (a) typed-field rules of A1 section 2 (action in {1,2,3}, root non-zero, admins strictly ascending/non-zero/at most MAX_ADMINS, REMOVE with empty admins). (b) `nonce == Governance.governanceNonce() + 1`. (c) `witnessSetVersion` equals its own. (d) **The TMSC preconditions of A1 section 3 hold now** (ADD: root neither authority nor tombstoned; REMOVE and SET: root is an authority). A certified action that fails a TMSC precondition reverts the whole transaction, leaves the nonce unchanged, and would pin `K` until expiry: the witness must refuse it up front. (e) the witness's **local approval** (below). (f) `expiresAt` inside the window of section 4. |

**Governance approval is a specification gap, not a discovered vulnerability.** The paper says membership changes need consent ("signed challenges from authorities",
Table 2 majorityConsent) but gives no rule for what makes a hospital's witness agree. A1's b1 makes the four witnesses the signers, so something must decide. Proposal for
the experiment: each honest witness holds a TEST-ONLY allow-list of `(action, root, admins)` tuples injected by the runner; it signs a governance action iff the action is on its own
list and passes the checks above; a Byzantine witness signs anything. That models "one hospital's witness decides locally" and makes FL-10 / F-12 / F-29 expressible. It is a
reconstruction choice with a trust consequence: a q=3 coalition of approving hospitals can change authorities, which is exactly what the matrix says quorum authority means.

## 4. Deterministic expiry [prop]

- **AccessDecision:** `expiresAt = min(request.expiresAt, checkpoint.expiresAt)`: a pure function of ledger state. The E term `dbc_now + DECISION_TTL` is dropped under the F profile.
  Check against E bounds: the fixture request TTL is at most 30 s and the decision TTL 30 s (`fixture.ttlSeconds`), so on ledgers that share a clock the dropped term never bound in E.
  That is an argument from fixture values, not a measurement; a runner that skews the two chains can make it bind, and the dropped term is then a behaviour change to state in the F report.
  The ledger accepts any `expiresAt <= checkpoint.expiresAt` that is in the future (`DecisionVerifier.sol:_checkState`), so the maximum is the largest acceptable value, never a looser one.
- **StateCheckpoint and GovernanceAction:** `expiresAt` is a liveness choice by the proposer, so it cannot be a pure function. The witness accepts it iff
  `obs.timestamp < expiresAt <= obs.timestamp + maxTtl`, with `obs` its own latest-block observation of the **target** ledger and `maxTtl` the ledger's bound
  (`maxCheckpointTtl`, fixture 60 s; `maxGovernanceTtl`, 120 s proposed by A1). The upper bound is conservative: the ledger checks it against the including block's timestamp, which is not earlier than `obs`.
  The proposer should choose **30 s (checkpoint) and 60 s (governance)** after its own observation so that witnesses whose observations differ by up to half the window still agree.
  These two numbers are **proposed defaults, not measured**; they only affect availability. If delivery is slower than the window the proposal is re-issued with a later `expiresAt`:
  the effect value is unchanged, so section 2 allows it (idempotent re-sign). Without this a late proposal would wedge the key until it expired. [model: P2 vs P5]
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
| Overtaken, Decision | `DBC.current.sequence > stateSequence`, or a grant exists for the request | `DecisionVerifier` requires `stateSequence == current.sequence`; `KSSC.requestData` rejects a second grant |
| Executed, Receipt | PSC request `status == OUTCOME_RECORDED` | one outcome per request |

Numeric observation parameters (the bounds A3-0056/0057 asked for), all **proposed**:

- **Confirmation depth k = 0**: observation is the `latest` block. This is only sound because core F assumes **safe ledgers** (a single local Anvil per chain, no reorganisation).
  With a ledger that can reorganise, `latest - k` replaces `latest` and k is its finality depth; k is then a ledger property, not a witness choice.
- **Staleness is safe**: an observation older than the real head only delays re-signing. [model: P5, observations may lag]
- **No clock-skew bound is needed for safety.** Each type's death uses only its own target ledger's timestamps, compared with a number signed into the digest by that same ledger's clock domain.
  Skew between the PBC and DBC clocks (E measured uncorrected skew) changes availability (a request can look expired on one chain), not agreement.
- **A mined block is required.** `Chain.now()` in E returns `max(latest, pending)` (`chain.py:125`), which is right for refusing (conservative) and **wrong for declaring death**: a pending timestamp
  is not a committed block. On an idle auto-mining Anvil `latest` stands still (E measured this, A2-0025), so no death is observable and the key stays pinned: a **liveness** stall, never a safety loss.
  The runner must provide a block producer (Anvil `--block-time`, or explicit mining) or accept the stall as the F-29 measurement.
- **Tripwire** [prop]: the witness stores its last observation per chain and refuses to sign (state FAULTED until an operator clears it) when `latest.number` or `latest.timestamp` decreases or the stored
  hash for the stored number changed. This turns a violated monotone-clock / no-reorg assumption into a refusal instead of silent unsafety. It cannot detect a violation that never shows up in its own observations.

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

## 8. Collector (pool) rules: filtering and continued collection [prop]

The collector holds no witness key and signs nothing. For one proposal it sends the same proposal to all four witnesses and, per reply:

1. Parse strictly. A reply whose struct differs from the proposal is a **dissent**: kept as evidence, never counted.
2. Recompute the digest itself, recover the signer, require `signer ==` the replying witness's configured address and membership in the set. Anything else is an **invalid reply**: recorded (witness id, reason), not counted, **not forwarded**.
3. Deduplicate by signer address (first valid reply wins; duplicates are recorded, they never raise the count).
4. Continue collecting after an invalid reply until q = 3 distinct valid signers or the deadline.
5. Submit exactly q signatures sorted by signer address (`QuorumLib` requires it); never alter the signed value.
6. At the deadline report a classified timeout `QUORUM_UNAVAILABLE` with the per-witness outcomes (valid, refusal with its code, invalid, silent). Never report a denial for a missing quorum.

Why: one invalid signature in the array fails the whole certificate (section 0), so a collector without these rules turns one Byzantine reply into a denial of service (FL-5, F-22). The ledger-side negative
controls (FL-4 duplicate, FL-5 unknown signer, F-23 unsorted) need the runner to craft raw certificates from per-witness signatures; the witness service therefore returns one signature per call and the runner assembles.

## 9. Open points that need a decision, not an assumption

| # | Point | Owner |
|---|---|---|
| O1 | Governance approval policy (section 3). The allow-list is a modelling choice. | agent 3 with the human, since it defines "who decides" |
| O2 | D-e2 (checkpoint reset). Reset breaks the Checkpoint "overtaken" predicate (a lower sequence becomes acceptable again). Under e2 only the expiry predicate stays valid and K needs a reset-generation in its key. Agent 2 can sign a reset action under the single-signing rule only after that rewrite; the answer to A1-0088 is **conditional yes**. | agent 3 chooses; agent 1 then specifies the generation field |
| O3 | D-d2 (user signature on the DBC). The `signed` object that `Relay.deliver(signed, ...)` already receives is what `prepare_request` returned and contains the user's signature (`relay.py:46` uses it for the PBC call; `deliver` does not forward it), so carrying it to the DBC is a one-argument change on the relay side; witnesses do not need it. Answer to A1-0088: **yes, no protocol obstacle**. It matters only in the f = 2 boundary run. | agent 3 |
| O4 | The F-profile receipt canonicalisation (section 5) and the dropped decision TTL term (section 4) change witness bytes under repaired-f only. | agents 1 and 3 |
| O5 | Numeric defaults of section 4 (30 s / 60 s) and k = 0. | agent 3, in the matrix' numeric plan |
| O6 | Whether the pool lives inside the adapter process or the four witnesses are separate OS processes (isolation differs). See `INVENTORY.md` section 5. | agent 3 |

## 10. Not claimed

No liveness under arbitrary delay; no validation-code correctness (that is what the future tests are for); no cryptographic or ABE claim; no independence of hosts; no real-network
finality; no statement about the ledger code beyond the lines cited; nothing about gate F. All scenario rows stay NOT_RUN.
