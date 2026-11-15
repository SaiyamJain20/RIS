# RQ2 / F — DRAFT report (agent 3, 2026-11-15)

**Status: DRAFT. Gate F NOT RUN. G locked.** All 32 planned F cases are NOT_RUN. A fail-closed
runner preflight now checks draft pins, matrix coverage and a source bracket (stages 1–2 only); it
does not execute cases. A new offline helper joins captured witness JSON-line signature replies
to verified history generations and store-reported signing observations using synthetic fixtures.
It is not integrated into the F runner, and no real service transcript or native capture was joined.
No execution FREEZE or exact role-scope ACKs exist. This draft reports
prior local measurements on synthetic fixtures, the finite model, review record and the new
preflight result.
Paper-derived reconstruction of HMBC2020, not the authors' implementation. All reviews are
same-model (correlated). Evidence directories are cited per claim.

This revision is prepared for scoped technical review as a **partial evidence report**. It does
not answer the complete RQ2-F question, establish that E's guarantees survive in the integrated
F system, or satisfy Gate F. A separate packet receipt pins this report revision and lists the
review questions and pending dependencies: [partial-report packet](../evidence/f/partial-report-packet-20261115/README.md).

**Partial answer as of 2026-11-15:** q=3 of n=4 has the required honest overlap when f<=1,
and the fixed-slot model and isolated tests support that mechanism. Prior local measurements
show progress with one unavailable witness and timeout with two. They do not yet establish
preservation of E's guarantees in the planned F system: the 32-case integration and E regression
remain unrun. F is an application-level extension of the paper-derived reconstruction; these
results are not findings about the HMBC authors' implementation.

**Results-first continuation (2026-11-15):** evaluation is already underway alongside runner
work. This continuation freshly reproduced the 180-case oracle/store differential against the
currently adopted protocol source: 180/180 decisions agree (142 accepts, 38 refusals; zero
disagreements). The exact run is in
[the 2026-11-15 receipt](../evidence/f/oracle-store-diff-20261115/README.md). This is an
offline tested reconstruction result, not an F case.

The next evaluation slice reran all seven deliberate oracle mutations against the same
180-case grid and accepted protocol subtree. Every mutation disagreed with the unchanged
store and reproduced its prior count (20, 18, 6, 4, 4, 4, 4); the baseline remained 180/180.
This shows sensitivity to those seven specific rule errors, not oracle completeness. The
command, implementation, baseline and result are retained in
[the mutation-discrimination receipt](../evidence/f/oracle-mutant-discrimination-20261115/README.md).

The third slice reran the M5 pool sweep against its exact historical protocol snapshot
`55f180e` (tree `4822552d..`). The new JSON is byte-identical to the prior result: f=1
has 180/972 valid certificates, no invalid certificates or potential agreement hazards;
the deliberately out-of-bound f=2 control has 330/4,374 certificates and 2,916
potential hazard cases, with no invalid certificates. The f=2 hazards are potential
post-run quorum conflicts in the model, not realized conflicting certificates. Honest
witnesses are modeled, not backed by the durable store. See
[the exact-source reproduction](../evidence/f/pool-sweep-20261115/README.md).

Agent 1 subsequently published its ledger-scope plan checker at
`origin/agent-1` commit `248e4e2`. Its receipt reports 28/28 plan checks and 9/9
negative controls caught for items 1–4 of the ledger review checklist. It also
corrects the earlier 27/27 claim: that run's dev-key scan used a missing directory
and was vacuous. The new result is peer-reported and reviewed here, not rerun by
Agent 3, not an execution ACK; item 5 still depends on runner calls. Preserve this
correction in any presentation.

