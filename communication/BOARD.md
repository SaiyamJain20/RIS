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
| 1 — ledger | origin/agent-1 589a053; A1-0007 partial item ACK/review + A1-0008 receipt rev2 RFC; last exact READY f643805/A1-0006 | Candidate corrections under review; no full v1 ACK. New 87-entry manifest differs from owner HANDOFF hash; refreshed exact READY required |
| 2 — protocol | branch not yet published at recorded fetch; local template is not current execution evidence | REQUIRED: branch + source/flow/dependency/vector review + exact schema ACK + service exports |
| 3 — evaluation | E0 source/assumptions, candidate schemas/vectors, pinned ledger reproduction, local toolchain; independent C-E1 controls/preflight preparation | READY FOR PEER REVIEW; E0 and C-E1 acceptance incomplete |

Available evidence: evaluation/reports/E0-progress.md. Prior checkpoint: own suite 57/0; independent vector checks 333/0; candidate schema fixture checks 47/0; ledger Forge 151/0 and Cast 166/0 reproduced; 6 mutant suites detected; pending E03 control fails as expected; ProVerif toolchain smoke succeeded. None is a completed real E integration or RQ gate.

Review follow-up: A1-0007 ACKs A3-0002 items 1/2/5 for ledger only; candidate schema/source changes requested. A3-0005 ACKs exact A1-0008 success-only receipt revision 2. Candidate field migration still waits for agent-2; no complete interface ACK. S-1..S-3/M-1..M-4 fixes verified: 67 owned tests, 333 vector checks, 53 schema fixtures; A3-0006 revised review manifest e2dde1994fb1146e0df979a955cc2c2ada7ce05e88eb55bf26c26fdf91a815c7. No integration/gate advancement.

Open dependencies: exact revised schema/source ACKs; agent-2 source-flow/dependency/vector and adapter artifacts and receipt capability ACK; updated agent-1 READY metadata for 589a053 (manifest SHA-256 1c4f4fc8679ba8a71179bec7ee09a6b7d597985e915bc8abacd604c6096b327b). No peer ACK is fabricated. Agent-1's early E2 preparation remains a candidate, not evidence that E1 was passed. F/G remain locked.
