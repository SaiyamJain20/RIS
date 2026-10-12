# Gate E one-command run: runner and plan (no services yet)

Paper-derived HMBC2020 reconstruction. Synthetic only. E/RQ1 is active; gate E is NOT_RUN; F and G
are locked.

Author: agent 3 (proxy), solo phase (A1-0059, A1-0082). **Correlated self-review**: every review and
ACK in the solo phase comes from the same model as agent 1.

**Status:** runner `evaluation/e_gate.py` implemented **test-first** and unit-verified; plan frozen as
S3-0021. No service has run. **This checkpoint completes no gate criterion.**

## Design (S3-0002 section 3.1, amended by A1-0082)

| # | Stage | What it does |
|---|---|---|
| 1 | verify-freeze and versions | `FREEZE.json` against the frozen hash; all 15 frozen copies; the two moved owner inventories against their frozen Git blobs; tool versions and hashes |
| 2 | source bracket (pre) | `agent3Sources` (103 files), the 24 gate inputs and a broad bracket of `evaluation/**`, `interfaces/v1/**` and 5 root files; must equal the plan |
| 3 | catalog, 56 rows | one fresh chain pair per row through `evaluation.e2.run_row`: the three controls first on D1, then the stress on a fresh D2 (and B for wrong destination) |
| 4 | **dropped** | mutants: human decision A1-0080 |
| 5 | **dropped** | window: human decision A1-0081 |
| 6 | ProVerif | `access.pv` and `access_mutant.pv` with the declared local 2.05 build (bc2cd5ed..); verdicts and stdout bytes compared with A3-0033 and `p3-proverif-20261012` |
| 7 | source bracket (post) | the same bracket; HEAD and `git status` unchanged; the gate plan re-verified |
| 8 | `manifest.json` | `rq E`, `executionMode real-integrated`, `interfaceVersion v1`, `adapterMode symbolic`, status, `sourceStable`, `worktreeUnchanged`, every row with its status, failure, time and free memory, `resultFiles`, host memory before and after |
| 9 | `gate-evidence.json` | all 9 `E_CRITERIA`, each with status, evidence paths, rule and note |

**Aggregation only.** The gate plan embeds the ten slice plans that the existing `e2.create_plan` slice
flags produce (`expired_retry`, `duplicate_outcome`, `nonce_replay`, `subject_substitution`,
`relay_stress`, `audit_stress`, `receipt_stress`, `trust_stress`, `barrier_stress`,
`destination_stress`). `verify_plan` regenerates all of them and calls `e2.verify_plan` on each. Every
row goes through `e2.run_row`, which is the P2 row loop body moved into a function (see below), so the
gate uses the same `e1._profile` runner and the same frozen row check as the slices. No oracle was added.

**`e2.py` change (behaviour-preserving).** The body of the `execute` loop moved verbatim into
`run_row(plan, item, output, record, case_records)`; the probe and case naming moved into `probe_name`
and `case_name`, and the two flag ladders into `slice_mode` and `slice_status`. `execute` now calls
them, in the same order. An indentation-insensitive diff shows only those moves, plus
`continue` → `return case`.

**Layouts unchanged.** The output is `<out>/catalog/<slice>/<case>/<profile>/...`, with
`<out>/catalog/<slice>/manifest.json` as the slice record. agent 1's tools find their rows as before:
`*/*/<kind>-stress/result.json` under each slice directory, `*-subject-substitution/*` under
`sl1-subject`, and `recovery/result.json`, `alice/duplicate-outcome/result.json` and
`alice/nonce-replay/result.json` by `rglob`.

## Rows

