# F0 source and interface plan — candidate 8, 2026-11-04

**DRAFT FOR EXACT OWNER REVIEW. NOT FROZEN. executionAuthorized=false.**
Goal: make the conditional n=4/q=3/f=1 application-certificate experiment
implementable while retaining the completed E study. This is an HMBC2020
paper-derived reconstruction with synthetic fixtures and symbolic crypto.
Agent3 proposes the choices below; no owner's silence is an ACK.

Spec: SPEC.md section 5, PLAN.md section 6. Candidate7 is preserved at
90ed51baa5b77505a8f1b7f1c66cfb9c1efeee04. Agent1 A1-0103 at
4c5b6914573f3a049797948f78d7f24dc8795ab8 ACKs candidate7 in ledger scope only;
Agent2 A2-0052 at e0f25ef861a7423f07dcd3677e3f614990045609 is a REVIEW
withholding ACK pending C-1..C-3. Neither transfers to candidate8.
Revision-4 F0 set: f746098c78bff2e1d0abcf8600934469a3f9a03a (A2-0046).
Production protocol bytes equal common baseline
376347d9b0979d1e46824a30197b935ffe91e4fb; E manifest SHA-256
005c8448faeb90d2dade129211a5f220635ee1c8bf421c89f17b2b7d0c2d7612.
The intended F0 amendment is revision7 at 0b81ee46c487488022585c99335c0e3fa0fa10c4,
whose exact signing/wire/manifest hashes below become design pins only after both
owners ACK candidate8. No implementation pin or execution authorization follows.
Frozen interface-v1 and signed E bytes stay immutable. No package, root lock,
cryptography change, extra agents, worktrees, main push or peer edits.

## Proposed scope and alternatives

Carry C0/a1/b1/c1/d1/e1 and reuse the existing QuorumLib rather than creating a
second verifier. Add profile REPAIRED_F=3 and mutation bits to the four profile
carriers, separate Governance, scoped authority/admin updates, and monotone
checkpoint/policy state. Reset e2 and DBC user-signature d2 remain deferred;
label d1's f=2 authenticity residual. These are the minimal owner-described
changes, not approval to implement the broader alternatives.

Use four supervised witness processes, each with one key, state directory and
exclusive lock; one adapter start command. The single-process alternative costs
less supervision but fails the real process-withholding/restart experiment.
Same user/host and public synthetic keys prevent a host-independence claim.
Use explicit per-witness TEST-ONLY governance approval tuples plus structural
and TMSC checks. Publish fixtures/dissent; do not infer a hospital consent rule
from the paper. Fixed witness identities/version 2; credential removal does not
reconfigure validators.

Use E1: keep the 21 Error.code values and add reason/collection only in the
candidate v2 schema. A collector timeout is ADAPTER_UNAVAILABLE with reason
QUORUM_UNAVAILABLE; INSUFFICIENT_QUORUM remains a submitted-certificate rejection.
The new-code alternative changes ledger meanings without helping this study.

## Shared interface work, Agent3 only after exact design ACKs

- Create interfaces/v2/README.md, hmbc.schema.json, BOUNDARY.md and vectors/;
  publish a candidate manifest before implementation. Do not edit interfaces/v1.
- Add repaired-f/profileEnum 3, Governance ABI/deployment entry, fixed four
  witness labels/q3/version2, GovernanceAction and its typed signing vectors.
  Use Agent1 design 2.2 sections 2/8/9 as the exact signed fields/domain/order.
- In successor ABI exports use canonical decimal-string runtimeBytes and
  immutableReferences=[{start,length}], with BOTH start and length canonical
  decimal strings (JSON integers forbidden), sorted/disjoint, length exactly 32,
  end <= runtimeBytes, empty list allowed. Build pins come from compiled exports.
  For immutableRefsSha256 hash UTF-8 canonical JSON of that **object list**
  (sorted object keys, compact separators, ensure_ascii=true); never hash RPC
  ranges. Require this field on all seven F contracts. This representation is
  an Agent3 proposal requiring both ACKs; the owner reference's pair list is
  only its function argument, not a different wire representation.
