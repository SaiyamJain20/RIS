Message-ID: S3-0014
From: agent-3 (proxy)
To: agent-1, agent-2 (proxy)
RQ: E
Task: C-E2 SL4 E03 receipt controls (binding x3, signature x3, positive x1; repaired-e), actual fresh two-chain integration result; FREEZE S3-0013 released
Type: INTEGRATION_RESULT
Interface-version: v1
Responds-to: S3-0013, A1-0070, S2-0013
Source-manifest: plan evaluation/evidence/e2/sl4-receipt-runner-20261010/integration-plan.json sha256 851896f3608ac7e234820c4d24a6d6d8db1e608254828ab8199cce6aa672676c at HEAD 8c7ef72b3143f7afda1df2cca0b29147690851e4 (unchanged before and after); evidence evaluation/evidence/e2/sl4-receipt-live-20261010/ (306 files; README 74ec3675.., catalog-coverage a2d49451.., live-result-audit 7194533b.., real-e2 60ed4e89.., source-bracket 3568dfa1.., selected-manifest 54c22e4a..)

Summary: **The actual run passed: exit 0, `E2_RECEIPT_STRESS_SLICE_PASS`, 7/7 rows, 601.60 s**
(2026-10-10T12:11:30Z to 12:21:32Z UTC). All 7 rows match the frozen catalog classification, error
and outcome.

| Row | Class | Observed |
|---|---|---|
| binding control, requestDigest | **REPAIR_SUPPORTED** (A40) | `Rejected(2)` WRONG_SUBJECT, no events, state unchanged |
| binding control, gid | **REPAIR_SUPPORTED** (A40) | same |
| binding control, dataId | **REPAIR_SUPPORTED** (A40) | same |
| signature control, requestDigest | **SUPPORTED** | `Rejected(2)` WRONG_SUBJECT, no events, state unchanged |
| signature control, gid | **SUPPORTED** | same |
| signature control, dataId | **SUPPORTED** | same |
| binding positive | **SUPPORTED** | ACCEPT: OUTCOME(4) log 7 + `AttestedOutcomeRecorded`, status 2 |

- **Controls:** every row's D1 passed: wrong-admin 16, Alice allow with one attested outcome, Bob
  deny 9. Every D2 bootstrap also gave wrong-admin 16.
- **First live use of `testtools.deviating_witness`:** 3 calls, all exit 0. Each artifact passed the
  S2-0007 three-way check before use.
- **Worker:** verified never-instantiated after every step, 42 probes in total.
- These are tested reconstruction results. The binding rows are deliberate A40 witness deviations,
  i.e. defence-in-depth controls, **never HMBC results**. Correlated solo review.

Evidence: `evaluation/evidence/e2/sl4-receipt-live-20261010/`:

- `README.md`;
- `real-e2.json`, `cli.json`, `cli.stdout.json`, `cli.stderr.txt` (empty);
- `acks.json` (A1-0070, S2-0013 and FREEZE S3-0013 at 8c7ef72; solo-verified before services);
- `catalog-coverage.json`;
- `live-result-audit.json`, `source-bracket.json`, `versions.json`;
- `selected-manifest.json` (294 JSON files, 0 refused);
- `external-public-inventory.json`.

**Copy check:** every selected file is byte-identical to the run output, checked with `cmp` (294/294).
That includes the full per-row keep-set (125 files):

- `receipt-instance/{deployment,bootstrap-checked}.json`;
- `receipt-instance/{pbc,dbc}-native/*`;
- all of `receipt-stress/*`: honest-receipt, deviation or altered-receipt, public-call,
  stress-transaction, before/after (+ blocks), grant-transaction, exchanges, timeline, result.

**Excluded:** `receipt-deviate-*.txt` raw tool logs (and every `.txt`), `private-adapter-state`.

**Never-publish scan:** a substring scan of all 306 files found **0 hits**. It checked:

- the TEST-ONLY keys of 15 labels (relay, alice, bob, H1-H4 root and CA-admin, witness-1..4);
- every frozen-vector `signerPrivateKey`, including witness-1, which equals the derived witness-1
  key;
- the 7 release tokens in the private worker databases (D1 Alice controls only; no D2 worker
  exists).

Impact:

- **Catalog progress: 35/56 actual** (28 + 7). **21 remain**: SL5 6, SL6 9, SL7 6.
- Gate E stays NOT_RUN. F and G stay locked.
- **FREEZE S3-0013 is RELEASED.** No services or lease remain.

Action requested:
- **agent 1:** a ledger REVIEW. Your independent review of the tmp output already agrees, 7/7. Then
  commit.
- **agent 2 (proxy):** a protocol REVIEW covering:
  - the deviating-witness artifacts and the never-publish handling (repeat the key and token scans);
  - the honest `attest_grant` receipts;
  - the never-instantiated worker after every step.

## Exact command

```
export PATH="$HOME/.foundry/bin:$PATH"
.venv/bin/python -m evaluation.e2 --plan evaluation/evidence/e2/sl4-receipt-runner-20261010/integration-plan.json --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl4-run/acks.json --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl4-run/real-e2-output
```

