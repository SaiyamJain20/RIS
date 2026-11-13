# Consolidated Agent 2 runtime review

C-F1 isolated review of A2-0076/0078/0079 plus A2-0083 TEST-ONLY additions.
Paper-derived HMBC2020 reconstruction, synthetic inputs, correlated author
review. No extra agents or owner/product/test edits. No chain/service deployment,
execution freeze, interface/dependency change, gate or full runtime acceptance.

## Source and provenance

Review snapshot: 5e25b536f01921683074b9c2678bac8d795a4c05 (2242 protocol files).
A2-0084 confirms no further P1..P3 source delta was required by A3-0105. Production
modules/exports/ABI are unchanged from the reviewed cumulative0078/79 state;
optional0083 hooks are TEST-ONLY. owner-source.json pins the complete snapshot;
owner-accounting.json pins the27cumulative non-evidence paths since7d97b90.
Exactly three of142historical E entries differ: worker.py, worker_log.py,
testtools/deviating_witness.py.7ABI fixture copies equal ledger85c59f5;52accepted
F0 pins,31frozen interface payloads, schema copy and baseline dependency bytes
match. These are file checks, not measured native E parity.

Correction to A3-0107: source commit7d97b902a7fa4d02c32c7cc95ef75a10b69694a9
contains the549hashed source entries but not the manifest itself. The manifest
was published at8b0a0b44f9d2f6f88a3bc50d2a79ae442a78d3cd, SHA256
7de8f334d0f68da97ffb5900359a422fc5a891de1a34a0c50a26e42b91880e81.
Our first source lookup failed because it blurred these two commits. Reading the
manifest from its actual publication and comparing all549source blobs reproduces
the identity result. A3-0107 remains immutable; this checkpoint corrects provenance.
Current snapshot changes exactly five of those549entries (witness_state.py,
test_witness_service_decision.py, faulty_adapter_v2.py and the faulty-adapter/
state mutation runners). New files are separately inventoried, never omitted.

## Scope and exact results

Every *-command.json records argv,cwd,UTC,exit,timeout,PID/process group, environment
SHA256 and output SHA256. Raw stdout/stderr is retained losslessly as *.log.gz.
Tool versions/source and helper hashes are in inputs-before.json. Current host:
Python3.13.13,SQLite3.47.2,pytest9.0.2,eth-account0.14.0,eth-abi6.0.0,
jsonschema4.26.0,Git2.54.0;offline Cast1.8.5 executable hash is separately pinned.
The owner reported SQLite3.50.4; no same-host/version assumption is made.

- Focused startup/lock/hot-journal tests:195PASS,exit0. This includes182startup
  refusal cases and closes A3-0096/97 in isolated tested scope.
- Full selectable no-chain protocol review, first trial:2929PASS/6FAIL/2ERROR/
  201SKIP/267DESELECT,exit1. Five failures came from the reviewer guard blocking
  offline Cast codecs; two setup errors came from a nested Git path prefix in the
  extracted snapshot; one failure was the owner initialization-kill coverage gap.
- Corrected broad trial:2935PASS/2FAIL/201SKIP/267DESELECT,exit1. Historical E pin
  setup works with explicit read-only GIT_DIR and GIT_OPTIONAL_LOCKS=0. One remaining
  failure was the guard omitting offline Cast keccak; the final targeted codec
  run passes1/1 after allowing it. The other failure is the owner harness below.
  The broad trial is NOT relabelled as passing and was not rerun again.
- State mutation runner: unmodified control PASS,42/42DETECTED,exit0.
- Startup mutation runner: unmodified control PASS,19/19DETECTED,exit0.
- Export check:9files match,exit0.
- Kill mutation runner: unmodified control FAIL,exit2; it correctly reports no
  mutation results. K1/K2/E1 are NOT evaluated/adopted by this review.
- Captured unmodified kill control separately:1FAIL/2PASS,exit1. Signing-kill and
  premature-reply positive controls pass; initialization coverage fails.
- Independent owner-store/evaluator-reader cross-probe: PASS,exit0. Baseline
  witness_state84d36e24 refuses idle snapshots after signing; cumulative current
  c6184a61 permits them. A writer waits while locked_store holds EX; an in-flight
  signing callback excludes a snapshot; final idle state is stable. This is a
  same-process/thread and independent-open-description lock probe with synthetic
  placeholder signatures, not a native-chain/witness-service or power-loss test.

Selection is explicit:3138selected/267excluded. Exclusions:166fixture-closure,
78whole live modules,22dynamic live fixture parameters,1catalog completeness
assertion requiring excluded live cases.201skips are200ScenarioResult and1FileHash
schema cases outside protocol scope. Guard refusals in the first two trials are
retained; the final targeted guard report has no blocked process. Anvil/Forge/Java
and non-codec Cast launches remain refused. The guard runs in the parent pytest
process, not as a general OS/network sandbox. Reviewed mutation runners copy only
known offline test files into disposable clones. No native chains were started.
Commands overlapped; no performance/timing comparison or independent-review claim.

## Remaining owner finding: random initialization kills never land here

Classification: tested reconstruction test-harness coverage/portability gap;
not a discovered HMBC defect, store-loss counterexample or wrong authorization.
At tests/test_witness_state_kill.py:160 the test requires interrupted>=1. With
HMBC_KILL_TRIALS=100 and its fixed seed2/delay window[0,0.05], every initialization
finished before SIGKILL in the broad trials and the separately captured control.
Thus interrupted=0 and finished=100. The non-vacuity assertion is doing its job.
The runner's control failure hides its child output, so kill-control.txt exposes
that output without changing the owner source/tests or retrying until green.

Request to Agent2: use a controlled or host-calibrated initialization-kill schedule
that verifies at least one actual interruption while retaining the assertion;
record exercised/finished counts and preserve the two passing signing/early-reply
controls. Then rerun the unmodified control and K1/K2/E1 runner on exact new READY
bytes. Do not weaken the assertion or count a control failure as detection.
Deterministic hot-journal recovery tests already pass here, so this finding does
not show that recovery or persistence failed. It concerns the additional random
initialization-kill claim, not a blanket rejection of baseline runtime behavior.

## Review and next step

Read strict startup readers/shared Refusal, schema-before-I/O ordering, profile
wiring, spawn-after-validation, persistent pid files/no respawn and bounded close,
transaction-only shared locks/finally release, marker-absent read-only recovery
and commit-before-reply paths. Broad non-live tests cover pool/binding/handlers,
virtual fault hooks and historical characterizations; no live compatibility or
unrun owner number is adopted. Source hash equality cannot substitute for code
behavior. Exports, source-accounting and failure evidence remain separate.

8739tracked inputs and2242owner snapshot inputs compare equal after execution;
helpers have explicit original/intermediate/final versions.13base receipts are
verified, and the parent separately verifies the verifier's own14th receipt.
417communication paths have exact file-changing commit/hash provenance, no
missing/divergent branch revision, and unchanged peer tips across the run.
Explanatory/shared edits follow postflight. The private owner snapshot is disposable
and may be archived losslessly after verification; re-create with git archive of
its exact pinned commit. No source change is inferred from that cleanup.

Agent2's complete READY EXISTS. Agent3 runner/oracles/model and their reviews now
remain on the critical path. Full native runtime acceptance/E parity, model runs,
execution FREEZE and exact owner execution ACKs remain outstanding. The prior TLC
execution denial is preserved and was not retried/rewrapped. Independent runner/
model text can continue; this owner harness issue does not block all Agent3 work.
All32Fcases/GateF NOT_RUN/G locked. Correlated author review; no deferred polish.
