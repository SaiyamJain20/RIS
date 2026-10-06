# Decisions and assumptions

Writer: agent 3. Status values: USER-DECIDED, PLAN-CHOICE, FROZEN, OPEN, SUPERSEDED. A plan choice is explicitly proposed for this project; it is not a paper fact or an instructor's requirement.

| ID | Status | Decision / evidence |
|---|---|---|
| D01 | USER-DECIDED | Use E/F/G; finish one RQ before the next. User instruction, 2026-10-06. |
| D02 | USER-DECIDED | HMBC only; JANUS may be integrated later if required. |
| D03 | USER-DECIDED | Three agents code concurrently, with modules spanning every RQ. |
| D04 | USER-DECIDED | Work directly in the main local checkout and put active work at its root; archive old documentation. |
| D05 | PLAN-CHOICE | Order E → F → G; reasons in SPEC/PLAN. |
| D06 | PLAN-CHOICE | Agent 1 ledger, agent 2 protocol/key service, agent 3 models/evaluation/integration; single-writer paths. |
| D07 | PLAN-CHOICE | Paper-derived strict/minimal reconstruction, explicit mutants and cumulative repairs; no JANUS implementation dependency. |
| D08 | PLAN-CHOICE | Two local EVM chains, four synthetic hospital authorities; one populated domain, no scaling conclusion. |
| D09 | PLAN-CHOICE | E uses one trusted witness; F/G use q=3 of 4 application witnesses with f=1. Safe ledgers/trusted key-worker assumptions remain explicit. |
| D10 | PLAN-CHOICE | Request/decision TTL 30 s, checkpoint TTL 60 s; DBC checkpoint is the effective revocation barrier for new grants. E0 must freeze timing and retry vectors. |
| D11 | PLAN-CHOICE | Core F studies application decision/governance faults; a Besu consensus deployment is optional and distinct from HMBC PoS. |
| D12 | PLAN-CHOICE | G tests future-data exclusion, no-history joins, later compromise, and cached-output limitations separately; old ciphertexts do not magically update. |
| D13 | OPEN | Exact compiler/library/formal-tool versions: freeze after E0 compatibility checks. Inspected host versions are observations only. |
| D14 | OPEN | Compatible real ABE/two-step adapter and epoch composition: mandatory G0 investigation, vectors and review. No implemented secrecy claim until resolved. |
| D15 | OPEN | Exact deadline, available student time/hardware and instructor proof/publication requirements. The plan uses gates and estimates, not invented answers. |
| D16 | OPEN | Commit/publication/outreach policy. No automatic commit or author contact authorized by these documents. |

For a new decision record: ID, date, requester, exact change, reason, affected tasks/interfaces, source/evidence and ACK message IDs. Never replace an OPEN item with an unstated default.
