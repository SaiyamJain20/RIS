# F0 source and interface plan — candidate 3, 2026-11-04

**DRAFT FOR EXACT OWNER REVIEW. NOT FROZEN. executionAuthorized=false.**
Goal: make the conditional n=4/q=3/f=1 application-certificate experiment
implementable while retaining the completed E study. This is an HMBC2020
paper-derived reconstruction with synthetic fixtures and symbolic crypto.
Agent3 proposes the choices below; no owner's silence is an ACK.

Spec: SPEC.md section 5, PLAN.md section 6; exact owner inputs and hashes are
in owner-review.json and scoped-ack.json alongside this plan. Agent1 commit
3b5c4140ba41240d1df7384ef7201bae7684c489, design 2.2; Agent2 commit
d4d5ff0eea1cb94c4f486bfeb3f52968e085a32f, F0 revision 3. Frozen v1 and signed
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
  immutableReferences=[{start,length}], sorted/disjoint, length exactly 32,
  end <= runtimeBytes, empty list allowed. Build pins come from compiled exports.
  For immutableRefsSha256 hash UTF-8 canonical JSON of that **object list**
  (sorted object keys, compact separators, ensure_ascii=true); never hash RPC
  ranges. Require this field on all seven F contracts. This representation is
  an Agent3 proposal requiring both ACKs; the owner reference's pair list is
  only its function argument, not a different wire representation.
- D50 binding: the closed B shape/encodings from revision3, prefix
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
- Pin SUCCESSOR-WIRE revision3's 19 reason mappings and precedence. Close all
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

Candidate transport parameters: concurrent per-witness reply timeout 5s;
overall collection deadline min(start+10s, proposal expiry-2s), measured on a
monotonic host clock for transport only. If the remaining window is <=2s refuse
collection; never use that clock to declare a signature dead. Reserve 2s for
inclusion as an experimental target, not a promise. Log actual mined target
time immediately before submission; expiry still wins. Parameterize these exact
numbers in the future start contract; do not silently retry with new deadlines.
Single-witness probes use the same 5s timeout. Startup validation completes
before ordinary request windows; F-13 deliberately measures restart inside a
window, retaining expiry/timeouts if startup consumes it.

These parameters need owner feasibility ACKs. Before an execution FREEZE,
measure startup S0 and per-signing RPC deltas, cold restart, inclusion and q3
completion under the chosen cadence. Preserve SPEC's 10 warmups/30 seeded
repetitions for measurements. A timeout is data, not permission to widen bounds
after observing results. Any revised bounds require a new exact plan/ACKs.
43/50 S0 counts are **not accepted as complete**: five promised immutable wiring
getter checks are absent from that total (README review R1). Timing is unmeasured.

## Owner tasks after the design and interface gates

Each task begins with failing controls, then the smallest owned implementation,
then its focused tests/full module regressions. Publish exact READY manifests.
No task below is checked off or authorized by this draft.

1. **Agent1 ledger/export:** modify src/types/ProtocolTypes.sol and
   src/{TMSC,PSC,KSSC,ACSC}.sol, with deployment plumbing as enumerated in
   design 2.2; create src/Governance.sol and its tests;
   reuse src/lib/SigLib.sol's verifier. Test q3 valid, q2/duplicate/unknown/
   unsorted/wrong action/wrong domain/expired nonce, failed governance transaction
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
   Resolve WAL/recovery controls in R2 before implementation. Full store locks
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

## Gates and unresolved exact amendments

First resolve review R1 startup counts/schedule and R2 WAL/logical-state refusal
controls; R3 initialization lock/file ordering needs consistent wording. Obtain
both owners' ACKs of this plan, the revised matrix/CSV and resolved numeric/source
choices. Then publish the full candidate v2 schema and vectors for exact mapping
ACKs **before any module consumes them**. Final F0 freeze records all those
hashes; fresh source READY/execution ACKs are a later gate, not transferred from
design approval. Current scoped A1-0097 and A1-0091 ACKs transfer to neither stage.

Self-review: each owner obligation maps to tasks 1-5; new wire/ABI/dependency
rules precede consumption; the main risks (WAL, cold restart, all-digest expiry,
invalid-first reply, constructor/storage limits) each has a control above.
Missing implementation/runtime/timing/TLC evidence remains NOT_RUN. Historical
qualified E is retained; F gate NOT_RUN and G locked.
