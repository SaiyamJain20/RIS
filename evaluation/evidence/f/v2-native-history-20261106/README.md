# Raw block and death joins — C-F1, 2026-11-06

Classification: **synthetic tested reconstruction/extension result**. This is an
internal evaluator slice, not an HMBC paper vulnerability or integrated F case.

`evaluation.witness_native_v2.verify_native_history` composes signed-history and
anchored context checks with caller-supplied raw block/ABI captures. Last stored,
signing, death, fault and clear observations require exact chain/number/hash/time.
Embedded PBC source blocks and receipt DBC references require number/hash only;
their signed layouts carry no timestamp. Safe intervals refuse conflicting hashes
at one chain height; faulted/cleared intervals remain explicitly outside that
assumption. The API changes no existing consumer or published/default-v1 bytes.

Deaths use owner public ABIs pinned by the caller's reviewed manifest:

- Expiry: block timestamp joined to every digest's declared expiresAt.
- Checkpoint/decision sequence: KSSC.currentCheckpoint exists and its sequence
  equals declared observed; the existing checker supplies >= / > relations.
- Governance: Governance.governanceNonce equals declared observed.
- ALLOW decision grant: derive grant ID from requestDigest/KSSC/DBC chain,
  then KSSC.grantDetails must report exists and matching requestDigest.
- Executed receipt: PSC.getRequest for that exact digest has status2
  (OUTCOME_RECORDED). This is not evidence of payload delivery.

Every call matches chain, death block hash, target and complete calldata. The
existing strict ABI codec refuses trailing/malformed return bytes. Exact ABI and
capture inventories are required; missing/duplicate/unused captures refuse.
Identical required reads share one capture. Inputs remain unchanged. Existing
orphan/generation/A->B->A rules, fault/clear labels and bit1/bit5 exclusions remain.

Fresh verification, UTC/argv/exits and raw/compressed hashes in commands.json:

- Genuine missing-module RED:63 failures.
- Initial implementation:62 PASS/1 FAIL, a malformed-signature test fixture
  expected ValueError but hit schema ValidationError first. Replaced it with a
  canonical wrong-owner signature; no production check weakened.
- Final new suite: **68 PASS**, including all eight type/death combinations,
  faulted/cleared same-height forks, shared calls and mutation exclusions.
- Seven deliberate narrow in-memory bypasses each admit bad captures refused by
  real code: number, timestamp, checkpoint, governance nonce, grant existence,
  receipt status and unused call. Actual source remains unchanged.
- Combined v2 schema/certificate/context/observation/signing/history/store/export/
  native suite: **754 PASS in60.43s**, exit0.
- Bare root `.venv/bin/python -m pytest -q`: **2439 PASS in462.01s**,
  command462.340s/exit0. All **246 selected inputs and181 complete execution
  sources** are unchanged before/after; the latter includes every discovered
  execution Python file, including evidence helpers. inputs-frozen.json pins
  exact bytes; verification.json records its SHA256.
- Python3.13.13, SQLite3.47.2, Git2.54.0, pytest9.0.2, jsonschema4.26.0,
  eth-account0.14.0. No dependency changes.

Exact peer review: Agent1 `8c0285ffa6986858caeb0140b930bf5db759fdc0` unchanged;
Agent2 advanced from254faac to `9184e3bbd961f5cf461320a9ef3edaceeea76af7`.
Read whole startup module and its tests/mutation definitions plus newest
STATUS/HANDOFF. Startup uses injected chain/worker/view/transport, explicitly
**NOT_READY**. Owner27tests/15mutants/360related counts are read, not rerun/adopted;
full owner suite was not rerun. No new ACK since A1-0116/A2-0062. Exact changed
path hashes/file-changing commits: peer-review.json; full369-path communication
provenance has no divergence/ambiguity.429 reviewed ledger READY entries,
52F0 pins,31 published interface payloads and four copied fixtures verify.

Limits: no RPC collector, authenticated chain/header/call provenance, actual owner
runtime/store/exporter, source-state truth or sign-time semantic validation is
established. Supplied bytes can be fabricated consistently; this pure checker
cannot detect that. Matching block/getter bytes do not prove complete signing
history, logical store/export row completeness, arrival chronology, persistence,
power-loss recovery, actual transport/timing or safe consensus. No live RPC, new
E parity, TLC, integrated F case or gate result is claimed. Historical qualified E
unchanged;32Fcases/GateF NOT_RUN/G locked. Full reviewed owner READYs/mapping and
separate complete exact source/tools/config/run FREEZE ACKs precede services.

Next C-F1 work: an authorized raw history acquisition layer retaining actual RPC
parameters and chain-identity brackets; source-state/sign-time semantic joins;
producer-specific exporter/store completeness only when full owner READY/path/
locking review permits; independent fault oracle/finite model. Review is
correlated author review under the no-extra-agents restriction (REVIEW.md).
No peer edits/worktrees/extra agents/dependencies/main push. Scheduled file flock
was the first tool operation; both scheduled/coordinator locks stay held through
publication and are released with independent reacquisition checks afterward.

Reproduce `.venv/bin/python -m pytest evaluation/tests/test_witness_native_v2.py -q`,
the combined/root commands in commands.json, sensitivity.py, then verify.py.
Logs are lossless gzip; raw snapshots from future real stores must stay private.
