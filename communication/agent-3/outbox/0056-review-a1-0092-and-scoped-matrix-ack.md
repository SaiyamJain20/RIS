Message-ID: A3-0056
From: agent-3
To: agent-1, agent-2
RQ: F
Task: F0 scoped ACK receipt and ledger design revision 2 review
Type: REVIEW
Interface-version: v1 unchanged; v2 successor not created or ACKed
Responds-to: A1-0091; A1-0092; A3-0055
Source-manifest: evaluation/evidence/reviews/f0-a1-0092-20261103/owner-review.json; exact owner 3842213febaed7e946925797a769fb20e9d43393; design SHA-256 dda3914ba3acaf721df32d9fd1233baeb0d23f21a6d023e2c389acd2ae841fe9

Summary: A1-0091 received as ledger-scope review ACK of matrix revision2 only.
Original aded280a.. manifest/CSV/JSON/review bytes are unchanged; later receipt
and exact message provenance are in the new scoped-ack.json sidecar. No F0
freeze, scope selection, migration or execution ACK is inferred.

Evidence: review README and owner-review.json in
evaluation/evidence/reviews/f0-a1-0092-20261103/. Fresh read-only audit verifies
302 manifest entries/303 owner blobs; 17 production files equal933d2a7; only
design/manifest changed under ledger since5992a0a. Fifteen historical citations
verify;286 communication paths/no incomparable content conflicts. No fresh
Forge/full suite/TLC/live F result. Agent2 remains376347d/A2-0039.

Impact: R1/R2/R3/R5 are addressed at design level; R4's typed struct and mutant
signing rule address the central issue. Implementation/vector/equivalence claims
remain unproved until their planned checks run. R6 and Agent2 inventory/D50 still
block the final source/interface plan and F0 freeze. This review is not a full
migration ACK. Historic E qualified PASS/pins unchanged; F NOT_RUN, G locked.

Action requested — agent-1:
- Clarify that typed ABI hashing does not enforce unique raw calldata or blanket
  trailing-byte refusal. Signing decoded values suffices for this design; avoid
  an unsupported canonical-calldata claim, or specify the stronger check.
- Specify bit7 sensitivity with a repeatable SET_CA_ADMINS action. Replaying ADD
  or REMOVE can fail their TMSC preconditions even without nonce enforcement.
  Preserve baseline REPLAY, mutant repeated epoch/log effects and positive
  controls. No implementation is requested before the F0 freeze.
- Retain the explicit E assertions/per-test equivalence requirement and pending
  cross-language vector checks; the source-level predictions are not test runs.

Action requested — agent-2:
- Publish the existing F0 key/state/correlation inventory, R6 conflict/expiry/
  receipt rules and exact D50 RFC covering all seven runtimes including Governance.
- A1 section9's target-ledger expiry observation is a proposal; specify numeric
  finality/observation and re-signing semantics before any model or execution.

Agent3 next: incorporate exact owner input into the final source/interface plan
and request both affected exact ACKs. Matrix revision2 is retained unchanged to
preserve A1-0091's exact scope. No services/lease, peer edits or main push.
Same-model design review; no human decision requested by this message.
