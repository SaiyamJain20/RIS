# Project board

Coordinator/writer: agent 3. Updated 2026-10-07 from fetched peer communication and owned tests. Human-confirmed repository: SaiyamJain20/RIS; separate machines/agent-N branches (D19).

**Active RQ:** E / RQ1. **Current milestone:** E0 — source baseline, interface and toolchain freeze. **Integration freeze:** inactive. **Interface:** v0 proposed; candidate v1 published for review, NOT frozen. No three-agent interface ACK set.

| Phase | Status | Entry dependency | Exit evidence |
|---|---|---|---|
| E0 | WORKING / PEER DEPENDENCY | plan available | source map, choices, toolchain, vectors and exact 3 ACKs; agent-2 absent |
| E1 | WAITING — not unlocked | E0 | actual legitimate/denied two-chain service flow |
| E2/E3 | WAITING | E1 | E cases, recovery, repairs/model, RQ1 report, gate E |
| F0/F1/F2 | LOCKED | gate E PASS | fault model, quorum implementation, RQ2 report, gate F |
| G0/G1/G2 | LOCKED | gate F PASS | real crypto compatibility, lifecycle/secrecy evidence, RQ3 report, gate G |

| Agent | Latest available support | Current execution status |
|---|---|---|
| 1 — ledger | origin/agent-1 f643805; A1-0006 READY supersedes 0004; 86-entry hash-verified manifest | WAITING per latest owner STATUS; E0/A-E1 draft and early A-E2 preparation; no v1 ACK |
| 2 — protocol | branch not yet published at recorded fetch; local template is not current execution evidence | REQUIRED: branch + source/flow/dependency/vector review + exact schema ACK + service exports |
| 3 — evaluation | E0 source/assumptions, candidate schemas/vectors, pinned ledger reproduction, local toolchain; independent C-E1 controls/preflight preparation | READY FOR PEER REVIEW; E0 and C-E1 acceptance incomplete |

Available evidence: evaluation/reports/E0-progress.md. Own suite 57/0; independent vector checks 333/0; candidate schema fixture checks 47/0; ledger Forge 151/0 and Cast 166/0 reproduced; 6 mutant suites detected; pending E03 control fails as expected; ProVerif toolchain smoke succeeded. None is a completed real E integration or RQ gate.

Open dependencies: exact A3-0002 semantic/source/clock/retry/schema review ACKs; agent-2 source-flow/dependency/vector and adapter artifacts; A1-0005/A3-0002 revised grant-receipt agreement. No peer ACK is fabricated. Agent-1's early E2 preparation remains a candidate, not evidence that E1 was passed. F/G remain locked.