- D50 binding: the closed B shape/encodings from revision4, prefix
  hmbc-deployment-binding/v2 followed by LF, then canonical JSON; SHA-256 in
  lowercase unprefixed hex. Hash decoded runtime bytes. Keep owner outside B.
  Anchor every read at the recorded block per chain; preserve raw observations.
  The evaluator independently reconstructs B, then compares the opt-in binding
  export. Default worker export and its legacy fingerprint remain unchanged.
- Add optional witnessIndex decimal string 0..3 on collect_checkpoint,
  collect_decision and attest_grant in v2 **synthetic experiment boundary**.
  Missing selector means pool mode, present selector means one witness. There
  is no production authorization claim for that selector. collect_governance
  takes the complete typed proposal plus optional selector. Every pool request
  chooses one common proposal; witnesses derive/check every field independently.
  Do not add caller-chosen sequence/source block to existing inputs.
- Pin SUCCESSOR-WIRE revision7 (sections outside pool retry unchanged from revision4),
  including its 19 reason mappings and precedence. Close all
  object shapes, bind each reason to its code, enforce exactly four outcomes in
  index order, q3 distinct sorted signers on success and none on timeout. Treat
  its short signature strings as illustrations; real vectors require canonical
  65-byte signatures and actual recovery. A collection response describes a
  certificate; separately record whether a transaction was submitted/accepted.
- Consume read-only witness_state --evidence and worker_log --binding, retaining
  conflict/digest/superseded/death/tripwire data and public binding observations.
  Secrets are never exported. A receipt proves authorization, not delivery.

## Numeric candidate for owner review, not measured timing guarantees

Use mined target-ledger observations, k=0, non-decreasing clocks/no reorgs.
Explicit Anvil mining cadence 1 second on both chains; freeze the start blocks
and UTC/chain observations. Checkpoint proposer window 30s, max 60s; governance
window 60s, max 120s; MAX_ADMINS=8. Decision expiry=min(request,checkpoint),
receipt block=the unique GrantIssued event block, **F only**. No original request
or grant is extended by renewal. Reuse requires **all earlier digests** dead.

Candidate transport parameters: concurrent per-witness reply timeout 5s.
At collection start read target-ledger time ONCE using Chain.now() (the
conservative direction for refusal), compute remaining=expiry-ledgerNow, then use
a host-monotonic duration min(10s, remaining-2s). Each witness has a concurrent
5s timeout. If remaining <=2s return EXPIRED with a reserve message before
contacting witnesses, with no collection and no new reason. Host time bounds
effort only; ledger-time jumps can shorten validity and expiry still decides.
Never use the host clock to declare a signature dead. Reserve 2s for
inclusion as an experimental target, not a promise. Log actual mined target
time immediately before submission; expiry still wins. Parameterize these exact
numbers in the future start contract; do not silently retry with new deadlines.
Single-witness probes use the same 5s timeout. Startup validation completes
before ordinary request windows; F-13 deliberately measures restart inside a
window, retaining expiry/timeouts if startup consumes it.

These parameters need exact owner design acceptance; feasibility is unmeasured. Before an execution FREEZE,
measure startup S0 and per-signing RPC deltas, cold restart, inclusion and q3
completion under the chosen cadence. Preserve SPEC's 10 warmups/30 seeded
repetitions for measurements. A timeout is data, not permission to widen bounds
after observing results. Any revised bounds require a new exact plan/ACKs.
S0 counts in A2-0044 are 48 (E) / 55 (F) per Ledger instance, including the
five immutable getters; five independent F processes total 275 startup requests.
These are request counts, not measured latency. Cold restart additionally opens
the store and performs one tripwire read per chain. Startup concurrency is measured
later. A1-0098 estimates about 25s for request + checkpoint collection + acceptState
+ decision collection + reserve, leaving only about 4–5s of the 30s request TTL.
This arithmetic is not a measurement; preserve timeout/expiry results.

## Owner tasks after the design and interface gates

Each task begins with failing controls, then the smallest owned implementation,
then its focused tests/full module regressions. Publish exact READY manifests.
No task below is checked off or authorized by this draft.

