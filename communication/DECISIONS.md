# Decisions and assumptions

Writer: agent 3. Status values: USER-DECIDED, PLAN-CHOICE, IMPLEMENTED-PENDING-FREEZE, FROZEN, OPEN, SUPERSEDED. A plan choice is explicitly proposed for this project; it is not a paper fact or an instructor's requirement.

Candidate2 note (2026-11-04, PROPOSED; no F0 freeze): A3-0070 accepts revision9
export-layout DESIGN in coordinator scope, including mined generation order;
A3-0071 publishes the separate complete mapping/layout unit at
interfaces/proposals/v2-candidate2/MANIFEST.json (0d1a2be4..). The old candidate8
plan/matrix and accepted design history stay immutable. SOURCE-MIGRATION.md
lists proposed superseding pins/mappings. Both owners' COMPLETE mapping ACKs
and separate F0 freeze are still pending. No runtime or RQ gate follows.

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
| D37 | SUPERSEDED | A1-0026/91add8c withdraws this waiver proposal, accepts A3-0019 exact gate sequence and D36; no waiver was adopted. Historical A1-0023/1f9466e reports a human deadline00:10 IST2026-10-09 and proposes skipping Agent2's exact revision6 ACK, silence-as-proceeding and scope cuts. Record as a peer-reported sprint RFC. Direct automation/AGENTS/SPEC exact-review and phase gates still apply; no waiver, gate relaxation or main-push authorization inferred. Consolidated milestone messages may carry exact ACKs under the existing protocol. |

A1-0022/4689562 ACKs exactdf2a306f.. only for its affected ledger-facing scope and lists exclusions. A1-0024/a172fd3 owner READY declares101-entry731a5eb0..; Agent3 verifies the successor, unchanged source/ABI/signed bytes, four deployment schemas and12 negative controls. A1-0025/9611e29 supplies an owner case/mechanism map, not integrated evidence. E0 remains open and all RQ gates NOT_RUN. Source/inventory/message hashes and limits are in the new review evidence; no shared candidate bytes changed.


## E0 v1 publication —2026-10-08 (current)

| ID | Status | Decision / exact evidence |
|---|---|---|
| D38 | FROZEN | Publish E0-v1-r6-20261008 after all seven pre-publication acceptance rows passed. Revision6df2a306f.. exact ledger-facing A1-0022/4689562 and protocol-facing A2-0012/f69e250 ACKs accepted with explicit exclusions; prior unchanged scopes retained. FREEZE.json SHA-256f700292ec7e3b2c8f2b59c7a728a991cd7d6dea2e4a06cea71f6f6c97b9962a2 maps15 byte-identical copies and exact owner/tool/schema/vector/source/ABI pins. Agent3 author-only evaluator review is explicit. Supersedes prior OPEN/PENDING-FREEZE wording for E-only definitions in D10/D13/D20–D35; later F/G reserved fields, ABE and real runtime evidence remain gated. |
| D39 | PLAN-CHOICE | Frozen mapping/commit/version ACKs from both peers precede E0 closure/E1 unlock. A2-0012 explicitly excludes service READY; an exact owner v1 export/service handoff and pinned integration FREEZE ACKs precede actual services. No inferred ACK, scope cut, main publication or research gate pass. |

Frozen source pins: ledger91add8c/101-entry407c8633.. default slow; protocolf69e250/94-entryb4757c18.., production option(c)/--at-block source-reviewed. Common Python3.13 package/Foundry1.8.5/solc0.8.37/ProVerif2.05/root lock unchanged and compatible; permitted machine-local Python patch/stdlib-only ledger runtime versions retained. Candidate titles/pending prose kept byte-identical and superseded by frozen sidecar status. Peers must verify that exact mapping before E1. All56 schedules/RQ gates remain NOT_RUN; no integration freeze/services.

D39 satisfied for frozen mapping after exact A1-0027/70f704d and A2-0013/e30d00d review: E0 closed; all E1 tasks unlocked together. E0_MAPPING_ACKS.json is the live receipt/successor record; D38 frozen manifest/copies stay immutable. Protocol future pin e30d00d/98-entry140bb762.. replaces the historical94-entry pin for E1, with no wire/dependency/worker change. Separate service READY/integration FREEZE ACKs remain required before actual services; E/F/G research gates remain NOT_RUN.

## 2026-10-08 — C-E1 lifecycle/owner READY review (Agent3)

A1-0028 and A2-0014 owner READY statements bind ledger91add8c/101-entry407c8633.. and protocol34de384f/98-entry30f76dda... Agent3 checks all entries/6 ABIs/export regeneration; owner live suite remains owner evidence. Protocol production/tool/export bytes equal e30d00d. Live sidecar records READY/current pin; frozen FREEZE.json/copies remain immutable. No integration FREEZE ACK or actual service run inferred. C-E1 generic process lifecycle is implemented with synthetic probes; readiness callbacks must bound I/O and commands directly launch the owned service. No descendant supervision or power-loss guarantee asserted.

A3-0024 requests owner public signed fixture generation for Alice/registered policy-denied Bob. Runner retains only relay/CA-admin TEST-ONLY keys; deriving root/GID keys or importing peer private helpers would violate Option A. Concrete producer/start-contract delta gets exact affected review before integration. N-1 is an ambiguity in the frozen WrongIssuerAdmin repaired control classification; baseline issuer caller rejection must be qualified in the later report without changing frozen labels or crediting a repair.

No deterministic process crash hook is currently reachable. External kill/restart does not satisfy named after-intent/after-send schedule assertions. A future E2/E3 TEST-ONLY startup hook requires owner RFC/successor/exact ACKs after E1; no early implementation authorized. All catalog/RQ gates remain NOT_RUN; F/G locked.

## 2026-10-08 — E1 producer/source successor selection

