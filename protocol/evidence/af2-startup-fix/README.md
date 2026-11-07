# Step 1 evidence: startup-refusal fix (answer to A3-0096 / A3-0097)

Paper-derived reconstruction, synthetic data, one host (Linux x86_64), CPython 3.13.12, pytest 9.0.2, eth-account 0.14.0, jsonschema 4.26.0 from the frozen root `uv.lock` (1fb4777a..). Tree under test: HEAD `67111f5`
plus the uncommitted Step 1 fix. All runs below were made in temporary copies by the runners; nothing under `protocol/hmbc_protocol` or `protocol/tests` was edited by this evidence work.
**Correlated review:** written and run by the same model family as the fix. A mutation result shows the tests are sensitive to the listed edits, not that the code is correct.

Source bytes the runs were made against (sha256, first 16): `startup_config.py` 3a65487edfb6695b, `adapter_v2.py` 1e3b1b8987447f01, `adapter_v2_main.py` 1da0a7b5c009cf7d, `witness_main.py` 7a66d829c4a5118a,
`rpc_binding_view.py` 924f1850ef9b2a8c, `rpc_witness_view.py` 08307cd281d6d471, `tests/test_startup_refusals.py` 389d116f923a1af6.

## 1. RED, then GREEN (the parent's run, files kept here)

