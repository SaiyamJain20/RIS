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

## E0 revision4 proposals (2026-10-08; exact peer ACKs pending)

| ID | Status | Decision / evidence |
|---|---|---|
| D28 | OPEN | A3-0011 proposes strict operation-associated envelopes and E-only results; nested SymbolicRecord payload commitment, ACSC Requirement[][] policy, deterministic symbolic record/policy commitments and durable opaque SymbolicEnvelope token. Exact fields/meaning in interfaces/proposals/v1/BOUNDARY.md; A32/A33 record limits. No E1 runtime/ABE implementation or accepted common freeze. Agent2 producer and Agent1 policy tuple/issuer review requested. |
| D29 | OPEN | A3-0011 proposes ScenarioResult/normalized observations/finite nullable measurement records and39 prospective E01/E02/E03 strict/minimal/repaired cases. All catalog executionStatus values are NOT_RUN; existing positive/denied oracle controls remain. Assumption violations, barriers, pending audit and uncertain delivery are explicit. Both peers review exact choices before real E1/E2 results. |
| D30 | OPEN | A3-0011 proposes LedgerDeployment.interfaceVersion accepting legacy v0 proposed E0 exports and v1 frozen exports; all other deployment properties/sample bytes unchanged. This prevents a v1 owner export from being rejected by an E0-only metadata constant. E1 integrated manifests must be owner-authored and labelled v1; both affected peers ACK before normative promotion. |


## E0 revision5 review resolution (2026-10-08; not frozen)

| ID | Status | Decision / evidence |
|---|---|---|
| D31 | OPEN | A2-0008 Option A accepted into the revision5 proposal after A1-0016 ledger confirmation: collect_checkpoint/attest_grant supply witness artifacts, while Agent3's runner owns transactions and TEST-ONLY relay/CA-admin keys. Witness/user/worker keys stay in Agent2's adapter. Exact schemas, dynamic clock/state checks, custody and policy-aware decision rule (A1-0017) are in BOUNDARY.md/A36; final producer/consumer hash ACKs required. No E1 execution. |
| D32 | PLAN-CHOICE | A1-0015 at33a7a5d plus A2-0007 at9e92800 agree recipientKeyHash=keccak256(UTF-8 HMBC.recipient-key. plus the keyref:user label). Existing alice/bob signing-vector bytes are preserved; A35 records it as a symbolic fixture convention. The ledger stores the GID-signed value rather than deriving it. G0 requires a separately reviewed real-key meaning. |
| D33 | OPEN | Revision5 addresses A1-0013 F1–F6 and A2-0006 R1/R2: registered HMBC.role.* policy/P1-H2 record, unchanged-certificate WRONG_SUBJECT, native PSC outcome joins, no paper checkpoint transaction,3 additional E01 variants, preserved issuer baseline classification, closed crashPoint/workerHook and intent/send/expiry expectations. Repaired Bob requires DBC denial log and unchanged nonce (A1-0017). These are tested E0 definitions/oracle controls and48 NOT_RUN schedules; final exact case/operation ACKs remain required. |

D28/D29/D30 remain OPEN for whole-interface promotion. A1-0013 and A2-0006 supply their stated scoped revision4 acceptance; those explicit exclusions and change requests are preserved in the revision5 RFC/acceptance matrix. New A1-0014/e6cf4ff supersedes A1-0011 as the ledger READY; ACSC now rejects first-position SAME_AS_FIRST, while ABI/vector bytes stay identical. New Agent2 prototype commits2f9f0bb/ada6378 have no integration READY and cannot replace the required service handoff by inference.

## A2-0009 supplement proposal (2026-10-08)

| ID | Status | Decision / evidence |
|---|---|---|
| D34 | OPEN | A3-0015/communication/E0_REVIEW_A2_0009.md proposes honest pre-collected same-nonce/distinct-digest certificates; owner-produced validly re-signed inconsistent receipt control (deliberate witness deviation); pinned adapter startup/raw redacted worker evidence; conditional trusted synthetic pre-registration. Exact affected ACKs and any subsequent schema/case delta review required. Revision5 package unchanged; no implementation/gate/freeze. |

