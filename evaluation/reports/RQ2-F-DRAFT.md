# RQ2 / F — DRAFT report (agent 3, 2026-11-14)

**Status: DRAFT. Gate F NOT RUN. G locked.** All 32 planned F cases are NOT_RUN. A fail-closed
runner preflight now checks draft pins, matrix coverage and a source bracket (stages 1–2 only); it
does not execute cases. The fault oracle exists and has synthetic tests, but it is not connected
to captured signing-time observations. No execution FREEZE or three ACKs exist. This draft reports
prior local measurements on synthetic fixtures, the finite model, review record and the new
preflight result.
Paper-derived reconstruction of HMBC2020, not the authors' implementation. All reviews are
same-model (correlated). Evidence directories are cited per claim.

## 1. Question and design
RQ2: can the single key-worker/witness trust point of E be replaced by q-of-n witnesses
(n=4, q=3, f=1 Byzantine) without losing the E properties? Mechanism: three signed paths
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
independent enumeration matches the state counts.

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
Mistakes of my own kept in the record: a model deadlock
(first TLC f=0 run), a parser artifact that reported a false 52,339 B TMSC size.

## 3. Trust matrix (what still requires trust)
| component | status |
|---|---|
| >= 3 of 4 witnesses honest and not sharing a source-view failure | required (f=1 bound) |
| governance quorum | required. A compromised quorum (>= 3 witnesses) can add an authority it controls, remove an honest authority permanently (tombstoned, never re-addable), replace an authority's CA admins, and sign arbitrary checkpoints and decisions. It cannot change the witness set: that is fixed at deployment (constructors only; A1-0126). CORRECTED from an earlier draft row that said the quorum could change the sets |
| key custody | TEST-ONLY synthetic keys; custody not evaluated |
| single local Anvil pair as the chain | assumed correct; consensus not evaluated |
| durable witness store | SIGKILL-tested only; no power-loss claim |
| the authors of code and reviews | same model family; reviews are correlated |
Failures outside f=1: two Byzantine witnesses can break agreement (TLC f=2, sweep f=2); two
unavailable witnesses stop certificates (availability, not safety). What conflicting f=2
certificates do on the ledger (agent 1's scratch test, reproduced by me, hash 5c0f3fb6.., 4/4
pass): two checkpoints for one sequence cannot both install (second STALE_STATE); two ALLOW
certificates for one request cannot both grant (second REPLAY). A DENY/ALLOW pair for one request
is accepted in either order, because a denial consumes no nonce (an E0 reconstruction choice), so
both outcomes are logged. Tested reconstruction results outside the fault bound.

Oracle note (answered from source, not yet tested): agent 2's SIGNING-RULES section 1 pins an
AccessDecision by `requestDigest` alone, and section 6 lets an honest witness sign a different
result for the same request once every earlier digest under it is dead: expired, overtaken by a
newer checkpoint sequence, or (for ALLOW) a grant already exists. So at f <= 1 a DENY after a
consumed ALLOW (same checkpoint sequence), or an ALLOW after a DENY whose sequence was overtaken,
is reachable. "One request has both a DENY and an ALLOW logged" is therefore NOT an agreement
violation by itself, and neither is keying on (requestDigest, stateSequence). The agreement oracle
must apply the pin-death rule in time order: two certificates for one request with different
effects conflict only if the earlier one was still live (not expired, sequence not overtaken, no
grant for an ALLOW) at the time the second was signed. Needs signing-time observations the E/F
captures do not all carry; an oracle limit to state, not a finding. Agent 2 may correct this reading.

## 4. Not done / not claimed
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