| Run | Result | File |
|---|---|---|
| RED, first trial (kept) | 131 failed / 33 passed, **but 54 of the failures were my test stub's bug** (`never_reached(**_)` rejected the witness path's positional call: `TypeError`), so the reason was wrong | `test-startup-refusals-RED-1-stub-bug-tb-line.txt` |
| RED, final | 131 failed / 33 passed, every failure for the intended reason: 115 lenient accepts ("startup went on to ask the chain"), 5 `RecursionError`, 5 `OverflowError`, 1 `AttributeError: 'list' object has no attribute 'get'`, 2 no last-resort guard, 2 real-process exit-1 tracebacks (A3's two cases), 1 wrong code | `test-startup-refusals-RED-final.txt` |
| GREEN | 164 passed, exit 0 | `test-startup-refusals-GREEN.txt` |

**The 33 passes are controls**: inputs the pre-fix code already refused (chainId `""`, `"0x10"`, `[]`, `null`, `{}` for both chains and both entry points = 20; the ABI `{}`/`null`/truncated cases = 6; allow-list `null`/string/number/bool/short-address/bad-action = 6; the valid-fixture control = 1).

**Three RED cases are RED only because the test asks for refusal BEFORE startup begins**: schemas `{}`, `{"$defs": []}` and `{"$defs": {}}`. The pre-fix CLI already refused them, later, through the dry `Context` of `adapter_v2_start` step 0
(`MALFORMED`, "startup refused: the supplied schema does not define ['LedgerDeploymentE', 'LedgerDeploymentF']"). Measured on a `git archive` of HEAD, real exit codes, in `prefix-schema-shapes.txt`:
`{}`, `{"$defs": []}`, `{"$defs": {}}` exit 2 MALFORMED; `null` exit 2 `ADAPTER_UNAVAILABLE` / `LEDGER_UNREACHABLE` (it got past the schema and asked the ledger: `Context(schema=None)` builds no response validators, which is
the "starts without response checking" risk, established here by code reading plus this behaviour, not by a live node); `[]` exit 1 with an `AttributeError` traceback (A3's case 2).

## 2. Mutation results (three runners, all single-site text replacements in a copy of the tree; DETECTED only when pytest ran and reported failed tests; control run first)

| Runner and command (repository root, `python -B -I`) | Exit | Detected | Output |
|---|---|---|---|
| `protocol/tools/run_witness_main_mutants.py` (tests: `test_witness_main.py` + `test_startup_refusals.py`) | 0 | **39 / 39**, 1 equivalent survivor | `runner-witness-main-39-mutants-after.txt` |
| `protocol/tools/run_adapter_v2_main_mutants.py` (tests: `test_adapter_v2_main.py` + `test_startup_refusals.py`) | **1** | **30 / 31**, 1 equivalent survivor, **1 TEST GAP (C27)** | `runner-adapter-cli-31-mutants-after.txt` |
| `protocol/tools/run_startup_config_mutants.py` NEW (tests: `test_startup_refusals.py`, both CLI test files, `test_adapter_v2.py`, `test_adapter_v2_output.py`) | **1** | **13 / 19**, **6 TEST GAPS** | `runner-startup-config-19-mutants-after.txt` |

Before: the same two CLI runners at HEAD 67111f5 were 20/20 (adapter) and 30/30 (witness), exit 0 (`runner-baseline-*-before.txt`). Changes to the existing runners: both now also copy and run `test_startup_refusals.py` (without it a mutant of a
new check could never be detected); new mutants C21-C32 (C25 is the equivalent) and H31-H40 (H35 is the equivalent); a new optional `E` list for equivalents that are RUN and must survive; the anchors of C6 (schema `except` clause, rewritten) and
C12/H28 (the exit code of a refusal: the anchor `return 2\n    return ...` now lands on the NEW last-resort `return 2`, because the guard sits between the refusal branch and the final return) were re-pointed and re-labelled, and C31/H39 now cover the refusal
branch itself. Every anchor is checked to match exactly once before anything runs.

### Equivalent survivors (claims checked by RUNNING the mutant; they must survive, otherwise the runner exits 1)
- **C25 / H35**: `Chain(url, numbers[s]["chainId"])` replaced by `Chain(url, int(manifest[...]["chainId"]))`. `sc.manifest_numbers(manifest)` has already run on the same manifest and refused every non-canonical chainId, and `int()` of a canonical decimal
  string is exactly the value `manifest_numbers` returned, so no input distinguishes the two. Ran and survived in both runners.

### Test gaps (NOT argued away): seven survivors, no test notices them
| Mutant | What is untested | Observable consequence |
|---|---|---|
| **C27** (adapter runner) / **A8** (new runner) | the shape check uses the SELECTED revision; no test runs v2.1 with a schema that lacks only `LedgerDeploymentEComplete` | the CLI would accept (until the later dry Context) a schema that cannot serve the chosen revision |
| **A3** | a schema that defines every carrier branch but lacks a response type | refused only later by `_build_response_validators`, not before startup begins (the property the new test states) |
| **A7** | `Context(check_responses=False)` must NOT require the response types, `check_responses=True` must | a wrong requirement either way goes unnoticed |
| **S5** | chainId width is 256 bits (a value between 2^64 and 2^255 must be accepted) | a narrower width would refuse legitimate large chain ids |
| **S6** | deployBlock width is 64 bits (2^64 must be refused) | a wider width would accept an out-of-range block number |
| **S10** | `chains`, or a chain, that is not an object (`null`, `[]`, `"x"`, `1`) | `TypeError` escapes `manifest_numbers`; at the process level only the last-resort guard hides it, with the wrong closed code (ADAPTER_UNAVAILABLE instead of MALFORMED) |

Proposed tests that kill all seven are in `proposed-additions-test_startup_refusals.py.txt` (not part of the suite: the test file was out of this work's ownership). Validated by `validate_proposed_additions.py.txt` against the real tree and
the seven mutants taken verbatim from the runners: control **18 passed**, then **killed 7 of 7** (`proposed-additions-validation.txt`). Adding them to `test_startup_refusals.py` and re-running the two runners should then give 31/31 and 19/19 (a prediction: the runners were NOT re-run with the additions; only the harness above was).

## 3. Failed trials kept
1. First RED run: 54 failures for the wrong reason (stub signature bug), see section 1.
2. First run of the new runner exited 2 at the control: `test_adapter_v2_output.py` imports `test_adapter_v2_ops`, which my copy list omitted (`runner-startup-config-run1-FAILED-control-missing-support-file.txt`, 11 failed / 342 passed in the diagnostic copy). Fixed in the runner (support file copied, not run); nothing from that run is used.
3. The dry anchor check found C6 no longer matched (the `except` clause it targeted was rewritten by the fix) and that my first C31/H39 anchors had an escaping error; both fixed before any runner started.

## 4. Honest limits
- Mutants are single-site text edits chosen by me; 100% detection (where reached) is not a proof that the checks are right, and the survivors above show where the choice of mutants found holes.
- Everything runs on one host in temporary copies with no ledger; the live behaviour of the CLI against a node is covered by other test files, not re-run here (the parent's full-suite run is separate).
- `deployBlock` is validated at both entry points only (pre-I/O). `binding_open.py`, which converts `deployBlock` with `int()` after the network step, is unchanged and not separately exercised with a float or overflow value.
- The three runners were run concurrently with other work on the same machine (load about 4 on 20 cores); no timeout or crash occurred (every non-detection above is `pass`).
- The runners and this README are not covered by any READY manifest yet.

## 5. SUPERSEDING RESULTS: the parent applied the seven gap-closing tests and re-ran everything (2026-11-07)

Sections 2 and the "prediction" sentence above describe the state BEFORE the additions. After this section's actions the gaps are closed and the runners were **re-run by the parent, not predicted**.

| Action | Result | File |
|---|---|---|
| The seven gap-closing tests (18 test cases) were appended to `tests/test_startup_refusals.py` (the self-import was dropped; `proposed-additions-...txt` stays as the record of the proposal) | `tests/test_startup_refusals.py` **182 passed**, exit 0 (was 164) | `PARENT-RERUN-test-startup-refusals-182-GREEN.txt` |
| `run_startup_config_mutants.py` (`python -B -I`, HEAD 67111f5 plus the fix) | exit 0, control passes, **19 / 19 detected, 0 equivalent survivors, 0 gaps** | `PARENT-RERUN-runner-startup-config-19of19.txt` |
| `run_adapter_v2_main_mutants.py` | exit 0, **31 / 31 detected**, 1 equivalent survivor (C25, run and survived) | `PARENT-RERUN-runner-adapter-cli-31of31.txt` |
| `run_witness_main_mutants.py` | exit 0, **39 / 39 detected**, 1 equivalent survivor (H35, run and survived) | `PARENT-RERUN-runner-witness-main-39of39.txt` |
| Full protocol suite BEFORE the 18 tests were appended (same tree otherwise) | **2611 passed, 201 skipped, 0 failed**, exit 0, 509 s (= the 2447 baseline + the 164 new tests). The 201 skips are only the documented out-of-scope schema cases; no Foundry skip | `PARENT-full-suite-before-the-18-added-tests-2611.txt` |
| `python -m hmbc_protocol.export --check` | exit 0, `exports match 9 files`; `exports/adapter.json` sha256 `7146495b..` unchanged | (read from the command) |
| E source inventory `sha256sum -c protocol/evidence/source-manifest.sha256` | exactly the three PRE-EXISTING mismatches (`worker.py`, `worker_log.py`, `testtools/deviating_witness.py`); this delta touches none of them | (read from the command) |

**The baseline discrepancy found on the way (kept):** at HEAD 67111f5 a first full run gave 2428 passed / 220 skipped, not the STATUS claim of 2391 / 201. The 19 extra skips were `test_rpc_binding_view_live.py`, which hard-codes `~/.local/share/hmbc-tools/foundry-1.8.5` and ignores `HMBC_FOUNDRY_DIR`, so on a host without that path
its live tests SKIP silently. With the verified Foundry linked into that path the file gives 19 passed, 0 skipped, so the combined baseline is **2447 passed, 201 skipped**. STATUS's 2391 was an older count (before slice 11a). Files: `PARENT-baseline-full-suite-HEAD-67111f5-live-skips.txt`, `PARENT-baseline-live-rpc-file-19-passed.txt`.
**Read the skip count, not only "passed".**

Still open (unchanged, stated plainly): `binding_open.py` converts `deployBlock` with `int()` after the network step and is not separately exercised with an overflow value (the entry points refuse it first); a startup defect that nobody anticipated ends in the generic `ADAPTER_UNAVAILABLE` closed refusal, which hides the cause by design; review is correlated (same model family as the fix).
