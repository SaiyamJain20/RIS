# SL2 re-plan r2: runner fix for the never-instantiated D2 worker (no services yet)

Paper-derived HMBC2020 reconstruction. Synthetic only. E/RQ1 is active; gate E is NOT_RUN; F and G
are locked.

Author: agent 3 (proxy), solo phase (A1-0059). **Correlated self-review.**

| Item | Value |
|---|---|
| Supersedes | plan d67f1786.. (S3-0007), whose live run FAILED (S3-0008, `../sl2-relay-failed-20261010/`) |
| New plan | `integration-plan.json` sha256 b3a02098.. |
| FREEZE | S3-0009 |

## The defect and the fix

The production worker creates `<state>/worker/worker.sqlite` lazily, on its first `release`,
`encrypt_record` or `finish_decryption`. SL2 performs none of these. So the relay collector's
idle-worker export of the fresh D2 adapter state was refused by the pinned exporter (exit 1).

Following agent 1's diagnosis, **no state-changing call is added.** A first local fix that called
`encrypt_record` was reverted before any plan; it never ran.

Instead, `e1.observe_worker_export(exit, raw, state)` records a **verified never-instantiated
worker**. All three conditions are required:

1. exit 1;
2. the output is exactly `no worker.sqlite in <state> (looked in <dir>/worker/ and in <dir>)\n`;
3. the runner confirms on disk that neither `<state>/worker/worker.sqlite` nor `<state>/worker.sqlite`
   exists.

The result is stored as `{instantiated: false, exitCode: 1, message, checkedAbsent}`, never as an
empty export.

- Exit 0 must be a non-empty JSON object (an instantiated export).
- Anything else fails.
- The oracles accept before/after that are both never-instantiated, or both equal idle exports; any
  change fails.
- The relay rows use this probe. The D1 controls and the SL1 subject path are unchanged: their
  worker already exists after `encrypt_record`.
- The plan text (`relayProbe.snapshots`) states the rule.

**No other SL2 step assumes a worker database.** The worker is read only for the forged and
new-reference `before`/`after` snapshots and the same-nonce `worker-before`/`worker-after`.
`prepare_request` and `collect_*` do not touch it.

## Verification (`manifest.json`)

**RED.**

1. The test double was first made to model lazy creation: 7 failed (`red-lazy-worker-double.txt`),
   reproducing the live failure.
2. The probe, oracle and collector tests were written before the implementation: 103 failed
   (`red-never-instantiated.txt`).

**GREEN.**

- Targeted: 142 passed.
- 12/12 negative controls fail for the intended reason.
- The probe accepts the **actual** failed-run exporter bytes.
- Full suite `.venv/bin/python -m pytest -q -rs`: exit 0, **1015 passed, 0 failed, 0 skipped**,
  286 s. Bracket of 2170 files stable.

**Diff from d67f1786** (`plan-diff-from-d67f1786.json`):

- `agent3Sources` changed in exactly 4 files: `e1.py`, `e2.py`, `relay_stress.py`,
  `oracles/provenance.py`.
- The top-level `runId`, `freezeMessage` and `relayProbe` text changed.
- Owner pins, tools, ports, controls, rows and expectations are unchanged.

## Limits

Unchanged from the S3-0007 runner README: the D2 relay wiring is live-proven only up to the D2
bootstrap. The pinned reads ran live for the first time in the failed run. The `eth_call`
simulation and the same-nonce timing are still live-untested.
