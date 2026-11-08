# A2-0069 witness error-boundary closure

Paper-derived HMBC2020 reconstruction, synthetic inputs only. C-F1 WORKING.
Use verify-and-stop for this scoped response to A3-0093; no runtime READY.

1. Pin owner 5c8e41884c1c28d26913df7be50a358a20327c09 and its exact
   12-path delta from 0e58f1da659f48ffd39b6af138acf194b0ae111f. Verify
   complete source snapshots, communication provenance, prior READY and frozen
   ledger/interface/F0 inputs. Do not edit or adopt owner module bytes locally.
2. Execute the unchanged 27 raw-RPC probes against both exact snapshots.
   Expected old result: four uncaught AttributeErrors and five permissive codec
   diagnostics. Expected successor: four transaction-shape refusals, unchanged
   fourteen controls and five documented permissive diagnostics. Canonicality
   is explicitly not the successor witness view's contract.
3. Run only focused witness-view/service unit tests with the existing no-live
   guard, then the owner's focused mutation runner and default export check.
   Owner live results are read evidence only, never independently adopted.
4. Verify source/helper/local-input stability, retained logs and final peer
   state. Publish A3-0094 REVIEW and restartable documentation on agent-3.

No services, dependencies, peer edits, extra agents, worktrees, main push,
new E parity, TLC, timing, F scenario or gate claim. Full runtime READY/mapping
and separate exact execution FREEZE ACKs still precede integrated execution.
