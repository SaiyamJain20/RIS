# Retrospective checkpoint RPC capture

C-F1 WORKING; integrated execution remains LOCKED. This is an isolated extension
result in the paper-derived HMBC2020 reconstruction. Tests use synthetic RPC
transports, frozen public ABIs and real EIP-712 signatures. No existing consumer,
frozen interface, dependency, peer module or peer runtime mailbox changed.

`evaluation.checkpoint_rpc_v2.collect` acquires the raw state required by the
existing checkpoint-history verifier for every live/superseded checkpoint digest.
The caller supplies exactly one historical PBC observation and a nonempty reason
per digest. The DBC observation comes from its indexed history entry. Per-digest
provenance retains those selections, the exact history location and explicit
unsigned observation bases; signing time and latest-head claims are always false.
Reasons are recorded caller assertions, not independently verified provenance.

Reads use exact source/head/DBC hashes and the published getter ABIs. Both chain
identities bracket all reads; headers are checked again after state calls.
Safe intervals require canonical hashes. Fault/clear intervals retain fork hashes
and their labels; bit1/bit5 death exclusions remain visible. A->B->A, multiple
expiry refinements, arbitrary selection order and empty checkpoint subsets work.
Budget/deadline refusal and transport errors retain partial API-level transcripts.
Hash-call incompatibility refuses without numeric fallback; no latest lookup.

## Verification

Fresh67 collector tests and510 focused tests PASS. Six narrow in-memory bypasses
are detected with their valid controls: duplicate selection, state verification,
trailing chain identity, safe canonicality, final header consistency and selection
drift. Full root regression:2650PASS in572.53s; command572.850s/exit0.

Retained RED:62 missing-module failures, with its exact test source copied to
red-test-source.py.txt. First GREEN:62PASS; five review controls were then added
and67PASS. Production code did not change after initial implementation. Early
trials precede the final product/test source bracket; complete initial trees were
not frozen. No branch coverage or performance result is claimed.

The first mutation helper failed: it changed both a source timestamp and an
explicitly selected head timestamp, so a different correct check refused before
the intended header-recheck bypass. The corrected helper changes only the source
header with no selected timestamp. Initial helper and lossless failed log are
retained. audit.py/verify.py were also adjusted to record helper changes honestly;
all three original versions are retained as *-initial.py.txt. Product/test inputs
remain unchanged; these evidence helpers are not root-pytest runtime inputs.

## Reproduction and provenance

The PLAN predates tests. Command receipts record exact argv/cwd, UTC interval,
elapsed time, exit and raw output hash; matching .log.gz files preserve all bytes.
record.py uses owned process groups and an1800-second timeout. Direct child STOPPED
receipts remain in ignored evaluation/runs/v2-checkpoint-rpc-20261107/. This is
no kill/recovery, durability or timing experiment.

inputs-before.json pins254 selected local inputs,899 complete owner inputs and
five initially bracketed evidence helpers. inputs-after.json records stable product/test/owner inputs
and exact before/after helper changes, with each original helper retained. The
owner inventory is inherited from the preceding checkpoint-history input manifest,
whose digest is recorded; every current owner blob, all52 protocol/f0 pins and the
frozen publication payloads are freshly checked. The clean initial Git baseline and all8443 carried tracked blobs were independently
checked, with their aggregate SHA256 in checkout-baseline.json; the post-root
carried-input diff also exits0. This covers immutable historical fixtures that
root tests may read. New product/test inputs use their explicit SHA256 bracket.
No peer runtime was executed or newly adopted. Exact fetched tips: Agent1
8c0285ffa6986858caeb0140b930bf5db759fdc0 and Agent2
67111f580b6ecfd1b924f3cd1a863981180822e1. Communication scans cover391 paths,
file-changing commit hashes/ancestry, with no divergence. Final fetched tips and all391 communication revisions match the first scan; no new owner READY/ACK.

Python3.13.13/Git2.54.0/pytest9.0.2/eth-account0.14.0/eth-abi6.0.0/jsonschema4.26.0.
Environment digest is a local observation, not a portable environment claim.
Known synthetic signing fixtures and ABI paths are in the pinned tests.

From the root, run `.venv/bin/python -m pytest evaluation/tests/test_checkpoint_rpc_v2.py -q`,
use the focused-command.json argv, or run `.venv/bin/python -m pytest -q`.
Run `.venv/bin/python evaluation/evidence/f/v2-checkpoint-rpc-20261107/mutants.py`
for corrected bypass controls. Audit/verify output filenames are immutable;
replays require a fresh evidence directory. verification.json SHA256 `36d9d66b886e75504df57d70cb802862a918483a8d0b9b67029d0d3fa1c3871d` checks14 predecessor receipts; its own15th receipt was independently checked without rewriting.

## Limits and continuation

Capturing a historical block now does not establish when a witness validated or
signed, what the latest head was then, chain/RPC authenticity, ancestry, producer
rule violation, complete exporter/store rows, native death facts, persistence,
consensus, E parity, TLC or any F scenario/gate result. A consistently lying RPC
can pass. Injected blocking clients require their own I/O timeout. REVIEW.md
records the correlated author review; no extra agents were launched.

No new peer READY/ACK. A3-0096/97 startup-refusal requests remain open; Agent2's
complete runtime READY/mapping and real transport-clock/CLI witness wiring/H2/H5/H6
remain pending. The three previously changed historical E paths are unchanged;
new full source READY and real E regressions remain required. Separate exact
source/tools/config/run execution FREEZE ACKs precede integrated services.
Historical qualified E is unchanged;32Fcases and GateF NOT_RUN; G locked.
Next: remaining signed-type source-state duties and exact producer/schema/path/
lock completeness joins, then fault oracle/finite model. No human action required.

The product/test source bracket precedes explanatory README/shared-state/handoff
edits. Publication receipts and final lock cleanup are retained in ignored runs
and automation memory. No unresolved important review finding is reported.
