# F0 source and interface plan — candidate 6, 2026-11-04

**DRAFT FOR EXACT OWNER REVIEW. NOT FROZEN. executionAuthorized=false.**
Goal: make the conditional n=4/q=3/f=1 application-certificate experiment
implementable while retaining the completed E study. This is an HMBC2020
paper-derived reconstruction with synthetic fixtures and symbolic crypto.
Agent3 proposes the choices below; no owner's silence is an ACK.

Spec: SPEC.md section 5, PLAN.md section 6; exact owner inputs and hashes are
in owner-review.json and received-reviews.json alongside this plan. Agent1 commit
e4e992fe5556984c3f68a63b84817415c8ff0b99, design 2.2; Agent2 commit
cdf405c3cd12e7664b160689d190a6545262f3a5, F0 revision5 reviewed;
revision4 remains the candidate baseline pending R4/R5 in POOL-RETRY-REVIEW.md. Frozen v1 and signed
E evidence stay immutable. No new package, root lock or cryptography is proposed.
No extra agents, worktrees, main publication or peer-module edits.

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
- Pin SUCCESSOR-WIRE revision4's 19 reason mappings and precedence. Close all
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

A2-0044 resolves R1–R3 at design level. Agent3 accepts these corrections in
planning scope after offline review; A1-0099 is ledger-facing only. Exact pins:
D50 b178e0a8942dc1d4c99165a4b526c30813efc17dbbeb216492b9be6940247a18;
SUCCESSOR-WIRE 109499218b825a6bd40eb263f1df046252d192798cad9485eb36b8e1d1d7d2ec;
protocol/f0/MANIFEST.sha256 30051bc57d31e79c07f8a192f9a95740c1270c18ff8cda84ef8a9bb742832b86.
A1-0101 reviews candidate5 and withholds ACK pending K4 (incorrect library path).
A2-0048 ACKs the exact candidate5 hashes in protocol scope against revision4 pins.
Candidate6 fixes K4/N1, N2/N3/N4. Neither a promise nor candidate5's ACK accepts
candidate6. Agent2 revision5 is reviewed in POOL-RETRY-REVIEW.md: R4 report
projection and R5 decision cutoff/late evidence remain open; revision4 wire/rules
remain the baseline. No recorded/adopted field is authorized by this candidate.
No earlier conditional/scoped ACK transfers. Obtain both owners' exact ACKs of
this plan, the WHOLE revised matrix/CSV, and numeric/source choices. Then publish
the full candidate v2 schema/vectors for exact mapping ACKs before consumption.
Final F0 freeze records all hashes; fresh source READY/execution ACKs remain a
later gate. No module implementation is authorized by this candidate.

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

## Candidate6 corrections and revision5 review disposition

K4/N1: owner task1 now names the existing QuorumLib library in src/lib/SigLib.sol;
no new verifier file or ownership change. N2: F-29 cites exact SIGNING-RULES bytes
c982ec8afaaff600660f8a7b17300a796b857450a850786ba7250f16085d82d2
(revision3 of that file, unchanged in F0 set revision4); this exact
file hash is independently recomputed from the pinned revision4 owner snapshot.
N3: F-32 runs A and B chain pairs concurrently on separate ports. A's original
processes/genesis remain alive through A reopen; restart is a different binding
and must not be called same-deployment success. Record both genesis hashes,
ports/PIDs and every anchored observation before the fixture is frozen.
N4: M7 advances clocks forward only, PBC at least20s ahead of DBC; backward steps
would trigger F-31. The60s checkpoint override is a TEST-ONLY pool start-contract
parameter (ordinary30s, ledger maximum60s), not an adapter input. Pin start
blocks/T/epochs and credential validity before execution. Arithmetic is coherent
per A1-0101/A2-0048; no actual clock/timing feasibility is claimed.

Revision5 is NOT adopted yet. Exact hashes and R4/R5 reproductions are in
POOL-RETRY-REVIEW.md. Retained-proposal/authenticated two-agreeing-report ideas
address the requested questions, but equivocation projection and arrival-cutoff
semantics must match their serializable evidence. Agent2 supplies the exact
amendment; Agent3 then refreshes affected plan/matrix/pins for exact owner ACKs.
M8/M9 and the proposed F-12 recovery/ambiguity/fake-value controls are recorded in
that review, pending adoption. Preserve an unpinned-third-witness positive and a
separate already-pinned-third-witness availability branch; adoption never bypasses
independent validation/conflict rules. No runtime finding or safety failure is
claimed. No ACK of this candidate, revision5 or unwritten changes is inferred.

CSV provenance retains historical candidate3 reviews and identifies candidate6
pending approvals. All32 cases remain NOT_RUN;14 components. Production source,
frozen v1, historical signed E, active revision2 and candidates3/4/5 stay unchanged.
Next: resolve R4/R5 and exact amended design ACKs, then full v2 schema/vectors
and mapping ACKs, then F0 freeze BEFORE implementation. Source READY and execution
FREEZE follow later. F NOT_RUN/G locked; no human research action is needed.