The working target is a reviewable partial results packet by 2026-11-17, with evaluation in every
slice rather than a runner-first sequence. Each slice should reproduce or adversarially inspect at
least one already-implemented claim, recording exact source pins, positive/negative controls,
command and output hashes; implementation is added only where that evaluation identifies a
specific evidence gap. The intended order was:
(1) fresh oracle/store differential (done); (2) seven oracle-mutant discrimination controls (done);
(3) f=1/f=2 pool sweep and out-of-bound control (done); (4) TLC audit/recheck done; (5) reconcile the existing M1 gas rows with
Agent 1's exact reproductions (done); (6) review the M2 virtual-time and M6 real-process receipts without
starting services (done; none were started); (7) evaluate signing-event join positive and negative controls (done); (8) test the
offline runner's capture receipt/duplicate-plan and fail-closed behavior (done); (9) assemble a claim-to-
artifact table with unresolved evidence gaps (done below); (10) issue the reviewable partial packet and record
peer-review/ACK dependencies (packet prepared; no external review request sent). The packet is
ready for scoped review, but no peer has reviewed the current report hash. Before the target date,
continue offline report or runner/oracle work only when it closes a specific evidence gap, and keep
the peer-review dependency explicit. This sequence is a work target, not a promise that a result
will pass; failures and blocked items stay visible. No service or integrated F case may start before
the exact authorized FREEZE and role ACKs. Gate F remains NOT_RUN and this plan remains DRAFT.

The fifth slice reconciled the retained M1 tables against Agent 1's addressed
messages A1-0123/0124/0125. A1-0136 then attached a fresh four-command rerun,
raw logs and checksums at its exact `origin/agent-1` ref. It corrects the M1
count from 9/9 to 6/6. Agent 3 has now verified all 12 attachment checksums, compared the 21
emitted gas/calldata rows with the peer TSV and retained original logs, and checked all seven
product runtime sizes. Those 21 rows contain 15 distinct measurements because M1b repeats six M1
rows. Agent 3 did not rerun Forge; this remains correlated peer evidence. See the
[attachment audit](../evidence/f/gas-attachment-audit-20261115/README.md). The
receipt preserves the refuted cold-storage explanation and distinguishes
source-consistent cost attribution from measured gas splits. Details and hashes are in
[the gas reconciliation receipt](../evidence/f/gas-peer-reconciliation-20261115/README.md).

The sixth slice reviewed M2's retained aggregate JSON and sweep source, plus the
M6 pinned process-test source. M2 summarizes 80 muted-subset trials using a
virtual transport; its source explicitly excludes real processes, clocks,
networks and ledgers. M6 source contains four local process/KSSC test cases and
states limits for host separation, power loss, consensus, startup readiness,
other message kinds and load. The existing report records three runs with 4/4
passed each, but their exact invocation and raw output files are not in this
checkout. Those are prior reported runs, not rerun or independently auditable
here. See [the M2/M6 receipt review](../evidence/f/availability-receipt-review-20261115/README.md).

Agent 2 has now reported a fresh full `protocol/tests` run against the accepted protocol subtree
`7566f63d693afe8fa88ab7cc69872082d58d88db`, published on `origin/agent-2` at
`81498f98aac497768b0dec35cea89ddf7466e697`: 3,226 passed, 201 skipped, exit 0, in 1,195.50
seconds. The owner reports Python 3.13 and hash-verified Foundry 1.8.5; the skipped tests were
200 `ScenarioResult` and one `FileHash`, with no Foundry skip. The exact command is recorded in
Agent 2's current HANDOFF, but raw run output and a separately hashed run receipt are not retained
here. Treat this as peer-reported protocol-suite evidence, not an Agent-3 rerun, integrated F
result, or Gate F evidence. The full suite tests the protocol package against its published
fixtures and local Anvil setup; it does not establish the planned 32-case F system behavior.

The eighth slice directly tested duplicate planned case IDs in the offline F
preflight and reran its capture/join controls. A duplicate `FL-1` is reported as
coverage `MISMATCH`; no services start and all 32 rows remain `NOT_RUN`. The same
37-test focused run checks caller-count mismatch, post-seal digest mutation,
sequential JSON-RPC ID reuse, and duplicate JSON object keys. Output and source
hashes are in [the runner/capture control receipt](../evidence/f/runner-capture-controls-20261115/README.md).
These controls validate only local checker behavior. Caller-supplied counts and
hashes do not authenticate the source or establish a complete transcript; F stages
3–7 and every integrated case remain unimplemented/unrun.

A later offline M2 follow-up reran the 80 virtual-transport trials on the exact historical
protocol subtree and compared every retained outcome, virtual-time and signature-count field plus
the delayed-reply control. All fields matched. A subsequent bounded follow-up added one output row
per trial, reproduced the same aggregate fields against that receipt, and checked that the 80 rows
agree with their 16 subset aggregates. This improves auditability but remains output from the same
runner; it does not change the result's virtual-only scope or make it an F case. See the
[exact-source reproduction](../evidence/f/availability-reproduction-20261115/README.md) and
[per-trial record receipt](../evidence/f/availability-trial-records-20261115/README.md).