D50 applies to the worker store open path for EVERY profile, including E.
E manifests may omit immutableRefsSha256 (all-or-none if present). E operations,
outputs, default export and legacy deploymentFingerprint remain byte-identical;
store open changes. E regression includes the existing suite, export --check and
unchanged fingerprint. Any integrated E re-run requires a NEW protocol pin, exact
plan and affected ACKs; the historical signed E study is not reinterpreted.

1. **Agent1 ledger/export:** modify src/types/ProtocolTypes.sol and
   src/{TMSC,PSC,KSSC,ACSC}.sol, with deployment plumbing as enumerated in
   design 2.2; create src/Governance.sol and its tests;
   reuse the existing QuorumLib library in src/lib/SigLib.sol (with SigLib signature recovery). Test q3 valid, q2/duplicate/unknown/
   unsorted/wrong action/wrong domain, expired action (EXPIRED) and stale/gap
   nonce (REPLAY/MALFORMED), failed governance transaction
   whole-state rollback, removal tombstones/admin history and policy poison.
   Update tools/export_abi.py and successor exports only after schema ACK;
   include all seven runtimes/ranges. Profile helper migration must preserve
   E assertions, with design's explicit test-source adjustments. Run forge test
   --root ledger -vv and owner mutation controls; export Governance vectors.
2. **Agent2 durable signer/binding:** create hmbc_protocol/{witness_state,
   witness_service}.py; update witness.py/ledger.py/worker.py for the exact
   successor while retaining E behavior. Test crash before/after commit and
   before reply/marker, concurrent signers, same-effect renewal, all-earlier-
   digests-dead, each identity refusal, and FAULTED persistence/clear-history.
   Use revision4 WAL-aware logical-state snapshots under the exclusive store lock; main DB +
   WAL + marker form committed state, SHM is recreatable. Preserve schema and
   rows in a consistent read transaction plus marker bytes. A WAL-only refused
   write must change that oracle while leaving main-file hashes unchanged; a
   checkpoint alone must preserve the oracle. Copy/restore under lock while
   stopped, or checkpoint then copy under the same exclusive lock. Main-only
   copies that lose committed WAL are rollback, not harmless backups. Initial
   directory/lock metadata is allowed before binding; DB/marker follow binding,
   signing follows directory fsync. Inject process death only; power loss and OS
   crash remain untested. R1–R3 are resolved at design level, not implemented.
   Full store locks
   are per directory; same key in another directory/consistent rollback remain
   outside persistent-state integrity. Run tests/test_witness_state.py and
   existing E worker/witness regressions, then the full protocol suite.
3. **Agent2 pool/wire:** create hmbc_protocol/witness_pool.py and TEST-ONLY
   testtools/byzantine.py; update adapter successor export without modifying
   frozen v1 bytes. Cover one withholding, two down, invalid first reply,
   duplicates, dissent, continued collection and exact q3 submission. Reproduce
   Governance vectors and three-witness identical decision/checkpoint/receipt/
   governance digests. Run tests/{test_witness_pool,test_byzantine}.py and
   tools/mutation_check.py M1-M7 plus D50/lifecycle/collector controls.
   Add H3 per-witness RPC overrides (F-16 split-view branch, F-17/F-18,
   F-31 regression), H5 compromised symbolic worker (F-19), and H6 per-operation
   delay injection (F-20 and M7) in TEST-ONLY testtools/byzantine.py. H1 faulty
   replies, H4 process crash points and H7 stopped/locked state copy complement
   the synthetic witnessIndex H2 selector. Test-only hooks stay outside adapter
   operations and adapter.json; no production control surface is added.
   Pin hook placement/values in the future execution plan before observing data.
4. **Agent3 evaluator/model:** after ACKs create evaluation/models/f/
   {DecisionQuorum.tla,DecisionQuorum.cfg,README.md}, oracles/faults.py and
   tests/test_f_faults.py; successor schema/binding tests belong to the shared
   contract slice. Independently validate recovery/log joins, expired-but-live
   renewal histories, signatures/decisions and transaction acceptance. TLC must
   distinguish durable choices/emission, expiry/overtaking, simultaneous live
   conflicting effects, and certificates/accepted effects. f0/1 positive checks,
   q2/f2 controls and explicit divergent-view assumptions are required. Pin jar,
   Java and commands/counts before reporting any model result. Retain positive
   access and correct denial controls against permissive and deny-all mutants.
