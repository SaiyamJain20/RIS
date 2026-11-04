# agent 2: F implementation progress, task 2 slices 1 and 2 (the durable signing store; the production D50 binding module and the read-only exporter CLI) and task 3 slice 3a (the pool decision core). NOT a source READY.

Accepted design inputs: F0 acceptance A3-0073 (`F0_ACCEPTANCE_CANDIDATE2.json` 03dcf485..), the 52 pinned `protocol/f0` files, interface `interfaces/v2` (FREEZE 7bb1d243..). Paper-derived reconstruction, symbolic, synthetic fixtures.
Same-model work and review: correlated. Nothing here ran against a chain, a witness process, a pool or an adapter; the signer and the observation source are injected.

Done in slice 1 (new files only; no E-listed file changed, so the E manifest 005c8448.. still verifies):
- `hmbc_protocol/witness_state.py`: the SQLite store (WAL, synchronous=FULL, marker, init lifecycle with crash points, all open refusals in the stage-9 order, the signing rule with commit before signature, idempotent
  re-sign, CONFLICT_PINNED with the recorded value, supersession only on observed death, the persisted tripwire and the explicit clear, read-only `evidence()` and `binding_export()`).
- `tests/test_witness_state.py` (34 tests incl. the integrity, mode, ALLOW-only-grant and effect-field tests added after the first mutation run; the first run failed at import, `test_witness_state-run1-red.txt`) and `tests/state_child.py` (process-death injection, hook H4).
- `testtools/state_oracle.py` (TEST-ONLY): the WAL-aware logical snapshot oracle and the main-file hash it must not be confused with (hook H7 support).
- `tools/run_state_mutants.py`: now 32 mutants (24 of the store plus 8 of the exporter CLI and anchor; the CLI run first detected 31 of 32, `state-mutants-run2-31-of-32.txt`, the survivor was the missing anchor-shape test); the store alone: 24 mutants (no durable record, commit ordering, wall-clock death, weak death conditions, tripwire disabled or not persisted, a clear that wipes history, every identity check dropped...).
  The first run detected **20 of 24** (`state-mutants-run1-20-of-24.txt`): the survivors showed test gaps (the integrity check, the ALLOW-only grant death, the effect-field check, the directory mode); I added the tests and the
  final run detects **24 of 24** (`state-mutants.txt`).
- Cross-checks against my own F0 references: every evidence document the store produces validates with `protocol/f0/vectors/export_layouts_reference.py`, and the binding export with the same reference.

Done in slice 2 (new files only):
- `hmbc_protocol/binding.py`: the PRODUCTION port of the pinned D50 reference (closed shape of B, canonical form and hash, the closed manifest-profile table with the open-time refusals, the object-list hash and the strict masked-build
  check; standard library only, no clock, no network). `tests/test_binding.py` (10 tests, written first) makes it equivalent to the reference: the pinned vector, a corruption corpus (verdict and hash on every case), a 50,000-call parity
  matrix of `profile_from_manifest`, the masked-build/object-list cases and key-order independence. `tools/run_binding_mutants.py`: 23 mutants; the first run detected **17 of 23** (`binding-mutants-run1-17-of-23.txt`): the survivors showed
  that the profile parity covered only the 14 vector cases, that key-order independence was untested, and that two primary checks were shadowed by a backstop (their message is now asserted); final run **23 of 23**.
- `witness_state.py` gained a read-only `StoreView`, the init-time anchor (persisted in `meta`) and the exporter CLI `python -m hmbc_protocol.witness_state --state-dir D --witness-index I (--binding|--evidence)` with the contract of
  EXPORT-LAYOUTS section 1 (exit 0 one canonical line, exit 3 one canonical ExporterError line, exit 2 usage; no write, no RPC). `tests/test_witness_state_cli.py` (23 tests, written first).
- All three test files: 67 tests pass (`tests-green.txt`). The anchor is persisted at INIT only; recording it at each successful open (the D50 text says "the pinned block per chain") is a question for the READY, not decided here.

Done in slice 3a (new files only; pure, no clock/network/key/file):
- `hmbc_protocol/pool_core.py`: the PRODUCTION port of the pinned reference `protocol/f0/vectors/pool_adoption.py` (`classify`, `adopt_recorded`, `decide`, `collection_deadline_ms`, `snapshot_close`, `reproposal_status`) plus `evidence(...)`, which
  assembles the wire members `recordedReports`, `inconsistentReports`, `lateReports`, `adopted` (selection, with the gated `reproposal` action) and `timing` from reports whose signatures the caller has already recovered. Standard library only (`json`, `re`).
  Explicit choices the reference leaves open are listed in the module docstring (canonical content as value identity, smallest signature per (witness, value), only valid reports of this sequence reach evidence, non-negative integer times, a report with an invalid
  signature is never read so a Byzantine witness cannot make the pool raise, no late report after a deadline close).
- `tests/test_pool_core.py` (88 tests, written first; the first run failed at import, `pool-core-run1-red.txt`): a differential against the reference on every report list of up to three reports from 20 distinct reports (8,421 lists), every four-subset in two orders (9,690),
  the exhaustive f <= 1 safety enumeration (3,456 assignments, agreeing assignment by assignment), the time functions on a grid and at the exact boundaries, shape refusals, the production-only choices, and the assembled evidence fed to my independent wire checker
  `check_wire_examples.py` (seven generated scenarios appended to a copy of SUCCESSOR-WIRE.md; four tampered copies must fail it). Same author for reference, checker and port: correlated.
- `tools/run_pool_core_mutants.py`: 47 mutants. Run 1 stopped on an ambiguous anchor in my own runner (INVALID, nothing ran; its one-line output was deleted, it is not a result). Run 2 detected **47 of 48** (`pool-core-mutants-run2.txt`): the survivor P48 is an EQUIVALENT
  mutant (`evidence` validates `proposal_expires_at` and `collection_deadline_ms` validates the same value with the same exception first), so it was removed with a comment and the final run detects **47 of 47** (`pool-core-mutants.txt`). Before that run I had also added
  one test, the members of `evidence` must not alias one another, which a hand-picked alias mutant (P36) required. `pool-core-green.txt`: the four new-code test files together, 155 passed.
- Not covered by slice 3a: signature recovery, the transport, outcome statuses, the retained proposal and the second round, the host clock, any run against a witness. Those are slices 3b and 3c.

Not done (task 2 and task 3 remain): the witness service (independent validation, profile-3 `witness.py`/`ledger.py`/`worker.py` changes, the D50 binding reconstruction and masked-build check from live reads), the worker store's D50 rows and `worker_log --binding`, the pool orchestration (retained proposal, fan-out, outcomes, second round, injected transport and clock; the decision and evidence core is slice 3a, done) and timing evidence, the successor adapter operations and strict parsing, D-4, D-6, the TEST-ONLY hooks
H3/H5/H6 and `testtools/byzantine.py`, the E regressions and export `--check` after those changes, and the source READY manifest. Power loss and OS crash are untested and no durability claim is made for them.
Baseline of the existing E suite before any F change: `e-baseline.txt`.
