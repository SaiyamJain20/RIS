# Partial witness RPC review — 2026-11-06

C-F1 remains WORKING. Paper-derived HMBC2020 reconstruction; synthetic inputs.
Pin A2-0067/0068 at 0e58f1da659f48ffd39b6af138acf194b0ae111f and the
14-path delta from 0297adb6e784b9667befbc6330e1dfcb3ec81e3e. This is
coordinator review provenance, not a new owner runtime READY.

1. Verify complete snapshot, previous READY, F0/interface/ledger pins and exact
   communication file provenance; retain source hashes before and after tests.
2. Check owner unit tests and affected witness-service tests with a no-live
   fixture guard. Do not execute the expanded live test file or deploy anything.
3. Run raw replies through the real carried Chain and new RpcWitnessView with
   injected RPC, retaining canonical successes and explicit transport refusals.
   Hypothesis: transaction shape errors can escape LedgerUnreachable because
   decode accesses tx.get outside _guard, while inherited quantity/ABI parsing
   remains permissive. No authorization exploit is inferred from parser gaps.
4. Run the owner's focused mutation controls and default export check. Keep all
   owner live results as read evidence, never independently adopted counts.
5. Publish scoped REVIEW and restartable state; exact full runtime READY/mapping
   and separate execution FREEZE ACKs still precede integrated services.

No peer edits, extra agents, worktrees, new dependencies, frozen-wire changes,
F case, timing, consensus, E parity or gate result. G remains locked.