5. **Agent3 integrated evidence/report:** only with READY source manifests,
   exact interface/tool/config/run ACKs and execution FREEZE: run the revised
   matrix with fresh chains/state per schedule, independent public-boundary
   evidence, pre/post hashes, owned PIDs and explicit cleanup. Cover F-30 honest
   refusal and separate crafted invalid-action rollback, F-27 corruption versus
   undetectable consistent rollback, F-29 all-digest death/idle-miner stall,
   F-13 cold startup, M1-M7, and q3 common-digest controls. F-25/26 are analysis
   only; public fixture keys/no payload store cannot demonstrate theft or real
   storage corruption. Then E regressions, RQ2-F.md and all three gate ACKs.

## Gates and remaining exact approvals

A2-0044 resolved R1–R3 at design level. The historical revision4 pins and
candidate6 ACKs remain historical and are not the intended candidate8 freeze pins.
Intended revision7 design pins, conditional on both exact candidate8 design ACKs:
- D50 b178e0a8942dc1d4c99165a4b526c30813efc17dbbeb216492b9be6940247a18;
- SIGNING-RULES 23a88159c869e767d4305236c089c6682a5a6be070afa43756e24b5f3f7919fb;
- SUCCESSOR-WIRE 065c46db8f3308e531b6b83db4bbf23cbe26f861a983a0af39ac3e86d505aa58;
- protocol/f0/MANIFEST.sha256 097d8ed8a8d4e094195f620f53b9c7839a2426210538c75ed06ad16c5f9fa6a0.
Obtain both owners' exact ACKs of this plan, the WHOLE revised matrix/CSV, and
numeric/source choices. Then publish full candidate v2 schema/vectors and obtain
exact mapping ACKs before consumption. Final F0 freeze records all hashes;
fresh source READY/execution ACKs remain a later gate. No module implementation
is authorized by this candidate. A1-0103 covers candidate7 ledger scope only;
A2-0052 withholds candidate7 protocol ACK. Neither is a candidate8 ACK.

Self-review scope: the mappings below cover the newly identified obligations; new wire/ABI/dependency
rules precede consumption; the main risks (WAL, cold restart, all-digest expiry,
invalid-first reply, constructor/storage limits) each has a control above.
Missing implementation/runtime/timing/TLC evidence remains NOT_RUN. Historical
qualified E is retained; F gate NOT_RUN and G locked.


## Retained candidate5 corrections and experiment coverage

K2 (A1-0100): FL-10 now isolates SET([]) to REMOVE action substitution (bit 6)
and repeatable SET replay (bit 7), with matching/fresh-nonce controls, expired
versus stale/gap errors, and whole governance state/log/event evidence. Its old
ADD-to-REMOVE title was misleading because payload shape already rejects it.
K3: F-28 requires PBC removal refusal and BOTH DBC barrier phases; use separate
equivalent fresh-state branches so a consumed grant cannot mask the second
phase. These are design/test obligations from ledger design2.2 sections6/7.

A2-K1: all M1-M7 are defined and mapped here and in the matrix. They are
deliberate source mutants, not observed vulnerabilities. Baseline controls must
reject the weakened behavior while legitimate access remains possible.

| Mutant | Definition | Pre-registered row/control |
|---|---|---|
| M1 | no durable conflict record | F-12, two live checkpoint certificates for one sequence |
| M2 | emit signature before durable commit | F-12/F-13, kill after emission before commit then conflicting proposal |
| M3 | declare expiry/re-sign from host wall clock | F-29, host advances while mined ledger still keeps an earlier digest live |
| M4 | skip all-field checkpoint validation | FL-7/F-24, honest signature on poison; ledger backstop separately classified |
| M5 | collector forwards replies without recovery/filtering | FL-5/F-22, invalid first reply reaches BAD_SIGNATURE instead of valid q3 submission |
| M6 | receipt reference uses DBC head instead of GrantIssued block | FL-1, mine between reads, compare all three digests |
| M7 | decision expiry retains local-clock term | FL-1, H6 delay with a binding clock-term fixture, compare all three digests |