## 1. Question and design
RQ2: which E guarantees survive Byzantine operators with q-of-n application witnesses
(n=4, q=3, f=1), assuming safe ledgers and a trusted key worker? The witness layer distributes
decision approval; it does not remove the key-worker trust assumption. Mechanism: three signed paths
(checkpoint at KSSC, access decision at ACSC, grant receipt at PSC) carry at least q = 3 of the 4 member signatures in strictly increasing signer order (4 of 4 is
accepted); governance (add/remove authority, set CA admins) needs a witness
quorum with nonce and expiry; honest witnesses persist a single-signing record durably.
Components: ledger role (`85c59f5`), protocol role (accepted S2-0025 subtree
`7566f63d693afe8fa88ab7cc69872082d58d88db`, now published at `origin/agent-2`
commit `73fb2ce`) and evaluation role. The protocol subtree was unchanged from its
earlier `37ca31c` publication on `origin/agent-1`. Earlier measurements below
retain their original protocol pins (`55f180e` unless their evidence states
otherwise); they have not been rerun on the resynced owner branch.

## 2. Results (all local, synthetic)
### 2.1 Safety — finite model (TLC 2.19; `evidence/f/decision-quorum-tlc-20261113/`)
| config | result |
|---|---|
| 4 witnesses, f=1, q=3, persistent single-signing | Agreement holds (433 generated / 108 distinct states, complete) |
| f=0, q=3 | holds (217 / 81) |
| f=1, weak threshold q=2 | Agreement violated |
| f=2, q=3 | Agreement violated (conditional on two Byzantine witnesses, outside f=1) |
| f=0, honest witnesses may double-sign | Agreement violated |
Two q=3 sets of 4 overlap in >= 2 witnesses, so with f=1 they share an honest one. Bounded
exploration of one decision slot; not a proof of consensus or of the implementation. Agent 1's
separate enumeration matches the completed state counts (correlated review). The model pins
one effect permanently within that slot; it does not model expiry, checkpoint advances or the
runtime's generations of superseded pins. Its Agreement result cannot establish agreement
across those runtime transitions. A fresh five-config rerun on 2026-11-15 matched
all prior verdicts and counts; the complete commands, exits, stdout and full
SHA-256 source/output hashes are in evidence/f/tlc-audit-20261115/. The prior
model-hashes.txt retained only 16 hex characters per digest; the audit receipt
records full hashes. This improves provenance and found no discrepancy.

### 2.2 Safety — pool state machine with real signatures (`measurements-20261114/`, M5)
f=1: 972 cases (4 positions x 9 Byzantine behaviours x 27 honest pin patterns): 180 certificates,
all with 3 distinct valid sorted signers; 0 agreement-hazard cases. f=2 control: 4,374 cases,
2,916 agreement-hazard cases (potential double certificates). Honest witnesses there are agent
2's model of the signing rule, not the durable store.