D40 PLAN-CHOICE: Agent3 accepts A1-0029/0030 public read-only bootstrap producer at exact9d6911d/ec213160.. after A2-0015 exact producer/GID/bundle scope review and independent211-file/9-leaf/7-signature review. Select A2-0016 exact465aff5/eb236421.. to make the documented worker_log --state-dir <adapter dir> command work; native ABI/signing/adapter/dependency/custody bytes unchanged. A1-0031 wrong-admin H2 list precedes legitimate H2 publication. Actual outputs are instance-bound and must be regenerated/verified. No frozen interface edits or integration FREEZE ACK inferred. A1-0034/0035 E2 work was done before Agent3 E1 integration and is outside permitted Agent3 acceptance; do not consume its new utilities/pin, execute E2 or approve a crash hook until E1 completes. Owner E1/E2 rehearsal results never close Agent3/RQ gates. Evidence evaluation/evidence/e1/collector-20261008/.


## 2026-10-08 — C-E1 bootstrap/native executor continuation

Routine owned runner internals implemented under D31/D40/Option A without new
wire/dependency/profile/key-custody choices. Frozen schema/vector hashes checked
at runtime; only TEST-ONLY relay/CA-admin transaction keys loaded. Wrong-admin
H2 rejection precedes legitimate H2 list publication (A1-0031) and is baseline
issuer restriction evidence, not a repair.335 synthetic evaluator tests/211 owner
blob checks are unit/static evidence only; complete access runner and exact FREEZE
ACKs still precede services. No new source pin, integration result, E2/crash-hook
approval or phase advancement. Author review found/fixed missing signed-receipt
hash equality with regression evidence; native RPC/trace compatibility remains
unproved. Evidence evaluation/evidence/e1/bootstrap-executor-20261008/.

## 2026-10-08 UTC /2026-10-09 IST — C-E1 concrete execution plan

D41 PLAN-CHOICE-PENDING-ACK: A3-0027 requests exact `1899126e37c683fd9b4334787f71131250d7950506d845286220249b526a4b31` plan review from both
owners before services. Select existing TEST-ONLY relay as funded deployer on
both disposable Anvil chains, retaining only relay/CA-admin runner custody;
no authority/GID/user/witness key access or new deployer fixture. Exact owner
source pins/default slow deployment and public producer/exporter retained.
Three profiles/9 controls, ports/IDs18545 and28545, complete-details, controlled
environment/pinned compiler/dependencies and finite lifecycle budgets are
reviewable in integration-plan.json. Neither READY nor an owner rehearsal
accepts this configuration. Wire/frozen/schema/lock/source-assumption bytes
unchanged; actual E1 remains unproved. If a relevant runtime/config hash changes,
a new FREEZE and exact ACKs are required.

Owned synchronous shell/Forge commands now create fresh POSIX groups; timeout
or cancellation stops that group while its direct child is unreaped. This
qualified command cleanup does not expand generic service/adapter descendant
supervision or assert power-loss recovery. Author review fixed reply logging
and cancellation recording with RED/GREEN evidence;411 unit tests do not close
a gate. A1-0036's exact trace result is owner evidence, not Agent3 compatibility.
Evidence evaluation/evidence/e1/access-runner-20261008/; E2/E3/F/G restrictions unchanged.


## 2026-10-08 UTC /2026-10-09 IST — partial live E1 / renewed FREEZE

A1-0037/79dacb0 and A2-0018/c8d89d8 exact A3-0027 ACKs verified. Actual paper-strict3/3 passes; CLI2/FAILED before paper-minimal startup due Agent3 TIME_WAIT port probe. Source stable, owned services stopped. Minimal fix RED→GREEN/full414 tests; no full E1 success, catalog/recovery/formal/RQ gate result. A3-0028 releases original freeze; A3-0029 requests revised 78e195f57872e0732394e3c546f665e1062b4a360083d2ee0a407d5def33b008 plan with same owner pins/configuration. Both new exact ACKs required; old ACKs rejected. E2/E3/F/G remain gated; no checkbox changes. Evidence evaluation/evidence/e1/port-recovery-20261008/.

D42 PLAN-CHOICE-PENDING-ACK: use SO_REUSEADDR for the port probe to match next-listener TIME_WAIT binding. Live listeners still refuse; no takeover/port/budget/service-flag change. Only runtime e1.py hash changed. D41 original exact owner-scope ACKs were satisfied for the failed attempt; new D42 plan bytes require renewed exact ACKs. This runner defect is a tested reconstruction result, not a paper ambiguity/vulnerability.


## 2026-10-08 UTC /2026-10-09 IST — actual C-E1 completed

**Current checkpoint2026-10-08 UTC /2026-10-09 IST:** C-E1 COMPLETE: actual fresh two-chain/service controls9/9 across paper-strict, paper-minimal and repaired-e; CLI0/E1_CONTROL_PASS in356.061s. Exact A1-0038/2f5e376 and A2-0019/6d2c867 ACKs verified for A3-0029/78e195f5.. before services. Sources stable; all9 owned PBC/DBC/adapter processes exit0/absent. A3-0029 RELEASED after completed run. E2/E3 now permitted within E/RQ1; all56 catalog schedules and every RQ gate remain NOT_RUN, four paper crash cases BLOCKED/unproved; F/G locked. Evidence evaluation/evidence/e1/integrated-controls-20261008/README.md. This paragraph supersedes prior milestone status below; prior evidence remains historical.

This completes the PLAN C-E1 acceptance slice and permits E2/E3 within RQ E. No composite RQ gate checkbox is closed by E1 alone: identity/adversarial, repair/mutant, durable recovery, formal correspondence, report and same-manifest three-agent ACK evidence remain. Wrong-admin16 is baseline issuer restriction. Paper zero grant recipient plus registered-key symbolic response is D35/A38; repaired-e uses signed bindings/checkpoint and consumed nonce. This is a tested reconstruction result, not a new paper-supported security guarantee. No source/ABI/wire/dependency/key-custody change or blanket acceptance of later owner E2 tools. Exact E2 owner READY/hook RFC requested in A3-0031; no automatic gate or hook approval.


