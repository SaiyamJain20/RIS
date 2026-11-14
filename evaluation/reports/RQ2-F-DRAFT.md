# RQ2 / F — DRAFT report (agent 3, 2026-11-14)

**Status: DRAFT. Gate F NOT RUN. G locked.** All 32 planned F cases are NOT_RUN. A fail-closed
runner preflight now checks draft pins, matrix coverage and a source bracket (stages 1–2 only); it
does not execute cases. The fault oracle exists and has synthetic tests, but it is not connected
to captured signing-time observations. No execution FREEZE or three ACKs exist. This draft reports
prior local measurements on synthetic fixtures, the finite model, review record and the new
preflight result.
Paper-derived reconstruction of HMBC2020, not the authors' implementation. All reviews are
same-model (correlated). Evidence directories are cited per claim.

**Partial answer as of 2026-11-14:** q=3 of n=4 has the required honest overlap when f<=1,
and the fixed-slot model and isolated tests support that mechanism. Prior local measurements
show progress with one unavailable witness and timeout with two. They do not yet establish
preservation of E's guarantees in the planned F system: the 32-case integration and E regression
remain unrun. F is an application-level extension of the paper-derived reconstruction; these
results are not findings about the HMBC authors' implementation.

## 1. Question and design
RQ2: which E guarantees survive Byzantine operators with q-of-n application witnesses
(n=4, q=3, f=1), assuming safe ledgers and a trusted key worker? The witness layer distributes
decision approval; it does not remove the key-worker trust assumption. Mechanism: three signed paths
(checkpoint at KSSC, access decision at ACSC, grant receipt at PSC) carry at least q = 3 of the 4 member signatures in strictly increasing signer order (4 of 4 is
accepted); governance (add/remove authority, set CA admins) needs a witness
quorum with nonce and expiry; honest witnesses persist a single-signing record durably.
Components: ledger (agent 1, `85c59f5`), witness runtime and pool (agent 2, `55f180e`),
evaluation (agent 3).

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
across those runtime transitions.

### 2.2 Safety — pool state machine with real signatures (`measurements-20261114/`, M5)
f=1: 972 cases (4 positions x 9 Byzantine behaviours x 27 honest pin patterns): 180 certificates,
all with 3 distinct valid sorted signers; 0 agreement-hazard cases. f=2 control: 4,374 cases,
2,916 agreement-hazard cases (potential double certificates). Honest witnesses there are agent
2's model of the signing rule, not the durable store.

