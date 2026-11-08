# Evidence: agent 3's store snapshot cannot lock a witness store that has signed (found by cross-running agent 3's real code on my real store)

Agent 3's `evaluation/store_snapshot_v2.locked_store(database, marker, lock)` (A3-0085, from a `git archive` of origin/agent-3 6358f7c, run unmodified with `python -I` out of tree) takes `flock(LOCK_EX | LOCK_NB)` on a caller-chosen lock path and says "a cooperative writer must honor the same flock". My real `witness_state.WitnessStore` locks `<dir>/.lock`: it takes `LOCK_SH` at the first signing (and in `clear_fault`) and **never releases it** while the store is open (no `LOCK_UN` anywhere in the module).
`probe.py.txt` runs a long-lived process holding my real store open and a second process calling agent 3's real `locked_store` on `<dir>/.lock`.
| Case | Result before the fix | File |
|---|---|---|
| witness alive, store open, never signed | snapshot taken | `probe-output-BEFORE-fix.json` |
| witness alive, store open, has signed once | **REFUSED: `ValueError: Store lock is busy`** | same |
| witness stopped (process exited) | snapshot taken | same |
Consequence for the integrated run: with the code of A2-0076 (commit of record 7d97b90) a collector built on `locked_store` can snapshot a running witness only before its first signing, never afterwards; and the "caller holds EX over before / action / after" choreography cannot run against a running witness at all. Single host, one probe run; the probe measures lock availability, not any other property of either module. Same-model correlated review.
