# Project board

Coordinator/writer: agent 3. Updated 2026-10-08 after A1-0012 and A2-0003/0004/0005. Repository SaiyamJain20/RIS; separate machines/agent-N branches (D19).

**Active RQ:** E / RQ1. **Current milestone:** E0 — source baseline, interface and toolchain freeze. **Integration freeze:** inactive. **Interface:** v0 proposed; candidate v1 revision 3 for exact review, NOT frozen. No three-agent complete interface ACK set.

| Phase | Status | Entry dependency | Exit evidence |
|---|---|---|---|
| E0 | WORKING — AGENT3 SCHEMA WORK / FINAL REVIEW | plan available | source map, choices, toolchain, vectors and exact complete 3 ACKs |
| E1 | WAITING — not unlocked | E0 | actual legitimate/denied two-chain service flow |
| E2/E3 | WAITING | E1 | E cases, recovery, repairs/model, RQ1 report, gate E |
| F0/F1/F2 | LOCKED | gate E PASS | fault model, quorum implementation, RQ2 report, gate F |
| G0/G1/G2 | LOCKED | gate F PASS | real crypto compatibility, lifecycle/secrecy evidence, RQ3 report, gate G |

| Agent | Latest available support | Current execution status |
|---|---|---|
| 1 — ledger | origin/agent-1 60b35cb; A1-0012 scoped revision3 ACK; unchanged ledger54262c2/A1-0011 READY | Waiting final interface revision/freeze; no new ledger implementation dependency |
| 2 — protocol | origin/agent-2 e1b4322; A2-0003 E0 READY + all6 operation examples; A2-0004 second-machine ledger reproduction; A2-0005 scoped revision3 ACK | Agent3 reproduced235 tests/1 explicit skip and7 generated exports; waiting operation/result/envelope schema review and E1 unlock |
| 3 — evaluation | Current20-file candidate unchanged; both peer scoped ACKs recorded; exact protocol E0 snapshot reproduced | WORKING: next owner is Agent3 for operation/envelope/result/ScenarioResult definitions and final review revision |

The new GrantReceipt contract is D23 IMPLEMENTED-PENDING-FREEZE. It signs a past allowed matching DBC grant; no delivery/decryption proof, no on-chain light client, no denial receipt. Agent1 prepared it before E1; this is a recorded ordering deviation, not E1 completion. Agent3 only reproduces module compatibility until E0 closes.

A2-0002 ACKs A3-0002 items1/2/5 and A1-0008 receipt capability/semantics in its stated scope. It reproduces old 8 signed types + credentialDigest, not the new receipt vector or schema. A1-0009 covers the old revision2 non-receipt ledger semantics only. Neither is a whole-interface ACK; revision3 changed bytes require renewed exact review.

Evidence and historical failures: evaluation/reports/E0-progress.md and evaluation/evidence/e0/. Current command outcomes are recorded in ready-a1-0011-published/checks.json after verification. Earlier pending E03 failures are preserved; the new receipt control replaces the removed pending profile. Module controls and trivial ProVerif smoke do not close RQ1.

Current dependencies: Agent3 complete strict operation/input/result/request-envelope/ScenarioResult proposals, clarify unimplemented nested record/policy/responseEnvelope shapes and instance-local deployment freeze rules, return exact revision for affected-party ACKs and common E0 acceptance. Agent2 startup/examples/receipt reproduction/READY and both revision3 scoped ACKs are now present. Older requests for those artifacts are satisfied; no full interface freeze is inferred. No peer module/mailbox edit or unreviewed merge. No services started here. F/G remain locked.

A3-0010 records the exact scoped reviews, three accepted error choices and local protocol reproduction. Evidence: evaluation/evidence/e0/peer-review-20261008/. Agent2 needs nothing further from Agent1 for this E0 handoff; actual E1 service implementation starts only after E0 acceptance.
