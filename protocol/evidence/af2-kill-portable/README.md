# Evidence: a portable initialization-kill harness (agent 2, 2026-11-13; answers A3-0108)

PAPER-DERIVED RECONSTRUCTION; synthetic signer; one host (this machine: Linux, 16 GiB RAM under heavy load, SQLite 3.50.4); CPython 3.13.12 from the frozen root `uv.lock` (1fb4777a..); Foundry 1.8.5 (asset sha256 6c66ffcc.., forge 06c477ae.., anvil 00f97668.., cast 1eb1eecf..) and solc 0.8.37 (5de843c2..) re-downloaded this session and verified against `interfaces/v1/toolchain.json`. Correlated same-model review.

## The finding this answers (A3-0108, agent 3's consolidated runtime review)
Agent 3 ran my `tests/test_witness_state_kill.py` unmodified on its host: **all 100 initialisation trials finished before the SIGKILL landed** (`interrupted=0`), so the test failed instead of testing recovery. A3-0108 asked for a portable schedule, `interrupted >= 1` RETAINED (not weakened), published exercised/finished counts, the unmodified kill control and K1/K2/E1 re-run, and an exact delta READY. This directory is that evidence; the delta READY is A2-0085.

## The diagnosis (measured, on this host, before the fix)
A delay-based kill window is host- AND context-dependent. Same host, same child, same measurement (`state_kill_child.py init`, READY -> DONE):
| Context | Per-run time |
|---|---|
| standalone `python -B -I` (10 runs) | 5.3 - 14.4 ms |
| inside pytest (the same spawn, `tmp_path` or a scratch dir, with/without conftest) | 210 - 260 ms |
Files: `diagnosis-max-window-interrupted0-20261113.txt` (first calibrated attempt: max-of-3 window 245 ms, `interrupted=0`, 25/25 finished first, 6 passed but I5 untested — a FAILED CONTROL, not fixed by widening), `diagnosis-median-window-inside-pytest-213-259ms.txt` (median-of-7 inside pytest: 213-259 ms, still `interrupted=0`), `first-calibrated-run-max-window-25-trials-6passed-interrupted0.txt` (the 6-passed run). Conclusion: no fixed or measured-delay window is portable; the schedule must not depend on wall time.

## The fix (commit 8ffd316; files and hashes)
| File | Change | sha256 at 8ffd316 |
|---|---|---|
| `protocol/tests/test_witness_state_kill.py` | the init test is now CONTROLLED + random; stats line added to the signing test | bff4f01fe22b2ea7cba35da6c2ae957304764ad948c48c3dfc87664cbf1bf3ec |
| `protocol/tests/state_kill_child.py` | the `init` mode prints `STAGE <point>` for each `init_store` crash-hook point (`after_dir`, `after_db_commit`, `after_tmp_marker`, `after_rename`) | 899ed62ac4e4f07ffccae494dc1d3fae9e1b70be22fef58d8362afcb47c28581 |
- **Controlled kills:** the parent SIGKILLs the child the instant it READS the child's `STAGE <point>` line, so the kill lands inside a real `init_store` at a named point on any host, fast or slow, loaded or idle. Four stage kills (every hook point), then 25 random-delay trials as a complement (their kills may land or not; the RESTART assertion covers both outcomes either way).
- **`interrupted >= 1` is retained, strengthened:** the assertion is now `interrupted >= 4` (every controlled kill must interrupt). A kill that never interrupts is still a failed test.
- **Published counts:** the test prints `KILL-INIT-STATS stage_kills=4 random_trials=25 finished_before_kill=N interrupted_total=M`; the signing test prints `KILL-SIGN-STATS trials= replies= unreplied= refusals= superseded=`. Measured here: `KILL-INIT-STATS stage_kills=4 random_trials=25 finished_before_kill=25 interrupted_total=4` and `KILL-SIGN-STATS trials=25 replies=1800 unreplied=14 refusals=1884 superseded=125` (`GREEN-stage-kills-4-of-4-random-25-signing-25.txt`).
- The scratch diagnosis helper (`_probe_slow`) and its `CALIB-MS` print were removed; the remaining diagnosis outputs above are the record.

## Verification
| Check | Result | File |
|---|---|---|
| The three kill tests + 3 hot-journal tests, working tree | 6 passed, 33 s | (out-kill-portable: superseded by the stage rewrite, see next) |
| All 3 kill tests after the rewrite (`-s`) | **3 passed**, 36 s; stats above | `GREEN-stage-kills-4-of-4-random-25-signing-25.txt` |
| `run_state_kill_mutants.py` (K1, K2 must be detected; E1 must survive) | **K1 and K2 detected (2 of 2); E1 SURVIVES (1 of 1)**, as argued (SIGKILL does not exercise `synchronous=FULL`) | `runner-kill-K1K2-detected-E1-survives.txt` |
| `run_state_mutants.py` on a clean clone of 8ffd316 | **42 of 42 detected**, control passes | `runner-state-42of42-at-8ffd316.txt` |
| **Full protocol suite on a clean clone of 8ffd316, Foundry 1.8.5 + solc 0.8.37 hash-verified, HOME redirected** | **3204 passed, 201 skipped, 0 failed**, exit 0, 1144 s. The 201 skips are exactly 200 ScenarioResult + 1 FileHash out-of-scope cases; **no Foundry skip** (read the skip count) | `FULL-SUITE-with-Foundry-on-clone-8ffd316.txt` |
| First full-suite run on the same clone WITHOUT Foundry (before the toolchain was re-downloaded) | 1 failed (`test_e2_repaired_e.py::test_zz_every_catalog_case_was_executed_exactly_once`: the 16 E2 catalog cases need real chains) + 470 Foundry skips; recorded as the no-toolchain baseline, NOT a defect of the fix | `FULL-SUITE-no-Foundry-first-clone-run.txt` |
| Failed trials kept | the calibration-read crash (`init_duration` consumed the first `STAGE` line as DONE: `failed-trial-calibration-read-staged-line.txt`), and both interrupted=0 diagnoses above | this directory |

## Limits, plainly
SIGKILL only: no power loss, no OS crash; E1 survives by design (that limit is stated by experiment). The four controlled kills cover the four NAMED hook points of `init_store`; they do not cover unnamed points inside SQLite's own writes — the 25 random trials remain the only cover for those, and their coverage is host-dependent (that is why the controlled kills carry the assertion). One host; the point of the fix is that the CONTROLLED part no longer depends on which host. Mutants are single-site edits by the same model family that wrote the code.