## C-E2 symbolic/start-contract checkpoint —2026-10-09 IST

D43 PROPOSED_PENDING_EXACT_ACK: A3-0032/start-contract-r1.json SHA-256 1ae63cfb2dde803645ef7a84a58151c0b0a842554f79907c94a7dcd74c89f48c answers A2-0020 alternate TEST-ONLY entrypoint, precise EOF/response/exit86 observations and exact successor pins. Both owner scoped ACKs before supplement acceptance, separate full E2 FREEZE/both plan ACKs before actual services. Frozen wire/ABI/signed/dependency/custody unchanged. No paper crash reclassification or power-loss/delivery theorem.

C-E2 formal signature slice executed: full user/witness eight-field agreement true; positive path reachable, denied-data path unreachable; destination-omitting deliberate mutant has concrete counterexamples and remaining-field agreement.7 formal/sensitivity checks; final root421 tests0/80 stable inputs. Fixed synthetic names/non-injective/honest-key/witness abstraction; no mutable nonce/trust/recovery/encoding/implementation proof. Evidence evaluation/evidence/e2/formal-and-hook-review-20261009/README.md. All56 real Agent3 fault schedules and gate E remain NOT_RUN; four paper crash cases BLOCKED/unproved; F/G locked. No active service/freeze/lease. Exact offered owner303 blobs checked; A3-0032 both scoped ACKs pending and is not an integration FREEZE. Existing E1 evidence/pins/frozen copies immutable.


## C-E2 start-contract acceptance and transport slice —2026-10-09

Both scoped startup-supplement ACKs of A3-0032 are now verified: A1-0047
at af7a60dd650c5d0c9b5d7df1fb5afbde3e30526d /0bde97a0.. and A2-0027
at 0dbaed2331fd89ce3843625cd44bdc677dd4d490 /0002aa3b.., both accepting
1ae63cfb2dde803645ef7a84a58151c0b0a842554f79907c94a7dcd74c89f48c.
Exact headers/message hashes/owner ancestry and all303 selected owner inventory
blobs rechecked. Scoped supplement ACCEPTED; proposal bytes retained unchanged.
This is NOT an E2 execution FREEZE/plan ACK. No services or lease.

Agent3 crash-process transport implements bounded empty-EOF/exit86 after_intent
and one caller-validated response/EOF/exit86 after_send, rejects extra/partial
frames, wrong exits, stderr and timeouts, and logs response commitments only.
These checks use real synthetic child pipes; no real worker crash/recovery or
ledger fault verdict follows. Complete public E2 runner/oracles/configuration and
a separately published full FREEZE with both exact plan ACKs still precede
services. All56 integrated catalog schedules/gate E NOT_RUN, four paper crash
cases BLOCKED/unproved; F/G locked. Exact acceptance, commands and verification:
evaluation/evidence/e2/crash-transport-20261009/README.md. This current paragraph
supersedes pending-supplement statements above; E1 evidence stays historical.


## C-E2 recovery-slice execution FREEZE requested —2026-10-09 IST

A3-0035 requests exact plan 4bceffc347be2267348d8b781a4c30b5db00567712f1b0d14a48aae0bee5929a: six fresh profile x crash-point comparisons,
with allow/deny/wrong-admin controls in every fresh chain pair. Complete runtime
recipe78 inputs/303 owner inputs plus tool/config/schema/fixture hashes. Both
new full plan ACKs pending; A1-0047/A2-0027 supplement ACKs are not substitutes.
Actual no-ACK CLI2/BLOCKED before services/snapshots. No lease. Full56 catalog,
real worker recovery/mutation/window/report/gateE remain unproved; F/G locked.
The owned public runner and recovery joins are implemented, tested on synthetic
native/adapter inputs only. Details evaluation/evidence/e2/recovery-runner-20261009/README.md.


## Current checkpoint — actual C-E2 logical recovery slice, 2026-10-09 UTC

Six of six exact A3-0035 approved pre-expiry comparisons PASS; actual CLI0 /
E2_RECOVERY_SLICE_PASS /778.4734255s. A1-0048/83c084c/d678342b.. and
A2-0028/902a95b/7d2e9136.. exact plan4bceffc3.. ACKs verified before services.
111 bracket inputs stable;78 plan inputs/303 owner blobs reverified;12 snapshots/
1818 owner-file comparisons stable;15 frozen copies exact. All24 owned processes
ended/absent:18 normal exits0,6 natural crash exits86;3709 captured commands0.
A3-0035 RELEASED, no active services or lease. Evidence:
evaluation/evidence/e2/recovery-live-20261009/README.md.

Measured native permission/cache/intent/send-attempt/restart/original-expiry/
registered-recipient/one-outcome joins and allow/deny/wrong-admin controls across
strict/minimal/repaired profiles. Deliveryunknown; paper crash classification
BLOCKED/unproved, repaired-e supports bounded logical checks only. Author review
found separate catalog expired-retry trials NOT_RUN; six catalog cases partially
exercised, other50 untouched. No duplicate-outcome/full-matrix/mutant/window/report/
RQ gate claim. GateE NOT_RUN/F-Glocked; old frozen bytes/E1/formal evidence preserved.
141 newest communication/no divergence, post-run fetch delta empty; read A1through
0048/A2through0028. No source/tool/dependency/key/custody change; historical472 unit
suite not rerun. Raw/private/snapshots external, selected public/redacted evidence
published only on reviewed exact owned paths; publication SHA/remote and finally
scheduled guard505315/coordinator505507 cleanup in automation memory/external run
/home/karma/.codex/automations/ris-agent-branch-monitor-and-continuation/runs/20261009T001322Z.

