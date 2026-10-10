# SL4: E03 receipt-control runner and plan (no services yet)

Paper-derived HMBC2020 reconstruction. Synthetic only. E/RQ1 is active; gate E is NOT_RUN; F and G
are locked.

Author: agent 3 (proxy), solo phase (A1-0059, A1-0064, S2-0007). **Correlated self-review.**

**Status:** runner implemented **test-first** and unit-verified; plan frozen as S3-0013. No service
has run. **No catalog row is completed by this checkpoint.**

## Rows, frozen expectations and pinned ledger facts (933d2a7)

All seven rows are repaired-e only (frozen supplement catalog).

| Row | Frozen expected | Ledger fact (PSC.sol:240-281) | Agreement |
|---|---|---|---|
| E03-receipt-binding-control-{requestDigest,gid,dataId}-repaired-e | NO_NEW_OUTCOME / REPAIR_SUPPORTED / WRONG_SUBJECT | `_checkReceipt` checks the binding (receipt requestDigest, gid, dataId against the forwarded record) first, so a validly witness-signed receipt with one bound field changed gives `Rejected(2)` | yes |
| E03-receipt-signature-control-{requestDigest,gid,dataId}-repaired-e | NO_NEW_OUTCOME / SUPPORTED / WRONG_SUBJECT | the same binding check precedes `QuorumLib.verify`, so the altered receipt with the honest signature also gives `Rejected(2)`, not BAD_SIGNATURE | yes |
| E03-receipt-binding-positive-repaired-e | ACCEPT / SUPPORTED | the honest receipt passes all checks; `lsc.outcomeLog(digest, abi.encode(digest, outcomeDigest, receipt, relay))` (OUTCOME = 4), status 2, `AttestedOutcomeRecorded(digest, grantId, outcomeDigest, dbcBlockNumber, logId)` | yes |

Full check order after profile, relay caller and request status:

1. binding gives WRONG_SUBJECT(2), unless the mutant bit MUT_NO_RECEIPT_BINDING is set;
2. dbcChainId, kssc and grantId give WRONG_DESTINATION(3);
3. keyEpoch gives WRONG_EPOCH(12);
4. grantExpiresAt of 0, or later than the request expiry, gives MALFORMED(20);
5. witnessSetVersion gives STALE_STATE(6);
6. quorum: a non-witness signer gives BAD_SIGNATURE(1) (SigLib.sol:47); no signature gives
   INSUFFICIENT_QUORUM(10).

**No disagreement between the catalog and the ledger was found.**

## Recipe (`integration-plan.json` sha256 851896f3..)

Each of the 7 rows runs on a fresh chain pair: PBC port 18545, DBC port 18546, chain IDs
18545/28545.

- **D1** runs the controls: wrong-admin 16; Alice allow with release and one outcome; Bob deny 9.
- **D2** is a fresh second deployment with its own bootstrap, production adapter and 0700 state
  (`kind=receipt`).

Every row uses its **own** fresh forwarded request, actual allowed grant and honest receipt. The
steps follow the catalog exactly:

1. **REQUEST_ACCESS:** Alice's request.
2. **FORWARD_OR_CONSUME:** checkpoint, honest ALLOW certificate, `consumeDecision`.
3. **ATTEST_GRANT:** the production witness, **before any report** on the request. The receipt's
   signature is recovered under the evaluator's own encoder. Its block hash and the grant at that
   block are joined natively.
4. The variant step:
   - **binding (RESIGN_RECEIPT_FIELD):** the pinned TEST-ONLY deviating witness, run at the honest
     receipt's `dbcBlockNumber`;
   - **signature (ALTER_RECEIPT_KEEP_SIGNATURE):** one field changed to the same deterministic
     value, honest signature kept, no tool;
   - **positive:** none.
5. **REPORT_OUTCOME:** the relay calls
   `PSC.reportAttestedOutcome(digest, keccak("HMBC.E03.receipt-control-outcome.v1"), receipt, signatures)`.

## TEST-ONLY deviating witness (S2-0007 conditions, accepted in A1-0064)

