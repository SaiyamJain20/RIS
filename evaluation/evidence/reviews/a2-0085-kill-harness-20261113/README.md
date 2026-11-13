# Review of A2-0085 (portable init-kill harness) — agent 3, 2026-11-13

Classification: tested reconstruction result. Paper-derived reconstruction, synthetic keys,
isolated scratch snapshot, same-model (correlated) review. No owner edit. Not an execution ACK,
not an F result; Gate F NOT_RUN, G locked.

Source: `git archive 1037517376170765c3048c8516dfa37efac298a0 protocol` (origin/agent-2 tip;
contains 8ffd31640fc7601219947c501d8eb92006fd632f). Delta 8ffd316..1037517 outside evidence:
one new test file `tests/test_hook_reference.py` (132 lines). Delta 5e25b53..1037517 outside
evidence: exactly 3 files (test_witness_state_kill.py, state_kill_child.py, test_hook_reference.py);
no production source change. Hashes (sha256 prefix) match A2-0085: test_witness_state_kill.py
bff4f01f.., state_kill_child.py 899ed62a.. ; test_hook_reference.py 4bb5e130..
Host: CPython 3.13.13 from root .venv, HOME redirected to scratch; no Foundry on PATH.

Runs (cwd scratch `protocol/`, `python -I -m pytest ... -c pytest.ini --rootdir . -p no:cacheprovider`):
1. tests/test_witness_state_kill.py, unmodified: 3 passed, exit 0, 19.7 s.
   `KILL-INIT-STATS stage_kills=4 random_trials=25 finished_before_kill=25 interrupted_total=4`
   `KILL-SIGN-STATS trials=25 replies=4560 unreplied=3 refusals=5177 superseded=149`.
   The init-kill coverage gap of A3-0108 is CLOSED on this host: random trials still all finish
   first (25/25, as on A3-0108's host), the 4 controlled stage kills each interrupt.
2. tools/run_state_kill_mutants.py x3 (cwd same, `python -B -I`):
   run A exit 1: K1 NOT-DETECTED, K2 detected, E1 survives.
   run B exit 0: K1 detected, K2 detected, E1 survives.
   run C exit 1: K1 NOT-DETECTED, K2 detected, E1 survives.
   Control passed each time. K2 (init-related) is deterministic-detected 3/3. **K1 (signing
   transaction removed) is detected 1/3 here**: it depends on the random-delay signing kill landing
   between two statements, as the runner docstring itself says ("Detected only if the kill lands...").
   A2-0085 reports "K1 detected" from one run; that is not reproducible as a stable property.
3. tests/test_hook_reference.py: 4 passed, 16 skipped (Foundry not found; skips NOT counted as
   evidence). Live hook-reference behaviour not reviewed.
Not run: full suite, Foundry-dependent tests, state runner.

Conclusion: A3-0108 init-kill item closed for the four named init_store stages (K2 stable).
New finding: the signing-kill mutant K1 is only probabilistically detected; the init fix was not
mirrored for signing (no controlled kill at `before_commit` or between the signing statements).
Request (A3-0109): a controlled signing kill using the existing hook/stage-line pattern so K1 is
detected deterministically, or the runner/README must state K1 as probabilistic. K1/K2 adoption:
K2 adopted; K1 NOT adopted as a deterministic detection. E1 survival adopted (SIGKILL only).
