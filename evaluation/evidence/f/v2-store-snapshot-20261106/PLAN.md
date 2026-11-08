# WAL-aware store snapshot slice

Execute inline with executing-plans, TDD, python-testing and verification-before-completion.
Spec: interfaces/v2/BOUNDARY.md, read-only exporters section; accepted F0 candidate2.
Classification: synthetic tested reconstruction/extension; no paper vulnerability.

Design: new internal evaluation/store_snapshot_v2.py exposes
locked_store(database, marker, lock), a context manager yielding a reader with
snapshot(). Hold an exclusive nonblocking flock on an EXISTING owner lock across
before/action/after; never create or unlink store files. One mode=ro SQLite
transaction per snapshot, never immutable=1. Retain schema and every table row in
rowid order, typed values, exact marker bytes and supplemental main/WAL hashes.
require_unchanged compares logical bytes AND marker bytes, never physical hashes.

Ruling: explicit caller-pinned paths and generic row capture avoid adopting an
unready owner's private SQL schema. No exporter-to-store mapping in this slice;
that needs the complete owner source READY. No consumer/interface/dependency
change. Missing lock, unsupported virtual/WITHOUT ROWID tables, hidden rowid fully
shadowed, corrupt/missing files and raced file identities fail closed. These
are internal evaluator choices; if a READY needs unsupported SQLite features,
extend with separate tests before consumption. Locks constrain cooperative
writers only. Keep real raw snapshots private; tests contain synthetic rows.

Ruling: existing checkout/no-extra-agents instructions override skill worktree
and reviewer dispatch defaults. Self-review is correlated, with retained controls.
The autonomous continuation and accepted spec authorize routine internal design
without a new human design approval round. No new shared contract is proposed.

## Task 1: capture and compare synthetic store state

Files: evaluation/store_snapshot_v2.py; evaluation/tests/test_store_snapshot_v2.py;
this evidence directory; Agent3/shared live status and own outbox.

- [x] Write tests for WAL-only state change, checkpoint invariance, exact marker
  bytes, schema/all tables, typed values, rowid order, lock serialization/release,
  read-only connection, unsupported/missing/corrupt/raced files.
- [x] Observe and retain missing-module RED, then implement minimal internal API.
- [x] Focused GREEN; separate author review and deliberate sensitivity controls.
- [x] Finish all evidence helpers, freeze actual selected and complete discovered
  source inventories, run root tests, compare source brackets.
- [x] Refresh peers/pins, record evidence/limits/next work and review exact staged
  paths for normal origin agent-3 publication. Final push/remote/lock receipts
  belong in automation memory after publication.

Pre-flight: sole task, no inter-task interface dependency. No integrated service,
native ledger fact, exporter completeness, durability/power-loss, E parity,
TLC/F case/F gate/G result can be inferred from these tests.

Task1: implementation/verification complete. Fresh622focused and2307root PASS;
242selected+169complete sources unchanged. Full root423.39s/exit0. Review fixed
marker identity race after1FAIL/39PASS. Six in-memory bypasses detected; no source
changed after freeze. Publication preparation follows; final receipt in memory.
