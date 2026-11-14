# K1 detection made deterministic: kill points between the signing statements (S2-0025, proxy-2 for absent agent 2, 2026-11-14)

PAPER-DERIVED RECONSTRUCTION. TEST-ONLY hooks and synthetic TEST-ONLY keys; one host (agent 1's machine, Linux, CPython 3.13.5 `.venv`, Foundry 1.8.5). This was written by proxy-2 (A1-0130), the same model as agent 1 and agent 3: correlated self-review, not agent 2's work and not agent 2's confirmation. It answers A3-0110 and A3-0122: K1 was detected in 29 of 40 runs on agent 3's host.

## The change (delta against origin/agent-2 9d44754, four files under `protocol/`)

| Path | sha256 at 9d44754 → now | What |
|---|---|---|
| `hmbc_protocol/witness_state.py` | c6184a61.. → 1a8787993df29ef379c366b181b823ca0a672f5ad7c48d7736c9c3b495d2fdbc | Two inert hook calls in `_sign_in_txn`: `self._hook("after_pin")` after the conflict INSERT block and before `signer(digest)`; `self._hook("after_digest")` after the digests INSERT and before the observed INSERT. `self._hook` is `lambda p: None` unless a `crash_hook` is passed (`:311`); the production entry passes none. `testtools/faulty_witness.py` fires only on `before_commit`/`after_commit` (its `POINTS`), so the F alternate entry is unaffected. |
| `tests/state_kill_child.py` | → ad59580ff02229eda7840f640be44dec819b5d20680dbae114b43f723d86f92b | New mode `sign-pause`: the hook prints STAGE lines and BLOCKS at the n-th occurrence of a named point (optionally only inside a superseding transaction) until the parent SIGKILLs it. |
| `tests/test_witness_state_kill.py` | → 16888a370303b333221a93f07cf7f99c35bedc800c0025344798fe7b9e30244d | New `test_kill_between_the_signing_statements_leaves_a_whole_record`: 3 kills (after_pin #1, after_digest #1, after_pin inside a supersede). It asserts that the stored digests equal the replies, the superseded count is unchanged, the supersede is non-vacuous, and `violations()` I1-I4 is empty. Existing tests unchanged. |
| `tools/run_state_kill_mutants.py` | → 90b9f07236d8638e10794a5c93b5a5ab7931655d64eb460135b66a0b9f3eacf6 | Docstring of K1 only; anchors unchanged. |

Why a production hook and not a probabilistic statement: the point between two statements of one transaction cannot be reached from outside the process. The existing stage lines print after the writes are issued (A3-0110's diagnosis). The hook follows the existing `init_store` and `before_commit`/`after_commit` pattern and is inert without a test-supplied callable.

## Results (all on this host; drivers in `drivers/`, outputs in `outputs/`)

Each trial runs one node id N times in a minimal copy laid out as `run_state_kill_mutants.py` lays it out, with that runner's own K1 edits (`drivers/k1_trials.py.txt`). K1 witness_state sha256: 9336b225.. on the base and 093acb7c.. on the new bytes.

| Step | Command (repo root unless stated) | Exit | Result | Output |
|---|---|---|---|---|
| RED 1 | `k1_trials.py <git archive 9d44754 protocol> k1 40 tests/test_witness_state_kill.py::test_kill_inside_the_signing_transaction_leaves_a_whole_record` | 0 | **K1 detected 1 of 40** (39 pass). Agent 3: 29/40. Control 40/40 pass | `RED-1-*.json` |
| RED 2 | the new test before the hook existed | 1 | "the child never reached store point 'after_pin'" | `RED-2-*.txt` |
| failed trial 1 | the new test, first run | 1 | `I3 a stored digest was never requested`: my test deduplicated repeated requests. Fixed to count REPLY/REFUSED lines | `failed-trial-1-*.txt` |
| failed trial 2 | the new test, second run | 1 | a misworded assertion, `AssertionError: True` (removed) | `failed-trial-2-*.txt` |
| GREEN | `drivers/green.sh.txt` on a snapshot equal to the working tree | 0 | new test with K1: **detected 40 of 40** (every run fails at case `after_pin-1`, "I3 a pin without a live digest"); control **40 of 40 pass** | `GREEN-new-test-*.json` |
| GREEN runner | `python -B -I tools/run_state_kill_mutants.py` ×5 on that snapshot | 0 ×5 | control pass; K1 DETECTED (2 failed tests each run); K2 DETECTED; E1 survives (argued equivalent); 132-136 s | `GREEN-run_state_kill_mutants-run{1..5}.txt` |
| PROBE | `drivers/percase.sh.txt`: each of the 3 cases ALONE, K1 ×5 and control ×5 | 0 | case0 after_pin: K1 5/5 ("I3 a pin without a live digest"); case1 after_digest: K1 5/5 ("left 1 record(s)"); case2 supersede: K1 5/5 ("a supersede of the killed request survived it (0 -> 1)"); control 5/5 pass for each. The docstring's "every case fails" holds | `PROBE-case*.json` |

Behaviour-neutral proof on the final working-tree bytes (`drivers/neutral.sh.txt`; hashes equal at start and end):

| Command | Exit | Result | Output |
|---|---|---|---|
| pytest: `tests/test_witness_state{,_cli,_lock,_hot_journal,_kill}.py` | 0 | 81 passed, 0 skipped | `NEUTRAL-state-tests-81-passed.txt` |
| pytest: 14 witness, service, pool, faulty-witness, mutant-tree and process files (list in the driver; live ones on ports 19545-19599) | 0 | 459 passed, 0 skipped | `NEUTRAL-witness-pool-tests-459-passed.txt` |
| `python -B -I protocol/tools/run_state_mutants.py` | 0 | detected 42 of 42 | `NEUTRAL-run_state_mutants-42-of-42.txt` |
| `python -B -I protocol/tools/run_state_kill_mutants.py` | 0 | control pass, K1 and K2 DETECTED, E1 survives | `NEUTRAL-run_state_kill_mutants-working-tree.txt` |
| `python -B -I protocol/tools/run_mutant_tree_mutants.py` (registry M1-M3 edit `witness_state.py`) | 0 | detected 7 of 7 | `NEUTRAL-run_mutant_tree_mutants-7-of-7.txt` |
| `drivers/anchors.py.txt`: every `witness_state.py` anchor of `run_witness_hooks_mutants.py` (W1-W6, live-only, NOT run) and `testtools/mutant_tree.py` | 0 | 10 of 10 match exactly once | `other-runner-witness_state-anchors-10-of-10.txt` |
| `sha256sum -c protocol/evidence/source-manifest.sha256` (the E-listed check) | 1 (expected) | 139 OK, exactly 3 FAILED (worker_log.py, worker.py, deviating_witness.py, as before); `witness_state.py` is not E-listed | `E-listed-check-139-OK-3-FAILED.txt` |
| `sha256sum -c protocol/f0/MANIFEST.sha256` | 0 | 52 OK | `F0-manifest-check-52-OK.txt` |
| `PYTHONPATH=protocol python -B -m hmbc_protocol.export --check` | 0 | "exports match 9 files" | `export-check.txt` |

Full protocol suite, run once in the background on the same bytes (`drivers/fullsuite.sh.txt`):
`.venv/bin/python -m pytest protocol/tests -c protocol/pytest.ini --rootdir protocol -p no:cacheprovider -rs -q`, with Foundry 1.8.5 on PATH, `HMBC_FOUNDRY_DIR` set and `HMBC_TEST_PORT_RANGE=19545-19599`.
- Result: **exit 0, 3226 passed, 201 skipped, 1571 s.**
- Skips: exactly 200 ScenarioResult ("not agent-2's scope") and 1 FileHash.
- Hashes of the four files were equal at start and end.
- Outputs: `FULL-SUITE-3226-passed-201-skipped.txt` and `FULL-SUITE-exit-and-versions.txt` (Python 3.13.5, forge and anvil 1.8.5).
- Disclosure: `tests/test_rpc_binding_view_live.py` binds OS-chosen ephemeral ports (kernel range 32768-60999, recorded), per agent 1's 2026-11-14 ruling. The test was not edited.

## Limits

- **One host.** K1 is deterministic here (40/40, plus 5/5 per case). Agent 3's host has not run it. The kill is now controlled (the child blocks at the point until the SIGKILL), so the host's speed should not matter, but that is an argument, not a measurement on agent 3's host.
- **SIGKILL only.** E1 (`synchronous=OFF`) still survives by design: power loss is not measured.
- **Production source changed.** `witness_state.py` gains two calls that are no-ops in production. `run_witness_hooks_mutants.py --live` (W1-W6) was not rerun. Its anchors were checked by text only.
- **Earlier failed trials kept.** The failed trials of agent 2's earlier stage-kill work stay in `../af2-kill-portable/`.
