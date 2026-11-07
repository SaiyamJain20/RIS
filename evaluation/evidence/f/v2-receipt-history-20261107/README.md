# Declared GrantReceipt history state coverage

C-F1 WORKING; integrated execution LOCKED. Tested evaluator reconstruction/
extension for HMBC2020, synthetic inputs and real EIP-712 signatures/raw ABI
bytes only. No paper implementation defect or new protocol behavior is claimed.

The internal receipt_history_v2.verify_receipt_history composes signed-history
verification with receipt_state_v2 for every declared live/superseded receipt.
PBC observation is selected from the stored signature; the caller separately
pins DBC observation. Closed captures require exactly one entry per signed digest.
All existing signature/context/schema and exact raw grant/request/event checks
remain active. Repeated headers/state calls/event identities and payloads agree;
same-height forks refuse in a declared safe interval. A grant retains one
canonical event in that interval. Captures are never modified. Empty receipt
subsets still validate all other declared signed records. No receipt expiry is
invented; late reconciliation remains valid. Fault/clear labels and mutation
death exclusions remain explicit. No existing consumer/wire/dependency changes.

## Evidence and reproduction

Run `.venv/bin/python -m pytest evaluation/tests/test_receipt_history_v2.py -q`.
Exact broader argv/cwd/UTC/exits/output SHA256 are in *-command.json; lossless
raw outputs are in deterministic gzip logs. Tools/environment digest, all899
owner hashes/264 selected local inputs, source/fixture hashes and8676carried
tracked blobs at initial HEAD371fdcbe5cbe8459acd78d7a48a6121b2fce9620 are pinned
in inputs-before.json and rechecked in inputs-after.json.52F0pins/31frozen payloads
also verify. runtime-before.json/runtime-after.json additionally pin the exact
1242path E2 source-discovery inventory including ignored run/evidence scripts.

- RED:38 expected missing-module failures, exit1; original test bytes/hash retained.
- GREEN:38PASS, exit0; no product/test correction after initial implementation.
- Focused composition:417PASS, exit0.
- Seven narrow in-memory deliberate evaluator bypasses detected, all seven valid
  controls pass; source bytes untouched. No producer mutation or coverage claim.
- Initial full root: interrupted after1FAIL/1275PASS, exit2; incomplete/INVALIDATED.
- Affected E2 guard test alone:1PASS, exit0; no guard or product change.
- Final root `.venv/bin/python -m pytest -q`:2944PASS in
  916.09s (command 916.844s), exit0.

The initial failure was test_duplicate_execution_requires_each_complete_probe[complete]
in evaluation/tests/test_e2_freeze.py:117. Its plan covered1241 runtime paths;
the coordinator created evaluation/runs/v2-receipt-history-20261107/verify.py
between its plan capture and post-check (17:39:46–17:39:51 UTC). This ignored
script is discovered by evaluation.e2._sources. The guard correctly refused.
root-failure-source-delta.json and failed-e2-plan/manifest.json.gz preserve the
exact one-path delta and failure; root.log.gz retains the interrupted result.
No product/test source changed. The initial verifier bytes and its pre-rerun
correction are retained. The final full run freezes the actual1242path inventory.
Earlier focused/mutation/initial-root commands partly overlap; no benchmark.

Verification JSON checks15 base command receipts, actual test totals,
source inventories, provenance and held original lock inodes. Its own receipt
and compressed log are checked from the parent. The first postflight verifier
invocation failed to import evaluation (exit1); the corrected invocation adds
explicit PYTHONPATH only, with no source change. The parent independently checks
all17 receipts, including that retained failure and the final verifier. The
artifact-sha256.json records
the resulting evidence bytes without rewriting verification.json. All direct
children recorded for this run stop; no integrated chains/services started.
Explanatory/live documentation was updated after the runtime postflight; no
full-regression rerun is claimed for those documentation-only edits.

## Scope and remaining work

Supplied-state consistency establishes no native death predicate or reachable
ledger transition. Synthetic superseded receipt controls deliberately use a
declared fault/clear interval; they are not safe-ledger transition examples.
Changing a canonical grant location in a declared safe interval refuses. The
event-conflict control changes both grant expiry and event nonce, so it tests
event-payload contradiction, not an isolated request-nonce join. Log identity/
payload checks do not authenticate transactionHash/logIndex or inclusion.

The exporter observations are not signature-bound signing time; neither is
proved to be the producer's latest head. Explicit signTimeEstablished,
latestHeadEstablished, logCompletenessEstablished and nativeTransitionsEstablished
flags are false. No RPC truth/ancestry, log-range/export/store completeness,
producer validation/misconduct, native deaths, persistence, delivery, quorum or
consensus follows. q2 is a synthetic fixture; one owner signature is no quorum.
No new E parity, TLC, F scenario or gate run follows from these unit regressions.

Fetched peer tips remain A18c0285ffa6986858caeb0140b930bf5db759fdc0 and
A267111f580b6ecfd1b924f3cd1a863981180822e1.396communication paths checked with
exact file-changing commits and hashes; no divergent revisions, new peer READY/
ACK or adopted owner runtime result. owner-provenance.json identifies the exact
owner statuses/handoffs/messages and accepted R6/revision9 source bytes.
A3-0096/97 startup requests remain open; complete runtime READY/mapping and
separate exact source/tools/config/run execution FREEZE ACKs precede services.
Qualified historical E unchanged; all32Fcases/GateF NOT_RUN/G locked. No human
action. Next: receipt RPC acquisition with explicit observation/log-range
provenance, remaining AccessDecision and producer/schema/path/lock duties,
then the fault oracle/finite model. Review is correlated; no extra agents.

Startup lock-protocol error and its limits are recorded in PLAN.md. Both original
persistent lock inodes were held through repository reads/fetches/edits and
publication; lock cleanup and remote publication receipts follow in ignored run
output and automation memory. No peer edits/worktrees/main push.
