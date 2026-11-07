# Historical E source accounting for the F source READY (agent 2)

Author: agent 2 (Fork C of the 2026-11-07 session). **PAPER-DERIVED RECONSTRUCTION; symbolic mode; synthetic data; one host.** This document accounts for every path of the historical E source inventory, ties each changed path to the approved plan, and separates what was **run** from what was only **read** and from what is **still to run**. It is not an E-parity claim and not a source READY.

Required by: A3-0073 ("A2-0058 N-1 CONFIRMED ... approved F edits to E-listed source use NEW F READY hashes. Preserve E assertions/operations/outputs/default worker export/legacy fingerprint, run actual isolated regressions/export checks, and retain failed trials. No E parity is claimed before tests"), `communication/F_SOURCE_READY.md` section "Historical E source and successor regressions - A2-0058 N-1", A3-0096 and A3-0097 ("Historical E inventory now differs at worker.py, worker_log.py, deviating_witness.py (3/142); new full READY must inventory them and provide E regressions").

## 1. The inventory and how it was checked

| Fact | Value | How established |
|---|---|---|
| Inventory file | `protocol/evidence/source-manifest.sha256` | read |
| SHA-256 of the inventory | `005c8448faeb90d2dade129211a5f220635ee1c8bf421c89f17b2b7d0c2d7612` | `git show 376347d:protocol/evidence/source-manifest.sha256 \| sha256sum`; equal at `HEAD` and in the working tree (3 commands, exit 0) |
| Entries | 142 | `wc -l` on the file at `376347d` |
| Historical commit | `376347d9b0979d1e46824a30197b935ffe91e4fb` (common F0 baseline) | `git cat-file -t` returned `commit` |
| Compared against | `HEAD` = `67111f580b6ecfd1b924f3cd1a863981180822e1` (branch `agent-2`) and the working tree at 2026-11-07T15:29Z | `git show <ref>:<path>` and `sha256sum` per path (read-only Python, exit 0) |
| Manifest vs historical blobs | all 142 entries equal the blob at `376347d` | same script |

## 2. Result: which of the 142 entries differ

| Outcome | Count | Paths |
|---|---|---|
| Unchanged (HEAD **and** working tree equal the inventory hash) | **139** | all others |
| **Changed** | **3** | `protocol/hmbc_protocol/worker.py`, `protocol/hmbc_protocol/worker_log.py`, `protocol/testtools/deviating_witness.py` |
| Removed (absent at `HEAD`, absent in the working tree) | **0** | none |

HEAD and working-tree hashes of the three are identical (no uncommitted edit touches them).

| Path | E inventory sha256 | Now (HEAD = working tree) sha256 | Commit |
|---|---|---|---|
| `protocol/hmbc_protocol/worker.py` | `204af36906a89521517c88b1314e596e087a303e576cff38836071532bdb8908` | `23f81953312fd8695ff6b0d9ebfa3f4f2c466b4c42229f5cc35bd7b719ec0c30` | `be27f32` (2026-11-07) |
| `protocol/hmbc_protocol/worker_log.py` | `b443d5e8a6b62e7cded7bbece00c78a2cfbc05fd983d912e303398de2a36cd0e` | `2202e8a3b4142c655f655301de890ecd0eb664cdb0657135755035bb0d4653a4` | `eb6e299` (2026-11-04) |
| `protocol/testtools/deviating_witness.py` | `0511ba571b71d960d8ffbe4b8c811da99ed7de53a4b7515ac425c5291cc3c2d7` | `8862f28c969e32778e8801e307fdf4ea59bfd35aa570017427af0770de430bff` | `0ec5422` (2026-11-06) |

**Unchanged by hash, by category (all 142):** the 34 E test files `tests/test_*.py` (every one, so **every E assertion is byte-identical**, by hash, not by run); the other 17 files of `tests/` (conftest, support, fixtures); `exports/*` (9, so `adapter.json` is `7146495b4dfbe351d73299223efdb853c41895ac880f9a6c13e2a525656a9220`, equal to the recorded value); `abi/*` (8); 14 of the 16 E production modules including `adapter.py`, `export.py`, `chain.py`, `witness.py`, `wire.py`, `eip712.py`; `pytest.ini`, `requirements.txt`, `README.md`; the other 3 `testtools`; 3 `tools`; 48 evidence files.

**Agreement with agent 3:** A3-0096/A3-0097 say the inventory differs at exactly these three paths (3/142). **No discrepancy found.** (My own older STATUS said "exactly 2 intended mismatches"; that was true until the third change, `worker.py` in `be27f32`.)

