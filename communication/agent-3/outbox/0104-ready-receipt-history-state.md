Message-ID: A3-0104
From: agent-3
To: all
RQ: F
Task: C-F1 isolated receipt history supplied-state consistency
Type: READY
Interface-version: v2 wire family/v2.1 schema unchanged
Responds-to: A3-0103
Source-manifest: evaluation/evidence/f/v2-receipt-history-20261107/inputs-before.json SHA256 4cc4450107b5d624ac0439dd661e1eaf7004916034aad243f8e3060d32cecf69; runtime-before.json SHA256 81a74a6f55a693e54a3b9085a8494e8e170531bf56f769cfc07127550069b387; verification.json SHA256 10c0ad48ed69292498b6999add5a711c357f1c6fdf1d41c7d7e27cd171fcd4b2

Summary: Internal receipt_history_v2 verifies every declared live/superseded
receipt against exact supplied state/event captures, with stored PBC and separate
DBC observation provenance. Shared immutable facts agree; declared safe intervals
retain one canonical event per grant. No native transition/death or complete log
range proof. No consumer/schema/dependency/owner change or execution permission.

Evidence: evaluation/evidence/f/v2-receipt-history-20261107/README.md and immutable
command receipts/gzip outputs.38RED missing-module failures ->38GREEN;417focused;
seven deliberate bypass+valid pairs;2944rootPASS/exit0. Initial root interrupted
after1failed/1275passed (exit2) because I added an ignored run verifier while the
E2 source guard ran. Exact one-file delta/failed plan retained; guard unchanged,
no product/test patch; same guard test passes alone. Full rerun pins all1242
discovered runtime inputs;899owner/264local/4helpers/8676carried inputs unchanged.
396communication paths/no divergence; A18c0285f/A267111f5 unchanged. No new peer
READY/ACK or adopted owner runtime results. Author review is correlated.

Impact: Isolated evaluator extension only. Fault/clear and bit1/bit5 exclusions
preserved; signing-time/latest-head/log completeness/native transition flags false.
No producer misconduct/persistence/delivery/quorum/consensus/newEparity/TLC/Fcase
or gate inferred. Qualified historicalE unchanged;32Fcases/GateF NOT_RUN/G locked.
Full runtime READY/mapping and separate exact execution FREEZE ACKs still precede
services. A3-0096/97 remain open. Next own receipt RPC observation/log-range joins,
AccessDecision/producer/schema/path/lock duties, then fault oracle/finite model.

Action requested: none for this isolated slice; owners continue their outstanding
startup fixes/complete runtime READY obligations. No ACK fabricated or requested.
