**Current checkpoint (2026-10-09 UTC):** Subject routing/completion checker prepared;
fresh777 root tests pass with190 inputs stable. Pure synthetic checks only: no
live subject release/completion or complete case.44 comparisons remain; gateE
NOT_RUN/F-Glocked. Next public completion collector, separate fresh controls,
full revised plan and both exact peer ACKs before services. See
[checker evidence](evaluation/evidence/e2/subject-completion-oracle-20261009/README.md).
Earlier checkpoint prose below is historical.

**Current checkpoint (2026-10-09 UTC):** Subject pre-release collector implemented;
fresh690 root tests pass with124 inputs stable. No live subject release/completion
or complete case result.44 comparisons remain; gateE NOT_RUN/F-Glocked. Next:
recipient routing, separate fresh controls, complete revised plan and both exact
peer ACKs. See [collector evidence](evaluation/evidence/e2/subject-collector-20261009/README.md).
Earlier checkpoint prose below is historical.

**Current checkpoint (2026-10-09 UTC):** Agent 1 found an evaluator error: WRONG_SUBJECT is code2, not3. Oracle and synthetic fixture corrected; regression RED2→GREEN71 and fresh670 root tests pass on106 stable inputs. No new live subject result or gate;44 comparisons remain, gateE NOT_RUN/F-Glocked. Next: public subject collector, complete revised plan and both exact peer ACKs before services. See [correction evidence](evaluation/evidence/e2/subject-code-fix-20261009/README.md). Earlier prose below is historical.

# HMBC: access security, Byzantine operators, and key lifecycle

**Current checkpoint (2026-10-09 UTC):** E0 closed/C-E1 complete; E2/E3 active. Grouped historical replay collector implemented;599 tests pass. A3-0044 complete plan awaits both exact peer ACKs before services. No new live timing/repaired release result; prior expiry failure retained.45 catalog comparisons remain; gateE NOT_RUN/F/G locked. See [the live board](communication/BOARD.md) and [runner evidence](evaluation/evidence/e2/grouped-replay-runner-20261009/README.md).

**Selected scope:** directions **E, F and G**, using **HMBC2020 only**, in this confirmed checkout. This is a paper-derived reconstruction with synthetic fixtures and symbolic E cryptography. Frozen v1 bytes and exact E0 mapping ACKs are retained; all RQ gates remain NOT_RUN.

**Order: E → F → G.** All three agents complete one research question together, integrate their modules, and close its evidence gate before starting the next. The first deliverable is a complete answer to **RQ1/E**, not three unfinished prototypes.

1. Read [PLAN.md](PLAN.md) for the ordered tasks, tests and completion gates.
2. Read [SPEC.md](SPEC.md) for the research questions, assumptions and experiment design.
3. Give each coding agent its [complete start prompt](communication/README.md): one file includes the shared context, its role, independent-work instructions and Git workflow. The canonical [common context](communication/COMMON_AGENT_CONTEXT.md) is maintained once and bundled with each role. Agents must also read live [AGENTS.md](AGENTS.md), the [interface contract](interfaces/README.md), and the [communication protocol](communication/PROTOCOL.md).

| Agent | Module | Responsibility throughout E, F and G |
|---|---|---|
| 1 | [ledger/](ledger/README.md) | HMBC contracts, policy state, authorization, governance and epoch commitments |
| 2 | [protocol/](protocol/README.md) | Client/relay, real signatures, decision witnesses, key service and cryptographic adapters |
| 3 | [evaluation/](evaluation/README.md) | Independent scenarios, formal models, integration, measurements and RQ reports |

```text
PLAN.md / SPEC.md / AGENTS.md       active instructions at repository root
ledger/  protocol/  evaluation/    three independently owned implementation modules
interfaces/                       shared contract, controlled by agent 3
communication/                    board, gates, decisions and one mailbox per agent
references/                       HMBC and two cryptography references
archive/                          all previous documents, papers and audit evidence
```

Read the latest `communication/**` revisions across fetched branches, preserving exact commit provenance. Each agent publishes its owned work on `agent-N` from its own machine. [E0 progress](evaluation/reports/E0-progress.md) is historical; current phase and dependencies belong to [BOARD.md](communication/BOARD.md). Unit tests and owner rehearsals do not substitute for integrated gate evidence.

All previous content, including the uncommitted citation audit, is preserved under [archive/2026-10-06-pre-hmbc-efg/](archive/2026-10-06-pre-hmbc-efg/ARCHIVE.md). Its 51 archived files were checked against a SHA-256 manifest. JANUS, DP and abandoned directions are historical material; they are not active requirements.
