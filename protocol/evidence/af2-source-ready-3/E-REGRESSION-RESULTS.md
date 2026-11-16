# E regression results for the F source READY (agent 2, Fork F; Step 5)

**PAPER-DERIVED RECONSTRUCTION; symbolic mode; synthetic TEST-ONLY data; one host; correlated same-model review.** Written 2026-11-07 against `origin/agent-2` 4d3462e (clean commit; the working tree also held the parent's uncommitted wiring edits to `adapter_v2_main.py`, which none of these checks imports). Required by A3-0073 and `communication/F_SOURCE_READY.md` ("Historical E source and successor regressions"); it completes the list that `E-SOURCE-ACCOUNTING.md` section 6 left open. **Everything in the "Ran" columns below was produced by a command; nothing is inferred.** Historical reference: commit `376347d9b0979d1e46824a30197b935ffe91e4fb` (common F0 baseline, E inventory `protocol/evidence/source-manifest.sha256`, SHA-256 `005c8448faeb90d2dade129211a5f220635ee1c8bf421c89f17b2b7d0c2d7612`, 142 entries).

## 0. Result in one paragraph
No difference between the historical and the current behaviour was found. The legacy worker fingerprint, the default worker export (on a synthetic state and on two real release flows), `exports/adapter.json` and `export --check` are unchanged; the three changed E-listed paths differ from the historical blobs only in the definitions the plan allows, and each allowed change is the reviewed one; the 34 historical E test files give **1383 passed, 201 skipped, 0 failed**, the same as the A2-0039 baseline. The pins catch **23 of 23** deliberate edits. **Not claimed:** anything about E that these checks do not exercise (see section 7).

## 1. What was built (all NEW files; no existing file edited)
| File | sha256 (first 16) | Role |
|---|---|---|
| `protocol/tests/test_e_regression_pins.py` | 440492652335a069 | 10 offline pins |
| `protocol/tests/test_e_regression_pins_live.py` | cca622c8afb82bbe | 3 live pins (fresh Anvil chains, real release flows) |
| `protocol/tools/run_e_regression_pins_mutants.py` | 1c4f6b65824db1db | 23 mutants + control |
| `protocol/evidence/af2-source-ready-3/E-REGRESSION-RESULTS.md` | this file | |

What the pins assert (historical code = `git archive 376347d` extracted to a temporary directory, imported in a subprocess whose printed package path is asserted, so a comparison of two empty outputs cannot pass):
1. **Fingerprint value** for `tests/fixtures/deployment-agent1-91add8c-v1-repaired-e.json`: `758f970ef15219817004e0a16683a0a64e1a4cbbd3c40c227bb2e9d76610f6a5`, historical == current (offline). Live, on fresh Anvil pairs: repaired-e, paper-strict, paper-minimal, `mutant-no-nonce`, `mutant-no-receipt-binding`: historical == current for each, and every value starts `9886222d774b769e`, as A2-0039 measured, all five equal (the documented weakness D-2: the fingerprint ignores the profile).
2. **Default worker export bytes**: a 2 x 2 cross (state written by the historical and by the current `Worker`, each exported by the historical and by the current `worker_log`) gives four equal, non-empty byte strings, pinned at 2644 bytes, sha256 `7a3ed500e3fbb567f1539eb481ab12613f170834e21e067d8e56d1c769d80d01`, with no raw token in them. Live: a real release flow (grant, release, retry) on repaired-e (the profile-2 recipient branch) and on paper-strict (the paper branch), exported by both `worker_log` versions: byte-identical.
3. `exports/adapter.json` sha256 `7146495b4dfbe351d73299223efdb853c41895ac880f9a6c13e2a525656a9220` and `python -m hmbc_protocol.export --check` exit 0, `exports match 9 files`.
4. **AST-level accounting** of the three changed E-listed paths against the historical blobs (docstrings ignored): the changed/added/removed definition sets are exactly `worker.py` {changed `Worker._recipient_for`}, `worker_log.py` {changed `main`}, `deviating_witness.py` {changed `main`; added the import `from hmbc_protocol.adapter import AdapterError, strict_loads`}. Beyond the set: `_recipient_for` equals the historical function **with only `profile == "2"` rewritten to `profile in ("2", "3")`** (checked by an AST rewrite of the historical function, one hit exactly); the two `main` functions equal the REVIEWED source embedded in the test (the opt-in `--binding` and the D-6 strict parse). A further edit to any of them fails.
5. **E inventory**: unchanged (sha `005c8448..`, equal to the blob at 376347d, 142 entries) and exactly the three allowed paths mismatch.
Plan items for the three allowed changes (from the accounting): `worker.py` profile-3 recipient binding (be27f32; A3-0073 "profile3"), `worker_log.py` opt-in D50 binding export (eb6e299; "exporter"), `deviating_witness.py` D-6 strict JSON (0ec5422; "D4/D6").

## 2. Commands and results (repository root; CPython 3.13.12 from the root `uv.lock`, pytest 9.0.2, eth-account 0.14.0, jsonschema 4.26.0, git 2.43.0, Foundry 1.8.5 (anvil 1.8.5) and solc 0.8.37 at the pinned hashes, Linux 7.0.0-42 x86_64; `HOME` redirected to a scratch directory, `HMBC_FOUNDRY_DIR` set)
| # | Command | Exit | Result | Saved output (scratchpad, sha256 first 16) |
|---|---|---|---|---|
| 1 | `run_suite.sh ff2-red protocol/tests/test_e_regression_pins.py` with **sentinel pins** (zero fingerprint, zero export hash and size, empty allowed-change table) | 1 | **5 failed / 5 passed**; the five failures print the real values: fingerprint `758f970e..`, export 1904 bytes (before the second release row was added), changed sets `{Worker._recipient_for}`, `{main}`, `{main}` + the one import | `ff2/RED-sentinel-pins-run1.txt`, `out-ff2-red.txt` (6876cd200a3f6e79) |
| 2 | same file, pins filled | 0 | 10 passed, 2.14 s | `out-ff2-green1.txt` (973806c18f53a88b) |
| 3 | same file after adding the second release row (see section 4) and re-measuring the export pin | 0 | **10 passed**, 2.33 s | `out-ff2-green2.txt` (29736b675cc2b40f) |
| 4 | `flock -x live.lock run_suite.sh ff2-live1 protocol/tests/test_e_regression_pins_live.py` | 0 | **3 passed, 0 skipped**, 157 s | `out-ff2-live1.txt` (da6b433b2024428a) |
| 5 | `python3 -B -I protocol/tools/run_e_regression_pins_mutants.py` (`run_runner.sh ff2-mut1`) | 0 | control passes; **detected 23 of 23**; equivalent survivors 0 of 0; 62 s | `runner-ff2-mut1.txt` (1689d47107b3b00f) |
| 6 | `flock -x live.lock run_suite.sh ff2-e34 <the 34 `protocol/tests/test_*.py` files of the E inventory>` (list: `ff2/e_test_files.txt`; each file's sha256 equals its blob at 376347d: 0 differ) | 0 | **1383 passed, 201 skipped, 0 failed**, 340 s; skips: ScenarioResult 2 x 100, FileHash 1 (the documented "not agent-2's scope" cases), **no Foundry skip** | `out-ff2-e34.txt` (04977edeb98b7440) |
| 7 | `PYTHONPATH=protocol python -B -m hmbc_protocol.export --check` | 0 | `exports match 9 files`; `adapter.json` `7146495b..` | (command) |
| 8 | `sha256sum -c protocol/evidence/source-manifest.sha256` | 1 (by design) | exactly `worker.py`, `worker_log.py`, `deviating_witness.py` FAILED; 142 entries; inventory sha `005c8448..` | (command) |
The 1383 / 201 of row 6 is **identical to the A2-0039 baseline** (1383 passed, 201 skipped). The skip count was read, not assumed.

## 3. The mutants (row 5): each is a single-site text edit in a copy of the whole `protocol/` tree, DETECTED only if pytest ran and reported failures
Fingerprint formula (F1-F6, 3 tests each): drop the RSC address, drop the ACSC address, unsorted keys, DBC slot carries the PBC chain id, **a field added to the legacy fingerprint (the D-2 hardening done in place)**, SHA-1. Default export (L1-L7): schema version, an extra member, indent 2, `--binding` on by default, event order, raw token instead of its digest, release order. Reviewed shape (R1-R4): the profile-3 fix lost, the profile test widened to 4, a second change inside the allowed function, a change in a definition the plan does not allow (`release` expiry boundary). `deviating_witness` (D1-D3): plain `json.loads` again, the non-UTF-8 refusal removed, the TEST-ONLY guard removed. E-listed adapter and export (A1, A2, X1): an operation status, a constant, the committed `adapter.json`. All 23 detected; the control (unmutated tree) passes. **The mutants do not make the code correct;** they show the pins are sensitive to these edits.

## 4. What the pins found, and failed trials kept
**Findings: none** (no difference between historical and current behaviour). Honest notes:
* **The first RED is a characterization RED, not a missing-feature RED.** These tests pin behaviour that already exists. Run 1 used sentinel pins so each pin demonstrably fails and shows what it measures; five of the ten (the two reviewed-`main` pins, the `_recipient_for` rewrite pin, the adapter export pin, the inventory pin) passed on their first run because there was no sentinel to fail. Their sensitivity is **only** shown by the mutants of section 3 (L4/R1/R2/R3/D1-D3/A1/A2/X1).
* **A sensitivity gap found and closed before the mutants existed:** the first synthetic state held ONE release row, so a change of the export's release ordering could not be seen. A second release row (created earlier but with the larger grant id) was added and the export pin re-measured (1904 to 2644 bytes); mutant L7 then detects an ordering change. The 1904-byte hash is superseded.
* The first verbose run could not show the full export digest (pytest elides it); the digest was then computed once with the current code, which is valid because the four exports are asserted equal by the test itself.
* Fork C's earlier probe, which compared two empty outputs because of `python -I`, is the reason every comparison here asserts the imported package path and a non-empty parsed export.

## 5. Seams needed in existing files
None. The pins use only the public `Worker`, `Ledger`, `worker_log` CLI and `export` CLI and `git archive`. The pin tests **fail, not skip**, when the historical commit is missing from the local object store.

## 6. Interaction notes for the parent
* The mutant runner needs `GIT_DIR` (it sets it from the real repository) because the temporary copy has no `.git`; run from a clone, it uses that clone's `.git`.
* The live file uses the session conftest fixtures (`ledger_chains*`, `world`, `world_paper`), which locate Foundry through `support.foundry()` and honour `HMBC_FOUNDRY_DIR`; with the parent's locator fix in `test_rpc_binding_view_live.py` no live file here depends on the hard-coded path. **Read the skip count of any live run.**
* The shared `$SCR/tmpd` holds `pytest-of-th4kur` (20 MB) and `wpt-mutant-*` (0.5 MB) from other runs; they are not mine and were left alone. No `e-pins-mutant-*` directory remains.

## 7. Not claimed
No claim about E beyond what is listed: not the live E integrated gate rerun (4749 s), not the existing owner mutation check `tools/mutation_check.py --only worker,worker_log,controls` (section 6 item 6 of the accounting: **NOT run here**), not the paper-minimal and mutant release flows (their fingerprints are pinned; their default exports were not compared on a real flow), not crash cases or the adapter process with the successor code, not power-loss behaviour, no ABE, secrecy, delivery or consensus claim, and no statement about the uncommitted wiring work in the tree. Review is correlated (same model family); one host; synthetic fixtures only.
