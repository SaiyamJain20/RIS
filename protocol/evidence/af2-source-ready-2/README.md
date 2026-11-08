# Agent 2 delta source READY (A2-0064): published-schema output validation

Source commit `c138185428ebe572c86cdc42985b340a262aa8aa` (agent-2). Full manifest of `protocol/` at that commit: `MANIFEST.sha256` (408 files; sha256 `016ffd0870e3b9bfd2b8b297c8c977bcfe29ce687d0a54b548b901c52e8b9cbf`; it includes the A2-0063 evidence directory and excludes this one). Relative to the A2-0063 source commit `dbae4e1e13fb26984a6d4b0aa042ae321c1c49f0` exactly FOUR non-evidence paths changed:

| Path | Change | sha256 (first 16) at c138185 |
|---|---|---|
| `protocol/hmbc_protocol/adapter_v2.py` | modified: `Context(..., check_responses=True)`, `Context.checked`, `RESPONSE_TYPE`, response validators built once, `published_format_checker()`, `handle_line` returns `ctx.checked(op, response)` | 15c03252f80350c1 |
| `protocol/tests/test_adapter_v2.py` | modified: the stub-handler helper passes `check_responses=False` | 077764f75f329865 |
| `protocol/tests/test_adapter_v2_output.py` | NEW, 19 tests | 60c24bf27451ed7e |
| `protocol/tools/run_adapter_v2_mutants.py` | modified: 16 new mutants, new test file included, two anchors repaired, A59 recorded equivalent | cbe1bed672cbf2ca |

Everything else under the A2-0063 manifest is byte-identical (the other 24 changed paths are evidence documents). The E-listed source manifest still has exactly two intended mismatches (`worker_log.py`, `deviating_witness.py`); `adapter_v2.py` is not E-listed.

Commands (from `/home/karma/Documents/RIS-agent-2`, same venv and versions as `../af2-source-ready/README.md`, UTC 2026-11-06):

| Command | Exit | Result |
|---|---|---|
| `python -B -m pytest -q -c protocol/pytest.ini --rootdir protocol -p no:cacheprovider protocol/tests -rs` | 0 | 2245 passed, 201 skipped (the same out-of-scope schema-review cases), 364 s (`../af2-state/full-suite-after-6d.txt`) |
| `PYTHONPATH=protocol python -B -m hmbc_protocol.export --check` | 0 | `exports match 9 files` |
| the five runners affected by the change (adapter_v2 58/58, ops 14/14, witness 57/57, start 15/15, Byzantine 20/20), `mutants/_exits.txt` | all 0 | every mutant detected, equivalents recorded |

The other eight runners test modules this change does not touch and are NOT rerun for this delta; their A2-0063 outputs stand for their unchanged files.

Failed trials kept: red run `../af2-state/adapter-v2-output-run1-red.txt` (10 failed), mutation run 1 at 51/54 and run 2 at 58/59 (`../af2-state/adapter-v2-output-mutants-run1-51-of-54.txt`, `...-run2-58-of-59.txt`), and eight older stub tests that failed until `check_responses=False` was added. Findings and limits: `../af2-state/README.md` section 6d. Limits unchanged from A2-0063 (no command line or real wiring; one shared fake view; same-model review, correlated); additionally the output check is only as strong as the published schema plus the registered formats: `user-key-ref` and `evidence-path` stay annotations.