### 2.3 Availability (M2 virtual time; M6 real processes)
All 16 muted-witness subsets over four real witnesses (virtual transport): 0 or 1 muted gives a
3-signature certificate every run; 2, 3 or 4 muted gives none by the 10 s deadline. With real
processes, a local Anvil and the real KSSC (agent 2's live tests, three runs, exit 0): q=3
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
All product contracts stay under 24,576 B (TMSC 12,635 -> 16,127 B). Not a fee estimate; single
deterministic runs; the E column is the F commit's E profile.

### 2.5 Assurance process
The kill-durability review found and drove fixes for: a hot-journal store refused after a kill in
init (fixed), a snapshot-lock defect (fixed), the evaluator anchor-selection defect (fixed on my
side). Open: the signing-kill mutant K1 is detected only probabilistically. A3-0122 measured 29/40
detections (72.5%) with the control passing 40/40; agent 2's 3/3 report was not reproduced in that
measurement. Agent 2 has not answered A3-0110 or confirmed the A3-0121 signing-rule reading.
Proxy note S2-0024, published on agent-1 at `73fec05`, supplies a source review and corrects one
consequence of my A3-0121 reading (below). It explicitly disclaims knowledge of agent 2's intent
and is not an execution ACK. A later refresh to agent-1 `f25eae1` found S2-0025's proxy
delta READY at `37ca31c` (protocol subtree `7566f63d693afe8fa88ab7cc69872082d58d88db`):
it reports 40/40 K1 detections and 40/40 controls on that host. That delta has not been
reproduced or adopted here; the 29/40 result still describes the old candidate. S2-0026 is a
plan review, explicitly not an owner ACK. Neither proxy result closes the execution requirements.
Mistakes of my own kept in the record: a model deadlock
(first TLC f=0 run), a parser artifact that reported a false 52,339 B TMSC size.

## 3. Trust matrix (what still requires trust)
| component | status |
|---|---|
| >= 3 of 4 witnesses honest and not sharing a source-view failure | required (f=1 bound) |
| governance quorum | required. A compromised quorum (>= 3 witnesses) can add an authority it controls, remove an honest authority permanently (tombstoned, never re-addable), replace an authority's CA admins, and sign arbitrary checkpoints and decisions. It cannot change the witness set: that is fixed at deployment (constructors only; A1-0126). CORRECTED from an earlier draft row that said the quorum could change the sets |
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
insufficient to diagnose a signing violation. The oracle needs time-ordered, authenticated
signing observations, all live digests in the relevant generation, and service-validation facts.
Its current store-level grant allowance may miss a service-validation violation. No such
end-to-end capture/validation check is implemented. Ledger submission of an already issued
certificate is a different event from fresh witness signing; `REPLAY` at signing does not
establish rejection of every previously signed DENY by the ledger. Missing detail and differences
between SPEC's shorthand and accepted F0 rules are ambiguities of this reconstruction, not HMBC
vulnerabilities.

## 4. Claim-to-evidence map for partial review

These are prior measurements unless marked fresh. No row is an integrated F result.

| claim / classification | evidence | practical limit |
|---|---|---|
| Fixed-slot quorum agreement; extension result in a finite model | [TLC logs, counts, controls and model hashes](../evidence/f/decision-quorum-tlc-20261113/README.md) | no runtime pin deaths, ledger consensus or liveness proof |
| Pool certificate filtering and potential agreement hazards; tested reconstruction result | [M3/M5, raw sweeps and commands](../evidence/f/measurements-20261114/README.md) | M5 honest behaviour is a model; f=2 hazards are potential states, not realized double certificates |
| One/two unavailable witness boundary; tested reconstruction result | [M2 virtual transport and M6 prior real-process runs](../evidence/f/measurements-20261114/README.md) | M6 has three local repetitions; no real-network latency or general liveness estimate |
| Signature overhead; tested reconstruction result | [M1/M1b/M1c and peer reproductions](../evidence/f/measurements-20261114/README.md) | single deterministic fixture calls; no production fee or throughput estimate |
| K1 sensitivity; deliberate mutation result | [A3-0122 signing-kill review](../evidence/reviews/a2-0086-signing-kill-20261113/README.md) | 29/40 detections and 40/40 control; does not measure corruption probability |
| Store death predicates; tested reconstruction result | [180-case differential and seven oracle mutations](../evidence/f/oracle-store-diff-20261114/README.md) | one earlier digest per key; grant/receipt facts caller-asserted |
| Service/store distinction; fresh tested reconstruction result | [four probes, selected owner tests, exact source/output hashes](../evidence/f/report-review-20261114/README.md) | injected view and synthetic keys; no native grant/sequence transition |
| Draft coverage and source pins; preflight check only | [A3-0128 final preflight](../evidence/f/preflight-20261114-r4/README.md) | 32/32 IDs is coverage of the plan; all case statuses remain NOT_RUN |

## 5. Not done / not claimed
Gate F, the 32 F cases, execution FREEZE and ACKs, runner stages 3–7, connection of the fault
oracle to signing-time captures, E regression reruns against the F system, certificate/latency
over a real network, power-loss durability, Besu/QBFT consensus, ABE, and any G (key lifecycle)
work remain undone. The 2026-11-14 preflight matched all 32 planned IDs against the frozen
revision-8 matrix, but exited 2 with `BLOCKED`; no case ran. The earlier first preflight used the
wrong matrix path and is retained as invalidated evidence. See
`evaluation/evidence/f/preflight-20261114-r4/README.md`. A1-0129's ledger-scope review was
incorporated into the DRAFT. Full evaluator suite: 2,978 passed; focused runner tests: 14 passed;
all exact draft pins match. A deliberate same-row-count matrix-ID drift is also blocked. These
checks do not lift the owner ACK, K1/signing-rule or later-stage blockers. Deviation from the plan
sequence: earlier measurements were taken before the runner/FREEZE on the human's instruction.

Before the 2026-11-17 partial-report target, the permitted next work is to join signing-time
observations to the oracle and implement offline runner stages/controls, while reviewing any
published exact protocol delta. The execution plan remains DRAFT. K1 disposition, the required
owner confirmation and both exact execution FREEZE ACKs remain open; S2-0024 and A1-0129 do not
close them. Run services/cases only after the authorized FREEZE requirements are met. A reviewable
partial report can document those blockers; it cannot substitute prior measurements for the
32 missing case results or close Gate F.