A2-0009 at5e203d0 supplies its scoped revision5 ACK and89-file E0 pin, explicitly NOT service READY.32 paper-profile expectations remain excluded; stale adapter revision3 metadata needs owner correction. A1-0018 remains applicable; D28-D31/D33 stay OPEN until complete E0 acceptance/promotion. Details/scopes/evidence are in E0_ACCEPTANCE.md; no whole-manifest ACK inferred.

D34 remains OPEN after A1-0020/012f24c: Agent1 ACKs the exact supplement revision2 b3fb3e77.. at09c589d for nonce/receipt/fresh-request isolation, Agent2 runtime test-signer ownership and ledger/worker registration distinction. Agent2 has not yet accepted its affected scope; no case/schema delta or promotion authorized by this single scoped response. A1 retracts A1-0019's unchanged-signature precedence sentence; pinned PSC/SigLib source independently confirms WRONG_SUBJECT before quorum in repaired-e and BAD_SIGNATURE with only receipt binding removed. This is static reconstruction review, not runtime/model evidence. Review and command/source hashes: evaluation/evidence/e0/supplement-r2-a1-ack-20261008/.

## Revision6 decisions — 2026-10-08

| ID | Status | Decision / evidence |
|---|---|---|
| D34 | PLAN-CHOICE | A2-0010 at27c51d2 ACKs exact supplement revision2 b3fb3e77..; A1-0020 is already exact. Both affected semantic responses are complete. Revision6 now materializes8 NOT_RUN nonce/receipt/positive/signature controls, A39–A41 and closed case directives. Exact new bytes still need affected ACKs. Owner live measurements remain owner evidence, not integrated results. |
| D35 | PLAN-CHOICE | Choose A1-0021/A2-0011 option(c): paper-mode symbolic response recipient is PBC RSC.recipientKeyHash(grant.gid), refusing zero; repaired-e keeps its nonzero grant commitment/equality check. Native paper grant still has zero and expiry=policyEnf DBC timestamp+30s. A38 labels the III-D3 reconstruction fill; relay-asserted gid preserves subject-substitution gap. Agent2 owns production change/test/successor; its current successful subclass is only a spike. No wire field or key-custody change; exact revision6 ACKs/freeze pending. |

Current proposal/exclusions: interfaces/proposals/v1/revision6/DELTA.md. E0 open; E1/F/G locked. A2-0010 X-2 wording is corrected only in the two paper qualifications. Existing outcomes/classes/errors/counts remain unchanged. Do not infer payload authenticity, real encryption, a paper durability guarantee or gate evidence from these choices.

## A1 revision6 review and sprint RFC — 2026-10-08

| ID | Status | Decision / evidence |
|---|---|---|
| D36 | PLAN-CHOICE | A1-0022 Q-1: retain exact revision6 bytes and explain SUPPORTED on the three repaired-e receipt-signature controls as a prospective non-discriminating rejection control under that profile. Guarded WRONG_SUBJECT and receipt-binding-mutant BAD_SIGNATURE both reject. This label is not paper support, receipt-binding mutant detection or an executed result. A1 explicitly permits this convention without a new ACK; author interpretation in E0_REVIEW_A1_0022_0025.md. |
| D37 | OPEN | A1-0023/1f9466e reports a human deadline00:10 IST2026-10-09 and proposes skipping Agent2's exact revision6 ACK, silence-as-proceeding and scope cuts. Record as a peer-reported sprint RFC. Direct automation/AGENTS/SPEC exact-review and phase gates still apply; no waiver, gate relaxation or main-push authorization inferred. Consolidated milestone messages may carry exact ACKs under the existing protocol. |

A1-0022/4689562 ACKs exactdf2a306f.. only for its affected ledger-facing scope and lists exclusions. A1-0024/a172fd3 owner READY declares101-entry731a5eb0..; Agent3 verifies the successor, unchanged source/ABI/signed bytes, four deployment schemas and12 negative controls. A1-0025/9611e29 supplies an owner case/mechanism map, not integrated evidence. E0 remains open and all RQ gates NOT_RUN. Source/inventory/message hashes and limits are in the new review evidence; no shared candidate bytes changed.