M6/M7: keep the fourth witness silent, so disagreement among the three required
signers prevents a common-digest q3 certificate. For M7 merely delaying ordinary
30s requests is insufficient: the extra term may never bind. Pre-register a
valid skewed-clock fixture where min(request.expiresAt, checkpoint.expiresAt)
exceeds the early witness target time + DECISION_TTL; delay another witness
across a mined second boundary, retaining request validity on both chains. Save
all candidate expiry terms and show the minimum changes under M7. The ordinary
no-skew fixture is a positive control, not a sensitivity claim. Exact fixture
values/source pins need later execution ACKs; no feasibility result is claimed.
Sensitivity-only candidate schedule: at DBC time T accept a checkpoint expiring
at T+60 (explicit override of the ordinary 30s proposal window, within max60).
The included PBC request was forwarded at PBC time T+20 with expiry T+50 (TTL30).
Read decisions at DBC T+1 and T+2, with PBC still before T+50. Baseline expiry is
T+50 for both; M7 gives T+31 versus T+32. This is a deliberately skewed synthetic
clock fixture, not measured clock behavior. Freeze actual start blocks and T
before execution; do not select a favorable schedule after seeing the outputs.
F-27 adds the WAL-only refusal-write mutant, main-only rollback classification
and checkpoint-preserves-logical-state positive control from revision4.

A2-K2: all F-16..F-20 are planned integrated synthetic experiments, not silently
model-only. The future report must label unexecuted branches NOT_RUN. H3/H5/H6
are Agent2 task3 testtools obligations; Agent3 task5 supplies schedules/oracles.

| Rows | Integrated schedule and assumption | Separate model/analysis |
|---|---|---|
| F-16 | safe-view replay/stale proposal with one faulty witness; separate H3 split-view branch OUTSIDE safe-ledger assumption | no claim of consensus failure |
| F-17 | H3 divergent honest RPC views plus two Byzantine keys, formed q3 certificates vs canonical-ledger acceptance | TLC boundary control, explicitly divergent views |
| F-18 | H3 divergent views and mutant-f-q2, one Byzantine key; formed certificates vs ledger acceptance | TLC q2 control, same extra view assumption |
| F-19 | H5 bypass of symbolic worker authorization, honest refusal positive control | no real secret theft or cryptographic result |
| F-20 | H6 delays 0/1/6/11/31 seconds, operation placement frozen before execution, original deadlines retained | no arbitrary-delay temporal liveness proof |
| F-25/F-26 | NONE: analysis-only, public synthetic keys/no real payload store | custody/storage residual inventory only |
| F-31 | H3 observed number/time/hash regression, fault refusal/restart/explicit clear | outside safe-ledger interval, never reclassified by clear |
| F-32 | old worker/witness stores on fresh differing deployments at identical addresses | independent D50 reconstruction; no consensus claim |

A2-K3: add F-31 and F-32 (32 total cases, all NOT_RUN, 14 components).
Agent2 task2 implements tripwire persistence/clear and all-profile D50 lifecycle;
task3 supplies TEST-ONLY observation/deployment fixtures; Agent3 task5 independently
joins observations/refusals/signatures and WAL-aware logical snapshots. F-31
requires a valid signature before fault, WITNESS_FAULTED with no signature after,
FAULTED after restart, and clear preserving ALL conflict/digest/superseded rows
plus appending fault_log. A clear that deletes history is a sensitivity mutant.
F-32 requires same-deployment reopen success; BINDING_MISMATCH on different
profile/runtime/state with identical addresses; fresh-B-directory success; and
LEGACY_STATE for an E store with committed rows and no binding. Refusals leave
logical state/marker unchanged. Exercise the keyless worker and witness owners.
Only lock/directory metadata may precede the binding check, per revision4.

## Candidate7 review of Agent2 revision7 (A2-0051)

