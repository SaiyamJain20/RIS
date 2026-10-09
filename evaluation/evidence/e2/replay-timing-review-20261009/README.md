# Replay timing diagnosis; runtime revision still pending

This run performs fresh read-only analysis of the preserved failed A3-0041 trial.
It starts no service, makes no live RPC call and changes no runtime module.
E/RQ1 remains active; gate E NOT_RUN, F/G locked. The repaired composite remains
BLOCKED/incomplete; the previous paper comparisons remain measured reconstruction
results. No additional catalog comparison is completed.

| Profile | Probe seconds | RPC calls | Recorded subprocess seconds | Outside-subprocess seconds |
|---|---:|---:|---:|---:|
| paper-strict | 10.081083 | 63 | 1.981843 | 8.099240 |
| paper-minimal | 10.001666 | 63 | 1.900507 | 8.101159 |
| repaired-e | 10.210406 | 63 | 2.109077 | 8.101329 |

Each probe also exports the worker twice. Of its63 RPCs,18 are chain identity
reads and25 are block reads; only8 are contract views. These are deliberate safety
checks, not ledger latency. Command elapsed intervals start inside record_command,
after RpcClient's first Cast hash; they exclude both full binary hashes and other
Python/JSON/ABI work. Thus the remainder above is measured outside recorded
subprocess intervals, not proven hash time. The historical source calls sha256
twice per RPC (126 full binary reads per probe). A fresh host microbenchmark of
the same77,443,976-byte pinned binary and read_bytes+sha256 primitive used10 warmups
and30 repetitions: median0.061271s per hash. Multiplication suggests7.72s for126
hashes on the current host. This supports the overhead hypothesis but cannot
recover historical per-hash timings, establish causality alone or predict a live fix.
No production performance/distribution or worker-clock equality claim.

Reproduce with `/home/karma/Documents/RIS/.venv/bin/python
evaluation/evidence/e2/replay-timing-review-20261009/analyze.py --prior-output
/home/karma/.codex/automations/ris-agent-branch-monitor-and-continuation/runs/20261009T044325Z/real-e2-output
--cast /home/karma/.local/share/hmbc-tools/foundry-1.8.5/cast --output <new-path>`.
Exact argv/cwd/start/end/exit/output digests: analysis-final-command.json, exit0;
timing.json contains source hashes, all selected command intervals and every hash
sample. Source inputs are hashed before and after analysis; unchanged assertions
passed. Initial diagnostic failed exit1 because it guessed --state instead of the
actual --state-dir; analysis-command.json/stdout preserve it. This is a helper
failure, not a research finding. Initial source-verification traversals also failed
on a mapping shape and missing local peer inventory; final correct proof verifies
85 original plan files,303 immutable owner blobs and15 frozen paths.

Exact new reviews: A1-0055 at2d2d386e4e164baf152dc3d22446bba10e85c8ae,
SHA334f61099af628384d95dd147d5ff7d372ea2a9182f8adf5b62a48999caf57f2;
A2-0035 at7b00f9faa4ca889a93a1d98467fcda72e094128b,
SHA6486c9d6f2ffcac4d4a867c8da0e7920264e3a76590ad625a4ca5b56cb587c95.
Both fetched owner ancestry/header/scope verified;162 communication paths scanned
by newest file-changing commit and owner rules, no incomparable shared conflicts.
Neither review is a new plan or report ACK. Original released ACKs stay immutable.
Python3.13.13, Cast1.8.5/tool hashes in versions.json and source-verification.json.
Synthetic fixtures, paper-derived reconstruction, symbolic crypto/safe ledgers/
trusted worker; original expiry and custody unchanged. No new key/seed/configuration.

Ruling: first revise the owned public snapshot collector to group contract views
at one explicit block per chain, with chain/block/ABI validation around the whole
group and individually retained call/return bindings. Preserve the existing full
before/after snapshots, including the idle worker, before first release. This
can remove redundant identity/latest-block checks without caching binary hashes
or changing the worker. RED/GREEN controls must reject wrong chain, reorg before/
during reads, ABI movement and changed request/grant/nonce/history; all positive
and expiry controls remain required. Cost: fewer checks between individual views,
acceptable only with bounded explicit common-block checks, tested refusal and a
new source-complete plan reviewed by BOTH peers. This is a proposal, not implemented
or accepted execution permission.

Ruling: do not simply postpone latest-state snapshots until after release.
RELEASE_INTENT/RELEASE_SENT and outcome logs legitimately change; treating that
later state as replay equality would corrupt the oracle. A deferred collector
would need explicitly pinned historical reads/log boundaries and a separate
pre-release worker observation. Cost: preserving current pre-release evidence
may require another timing revision if grouped reads are insufficient. Trace
deferral alone is unlikely to remove the measured repeated-check overhead.

Author self-review only per explicit no-extra-agent instruction, weaker than a
fresh review. No unit suite rerun for this diagnostic slice, no claim of a runtime
fix or completion. Existing checkout, no worktree/peer edits/main/history rewriting.
Scheduled exclusive lock and separate coordinator flock held before fetch through
publication; finally cleanup/publication recorded externally and in automation
memory. Prior unrelated untracked scheduled-run evidence stays unstaged.45 catalog
comparisons, live mutants/windows/report/all3 exact report-source ACKs/every Gate E
criterion still need completion. No human action required.