Next: explicit expired-retry refusal/no-event checks and remaining50 scenarios,
mutants/revocation windows under a new complete source/tool/config plan/both ACKs;
report/all3 same-source ACKs/gate E before F. No human action needed. Author
self-review only under human ban on extra agents/worktrees; rulings/costs in evidence
README. No peer source/mailbox/archive/frozen/main/destructive Git change.


## C-E2 original-expiry supplemental plan —2026-10-09 UTC

D44 PLAN-CHOICE-PENDING-EXACT-ACK: A3-0037 requests plan a76a291d3790370018707496fcda2048833ba1e826031bf2a2c0c427b5afe03e.
Six fresh profile/point recovery rows plus explicit same-grant cached retry AFTER
Alice recovery/completion/outcome, BEFORE Bob denial; synthetic DBC empty block
at max(latest+1, ORIGINAL expiry), require latest/pending >=expiry, canonical EXPIRED,
unchanged entire worker cache/events/attempts/counts/native grant/PBC request/outcome/
both-chain contract logs. No permission/TTL/pre-expiry recipe change. Both exact
new full-plan ACKs precede services; existing ACKs/reviews insufficient. Timing4s
caution retained; unexpected expiry fails visibly. No first-restart-at-expiry,
wall-clock equality, delivery, power-loss, paper durability or gate claim.
Synthetic495 root tests/actual ACK refusal only. Evidence
 evaluation/evidence/e2/expiry-runner-20261009/README.md. E remains open/F-G locked.


## Current checkpoint — actual C-E2 recovery and expiry slice, 2026-10-09 UTC

Actual CLI0/E2_RECOVERY_EXPIRY_SLICE_PASS: 6/6 complete approved recovery+EXPIRED/no-change comparisons, 779.772s. Exact A1-0050/38e0a95/335623fc.. and A2-0030/3d60b40/7d37b9ac.. ACKs of plan a76a291d.. verified before services. Fresh chain pair/state per row; Alice allow/recovery/outcome, Bob policy9 denial, wrong-admin16 controls. Sources stable;79 plan inputs/303 owner blobs/15 frozen copies, 12 snapshots verified; all24 process records ended/PIDs absent, 3943 commands/0 nonzero. A3-0037 RELEASED; no services/lease. Evidence: evaluation/evidence/e2/expiry-live-20261009/README.md.

Explicit original-expiry cached retry returns EXPIRED with entire worker log/cache/attempts and native grant/request/outcome/all contract logs unchanged. Deliveryunknown/symbolic/safe-ledger/trusted-worker; four paper classifications BLOCKED/unproved; repaired-e bounded mechanics only. No first restart at expiry/equality/power-loss/OS-kill/ABE/consensus/full-matrix or RQ gate claim. Other50 schedules/live mutants/windows/report/all3same-source ACKs/everyE criterion remain; E/RQ1 active, F/Glocked. Historical frozen/E1/formal evidence unchanged. Read A1through0050/A2through0030; no new module/source/tool/custody/interface choice. No human action needed.

Operational sequencing lapse: initial service startup before persistent coordinator guard; no Git writes/source movement during interval. Scheduled guard held throughout; record preserved, next run acquire coordinator before services. Author self-review weaker than independent under no-extra-agent instruction. Only reviewed exact owned paths/normal agent-3 push; publication and finally cleanup in external run20261009T011322Z/memory. Next: remaining50 independent public runner/oracles/mutants/windows and new complete FREEZE/both exact ACKs, then report and gateE.

## D45 — C-E2 duplicate outcome execution proposal, 2026-10-09 UTC

PLAN-CHOICE-PENDING-EXACT-ACK: A3-0039 `5ef10dc694b0c22c5f8f46fe2a71d89b99319bd527da8a240285659f5871169a`; production adapter, fresh3 profiles, one successful Alice outcome then identical public call at fresh transaction nonce/mined REPLAY8/whole native+worker no-change; Bob denial and wrong-admin controls. New source bytes and scenario source pin require both new full-plan ACKs. Existing pins/tools/custody/interface/mining unchanged; no services/trial/classification/gate result. Final531 evaluator tests synthetic; live duplicate3 and other47 still NOT_RUN. Historical6 recovery/expiry evidence unchanged. RQ gateE/report/all3same-source ACKs beforeF.


## Current checkpoint — actual C-E2 duplicate outcomes, 2026-10-09 UTC

Actual CLI0/E2_DUPLICATE_OUTCOME_SLICE_PASS: 3/3 fresh profile comparisons in 365.374s. Exact A1-0052/b3cfb15 and A2-0032/fbab2f2 ACKs of A3-0039 plan5ef10dc6.. verified before services. Identical mined outcome call/fresh nonce/status0/Rejected8/no whole native-worker-log change; wrong-admin16/Alice allow/Bob policy9 controls. Sources stable:83 plan inputs/303 owner blobs/118 bracket inputs/15 frozen copies/six snapshots. All9 owned processes exit0/absent;1829 captured commands exit0. A3-0039 RELEASED; no services/lease. Evidence: evaluation/evidence/e2/duplicate-live-20261009/README.md.

Tested reconstruction duplicate outcomes: paper SUPPORTED, repaired-e REPAIR_SUPPORTED; no authors-implementation/delivery/ABE/consensus/power-loss theorem. Historical6 recovery/expiry rows preserved; four paper crash classifications BLOCKED/unproved. Other47 schedules/live mutants/windows/report/all3same-report-source ACKs/every gateE criterion remain; E/RQ1 active, E0closed/C-E1complete/E2-E3permitted, F/Glocked. No source/tool/custody/interface change; historical531 unit tests not rerun as live evidence. Read through A1-0052/A2-0032; no human action needed. Scheduled/coordinator guards held before fetch/services/publication; finally cleanup/publication recorded in external run 20261009T021359Z/memory. Author self-review only, weaker than independent review.


## D46 — C-E2 identical-request replay plan, 2026-10-09 UTC

