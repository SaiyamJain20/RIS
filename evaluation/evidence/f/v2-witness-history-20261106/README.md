# C-F1 declared witness signing-history verification

Classification: tested paper-derived reconstruction extension and deliberate
mutations. Synthetic fixtures/observations and real EIP-712 signatures; no live
RPC, service, ledger experiment, new integrated E parity or F gate result.

`evaluation/witness_history_v2.py` independently checks the declared export's
binding/owner/marker/fingerprint, ordered live and append-only historical keys,
effect hashes, every signing digest/signature, death inequalities and generation
ordering. It rebuilds all four message types from K/effect/liveness and uses
`signing_context_v2.verify_bound_signature` with a caller-pinned owner and
independently reconstructed context. Existing certificate checks still require
the exact observed quorum. Historical keys require their live successor even
during faults/clears. A->B->A is legal; equal block numbers require equal hashes.
Fault/clear intervals and bit1/bit5 death exclusions are explicit result labels.

This is declared consistency/authenticity only. The embedded marker object is
not physical INITIALIZED bytes. Export completeness against WAL-aware SQLite
rows/marker bytes, raw native observation/death facts, arrival completeness,
durability/power loss, the fault oracle and finite model remain unimplemented.
No existing runner/consumer, shared schema, frozen payload or peer module changed.

## Verification

- Tests first:90 missing-module failures, then90 PASS; review controls139 PASS.
- Seven deliberate in-memory bypasses admit inputs the real verifier refuses.
- Wide focused suite609 PASS/35.94s; core582 PASS/35.16s.
- Fresh root `.venv/bin/python -m pytest -q`:2267 PASS/441.15s, command441.46s,
  exit0. Both240 selected inputs and all163 execution-discovered source entries
  match before/after. Final frozen manifest SHA-256:
  `38d7cb4019ae95aeadd427f225a7f163046aeda9aa3e6f3570f59ac4ef84e89a`.
- 429 ledger READY entries,52 F0 protocol pins and31 frozen publication payloads
  verified. Python3.13.13/Git2.54.0/pytest9.0.2/jsonschema4.26.0/eth-account0.14.0.

Exact argv/UTC/exits and raw/compressed hashes: `commands.json`; lossless gzip
outputs; `inputs-{before,frozen}.json`; `verification.json`. Preimplementation
inventory is retained separately. Reproduce the isolated slice with
`.venv/bin/python -m pytest evaluation/tests/test_witness_history_v2.py -q`.
The fixtures derive signatures from the published vectors and documented
synthetic witness keys; they cover F q3/q2 and carried E q1. All observations
are synthetic and caller supplied, not authenticated chain evidence.

Retained helper failures: a noncanonical mutation signature; a global fixed
stub result causing unrelated digest failures; mistaken README/draft newest-
outbox selection; proof expected582 core tests while the command included27
extra v2.1 tests (609 PASS). The intended582 selection was subsequently run;
no tested source/proof helper was changed after the root freeze. These are
author tooling mistakes, not HMBC findings. `REVIEW.md` records the correlated
author review, stronger equal-height clear-baseline hash check and scope limits.

## Exact peer state and next work

Agent1 `8c0285ffa6986858caeb0140b930bf5db759fdc0` is unchanged; reviewed ledger
snapshot `85c59f588de58a8ff5e87b9fe6f630c9d8c43642`/manifest `70f541cd..`
remains fixed. Agent2 `305ca39d48b5cb2fe3f561b20c31a103189cbc19` adds a partial
adapter front-end with explicit revision selection/whole-manifest checks and
injected handlers. Owner says NOT_READY. Its96 tests/43 mutants were read, not
rerun/adopted. Four copied fixtures match cited source bytes. No new owner ACK
or READY since A1-0116/A2-0062.366 communication paths have no divergent or
ambiguous revision. Exact owner STATUS/HANDOFF/file-changing commits/hashes are
in `communication-provenance.json`, `peer-review.json` and the input manifests.

Next C-F1: WAL-aware logical snapshots/physical marker bytes and exporter/native
completeness joins, then fault oracle/finite model. Full owner READYs and consumer
mapping, followed by a separate complete source/tools/config/run FREEZE and exact
affected ACKs, precede integrated services/scenarios. Historical qualified E is
unchanged; all32 F cases/GateF NOT_RUN; G locked. No human action required.

Operational record: initial mkdir probe refused the existing file lock. Skills
and prior memory were read before the established flock was acquired; project/
Git work began only after successful file flock. The separate coordinator flock
was held for Git work. No overlap was detected. Keep both original lock inodes;
publication receipts and verified release are in automation memory/run records.
