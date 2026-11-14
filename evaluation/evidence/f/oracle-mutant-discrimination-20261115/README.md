# Fault-oracle mutation discrimination — 2026-11-15

**Classification:** tested paper-derived reconstruction result on synthetic
fixtures. This is oracle sensitivity evidence, not a Gate F case or an
implementation security result.

## Result

Using the accepted protocol source at `origin/agent-2` commit
`73fb2ce42d513ad3faf384500609e76d54aedbfb` (protocol subtree
`7566f63d693afe8fa88ab7cc69872082d58d88db`), the unmutated oracle agrees with
the SQLite `WitnessStore` on **180/180** grid rows (142 accepts, 38 refusals,
zero disagreements). Each deliberate oracle mutation produced disagreements
with the unchanged store, and all seven counts match the 2026-11-14 receipt:

| Deliberate oracle mutation | Disagreements / 180 |
|---|---:|
| Expiry `>=` changed to `>` | 20 |
| Executed receipt never dies | 18 |
| Decision sequence `>` changed to `>=` | 6 |
| Drop ALLOW grant death | 4 |
| Let grant kill a DENY | 4 |
| Checkpoint sequence `>=` changed to `>` | 4 |
| Governance nonce `>=` changed to `>` | 4 |

The harness monkey-patches only the imported oracle predicate for each trial;
the protocol source and `faults.py` remain unchanged. Each trial reruns the same
180-case differential with fresh temporary SQLite stores. The baseline output,
seven-control summary, command, stdout and hashes are retained here.

## Limits

Same-model oracle and store; synthetic keys/observations; one earlier digest per
key. Grant and executed-receipt death facts are caller-asserted by the store
interface. No native ledger reachability, quorum, process transcript, or
integrated F case is evaluated. This establishes that these seven simplified
rule errors are discriminated by this grid; it does not establish completeness
of the oracle or validate a production implementation.

See `command.txt`, `hashes.txt`, `results.json`,
`results.baseline.json`, and `stdout.txt` for the reproduction record.