PLAN-CHOICE-PENDING-EXACT-ACK: A3-0041 plan `a7732650007e9b06a3de49bbe5cc36c1baed674f67eb4e947da9cbbef851d652`.
Routine public evaluator slice of frozen E01-nonce-replay choices: fresh3 profiles,
original allowed grant then identical policyEnf/consumeDecision at fresh transaction
nonce before release; require REPLAY8/no whole native-worker-history change;
then original release/completion/outcome and Bob denial. Both exact new full-plan
ACKs before services. No new reference, timing permission, key ownership, ABI/wire,
tool/dependency or owner pin. Equal idle worker logs do not prove retry/idempotence.
Synthetic584 tests and actual ACK refusal only; no new live class or gate result.
Evidence: evaluation/evidence/e2/nonce-replay-runner-20261009/README.md.


## Current checkpoint — replay attempt FAILED at repaired release, 2026-10-09 UTC

Actual CLI2/FAILED in 341.181s. Paper-strict/minimal complete PASS; repaired-e replay subcheck PASS then first release EXPIRED; completion/outcome/Bob NOT_RUN. No three-profile success. Original expiry1791521422; probe10.210406s, release04:50:22.053340UTC at corresponding wall-clock second; worker effective-clock equality not directly measured. Failure preserved, no TTL extension. Exact A1-0054/194379c+A2-0034/ca1b8ce ACKs of A3-0041 plana7732650.. verified before services. A3-0041 RELEASED/no services/lease. Evidence evaluation/evidence/e2/nonce-replay-live-20261009/README.md.

All3 identical ACSC replays mined status0/Rejected8/no logs/whole request-grant-nonce-access-worker-both-history unchanged; grant uniqueness precedes nonce check. Paper2 catalog SUPPORTED as tested reconstruction; repaired composite BLOCKED/incomplete, different-digest same-(gid,nonce) controls unrun; idle-worker equality not retry/idempotence. Wrong-admin16 all3/Alice+Bob paper2 pass. Sources stable:85plan/303owner/121bracket/15frozen/six snapshots;9processes ended0/PIDs absent;1667commands0, CLI2 retained. Post-stop worker exporter same empty log; no full native post-refusal claim.

Historical6recovery-expiry+3duplicate preserved; paper2replay complete/repaired1incomplete/other44untouched:45 comparisons remain. Fourpaper crash classes BLOCKED/unproved; live mutants/windows/report/all3same-source ACKs/every gateE criterion remain. E/RQ1 active/E0closed/C-E1complete/E2-E3permitted/F-Glocked. Deliveryunknown/symbolic/safe-ledger/trusted-worker/no authors-implementation/ABE/consensus/power-loss theorem. ReadA1through0054/A2through0034,159communication/no divergence/postrun fetched branches unchanged. No runtime/tool/custody/interface change; historical584 unit tests not rerun. Author self-review weaker than independent.

Scheduled+separate coordinator held before fetch/services/publication; finally cleanup/publication external20261009T044325Z/memory. No human input/peer module repair needed. Next owned runner timing revision preserving snapshots/original expiry; RED/GREEN/source-complete new FREEZE/both exact ACKs before services, then remainingE/report/gateE.


## Current checkpoint — grouped replay completed, 2026-10-09 UTC

Actual CLI0/E2_NONCE_REPLAY_SLICE_PASS: 3/3 fresh comparisons PASS in 375.185s. Exact A1-0056/d89fc843/9bac585b.. and A2-0037/6ce46bd6/0c309f16.. ACKs of A3-0044 plan1b3cf7cd13ea8b1436396f8cc6268bbbdcae753661730290043ee144c1804a32 verified before services. A3-0044 RELEASED; no services/lease. Historical failed nonce-replay trial retained unchanged; no expiry extension. Probes: paper-strict 7.074894s, paper-minimal 6.999435s, repaired-e 6.995111s. Wall timing is not direct worker effective-clock margin.

All3 identical ACSC calls/fresh transaction nonce/mined status0/Rejected8/no logs; entire request/grant/nonce/access/idle-worker/both-history unchanged. One explicit block per chain/snapshot and individual ABI/calldata/return rows checked. Original Alice release/completion/one outcome plus Bob policy9 and wrong-admin16 pass all3. Existing grant uniqueness precedes nonce checking; distinct-digest same-(gid,nonce) and new-reference stress unrun. Equal idle-worker logs are not worker retry/idempotence. Paper-derived/symbolic/safe-ledger/trusted-worker; deliveryunknown/no authors-implementation/ABE/consensus/power-loss theorem. Boundary identity cannot detect transient drift restored between checks.

Sources stable:86 plan inputs/303 owner blobs/123 bracket inputs/15 frozen copies/six snapshots. All9 owned processes ended0/PIDs absent;1841 captured owner/RPC commands exit0, mined negative receipts retained.167 latest communication paths/no divergence. Historical599 unit tests not rerun; actual integration and read-only audit provide this run's evidence. Author self-review only under no-extra-agent rule, weaker than independent. Evidence: evaluation/evidence/e2/grouped-replay-live-20261009/README.md.

Historical6 recovery/expiry+3duplicate preserved; replay 3complete; 44 catalog comparisons still need completion. Four paper crash classifications BLOCKED/unproved. Live mutants/windows/RQ1 report/all3same-report-source ACKs/every E criterion remain; gateE NOT_RUN/F-Glocked. No human input or peer source repair needed. Next: earliest remaining E01 public runner/oracle schedule, preserve controls, full revised plan and BOTH new exact ACKs before services. Scheduled exclusive guard plus separate coordinator held before fetch/services/publication; finally cleanup/publication external20261009T061325Z/automation memory. No peer/module/mailbox/archive/frozen/main edits or worktrees/extra agents; preexisting untracked scheduled-runs preserved unstaged.


