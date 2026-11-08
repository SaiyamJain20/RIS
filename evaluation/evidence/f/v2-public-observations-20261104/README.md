# Public ABI acquisition for successor deployment context

Agent3, 2026-11-04. C-F1 isolated evaluator work for the paper-derived HMBC2020
reconstruction and F extension. Classification: tested reconstruction results
on synthetic RPC bytes, plus deliberate in-memory check removals. No original
paper vulnerability, running-chain observation or integrated gate result.

Added evaluation/public_observations_v2.py. collect() explicitly selects a v2 or
v2.1 successor manifest, checks the complete ABI inventory and owner ABI hashes,
then reads chain/genesis/deployment identity, raw code and required getters. All
code/getter reads use one explicit historical block per chain. After both chains
are read it rechecks BOTH identities, genesis/deployment blocks and read anchors,
rechecks local ABI/manifest inputs, and invokes the existing independent B
reconstruction. Caller-selected pins supply the compiled MAX_ADMINS attestation.

Each raw API call, parameters, result or exception survives in transcript.json;
the existing RpcClient additionally retains subprocess argv/raw stdout/output
digests, tool hashes and endpoint provenance. A fresh output directory refuses
overwrites. A validated result is written to a pending file and renamed; failed
collection has no published result. A finite whole-collection deadline and 128
call cap supplement RpcClient's per-command timeout. This is an internal API,
not D50's open implementation or its frozen S0 count, and no existing consumer
is switched. Existing schema/signature/context code and shared bytes stay fixed.

## Fresh verification

- Tests first: 39 failures because the collector module was absent; then 39 PASS.
- Review added 14 controls. A controlled interrupted result write exposed a
  partial final file: 1 FAIL/52 PASS. Pending-file publication fixed it; 53 PASS.
- A real RpcClient subprocess test uses a synthetic CLI and dataset, with actual
  tool checkpoints, ABI decoding and per-command output hash verification:
  54 new tests PASS. It starts no server and is not a Cast/Anvil experiment.
- Focused schema/signature/context/collector run: 351 PASS, exit0, 7.84s pytest
  time. Six check removals each accept a bad observation the original refuses.
- First full attempt: source-stability test
  test_audit_execution_requires_each_complete_row_proof[complete] failed because
  this author added sensitivity.py and review_peers.py during the run. The E2
  source selector includes evidence Python scripts even though the initial outer
  input bracket excluded them. The exact failed manifest and two additions are
  retained in source-drift.json. Stopped only the verified owned pytest PID794357
  with SIGINT: 1 FAIL/896 PASS/exit2/213.51s; this is not a complete suite result.
- Finished all discovered scripts and captured both inventories in
  inputs-frozen.json: 236 selected inputs and 153 complete E2 source entries.
  The fresh full suite passed all2036 tests, exit0, 401.62s pytest time
  (401.897s command wall time). The after-suite audit confirmed both complete
  inventories unchanged. Exact commands/brackets are recorded separately in
  commands.json and verification.json. The failed attempt remains evidence.

record.py retains exact argv/cwd/UTC/exits/output digests. Failed raw logs are
stored losslessly with gzip and raw/compressed SHA-256 values. audit.py verifies
all429 exact owner ledger READY entries, all52 protocol F0 pins, all31 frozen
publication payloads, and every fetched communication revision's provenance.
review_peers.py verifies seven byte-exact owner ABI fixture copies from source
85c59f588de58a8ff5e87b9fe6f630c9d8c43642 and the new peer notes/artifact hashes.
Author review is correlated under the no-extra-agents instruction; see REVIEW.md.

## Peer ruling and remaining work

A1-0116 at8c0285f and A2-0062 atbeab2d1 are notes, not ACKs or source READYs.
Agent2 reports B/hash agreement on three synthetic carrier fixtures and 178
fault verdicts. Its raw-code hashes are replaced with synthetic hashes and its
fake facts derive from Agent3's expected-view builder. This is correlated
cross-implementation evidence, not an independent oracle or a measured ledger.
Only its source/output manifest hashes are verified here; it is not rerun.

Keep D50 S0 unchanged. BOUNDARY already requires the evaluator to check
Governance.governanceChainId and maxGovernanceTtl, and this collector acquires
both. No new shared field, count, dependency or owner change is requested.
Agent2's implementation remains explicitly NOT_READY; owner suite counts are
not rerun or adopted. Ledger source/exports remain unchanged from the reviewed
85c59f5 snapshot. No new source READY or execution ACK is inferred.

Next: wire these independently acquired observations into signature context;
join exporter history/orphan/WAL/native completeness; then fault oracle/finite
model. Actual use needs complete reviewed owner source READYs and a separate
source/tools/config/run FREEZE with exact affected ACKs before services. No live
RPC, deployment, service lease, new E parity, TLC, integrated F case or timing
measurement occurred. Historical qualified E unchanged; all32 F cases/GateF
NOT_RUN; G locked. No human action required.

Limits: fabricated but internally consistent RPC remains indistinguishable;
bracketing misses transient drift restored between checks; pinned ABIs and masked
code equality do not attest constructor/source truth. No cryptographic protocol,
host-independent witness, durable store, power-loss or consensus theorem follows.
Injected transports that block forever cannot be preempted by the aggregate
deadline; use the separately bounded real RpcClient in an approved recipe.
