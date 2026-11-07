# GrantReceipt supplied-state check

Goal: complete one internal C-F1 evaluator slice using accepted R6 sections 3/5,
the owner-authored KSSC/PSC ABI and the frozen v2 signing context. Synthetic
paper-derived reconstruction/extension only; no wire, consumer or owner edits.

Approach: a pure receipt_state_v2.verify_receipt_signature composes the existing
bound single-owner signature check with exact hash-selected raw captures. It
compares every receipt field to the allowed grant, pending PBC request and one
declared GrantIssued log, including its header and issuance timestamp. The
alternative of accepting normalized exporter grant/log claims would omit the
raw ABI join. A live collector/history integration is a later separate slice.

The caller pins separate PBC/DBC observations and exact ABI paths. Strict capture
inventories reject unused/duplicate bytes. Supplied blocks at the same chain and
height must agree; this checker covers a caller-declared safe interval only.
No receipt-expiry rejection: late reconciliation is valid. Grant expiry must
still be positive and bounded by the pending request's original expiry.

1. Write synthetic independent ABI/EIP-712 fixtures, success/late controls and
   wrong grant/request/event/block/context refusals; record missing-module RED.
2. Implement the pure checker only; record GREEN and deliberate bypass controls.
3. Bracket exact owner/local/carried inputs and frozen payloads, run relevant
   composition regression, fetch/review communication again, inspect owned diff.
4. Publish evidence, limitations, STATUS/HANDOFF and one immutable READY on
   agent-3, verify remote, then release both original persistent lock inodes.

Limits: no RPC truth, ancestry, actual signing time/latest head, log/export/store
completeness, witness persistence/policy, quorum/consensus, delivery, E parity,
TLC, F scenario or gate claim. One declared event is not proof that no omitted
event exists. Extra-agent review is prohibited; author review is correlated.
Full runtime READY/mapping and separate exact execution FREEZE ACKs still precede
services. Historical qualified E unchanged; all32 F cases/GateF NOT_RUN/G locked.