## Current checkpoint — subject oracle code corrected, 2026-10-09 UTC

C-E2 WORKING. Exact A1-0058/e66eeb91/1e3644dd.. identified a real evaluator
error: frozen WRONG_SUBJECT is `2`, not `3` (WRONG_DESTINATION). Fixed the oracle
and mirrored fixture; wrong-code control now supplies `3`. Test-first RED:
2 failed/69 passed; GREEN71; fresh root670 PASS/exit0 in108.89s,106 inputs stable.
Post-suite303 selected owner blobs/15 frozen copies verify. Earlier subject
preparation prose using `(3)` is superseded; historical raw evidence is preserved.

No new live subject collector, integration, release or gate result. E0closed/
C-E1complete; gateE NOT_RUN/F-Glocked;44 comparisons remain/four paper crash
classes BLOCKED. No services, execution FREEZE or lease. A1 review is not a plan
or report ACK; no peer module repair or human input needed. Next: public subject
collector in separate fresh stress/control states, recipient/symbolic completion,
complete revised plan/FREEZE/BOTH NEW exact peer ACKs before services.

Evidence: evaluation/evidence/e2/subject-code-fix-20261009/README.md.172 latest
communication paths/no divergence; final fetched peer tips unchanged. Frozen/
ABI/owner/tool/dependency/custody bytes preserved. Author final review under
no-extra-agent rule; scheduled+separate coordinator guards through publication,
finally cleanup/verified remote commit in automation memory. A3-0047 responds to
A1-0058 with the correction; no execution ACK requested. Preexisting untracked
scheduled-runs preserved unstaged; only reviewed owned agent-3 publication.


## Current checkpoint — subject completion checker prepared, 2026-10-09 UTC

C-E2 WORKING. Added independent paper-profile routing/completion checker:
recheck pre-release subject facts; require Bob registered nonzero key distinct
from Alice, unchanged native zero recipient/original pending Alice request,
response/token/cache/native-grant/record joins, one fresh intent/send strictly
within original expiry, Bob symbolic completion and Alice WRONG_SUBJECT refusal.
Release and both completions preserve whole native histories/nonces/count; both
completions leave the worker unchanged. No outcome is fabricated for Alice.

Tests-first missing-feature RED87 -> GREEN87. Fresh root777 PASS/exit0 in117.25s;
190 suite inputs unchanged. Six deliberate in-memory check-removal controls admit
false facts which the real checker rejects. Script import-path failure retained;
corrected invocation passes.303 selected owner blobs/15 frozen copies verified.

No live subject release/completion, collector extension, fresh integrated controls,
new FREEZE or lease.44 catalog comparisons remain/four paper crash classifications
BLOCKED/unproved; gateE NOT_RUN/F-Glocked. Next: public completion collector with
authenticated registered keys/ciphertext and same-response Bob/Alice key-reference
calls; separate fresh Alice/Bob/wrong-admin deployments; complete revised execution
plan/FREEZE and BOTH NEW exact owner ACKs before services. Old plan ACKs cannot
cover these new evaluator bytes. This pure checker is not a completed E01 case.

Evidence: evaluation/evidence/e2/subject-completion-oracle-20261009/README.md.
174 latest communication paths/no divergence; fetched peers e66eeb91/96ebe160
unchanged; read A1through0058/A2through0038. No new ACK inferred or requested,
owner source/ABI/frozen/dependency/custody change or human action needed. Author
review under explicit no-extra-agent rule is weaker than independent. Scheduled
exclusive guard + separate coordinator held before fetch through publication;
finally cleanup/publication recorded externally and in automation memory.
Preexisting untracked scheduled-runs preserved unstaged; exact owned agent-3 only.


## D47 — Paper crash rows relabelled SPEC_GAP next to the frozen BLOCKED label (solo phase), 2026-10-09 IST

DECIDED by agent 1 under the human solo directive (A1-0059). The ruling is A1-0061 G-4 / D-S2, which amends A1-0060. Recorded by agent 3 (proxy). It is **solo, correlated self-review**: the original agents 2 and 3 can overturn it on return.

**Scope:** the four rows E03-crash-after-intent and E03-crash-after-send, each in paper-strict and paper-minimal.

**Ruling:**
- Report the paper property as **SPEC_GAP (ambiguity)**, with outcome **UNPROVED**.
- Every report table shows the **pre-registered frozen label BLOCKED** next to the decided label, citing D47.

**Reasons:**
- The frozen qualification predates D35/A2-0012: paper grants and releases now run in production.
- The mechanics ran live (A3-0036, A3-0038).
- HMBC is silent on worker durability, retries and crash recovery (S2-0002).

**What this is not:**
- not a pass;
- not a changed outcome;
- never a finding.

No frozen bytes change. Repaired-e crash rows stay REPAIR_SUPPORTED for bounded logical mechanics only. Evidence: S2-0002, S3-0002 G-4, A1-0061.

## D48 — Solo-phase evaluator portability (SL0), 2026-10-09 IST

DECIDED by agent 1 (A1-0061, D-1..D-5), implemented by agent 3 (proxy) in SL0 (S3-0004). Solo, correlated.

- **Solo review mode** (`reviewMode: solo-correlated`):
  - FREEZE IDs are S3-NNNN; ACKs are A1-NNNN (agent 1) plus S2-NNNN from a declared `agent-2 (proxy…)`.
  - The committed FREEZE carries `Plan-sha256`.
  - Every FREEZE and ACK blob is read from a commit that is an ancestor of HEAD.
  - Plans and results carry the correlated-review disclosure.
  - Strict A2/A3 verification is unchanged. Nobody writes A2/A3 messages.
- **Host tool override:** `evaluation/host-tools.json` maps frozen tools to local paths.
  - Each binary must hash to the frozen `evaluation/toolchain.json` value, which stays byte-identical to `interfaces/v1/toolchain.json`.
  - A frozen path that exists never falls through to the override.
  - The only exception is a declared local ProVerif 2.05 build: binary bc2cd5ed.. against the frozen c1087205..; source 4871f53c.. equal.
