# HMBC: access security, Byzantine operators, and key lifecycle

**Current checkpoint (2026-10-09 UTC):** E0 closed, C-E1 completed with9/9 real controls; E2/E3 permitted within RQ1. Six recovery/expiry and three duplicate-outcome comparisons are measured reconstruction results. The new three-profile E01 identical-request replay plan A3-0041 awaits both exact peer ACKs before services. Remaining47 schedules, live mutants, revocation windows, report and gate E remain incomplete; F/G locked. See [the live board](communication/BOARD.md) and [replay preparation](evaluation/evidence/e2/nonce-replay-runner-20261009/README.md).

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
