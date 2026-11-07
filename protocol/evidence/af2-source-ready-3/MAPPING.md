# Agent 2 runtime source: consumer mapping, refreshed for the complete runtime READY (A3-0079 request; supersedes af2-source-ready/MAPPING.md for every file it covered)

Source bytes under test: commit `8751cf8`. Commit of record: `7d97b902a7fa4d02c32c7cc95ef75a10b69694a9`, which differs from `8751cf8` ONLY in four mutation-runner tool files (`protocol/tools/run_{adapter_v2,adapter_v2_ops,rpc_binding_view,rpc_witness_view}_mutants.py`, repaired, see README) and in documents and evidence; `protocol/hmbc_protocol`, `testtools`, `exports`, `abi`, `tests`, `pytest.ini`, `requirements.txt` and the root locks are byte-identical (checked with `git diff`). PAPER-DERIVED RECONSTRUCTION; symbolic mode; synthetic TEST-ONLY keys; one host; correlated same-model review (forked sub-agents wrote parts, see README).

## 1. Publication receipt (hashes read from origin/agent-3 and checked by me)
| Item | SHA-256 (first 16) | Check |
|---|---|---|
| `interfaces/v2/FREEZE.json` | 7bb1d243d546dcc6 | equals the hash named in A3-0073 |
| `interfaces/v2.1/FREEZE.json` | 232b84bb7f997b68 | equals the hash named in STATUS and A3-0079 |
| `interfaces/v2.1/hmbc.schema.json` | d43c3a9a4cbb1021 | byte-identical to my fixture `protocol/tests/fixtures/agent3-v2.1-hmbc.schema.json` |
| `communication/F0_ACCEPTANCE_CANDIDATE2.json` | 03dcf485668430b1 | equals A3-0073 |
| the 52 pinned `protocol/f0` design files | manifest 8496c7f3266bdfd9 | `sha256sum -c protocol/f0/MANIFEST.sha256` from the repository root: exit 0 (no drift from the accepted design) |

