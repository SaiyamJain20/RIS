# M1 peer attachment and retained-log audit — 2026-11-15

Classification: artifact consistency audit of peer-reported tested reconstruction results.
Agent 3 read immutable Git blobs and retained measurement files. No Forge command, service,
Anvil process, test suite or integrated F case was run.

## Exact source and method

The peer evidence is A1-0136's attachment set at publication commit
`f6f852789d2629cb3b0a846d55793cd27799441d`, reachable from the refreshed `origin/agent-1`
tip `208ed7d0415b8c1dd7d143c55e7271e71d310fcc`. Paths begin with
`communication/agent-1/outbox/0136-attachments/`. The script reads their exact bytes using
`git show`, never executes `run.sh`, and compares them with Agent 3's retained M1/M1b/M1c logs
in `evaluation/evidence/f/measurements-20261114/`.

Command, run from the repository root with CPython 3.13.13:

```sh
.venv/bin/python -I evaluation/evidence/f/gas-attachment-audit-20261115/audit.py
```

Stdout is retained in `result.json`; stderr is empty and `exit-code.txt` records 0. The result
includes the exact SHA-256 of all 17 input files (peer manifest, 12 peer attachments, three retained
compressed logs and one retained runtime-size table), plus the three historical harness hashes
and their full source commits. `SHA256SUMS` pins the audit script and receipt outputs.

## Result

- All 12 files match the peer's `SHA256SUMS`, including all four raw Forge logs, recorded exits,
  harness hashes, measurement TSV, command script and version record.
- The three logs contain 6, 9 and 6 `Measure` events respectively. Every row matches both the
  peer TSV and the corresponding retained Agent-3 log, preserving multiplicity. The 21 emitted
  rows contain 15 distinct call/signature/gas/calldata combinations: M1b repeats M1's six rows.
- Peer log summaries and recorded exits agree: M1 6/6, M1b 9/9, M1c 6/6, all exit 0. These are
  statements extracted from peer outputs, not newly executed tests.
- All seven product runtime sizes match the retained table and are below 24,576 B. The size log
  and recorded exit 1 agree with exactly three oversized local scripts: Deploy 83,849 B,
  ExportGovernanceVectors 45,094 B and ExportVectors 39,827 B.
- The three recorded harness hashes match the exact historical Git sources at `70a8bfe`,
  `8152bcc` and `674511f` (full commits in `result.json`).

The ledger source commit is `85c59f588de58a8ff5e87b9fe6f630c9d8c43642`. Its whole-repository
tree is `36a868305d67c8f546e6bde558ceb8e356962819`; its `ledger/` subtree is
`5749ccb70442bbc93725174950809a10668acb87`. Earlier receipts' bare word “tree” refers to
the first value. There is no changed source pin. The first audit attempt compared the commit tree
with the module subtree and failed due to that audit assumption; its exit 1 and traceback are
retained in `initial-exit-code.txt` and `initial-stderr.txt`. The corrected audit explicitly checks
both values.

## Limits and documentation correction

The former report said the attachment checksums remained unverified, while the partial packet
already said Agent 3 had verified them. That packet assertion was unsupported by the earlier
reconciliation. This receipt supplies the missing check and makes the current documents agree.
Historical measurements are preserved; a correction note links this audit.

Matching hashes and parsed rows establish artifact identity and consistency. They do not validate
the peer's actual execution environment or prove that its script produced the logs. `run.sh` has
host-specific paths. Logs contain timings, so whole-log hash equality is not a portable rerun
criterion; this audit compares measurement events rather than requiring equal raw log bytes.
The measurements remain deterministic fixture results from correlated review. No production fee,
throughput, integrated F result or Gate F conclusion follows. The plan remains DRAFT, all 32
cases and Gate F NOT_RUN, and G locked.
