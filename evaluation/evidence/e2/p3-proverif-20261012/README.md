# P3 ProVerif publication (A1-0078 D-P3-4)

Paper-derived HMBC2020 reconstruction; E/RQ1. Author: agent 3 (proxy), solo phase. **Correlated
self-review.** No services were started.

## Tool and inputs

| Item | sha256 |
|---|---|
| ProVerif 2.05, declared local build (`evaluation/host-tools.json`) at `~/.local/share/hmbc-tools/src-proverif/proverif2.05/proverif` | bc2cd5eddb8976fbab0194b6a10f6f05cf057287cf49dbbc97b37322b46af1cb |
| `evaluation/models/e/access.pv` | 1ca655061e9eb6d5717a919f554a6071eefdcf71b155a7a08f863464d64f01f8 |
| `evaluation/models/e/access_mutant.pv` | 1c6e1acc6346d9f3859180f76f2a7a5e679477d3a61c4a132eefa46da1775537 |
| `evaluation/models/e/README.md` (expectations) | 97040ff004613daccd0448dea34a8bf5706121a2c260cc26ccc7cf6fd4a859d6 |

Each model was run with `<proverif> evaluation/models/e/<model>.pv` from the repository root.

## Results

| Model | Exit | Wall | RESULT verdicts | README expectation | A3-0033 saved output |
|---|---|---|---|---|---|
| `access.pv` | 0 | 0.014 s | user agreement **true**; witness agreement **true**; witness with the approved destination **true**; `not event(AllowedGrant)` **false** (a legitimate grant is reachable); `not event(DeniedGrant)` **true** (a denied grant is unreachable) | matches | RESULT lines equal; the full output is byte-identical to `formal-and-hook-review-20261009/positive-final.stdout` |
| `access_mutant.pv` | 0 | 0.015 s | user agreement **false**; witness agreement **false** (destination-substitution counterexamples); the remaining-field query (approved destination) **true**; reachability unchanged (**false** / **true**) | matches | RESULT lines equal; the full output is byte-identical to `mutant-final.stdout` |

Stderr is empty for both runs. These verdicts agree with agent 1's re-run in A1-0078 D-P3-4.

## Files

- `access.stdout`, `access.stderr`, `access.run.json`;
- `access_mutant.stdout`, `access_mutant.stderr`, `access_mutant.run.json`;
- `summary.json`, which records argv, exit codes, wall times, hashes, the RESULT lines and the comparisons.

The `wallSeconds` values in the `.run.json` files came from a shell wrapper whose `bc` output lacked
a leading zero. I added the zero in place; the numbers are unchanged.

## Scope

- The model is a symbolic abstraction of the access flow. It is not the deployed ledger, and it is
  not a computational proof.
- The mutant model is the evidence for destination-binding detection (A1-0078 D-P3-2, item 2). It
  does not replace the paused live mutant matrix (A1-0079).
