# M2 virtual availability sweep — fresh reproduction, 2026-11-15

**Classification:** tested reconstruction result from an offline virtual-transport experiment.
This is not an integrated F case, execution FREEZE, or Gate F result. Synthetic keys and local
durable witness stores are used. No service, Anvil process, network endpoint, or integrated case
was started.

## Method and source

Re-ran the existing Agent-3 M2 runner against the exact historical protocol snapshot used by the
original measurement: commit `55f180e15d73825870d3326a3edb817824b3f265`, protocol subtree
`4822552dee489c2da72910b68d0a0b1ed7b64114`. The runner constructs four witness objects with
temporary SQLite stores and real EIP-712 signatures, then uses `VirtualTransport`; virtual
milliseconds are scheduled transport time, not wall-clock or network latency.

Command:

```sh
git archive 55f180e protocol | tar -x -C "$scratch"
.venv/bin/python -I evaluation/measurements/availability_sweep.py \
  "$scratch/protocol" evaluation/evidence/f/availability-reproduction-20261115/availability.json \
  --runs 5
```

Environment: Python 3.13.13; root `uv.lock` SHA-256
`1fb4777a5d4078434af8e7fe4a88f2f3afbe1d8f65d30e8a182999d7a7a29cbe`; eth-account 0.14.0,
eth-abi 6.0.0, eth-utils 6.0.0, eth-keys 0.8.0, eth-hash 0.8.0, hexbytes 2.0.0, rlp 5.0.0,
pycryptodome 3.24.0. The exact source pin, command record, stdout/stderr, exit code and hashes are
retained in this directory.

## Result

Exit 0. The fresh run covers 16 muted-witness subsets, five runs per subset (80 total), plus the
separate reply-delay ordering control. All compared outcome fields match the retained aggregate
JSON: success set, virtual finish time, signature count and run count for every subset; the delayed
control also matches at 300 virtual ms with three signatures. Host wall-time medians/maxima differ
from the earlier run and are not treated as a result. The captured runner output remains one
aggregate row per subset, not an individual record for each of the 80 trials.

For the schedule result: 0 or 1 muted witness yields three signatures at virtual time 0 ms; every
subset with 2–4 muted witnesses yields no certificate by the 10,000 ms virtual deadline. Delays
400/300/200/100 ms yield a certificate from three signers at 300 virtual ms. This bounds only the
tested virtual schedules; it does not establish general liveness or real-network timing.

## Retained artifact hashes

| Artifact | SHA-256 |
|---|---|
| M2 runner `evaluation/measurements/availability_sweep.py` | `5e6ab7e7a8a0ba2e9d162dc7bc434b62aa577a7a2b9c3d18d072d2d168d668c4` |
| prior aggregate input `measurements-20261114/availability.json` | `45ddc99d907be0c88f760b97f91f69a6b95b3f3a9c12e4d8f97f5895c402c692` |
| fresh aggregate `availability.json` | `83b207ef8267144ed5d276958cb9449bb5a00dc7181208100b29b73c34ad6cbc` |
| fresh stdout | `7999c83ee14aa569418d74e21bb7507b91429a8463f1bafef96d7ab0cf5bd54c` |
| fresh stderr (empty) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `source-pin.txt` | recorded in `SHA256SUMS` |

The result repeats the prior M2 aggregate for outcome fields; it does not repair the runner's
missing per-trial output. It remains isolated virtual-transport evidence and must not be presented
as any of the 32 F case results or as Gate F evidence.
