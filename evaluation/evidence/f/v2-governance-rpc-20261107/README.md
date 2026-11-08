# Retrospective governance RPC state acquisition

C-F1 WORKING; integrated execution stays LOCKED. This is an internal evaluator
extension for the paper-derived HMBC2020 reconstruction, with synthetic fixtures.
No author implementation or HMBC vulnerability is claimed.

evaluation/governance_rpc_v2.collect captures every declared live/superseded
GovernanceAction digest and expiry refinement at its recorded PBC hash. It reads
Governance nonce/version/maxTTL and TMSC authority/tombstone getters through
pinned ABIs. Shared exact getter/header keys deduplicate. Both PBC/DBC deployment
identities and all selected PBC headers are bracketed around acquisition. Safe
intervals check numeric canonicality plus hash-selected requireCanonical calls;
fault/clear intervals retain competing hashes without calling them safe. There
is no numeric/latest eth_call fallback, service startup or consumer switch.

Each digest has an exact closed capture and location/unsigned-exporter-observation
provenance. TEST-ONLY approval tuples are separate caller inputs, pinned by hash
with a mandatory reason and explicit caller-fixture basis. The final governance
history checker consumes assembled captures plus those approvals. A matching
retrospective capture establishes neither actual signing time nor latest head,
producer policy or chain truth; signTimeEstablished, latestHeadEstablished and
approvalPolicyEstablished remain false. One stored signature is not a quorum.

## Reproduction and evidence

Run .venv/bin/python -m pytest evaluation/tests/test_governance_rpc_v2.py -q;
then the focused argv and full root argv recorded in *-command.json. record.py
retains exact argv/cwd/UTC/exit/elapsed/output SHA256 and deterministic gzip logs;
owned child-group status receipts are in the ignored run directory. All initial
71 missing-module RED reasons and exact test bytes are retained in red-inputs.json.
The first GREEN and mutant trial predate the complete bracket. Final focused,
mutant and root results use unchanged product/tests, selected local runtime inputs,
exact owner source blobs and all initial carried tracked blobs (including historical
fixtures consumed by tests). Tools/environment digest are recorded without values.
No intermediate change-and-restore detection or performance inference is claimed.
The focused suite/mutant/root commands partly overlapped; timings are execution
records only. The unused mutation-helper branch was removed before preflight;
helpers stayed fixed throughout the final bracket. Explanatory/shared edits follow it.

Six narrow in-memory bypasses target state/history composition, chain-ID equality,
final endpoint identity checks, final header reread, caller approval input drift
and canonical equality. Each bypass preserves a valid control and exposes its
intended invalid control. This is not exhaustive mutation or branch coverage.

communication-before/final.json retain exact branch, file-changing commit and
SHA256 provenance across fetched branches. owner-provenance.json independently
checks the relevant accepted R6/Governance/TMSC source pins; audit.py verifies
all owner inputs and frozen payloads. No owner runtime result is executed/adopted.

## Limits and continuation

Review is correlated author review under the explicit no-extra-agent instruction.
No actual pinned-node EIP-1898 support, RPC/chain truth, ancestry, actual signing/
validation time, historical latest-head, producer approval policy/misconduct,
complete store/export/history, native death, persistence, quorum/consensus,
cryptographic performance, new E parity, TLC, F scenario or RQ gate follows.
The cooperative budget cannot preempt a blocking injected transport; RpcClient's
per-call timeout is separate. The collector retains partial failure artifacts
and never overwrites an existing output directory.

Complete runtime READY/mapping and separate exact execution FREEZE ACKs remain
required before integrated services. A3-0096/97 remain open. The three known
historical E source differences still require full READY inventory/E regressions.
Historical qualified E unchanged; all 32 F cases/Gate F NOT_RUN; G locked.
Next: remaining AccessDecision/GrantReceipt state duties and producer/schema/
path/lock completeness, then fault oracle/finite model; review owner startup
fixes/complete runtime READY when published. No human action is requested.

Original scheduled/coordinator persistent-file locks acquired before context
reads/Git writes and independently refused concurrent acquisition. They remain
held through remote publication verification; final cleanup records release.

## Final verified results

| Command | Result | Exit |
| --- | --- | --- |
| red | 71 expected missing-module failures, exact reasons verified | 1 expected |
| green | 71 passed in 23.50s | 0 |
| focused | 449 passed in 110.57s | 0 |
| mutants-trial / mutants | 6 bypasses detected, 6 valid controls, each run | 0 |
| root | 2834 passed in 617.31s (command 617.650s) | 0 |
| preflight / postflight | Owner/local/helper/all carried input equality | 0 |
| peers-before / peers-final | 394 paths; exact tips/revisions unchanged, no divergence | 0 |
| fetch-final | Success | 0 |

899 owner blobs, 260 selected local runtime inputs and 5 helpers stayed fixed.
All 8577 carried tracked blobs match initial clean HEAD
c715b5e4da53de6e1a9781225b9b26ec3dab536f; canonical carried path/SHA256 map
13673f1caf185cae04064341df1e26eb3da9e6481c7ff57994bbdd1dc95ca241.
52 accepted F0 source pins and 31 frozen payloads match. Final peer tips:
A1 8c0285ffa6986858caeb0140b930bf5db759fdc0;
A2 67111f580b6ecfd1b924f3cd1a863981180822e1. No new owner READY/ACK.

Python 3.13.13, Git 2.54.0, pytest 9.0.2, eth-account 0.14.0,
eth-abi 6.0.0 and jsonschema 4.26.0; exact strings/paths are in inputs-before.
verification.json pins immutable evidence/predecessor receipts; its own receipt
and output are independently checked afterward, without rewriting the verifier.

An unrecorded initial evidence-assembly command exited 1 by comparing the entire
communication scans, including capturedAt. Diagnosis found capturedAt was the
only changed field; the corrected check compares exact branches/files, matching
the retained verifier. assembly-note.json preserves the failure and correction.
No product/test source or regression result changed. The evidence verifier was
updated after postflight to retain and accept the assembly command failure; the corrected
assembly command is recorded separately. The parent checks all recorded direct children STOPPED after assembly completes.

The recorded assembly attempt also exited 1 because it required its own RUNNING
process receipt to be STOPPED. The corrected assembly excludes its own PID while
checking predecessors; the parent subsequently checks every recorded PID receipt.
The original attempt source/log/exit are retained. helper-correction.json records
one verification-helper change after postflight so the final verifier explicitly
checks the retained expected failure. Runtime/product/tests did not change.
