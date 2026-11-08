# Scoped CLI/worker verification plan

Before execution: pin partial A2-0071/A2-0072 source at 7915d532ff17c9e782bd23d4887374c01601154f, previous worker b0184e7cca2be4328ccd1ce10e99b3c87eacff28, ledger READY 85c59f588de58a8ff5e87b9fe6f630c9d8c43642, unchanged Agent1 tip 8c0285f. No complete runtime READY is inferred.

1. Read exact owner messages/deltas and scan all fetched communication revisions for divergent file changes; preserve hashes/file-changing commits.
2. Extract exact immutable sources in ignored evaluator scratch. Check historical E deltas, 429 ledger READY entries, 52 F0 pins, and frozen publication bytes. Bracket complete owner inputs, evaluator inputs and review helpers.
3. Fresh isolated tests of CLI, worker recipient handling, sequence bounds, ABI loader, adapter startup/operations/output. Explicitly exclude live test files; install a pre-setup guard against ledger/world fixtures. Do not start a service or chain.
4. Independently compare old/current worker behavior using synthetic public ABI call stubs: profiles 0/1/2 preserved; profile3 legitimate release repaired and invalid recipient still refuses. CLI startup malformed-data controls must exit2 with a JSON refusal and no state; retain deviations as findings rather than alter peer code. Check exact schema/default response pinning and supplied-ABI hashes.
5. If useful, rerun the owner CLI mutation runner: it mutates disposable copies only. A detected mutant requires failed assertions, not crash/timeout. Preserve any failed helper/test trial.
6. Recheck input hashes and latest peers; publish a bounded REVIEW on agent-3. A2-0072 qualifies the prior sequence statement; verify matching source and focused tests, without rerunning the previous ledger experiment.

Classification: tested reconstruction results and synthetic controls only. Shape checks do not prove ledger truth. No full runtime readiness, new E integration parity, process-kill/durability, native chain truth, sign-time/source-state/store completeness, consensus, TLC, timing measurement, F case or gate result. Historical qualified E unchanged; Gate F NOT_RUN/G locked. No peer edits, extra agents, worktrees, external messages or main push.
