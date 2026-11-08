# Evidence: agent 3's store snapshot cannot lock a witness store that has signed (found by cross-running agent 3's real code on my real store)

Agent 3's `evaluation/store_snapshot_v2.locked_store(database, marker, lock)` (A3-0085, from a `git archive` of origin/agent-3 6358f7c, run unmodified with `python -I` out of tree) takes `flock(LOCK_EX | LOCK_NB)` on a caller-chosen lock path and says "a cooperative writer must honor the same flock". My real `witness_state.WitnessStore` locks `<dir>/.lock`: it takes `LOCK_SH` at the first signing (and in `clear_fault`) and **never releases it** while the store is open (no `LOCK_UN` anywhere in the module).
`probe.py.txt` runs a long-lived process holding my real store open and a second process calling agent 3's real `locked_store` on `<dir>/.lock`.
| Case | Result before the fix | File |
|---|---|---|
| witness alive, store open, never signed | snapshot taken | `probe-output-BEFORE-fix.json` |
| witness alive, store open, has signed once | **REFUSED: `ValueError: Store lock is busy`** | same |
| witness stopped (process exited) | snapshot taken | same |
Consequence for the integrated run: with the code of A2-0076 (commit of record 7d97b90) a collector built on `locked_store` can snapshot a running witness only before its first signing, never afterwards; and the "caller holds EX over before / action / after" choreography cannot run against a running witness at all. Single host, one probe run; the probe measures lock availability, not any other property of either module. Same-model correlated review.

## The fix (A2-0078) and its evidence
`witness_state.WitnessStore` is now a cooperative writer: a new `_writing()` context manager takes `LOCK_SH` on `.lock` only while a signing transaction or `clear_fault` runs and ALWAYS releases it (also on a refusal or an exception); `exclusive()` (TEST-ONLY) releases with `LOCK_UN` instead of re-taking a shared lock. A snapshot taker holding the lock exclusively therefore waits for a transaction in progress, and a writer that starts while it holds the lock waits for it.
| Check | Result | File |
|---|---|---|
| RED, `tests/test_witness_state_lock.py` on the unfixed store | **7 failed, 2 passed**; every failure is "the lock is still held after the operation" (the 2 passes are the controls: free before any signing, held during one) | `RED-lock-tests-7failed-2passed.txt` |
| GREEN (10 tests, one added for `clear_fault`) | **10 passed** | `GREEN-lock-tests-10passed.txt` |
| The same cross-probe after the fix, agent 3's real `locked_store` on the real store | witness alive and **has signed once -> SNAPSHOT TAKEN** (it was REFUSED before); never signed and stopped cases unchanged | `probe-output-AFTER-fix.json` |
| `run_state_mutants.py` (33 old + 7 new lock mutants L1..L7) | control passes, **40 / 40 detected**, exit 0 | `runner-state-40of40.txt` |
| Store-dependent tests (state, state CLI, the five service files, witness_main, worker_binding, lock tests) | 364 passed (before the added `clear_fault` test) | (command) |
Not claimed: that agent 3's full choreography (EX held across before / action / after) works end to end against a running adapter (the probe measures lock availability only; a real action that makes the witness SIGN while the caller holds EX waits by design until the caller releases); anything outside lock behaviour. Single host, correlated review.

## Broader verification of the fix, on a clone of exactly d375dda (outputs in `outputs-at-d375dda/`; A2-0078)
| Check | Result | File |
|---|---|---|
| Full protocol suite | **2956 passed, 201 skipped, 0 failed**, exit 0, 1014 s (2946 of A2-0076 + the 10 lock tests); the 201 skips are 200 ScenarioResult + 1 FileHash outside agent 2's scope, no Foundry skip | `FULL-SUITE-on-clone-of-d375dda.txt` |
| Runners of the modules that import or mention `witness_state` (control passes, every mutant detected, argued equivalents run and survive) | state 40/40 (above); service **137/137**; witness_main **39/39** (+1 equivalent); adapter_v2_witness **57/57**; witness_process_transport **92/92**; faulty_adapter_v2 **41/41** (+2 equivalents); witness_hooks `--live` **46/46** (+2 equivalents); adapter_v2_main **43/43** (+1 equivalent); adapter_v2_start **15/15**; binding_open **52/52**; worker_binding **32/32**; pool_driver **15/15**; all exit 0 | `runner-<name>.txt` |
| Failed trial kept | the first queue script for the last five runners omitted the `.py` suffix; all five exited 2 in under a second without testing anything; re-run correctly | `failed-trials/` |
Not re-run: the 10 other runners (their modules neither import nor mention `witness_state`; their controls are inside the full suite). A mutant `pytest` orphaned by an earlier stopped runner spun at 100% CPU for 14 hours on this host and was killed before the last runs; the runs were measured with one core busy.
