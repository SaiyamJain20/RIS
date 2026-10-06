# Decisions and assumptions

Writer: agent 3. Status values: USER-DECIDED, PLAN-CHOICE, FROZEN, OPEN, SUPERSEDED. A plan choice is explicitly proposed for this project; it is not a paper fact or an instructor's requirement.

| ID | Status | Decision / evidence |
|---|---|---|
| D01 | USER-DECIDED | Use E/F/G; finish one RQ before the next. User instruction, 2026-10-06. |
| D02 | USER-DECIDED | HMBC only; JANUS may be integrated later if required. |
| D03 | USER-DECIDED | Three agents code concurrently, with modules spanning every RQ. |
| D04 | SUPERSEDED | Work directly in the main local checkout and put active work at its root; archive old documentation. |
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
| D16 | OPEN | External publication/outreach policy remains unselected. No author contact or external deployment is authorized by these documents. |
| D17 | USER-DECIDED | Create common context and three complete role-specific launch prompts and push this documentation update. User instruction, 2026-10-06. |
| D18 | SUPERSEDED | Complete human-supplied launch assignments include agent 3's reviewed checkpoint commit/push workflow to origin/main. Agents 1/2 only hand off files. A template found on disk is not authorization; exact reviewed paths, owner ACKs and coordinator serialization are mandatory. |

For a new decision record: ID, date, requester, exact change, reason, affected tasks/interfaces, source/evidence and ACK message IDs. Never replace an OPEN item with an unstated default.

## Distributed execution and E0 proposals (2026-10-07)

| ID | Status | Decision / evidence |
|---|---|---|
| D19 | USER-DECIDED | 2026-10-07: separate machines; GitHub communication; each agent publishes `agent-N`. Agent 3 confirmed `/home/karma/Documents/RIS`, origin `SaiyamJain20/RIS`. Supersedes D04/D18 Git/location rules; ownership and gates unchanged. Human instruction and A1-0001. Main publication is not part of this assignment. |
| D20 | PLAN-CHOICE | E0 review proposal: registration authority is the GID possession signature (a submitter conveys it); CA admins remain issuer-scoped; strict verifies issuer signatures, minimal trusts scoped admin; latest-appended wins in paper profiles; both use the configured PSC relay at the cross-chain hop. These are choices, not recovered author code. A1-0002 C02/C04/C05/C06/C15; peer ACKs pending. |
| D21 | PLAN-CHOICE | E0 proposed fixture: Doctor AND OnDuty from the same issuer; emergency context is synthetic and assumed; no treating relation claim. C16 conservatively instantiates Rule 2; wildcard issuer ambiguity recorded. Peer source/fixture ACKs pending. |
| D22 | PLAN-CHOICE | E0 proposed repaired-e: equal current checkpoint sequence and authEpoch; 30s request/decision and 60s checkpoint upper bounds; equality expiry rejects; use DBC clock for decisions/checkpoints, measure request clock skew; cached retry only before original grant expiry. Availability cost of non-revoking checkpoint invalidation is recorded. A1-0003/A1-0005; ACKs pending. |
| D23 | OPEN | E03 authenticated grant receipt proposed by A1-0005; agent 3 supports implementation preparation but exact receipt semantics and agent-2 capability ACK remain required before shared contract change/freeze. DBC authorization cannot establish delivery. |
