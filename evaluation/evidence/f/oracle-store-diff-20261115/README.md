# Fresh oracle/store differential — A3-0133, 2026-11-15

**Classification:** tested paper-derived reconstruction result on synthetic
fixtures. This is an offline differential, not an integrated RQ2-F case, a
Gate-F result, or evidence about the HMBC authors' implementation.

## Result

Re-ran `evaluation/measurements/oracle_store_diff.py` against the exact protocol
archive from candidate `37ca31c80ab9a81956647428435addb1802cb370` (protocol tree
`7566f63d693afe8fa88ab7cc69872082d58d88db`). Result: **180/180 oracle/store
decisions agree**, with 142 store accepts, 38 `CONFLICT_PINNED` refusals, zero
disagreements. This run covers the same four signing kinds and observation grid
described in the 2026-11-14 evidence. It freshly reproduces the primary
differential only; the seven deliberate-oracle-mutant discrimination checks
remain supported by the earlier receipt and were not run again here.

## Reproduction record

Exact command, UTC start/end, interpreter, input revision, script/oracle hashes,
exit code, output hash and stdout hash are in `command.txt`. Captured output is
in `stdout.txt`; the complete machine-readable rows are in
`oracle_store_diff.json`. The protocol source was extracted with `git archive`
to a temporary directory. SQLite stores and keys/observations were synthetic.

Limits are unchanged from the previous run: one earlier digest per key; the
grant and executed-receipt death facts are caller-asserted; no observation
regression, native ledger reachability, quorum, process transcript, or F case is
evaluated. Same-model authorship remains a correlation limit.
