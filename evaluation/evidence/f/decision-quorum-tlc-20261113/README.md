# DecisionQuorum TLC results — agent 3, 2026-11-13

Tested reconstruction result on a finite model; NOT a proof of production consensus. TLC 2.19
(rev 5a47802), OpenJDK 21.0.11, tla2tools.jar sha256 936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88
(path ~/.local/share/hmbc-tools/tlaplus-v1.7.4/). Run from repo root with `-metadir` in scratch;
command `java -cp <jar> tlc2.TLC -metadir <scratch> -config evaluation/models/f/<cfg> evaluation/models/f/DecisionQuorum.tla`.
Authorization: the human invoked the same command by hand (placeholder error) and this session then ran it.

Final run (`final/*.log.gz`), CHECK_DEADLOCK FALSE in every cfg:
| config | exit | result | generated/distinct |
|---|---|---|---|
| DecisionQuorum (f=1,Q=3,persist) | 0 | no error, search complete, depth 6 | 433/108 |
| -f0 (f=0,Q=3) | 0 | no error | 217/81 |
| -weak-q2 (f=1,Q=2) | 12 | Agreement violated | 202/78 (stopped at violation) |
| -f2 (f=2,Q=3) | 12 | Agreement violated | 679/142 (stopped) |
| -no-persist (f=0,Q=3,no persistence) | 12 | Agreement violated | 1344/226 (stopped) |
All five equal the predictions in README. Counterexample traces are in the logs. The f=2 trace is
conditional on two Byzantine witnesses (f=2 > 1, outside the fault bound), not a measured break of Anvil consensus.

First run (`first-run-with-deadlock/`, retained): f0 exited 11 "Deadlock reached": a defect of my
model (no step after every honest witness signs), not a quorum result. Fixed by adding
CHECK_DEADLOCK FALSE to the cfgs (model text unchanged); all verdicts above come from the rerun.
The "two states had the same fingerprint" lines are TLC's standard probability estimate (1.9E-15).
Model file hashes: model-hashes.txt (cfgs hashed after the edit).
Not covered: liveness/delivery, key custody, real signing rules, integrated availability schedules.

Follow-up (A1-0121 review, agent 1): its independent enumeration gives 108/81/108/144/256 reachable
states; TLC agrees where runs complete (108, 81). Its f0-deadlock finding matches the defect found in
my first run (fixed via CHECK_DEADLOCK FALSE; agent 1 preferred a stuttering disjunct, equivalent for
these configs). Its wording nit was applied (comment/README only; the .tla was rerun on the f=1
config afterwards: no error, 433/108). model-hashes.txt refreshed. Agent 1 reviewed pre-run text and
did not run TLC; its review is correlated same-model.
