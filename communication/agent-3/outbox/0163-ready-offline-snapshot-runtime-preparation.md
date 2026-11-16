Message-ID: A3-0163
From: agent-3
To: agent-1, agent-2
RQ: F
Task: C-F1
Type: READY
Interface-version: v2 wire family / v2.1 unchanged
Responds-to: A3-0162, A1-0144
Source-manifest: evaluation/evidence/f/snapshot-materializer-20261116/source-inputs.sha256 (SHA-256 identity in receipt SHA256SUMS)

Summary: offline snapshot preparation and selected runtime inventory component;
92 focused checks pass (42 new), no owner suites/services/cases executed.

Evidence: evaluation/evidence/f/snapshot-materializer-20261116/README.md and
commands.json retain fresh commands, exit codes, synthetic controls, source/tool
hashes and limits. Separate shallow Git store retains required historical
cat-file/archive inputs without original-repository dependency; source extraction
rejects nonregular/unsafe inputs and verifies bytes/modes. Selected runtime tree
and lexical tool verification detect drift; runtime closure stays false.

A1-0144: verified all six attachment hashes at the exact fetched publication.
Existing executor already excludes ledger/out and ledger/cache, matching your
observed generated paths. Peer command results are not rerun here or promoted to
F-case results/ACKs. The new DRAFT snapshot plan separately pins historical
protocol test archives91add8cc.. and9d6911d9..; real sources not materialized.

Impact: component implementation READY only, coordinator still unfinished.
Report/packet/plan bytes preserved; DRAFT/false, all32cases/Gate F NOT_RUN/G LOCKED.
No interface/dependency or owner module change. Same-author/correlated self-review.

Action requested: none from peers/human for this component. Agent3 next wires
source/object/runtime manifests into stage-3 recipes and establishes runtime
closure, then completes native acquisition/oracles/post-bracket/E regression and
the exact executable FREEZE. Actual services/cases require exact owner ACKs.
