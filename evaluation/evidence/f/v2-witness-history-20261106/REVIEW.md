# Correlated author review

Reviewed production additions, the complete test file, accepted BOUNDARY export
requirements and the exact revision9 layout text/reference at Agent2's fetched
305ca39d48b5cb2fe3f561b20c31a103189cbc19. No peer code is imported or executed.
Extra agents are prohibited; this review is by the implementing author, weaker
than independent review. No claim of independent validation or gate completion.

The added single-signature entry point retains reconstructed membership/version,
fixed domain and embedded-ledger checks. Existing certificate verification still
requires the exact observed quorum. Each record's K/effect/liveness is rebuilt;
signature owner, digest and domain are all checked, including later liveness
digests and superseded records. Input objects are preserved.

Generation chains use append seq per key followed by one live row. The explicit
orphan check remains active during faults/clears. Adjacent equal effects refuse;
nonadjacent A->B->A passes with new signatures. Both number and timestamp order
are checked in declared safe intervals; equal block numbers require equal hashes.
All death fields/type/ALLOW-only restrictions are schema checked; the independent
verifier recomputes expiry and sequence inequalities. Fault reasons, current last
observation, clear append order and baseline bounds are checked. Bit1 checkpoint/
decision-sequence and bit5 receipt deaths are explicitly excluded from baseline
evidence. The result deliberately says *declared* safe-ledger interval.

Review added49 controls to the initial90, all139 PASS. Seven deliberate in-memory
bypasses admit records that the real implementation refuses. The first sensitivity
helper used a noncanonical signature and did not catch its schema exception;
the second used one stub result for every record. Corrected only the helper:
use a canonical signature by the wrong configured owner and bypass only that
one verification. Both failures remain in command evidence. Initial peer helper
mistakenly selected README/draft as newest outbox; corrected to numbered direct
outbox paths. Four copied peer fixtures match their cited source bytes exactly.
The first proof run also caught an author command/count mismatch: the focused
command included27 extra v2.1 tests (609 PASS), while the proof specifies the582
core selection. Preserve the609 result and failed proof, then run the intended
582 selection. No source/test/proof-helper change or freeze invalidation is used
to resolve this bookkeeping error. The root suite includes those27 tests too.

No production correctness issue found in this review. Native ledger truth,
WAL-aware logical-row/marker-byte completeness, persistence/power-loss behavior,
exporter command stdout/stderr/refusal behavior and fault-oracle/formal-model
execution are explicitly outside this slice and still required. The declared
INITIALIZED object check is not a physical marker-file read. No integrated
execution, owner source READY, new E parity or F gate is inferred.

Internal ruling: equal-height clear-baseline comparisons require matching hashes
as well as number/time bounds. This follows the evaluator's same-block raw-hash
join obligation and is stricter than the owner's layout-only reference; it does
not rewrite the wire/checker. A rejected baseline needs raw chain reconciliation,
never promotion to safe evidence by merely changing the reported hash.

No deferred cosmetic work; no peer module, interface/dependency, frozen payload,
historical evidence, service, archive, worktree or main-branch change.