| Slice | Plan flag | Rows | Case directories | Historical run |
|---|---|---|---|---|
| recovery-expiry | `expired_retry` | 6 | `<profile>-after_intent`, `<profile>-after_send` | `expiry-live-20261009` (A3-0038); recovery only `recovery-live-20261009` (A3-0036) |
| duplicate-outcome | `duplicate_outcome` | 3 | `<profile>-duplicate-outcome` | `duplicate-live-20261009` (A3-0040) |
| nonce-replay | `nonce_replay` | 3 | `<profile>-nonce-replay` | `grouped-replay-live-20261009` (A3-0045); the failed earlier trial is kept |
| sl1-subject | `subject_substitution` | 3 | `<profile>-subject-substitution` | `sl1-subject-live-20261010` (S3-0006) |
| sl2-relay | `relay_stress` | 7 | `<profile>-<variant>` | `sl2-relay-live-20261010` (S3-0010); the failed first run S3-0008 is kept |
| sl3-audit | `audit_stress` | 6 | `<profile>-<variant>` | `sl3-audit-live-20261010` (S3-0012) |
| sl4-receipt | `receipt_stress` | 7 | `repaired-e-<variant>[-<field>]` | `sl4-receipt-live-20261010` (S3-0014) |
| sl5-trust | `trust_stress` | 6 | `<profile>-<variant>` | `sl5-trust-live-20261010` (S3-0016) |
| sl6-barrier | `barrier_stress` | 9 | `<profile>-<variant>` | `sl6-barrier-live-20261011` (S3-0018) |
| sl7-destination | `destination_stress` | 6 | `<profile>-<variant>` | `sl7-destination-live-20261011` (S3-0020) |

Total 56: the 48 cases of `e0_cases.json` and the 8 of `e0_supplement_cases.json`, each exactly once
(checked by `create_plan`). The crash rows map to `E03-crash-after-intent|after-send-<profile>`. The 4
paper crash rows are labelled "frozen BLOCKED / decided SPEC_GAP, UNPROVED (D47)" and are never findings.

## Criteria (`gate-evidence.json`)

| Criterion | VERIFIED iff |
|---|---|
| interface-and-source-review | verify-freeze is UNCHANGED (E0 review is the closed E0 record) |
| legitimate-and-denied-controls | all 56 rows PASS (every row runs wrong-admin 16, Alice allow, Bob deny 9 first) |
| E01-E02-E03-classification | all 56 rows PASS and `catalog-coverage-56.json` has a reported classification for each |
| repairs-and-mutants | **human-scoped (A1-0080)**: the 8 guard rows PASS with their error (SL2 REPLAY, SL4 WRONG_SUBJECT ×3, SL5 STALE_ANCHOR, SL6 STALE_STATE and EXPIRED, SL7 WRONG_DESTINATION), all rows PASS, ProVerif matched, and the owner mutant evidence hashes as planned. Note: "met on owner, formal and baseline evidence (human decision A1-0080); integrated live mutant matrix not run ..." Evidence: `ledger/evidence/p3-mutant-suite-rerun/`, `evaluation/evidence/e2/p3-proverif-20261012/`, the guard rows of this run, A1-0080 |
| real-two-chain-and-recovery | all 56 rows PASS, including the 6 crash/recovery rows with their expired cached retry |
| proverif-and-negative-control | both models exit 0, empty stderr, expected verdicts, stdout byte-identical to A3-0033 and p3-proverif-20261012 |
| RQ1-report | **PENDING** by design: RQ1-E.md comes after the run (P4-2) |
| stable-hashed-input-output-tools | bracket equal before, after and to the plan; HEAD and `git status` unchanged; tool hashes; plan re-verified |
| three-matching-acks | **PENDING** by design: P4-3 |

So a fully passing run gives 7 VERIFIED and 2 PENDING. The window is not a criterion. `evaluation.gate`
is unchanged and stays fail-closed: a test shows it still returns BLOCKED on a complete passing run.
The manifest status reports the run stages only (`gateDecision`: "not gate E PASS").

## Failure, output and host policy