- **Ports:** solo plans use PBC 18545 / DBC 18546. Chain IDs stay 18545/28545. Strict plans keep 18545/28545.
- **Cast hash policy:**
  - Solo plans use `castHashPolicy: checkpoint`: Cast is hashed at construction, at each read group and submit, and at run start and end.
  - A mismatch refuses that call and every later one.
  - Strict per-call hashing is unchanged.
- **Python:** 3.13.5 on this host is recorded against the frozen 3.13.13 as `hostDifferences`.

Evidence: `evaluation/evidence/e2/sl0-portability-20261009/README.md`.

## D49 — SL2 runner defect and the verified never-instantiated worker rule (solo phase), 2026-10-10 IST

Decided by agent 1 (diagnosis message after S3-0008); implemented by agent 3 (proxy) in S3-0009. Solo, correlated.

**The defect.** The first SL2 run (plan d67f1786.., S3-0007) failed before any stress transaction.

- The pinned worker creates its database lazily (`adapter._worker`, adapter.py:133-136), only on `release`, `encrypt_record` or `finish_decryption`.
- The relay stress performs none of these, so the exporter refused the fresh D2 state.
- This is an evaluator recipe defect, a tested reconstruction result of the runner. It is **not** a protocol or ledger finding.
- The failed trial is kept in `evaluation/evidence/e2/sl2-relay-failed-20261010/`.

**The rule.** An idle worker may be recorded as `{instantiated: false}` only when all three hold:

1. the pinned exporter exits 1;
2. its output is exactly `no worker.sqlite in <state> (looked in <dir>/worker/ and in <dir>)`;
3. the runner confirms on the filesystem that both database paths are absent.

It is never recorded as an empty export. Before and after must be both never-instantiated, or both equal idle exports; any other refusal fails.

**Prohibited:** instantiating the worker through `encrypt_record` or any other state-changing call to avoid this.

Implemented in `evaluation/e1.py` (`observe_worker_export`), `relay_stress.py` and `oracles/provenance.py`. New plan b3a02098.. (S3-0009).

## D50 — Returning Agent2 successor candidate and F0 prerequisites, 2026-10-12

Agent3 REVIEW A3-0051 answers A2-0039. The owner-published exporter URI fix at
agent-2 79bfb4afdb6fb12622c913b0991ad5c089602d24 / source manifest005c8448.. is an
accepted successor **candidate** for future F0 planning. Historical E pins/report
and v1 freeze remain unchanged. No current integrated source plan has adopted it.
No F implementation or execution FREEZE ACK is authorized by this decision.

D-2 is a measured reconstruction limit: current worker/evaluator fingerprint
binds chain IDs and four addresses, but not profile/mutations/runtime code, and
cannot distinguish clean/mutant fresh chains with matching deployment addresses.
A new private SQLite binding belongs in a future F0 prerequisite RFC. Its exact
formula, encoding, all six roles/runtime hashes, trusted source validation,
fail-closed old-state migration and restart/negative controls require owner and
consumer ACKs. Retaining the exported fingerprint preserves bytes; it does not
establish stronger provenance or guarantee zero evaluator impact.

Agent2 may draft that RFC when F0 planning is human-authorized. D-4 stale production
labels and D-6 strict JSON backlog stay for a later exact owner revision. Durable
single-signing and deterministic certificate expiry remain F planning requirements.
F0 needs its separate plan/human go-ahead; G remains locked. No paper vulnerability,
new gate PASS, independent review or replacement historical ACK is claimed.

## D51 — Human-authorized main merge and common F0 starting branches, 2026-10-12

The human explicitly directed: "merge work from all 3 agents' branches into main,
and then normalise their individual branches as well so that all 3 can start F
having the same initial files". This authorizes this one consolidation into main
and normal fast-forward publication of the same commit to agent-1/2/3. It does
not transfer module/mailbox ownership, rewrite history, or authorize subsequent
main/peer-branch pushes. Existing local unpublished work on peer machines stays
under its owner; remote convergence does not prove those checkouts were updated.

Reviewed incoming commits and fresh verification are in communication/F0_BASELINE.json
and evaluation/evidence/reviews/f0-baseline-20261012/. Agent1 was already an
ancestor of Agent3; Agent2 is merged with three conflicts resolved to exact
owner-authored README/manifest/mutation-checker bytes (A2-0039 recommendation).
All protocol files remain exact owner blobs, signed E bytes and frozen v1 unchanged.
The stronger worker binding from D50 and later D-4/D-6 remain candidate revisions.

The common files are the starting point for **F0 planning**. Human go-ahead to
prepare/start F0 is now recorded, superseding older waiting-for-go-ahead prose.
PLAN section 6 controls the next tasks: component/attacker/key-control matrix,
n=4/q=3/f=1 assumptions and expected safety/availability classifications, then
exact affected source/interface ACKs before F implementation/experiments. No
F implementation, TLC result, integrated F evidence, new source execution ACK or
F gate PASS is created by Git synchronization. G remains locked.

Local synchronization: inspect/preserve uncommitted work; git fetch origin and
git merge --ff-only origin/agent-N on the assigned branch. A divergence or refusal
is a blocker to report, not permission to reset/rebase/stash/clean/force-push.

## D52 — Candidate8 design ACK receipt; successor mapping remains proposed, 2026-11-04

A3-0066 records exact A1-0104 and A2-0053 hashes/scopes for candidate8. Its intended
revision7 protocol design pins and ledger design sha2567eed1b29.. now apply as
design input, not implementation or execution pins. See input-provenance.json in
evaluation/evidence/reviews/f0-v2-candidate1-20261104/ for full hashes/commits.
Candidate8 files and historical signed/frozen artifacts remain unchanged.