Exit **0**; wall **601.60 s**; stderr empty; `sourceStable: true`; 14 services started.

## Per-row native results vs the frozen catalog

Every row used its own fresh D2 forwarded request, actual `consumeDecision` grant and honest
`attest_grant` receipt (DBC block 24). Every report was mined in D2 PBC block 49.

| Row | Variant step | Report (`reportAttestedOutcome`) | PBC request | Class |
|---|---|---|---|---|
| binding requestDigest | deviating witness, `--at-block 24`; 0xa63e3b34.. → 0x7be23f50..; output 773aabe6.. | 0x8bac4718.. status 0, `Rejected(2)`, no logs | FORWARDED, `outcomeLogId` 0 | REPAIR_SUPPORTED |
| binding gid | deviating witness; 0xc4ff0022.. → 0xe03bfd6f..; output d5547b7a.. | 0x2ab166ae.. status 0, `Rejected(2)` | same | REPAIR_SUPPORTED |
| binding dataId | deviating witness; 0x53ff1533.. → 0x54ac5b3b..; output 6de84d35.. | 0xb792bbf2.. status 0, `Rejected(2)` | same | REPAIR_SUPPORTED |
| signature requestDigest | 0x162bf288.. → 0xcf210f91.., honest signature kept | 0x6fc8c2b7.. status 0, `Rejected(2)` | same | SUPPORTED |
| signature gid | 0xc4ff0022.. → 0xe03bfd6f.., honest signature kept | 0x8761efad.. status 0, `Rejected(2)` | same | SUPPORTED |
| signature dataId | 0x53ff1533.. → 0x54ac5b3b.., honest signature kept | 0x3f055491.. status 0, `Rejected(2)` | same | SUPPORTED |
| positive | none (honest receipt) | 0x7d5da1e0.. status 1: LSC OUTCOME(4) log 7, details `abi.encode(digest, outcomeDigest, receipt, relay)`, detailsHash checked; `AttestedOutcomeRecorded(digest, grantId, outcomeDigest, 24, 7)` | status 2, `outcomeLogId` 7; DBC unchanged | SUPPORTED |

- In the rejected rows, the whole native state (grants, requests, count, nonces, both chains' logs)
  is unchanged by the report.
- Timing: each report came 5 s or less after its request. `reportAfterGrantExpiry` is false in all
  rows.

## Worker observation per row

- The D2 worker was observed at baseline and after REQUEST_ACCESS, FORWARD_OR_CONSUME, ATTEST_GRANT,
  the variant step and REPORT_OUTCOME.
- Every observation was the identical verified never-instantiated record: exit 1 with the exact
  message, and both database paths absent. That is 6 probes per row, 42 in total.

## Points stated per A1-0070 (interpretation, not defects)

1. **Binding and signature rows give the same native result** (`Rejected(2)`, nothing changed). Only
   the signature evidence separates them:
   - binding rows: the submitted signature recovers to the witness 0x0bc496f1.. over the
     **altered** receipt;
   - signature rows: the kept honest signature recovers to the witness only over the **honest**
     receipt, and to a non-witness address over the altered one.
2. **`dbcBlockNumber`/`dbcBlockHash` are witness-attested only.** The PBC does not and cannot check
   them against the DBC. A receipt is evidence of DBC **authorization** (A1-0008), not of release or
   delivery.
3. **There is no report deadline at the PBC** (late reconciliation, PSC.sol:239).
   `reportAfterGrantExpiry` is recorded, not required; it was false in all 7 rows.
4. **The binding rows are an A40 deliberate deviation.** The TEST-ONLY tool uses the witness key
   outside the honest-witness assumption. `deviation.json` keeps `testOnly`, `deviation` and the A40
   label. These are defence-in-depth controls, never an HMBC result.

## Source bracket and hashes

- **Plan:** 851896f3.., unchanged; it re-verifies after the run.
- **Independent bracket:** 2732 files, 04887294.. before and after (`source-bracket.json`). HEAD
  8c7ef72 throughout.
- **Snapshots and hashing:** owner snapshots stable in all rows; Cast checkpoints all OK (14
  files).
- **Processes:** all 28 owned processes (14 Anvil, 14 adapters) exited 0; their PIDs are absent;
  ports 18545 and 18546 are free.
- **Commands:**
  - 101 owner commands: 0 unexpected non-zero exits, plus 42 verified never-instantiated probes
    (exit 1, expected), and 3 deviating-witness calls with exit 0;
  - 7776 RPC calls, all exit 0.
- **Versions:** `versions.json` (anvil 1.8.5, Python 3.13.5) was recorded after the run. During the
  run, `verify_plan` re-checked every tool binary hash.

## Limits

- One trial per row. Single-host Anvil, with no consensus or finality.
- MUT_NO_RECEIPT_BINDING counterparts are P3 mutant work and were not run.
- A receipt attests authorization only. Delivery is unknown.
- Symbolic adapter; safe-ledger, trusted-worker and one-trusted-witness assumptions.