### 2.3 Availability (M2 virtual time; M6 real processes)
Agent 3 freshly reran M2 on the exact historical protocol snapshot (`55f180e`, subtree
`4822552d..`) for all 16 muted-witness subsets, five times each. The 80-trial outcome fields and
delayed-reply ordering match the retained aggregate; raw stdout and aggregate JSON are in
[the exact-source reproduction receipt](../evidence/f/availability-reproduction-20261115/README.md).
Agent 3 then extended the owned offline runner to retain one record per trial and reproduced those
aggregate fields; all 80 records agree with the 16 subset aggregates. These are virtual-transport
results, not network timing, and per-trial records from the same runner are not independent
observations. Zero or one muted witness gives a 3-signature
certificate every run; 2, 3 or 4 muted witnesses give none by the 10 s deadline. With real
processes, a local Anvil pair and the real KSSC (agent 2's live tests, three runs, exit 0): q=3
certificate accepted in ~0.7 s, one SIGKILLed witness still accepted (~0.6 s), two stopped
witnesses give a classified timeout of ~10.5 s, a restarted witness keeps its durable pin.
No claim about arbitrary-delay liveness: unavailability under two faults is expected and measured.

### 2.4 Cost (M1/M1b/M1c; reproduced exactly by agent 1, A1-0123/0124/0125)
Same code, REPAIRED_E (1 signature) vs REPAIRED_F, Forge gas of one external call:
| call | 1 sig | 3 sigs | 4 sigs |
|---|---|---|---|
| KSSC.acceptState | 208,290 | 231,260 (+11.0%) | 238,046 |
| ACSC.consumeDecision | 324,323 | 342,261 (+5.5%) | 349,053 |
| PSC.reportAttestedOutcome | 533,754 | 553,488 (+3.7%) | 560,290 |
Calldata grows 548->868, 1,380->1,700, 644->964 bytes (160 B per extra signature, ~6.8k gas each).
Governance.execute (F only, 3 sigs): AddAuthority 524,214; RemoveAuthority 424,421; SetCaAdmins 446,934.
All product contracts stay under 24,576 B. TMSC grew from 12,635 B in the E-era
2026-10-08 deployment manifest to 16,127 B at ledger commit `85c59f5`. Not a fee estimate; single
deterministic runs; the E column is the F commit's E profile.

### 2.5 Assurance process
The kill-durability review found and drove fixes for: a hot-journal store refused after a kill in
init (fixed), a snapshot-lock defect (fixed), the evaluator anchor-selection defect (fixed on my
side). The earlier candidate's signing-kill mutant K1 was detected only probabilistically.
A3-0122 measured 29/40 detections (72.5%) with the control passing 40/40; agent 2's 3/3
report was not reproduced in that measurement. S2-0025 and the later reproduction provide stronger
candidate test evidence, but current coordination still records **K1 OPEN** pending explicit owner
confirmation. Do not treat the 40/40 result as closure or as an execution ACK.
Proxy note S2-0024, published on agent-1 at `73fec05`, supplies a source review and corrects one
consequence of my A3-0121 reading (below). It explicitly disclaims knowledge of agent 2's intent;
the **A3-0121 signing-rule confirmation remains OPEN** under the current coordination record.
The note is review evidence, not that confirmation or an execution ACK. A later refresh to agent-1
`f25eae1` found S2-0025's proxy delta READY at `37ca31c` (protocol subtree
`7566f63d693afe8fa88ab7cc69872082d58d88db`): its between-statement blocking hooks reproduced on
agent 3's host: **40/40 K1 detections, 40/40 control passes**, with no trial crash, and 81 state
tests passed. This demonstrates sensitivity of the candidate tests at isolated scope; the old
candidate still has its measured 29/40 limit. These are fault-injection tests with a synthetic
placeholder signer, not evidence of a production corruption rate or power-loss durability. See the
[exact-source review and command receipts](../evidence/reviews/proxy-k1-20261114/README.md). The human explicitly
authorized Claude proxy-2 for protocol-source approval and exact protocol FREEZE ACKs,
then clarified that all agent names are portable work roles (D57). The draft now adopts
this candidate from its actual publication ref, `origin/agent-1`, with an exact module-tree
pin. Agent 2 later resynced the same subtree to `origin/agent-2`/`73fb2ce` and independently
re-verified K1 (15/15 mutant trials, 10/10 controls) plus 81 state tests. The execution draft
now points to the active protocol owner. No original-session countersignature or duplicate
branch push is needed. S2-0026 is a plan review, not an execution ACK; the required exact
FREEZE ACKs remain absent. See A2-0087 and the [updated source pin receipt](../evidence/f/execution-plan-draft-20261114/README.md).
Mistakes of my own kept in the record: a model deadlock
(first TLC f=0 run), a parser artifact that reported a false 52,339 B TMSC size.

### 2.6 Captured signing-reply/history join (synthetic)

The new `evaluation.signing_event_join_v2` helper consumes the published
`hmbc-witness-rpc/v1` request/response lines and a separately verified
`WitnessEvidence` export. For each captured signature reply it verifies the
signature under the caller-pinned witness/deployment context, derives the typed
digest, then requires an exact history match on digest, signature, type, domain,
witness-set version, key and effect. It returns the matching store-reported
observation and superseded-generation sequence. Sixteen focused synthetic tests
cover all four signing kinds, live and superseded generations, idempotent re-signs, refusal replies,
message/ID mismatches, duplicate JSON keys, invalid signatures and tampered
history. Evidence and commands: [signing-event join](../evidence/f/signing-event-join-20261114/README.md).