Agent2's exact revision7 F0 manifest is `097d8ed8a8d4e094195f620f53b9c7839a2426210538c75ed06ad16c5f9fa6a0` (36 entries). Its protocol design pins are `SIGNING-RULES.md` `23a88159c869e767d4305236c089c6682a5a6be070afa43756e24b5f3f7919fb` and `SUCCESSOR-WIRE.md` `065c46db8f3308e531b6b83db4bbf23cbe26f861a983a0af39ac3e86d505aa58`. The F0 protocol files are proposed design material; production protocol files and E manifest remain unchanged. Candidate6 ACKs A1-0102 and A2-0050 were against candidate6/revision4 pins and do not transfer. Candidate7 subsequently received A1-0103 in ledger scope; A2-0052 withholds protocol ACK. Neither transfers to candidate8.

**Agent3's design decision for R6:** adopt the separation of selection and action. `collection.adopted` records only the pair-rule selection from the one-time report snapshot. `collection.adopted.reproposal` records whether the action was `sent`, `skipped_validity` or `skipped_deadline`. The <=2s rule gates only re-proposal and never changes the report projection or declares a signature dead. At the original collection deadline, close a snapshot over reports received by then, apply the same pair rule, record `skipped_deadline`, and run no second round or late collection. This explicit partial-snapshot rule is accepted as a design choice; it is not a timing result. A no-selection hard-stop alternative would also be safe, but is not the candidate7 choice.

The proposed successor v2 mapping includes `collection.timing` (the five closed fields pinned in revision7) and `collection.adopted.reproposal`, together with the already proposed `recordedReports`, `inconsistentReports` and `lateReports`. It must also carry single-witness `error.recorded={message, signature}` only for StateCheckpoint `CONFLICT_PINNED`, `collection.adopted.{message, reporters}`, and the rule that `collection.timing` is present iff any pool-retry member is present, per SUCCESSOR-WIRE revision7. This enumerates obligations, not a schema or mapping ACK. Frozen v1 bytes remain unchanged. These fields and their mapping still require both exact design ACKs before the full v2 schema/vectors, exact mapping ACKs and F0 freeze.

The owner checker recomputes close reason and action from declared fields, but that is internal consistency, not proof that the fields came from observed events. F-12 therefore adds required evidence for the raw runner event trace: the one target-ledger time observation at start (including latest/pending inputs), host-monotonic start and each witness reply arrival, close event/reason, pool sends/cancellations, and reconciliation of that trace with `collection.timing`, report partitions, `adopted` and `reproposal`. Actual witness signature checks, timing, liveness and both recovery schedules remain unrun.

Candidate7 refreshes only the F-12/F-29 dependencies and controls that depend on pool retry. The M8/M9, inconsistent-reporter, prefix/late, reversed-order, two-Byzantine and both pinned/unpinned recovery controls remain pre-registered. The unpinned positive still requires the TEST-ONLY delivery hold/cancel hook and more than 2000 ms validity for A at snapshot close; the pinned branch remains an availability failure, not a safety finding. All 14 components and 32 cases remain NOT_RUN. No F implementation or execution is authorized.

Next: obtain exact candidate8 ACKs from agents1/2; then produce the full successor v2 schema/vectors including the D-4/D-6 items noted by agent2 and obtain mapping ACKs; then freeze F0 before implementation. Source READY and execution FREEZE follow later. Historical qualified E PASS, signed bytes, frozen v1 and earlier candidates remain unchanged; F is NOT_RUN and G locked.


## Candidate8 mechanical corrections after A2-0052

C-1: F-12 now explicitly carries the 2-2 ambiguous split, the f=2 fabricated-value
positive boundary control, and the honest-pair selection despite an excluded
equivocator. These are prospective extension controls, not observed results.
C-2: F-29 pins the complete revision7 SIGNING-RULES SHA-256 in its dependency.
C-3/N-1: distinguish revision4 F0 set from common production bytes; the intended
conditional design pins are revision7, enumerated above. Matrix protocolCommit
retains the historical revision4 commit and is explicitly labelled as that set.
N-2: the 5000ms F-12 snapshot fixture holds or silences witnesses 2 and 3, so it
cannot close early through all-replied. N-3: enumerate the remaining wire mapping
obligations above. No numeric bound, ledger-facing case, ownership or gate changes.
CSV is byte-identical to candidate7; its candidate7 labels describe that historical
proposal. All 14 components/32 cases remain NOT_RUN; no candidate8 owner ACK exists.
