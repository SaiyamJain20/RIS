# Witness signing history implementation plan

> Execute inline using executing-plans, TDD and verification-before-completion.

Goal: independently check declared witness-history consistency, deployment-bound
single signatures and the missing live-successor completeness rule.
Spec: interfaces/v2/BOUNDARY.md lines196-242 and exact pinned EXPORT-LAYOUTS
revision9 in the accepted F0 plan. Synthetic HMBC2020 reconstruction only.

Approach: a new internal evaluation/witness_history_v2.py composes the independent
schema/context/signature checks. Extend signing_context_v2 with one explicitly
caller-owned single-signature entry point; quorum verification remains separate.
Reconstruct each message from key/effect/liveness. Check fingerprints, record
ordering, digest uniqueness, death inequalities, per-generation order and equal-
block hashes; require every superseded K to have its live successor. Preserve
A->B->A. Label fault/clear intervals and bit1/bit5 death exclusions explicitly.
Reusing an export's claimed context would trust the object under test. Importing
peer private classes would violate the public boundary. Neither is used.

Scope limits: no WAL/marker-byte/store completeness join, native ledger truth,
arrival chronology, running consumer switch, source READY or execution authority.
No shared interface/dependency/owner module/frozen payload change. No additional
agent/worktree. Existing accepted design and autonomous continuation instructions
authorize this slice without reopening human approval. Review is correlated.

Review focus: wrong indexed owner; valid signatures under wrong embedded/domain
identity; deleted live successor; legal nonadjacent effect recurrence; equal
block number with different hashes; faults/clears and bit1/bit5 exclusions.

## Task 1: signed history verifier

Files: evaluation/witness_history_v2.py; evaluation/signing_context_v2.py;
evaluation/tests/test_witness_history_v2.py; this evidence directory.
Consumes: caller manifest/observations/expected_owner, independently reconstructed
B and published v2 schema; no peer runtime imports. Produces:
verify_signed_history(evidence, *, manifest, observations, expected_owner,
compiled_max_admins=None) -> counts and explicit declared/exclusion labels.

- [x] Write positive four-type/E/F/q2 fixtures using real vector-derived signatures;
  adversarial signature, orphan, recurrence, ordering, fault and mutation tests.
- [x] Run focused test file; expected missing-module RED, retained losslessly.
- [x] Implement the internal API and single-signature context helper.
- [x] Focused GREEN; deliberate bypass controls; separate author review.
- [x] Finish evidence helpers; freeze selected and actual complete execution
  source inventories; run full root pytest and prove no source drift.
- [ ] Refresh exact peer communication/source provenance and immutable pins;
  handoff, complete staged diff review, normal agent-3 push and remote verification.

Pre-flight: sole task; no inter-task interface dependency. Existing bound
certificate count must remain exact quorum; the new single-record function is
separate and never allows the artifact to choose its owner.
