# SL2 actual run: FAILED at row 1 before any stress transaction (runner defect)

Directory: `evaluation/evidence/e2/sl2-relay-failed-20261010/` (A1 diagnosis). It adds the raw CLI records (`cli.json`, `cli.stdout.json`, `cli.stderr.txt`) and the failing command row and process record (`failed-command-*`).

Paper-derived HMBC2020 reconstruction. Synthetic only. E/RQ1 is active; gate E is NOT_RUN; F and G
are locked.

Solo phase (A1-0059). **Correlated self-review.**

**This failed trial is kept as it is.** It was not retried; agent 1 decides any re-plan.

## Run

**Authorization:**

- Plan `evaluation/evidence/e2/sl2-relay-runner-20261010/integration-plan.json`, sha256
  `d67f178665d0b64d32fd875f1a3ab3e689da0032e3984a8747bde839512fa3b1`.
- FREEZE S3-0007, ACKs A1-0065 and S2-0008, all in c649e12.
- `acks.json` was verified by the solo verifier before services.

**Command** (`export PATH="$HOME/.foundry/bin:$PATH"`):

```
.venv/bin/python -m evaluation.e2 --plan evaluation/evidence/e2/sl2-relay-runner-20261010/integration-plan.json --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl2-run/acks.json --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl2-run/real-e2-output
```

**Result:** **exit 2, status FAILED**, 2026-10-10T00:54:18Z to 00:55:34Z, 75.45 s. Stderr is empty
(`real-e2.json`).

The failure message is `Public access owner command relay-worker-export-00 failed`.

## What happened (row 1: E01-forged-tuple-paper-strict)

1. A fresh chain pair started: PBC 18545 / chain ID 18545, DBC 18546 / chain ID 28545. This was
   the first live use of port 18546 and of the solo ACK path; both worked.
2. **D1 controls passed:**
   - bootstrap wrong-admin rejected with code 16;
   - Alice allowed, released, completed and recorded her outcome;
   - Bob was denied by policy (code 9).
3. **D2 (`relay-instance`) was deployed and bootstrapped**, and its production adapter started. This
   was the first live use of the generalized D2 path; it worked.
4. The relay collector built the forged tuple (`relay-stress/public-call.json`) and began the
   `before` snapshot.
   - Both chains' pinned read groups completed.
   - The D2 worker export then failed: `no worker.sqlite in …/relay-instance/private-adapter-state (looked in <dir>/worker/ and in <dir>)`
     (`failed-command-relay-worker-export-00.txt`, exit 1).
5. **No stress transaction was submitted.** Rows 2-7 did not start.

**Cause: an agent-3 (proxy) evaluator recipe defect, not a ledger or protocol defect.**

- The production worker creates its database lazily, on its first worker operation.
- The D2 adapter had performed **no** operation. The paper forged tuple uses no adapter call at all.
- `execute_access` (E1, SL1) always calls `encrypt_record` first; `relay_stress` did not.
- My TEST-ONLY world double exported an idle worker unconditionally, so unit tests could not catch
  this. That is a test-double fidelity gap.

**Fix (S3-0009, test-first; agent 1's diagnosis).** No state-changing call is added: `encrypt_record`
is never used to create the worker. Instead, the runner records a **verified never-instantiated
worker** (`e1.observe_worker_export`), which needs all three of:

- the exporter exits 1 with exactly `no worker.sqlite in <state> (looked in <dir>/worker/ and in <dir>)`;
- the runner confirms on disk that neither `<state>/worker/worker.sqlite` nor `<state>/worker.sqlite`
  exists;
- the record is written as `{instantiated: false, ...}`, never as an empty export.

Before and after must be equal; any other refusal fails. The test double now models lazy worker
creation.

## Integrity and cleanup

- **Sources stable:**
  - runner `sourceStable: true`;
  - independent bracket of 2120 files, 5af5c31b.. both before and after;
  - HEAD c649e12 both before and after;
  - owner snapshots stable; Cast checkpoints all OK.
- **Processes:** all 4 owned processes (2 Anvil, D1 adapter, D2 adapter) exited 0, and their PIDs
  are absent. Ports 18545 and 18546 are free.
- **Commands:** 9 owner commands, of which 1 failed: the worker export above. 825 RPC calls, all
  exit 0.
- **Public evidence:** 33 redacted JSON files under `run/`.
  - The scan checked the TEST-ONLY private keys of 15 fixture labels and the one release token in
    the private worker databases. 0 hits.
  - Raw logs and private state stay in `tmp/p3/sl2-run`, hashed in `external-public-inventory.json`.

## Catalog coverage (`catalog-coverage.json`)

**0 of the 7 SL2 rows are complete.**

| Row | Status |
|---|---|
| E01-forged-tuple-paper-strict | FAILED_BEFORE_STRESS_TRANSACTION |
| Rows 2-7 | NOT_RUN_ABORTED_SLICE |

No classification is claimed. **41 catalog comparisons remain.**
