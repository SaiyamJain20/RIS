# Byzantine pool sweep reproduction — 2026-11-15

**Classification:** tested paper-derived reconstruction result on synthetic
fixtures. This virtual pool-model sweep is not a Gate F case, a consensus
measurement, or a result about the HMBC authors' implementation.

## Exact source and reproduction

Re-ran `evaluation/measurements/byzantine_sweep.py` against an archive of
Agent 2 source commit `55f180e15d73825870d3326a3edb817824b3f265`, protocol tree
`4822552dee489c2da72910b68d0a0b1ed7b64114`. Command exited 0 in 8 seconds on
CPython 3.13.13 with `eth-account 0.14.0`, `eth-abi 6.0.0`, and `eth-utils 6.0.0`.
The full command and hashes are in `command.txt` and `hashes.txt`.

The newly produced `byzantine.json` is **byte-identical** to the retained
2026-11-14 result (`cmp` exit 0; SHA-256
`2e0655199163c6f94f6ea5ede6b4ba2c1c3182cd8efdb7fd3a5a99cf3bf523af`). The
baseline/control results are:

| Bound | Cases | Certificates | No certificate | Invalid certificates | Potential agreement-hazard cases |
|---|---:|---:|---:|---:|---:|
| `f=1` | 972 | 180 | 792 | 0 | 0 |
| `f=2` control | 4,374 | 330 | 4,044 | 0 | 2,916 |

The f=2 row is deliberately outside the stated f=1 bound. A hazard means two
different values could each gather at least three signers after the run,
counting honest witnesses whose model store holds that value plus all Byzantine
witnesses. It is a potential, not two realized conflicting certificates. The
f=1 control retains zero potential-hazard cases. All accepted certificates in
both rows have three distinct, sorted, valid signers.

## Limits

Honest witnesses are Agent 2's pool/signing-rule **model**, not its durable
SQLite store. Real EIP-712 signatures are checked, but the witness state and
virtual transport remain modeled. The sweep covers one fixture family and
enumerated behaviors/pin patterns; it is not liveness, production process,
native-ledger, or consensus evidence. The same-model correlation remains.

See `byzantine.json`, `stdout.txt`, `command.txt`, and `hashes.txt` for the raw
result and reproduction record.