| Condition | How the runner meets it |
|---|---|
| exact bytes | `protocol/testtools/deviating_witness.py` sha256 0511ba57.. = the 0716a8e inventory entry = `git show`; re-hashed before every call |
| exact command | argv only from the plan template: `python -m testtools.deviating_witness --deployment <D> receipt --grant-id <0x..> --field <f> --at-block <N>`; cwd = the materialized protocol snapshot; **no `--value`** (`e1.deviation_argv`, tested) |
| same deployment file (R11) | `<D>` is the stress adapter's own `--deployment` path; its bytes are re-checked as identical before every call |
| non-zero exit | a failed trial: no retry, no report. Only `deviation-refusal.json` (exit code, output sha256, first line) is written. The raw command log stays in the private run output |
| three-way check, before use | (1) only the named field differs from the honest receipt; (2) the signature recovers to the configured witness under the evaluator's own EIP-712 encoder (HMBCReceipt v1, PBC PSC domain); (3) `testOnly` is true and `deviation.field` equals the row field. Plus: the default deterministic alteration and exactly one JSON line. The oracle repeats the same check |
| labelling | `deviation.json` keeps `testOnly` and `deviation` and is labelled "A40 deliberate witness deviation", not an honest-witness receipt and not an HMBC result |
| never publish | keys, seeds, anything derived from a key label, raw release tokens (the D1 Alice control keeps `tokenSha256` only), the raw tool log |

## Worker-DB precondition, re-checked for every step

**Static check at protocol pin 0716a8e:**

- The worker database is created only by `_worker` (adapter.py:133-136). Only `release`,
  `encrypt_record` and `finish_decryption` reach it (adapter.py:178-190).
- `prepare_request` is pure.
- `collect_checkpoint`, `collect_decision` and `attest_grant` use `Witness` only
  (adapter.py:153-176). `Witness` and `Ledger` hold no files.
- The deviating witness takes no state directory.

**SL4 calls none of the three worker operations.**

**Dynamic check:** the D2 worker is observed with the D49 probe at baseline and after **every**
catalog step:

- `baseline`
- `REQUEST_ACCESS`
- `FORWARD_OR_CONSUME`
- `ATTEST_GRANT`
- the variant step (`RESIGN_RECEIPT_FIELD` or `ALTER_RECEIPT_KEEP_SIGNATURE`; positive has none)
- `REPORT_OUTCOME`

Each observation must be the identical verified never-instantiated record. Any instantiation fails
the row (`workerSteps` in `result.json`).

## Verification (`manifest.json`)

**RED first:** all SL4 tests were written before any SL4 code: **116 failed**
(`red-before-implementation.txt`): 74 oracle-module-missing, 18 collector-module-missing and 24
`create_plan(receipt_stress)` errors. The test files are unchanged since RED.

**GREEN:**

- oracle 74 passed and collector 18 passed;
- **7/7 collector negative controls fail for the intended reason** (`control-reasons.txt`):

  | Control | Fails with |
  |---|---|
  | tool exits 1 | failed trial, sha256 and first line only |
  | tool alters two fields | "only the named field differs" |
  | tool signs with a non-witness key | "recovers to the configured witness" |
  | mutant-like acceptance on a binding row | native status differs from the expected rejection |
  | mutant-like BAD_SIGNATURE on a signature row | "Rejected(WRONG_SUBJECT)" |
  | worker instantiated after ATTEST_GRANT (×2) | "never-instantiated worker after ATTEST_GRANT" |

- plan tests: 24 passed;
- full suite `.venv/bin/python -m pytest -q -rs`: exit 0, **1226 passed, 0 failed, 0 skipped**,
  351 s. The bracket of 2726 files is stable.

**`agent3Sources` changed since SL3 (96 files):**

- new: `evaluation/receipt_stress.py` and `evaluation/oracles/receipt.py`;
- changed: `evaluation/e1.py` (the `receipt_stress` D2 path, `deviation_argv`, `stress_deviate`) and
  `evaluation/e2.py` (the receipt plan).

## Limits

- **Not yet run live:** the D2 receipt wiring, the deviating witness on Anvil, and
  `reportAttestedOutcome` rejections. All are unit-tested only, against a TEST-ONLY double that
  follows the pinned check order.
- **MUT_NO_RECEIPT_BINDING counterparts** are P3 mutant work and are not run here.
- **A receipt attests DBC authorization only**, not release or delivery. Delivery is unknown.
- Symbolic adapter; safe-ledger, trusted-worker and one-trusted-witness assumptions.
- **Do not touch these files before the run.** All 96 `agent3Sources` are frozen, including every
  `evaluation/**/*.py`. Store helper scripts as `.py.txt`.
