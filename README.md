# HMBC: access security, Byzantine operators, and key lifecycle

**Selected scope:** directions **E, F and G**, using **HMBC2020 only**. Work directly in this repository. Interface v1 has been frozen from exact scoped peer ACKs and verified owner snapshots. Both peers’ exact frozen mapping ACKs are verified; E0 is closed and E1 is unlocked. C-E1 public runner is implemented/unit verified; exact A3-0027 plan ACKs and real integration remain pending; all RQ gates remain NOT_RUN.

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

The live board is **E1: unlocked; public runner verified, exact plan ACKs/service integration pending**. Read the latest `communication/**` revisions across fetched branches, preserving exact commit provenance. Each agent publishes its owned work on `agent-N` from its own machine. See [E0 progress](evaluation/reports/E0-progress.md) for historical verification and limitations; current mapping completion is recorded in communication/E0_MAPPING_ACKS.json. The root evaluator preflight is available; the public two-chain runner is implemented/unit verified; real nine-control integration and RQ gates are not complete.

All previous content, including the uncommitted citation audit, is preserved under [archive/2026-10-06-pre-hmbc-efg/](archive/2026-10-06-pre-hmbc-efg/ARCHIVE.md). Its 51 archived files were checked against a SHA-256 manifest. JANUS, DP and abandoned directions are historical material; they are not active requirements.
