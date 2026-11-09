# Protocol-scope inventory of the 32 F cases against the hooks and mutants that exist (agent 2, 2026-11-09)

PAPER-DERIVED RECONSTRUCTION; protocol scope only; one author (agent 2), correlated same-model review. This is the "agent 2 P0 inventory" that `communication/agent-1/solo/F-PLAN.md` assigns to proxy-2, written by the real agent 2 after its usage limit reset. It is a reading of the plan against MY code; it is not an F result and not an execution ACK (all 32 cases are NOT_RUN).

## Sources
- The case list: `evaluation/evidence/reviews/f0-revision8-20261104/f_matrix.json` (sha256 2230daf3.., 32 cases: FL-1..FL-11 and F-12..F-32) and `SOURCE-INTERFACE-PLAN.md` (sha256 76069506..), read from `origin/agent-3` 6358f7c. The hook and mutant definitions (H1..H7, M1..M7) are those of that plan, section "Owner tasks" 3 and "experiment coverage".
- My code at origin/agent-2 9d56d2c: `testtools/{byzantine,faulty_witness,delayed_witness,compromised_worker,faulty_adapter_v2,virtual_transport,state_oracle}.py`, `witness_process_transport.py`, `witness_state.py`, the runners in `tools/`, and the live tests.

## Result in one table (`inventory.csv`, one row per case, all 32 present)
| Group | Cases |
|---|---|
| Real-process support BUILT, nothing more needed from my hooks | FL-2, FL-3, F-19, F-20, F-23, F-32, and (store and process refusal level) F-27 |
| Built enough for protocol scope; the case is ledger, relay, evaluator or fixture work | FL-6, FL-8, FL-9, FL-10, FL-11, F-14, F-15, F-21, F-24, F-28, F-30 |
| Analysis only (no hook) | F-25, F-26 |
| **A gap in my hooks (12 cases)** | FL-1, FL-4, FL-5, FL-7, F-12, F-13, F-16, F-17, F-18, F-22, F-29, F-31 |

### The three gaps (all mine, all TEST-ONLY, none touches an adapter operation or `exports/adapter.json`)
- **G1: real-process H1.** The Byzantine witness variants (Repeater, Equivocator, Impersonator, Poisoner, Garbage, withhold, delayed) exist only as endpoints of the virtual transport (`testtools/byzantine.py`); the supervised `witness_main` children cannot be replaced by one. Needed by FL-4, FL-5, FL-7, F-12, F-17, F-22.
- **G2: real-process H3.** A per-witness divergent ledger view exists only in-process (`view_override`). The tripwire is reachable in a real process for a NUMBER regression only (`evm_revert`, cross-run S14); a same-height hash change, a timestamp regression and any split view need a per-witness RPC override. Needed by F-16, F-17, F-18, F-31.
- **G3: integrated source mutants M1..M7.** The mutants exist as single-site text edits inside my mutation runners (unit level), but no supervised witness or adapter process can be STARTED as a mutant, which the plan needs for FL-1 (M6, M7), FL-5 (M5), FL-7 (M4), F-12 (M1, M2), F-13 (M2), F-29 (M3).
Not a gap in my hooks but a fixture the runner must supply: the skewed-clock fixture for M7 (H6 itself is built), the governance-before-checkpoint ordering (a governance ADD makes earlier requests stale: A2-0080 F2), each checkpoint's own source block as `pbcHead` (A2-0080 F1), and the BindingExport anchor and worker snapshot decisions (A2-0077 F1, F2).

## Proposed order for agent 2 (smallest unblocking first; each test-first with a saved RED, then runner mutants, then a delta READY)
1. G3 as a tree-level mutant builder: copy `protocol/` to a scratch directory, apply ONE documented single-site edit (the anchors already in my runners; each must match exactly once), and start the witness or adapter child from the copy through the existing `command_for` seam. This yields REAL source mutants as separate processes, which is what "deliberate source mutants" means in the plan.
2. G1 as a TEST-ONLY real-process Byzantine witness over the existing `byzantine.py` classes, started through the same seam (`--witness-variant I=byz:...`).
3. G2 as a TEST-ONLY per-witness RPC override (a witness reading another Anvil node that shares genesis and the deployment block but is at another height or hash), through the same seam.
## What this does NOT say
It does not say any case passes; no case was run. It does not review the evaluator, the ledger or the oracles. A "BUILT" row means the hook exists and was exercised by my tests or by the cross-runs, not that the F oracle accepts what it produces. Whether a case needs a real Byzantine PROCESS rather than crafted signatures (F-24 is crafted) is a runner-design choice that agent 3's side must confirm.

## Progress after the inventory (2026-11-09; the inventory above is the state at 9d56d2c)
| Gap | Built | Tests (offline / live) | Mutation check |
|---|---|---|---|
| **G3** source mutants M1..M7 as real processes | `testtools/mutant_tree.py` (registry and builder, one verified single-site edit per mutant), `testtools/mutant_run.py` (exec launcher, allow-list, same pid), `testtools/mutant_probe.py`; `--witness-variant I=mutant:ID --mutant-tree ID=DIR` of the alternate entry | `test_mutant_tree.py` 31, `test_faulty_adapter_v2_mutants.py` 44; live `test_mutant_tree_live.py` 2 passed: **M1** a real supervised witness signs two conflicting checkpoints for one sequence with no pin where the production witness refuses (F-12); **M2** a witness replies BEFORE its commit, has no pin after a kill and then signs a conflicting checkpoint (F-12/F-13). M5 is an ADAPTER-role mutant (run the whole alternate entry from its tree); M3, M4, M6, M7 are started the same way but their integrated schedules are runner scope | `tools/run_mutant_tree_mutants.py`: the control passes and **7 of 7** registered mutants are detected by the EXISTING unit tests (M7 first SURVIVED: my service tests had no skewed-clock case; `test_the_expiry_has_no_local_clock_term_even_where_one_would_bind` was added and M7 is now detected) |
| **G1** real-process H1 | `testtools/byzantine_witness.py` (withhold, garbage, repeat:N, equivocate, impersonate:J, poison:FIELD over the production serve loop); `--witness-variant I=byz:SPEC` | `test_byzantine_witness.py` 66, `test_faulty_adapter_v2_byz.py` 34; live `test_byzantine_witness_live.py` 4 passed against the real pool and ledger: **FL-4** a repeater counts once (three distinct signers); **F-12** an equivocator's second value never joins the certificate and its store holds one pin; **FL-5/F-22** an impersonated signature is `invalid` and the pool classifies QUORUM_UNAVAILABLE; **FL-7** a poisoned checkpoint is `dissent` | `tools/run_byzantine_witness_mutants.py`: **19 of 19** detected (two survived at first: no test for the TEST-ONLY derivation check and none for a usage text on the real stderr; both added) ; `tools/run_faulty_adapter_v2_mutants.py` now 55 mutants: **55 of 55** detected, 2 argued equivalents survive |
| **G2** real-process H3 | not built | | |
Failed trials kept: the first live M2 run failed on my own pid-file race (`failed-trial-live-m2-pid-file-race-m1-passed.txt`); the `RED-*.txt` files are the failing runs before each implementation (the missing-module REDs are weak by construction: their sensitivity is shown by the mutation runners above).
Limits: the live tests are one trial each on one host with one adversary position (witness 3); two of them stop an honest witness so the outcome does not depend on reply order; no F oracle has judged any of this; the mutants are deliberate single-site edits by the same model family that wrote the code.