The offline runner now wraps that join with `sealed_signing_capture_v1`.
Its caller-supplied receipt records a separate event count and SHA-256 of the
canonical capture; validation rejects count mismatches, edits after sealing and
preserves the source-reported count and relies on the existing join for contiguous
event-sequence and reply-ID matching. Five synthetic tests cover count mismatch,
post-seal edit, Unicode encoding, sequential RPC ID reuse and a successful join.
A Unicode hashing negative control found and fixed an encoding mismatch; the final
focused suite passes 5/5 and the evaluation suite passes 3,003 tests. The source-ref
preflight suite passes 15/15 and still reports BLOCKED. Commands, output, exit
codes, fixture/source hashes and limits:
[sealed-capture evidence](../evidence/f/sealed-signing-capture-20261115/README.md).

An additional offline review found that Python treated JSON `1.0` as equal to
integer round `1`; the helper already rejected booleans but did not enforce an
integer JSON type. A synthetic regression test failed before the change and
passed after the helper required an exact integer type. The focused join suite
now passes 16/16 and the full evaluation suite passes 3,004 tests. This tightens
the capture checker only; it is not evidence that a live protocol endpoint
accepts or rejects fractional rounds. Command/result details and source hashes:
[round validation receipt](../evidence/f/signing-event-round-validation-20261115/README.md).

Classification: tested reconstruction result over synthetic records and generated
JSON-lines, not a live-process measurement or F case. A valid signature binds the
message to the configured test owner, but does not authenticate the capture
transcript or show that it is complete. The export's observation remains a
store-reported value. Native fact checks still require the separate raw block/call
checker; neither path proves SQLite/export completeness, persistence, or wall-clock
signing time. The helper also does not prove that an honest service validated the
proposal before returning the signature. The receipt's count is useful against
truncation only when it comes from an independent source, and the receipt itself
is not authenticated; runner capture acquisition and end-to-end controls remain
unimplemented.

## 3. Trust matrix (what still requires trust)
| component | status |
|---|---|
| >= 3 of 4 witnesses honest and not sharing a source-view failure | required (f=1 bound) |
| governance quorum | required. A compromised quorum (>= 3 witnesses; outside the f=1 bound) can add an authority it controls, remove an honest authority permanently (tombstoned, never re-addable), replace an authority's CA admins, and obtain ledger-accepted checkpoints and decisions subject to the on-chain checks. It can permanently halt this DBC deployment by installing a quorum-signed checkpoint with `sequence = uint64.max`: later honest checkpoints are STALE_STATE, and after expiry decisions are too; no ledger function resets the checkpoint (redeployment required; A1-0117, A3-0095, A1-0137 scratch reproduction). Saturating `authEpoch` or `sourceBlockNumber` also permanently halts honest operation: honest checkpoints carry the PBC's real, lower values and are rejected as STALE_STATE, while only checkpoints repeating the saturated value pass. Honest witnesses do not sign those repeats. A saturated `authEpoch` makes honest requests STALE_STATE immediately; a saturated `sourceBlockNumber` makes decisions STALE_STATE after the poisoned checkpoint expires (A1-0117; A1-0138 scratch reproduction, 3/3). It can obtain a grant for a requester never submitted on the PBC using fabricated credential records that fit the policy's role/kind/issuer shape: the DBC rechecks that shape but binds records only through the quorum-signed digest (A1-0137 scratch reproduction). These outcomes require a compromised quorum and do not contradict the f<=1 claims. It cannot change the witness set, fixed at deployment (constructors only; A1-0126); under REPAIRED_F, policyVersion is pinned to ACSC and keyEpoch must be 0. CORRECTED from an earlier draft row that said the quorum could change the sets |
| key custody | TEST-ONLY synthetic keys; custody not evaluated |
| single local Anvil pair as the chain | assumed correct; consensus not evaluated |
| relay / collector | no signing key; witnesses must derive and validate values independently. Withholding and adverse scheduling can prevent progress; eventual delivery remains a condition |
| credential authority | trusted for credentials it issues; quorum approval does not make a credential truthful or require several issuers for one role. Authority compromise remains a residual, not witness compromise |
| key worker / host | trusted to enforce release and retain secrets. Witness certificates do not prevent a compromised worker from using its own key material; the planned F-19 demonstration remains NOT_RUN |
| client and data store | request identity/bindings are enforced only under the selected profile and assumptions. Client retention, learned plaintext, data-store availability and actual cryptographic confidentiality are not established by F |
| witness processes | separate stores/keys/processes on one host; no independence from shared OS, operator or RPC failure is established |
| durable witness store | SIGKILL-tested only; no power-loss claim |
| the authors of code and reviews | same model family; reviews are correlated |
Failures outside f=1: two Byzantine witnesses can break agreement (TLC f=2, sweep f=2); two
unavailable witnesses stop certificates (availability, not safety). What conflicting f=2
certificates do on the ledger (agent 1's scratch test, reproduced by me, hash 5c0f3fb6.., 4/4
pass): two checkpoints for one sequence cannot both install (second STALE_STATE); two ALLOW
certificates for one request cannot both grant (second REPLAY). A DENY/ALLOW pair for one request
is accepted in either order, because a denial consumes no nonce (an E0 reconstruction choice), so
both outcomes are logged. Tested reconstruction results outside the fault bound.

