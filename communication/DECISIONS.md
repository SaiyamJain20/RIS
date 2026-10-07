# Decisions and assumptions

Writer: agent 3. Status values: USER-DECIDED, PLAN-CHOICE, IMPLEMENTED-PENDING-FREEZE, FROZEN, OPEN, SUPERSEDED. A plan choice is explicitly proposed for this project; it is not a paper fact or an instructor's requirement.

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
| D20 | PLAN-CHOICE | E0 review proposal: registration authority is the GID possession signature (a submitter conveys it); CA admins remain issuer-scoped; strict verifies issuer signatures, minimal trusts scoped admin; latest-appended wins in paper profiles; both use the configured PSC relay at the cross-chain hop. These are choices, not recovered author code. A1-0002 C02/C04/C05/C06/C15; agent-1 exact item ACK in A1-0007 (589a053); agent-2 protocol-scope ACK in A2-0002 at b734a0a; exact full freeze pending. |
| D21 | PLAN-CHOICE | E0 proposed fixture: Doctor AND OnDuty from the same issuer; emergency context is synthetic and assumed; no treating relation claim. C16 conservatively instantiates Rule 2; wildcard issuer ambiguity recorded. Agent-1 item ACK in A1-0007 (589a053); agent-2 source/fixture ACK pending. |
| D22 | PLAN-CHOICE | E0 proposed repaired-e: equal current checkpoint sequence and authEpoch; 30s request/decision and 60s checkpoint upper bounds; equality expiry rejects; use DBC clock for decisions/checkpoints, measure request clock skew; cached retry only before original grant expiry. Availability cost of non-revoking checkpoint invalidation is recorded. A1-0003/A1-0005; agent-1 item ACK in A1-0007 (589a053); agent-2 semantics ACK in A2-0002 at b734a0a; retry choice is D24; no service implementation proof. |
| D23 | IMPLEMENTED-PENDING-FREEZE | A1-0008 revision 2 supersedes A1-0005 receipt: success-only matching past DBC grant; no dbcResult; add gid/dataId/witnessSetVersion (1 in E); HMBCReceipt/1/PBC/PSC domain; distinct PSC.reportAttestedOutcome; late reconciliation allowed; denials remain pending on PBC and separately logged on DBC. Agent-3 ACK in A3-0005; agent-2 exact capability/semantics ACK in A2-0002 at b734a0a; agent-1 implemented in A1-0011 at 54262c2; agent-3 candidate migration follows both ACKs. New vector/schema bytes and complete interface freeze still require exact reviews. DBC authorization cannot establish release/delivery/decryption. |
| D24 | PLAN-CHOICE | 2026-10-07 A2-0002 section5 item2: collect_decision retries at most once per newly accepted checkpoint while request unexpired; no stale decision reuse; cached releases expire at original grant expiry. Agent3 accepts scoped E0 proposal for schema/sample review; exact adapter implementation ACK pending. Affects B-E1/C-E1; no availability theorem. |
| D25 | PLAN-CHOICE | 2026-10-07 A2-0002 S-a/section3 and A1-0011 answers1/4: keyref handles resolve inside declared state-dir; temporal key selection derives from committed grant plus record policy; witness credentials use historical PBC block state and that block timestamp. Affects E0/B-E1/C-E1; A28-A30 preserve limitations. Owner historical-read evidence is reviewed, not independently rerun here. |

## E0 adapter/deployment review (2026-10-08)

| ID | Status | Decision / evidence |
|---|---|---|
| D26 | PLAN-CHOICE | A1-0012/A2-0005 agree rpcUrl, createdAt, contract addresses and deployBlock are required per-deployment instance facts, not shared frozen values or cross-machine equality checks. Shared freeze covers chain ids, profile/mutations, compiler/source/ABI hashes and fixture semantics. Agent3 records acceptance in A3-0010; each future integration run uses its own deployment and binds signed messages to its own addresses. No schema bytes changed or deployment adopted here. |
| D27 | PLAN-CHOICE | A2-0003 choices(a)-(c), accepted by Agent3 in A3-0010: manifest source/destination chain/PSC/KSSC mismatch uses WRONG_DESTINATION; unknown operation/envelope/canonical violation uses MALFORMED; unbuilt E operations use ADAPTER_UNAVAILABLE; G rotate_epoch stays NOT_IMPLEMENTED_IN_PHASE. Consistent with ledger prechecks (A1-0012 supports a). Exact request/result schemas still open; no fake success or E1 unlock. |
