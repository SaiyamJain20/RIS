# A2-0039 successor-pin review, 2026-10-12

Agent3 reviewed origin/agent-2 `79bfb4afdb6fb12622c913b0991ad5c089602d24`,
message A2-0039 (file-changing commit is that same commit), while local agent-3
was `b4d3df66b193e26c0f3ff57e1c9e28adbbf14242`. Fetch exit 0; Agent1 unchanged
at 691147873fb077322d33a0a8dd14b78764d01f70. Full communication scan: 274 paths,
no divergent revisions. Exact branch/file provenance: communication-provenance.json.
Agent2's STATUS/HANDOFF and immutable message contain pre-publication Git prose;
the fetched commits establish that the successor is now published.

## Result

Accept the worker-log URI fix as a reviewed **successor candidate** for a future
F0 source plan. This is a scoped REVIEW, not an integration FREEZE ACK or F launch.
Historical E source/report/ACKs retain their original meaning. Actual protocol/**
in the Agent3 checkout remains unchanged; the review used a git-archive snapshot,
not a merge. No service processes, live transactions, dependency changes or peers'
mailbox edits. Single-session, same model family; not independent confirmation.

## Fresh checks and commands

Every recorded command's argv, cwd, UTC interval, output SHA-256 and exit are in
its `.json` sidecar; raw output in `.stdout.txt` (renamed from recorder `.log` for publication).
`run.py` records them. Snapshot:
`.git/ris-communication-20261012/snapshot`, git archive of the exact incoming pin.
The archive's 168 tracked protocol files were checked against their owner Git
blobs after execution: all unchanged (source-audit.json). Imports used that pinned
protocol package and the existing root venv. Shared fixture paths link to current
root interfaces/ledger/evaluation; selected tests need no chains or Git operations.

- `owner-uri-tests`: python -m pytest protocol/tests/test_worker_log.py, select
  reads_exactly/sibling_database/relative_state/missing_or_foreign/ambiguous,
  -q -rs -c protocol/pytest.ini --rootdir protocol -p no:cacheprovider.
  Exit 0, **9 passed, 2 deselected**, 1.44s, no skips. Five path variants plus
  sibling, relative, missing and ambiguous cases. Two live-ledger tests deselected.
- `manifest`: sha256sum -c --quiet protocol/evidence/source-manifest.sha256:
  exit 0, all **142 entries**. Manifest SHA256
  005c8448faeb90d2dade129211a5f220635ee1c8bf421c89f17b2b7d0c2d7612.
- `export`: PYTHONPATH=protocol python -m hmbc_protocol.export --check:
  exit 0, exports match **9 files**.
- `semantic-review-corrected`: owned review.py.txt uses synthetic offline real
  Worker/SQLite data. Old pinned exporter reads the valid sibling at truncated
  `run#1`; successor reads the requested database and preserves primary database
  bytes. Negative control demonstrates this is not denial of all exports.
  The constructor accepts a reused worker state after only profile/mutations
  change; owner and evaluator fingerprints remain equal. This is a tested
  reconstruction limit, **offline only**, not an adapter or six-profile live run.
  Exit 0. All **103 distinct** historic --state-dir values (1039 occurrences)
  lack #/?/%; fresh scan supports the owner's historical non-impact assertion.
- `semantic-review` exit 1 retained: initial diagnostic bracket mistakenly included
  SQLite WAL/SHM side effects and the known broken old exporter in its no-change
  assertion. Corrected bracket checks primary database bytes during successor
  reads only; no production fix or gate result derived from that diagnostic failure.
- `environment`: exit 0. Python 3.13.13, SQLite 3.47.2, pytest 9.0.2,
  eth-utils 6.0.0, eth-account 0.14.0, jsonschema 4.26.0. No Foundry/PV executed.

Production diff against current Agent3: **only** worker_log.py changes among
hmbc_protocol/testtools/exports/abi. Old SHA256
0eacaa1c0ffd176ba4fd2de9b20171738fb38997c1376e5fe0c24ed32e83df55 -> successor
b443d5e8a6b62e7cded7bbece00c78a2cfbc05fd983d912e303398de2a36cd0e.
The old manifest d16ddad8.. and source 0716a8e remain the integrated E pin.
Frozen interface/report/gate manifest hashes unchanged (source-audit.json).

## Limits and next work

No full protocol/evaluator suite or live D49 check rerun in this focused review;
owner's 1383/201 suite and six mutants are read evidence, not Agent3 results.
No new gate run, stronger fingerprint, F model or signature-expiry implementation.
A3-0051 answers the pin question. D50 tracks D-2 for a future exact RFC:
canonical bytes, six contract roles, trusted manifest verification, state migration,
fail-closed old-state policy, differing profiles/code and ordinary restart controls.
Unchanged exported fingerprint alone never proves these stronger identities.
D-4/D-6 remain candidate owner backlog for the next reviewed revision. Human F
planning/go-ahead remains pending. No gate advancement or peer ACK fabricated.

Publication note: first exact git-add exited 1 for six ignored *.log evidence
paths, staging only the other reviewed files. Renamed selected raw outputs to
*.stdout.txt and refreshed this manifest; no ignore override, reset or peer edit.
