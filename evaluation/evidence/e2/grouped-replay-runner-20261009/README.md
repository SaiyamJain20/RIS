# Grouped historical replay collector — C-E2 owned revision

Paper-derived HMBC2020 reconstruction, synthetic inputs only. This is a tested
collector revision, not live integration, paper behavior, a vulnerability, or a gate.
A3-0044 full plan SHA-256 `1b3cf7cd13ea8b1436396f8cc6268bbbdcae753661730290043ee144c1804a32` binds86 runtime/config/fixture inputs,
ledger195 entries at933d2a75483a08e7374cd417a6cf8a9e5c13a33c/c7b7dd51.. and
protocol108 entries at0716a8e2d46f985f35a612d42acaae02ab8701a4/d16ddad8..
(complete pins/entries/tools/packages/environment/custody/ports in integration-plan.json).
All303 immutable Git inputs and15 frozen v1 copies verify;78 Python sources stable.

Executed brief: PLAN C-E2 and A3-0043's grouped-reader design. Ruling: use existing
agent-3 checkout and author review under human no-worktree/no-extra-agent rule;
cost: no fresh independent reviewer. Ruling: retained whole snapshots before
release; cost: grouping is not yet shown sufficient for the repaired expiry window.
Ruling: group checks use boundary identity under existing safe-ledger assumptions;
cost: a transient change restored between checks is undetectable. No new paper/key,
cryptographic, dependency, peer module or interface assumption. No model change/rerun.

Reader: one block per chain/snapshot; chain checked on both boundaries; selected
block re-read before/after; all selected ABI hashes checked before/after.16 query
limit and common10s timeout; individual canonical ABI-bound rows saved only after
successful group. The replay collector selects ALL deployed roles, queries logs
from0 through group block, and writes before/after-blocks.json anchors separately
because mined replay advances DBC blocks. The entire grant/request/nonce/access/
worker/contract-history payload still compares exactly. Both idle-worker snapshots
precede release/completion/outcome. No arbitrary new reference, expiry extension,
worker operation, crash/restart/clock change, or binary hash cache.

Fresh RED/GREEN: group14 missing-method failures→39 reader+transaction passes;
collector3 missing-anchor failures/43passes→85 combined passes; plan1 missing recipe
failure→28passes. Complete `.venv/bin/python -m pytest -q`:599passed/108.31s pytest,
108.5501s measured wall/exit0. Initial shell-tail metadata limits preserved in
initial-command-limitations.json; navigation helper errors are not research findings.
Canonical return, wrong-chain-before/during, block drift before/during, ABI before/
during, malformed history, finite deadline, scope, nesting, budget/body failures,
closed group and all3 positive/mutated transaction controls exercised. No live reorg.
Fixtures: existing e1 pinned public ABIs, synthetic Replies/Model and TEST-ONLY
bootstrap users; versions.json records fresh tool commands/hashes and the pytest version. Source-bracket.json records final stable hashes.
Author-review.json is self-review only.

Actual `.venv/bin/python -m evaluation.e2 --plan
 evaluation/evidence/e2/grouped-replay-runner-20261009/integration-plan.json --output
 /home/karma/.codex/automations/ris-agent-branch-monitor-and-continuation/runs/20261009T054323Z/no-ack` exits2/BLOCKED on absent both NEW exact peer ACKs,
no services/cases/snapshots. no-ack-command.json and no-ack-manifest.json preserve it.
No active lease; old A3-0041 RELEASED. New A3-0044 REQUESTED, not accepted.

communication-provenance.json selects164 latest file-changing revisions with
exact commits/hashes, no incomparable conflict. Owner STATUS/HANDOFF read externally.
A1-0055/2d2d386/334f6109.. and A2-0036/d408669/67a548eb.. read; both scoped REVIEWs,
not execution/report ACKs. Source choices preserve their exclusions and owner pins.
Historical paper2 replay success and repaired first-release EXPIRED remain unchanged;
no measured reduction in probe time or repaired composite success. Historical6
recovery/expiry+3 duplicate controls retained;45 comparisons still need completion,
plus live mutants/windows/report/all3 exact same-report-source ACKs/every E criterion.
Four paper crash classes remain BLOCKED/unproved. No delivery, ABE, consensus,
power-loss theorem or authors executable reproduction; symbolic/safe-ledger/trusted-worker.
F/G locked. No human action needed: await both exact plan ACKs and verify sources
before live3, then finish remaining E work. Publication/guard finally outcome at
/home/karma/.codex/automations/ris-agent-branch-monitor-and-continuation/runs/20261009T054323Z/publication-and-cleanup.json and automation memory.

Publication retry: staged whitespace check first exited2 on pytest traceback trailing spaces; no commit/push, finally locks released. Reacquired guards, retained raw collector-red output externally and published whitespace-normalized copy with both hashes in its command record. No source/plan/test changes or retesting needed. publication-retry.json retains the failure.