## 3. Entries added since the inventory (not in it)

`git diff --name-status 376347d..HEAD -- protocol/` gives **301 added (A), 3 modified (M), 0 deleted**; the 3 modified are exactly the paths of section 2, so **no other path of the inventory was modified**. The 301 additions (none is in the inventory):

| Area | Added |
|---|---|
| `protocol/evidence/` | 135 |
| `protocol/f0/` (pinned F0 design, vectors, models) | 53 |
| `protocol/tests/` | 42 (28 `test_*.py`/helpers as `.py`, 14 other, fixtures) |
| `protocol/v2-review/` | 35 |
| `protocol/tools/` (mutant runners) | 17 |
| `protocol/hmbc_protocol/` | 16 (`adapter_v2.py`, `adapter_v2_main.py`, `adapter_v2_ops.py`, `adapter_v2_start.py`, `adapter_v2_witness.py`, `binding.py`, `binding_open.py`, `pool_core.py`, `rpc_binding_view.py`, `rpc_witness_view.py`, `witness_main.py`, `witness_pool.py`, `witness_pool_driver.py`, `witness_service.py`, `witness_state.py`, `worker_binding.py`) |
| `protocol/testtools/` | 3 (`byzantine.py`, `state_oracle.py`, `virtual_transport.py`) |

**Uncommitted at the time of writing (2026-11-07T15:35Z; other work in the same tree, not part of the 301):** modified `hmbc_protocol/{adapter_v2,adapter_v2_main,rpc_binding_view,rpc_witness_view,witness_main}.py` and two runners under `tools/`; untracked `hmbc_protocol/startup_config.py`, `tests/{test_startup_refusals,test_faulty_witness,test_witness_process_transport}.py`, `tests/stub_witness_child.py`, `testtools/faulty_witness.py`, `tools/run_startup_config_mutants.py`, `evidence/af2-startup-fix/`. None of these is an E-listed path; the READY's own inventory must list them with their final hashes. **None of the three E-listed paths is among them.**

## 4. The three changed E-listed paths

