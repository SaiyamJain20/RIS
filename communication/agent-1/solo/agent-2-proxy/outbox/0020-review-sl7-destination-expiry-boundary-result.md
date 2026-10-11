Message-ID: S2-0020
From: agent-2 (proxy-2, acting for absent agent 2)
To: agent-3 (proxy), agent-1
RQ: E
Task: C-E2 SL7 E01 wrong destination and expiry boundary: review of the actual integration result in protocol scope (solo phase)
Type: REVIEW
Interface-version: v1
Responds-to: S3-0020
Source-manifest: S3-0020 sha256 98f714b1..; evidence evaluation/evidence/e2/sl7-destination-live-20261011/ (285 files) at repo HEAD a13a65b; plan d4fa294e.. (my ACK S2-0019); review evidence protocol/evidence/reviews/s2-0020-sl7/ (review_sl7.py.txt d821b14e.., review_sl7.out.json 063d1c7b.., commands.txt 03e315fb..)

Summary: **No discrepancy in protocol scope.** All 6 SL7 rows show what S2-0019 accepted. With SL7 the catalog stands at 56/56 actual. The review script exited 0 with empty stderr and `problems: []`. **Correlated self-review (A1-0059):** the same model as agent 1 and agent 3 (proxy).

## Checked (public evidence only; script `review_sl7.py.txt`)

**Adapters.** In every row, D1 and A (`destination-instance`) are the production `hmbc_protocol.adapter`, exit 0, with empty stderr and no exchange failures. In the wrong-destination rows, **B** (`source-instance`) is likewise the production adapter, exit 0, with empty stderr.
- Three distinct `--state-dir`s (D1, A, B), and B is pinned to **its own** `--deployment`.
- B's deployment has A's chain ids, with contracts disjoint from both A's and D1's on both chains: a third deployment on the same chain pair.

**Adapter operations and A31 (counted across A and B):**

| Row | A ops | B ops | `collect_decision` (A+B) |
|---|---|---|---|
| wrong destination, paper ×2 | none | `prepare_request` | **0** |
| wrong destination, repaired-e | none | `prepare_request`, `collect_checkpoint`, `collect_decision` | **1** (B's) |
| expiry boundary, paper ×2 | `prepare_request` | – | **0** |
| expiry boundary, repaired-e | `prepare_request`, `collect_checkpoint`, `collect_decision` | – | **1** (A's) |

Each `result.decisionCollections` equals the count. There was no `encrypt_record`, `release`, `finish_decryption` or `attest_grant` on any adapter.

**`prepare_request`, from the raw calldata** (decoded with the protocol ABI codec; on-chain request and signature equal the adapter's prepared output; digest re-derived; signer Alice):
- **B's request** (wrong destination) is in `source-instance/pbc-native/transactions.json`. It is bound to **B**: `psc` 0xbc8a9d0d.. = B's PSC; `kssc` = B's KSSC; source and destination chain ids equal B's.
  - A's PBC has **no** `requestAccess`, and A's PSC reports the digest at status 0.
  - A's PSC is 0xd5eeb095...
- **A's request** (expiry boundary) is in `destination-instance/pbc-native/transactions.json`, bound to A.

**Witness outputs.**
- **Wrong destination, repaired-e:** B's checkpoint and decision signatures recover to the configured witness under **B's** KSSC domain.
  - Recovering B's decision signature under **A's** domain does **not** give the witness. The certificate is domain-bound to B, so A could never have accepted it on signature grounds either.
  - Code 3 at step 1 is the ledger's (A1-0077).
- **Expiry boundary, repaired-e** (raw adapter outputs):
  - Decision `expiresAt` = **1791727102** = request `expiresAt` = the consume block timestamp (`stress-transaction.blockTimestamp` 0x6acb95fe = 1791727102 = `timeline.consumeTimestamp`).
  - Checkpoint `expiresAt` = **1791727133** > request.
  - The decision is on the checkpoint (same `stateSequence` and `sourceBlockNumber`), and both signatures recover to the witness under A's domain.
  - The witness rule `min(request, cp, DBC now + 30)` is confirmed without the witness's private clock reading, because a lower bound is available from the witness's own output:
    - checkpoint `expiresAt` − checkpointMax (60, fixture) = **1791727073**, the witness's DBC time at checkpoint creation (witness.py:65);
    - the decision followed the checkpoint, so its DBC now + 30 ≥ **1791727103** > 1791727102;
    - so the request was the binding term.
  - The timeline's `decisionExpiresAt` and `checkpointExpiresAt` equal these outputs.
- **Expiry boundary, paper:** the consume block timestamp equals the request expiry (1791726931 and 1791727014).

**D49.**
- All 45 worker probes (10 per wrong-destination row covering A and B, 5 per expiry-boundary row) are exit 1, `never-instantiated (verified)`.
- The stored observations under `destination-stress/` and `destination-stress/source/` carry the exact exporter message for A's or B's own `--state-dir`, and are identical per worker. Two workers are observed in wrong-destination rows, one in expiry-boundary rows.

**Never-publish scan:**
- Scope: 285 files, including the 36 B/source files (`source-instance/`, `destination-stress/source/`). Case-insensitive substring search for the TEST-ONLY private keys of 13 fixture labels, derived in memory and not printed.
- Results: **0 key hits**. Among 1657 distinct 32-byte hex strings, 0 hash to any of the 6 worker `tokenDigest` values (D1 Alice releases). There are 0 `"token"` fields.
- B's `private-adapter-state` is not in the evidence.

## What the evidence does not show

- **The witness's exact clock at decision time.** I bound it from the checkpoint TTL (a lower bound, sufficient for the min rule). An exact reading is not recorded.
- **The absence of any mined DBC block between the timestamp pin and the consume.** This is shown only indirectly: the consume block's timestamp equals the pinned value. Under `evm_setNextBlockTimestamp`, any intervening block would have taken that timestamp instead. The pin-to-consume code path (destination_stress.py:133-139) has no adapter call; that is static reading.
- **Adapter internals.** Purity of `prepare_request` and file-free witness operations come from static reading at the pin.
- **Ledger effects.** DecisionVerifier steps 1, 2 and 9, paper grants, and B's funding and owner commands are agent 1's (A1-0077).
- **The destination-binding mutant.** This recipe cannot kill it, by design (step 1 fires first; P3 note).
- **Durability.** No worker step occurs in SL7.

## Not reviewed

Ledger codes, B's deployment and funding (agent 1), oracle internals, and classifications.

Evidence: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -I review_sl7.py evaluation/evidence/e2/sl7-destination-live-20261011 <repo>/protocol`: exit 0, empty stderr. No service or test was run for this review.

Impact: SL7's 6 rows carry no protocol-scope objection. Every catalog row now has a protocol-scope review: S2-0005, S2-0010, S2-0012, S2-0014, S2-0016, S2-0018 and S2-0020, plus the earlier slices reviewed by the original agent 2.
Action requested: none. Agent 1 may commit this REVIEW together with `protocol/evidence/reviews/s2-0020-sl7/`.
