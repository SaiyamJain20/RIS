# F execution plan DRAFT — agent 3, 2026-11-14

DRAFT. Authorizes nothing: no service, no integrated run, no FREEZE. Gate F NOT_RUN; all 32 cases NOT_RUN;
G locked. This is my proposal after the E gate precedent (`evidence/e3/gate-plan-20261012`) and the merged
case coverage map (`case-coverage-map-20261114`). Grouping into families is a planning choice, not a protocol result.

`plan-draft.json` holds the machine-readable form: pins, six case families (8+6+4+8+3+3 = 32, each case once),
stages, preconditions and non-goals. Key points:
- Ledger pin is 85c59f5, not the e4e992f named in f_matrix.json (A1-0127; matrix not edited).
- The protocol pin is NOT final: candidate 55f180e, blocked on K1 (A3-0110, ~72% per-run detection, not
  deterministic) and on agent 2 confirming the signing-rule reading (A3-0121). Agent 2 has been silent since A2-0086.
- Family B uses the fault oracle (`oracles/faults.py`); the oracle needs signing-time observations that current
  captures do not all carry. That gap must be closed by the runner before family B can produce verdicts.
- F-25 and F-26 are residual-inventory analysis items and are NOT_EXECUTED by design; F-17, F-18, F-24, F-19 are
  outside-bound or mutation cases and are expected to show violations or trust assumptions, reported as such.
- Stages mirror the E gate: verify pins, source bracket, isolated baselines as controls, per-family integrated runs
  with positive controls first, result classification, post bracket, manifest and E regression, then RQ2-F.md.
Next real work: runner skeleton test-first in evaluation/** (stage 1-2 first), then family A against the existing
real-process live tests as its reference. Honest size: the runner and six families are the bulk of F.
