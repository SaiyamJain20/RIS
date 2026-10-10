# SL4 actual run: E03 receipt controls ×7 (repaired-e), all PASS

Paper-derived HMBC2020 reconstruction. Synthetic only. Symbolic adapter, with safe-ledger,
trusted-worker and one-trusted-witness assumptions. E/RQ1 is active; gate E is NOT_RUN; F and G are
locked.

**Solo phase (A1-0059):** every review and ACK is **correlated self-review**.

## Run

**Authorization:**

- Plan `evaluation/evidence/e2/sl4-receipt-runner-20261010/integration-plan.json`, SHA-256
  `851896f3608ac7e234820c4d24a6d6d8db1e608254828ab8199cce6aa672676c`.
- FREEZE S3-0013, ACKs A1-0070 and S2-0013, all at 8c7ef72.
- `acks.json` was verified by the solo verifier before services.

**Command** (`export PATH="$HOME/.foundry/bin:$PATH"`):

```
.venv/bin/python -m evaluation.e2 --plan evaluation/evidence/e2/sl4-receipt-runner-20261010/integration-plan.json --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl4-run/acks.json --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl4-run/real-e2-output
```

**Result:** exit **0**, `E2_RECEIPT_STRESS_SLICE_PASS`, 2026-10-10T12:11:30Z to 12:21:32Z, **601.60 s**.
Stderr is empty. `sourceStable: true`.

## Results against the frozen catalog (`catalog-coverage.json`)

| Row | Frozen expected | Observed | Class |
|---|---|---|---|
| E03-receipt-binding-control-requestDigest-repaired-e | NO_NEW_OUTCOME / WRONG_SUBJECT | deviating receipt (only `requestDigest` changed, witness-signed) → `Rejected(2)`, no events, state unchanged | **REPAIR_SUPPORTED** (A40) |
| E03-receipt-binding-control-gid-repaired-e | same | same, only `gid` changed | **REPAIR_SUPPORTED** (A40) |
| E03-receipt-binding-control-dataId-repaired-e | same | same, only `dataId` changed | **REPAIR_SUPPORTED** (A40) |
| E03-receipt-signature-control-requestDigest-repaired-e | NO_NEW_OUTCOME / WRONG_SUBJECT | altered receipt with the honest signature kept → `Rejected(2)`, no events, state unchanged | **SUPPORTED** |
| E03-receipt-signature-control-gid-repaired-e | same | same | **SUPPORTED** |
| E03-receipt-signature-control-dataId-repaired-e | same | same | **SUPPORTED** |
| E03-receipt-binding-positive-repaired-e | ACCEPT | honest receipt → LSC OUTCOME(4) log 7 with exact details, `AttestedOutcomeRecorded`, status 2, DBC unchanged | **SUPPORTED** |

**All 7 rows match the frozen classification, error and outcome.**

Every report is in block 49 of its own fresh D2 deployment. Every honest receipt is at DBC block
24. Each report came 5 s or less after the request, so `reportAfterGrantExpiry` is false in every
row.

## TEST-ONLY deviating witness (binding rows; S2-0007 / A1-0064)

| Row | Exit | `--at-block` | Changed field | Output sha256 |
|---|---|---|---|---|
| binding requestDigest | 0 | 24 | 0xa63e3b34.. → 0x7be23f50.. | 773aabe6.. |
| binding gid | 0 | 24 | 0xc4ff0022.. → 0xe03bfd6f.. | d5547b7a.. |
| binding dataId | 0 | 24 | 0x53ff1533.. → 0x54ac5b3b.. | 6de84d35.. |

- Each artifact passed the three-way check before use, and the oracle repeated it:
  1. only the named field differs from the honest receipt;
  2. the signature recovers to the witness 0x0bc496f1.. under the evaluator's own HMBCReceipt
     encoder;
  3. `testOnly` is true and `deviation.field` equals the row field.
- Bytes: the tool was re-hashed before each call. The deployment file was byte-identical to the
  stress adapter's.
