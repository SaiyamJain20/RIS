# Consolidated Agent 2 runtime review

Current task: C-F1, HMBC2020 paper-derived reconstruction, synthetic fixtures.
Review A2-0076/0078/0079 and the supplied A2-0083 TEST-ONLY delta together.
No peer edits, product changes, services, integration freeze or F/G result.

Acceptance for this checkpoint:
1. Pin complete owner snapshot, original READY manifest, cumulative deltas,
   file-changing communication provenance and frozen dependencies/interfaces.
2. Read the entry-point/supervisor/store changes and contract mapping. Run all
   safely selectable non-live protocol tests, with explicit fixture/dynamic/live
   exclusions and a guard that refuses native chain/build process execution.
3. Independently reproduce the old startup refusals using the fixed owner tests;
   check cooperative locks, hot-journal recovery, random-SIGKILL tests and narrow
   owner mutation runners. Retain failure/equivalent controls and actual counts.
4. Compare exact source hashes before/after. Publish a scoped review, dependency
   state and next runner work on agent-3; verify normal push and release locks.

This can accept only the tested isolated scope. Native E parity, live transport/
ledger compatibility, a whole runtime acceptance, signing-time/complete history,
power-loss durability and integrated F scenarios remain unproved. An author's
numbers are not adopted by reading them. The prior TLC execution denial remains;
no retry/rewrapping. Correlated author review; no extra agents.