interfaces/proposals/v2 candidate1 is proposed for owner review. Its README lists
new mapping choices (base repaired-f manifest with mutation bits/q2 experiment
label; q2 certificates assembled from single-witness replies), and the E mutant
profile/D50 vocabulary ambiguity. These choices are NOT ADOPTED by this record;
exact affected owner review/ACKs and final complete schema/vector mapping ACKs
are still needed. Agent2's exact binding/evidence exporter shapes also precede
consumption. D-4/D-6 remain owner tasks. No F0 freeze, F implementation, runtime
result, new gate PASS or main publication is authorized. Source READY and
execution FREEZE follow later; F NOT_RUN/G locked.

## D53 — Exact F0 design acceptance and v2 publication, 2026-11-04

A1-0110 and A2-0058 ACK the full F0 request f9f0906f.. in ledger/protocol scopes.
Agent3 verifies exact message bytes/commits/ancestry and records acceptance in
communication/F0_ACCEPTANCE_CANDIDATE2.json (03dcf485..). The unchanged request
remains a historical request. interfaces/v2/FREEZE.json (7bb1d243..) publishes
all14 candidate2 payloads byte-for-byte; their pending labels remain historical.
Acceptance retains candidate8 components/cases/controls/requiredEvidence/bounds,
with candidate2's explicitly reviewed migration. No new fault-model choice.

Owned implementation and isolated tests are now authorized. Integrated services,
scenarios and gate claims still need exact source READYs, matching mapping
receipts and a separate run/tools/config/source execution FREEZE with owner ACKs.
No source READY/run ACK is inferred from design or mapping replies.

A2-0058 N-1 is the existing plan's E preservation rule: fixed historical evidence
and manifests verify at historical commits; approved F changes to E-listed source
receive new source READY hashes and real E regressions. E operations/outputs/
default export/fingerprint and assertions remain required. No implementation
parity is declared before those tests. communication/F_SOURCE_READY.md defines
the handoff; all52 pinned protocol/f0 files and all candidate history stay fixed.

Receipt/publication verification is specification evidence only. F gate NOT_RUN,
all32 cases NOT_RUN, G locked; qualified historical E unchanged. No runtime,
TLC, service lease, new dependency, peer edit, extra agent, worktree or main push.

## D54 — Exact ledger READY review and proposed E carrier closure, 2026-11-04

A3-0077 reviews A1-0111 source aef3daa/6358359e.. for isolated F ABI/export/source
consumption after fresh hash/source/compiler/test verification. This is not an
execution ACK. Embedded E map incompleteness is reproduced; complete418source
inventory remains mandatory. A3-0078 proposes option1 with an additive distinct
E carrier marker and full12map, manifest7810ad10..; NOT ADOPTED, no schema or
consumer changed. Both exact affected ACKs and separate publication precede any
migration. A2-0059 is not an amendment ACK. Existing accepted F work may continue;
Agent2 source READY/owned evaluator work/separate complete run FREEZE remain.
No new E/F gate result/G work, services, peer edits or main authorization.

## D55 — Exact E carrier amendment accepted and separately published, 2026-11-04

A1-0114 and A2-0060 ACK exactly amendment manifest7810ad10.. in ledger and
protocol producer/consumer scopes. E_SOURCE_CLOSURE_ACCEPTANCE.json511e235f..
records their full message hashes, observed and file-changing commits. Separate
interfaces/v2.1/FREEZE.json232b84bb.. pins schema d43c3a9a.., the exact semantic
application of both reviewed additions. No original schema/proposal is overwritten;
135old non-union definitions and all other top-level values remain unchanged.
Copied historical x-status annotation is retained as ACKed, superseded by the
publication README. Wire interfaceVersion v2 and D50 preimage remain unchanged.

This authorizes owned opt-in exporter/consumer migration and isolated tests.
A3-0079 asks both owners to receipt exact schema/freeze and publish fresh matching
source READYs; proposal ACKs do not stand in for publication or run ACKs. Historical
ten-source E remains compatibility only with its known omission; F-tree E successor
uses the v2.1 marker/twelve-source map. Default v1/F carriers/history unchanged.
Fresh1884evaluatorPASS/202selected stable inputs is not integrated parity or a gate.
Full source/tools/config/run FREEZE with exact affected ACKs still precedes services.
All32Fcases/Fgate NOT_RUN/G locked; qualifiedE unchanged. No peer/main authorization.

## D56 — Evaluator Governance reads remain separate from D50 S0, 2026-11-04

Reviewed A1-0116 at8c0285ffa6986858caeb0140b930bf5db759fdc0 and A2-0062
atbeab2d1e9545ae5df3b0867503c47750f42446c8, with exact note hashes and owner
artifact pins in evaluation/evidence/f/v2-public-observations-20261104/peer-review.json.
Both are notes, not source READYs or ACKs. Agent2's differential is correlated
synthetic cross-implementation evidence; its fake facts use Agent3's expected
views and substituted synthetic runtime hashes. It is not an independent oracle
or live-chain result; no rerun or adoption of its owner test totals is claimed.

Keep the published D50 open schedule and its S0 request count unchanged. The
already accepted BOUNDARY separately requires evaluator checks of Governance
governanceChainId/maxGovernanceTtl and the compiled MAX_ADMINS attestation.
The evaluator's public ABI collector acquires both getters before reporting any
F evidence. A mismatching first binding therefore cannot pass those checks.
This implements existing evidence requirements, without a new shared schema,
open-stage rule or implied safety proof. A future change to S0 requires its own
exact RFC/affected ACKs; this record neither requests nor authorizes one.

No source READY, full consumer mapping, execution freeze or gate follows from
these notes or isolated tests. Full reviewed owner handoffs and a separate exact
source/tools/config/run FREEZE with affected ACKs still precede services. All32
Fcases/GateF NOT_RUN; G locked; qualified historical E unchanged.
