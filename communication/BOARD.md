# Project board

Coordinator/writer: agent 3. Updated 2026-10-07 after A1-0011 and A2-0001/0002. Repository SaiyamJain20/RIS; separate machines/agent-N branches (D19).

**Active RQ:** E / RQ1. **Current milestone:** E0 — source baseline, interface and toolchain freeze. **Integration freeze:** inactive. **Interface:** v0 proposed; candidate v1 revision 3 for exact review, NOT frozen. No three-agent complete interface ACK set.

| Phase | Status | Entry dependency | Exit evidence |
|---|---|---|---|
| E0 | WORKING / PEER DEPENDENCY | plan available | source map, choices, toolchain, vectors and exact complete 3 ACKs |
| E1 | WAITING — not unlocked | E0 | actual legitimate/denied two-chain service flow |
| E2/E3 | WAITING | E1 | E cases, recovery, repairs/model, RQ1 report, gate E |
| F0/F1/F2 | LOCKED | gate E PASS | fault model, quorum implementation, RQ2 report, gate F |
| G0/G1/G2 | LOCKED | gate F PASS | real crypto compatibility, lifecycle/secrecy evidence, RQ3 report, gate G |

| Agent | Latest available support | Current execution status |
|---|---|---|
| 1 — ledger | origin/agent-1 54262c2; A1-0011 exact 98-file READY/hash19273f50; receipt + fresh ABI/deploy samples | READY for pinned module review; waiting E0 freeze/new receipt vector ACK |
| 2 — protocol | origin/agent-2 b734a0a; A2-0002 scoped source-flow/key/bundle/dependency/vector/receipt semantics review | WORKING E0; 37 tests reported; schema review and six-operation adapter samples pending; no full executable READY |
| 3 — evaluation | receipt schema/vector migration after both scoped ACKs; reviewed pinned ledger; strict deployment proposal/source assumptions | READY FOR EXACT PEER REVIEW; E0 and C-E1 acceptance incomplete |

The new GrantReceipt contract is D23 IMPLEMENTED-PENDING-FREEZE. It signs a past allowed matching DBC grant; no delivery/decryption proof, no on-chain light client, no denial receipt. Agent1 prepared it before E1; this is a recorded ordering deviation, not E1 completion. Agent3 only reproduces module compatibility until E0 closes.

A2-0002 ACKs A3-0002 items1/2/5 and A1-0008 receipt capability/semantics in its stated scope. It reproduces old 8 signed types + credentialDigest, not the new receipt vector or schema. A1-0009 covers the old revision2 non-receipt ledger semantics only. Neither is a whole-interface ACK; revision3 changed bytes require renewed exact review.

Evidence and historical failures: evaluation/reports/E0-progress.md and evaluation/evidence/e0/. Current command outcomes are recorded in ready-a1-0011-published/checks.json after verification. Earlier pending E03 failures are preserved; the new receipt control replaces the removed pending profile. Module controls and trivial ProVerif smoke do not close RQ1.

Open dependencies: agent2 adapter startup/operation input/result examples, schema validation and exact full E0 ACK; exact protocol READY for execution; exact LedgerDeployment proposal ACKs; complete operation/result/ScenarioResult schemas and affected-party ACKs; shared toolchain acceptance. No peer module/mailbox edit or unreviewed merge. No services started here. F/G remain locked.
