# Conflict-key bounded check: run record (agent 2, 2026-11-03)

Design check only (see model/PREDICTIONS.md for scope and for what a pass does NOT mean). Predictions file sha256
`cd7b2740be0a8a0a84b1c8eaa7125d45ee2630f821cd74c8a50c6a194ff79024` was fixed before the first run (2026-11-03T17:55:22Z) and was not edited afterwards.

| Run | Source | Command (from `protocol/f0/model`) | Exit | Wall | Output |
|---|---|---|---|---|---|
| 1 | `evidence/conflict_key_model.run1.py` sha256 `13ddf926..` | `python3 -I conflict_key_model.py` | 0 | 19.3 s | `evidence/model-run1-initial.json` sha256 `cccc53fb..` |
| 2 | `model/conflict_key_model.py` (see manifest) | same | 0 | 18.8 s | `evidence/model-run2-corrected.json` |

Interpreter: CPython 3.13.13 (`evidence/model-python-version.txt`). Standard library only. Host: single developer machine; no services.

## Outcome against the predictions

Run 1: **9 of 10 predictions held; P9 failed.** P9 (honest witness whose durable record is rolled back) predicted VIOLATED and the model said SAFE.
Cause: a model defect, not a property of the rule. The rollback transition cleared the witness's durable bitmask, and the violation check counted that
same bitmask, so signatures the witness had already emitted vanished from the certificate count. A signature stays valid after the signer forgets it.

Run 2 (source fixed: an append-only `emitted` bitmask counts certificates, the durable bitmask is what rollback wipes): **10 of 10 predictions hold.**
Only P9 changed; the verdict and the explored-state count of every other row is identical between the two runs (P1 9973, P2 105468, P3 56274, P4 19422,
P5 56274, P6 942533, P7 145, P8 345, P10 66042 states), which is the regression evidence that the fix touched only the rollback path.

| Id | Configuration | I1 (no two live certificates with different values) | Extra check |
|---|---|---|---|
| P1 | N0 no persistence, f=1 | VIOLATED (positive control) | |
| P2 | N1 permanent single-signing, f=1 | holds | stall reachable: 17820 of 25024 prefix states cannot recover |
| P3 | N2 wall-clock re-sign, skew 0 | holds | |
| P4 | N2 wall-clock re-sign, skew 1, f=1 | VIOLATED | |
| P5 | R-new (ledger-observed death), f=1 | holds | no stall: 25024 of 25024 prefix states recover |
| P6 | R-new, f=0 | holds | |
| P7 | R-new, f=2 | VIOLATED (outside the bound) | |
| P8 | R-new, q=2, f=1 | VIOLATED (mutant-f-q2) | |
| P9 | R-new, f=1, durable rollback | VIOLATED (assumption violation) | |
| P10 | R-new, f=1, ledger clock regression | VIOLATED (assumption violation) | |

Limits: two values, two expiries, six clock ticks, one key. Byzantine witnesses are worst case (pre-signed on everything) and proposals are adversarial
(any value to any witness), so honest validation is NOT modelled; the model isolates the single-signing/re-signing rule. Not TLC, not agent 3's model, not
the implementation, not a liveness proof under arbitrary delay. The recovery check is "after every old digest expired, can three honest witnesses agree on
a fresh digest", a one-step abstraction.
