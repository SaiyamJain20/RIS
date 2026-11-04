# agent 2: F implementation progress, task 2 slice 1 (the durable signing store). NOT a source READY.

Accepted design inputs: F0 acceptance A3-0073 (`F0_ACCEPTANCE_CANDIDATE2.json` 03dcf485..), the 52 pinned `protocol/f0` files, interface `interfaces/v2` (FREEZE 7bb1d243..). Paper-derived reconstruction, symbolic, synthetic fixtures.
Same-model work and review: correlated. Nothing here ran against a chain, a witness process, a pool or an adapter; the signer and the observation source are injected.

Done in this slice (new files only; no E-listed file changed, so the E manifest 005c8448.. still verifies):
- `hmbc_protocol/witness_state.py`: the SQLite store (WAL, synchronous=FULL, marker, init lifecycle with crash points, all open refusals in the stage-9 order, the signing rule with commit before signature, idempotent
  re-sign, CONFLICT_PINNED with the recorded value, supersession only on observed death, the persisted tripwire and the explicit clear, read-only `evidence()` and `binding_export()`).
- `tests/test_witness_state.py` (34 tests, written first; the first run failed at import, `test_witness_state-run1-red.txt`) and `tests/state_child.py` (process-death injection, hook H4).
- `testtools/state_oracle.py` (TEST-ONLY): the WAL-aware logical snapshot oracle and the main-file hash it must not be confused with (hook H7 support).
- `tools/run_state_mutants.py`: 24 mutants (no durable record, commit ordering, wall-clock death, weak death conditions, tripwire disabled or not persisted, a clear that wipes history, every identity check dropped...).
  The first run detected **20 of 24** (`state-mutants-run1-20-of-24.txt`): the survivors showed test gaps (the integrity check, the ALLOW-only grant death, the effect-field check, the directory mode); I added the tests and the
  final run detects **24 of 24** (`state-mutants.txt`).
- Cross-checks against my own F0 references: every evidence document the store produces validates with `protocol/f0/vectors/export_layouts_reference.py`, and the binding export with the same reference.

Not done (task 2 and task 3 remain): the witness service (independent validation, profile-3 `witness.py`/`ledger.py`/`worker.py` changes, the D50 binding reconstruction and masked-build check from live reads), the CLIs
(`worker_log --binding`, `witness_state --binding/--evidence`), the pool collector with snapshot selection, the effort gate and timing evidence, the successor adapter operations and strict parsing, D-4, D-6, the TEST-ONLY hooks
H3/H5/H6 and `testtools/byzantine.py`, the E regressions and export `--check` after those changes, and the source READY manifest. Power loss and OS crash are untested and no durability claim is made for them.
Baseline of the existing E suite before any F change: `e-baseline.txt`.
