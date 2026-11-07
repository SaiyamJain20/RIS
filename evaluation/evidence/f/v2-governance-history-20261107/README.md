# Declared governance history and supplied-state coverage

C-F1 WORKING; integrated execution remains LOCKED. Internal evaluator extension
for the paper-derived HMBC2020 reconstruction, using synthetic fixtures only.
No author implementation or HMBC vulnerability is claimed.

`evaluation/governance_history_v2.py` composes the declared four-type signed
history check with governance state/approval checks for every live/superseded
governance digest, including each expiry refinement. Captures are exact closed
{digest,blocks,calls} records. Observations are taken from each stored digest;
approval lists are separately selected TEST-ONLY caller fixtures. Repeated block number/timestamp facts for each hash and exact getter results
must agree, with one hash per height inside declared safe intervals. Fault/clear labels and bit1/bit5 exclusions remain explicit.

The returned signTimeEstablished/latestHeadEstablished/approvalPolicyEstablished
flags stay false. Matching retrospective supplied state proves no actual signing
time, historical latest head or producer approval configuration/policy. These
unsigned exporter observations are not bound into the signature. One signature
is not a quorum. No existing consumer, frozen interface or dependency changed.

## Reproduction and evidence

Exact argv/cwd/UTC/exits/elapsed/output hashes are retained in *-command.json,
with deterministic gzip logs. record.py uses bounded owned process groups;
direct-child STOPPED receipts are in ignored evaluation/runs/v2-governance-history-20261107.
The before/after input bracket covers selected local runtime inputs, all carried
tracked blobs at initial HEAD and freshly re-read owner source blobs; this
includes historical fixtures consumed by root pytest. Helpers/tool versions and
environment digest (no values) are recorded. No intermediate write-and-restore
detection is claimed. Final explanatory/shared documentation follows the bracket.

42 new tests failed first because the module was missing (all reasons verified),
then passed. RED pins exact test bytes/initial HEAD; initial RED/GREEN and mutant
trial predate the complete bracket. The bracketed focused suite passed 286 tests;
eight narrow in-memory bypass controls detected / eight valid controls passed.
The full root suite passed 2,763 tests in 615.14 seconds (command 615.459s), exit 0.
Both input checks also verify 52 accepted F0 files and 31 frozen payloads.
The focused suite partly overlapped the mutant/root run; timings are execution
records, not benchmarks. No branch-coverage or exhaustive sensitivity claim.

Exact communication branch/file-changing-commit/SHA256 provenance is in the two
communication JSONs. Owner spec/source provenance is in owner-provenance.json.
No owner runtime result is rerun/adopted here. Full runtime READY/mapping and
separate complete exact execution FREEZE ACKs remain required before services.
A3-0096/97 startup requests remain open. No human action requested.

## Limits and next work

Review is correlated author review under the no-extra-agent rule (REVIEW.md).
No actual signing/validation time, latest-head/ancestry, RPC/chain truth, producer
rule violation or completeness, native death, complete store/export, persistence,
consensus, crypto performance, new E parity, TLC, F scenario or gate follows.
Historical qualified E is unchanged; all 32 F cases/Gate F NOT_RUN; G locked.
Next: raw governance acquisition with explicit observation/approval provenance;
remaining AccessDecision/GrantReceipt state duties and producer/schema/path/lock
completeness; independent fault oracle/finite model. Review owner startup fixes
and complete runtime READYs when published. No peer edits or main push.

Locks: persistent-file kernel flock was acquired before context reads. The first
non-TTY holder saw EOF immediately and released; the second TTY holder reacquired
before any context/repository work. Original inodes were retained. Both original
locks exclude independent concurrent acquisition and stay held through remote
publication verification. Cleanup receipts/memory record final release.

## Final bracket and results

899 owner blobs / 258 selected local runtime inputs / 5 helpers stayed fixed.
All 8,536 carried tracked blobs match initial clean HEAD
bef9c8d05329e901edfc35d394584499236a334a. The canonical carried path/SHA256 map
is 0184660d4318cef77887a3ab89abdf7fcf0cb7ea1676f108d7397e877b279bd1.
393 communication paths have no divergent revisions; peer tips are unchanged:
A1 8c0285ffa6986858caeb0140b930bf5db759fdc0;
A2 67111f580b6ecfd1b924f3cd1a863981180822e1. No new owner READY/ACK appeared.

| Command label | Observed result | Exit |
| --- | --- | --- |
| red | 42 expected missing-module failures | 1 expected |
| green-trial | 42 passed in 19.56s | 0 |
| mutants-trial / mutants | 8 bypasses detected / 8 valid controls, each run | 0 |
| focused | 286 passed in 59.32s | 0 |
| root | 2763 passed in 615.14s | 0 |
| preflight/postflight | Owner/local/helper/carried input equality | 0 |
| peers-before/peers-final | 393 paths, peers unchanged, no divergence | 0 |
| fetch-final | Success | 0 |

verification.json records hashes of these immutable artifacts and predecessor
command receipts; its own receipt/log are independently verified afterward.
Python 3.13.13 / Git 2.54.0 / pytest 9.0.2 / eth-account 0.14.0 /
eth-abi 6.0.0 / jsonschema 4.26.0; full executable/version strings are in inputs-before.