- **Failures are kept.** Each row runs exactly once. An exception or a failed row check marks the row
  FAILED with its type and message. The run then continues with the next row on a fresh chain pair.
  Rows never reached stay NOT_RUN. There is no retry. Any FAILED or NOT_RUN row, a ProVerif mismatch,
  a changed input or a changed worktree makes the run FAILED. Re-running needs a new FREEZE.
  - This differs from `e2.execute`, which stops a slice at its first failure. It is my explicit choice,
    so that one timing failure does not hide the rest of the evidence.
- **Output** goes only under `--output`, which must lie outside the repository working tree (refused
  otherwise). Nothing is written in the repository during the run. Publication is a separate selection
  with a never-publish key scan after the run, as in the slices.
- **Memory:** `/proc/meminfo` before and after the run, and `MemAvailable` at each row start.
- **Stopping:** SIGTERM is not trapped, as in the slices. To stop the run cleanly, send SIGINT
  (`kill -INT <pid>`); the row's `ExitStack` then stops its Anvil and adapter children and the manifest
  is written.
- **Wall time (estimate, not measured):** about 1.5 h; allow up to 2.5 h. The basis is the sum of the
  actual slice wall times, 5252 s: SL1-SL7 3732 s on this host, plus the pre-solo slices (1520 s, on
  agent 3's host).

## Verification (`manifest.json`)

**RED first:** both new test files were written before `e_gate.py` and before the `e2.py` refactor:
**48** (29 failed, 19 errors; `red-before-implementation.txt`): 25 `ModuleNotFoundError: evaluation.e_gate`
and 23 `AttributeError` for `e2.case_name`, `e2.slice_status` and `e2.run_row`. **No test was changed
after RED** (hashes in `manifest.json`).

**GREEN:**

- the 48 new tests pass (`green-new-tests.txt`, 74 s). They cover: the ten embedded slice plans and the
  56 catalog cases; the dropped stages and the criterion 4 wording; the hashed gate inputs and the
  ProVerif pin; solo-only plans; six plan mutations refused; verify-freeze (unchanged, and one changed
  copy reported); the real ProVerif stage, byte-identical to the saved outputs, and two mismatches
  reported; a full run of all 56 rows through the real `e2.run_row` with a TEST-ONLY `e1._profile`
  double (layouts, slice statuses, coverage, gate evidence, result hashes, `gate.py` still BLOCKED);
  two injected row failures kept while the other 54 rows still run, each exactly once; BLOCKED without
  ACKs with nothing started; an output inside the repository refused; a ProVerif mismatch and a changed
  input each fail the run; CLI exit 2;
- the `e2` row-runner tests: case names and slice statuses for all ten flags, `execute` delegating to
  `run_row` once per row and still stopping a slice at its first failure;
- full suite: `.venv/bin/python -m pytest -q -rs -p no:cacheprovider --color=no` exit 0, **1644 passed,
  0 failed, 0 skipped**, 574 s (`full-suite.txt`); the bracket of 4028 files is stable before and after;
- `e2-refactor-diff.txt`: `git diff -w` of `e2.py` against HEAD, showing only the moves.

## Limits

- **Not run live:** the gate command itself. Its row path is the live-proven slice path, but the
  aggregation, the per-row continuation, the brackets and the evidence writer are unit-tested only,
  against TEST-ONLY doubles of `e1._profile`.
- The early slices (recovery-expiry, duplicate, nonce replay) were strict-mode plans on agent 3's host.
  Here they run as solo-mode slice plans on this host (ports 18545/18546). The recipe is unchanged, but
  this host has not run them before.
- Repaired TTL margins are about 2 s (SL7 expiry boundary) and about 7 s (SL6 expired duty). A long run
  under memory pressure can fail such a row; it would be kept.
- One trial per row on one host; Anvil without consensus or finality; symbolic adapter; safe-ledger,
  trusted-worker and one-trusted-witness assumptions; no statistics.
- **Do not touch these files before the run.** All `agent3Sources` and the 24 gate inputs are frozen by
  the plan. Store helper scripts as `.py.txt`.
