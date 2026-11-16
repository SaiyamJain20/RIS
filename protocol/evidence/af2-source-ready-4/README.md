# Agent 2 delta READY A2-0083: the three F-plan hook gaps G3, G1 and G2 (TEST-ONLY)

Delta on the A2-0079 commit of record f026a50. Source bytes under test: `origin/agent-2` 35f2bad for everything except `protocol/tools/run_faulty_adapter_v2_mutants.py` (a tool file, changed after 35f2bad; its hash below is the one of the commit of record that carries this directory). **No file under `protocol/hmbc_protocol`, `protocol/exports` or `protocol/abi` changed since f026a50** (`git diff --name-status f026a50 HEAD -- protocol/hmbc_protocol protocol/exports protocol/abi` is empty): the production witness, adapter, pool, store, exports and the D50 preimage are byte-identical to A2-0079. All twenty changed or new paths are TEST-ONLY tools, tests and runners.

## Files (sha256, first 16 hex, of the working-tree bytes at the commit of record)
| Path (under protocol/) | sha256 |
|---|---|
| `testtools/byzantine_witness.py` | 31cec279b733b545 |
| `testtools/divergent_witness.py` | 6de28f14beee47ff |
| `testtools/faulty_adapter_v2.py` | 0b0714ca9a16fe12 |
| `testtools/mutant_probe.py` | 7813e7d75f4bc84e |
| `testtools/mutant_run.py` | 3066b8956ba65510 |
| `testtools/mutant_tree.py` | 76ec604bcdeb5adf |
| `tests/test_byzantine_witness.py` | a0df90ebca73a919 |
| `tests/test_byzantine_witness_live.py` | b1029ae8f1d3ed24 |
| `tests/test_divergent_witness.py` | 4e9c80b3f46135ab |
| `tests/test_divergent_witness_live.py` | 3d12ef8d00d85f48 |
| `tests/test_faulty_adapter_v2_byz.py` | 0e0eef01eeec0500 |
| `tests/test_faulty_adapter_v2_mutants.py` | 431fb7eb6e917fef |
| `tests/test_faulty_adapter_v2_view.py` | e424ed4f62dfe205 |
| `tests/test_mutant_tree.py` | 78b2a9e1d681f904 |
| `tests/test_mutant_tree_live.py` | 9174f832ca0a3387 |
| `tests/test_witness_service_decision.py` | 365ff42d1126986c |
| `tools/run_byzantine_witness_mutants.py` | 5d851c99a9f6bb21 |
| `tools/run_divergent_witness_mutants.py` | 2adcee4a67e65719 |
| `tools/run_faulty_adapter_v2_mutants.py` | 64b579e0a9a3dd0e |
| `tools/run_mutant_tree_mutants.py` | e9c45cf700251dda |

Changed against f026a50: 17 new files and 3 modified (`testtools/faulty_adapter_v2.py`, `tests/test_witness_service_decision.py` (+11 lines, from the G1/G3 commit), `tools/run_faulty_adapter_v2_mutants.py`). Against the A2-0076 manifest (549 entries, 7de8f334..) a `git archive` of 35f2bad gives **544 OK and exactly five FAILED**: `witness_state.py`, `run_state_mutants.py` (A2-0078 and A2-0079), `tests/test_witness_service_decision.py`, `testtools/faulty_adapter_v2.py`, `tools/run_faulty_adapter_v2_mutants.py`; the archive of f026a50 gives 547 OK and the first two FAILED.

## What each gap is (see `../af-case-hook-inventory/README.md`)
- **G3** `testtools/mutant_tree.py`, `mutant_run.py`, `mutant_probe.py`: the F-plan source mutants M1..M7 as real processes (a verified single-site edit built into a tree and started through the alternate entry as `--witness-variant I=mutant:ID --mutant-tree ID=DIR`).
- **G1** `testtools/byzantine_witness.py`: a Byzantine witness as a supervised process (`I=byz:SPEC`: withhold, garbage, repeat:N, equivocate, impersonate:J, poison:FIELD).
- **G2** `testtools/divergent_witness.py`: a witness process whose `RpcWitnessView` is altered in-process (`I=view:SPEC`: authEpoch:N, policyVersion:N, witnessSetVersion:N, headLag:N). **It is NOT a second node with another block history**: no divergent hashes, fork or reorg.

## Commands and results (all from /home/karma/Documents/RIS-agent-2; CPython 3.13.13 in a venv whose .pth reads agent 3's pinned site-packages read-only; Foundry 1.8.5 via HMBC_FOUNDRY_DIR; UTC 2026-11-12)
| Command | Exit | Result |
|---|---|---|
| `pytest -q -c protocol/pytest.ini --rootdir protocol -p no:cacheprovider protocol/tests -rs` on the tree with G2 (before the runner-only edit) | 0 | **3204 passed, 201 skipped**, 26 min (`../af-case-hook-inventory/full-suite-with-g2-3204passed-201skipped.txt`); the live tests (G1, G2, G3, D50, CLI) ran; the 201 skips are 200 ScenarioResult and 1 FileHash schema-review cases outside agent 2's scope |
| `PYTHONPATH=protocol python -B -m hmbc_protocol.export --check` | 0 | exports match 9 files |
| `sha256sum -c protocol/f0/MANIFEST.sha256` | 0 | 52 OK, 0 failed |
| E-listed accounting (`protocol/evidence/source-manifest.sha256`, 142 entries) | n/a | exactly 3 differ: `worker_log.py`, `worker.py`, `deviating_witness.py` (unchanged since A2-0076) |
| the five affected mutation runners, `outputs/_exits.txt` | see below | byzantine_witness 19/19; mutant_tree 7/7; divergent_witness 27/27; service 137/137 (the decision test file changed); faulty_adapter_v2 **61/61** after two repairs |

The other 21 runners test modules that did not change and were NOT rerun for this delta; their A2-0076/78/79 outputs stand.

## Failed trials, kept
- Offline G2 tests were red first (`RED-divergent-witness-and-view-variant-41failed-14passed.txt`); the 4 G2 live tests passed on their FIRST run, so they are not red-first.
- G2 mutation run 1: 23/27 (`divergent-witness-mutants-run1-23-of-27.txt`): four gaps in my tests, fixed.
- **My own G2 edit broke two anchors of `run_faulty_adapter_v2_mutants.py`** (P10 and Q14: the error text and the `byz` partition line now matched differently). The runner's pre-validation stopped it with "INVALID anchors, nothing was run" (`outputs/run_faulty_adapter_v2_mutants-INVALID-anchor-P10.txt`); I repaired both, added six mutants for the `view` branches and ran again: 55/61, the six new ones NOT detected (`..-run-without-view-tests-55-of-61.txt`) because the runner's test selection did not include `test_faulty_adapter_v2_view.py`; with it included: 61/61, two argued equivalents survive as designed. I should have rerun this runner before pushing 35f2bad.
- My pkill pattern killed my own shell once during the commit; nothing lost.

## Limits (plain)
One author and one model family wrote the hooks, the tests and the mutants: correlated review. G2 is a view-level divergence (above). The live tests are single trials on one host with one adversary position (witness 3); two modes stop an honest witness so the outcome does not depend on reply order. No F oracle has judged any output, and all 32 F cases remain NOT_RUN. Nothing here is an execution ACK or a gate result.
