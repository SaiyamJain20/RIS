# WAL-aware logical store snapshots — 2026-11-06

C-F1 WORKING; integrated execution remains LOCKED. Synthetic tested
reconstruction/extension of HMBC2020, not an original-paper vulnerability.

New internal `evaluation.store_snapshot_v2.locked_store(database, marker, lock)`
yields a reader with `snapshot()`. Caller explicitly pins all three paths. Hold
its existing exclusive nonblocking flock across before/action/after. One
`mode=ro` SQLite transaction per snapshot; never `immutable=1`. Capture full
schema (excluding physical rootpage addresses), every table and all rows sorted
by hidden rowid, columns, typed values and selected logical header pragmas.
Include SQLite sequence and generated-column values. Snapshot retains exact
INITIALIZED bytes, separate logical/marker SHA256 and supplemental main/WAL
hashes. `require_unchanged` compares logical bytes AND marker bytes; checkpoint
physical churn is allowed. SQLite shared-memory index is recreatable, not state.

Tests demonstrate a committed synthetic refusal-row insertion in WAL changes
logical state while the main database hash misses it. A checkpoint changes
main/WAL hashes and preserves logical bytes. The reader also refuses missing,
corrupt, symlink, nonregular, replaced and unsupported inputs; a marker held-open
descriptor prevents equal-content replacement escaping a snapshot. Writers that
ignore the lock can still write; a control proves the read transaction sees one
consistent table state under such a write. Physical fingerprints are only
supplemental in that case. No application state or lock file is created.

Evidence and reproduction:

- `PLAN.md`: bounded internal design, accepted spec, decisions and task ledger.
- `commands.json` plus lossless `.txt.gz`: exact argv, UTC, exit codes, timing,
  raw/compressed output hashes. Initial missing-module 30ERROR retained.
  First implementation 2FAIL/28PASS came from test harness mistakes (a wrapper
  argument collision and missing context-exit refusal expectation).
- `review-red.txt.gz`: real marker race, 1FAIL/39PASS; `review-green.txt.gz`:
  40PASS after retaining the original marker descriptor. No guard weakened.
- `focused.txt.gz`: 622PASS across snapshot, history, signing, public acquisition,
  context, certificates and schema checks.
- `sensitivity.py`/log: six in-memory bypasses detected. WAL omission, missing
  rows, logical comparison removal, marker comparison removal, shared lock and
  main-hash-only comparison each fail its targeted test. Source unchanged.
- `inputs-frozen.json`: 242 selected inputs and 169 complete execution sources,
  fixtures, current exact peers and tools. All Python helpers completed BEFORE
  this freeze. Full root result and final bracket verification recorded below.
- `communication-provenance.json` and `peer-review.json`: exact fetched owner
  branches, latest file-changing commits and hashes; no mutable-tip execution.
- `REVIEW.md`: separate correlated author review; no extra agents permitted.

Run `.venv/bin/python -m pytest evaluation/tests/test_store_snapshot_v2.py -q`;
focused argv and bare root `.venv/bin/python -m pytest -q` are in commands.json.
Run `.venv/bin/python evaluation/evidence/f/v2-store-snapshot-20261106/verify.py`
to recheck retained evidence and source hashes at this checkpoint. Later source
changes intentionally invalidate the current-tree bracket, not the saved result.
Python3.13.13 / SQLite3.47.2 / Git2.54.0 / pytest9.0.2 / jsonschema4.26.0 /
eth-account0.14.0. No dependency changes.

Agent1 8c0285f unchanged; reviewed ledger85c59f5/429 entries unchanged.
Agent2 b8d57cd adds first successor adapter handlers: E result validation,
top-level v1/v2 relabel and closed error mapping over injected workers. Source
and latest state read; owner40tests/14mutants are NOT rerun/adopted. Four copied
fixtures match cited source bytes. Explicitly NOT_READY; no new ACK/source READY.
All 52 F0 protocol pins and 31 frozen publication payloads verify.

Limitations/next: no actual owner store opened or exporter executed; no
exporter-to-store completeness, native death-fact/source-state truth, arrival
chronology, persistence/power-loss or hostile-filesystem proof. Real raw snapshots
must stay private, since they may contain data redacted by public exporters.
Virtual/WITHOUT ROWID/fully-shadowed-rowid tables fail closed, an internal choice
to revisit against a complete owner READY. Owner path/locking choreography still
requires review. Compose these snapshots with signed history and exporter/native
joins next, then fault oracle and finite model. Existing consumers/defaultv1/
wire v2/published v2.1 bytes remain unchanged. Full owner source READYs/consumer
mapping and a separate complete exact source/tools/config/run FREEZE with affected
ACKs precede integrated services/scenarios. No process/port/lease/liveRPC/newEparity/
TLC/timing/Fcase/gate. Qualified historical E unchanged;32Fcases/GateF NOT_RUN/G
locked. No human action needed. Publication, independent remote SHA and final
lock release receipts are in automation memory; READY delivery follows push only.

## Full root result and source proof

Fresh root: **2307PASS / 423.39s / exit0** (423.71s command wall time).
`audit-after` verifies all242 selected inputs and169 complete discovered
execution-source entries unchanged. Frozen manifest SHA256
`923e4e3f8993d3a60a0ff3393760beea2589dd1e71585a6b0a468371737f6fd6`.
`verification.json` checks exact retained raw/compressed logs, RED/GREEN/review/
sensitivity results, input hashes and no divergent/missing peer communication.
Final fetch remains A18c0285f/A2b8d57cd;367communication paths, no divergence or
ambiguity. This result is unit/regression evidence, not owner suite execution,
new integrated E parity, TLC or any F case/gate. A3-0085 announces the slice.

Task1 implementation and verification complete. Publication/remote/lock cleanup
receipts are written to automation memory after normal owned-branch publication.