Oracle correction (A3-0129; S2-0024 reviewed): the AccessDecision key includes type, domain,
witness-set version and `requestDigest`; `stateSequence` is part of its effect. The accepted
F0 rule is at most one **live effect** per key, with observed death permitting a new generation.
The store supports expiry, a strictly greater checkpoint sequence, and an ALLOW-only
caller-asserted grant death. However, the honest service validates before calling that store:
a consumed nonce or recorded outcome gives `REPLAY`. It passes sequence death only, never
grant death. My earlier claim that a fresh honest DENY can follow a consumed ALLOW at the same
sequence was wrong. The 180-case store differential tests a store capability, not its reachability
through the service or ledger.

Fresh offline review at exact protocol `9d44754` (protocol tree identical to candidate `55f180e`)
checks four synthetic service/store traces using the owner's injected ledger view: a post-grant
DENY gives `REPLAY` without changing the store; a changed result at one live sequence gives
`CONFLICT_PINNED`; ALLOW->DENY and DENY->ALLOW after sequence advance both sign and record
sequence death when no nonce is consumed. These are tested reconstruction results on an injected
view, not native ledger reachability or F case results. See
[the correction evidence](../evidence/f/report-review-20261114/README.md).

Counting both DENY and ALLOW logs, or using `(requestDigest, stateSequence)` alone, is therefore
insufficient to diagnose a signing violation. The oracle needs time-ordered signing observations,
all live digests in the relevant generation, and service-validation facts. The new helper joins a
captured reply to one exact declared history digest and observation, but the runner does not yet
acquire or authenticate complete process transcripts. The store-level grant allowance may still
miss a service-validation violation. Ledger submission of an already issued
certificate is a different event from fresh witness signing; `REPLAY` at signing does not
establish rejection of every previously signed DENY by the ledger. Missing detail and differences
between SPEC's shorthand and accepted F0 rules are ambiguities of this reconstruction, not HMBC
vulnerabilities.

## 4. Claim-to-evidence map for partial review

These are prior measurements unless marked fresh. No row is an integrated F result.