### 4.1 `hmbc_protocol/worker.py` - profile-3 recipient binding (`be27f32`)
* **Diff (read):** 2 insertions, 2 deletions, both inside `Worker._recipient_for`: the docstring ("repaired-e **and repaired-f (profiles 2 and 3)**") and the profile test `led.pbc.call(led.PSC, "profile") == "2"` becomes `in ("2", "3")`. Nothing else changed, in particular not `__init__` (the deployment fingerprint), `release`, `encrypt_record`, `finish_decryption` or the schema.
* **Why (finding, tested reconstruction result):** found live: a valid F grant (profile 3) fell into the paper branch and was refused as a "paper profile" grant.
* **Plan item:** the accepted profile-3 change: A3-0073 ("D4/D6/profile3/store/exporter source changes are Agent2-owned accepted tasks") and `F_SOURCE_READY.md` ("Agent2 may perform the accepted D4/D6, D50/store, profile-3 and exporter changes in its owned source"); N-1 confirmed by A3-0073. A3-0096 reviewed it: "profile3 valid recipient now succeeds, invalid/zero recipients still refuse; profiles 0/1/2 preserved" (16 old/current recipient cases, agent 3's own run, **not** re-run by me).
* **Tests that import the module directly (grep, not coverage):** `test_worker.py`, `test_worker_hardening.py`, `test_paper_release.py`, `test_paper_profile.py`, `test_recovery.py`, `test_faulty_adapter.py`, `test_e2_repaired_e.py` (live E catalog), `test_worker_log.py`, plus the F additions `test_worker_profile3.py`, `test_worker_binding.py`, `test_adapter_v2_ops.py`, `test_adapter_v2_start.py`. Tests that reach it only through the adapter are not enumerated.
* **Status:** the E branches of `_recipient_for` (profile "2" and the paper branches) are not edited in logic; **parity is not demonstrated until the E suite is run (section 6).**

### 4.2 `hmbc_protocol/worker_log.py` - opt-in D50 binding export (`eb6e299`)
* **Diff (read):** 6 insertions, 1 deletion, all in `main`: a new opt-in flag `--binding` (print the D50 binding export of `<state-dir>/worker` instead of the log; read-only, no RPC) dispatched to `worker_binding.binding_main`, imported lazily; otherwise the original `print(json.dumps(export(...), indent=1))`. **The whole diff against the inventory version is one hunk (`git diff -U0 ... | grep -c '^@@'` = 1), and it is inside `main`; so everything else, `export()` and `_database()` included, is textually identical.** (I additionally compared the `export()` body alone with `diff`, exit 0.)
* **Note:** the inventory version `b443d5e8..` already contains the A2-0039 URI-quoting fix (the 142-entry inventory was taken after it).
* **Plan item:** the accepted exporter change (A3-0073 "exporter"; `F_SOURCE_READY.md`); D50 binding export per `protocol/f0/EXPORT-LAYOUTS.md`.
* **Tests that import it:** `test_worker_log.py`, `test_adapter_process_paper.py`, `test_faulty_adapter.py`, `test_exports.py`, and the F addition `test_worker_binding.py`.
* **Status:** default behaviour unchanged by reading; **bytes of the default export compared by run only on a synthetic state (section 5); real-flow comparison still to run.**

### 4.3 `testtools/deviating_witness.py` - strict JSON for the TEST-ONLY tool (D-6, `0ec5422`)
* **Diff (read):** 8 insertions, 1 deletion: the deployment is read with `hmbc_protocol.adapter.strict_loads` instead of `json.loads` (duplicate member names and NaN/Infinity refused), with closed `refusing:` exits for non-UTF-8 and strict-parse errors. No change to the receipt construction, the field guard, the TEST-ONLY guard or `--at-block`.
* **Plan item:** D-6: R11 of S2-0007 ("one-line fix plus a test, after gate E"), carried as an accepted task in the F plan (A3-0073 "D4/D6"; `F_SOURCE_READY.md`). A TEST-ONLY tool, outside the adapter and `exports/`.
* **Tests that import/run it:** `test_supplement_controls.py` (E: the receipt-binding controls) and the F addition `test_deviating_witness_strict.py`.
* **Status:** by reading, valid (byte-identical) deployments parse the same; **E parity is not demonstrated until `test_supplement_controls.py` is run (section 6).**

## 5. What I RAN for this document (all read-only on the repository)

| # | Command (cwd = repository root) | Exit | Result |
|---|---|---|---|
| 1 | `git cat-file -t 376347d9..`; `git show 376347d..:protocol/evidence/source-manifest.sha256 \| sha256sum`; `wc -l`; same at `HEAD`; `sha256sum` of the working-tree file | 0 | manifest `005c8448..`, 142 entries, identical in all three places |
| 2 | Python 3.12.3 script: for each of the 142 entries `git show 376347d:<path>`, `git show HEAD:<path>` and the working-tree file, `sha256` | 0 | 139 equal, 3 changed, 0 removed; manifest equals the historical blob for all 142 |
| 3 | `git diff --name-status 376347d HEAD -- protocol/` and classification by manifest membership | 0 | A 301, M 3 (the three), D 0 |
| 4 | `git diff --stat` / `git log` / `git diff -U2 376347d HEAD -- <each of the 3 paths>` | 0 | the diffs of section 4 |
| 5 | `git diff --name-status 376347d HEAD -- protocol/exports protocol/abi`; `sha256sum protocol/exports/adapter.json`; per-module `git diff --quiet` of the other E production modules | 0 | empty diff; `adapter.json` `7146495b..` as recorded; all listed E modules `same` |
| 6 | `diff` of `worker.py` lines 60-75 (the fingerprint computation) and of `worker_log.export()` between `376347d` and `HEAD` | 0 | both identical |
| 7 | **Partial regression probe** (below), 6 sub-commands | 0 | fingerprint equal; default export byte-identical on a synthetic state |

**The probe (scratch directory only, nothing written in the repository).** It is a *partial* check on a **synthetic offline state**, not the E suite and not a live release flow.
1. `git archive 376347d protocol | tar -x -C <scratch>/hist` (historical code; its `worker.py` hashes to `204af369..`, its `worker_log.py` to `b443d5e8..`, equal to the inventory).
2. A 12-line Python script builds a `Worker` **offline** (no chain call) on the E fixture `protocol/tests/fixtures/deployment-agent1-91add8c-v1-repaired-e.json`, prints the deployment fingerprint from its `meta` table, inserts one synthetic `events` row and one synthetic `releases` row, and closes. It was run once with the historical code (state A) and once with the current code (state B).
3. `python -B -m hmbc_protocol.worker_log --state-dir <state>` with `env -i PATH=/usr/bin:/bin PYTHONPATH=<root>` was run with the historical and the current `worker_log.py` on **both** states (2 x 2 = 4 exports).

Results: the fingerprint is `758f970ef15219817004e0a16683a0a64e1a4cbbd3c40c227bb2e9d76610f6a5` for both code versions, and its first 16 hex digits equal the reference recorded in `protocol/evidence/return-review-2026-10-12/fingerprint-measurement.txt` (`758f970ef1521981`). All four exports exit 0 with empty stderr and are **byte-identical** (1533 bytes, sha256 prefix `d1f63d10c9a890d3`); the content is not vacuous (schema `hmbc-worker-log/v0`, one `RELEASE_INTENT` event, one release, counts `1`/`0`, fingerprint prefix `758f970e`).

**Failed trial kept:** the first run of the four exports used Python's `-I`, which removes the current directory from the module path, so every export exited 1 with `ModuleNotFoundError: No module named 'hmbc_protocol'` and empty stdout; the "all four identical" comparison of that run was **vacuous (empty equals empty) and is not used**. The corrected run above is the evidence.

**Tool versions:** git 2.43.0; analysis scripts Python 3.12.3; probe Python 3.13.12 (venv built from the root `uv.lock`) with eth-account 0.14.0, jsonschema 4.26.0, pytest 9.0.2; GNU coreutils sha256sum 9.4. Host Linux x86_64, one machine.

**What the probe does not show:** no real release flow, no live chain, no `RELEASE_SENT` row, no profile-2/3 recipient branch, no crash case, no adapter process.

## 6. STILL TO RUN before the READY may say anything about E (nothing below was run by me)

| # | Check | Command (repository root, root-lock Python 3.13, Foundry 1.8.5 and solc 0.8.37 at the pinned hashes, `HOME`/`HMBC_FOUNDRY_DIR` set) | What it must show |
|---|---|---|---|
| 1 | The E suite | `python -m pytest protocol/tests -c protocol/pytest.ini --rootdir protocol -p no:cacheprovider -rs -q` (whole directory, including the 34 byte-identical E test files). **Read the skip count:** the expected skips are the 201 "not agent-2's scope" schema-review cases; a live-fixture skip means a live test did not run (for example `test_rpc_binding_view_live.py` ignores `HMBC_FOUNDRY_DIR` and needs `~/.local/share/hmbc-tools/foundry-1.8.5`). | 0 failures; every E test passes at the current hashes |
| 2 | The three affected E test groups, named | `test_worker.py test_worker_hardening.py test_paper_release.py test_paper_profile.py test_recovery.py test_faulty_adapter.py test_e2_repaired_e.py test_worker_log.py test_adapter_process_paper.py test_exports.py test_supplement_controls.py` | pass; these are the tests of section 4 that exist at the historical commit |
| 3 | Export check | `PYTHONPATH=protocol python -m hmbc_protocol.export --check` | exit 0, `exports match 9 files` (`adapter.json` `7146495b..`) |
| 4 | **Legacy worker fingerprint, on fresh chains** | deploy repaired-e, paper-strict, paper-minimal and the two mutant profiles on fresh Anvil pairs (as `protocol/evidence/return-review-2026-10-12/measure_fingerprint.py.txt`) and compare to `fingerprint-live-fresh-chains.jsonl` (`9886222d774b769e` for all six) | equal to the recorded values. **Gap found: no existing test pins the fingerprint value, only `len(...) == 64` (`test_worker_log.py`); a value-pinning check must be added or this one run.** |
| 5 | **Default worker-export bytes on a real flow** | run a real E release flow (for example the `test_adapter_process_paper.py` state), then export the same state directory with the historical `worker_log.py` (`git archive 376347d`) and the current one | byte-identical |
| 6 | Mutation checks of the three paths | `python protocol/tools/mutation_check.py --only worker,worker_log,controls --out <scratch>` on a scratch copy (it edits sources in place) | every mutant detected as before; read each recorded tail (a failed assertion, not a collection error) |
| 7 | Retain failed trials | any red run, any first attempt that failed | listed in the READY |

## 7. Not claimed

No E parity, no run of the E suite, the export check, the live fingerprint check, the real-flow export comparison or the mutation checks for this document; no review of agent 3's own 16-case recipient comparison (A3-0096); no statement about the uncommitted work in the tree beyond naming it; no ABE, secrecy, delivery or consensus claim. Correlated same-model review; single host; synthetic fixtures only.
