# Final presentation outline — what we did since mid-submission (agent 3, 2026-11-14)

Every number below is in the cited evidence directory. Rule for the talk: say "reconstruction",
"local synthetic", "model-checked" and "peer-reproduced (same model family)"; never "proved",
"consensus", "Gate F passed" or "live network". Evidence root: `evaluation/evidence/`.

## Slide plan (about 12 slides)
1. **Question.** Can HMBC's single key-worker trust point be replaced by q-of-n witnesses without
   losing the authorization/audit properties? (RQ2/F; RQ1/E closed earlier.) Paper-derived
   reconstruction, not the authors' code.
2. **Design.** n=4, q=3, f=1. Three witness-signed paths (checkpoint, decision, receipt) carry
   at least 3 of 4 member signatures in increasing signer order; governance by quorum with nonce and
   expiry; honest witnesses persist a single-signing record. Witness set fixed at deployment.
3. **Three agents, three modules.** Ledger (contracts), protocol (witness runtime/pool), evaluation
   (oracles, model, measurements). Cross-review between agents (honest caveat: same model family).
4. **Safety, model level.** TLC: f=1,q=3 holds (108 distinct states); f=0 holds; weak q=2, f=2 and
   honest double-signing each break Agreement. `f/decision-quorum-tlc-20261113/`.
5. **Safety, real signatures.** Pool state machine: f=1: 972 Byzantine cases, 0 agreement hazards, 0
   invalid certificates; f=2 control: 2,916 of 4,374 hazard cases. `f/measurements-20261114/` (M5).
6. **Availability.** All 16 muted-witness subsets: <=1 muted gives a certificate, >=2 muted gives none
   at the 10 s deadline. Same boundary with four real OS processes and a real contract (certificate
   ~0.7 s; two stopped witnesses time out at ~10.5 s). (M2, M6)
7. **Cost.** q=3 adds +11.0% gas (checkpoint), +5.5% (decision), +3.7% (receipt) over 1 signature;
   ~6.8k gas and 160 B calldata per extra signature; governance actions 424k-524k gas. All gas
   numbers reproduced exactly by agent 1. (M1, M1b, M1c)
8. **What f=2 does on the ledger.** Conflicting checkpoints/ALLOWs cannot double-install (STALE_STATE /
   REPLAY); DENY and ALLOW for one request are both accepted (denial consumes no nonce). A1-0126.
9. **Trust matrix.** Still required: >=3 honest witnesses; the governance quorum (can add/remove
   authorities, not witnesses); key custody (test-only keys); the chain (single local Anvil pair);
   the durable store (SIGKILL-tested, no power-loss claim). `reports/RQ2-F-DRAFT.md`.
10. **Process findings (the method works).** Bugs found and fixed: store refused after kill in
   initialization; snapshot-lock defect; anchor-selection defect in our evaluator; sequence exhaustion
   at uint64 max. Review caught a non-vacuous-test gap and an unreproducible mutation claim (K1: our
   rate 29/40 vs claimed 3/3).
11. **Our own errors, kept.** Model deadlock in the first TLC run; a parser artifact reporting a false
   52,339 B contract size; a wrong trust-matrix row (corrected after peer review). Shows the evidence
   discipline: corrections are recorded, not hidden.
12. **Limits and next steps.** Gate F not run: the 32 planned F cases, fault oracle, execution
   freeze and ACKs remain; no consensus, network latency, power loss, or key-custody evaluation;
   G (key lifecycle) not started. Next: runner + fault oracle, agreement oracle keyed on the pin-death
   rule (denial-then-grant is legal at f<=1, A3-0121).

## Likely hard questions (honest answers)
- *Did Gate F pass?* No. It has not been run. We report model, sweep, gas and real-process results.
- *Are the reviews independent?* No: agents are the same model family, so reviews are correlated;
  they still reproduced numbers exactly and found real errors (trust row, size artifact).
- *Is this a proof of consensus safety?* No. TLC covers one decision slot with four witnesses; f=2 is
  explicitly outside the bound and does break agreement.
- *Why is unavailability under 2 faults acceptable?* It is the threshold design: safety needs q>n/2+f/2
  overlap; two silent witnesses cost availability, not safety. We make no liveness claim under arbitrary delay.
- *Is the gas overhead realistic?* It is Forge-EVM gas of one call on a synthetic fixture, a single deterministic
  run, not a fee estimate; the E column is the F commit's own single-signature profile.
- *Could a compromised governance quorum replace witnesses?* No (fixed at deployment); it can change
  trust-list authorities and sign arbitrary checkpoints/decisions.
- *Is the witness store durable?* Against SIGKILL, yes within tests (K1 mutant detected ~72% per run, so
  the harness is not perfect); against power loss, untested.
- *Why were measurements taken before the runner/freeze?* Human instruction to produce results for the
  deadline; recorded as a deviation from the plan sequence.
- *Where is G?* Not started by design; it unlocks after Gate F.