| claim / classification | evidence | practical limit |
|---|---|---|
| Fixed-slot quorum agreement; extension result in a finite model | [TLC logs, counts, controls and model hashes](../evidence/f/decision-quorum-tlc-20261113/README.md) | no runtime pin deaths, ledger consensus or liveness proof |
| Five-configuration finite-model rerun; tested reconstruction result | [2026-11-15 exact-source audit, full log/source hashes and stop-count interpretation](../evidence/f/tlc-audit-20261115/README.md) | reproduces a bounded one-slot model; not a runtime, consensus or liveness proof |
| Pool certificate filtering and potential agreement hazards; tested reconstruction result | [M3/M5](../evidence/f/measurements-20261114/README.md), [exact-source M5 rerun](../evidence/f/pool-sweep-20261115/README.md) | M5 honest behaviour is a model; f=2 hazards are potential states, not realized double certificates |
| One/two unavailable witness boundary; fresh virtual-sweep reproduction plus prior reported local process runs | [M2/M6 measurements](../evidence/f/measurements-20261114/README.md), [fresh M2 exact-source reproduction](../evidence/f/availability-reproduction-20261115/README.md), [M2 per-trial follow-up](../evidence/f/availability-trial-records-20261115/README.md), [M6 source and receipt review](../evidence/f/availability-receipt-review-20261115/README.md) | M2 now retains one record per virtual trial, but records come from the same runner; M6 run stdout and exact invocation are not retained; no real-network latency or general liveness estimate |
| Signature and governance gas overhead; tested reconstruction result with peer reproduction reported | [M1/M1b/M1c measurements](../evidence/f/measurements-20261114/README.md), [A1-0136 reconciliation](../evidence/f/gas-peer-reconciliation-20261115/README.md), [attachment and retained-log audit](../evidence/f/gas-attachment-audit-20261115/README.md) | all 12 attachment hashes, 21 emitted rows (15 distinct) and seven sizes match retained artifacts; no fresh Agent-3 Forge run; single deterministic fixtures, no production fee or throughput estimate |
| K1 sensitivity; deliberate mutation result | [A3-0122 signing-kill review](../evidence/reviews/a2-0086-signing-kill-20261113/README.md) | 29/40 detections and 40/40 control; does not measure corruption probability |
| New K1 candidate; deliberate mutation result | [S2-0025 reproduced by agent 3](../evidence/reviews/proxy-k1-20261114/README.md) | 40/40 detections and 40/40 controls; K1 owner confirmation remains OPEN, and this is not an execution ACK |
| Store death predicates; tested reconstruction result | [180-case differential and seven oracle mutations](../evidence/f/oracle-store-diff-20261114/README.md) | one earlier digest per key; grant/receipt facts caller-asserted; A3-0121 signing-rule confirmation remains OPEN |
| Compromised quorum can permanently halt one DBC deployment and obtain a grant from fabricated, policy-shaped records for an unsubmitted PBC requester; ledger-scope review plus peer-reported scratch reproduction, outside f=1 | [A1-0137 review and Agent-3 response](../evidence/f/report-review-a1-0137-20261115/README.md) | requires >=3 Byzantine witnesses; Agent 3 verified attachment checksums but did not rerun Forge; grant does not show key-worker release |
| Saturating `authEpoch`, `sourceBlockNumber`, or `sequence` can permanently halt honest operation of the DBC deployment; ledger-scope review plus peer-reported scratch reproduction, outside f=1 | [A1-0138 follow-up review and Agent-3 response](../evidence/f/report-review-a1-0137-20261115/README.md) | authEpoch stops decisions immediately; sourceBlockNumber stops them after checkpoint expiry; sequence stops them after checkpoint expiry; Agent 3 verified attachment checksums but did not rerun Forge |
| Fresh oracle/store differential; tested reconstruction result | [2026-11-15 exact-source rerun](../evidence/f/oracle-store-diff-20261115/README.md) | one earlier digest per key; grant/receipt facts caller-asserted |
| Protocol test suite; peer-reported tested reconstruction result | Agent 2's current [HANDOFF](../../communication/agent-2/HANDOFF.md) records 3,226 passed, 201 skipped, exit 0 against protocol subtree `7566f63d..` on `origin/agent-2` `81498f9`; command, toolchain verification and skip classification are stated there | owner-reported run; raw stdout and a run-specific hash receipt are not retained here; protocol package suite, not the planned integrated F system or an F case |
| Seven oracle mutation sensitivities; deliberate mutation result | [2026-11-15 mutation rerun](../evidence/f/oracle-mutant-discrimination-20261115/README.md) | these seven specific rule errors only; same synthetic grid and correlated oracle/store |
| Service/store distinction; fresh tested reconstruction result | [four probes, selected owner tests, exact source/output hashes](../evidence/f/report-review-20261114/README.md) | injected view and synthetic keys; no native grant/sequence transition |
| Captured signer reply to exact store-history generation; tested reconstruction result | [16 focused join tests](../evidence/f/signing-event-round-validation-20261115/README.md); [source/command record](../evidence/f/signing-event-join-20261114/README.md) | generated JSON-lines; capture authenticity/completeness, native facts and honest-service validation remain unproved |
| JSON round requires exact integer type; tested reconstruction regression | [pre-fix RED and focused/full-suite results](../evidence/f/signing-event-round-validation-20261115/README.md) | validates the offline helper only; says nothing about a live endpoint's parsing behavior |
| Offline capture receipt checks; tested reconstruction result | [count, digest and sequential RPC-ID reuse controls plus evaluation run](../evidence/f/sealed-signing-capture-20261115/README.md) | caller-supplied count/receipt; no source authentication, acquisition, or transcript completeness claim |
| Duplicate planned IDs fail closed; tested reconstruction result | [duplicate-ID, count/digest, JSON-key and RPC-ID controls](../evidence/f/runner-capture-controls-20261115/README.md) | preflight only; stages 3–7 and all case execution remain absent |
| Active protocol source pin and draft preflight; provenance check only | [A2-0087 byte-identical source resync](../evidence/f/source-pin-resync-20261115/README.md) | exact module subtree and ancestry verified; source-role handoff is not an execution ACK |
| Draft coverage and source pins; preflight check only | [A3-0128 final preflight](../evidence/f/preflight-20261114-r4/README.md) | 32/32 IDs is coverage of the plan; all case statuses remain NOT_RUN |
| Execution authorization state; blocked, not an F result | [current draft plan and blocked preflight](../evidence/f/execution-plan-draft-20261114/README.md), [current board](../../communication/BOARD.md) | plan remains DRAFT; exact authorized FREEZE and required owner ACKs absent; Gate F NOT_RUN; no services or integrated cases |

