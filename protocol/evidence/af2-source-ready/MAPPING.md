# Agent 2 successor source: consumer mapping (A3-0079 request, F task 2 and 3)

Source commit: `dbae4e1e13fb26984a6d4b0aa042ae321c1c49f0` on `agent-2`. Source manifest: `MANIFEST.sha256` in this directory (384 files under `protocol/` at that commit, SHA-256 of the manifest `6ed9a53de1ec2ec32fedad01019ce18cd4196a304cc47202b4a0e3655218ca08`). PAPER-DERIVED RECONSTRUCTION; synthetic fixtures only; symbolic cryptography only; no integrated run.

## 1. Explicit successor schema selection (what A3-0079 asked of agent 2)

- `adapter_v2.Context(manifest, schema_revision, handlers, schema=None)` REQUIRES `schema_revision` to be `"v2"` or `"v2.1"`; there is no default. A manifest carrying the v2.1 marker `hmbc-ledger-deployment/v2.1` with revision `"v2"` is a `ValueError` at construction; the v2.1 branches (`LedgerDeploymentE`, `LedgerDeploymentF`, `LedgerDeploymentEComplete`) are the ones the selected revision allows. With the parsed published schema passed as `schema`, the pinned manifest is validated against those branches at construction (before any chain read: `adapter_v2_start.start` builds a dry Context first).
- Whole-manifest equality: every request's `deploymentManifest` is compared with the pinned manifest as a whole (`handle_line`); any difference is WRONG_DESTINATION; a request manifest that is not even deployment-shaped is MALFORMED first.
- D50 preimage retained: `binding.py` is unchanged since slice 2 (`f48cb34`); `binding_open.reconstruct` builds the same document B and the same `binding_v2` as the independent reference (`test_binding_open.py`, 106 tests, document built independently in the test) and, on agent 1's three real v2.1 manifests, as agent 3's `evaluation.binding_context_v2` (A2-0062 differential, accept/refuse and hashes; the one-sided `Governance.maxGovernanceTtl`/`governanceChainId` reads were settled as no RFC by A3 D56 and A1-0116).
- The default v1 adapter and export are untouched: `python -m hmbc_protocol.export --check` exits 0 (9 files match), and the carried E suites pass (full-suite run in `README.md`).
- Published-schema byte copies used as fixtures: `protocol/tests/fixtures/agent3-v2.1-hmbc.schema.json` (sha256 d43c3a9a4cbb10214135afb767a2adc109da462f88bd11a81a8c8955d44fd1f3), `agent3-v2-reason-codes.json`, `agent1-85c59f5-f-base-deployment.json`, `agent1-85c59f5-e-successor-v2.1-deployment.json`, with `agent3-interfaces-provenance.json`.

## 2. Historical E-listed source changed against the approved plan

`protocol/evidence/source-manifest.sha256` (142 entries, SHA-256 005c8448..) checked at this commit: exactly TWO entries differ.

| File | Change | Plan basis | Evidence |
|---|---|---|---|
| `protocol/hmbc_protocol/worker_log.py` | opt-in `--state-dir D --binding` reads `<D>/worker/` and prints the D50 binding of the worker store; without the flag nothing changes | D50 section 5 worker store identity (slice 5b) | `test_worker_binding.py` 42, `run_worker_binding_mutants` 32/32; carried `test_worker_log.py` passes |
| `protocol/testtools/deviating_witness.py` | reads the pinned deployment with the carried strict JSON parser (duplicate keys, NaN/Infinity, invalid UTF-8 refused) | D-6 hardening backlog, carried by DECISIONS | `test_deviating_witness_strict.py` 7 (6 red first); 4 of 4 hand-made mutants (not a pre-validated runner) |

D-4 (relabel results v1 to v2) is NOT an edit of an E file: it is the new `adapter_v2_ops.py`, which validates the carried E result first. `witness.py` (the carried E witness) is UNCHANGED: the plan listed "changes to witness.py (profile 3 ...)"; I chose new modules (`witness_service.py` and the pool) instead, so the carried E witness keeps its behaviour. That is a deviation from the file list in INVENTORY section 5, stated here, not hidden.

## 3. New source, its tests and mutants (all rerun at this commit; outputs in `mutants/`)

| Module (all under `protocol/`) | Tests (collected) | Runner: detected |
|---|---|---|
| `hmbc_protocol/witness_state.py` (+ read-only exporter CLI) | `test_witness_state.py` 40, `test_witness_state_cli.py` 23 | `run_state_mutants` 33/33 |
| `hmbc_protocol/binding.py` | `test_binding.py` 10 | `run_binding_mutants` 23/23 |
| `hmbc_protocol/binding_open.py` | `test_binding_open.py` 106 | `run_binding_open_mutants` 52/52 |
| `hmbc_protocol/worker_binding.py` | `test_worker_binding.py` 42 | `run_worker_binding_mutants` 32/32 |
| `hmbc_protocol/pool_core.py` | `test_pool_core.py` 88 | `run_pool_core_mutants` 47/47 |
| `hmbc_protocol/witness_pool.py` | `test_witness_pool.py` 52 | `run_pool_mutants` 58/58 |
| `hmbc_protocol/witness_pool_driver.py`, `testtools/virtual_transport.py` | `test_witness_pool_driver.py` 12 | `run_pool_driver_mutants` 15/15 |
| `hmbc_protocol/witness_service.py` (checkpoint, decision, receipt, governance) | `test_witness_service.py` 52, `_decision` 56, `_receipt` 36, `_governance` 52 | `run_service_mutants` 137/137 |
| `hmbc_protocol/adapter_v2.py` | `test_adapter_v2.py` 96 | `run_adapter_v2_mutants` 43/43 |
| `hmbc_protocol/adapter_v2_ops.py` | `test_adapter_v2_ops.py` 40 | `run_adapter_v2_ops_mutants` 14/14 |
| `hmbc_protocol/adapter_v2_witness.py` | `test_adapter_v2_witness.py` 49 | `run_adapter_v2_witness_mutants` 57/57 (7 equivalents recorded in the runner) |
| `hmbc_protocol/adapter_v2_start.py` | `test_adapter_v2_start.py` 27 | `run_adapter_v2_start_mutants` 15/15 (1 equivalent recorded) |
| `testtools/byzantine.py` (H1, H3) | `test_byzantine.py` 22, `test_byzantine_types.py` 33 | `run_byzantine_mutants` 20/20 |

Mutant runners count a mutant detected only when the tests ran and failed; anchors are validated before any run; the unmutated control runs first; equivalent mutants are recorded and dropped, never counted. Same-model (correlated) design of tests and mutants.

## 4. What the v2 consumer mapping covers, and what it does not

Covered: the nine v2 operations on the closed v2 envelope with strict JSON lines (`prepare_request`, `collect_checkpoint`, `collect_decision`, `attest_grant`, `collect_governance`, `release`, `encrypt_record`, `finish_decryption`; `rotate_epoch` is NOT_IMPLEMENTED_IN_PHASE); the 19-reason table; collection evidence in the published `Collection` shape; results validated against the PUBLISHED schema in the tests.

NOT covered (see `README.md` for the full list): no command line and no real wiring (chain view, `Worker` factory, witness channels are injected fakes); no witness processes; no real transport or clock; the four witnesses share one fake ledger view in the pool tests; hooks H2, H4 (crash points exist as `witness_state` `crash_hook`, tested there), H5 and H6 beyond the transport's delay knobs; the Byzantine variants run for all four message types but only against that shared fake view.