## 2. Explicit successor schema selection (what A3-0079 asked of agent 2)
- The command line REQUIRES `--schema-revision v2|v2.1` (no default) and the exact published schema file with its pinned SHA-256; `adapter_v2.Context` requires the revision too. A manifest carrying the v2.1 marker with revision `v2` is refused.
- **New since A2-0063:** `adapter_v2.schema_problem(schema, revision, responses)` is the single authority for what a usable published schema contains (an object with an object `$defs` defining the revision's carrier branches and every response type). `Context` and the command line both ask it before anything else, so a schema of the wrong shape (null, an array) is refused up front and can never silently disable response checking (A3-0096).
- Whole-manifest equality: every request's `deploymentManifest` must EQUAL the pinned manifest as a whole; any difference is `WRONG_DESTINATION` (a manifest that is not deployment-shaped is `MALFORMED` first). Unchanged.
- Every response is checked against the published schema (`check_responses` stays on; nothing in the command line can switch it off).

## 3. D50 preimage retained
`hmbc_protocol/binding.py` is unchanged since its introduction (`f48cb34`; `git diff f48cb34 HEAD` is empty). `binding_open` rebuilds the same document and binding as the independent reference in `test_binding_open.py`; the F0 D50 vectors are pinned by the manifest of section 1. No source field enters the D50 binding B.

## 4. Historical E-listed source: exactly three of 142 entries differ (verified: `sha256sum -c protocol/evidence/source-manifest.sha256`, 005c8448..)
| File | Change | Plan basis |
|---|---|---|
| `hmbc_protocol/worker.py` | `Worker._recipient_for`: `profile == "2"` became `in ("2","3")` (a valid F grant fell into the paper branch; found live) | accepted profile-3 change (A3-0073, F_SOURCE_READY) |
| `hmbc_protocol/worker_log.py` | `main`: the opt-in `--state-dir D --binding` prints the D50 binding of the worker store; without the flag the default export is byte-identical | D50 section 5, worker store identity |
| `testtools/deviating_witness.py` | `main`: reads the pinned deployment with the strict parser (+ one import) | D-6 |
The carried E `witness.py` is UNCHANGED (`git diff 376347d HEAD` empty; I chose new modules instead of editing it). Detail: `E-SOURCE-ACCOUNTING.md`; the pins and their results: `E-REGRESSION-RESULTS.md` and `protocol/tests/test_e_regression_pins*.py`. **Actually run by me on this tree:** the 34 historical E test files together: **1383 passed, 201 skipped, 0 failed** (the A2-0039 baseline; the 201 are only ScenarioResult/FileHash out-of-scope cases); `python -m hmbc_protocol.export --check` exit 0 (9 files, `adapter.json` 7146495b..); the E pins (offline 10 passed; live pins inside the full suite).

## 5. New source, its tests and mutation runners (all 22 runners and the full suite re-run by me on a clone of `8751cf8`; outputs in `outputs/`)
| Module | Tests (collected) | Runner: detected |
|---|---|---|
| `hmbc_protocol/witness_state.py` (+ read-only exporter CLI) | `test_witness_state.py`, `test_witness_state_cli.py` (63) | `run_state_mutants`: 33 / 33 |
| `hmbc_protocol/binding.py` (D50 binding, UNCHANGED since f48cb34) | `test_binding.py` (10) | `run_binding_mutants`: 23 / 23 |
| `hmbc_protocol/binding_open.py` | `test_binding_open.py` (106) | `run_binding_open_mutants`: 52 / 52 |
| `hmbc_protocol/worker_binding.py` | `test_worker_binding.py` (42) | `run_worker_binding_mutants`: 32 / 32 |
| `hmbc_protocol/pool_core.py` | `test_pool_core.py` (88) | `run_pool_core_mutants`: 47 / 47 |
| `hmbc_protocol/witness_pool.py` | `test_witness_pool.py` (52) | `run_pool_mutants`: 58 / 58 |
| `hmbc_protocol/witness_pool_driver.py`, `testtools/virtual_transport.py` | `test_witness_pool_driver.py` (12) | `run_pool_driver_mutants`: 15 / 15 |
| `hmbc_protocol/witness_service.py` (checkpoint, decision, receipt, governance) | `test_witness_service.py`, `test_witness_service_decision.py`, `test_witness_service_receipt.py`, `test_witness_service_governance.py`, `test_witness_service_sequence_bounds.py` (202) | `run_service_mutants`: 137 / 137 |
| `hmbc_protocol/adapter_v2.py` (incl. `schema_problem`) | `test_adapter_v2.py`, `test_adapter_v2_output.py` (115) | `run_adapter_v2_mutants`: 56 / 56 (+2 argued equivalent: A27, A50) |
| `hmbc_protocol/adapter_v2_ops.py` | `test_adapter_v2_ops.py` (40) | `run_adapter_v2_ops_mutants`: 14 / 14 |
| `hmbc_protocol/adapter_v2_witness.py` | `test_adapter_v2_witness.py` (49) | `run_adapter_v2_witness_mutants`: 57 / 57 |
| `hmbc_protocol/adapter_v2_start.py` | `test_adapter_v2_start.py` (27) | `run_adapter_v2_start_mutants`: 15 / 15 |
| `hmbc_protocol/adapter_v2_main.py` (command line, `build_runtime`, supervisor lifecycle) | `test_adapter_v2_main.py`, `test_adapter_v2_main_wiring.py`, `test_adapter_v2_main_wiring_live.py` (63) | `run_adapter_v2_main_mutants`: 43 / 43 (+1 argued equivalent: C25) |
| `hmbc_protocol/witness_main.py` (one witness, one process) | `test_witness_main.py` (48) | `run_witness_main_mutants`: 39 / 39 (+1 argued equivalent: H35) |
| `hmbc_protocol/startup_config.py` (strict startup readers, one `Refusal`) | `test_startup_refusals.py` (182) | `run_startup_config_mutants`: 19 / 19 |
| `hmbc_protocol/rpc_binding_view.py` | `test_rpc_binding_view.py`, `test_rpc_binding_view_live.py` (66) | `run_rpc_binding_view_mutants`: 32 / 32 |
| `hmbc_protocol/rpc_witness_view.py` | `test_rpc_witness_view.py` (49) | `run_rpc_witness_view_mutants`: 45 / 45 |
| `hmbc_protocol/witness_process_transport.py` (supervisor + transport) | `test_witness_process_transport.py`, `test_witness_process_transport_live.py` (76) | `run_witness_process_transport_mutants`: 92 / 92 |
| `testtools/{faulty_witness,compromised_worker,delayed_witness}.py` (H4, H5, H6) + H7 process tests | `test_faulty_witness.py`, `test_compromised_worker.py`, `test_delayed_witness.py`, `test_witness_process_state_refusals.py` (103) | `run_witness_hooks_mutants`: 46 / 46 |
| `testtools/faulty_adapter_v2.py` (P3 alternate entry) | `test_faulty_adapter_v2.py`, `test_faulty_adapter_v2_live.py` (88) | `run_faulty_adapter_v2_mutants`: 41 / 41 |
| `testtools/byzantine.py` (H1, H3; virtual-time only) | `test_byzantine.py`, `test_byzantine_types.py` (55) | `run_byzantine_mutants`: 20 / 20 |
| E regression pins (fingerprint value, default export, `adapter.json`, AST-confined changes, E inventory) | `test_e_regression_pins.py`, `test_e_regression_pins_live.py` (13) | `run_e_regression_pins_mutants`: 23 / 23 |

Mutation method: a runner counts a mutant DETECTED only when the tests ran and failed; every anchor is validated to match exactly once before anything runs; the unmutated control runs first; an equivalent mutant is RUN and must survive (a runner exits 1 if a test notices one). Mutants are single-site text edits chosen by the same model family that wrote the code: 100% detection shows the tests are sensitive to those edits, not that the code is correct.
**Full protocol suite on a clone of exactly 8751cf8: 2946 passed, 201 skipped, 0 failed, exit 0, 1078 s** (`outputs/FULL-SUITE-on-clone-of-8751cf8.txt`). The 201 skips are 200 ScenarioResult and 1 FileHash schema-review cases outside agent 2's scope; **there is no Foundry skip.** Read the skip count, not only "passed".

## 6. What this mapping covers, and what it does not
Covered: the nine v2 operations on the closed v2 envelope with strict JSON lines, the 19-reason table, the four witness operations through four real supervised `witness_main` processes (live), the per-witness `witnessIndex` mode, the supervisor lifecycle and its pid and stderr files, the hooks H4/H5/H6 and the H7 refusals, the alternate TEST-ONLY entry, the startup refusals at both entry points, D50 as the worker and as the witness against real chains.
NOT covered or not claimed: any F case or the F gate (agent 3's integrated run); real-process H1/H3 (virtual transport only); power-loss or OS-kill durability (process death only); consensus (Anvil is not Byzantine consensus); real ABE or confidentiality (symbolic); production key custody (TEST-ONLY keys derivable from labels); `binding_open` still converts `deployBlock` with `int()` after the network step (the entry points refuse bad values first); the two argued-equivalent mutants of `adapter_v2` (A27, A50) are duplicate checks kept as defence in depth.
