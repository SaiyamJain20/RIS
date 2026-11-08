# Correlated author review: declared governance history

Classification: tested paper-derived HMBC2020 extension and deliberate evaluator
sensitivity controls. The consent allow-list is an explicit reconstruction
choice, not a paper vulnerability. Same-author review only; extra agents are
prohibited. No owner runtime or internal class is imported/executed.

Compared R6 signing rules sections 1-4 and frozen boundary with the composition.
Owner source hashes/file-changing commits are in owner-provenance.json.

- Full signed history runs first, even with no governance records: context,
  owner, fingerprints, ordering, recurrence, death predicates and other typed
  signatures remain checked. This is declared-document scope, not completeness.
- Every live/superseded GovernanceAction digest has exactly one closed capture.
  Each refinement reconstructs nonce and expiresAt from the stored key/digest;
  its PBC observation comes from that digest, with no capture-side override.
- The existing governance checker validates exact raw nonce/version, authority/
  tombstone state, public TTL, action fields, signature and caller approval.
  Approvals are separate caller arguments, not read from the export. The list
  does not authenticate producer configuration, intent or historical policy.
- Repeated number/timestamp facts for each block hash and exact call keys must agree across all
  governance captures. Identical shared facts pass. Safe intervals also require
  one hash per height; fault/clear labels retain their restricted interpretation.
- A-B-A recurrence, expiry refinements, ADD/REMOVE/SET and q2 fixtures pass.
  Empty SET/eight-admin/canonical-field edge controls are inherited from the
  separately executed governance-state tests; no quorum is inferred from q2.
- bit1/bit5 death exclusions are preserved; no native death verification occurs.
- Eight in-memory bypass controls preserve legitimate inputs and independently
  expose omitted coverage/state/history checks, conflicting headers/getters,
  same-height forks, falsely safe labels and erased death exclusions.

No product changes were needed after the first GREEN. The initial 42 RED
failures were all missing-module failures, verified from retained output. RED
pins its test bytes and initial HEAD; initial RED/GREEN and mutant trial predate
complete input brackets. Final focused/mutant/root results use the bracket.
No branch-coverage measurement, exhaustive mutation, model or performance claim.

No unresolved product-code issue found in this correlated review. Missing
runtime READY/mapping/execution ACKs, source-state duties for AccessDecision/
GrantReceipt, raw governance acquisition, producer/schema/path/lock completeness,
finite model and fault oracle remain unfinished. A3-0096/97 stay open. Historical
qualified E unchanged; all 32 F cases/Gate F NOT_RUN; G locked. Supplied state and
unsigned observations establish no RPC truth, latest head/ancestry, sign time,
producer misconduct, complete store/export, persistence, consensus or a gate.

Final fresh results: 42 new tests, 286 focused tests and 2763 root tests PASS.
Eight bypass/valid control pairs pass. All recorded direct children are STOPPED.
899 owner / 258 local / 5 helper / 8536 carried inputs match; 52 F0 pins / 31
frozen payloads match. 393 communication paths have no divergence; peers unchanged.
The complete runtime bracket precedes explanatory/shared documentation edits.