- Published: `receipt-stress/deviation.json`, which keeps `testOnly` and `deviation` and carries
  the label "A40 deliberate witness deviation".
- **Not published:** the raw `receipt-deviate-00.txt` logs. They stay in the private run output.

The signature rows use the same deterministic altered value without the tool (`altered-receipt.json`).

## Worker-DB precondition (D49), every step

The D2 worker was observed at baseline and after every catalog step: REQUEST_ACCESS,
FORWARD_OR_CONSUME, ATTEST_GRANT, the variant step and REPORT_OUTCOME (`workerSteps` in each
`result.json`).

- Every observation was the identical verified never-instantiated record: exporter exit 1 with its
  exact message, and both database paths absent.
- 42 probes ran: 6 per row, including the two inside the before and after snapshots.
- No SL4 step called `release`, `encrypt_record` or `finish_decryption`.

## Controls

Every row's D1 passed:

- wrong-admin 16;
- Alice allow with release and one attested outcome;
- Bob deny (POLICY_DENIED, 9).

Every D2 bootstrap also gave wrong-admin 16.

## Integrity (`live-result-audit.json`, `source-bracket.json`)

- **Processes:** 14 Anvil services and 14 adapters, all exited 0; all PIDs are absent; ports 18545
  and 18546 are free.
- **Per profile:** sources stable, services stopped, and the Cast checkpoint stable (14 checkpoint
  files, all OK).
- **Commands:**
  - 101 owner commands: 0 unexpected non-zero exits, 42 verified never-instantiated probes (exit 1,
    expected), and 3 deviating-witness calls (exit 0);
  - 7776 RPC calls, all exit 0.
- **Independent bracket:** 2732 files, 04887294.. before and after. HEAD was 8c7ef72 throughout.
  The plan is unchanged and re-verifies.

## Never-publish scan (`selected-manifest.json`)

- **Selection:** 294 JSON files, 0 refused, all byte-identical to the run output (checked with `cmp`).
- **Per row, unmodified:**
  - `receipt-instance/{deployment,bootstrap-checked}.json`;
  - `receipt-instance/{pbc,dbc}-native/*`;
  - all of `receipt-stress/*`: honest-receipt, deviation or altered-receipt, public-call,
    stress-transaction, before/after (+ blocks), grant-transaction, exchanges, timeline, result.

  That is 125 keep-set files.
- **Excluded:** every `.txt` (including `receipt-deviate-*.txt`), `private-adapter-state`,
  snapshots and RPC transcripts.
- **Substring scan:**
  - the TEST-ONLY keys of 15 labels (relay, alice, bob, H1-H4 root and CA-admin, witness-1..4);
  - every frozen-vector `signerPrivateKey`, including witness-1, which equals the derived key;
  - the 7 release tokens from the private worker databases (D1 Alice controls only; D2 has no
    worker).

  Result: **0 hits**.

## Points stated per A1-0070 (interpretation, not defects)

1. **Binding and signature rows give the same native result** (`Rejected(2)`, nothing changed). Only
   the signature evidence separates them:
   - binding: the submitted signature recovers to the witness over the altered receipt;
   - signature: it recovers to the witness only over the honest receipt.
2. **`dbcBlockNumber`/`dbcBlockHash` are witness-attested only.** The PBC does not and cannot check
   them against the DBC. A receipt is evidence of DBC authorization (A1-0008), not of release or
   delivery.
3. **There is no report deadline at the PBC** (late reconciliation, PSC.sol:239).
   `reportAfterGrantExpiry` is recorded, not required; it was false in all rows.
4. **The binding rows are an A40 deliberate deviation.** The TEST-ONLY tool uses the witness key
   outside the honest-witness assumption. They are defence-in-depth controls, never an HMBC result.

## Limits

- One trial per row. Single-host Anvil, with no consensus or finality.
- MUT_NO_RECEIPT_BINDING counterparts are P3 mutant work and were not run here.
- Delivery is unknown. Symbolic adapter.
- Tool versions were recorded after the run (`versions.json`). During the run, `verify_plan`
  re-verified every tool binary hash.
