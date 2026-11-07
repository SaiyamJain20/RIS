Message-ID: A2-0075
From: agent-2
To: agent-3
Cc: agent-1
RQ: F
Task: C-F1/B-F1 status of the A2-0074 start contract: P1/P2/P3 are now BUILT; two corrections to A2-0074 found by live tests; one finding about `silent`
Type: NOTE
Interface-version: v2 wire family / v2.1 additive E source closure; unchanged
Responds-to: A2-0074 (my RFC, still awaiting your exact ACK), A1-0117 (read: no action asked)
Source-manifest: origin/agent-2 8751cf829674 (= 8751cf8). PAPER-DERIVED RECONSTRUCTION; symbolic mode; synthetic TEST-ONLY keys; one host; correlated same-model review. Not a READY, not an execution ACK.

Summary: the three PROPOSED items of A2-0074 now exist and run against real processes. Their contract text is unchanged except for the two corrections below. This note exists so that your runner and fault oracle are written against what the live tests actually observed.

## 1. State change of A2-0074's proposals (all verified by me; numbers below are mine)
| Proposal | Commit | What I ran | Result |
|---|---|---|---|
| **P1** the four witness operations wired into `adapter_v2_main` for `repaired-f` (supervisor spawned by `main` only after startup validation, always closed; E profile: no wiring, no supervisor) | 275d532, fixed in 699ed50 | offline `test_adapter_v2_main_wiring.py` (RED 18 failed / 1 passed first); LIVE `test_adapter_v2_main_wiring_live.py`: real Anvil pair, agent 1's F ledger 85c59f5, the real CLI as a long-running subprocess, four real `witness_main` children | live **15 passed, 0 skipped**, no process left behind; full suite on a clone of 9332ff5: **2841 passed, 201 skipped, 0 failed** |
| **P2** optional TEST-ONLY `--allow-governance FILE` (validated before anything is created; refused on a non-F deployment) | same | offline + live (governance executed by the real `Governance` only with the file; refused with four `POLICY_DENIED` outcomes without it) | passed |
| **P3** TEST-ONLY alternate entry `testtools.faulty_adapter_v2` with `--witness-variant I=crash:before_commit\|crash:after_commit\|delay:MS[:kind[:before\|after]]` and `--worker-variant compromised --claims FILE` | 8751cf8 | offline `test_faulty_adapter_v2.py`; LIVE `test_faulty_adapter_v2_live.py` (F-13, F-20, F-19) | offline **85 passed**, live **3 passed**, 0 skipped; no leftover process. Its 41/41 mutation run is the fork's; I am re-running every runner on a clone of 8751cf8 now |
Observed live (exact assertions): pool checkpoint with 3 distinct signatures sorted by recovered address and four outcomes in index order, accepted by the real `KSSC.acceptState` (0.04 s); decision and receipt accepted by the real `ACSC.consumeDecision` and `PSC.reportAttestedOutcome` (0.5 s); one SIGSTOPped witness leaves 3 signatures; two stopped or killed give a classified `QUORUM_UNAVAILABLE` at the 10 s cap, no respawn, pid files unchanged; killing the adapter ends all four children in about 0.1 s and the restart on the same state keeps the durable pin; a child with a corrupt store leaves the adapter serving, that witness `silent`, and its single closed JSON error in `<state>/witness-<i>.stderr`; a refused startup spawns nothing; the E deployment spawns nothing. P3: after `1=crash:after_commit` the first collection has witness 1 `silent` with its record durable and the production entry restarted on the same state returns the SAME checkpoint; `2=delay:6000` is `silent` in the pool and times out at 5 s in single-witness mode; the compromised worker releases for a claimed digest with no ledger grant (symbolic only) while the production entry answers `NOT_COMMITTED`.

## 2. Corrections and a finding (please carry these into the FREEZE and the oracle)
1. **`silent` in a pool SUCCESS means "not heard before quorum", not "stopped".** The pool returns as soon as three matching signatures arrive and reports an unheard witness `silent`. Five consecutive collections with four healthy witnesses and no fault each had a `silent` outcome, and the index varied. A2-0074 section 5 said "`silent` = zero replies": that is true of replies received before the result, and it must not be read the other way round. **A fault oracle must decide that a witness is dead from its pid file and `/proc/<pid>`, never from `silent` in a result that succeeded.** In a FAILED collection `silent` is a witness that did not answer within the deadline. (Pinned by `test_silent_in_a_pool_result_means_not_heard_before_quorum_and_occurs_in_healthy_runs_too`.)
2. **The E-profile answer** is `ADAPTER_UNAVAILABLE "<operation> is not wired in this process"` (no witness handler is installed for the carried E successor deployment). The text "not wired for this deployment profile" belongs to the F handlers meeting a non-F manifest. A2-0074 did not state the E text; my module docstring did and was wrong (corrected).
3. **A bug of mine found only by the live tests (fixed in 699ed50):** run as `python -m`, the command's `Refusal` class and the one a lazily imported module raised were two different classes, so a corrupt `--allow-governance` file ended as `ADAPTER_UNAVAILABLE "internal startup failure"` instead of `MALFORMED`. No offline test could see it. `Refusal` now lives once in `startup_config`.

## 3. Carried from A1-0117 (read, no action asked)
The ledger enforces `sequence > current`; the exact `current + 1` is witness-side validation. A compromised quorum of three can also saturate `authEpoch` and `sourceBlockNumber`, not only `sequence`: that is the same out-of-bound case (outside f = 1) as my A2-0072 characterization, which covers the sequence path only.

## 4. What is still owed, and what I do not claim
Still owed: re-run of all 22 mutation runners and the full suite on a clone of exactly 8751cf8 (running); the complete runtime READY with those numbers, the refreshed v2/v2.1 mapping evidence and the E regression results; then your execution FREEZE and my exact ACK. **Not claimed:** any F case, E parity beyond the pins I ran (fingerprint, default export, `adapter.json`, AST-confined changes of the three E-listed paths; results in `protocol/evidence/af2-source-ready-3/E-REGRESSION-RESULTS.md`), real-process H1/H3 (not proposed), power-loss durability, consensus.
Limits: real-time bounds in the live tests are generous but a heavily loaded host can still flake the 10 s FL-3 cap and the 5 s H6 checks; forked sub-agents wrote parts of the transport, hooks, wiring tests and pins on the human's instruction and I re-ran each claim above myself.

Action requested:
- agent 3: your exact ACK or amendments of A2-0074 (O1..O6) still gate my READY; please use the two corrections above (`silent`, E text) in your oracle and FREEZE. If you want real-process H1/H3, say so now.
- agent 1, human: none.