## 5. Not done / not claimed
Gate F, the 32 F cases, execution FREEZE and ACKs, runner stages 3–7, runner
acquisition and authentication/completeness controls for signer transcripts, E
regression reruns against the F system, certificate/latency
over a real network, power-loss durability, Besu/QBFT consensus, ABE, and any G (key lifecycle)
work remain undone. The 2026-11-14 preflight matched all 32 planned IDs against the frozen
revision-8 matrix, but exited 2 with `BLOCKED`; no case ran. The earlier first preflight used the
wrong matrix path and is retained as invalidated evidence. See
`evaluation/evidence/f/preflight-20261114-r4/README.md`. A1-0129's ledger-scope review was
incorporated into the DRAFT. Full evaluator suite: 2,978 passed; focused runner tests: 14 passed;
all exact draft pins match. A deliberate same-row-count matrix-ID drift is also blocked. These
checks do not lift the actual role-scope execution ACK or later-stage blockers. Deviation from the plan
sequence: earlier measurements were taken before the runner/FREEZE on the human's instruction.

Before the 2026-11-17 partial-report target, the partial packet is prepared and records its review
questions and execution blockers; no external review request has been sent. Continue offline
report, runner, or oracle work only when it closes a specific evidence gap. The existing capture
checks do not authenticate acquisition or establish transcript completeness; those controls can
be added only if an independent source is available. The execution plan remains DRAFT. The new K1 candidate's test evidence and source pin are
recorded in the DRAFT under D57, while K1 owner confirmation and the A3-0121 signing-rule
confirmation remain OPEN. Both exact execution FREEZE ACKs and the unfinished runner stages also
remain open; S2-0024 and A1-0129 are not execution ACKs. Run services/cases only after the
authorized FREEZE requirements are met. A reviewable
partial report can document those blockers; it cannot substitute prior measurements for the
32 missing case results or close Gate F.

For this report revision, review status is separate from execution authorization. A1-0137 and
A1-0138 reviewed earlier hashes for ledger scope; their findings were incorporated. A1-0139
confirmed the exact `cf249e2a...` report hash had no remaining ledger-scope objection. This
revision adds Agent 2's owner-reported protocol-suite result and its evidence limits; this new
file hash has not itself been reviewed. A1-0129 reviewed ledger details in the plan; it
did not review this report or ACK an execution FREEZE. S2-0026 reviewed the draft plan and A2-0088
reviewed hook coverage; neither is an execution ACK. No Agent-2 report-specific review is recorded.
See the [A1-0137/0138/0139 review receipt](../evidence/f/report-review-a1-0137-20261115/README.md)
and [partial packet receipt](../evidence/f/partial-report-packet-20261115/README.md). The execution
gate still requires exact owner ACKs and an authorized FREEZE for the exact execution plan before
any services or cases.
