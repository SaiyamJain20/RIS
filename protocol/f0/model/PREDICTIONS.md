# Predictions for the conflict-key bounded check (written BEFORE the model was run)

Author: agent 2, 2026-11-03. Status: F0 planning evidence, **design check only**. This is a small explicit-state exploration of
one conflict key, not agent 3's TLA+ model (C-F1), not a measured implementation and not a consensus claim. Agent 3's TLC model must
state the same lifetime rule; neither has been run against the other.

## What is modelled

One conflict key K (one governance nonce, checkpoint sequence or request digest). Four witnesses, q = 3. A digest is `(value, expiry)`
with value in {A, B} and expiry from a small set. The ledger clock `t` only moves forward (except in the two assumption-violation controls).
Honest witnesses keep a durable set of digests they signed for K and a monotone observation `o <= t` of the target ledger clock (it may
be stale). Byzantine witnesses are worst case: they have signed every digest. A certificate is *formed* when >= q witnesses signed the
digest, and *live* while `t < expiry`.

Property I1 (agreement over simultaneously live values): in no reachable state are two formed, live certificates for different values present.

Signing rules compared:

| Rule | Honest witness may sign (v, e) for K when |
|---|---|
| N0 | always (no persistence) |
| N1 | every digest it signed earlier has the same value v (permanent single-signing per value) |
| R-new | every digest it signed earlier with a different value has expiry <= o (dead by the witness's own ledger observation o), and o < e |
| N2 | like R-new but o is a LOCAL clock that may run ahead of the ledger clock by up to s (wall-clock re-signing) |

## Predictions (each is a claim the run can falsify)

| # | Run | Predicted result |
|---|---|---|
| P1 | N0, f = 1 | I1 VIOLATED (positive control: the checker can find a violation) |
| P2 | N1, f = 1 | I1 holds; AND a stall is reachable: two honest witnesses signed A, the third signed B, so no later proposal can gather three honest signatures even after every old digest expired |
| P3 | N2 with s = 0 | I1 holds (identical to R-new when the local clock never runs ahead) |
| P4 | N2 with s = 1, f = 1 | I1 VIOLATED (a local clock one tick ahead lets an honest witness sign B while A is still live) |
| P5 | R-new, f = 1 | I1 holds; no stall: after all old digests expired the three honest witnesses can always agree on a fresh digest |
| P6 | R-new, f = 0 (four honest) | I1 holds |
| P7 | R-new, f = 2 | I1 VIOLATED (outside the fault bound; matches matrix row F-17) |
| P8 | q = 2 (configuration mutant), R-new, f = 1 | I1 VIOLATED (matches matrix row F-18) |
| P9 | R-new, f = 1, plus one honest witness whose durable record is rolled back | I1 VIOLATED (durable-state assumption, matrix rows F-27 / FM-14) |
| P10 | R-new, f = 1, plus one ledger clock regression | I1 VIOLATED (the monotone-clock assumption is load-bearing; the proposed tripwire refuses instead) |

If any prediction fails, that is a finding about the rule or the model and is reported as such; the prediction is not edited afterwards.
A passing P5 means only: in this bounded abstraction (2 values, 2 expiries, 6 ticks) the re-signing rule keeps I1. It is not a proof for the
real protocol and says nothing about validation, delivery, cryptography or the ledger code.
