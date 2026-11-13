# C-F1 finite model: DecisionQuorum (agent 3)

Status: TLC RUN 2026-11-13, all five outcomes match the predictions below; see evaluation/evidence/f/decision-quorum-tlc-20261113/README.md. (Originally written as text only after an earlier blocked run.) The earlier TLC smoke run was denied by the
session's permission classifier (downloaded jar) and is not retried or rewrapped. Paper-derived reconstruction, synthetic, same-model author.

Files: `DecisionQuorum.tla` and five configs. Expected outcomes are PREDICTIONS to be checked, not results:

| config | Byz | Q | Persist | prediction |
|---|---|---|---|---|
| `DecisionQuorum.cfg` | {w1} | 3 | TRUE | Agreement holds (positive control, f=1) |
| `-f0.cfg` | {} | 3 | TRUE | holds |
| `-weak-q2.cfg` | {w1} | 2 | TRUE | Agreement violated (two disjoint size-2 sets; the overlap ASSUME holds trivially since 2Q-N=0) |
| `-f2.cfg` | {w1,w2} | 3 | TRUE | Agreement violated (both Byzantine sign both values, one honest each side); conditional on two Byzantine witnesses (f=2 > 1, outside the fault bound); not a measured chain break |
| `-no-persist.cfg` | {} | 3 | FALSE | Agreement violated even at f=0 (honest double-signing; control for the persistence rule); HonestSingle holds vacuously |

Run by a human or an authorized session (I did not): 
`java -cp ~/.local/share/hmbc-tools/tlaplus-v1.7.4/tla2tools.jar tlc2.TLC -config evaluation/models/f/<cfg> evaluation/models/f/DecisionQuorum.tla`
(run from repository root; record jar sha256 and state counts).

Not modeled: delivery, timeouts/liveness, key custody, governance, the real signing rules, expiry. The
integrated availability schedules and the arbitrary-delay vs eventual-delivery distinction remain
in the F runner work (not started).
