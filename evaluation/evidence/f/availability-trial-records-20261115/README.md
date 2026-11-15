# M2 virtual availability sweep — per-trial records, 2026-11-15

**Classification:** tested reconstruction result from an offline virtual-transport experiment.
This is not an integrated F case, execution FREEZE, or Gate F result. Synthetic keys and local
durable witness stores are used. No service, Anvil process, network endpoint, integrated case, or
test suite was started.

## Method and source

Re-ran Agent 3's M2 runner with per-trial output enabled against the same historical protocol
snapshot used by the prior M2 aggregate: commit `55f180e15d73825870d3326a3edb817824b3f265`,
protocol subtree `4822552dee489c2da72910b68d0a0b1ed7b64114`. The modified runner preserves the
existing aggregate fields and additionally records one row for each of the five runs per muted
subset. Each trial row includes muted witness indexes, trial number, certificate outcome, virtual
finish time, signature count, and host wall duration. The duration is execution metadata only and
is not interpreted as network availability.

The runner constructs four witness objects with temporary SQLite stores and real EIP-712
signatures, then uses `VirtualTransport`. Virtual milliseconds are scheduled transport time, not
wall-clock or network latency. The delay-order control remains a separate single run.

Commands:

```sh
git archive 55f180e protocol | tar -x -C "$scratch"
.venv/bin/python -I evaluation/measurements/availability_sweep.py \
  "$scratch/protocol" evaluation/evidence/f/availability-trial-records-20261115/availability.json \
  --runs 5
.venv/bin/python -I evaluation/evidence/f/availability-trial-records-20261115/compare_trials.py \
  evaluation/evidence/f/availability-trial-records-20261115/availability.json \
  evaluation/evidence/f/availability-reproduction-20261115/availability.json
```

Environment: Python 3.13.13; root `uv.lock` SHA-256
`1fb4777a5d4078434af8e7fe4a88f2f3afbe1d8f65d30e8a182999d7a7a29cbe`; eth-account 0.14.0,
eth-abi 6.0.0, eth-utils 6.0.0, eth-keys 0.8.0, eth-hash 0.8.0, hexbytes 2.0.0, rlp 5.0.0,
pycryptodome 3.24.0.

## Result

Both commands exit 0. The JSON contains all 16 muted-witness subsets and 80 individual trial
records. The checker confirms five consecutively numbered trials per subset, consistency between
individual records and aggregate outcome fields, and equality of aggregate outcome, virtual-time,
signature-count, and run-count fields with the prior M2 aggregate. The delayed-reply control also
matches at 300 virtual ms with three signatures.

Outcomes: zero or one muted witness yields three signatures at virtual time 0 ms in every run;
every subset with two through four muted witnesses yields no certificate by the 10,000 ms virtual
deadline. Delays 400/300/200/100 ms yield a certificate from three signers at 300 virtual ms.
This bounds only the tested virtual schedules; it does not establish general liveness or real-network
timing. Per-trial rows improve auditability of this reproduction but remain output from the same
runner and are not independent observations.

## Retained artifact hashes

See `SHA256SUMS` for the runner, source pin, commands, comparison script, and outputs. SHA-256 of
this README is recorded by the parent report packet after publication.
