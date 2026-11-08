# Retrospective checkpoint RPC capture

Execute inline under the accepted C-F1 design and the user's continuation.
No extra agents, worktrees, peer edits, services or frozen-interface changes.

Goal: acquire the exact raw state needed by checkpoint_history_v2 for every
declared checkpoint digest. Existing consumers remain unchanged. This is a
paper-derived HMBC2020 extension with synthetic transports for verification.

Approaches considered: extend history_rpc_v2's native-death scope, or add a
separate checkpoint collector. Choose the separate collector to preserve the
existing consumer and distinguish state checks from native death checks.
Reuse its established identity/header/receipt choreography locally; do not
generalize or refactor the existing collector in this slice.

The internal collect API takes the existing history/context/ABI/RPC pins and
an exact selections list: {digest, pbcHead, reason}. A nonempty reason is caller
provenance only. DBC observation comes from the history entry, with its exact
collection/row/digest index retained. Both PBC head and DBC observation are
explicitly labelled unsigned retrospective selections, never actual sign time
or proof that the head was latest. No latest RPC lookup or numeric call fallback.

Plan source/head/target headers and the seven R6 getters by exact hash. Share
identical keys, refuse inconsistent planned header facts. Bracket ALL reads on
BOTH chains with chain/genesis/deploy/anchor identities; recheck headers after
state reads. Safe intervals require canonical hashes, fault intervals preserve
separate fork hashes. Compose the existing checkpoint-history verifier and
preserve fault/clear labels and bit1/bit5 exclusions. Empty checkpoint subsets
still check complete declared history and both endpoint identities.

Checklist:
- [ ] Write tests and retain missing-module RED before product code.
- [ ] Implement exact selection/planning, bounded capture and partial receipts.
- [ ] Verify recurrence/refinements, state failures, endpoint/header changes,
  malformed selections, budgets/deadlines, input/ABI drift, faults and provenance.
- [ ] Run narrow bypass controls and focused/root regression with exact brackets.
- [ ] Review fetched communication provenance, document evidence and remaining
  limits, publish exact owned checkpoint on agent-3 and verify remote/locks.

Review focus: no inferred validation/sign time, no dropped superseded digest,
no caller override of target observation, no cross-chain unbracketed reads,
no safe relabelling after fault/clear, no result.json on failure. Input/source
brackets and receipts must remain immutable. Review is correlated author review
because the user forbids additional agents.

No RPC authenticity, historical latest head, ancestry, producer rule violation,
store completeness, persistence, native death, new E parity, timing/consensus,
F scenario or gate claim. Complete runtime READY/mapping and separate exact
execution FREEZE ACKs remain prerequisites for integrated services. G locked.
