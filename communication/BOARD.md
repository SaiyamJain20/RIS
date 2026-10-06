# Project board

Coordinator/writer: agent 3. Initial state created by the planning task, 2026-10-06.

**Active RQ:** E / RQ1. **Current milestone:** E0 — source baseline, interface and toolchain freeze. **Integration freeze:** inactive. **Interface:** v0 proposed, no ACKs yet.

| Phase | Status | Entry dependency | Exit evidence |
|---|---|---|---|
| E0 | READY TO START | plan available | source map, choices, toolchain, v1 vectors and 3 ACKs |
| E1 | WAITING | E0 | legitimate integrated access flow |
| E2/E3 | WAITING | E1 | E cases, repairs/model, RQ1 report, gate E |
| F0/F1/F2 | LOCKED | gate E PASS | fault model, quorum implementation, RQ2 report, gate F |
| G0/G1/G2 | LOCKED | gate F PASS | real crypto compatibility, lifecycle/secrecy evidence, RQ3 report, gate G |

| Agent | First task | Next owned task | Current execution status |
|---|---|---|---|
| 1 — ledger | E0 contract/source review and digest vectors | A-E1 | NOT STARTED |
| 2 — protocol | E0 flow/key review and digest vectors | B-E1 | NOT STARTED |
| 3 — evaluation | E0 source/interface/toolchain coordination | C-E1 | NOT STARTED |

Open blockers: none encountered by coding yet. Unresolved setup choices are E0 tasks, not completed work. No program, formal model or attack has been executed under this new plan.
