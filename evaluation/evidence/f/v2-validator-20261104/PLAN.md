# C-F1 successor validator slice

Use the accepted F0 candidate2 boundary and source migration, without changing
their published bytes or the existing E validator/consumers. Implement an
explicit `evaluation.schema_v2` entry point for shape plus declared semantic
checks: integer/signature encodings, inherited E ordering, governance admins,
immutable ranges and object-list hash, D50 document/profile/set consistency and
binding fingerprint, and collection/retry selection/timing self-consistency.

Write paired valid/invalid tests first, retain the RED log, implement, run focused
checks then the root evaluator suite with source hashes before/after. Read the
fetched owner branches by exact file-changing ancestry, verify owner manifests
at their own commits, and retain commands/exits/tool versions. No source READY
or execution ACK is inferred from a commit subject or an unchanged outbox.

Ruling: preserve E validator and all frozen/proposal artifacts. Add an isolated
consumer instead of switching a global schema path; costs one additional module
but preserves reproducibility. Reuse its encoding predicates without mutating
its format registry. No new packages, assumptions or wire fields.

Ruling: self-review in this session because the user forbids extra agents.
Review is correlated and weaker than an independent reviewer. No worktree.

Stop condition for this checkpoint: tested owned validator with explicit coverage
and limits plus immutable peer notice, reviewed exact-path agent-3 publication.
Fault oracle/model, source/ledger reconstruction, exporter history/completeness,
WAL snapshots, signature recovery and runtime joins remain next slices. All32 F
cases stay NOT_RUN; no services, integrated execution, formal-tool run or gate.
