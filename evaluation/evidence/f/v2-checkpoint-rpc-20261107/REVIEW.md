# Correlated author review

Scope: new internal checkpoint_rpc_v2, its tests, and the acquisition plan.
No additional agent was launched; the user forbids extra agents. This is weaker
than an independent reviewer and establishes no integrated execution readiness.

The collector verifies the full signed history before RPC, including other signed
types, then checks exact per-digest capture coverage with the existing state/history
verifier. Explicit selection is by digest and a nonblank caller reason; target
observation is taken only from the indexed history entry. Provenance labels the
unsigned observation bases and always keeps signTimeEstablished/latestHeadEstablished
false. Reasons are caller assertions, not independently validated provenance.

Source/head/DBC reads use exact hash keys and frozen ABI hashes. Both endpoints'
chain/genesis/deployment/anchor identities surround all cross-chain reads; headers
are rechecked after getter reads. Canonical hash comparison is required only for
safe intervals; fault/clear scope and bit1/bit5 death exclusions pass through.
Recurrence, expiry refinements and empty checkpoint subsets remain supported.
Budget and deadline refusal, state/identity/header mismatch, and RPC exceptions
retain partial transcripts; completed result.json appears only after success.
Original caller arguments, transport identities/URLs and ABI paths/bytes are
compared after capture. Neither numeric-call fallback nor latest-head lookup exists.

Six deliberate bypasses preserve their valid controls and expose duplicate selection,
state verification, trailing identity, canonicality, final header consistency and
selection-drift checks. The initial header probe changed BOTH source and selected
head; the selected-head timestamp check correctly refused it before the intended
bypass. The corrected probe changes only the source hash with no selected timestamp.
Its initial source/log and exact corrected command are retained. Product code did
not change after first implementation. No unresolved critical/important finding.

Decisions: the separate collector follows the preceding slice boundary; sharing
history_rpc_v2's pure _header parser avoids a second raw-header interpretation.
The acquisition choreography is kept local to avoid altering the prior consumer.
No claim of branch coverage was measured. Deadline enforcement is cooperative for
injected clients; real RpcClient has its own timeout. A consistently lying endpoint
or restored inputs between comparisons remains outside this consistency check.
Filesystem write/cancellation failure can leave a pending/collecting transcript;
only result.json is a completed capture. No durability experiment was performed.

Explicitly unproved: actual validation/sign time, historical latest head, chain/RPC
truth, cross-height ancestry, producer rule violation, native death joins, complete
store export, persistence, consensus, E parity, TLC, scenario or RQ gate results.
These are continued live dependencies, not defects inferred from unsigned exports.
