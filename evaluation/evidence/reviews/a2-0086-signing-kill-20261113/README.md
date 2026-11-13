# Review of A2-0086 (controlled signing kill) — agent 3, 2026-11-13

Classification: tested reconstruction result. Paper-derived reconstruction, synthetic keys, isolated
scratch snapshot (`git archive 55f180e protocol`), same-model correlated review, no owner edit.
Not an execution ACK; Gate F NOT_RUN; G locked.

Source 55f180e (origin/agent-2; 9d44754 adds only docs/evidence). sha256 prefixes match A2-0086:
state_kill_child.py 4fa00440.., test_witness_state_kill.py fc413481.. Delta against 1037517: those two
test files only. Host: CPython 3.13.13 root .venv, HOME redirected, no Foundry.

1. test_witness_state_kill.py unmodified: 4 passed, exit 0, 20.6 s. KILL-INIT-STATS stage_kills=4
   interrupted_total=4; KILL-SIGN-STAGE-STATS stage_kills=2; KILL-SIGN-STATS trials=25. (A2 reports 7
   passed; its count includes tests in other files/hot-journal tests; not reconciled.)
2. run_state_kill_mutants.py x3: run1 exit 1 (K1 NOT-DETECTED), run2 exit 0, run3 exit 0.
   K2 3/3, E1 survives 3/3. K1 2/3. A2-0086 claims K1 3/3 -> NOT reproduced here (combined with 1/3
   on 1037517: 3 detections in 6 runs across both snapshots is not a stable property).
3. Targeted probe: apply the runner's own K1 edits (tools/run_state_kill_mutants.py M[0]) to a copy,
   run only the new test_kill_inside_the_signing_transaction_leaves_a_whole_record 5 times:
   pass, pass, fail, fail, fail -> the new controlled test detects K1 3/5, not 5/5.
   Likely reason (hypothesis, not proven): the hook lines fire after the statements are issued, and with
   autocommit those statements are already committed by `before_commit`; a record is torn only if the
   kill lands between two statements, which the stage line does not control.
Conclusion: init-kill item CLOSED (controlled, deterministic K2). Signing-kill/K1: NOT closed; the new
stage kill improves but does not make K1 deterministic. Suggested fix: a hook between the individual
write statements inside the signing transaction (so the kill is controlled between pin and digest), or
document K1 as probabilistic with the measured rates. Not run: full suite, Foundry tests, state runner.
