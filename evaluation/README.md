**Current C-E2 checkpoint (2026-10-09 IST):** actual scoped ProVerif user/witness tuple agreement, reachable legitimate grants and unreachable policy-denied grants, plus a destination-omitting mutant counterexample, are saved. Seven formal/sensitivity checks and421 root tests pass. This is a fixed-name non-injective honest-key/witness abstraction; no replay, recovery or implementation proof. All56 real Agent3 fault schedules/gate E remain NOT_RUN; F/G locked. [Evidence](evidence/e2/formal-and-hook-review-20261009/README.md). A3-0032 exact TEST-ONLY startup supplement awaits both scoped ACKs; complete E2 runner/configuration FREEZE and both exact plan ACKs precede services. Earlier status below is historical.

**Current checkpoint2026-10-08 UTC /2026-10-09 IST:** C-E1 COMPLETE: actual fresh two-chain/service controls9/9 across paper-strict, paper-minimal and repaired-e; CLI0/E1_CONTROL_PASS in356.061s. Exact A1-0038/2f5e376 and A2-0019/6d2c867 ACKs verified for A3-0029/78e195f5.. before services. Sources stable; all9 owned PBC/DBC/adapter processes exit0/absent. A3-0029 RELEASED after completed run. E2/E3 now permitted within E/RQ1; all56 catalog schedules and every RQ gate remain NOT_RUN, four paper crash cases BLOCKED/unproved; F/G locked. Evidence evaluation/evidence/e1/integrated-controls-20261008/README.md. This paragraph supersedes prior milestone status below; prior evidence remains historical.

# Agent 3 evaluation — E1 public runner awaiting exact ACKs

**Current E1 checkpoint (2026-10-08 UTC):** actual paper-strict3/3 controls pass; all-profile run failed on the runner’s TIME_WAIT port probe before second-profile startup. Probe fixed with414 tests; A3-0029 revised plan 78e195f57872e0732394e3c546f665e1062b4a360083d2ee0a407d5def33b008 awaits both new exact ACKs. E1 incomplete; E2/E3/F/G remain gated. See [evaluation/evidence/e1/port-recovery-20261008/README.md](evidence/e1/port-recovery-20261008/README.md). Earlier checkpoint text below is historical.


This is a **paper-derived HMBC2020 reconstruction**. E0 v1 bytes are frozen after exact affected reviews and compatibility checks; both exact frozen mapping ACKs are verified, closing E0 and unlocking E1; the C-E1 public runner is implemented/unit verified; exact A3-0027 plan ACKs and real service integration remain pending. No E/F/G gate has passed. See interfaces/v1/FREEZE.json and communication/E0_ACCEPTANCE.md.

Implemented owned preparation:

- Independent EIP-712/array hash/signature/mutation verification using eth-account/eth-abi, not ledger imports.
- Strict candidate schemas with integer widths, canonical encodings, signatures and ordering; candidate control/result record envelopes.
- Positive/denial access oracles that reject grant-all/deny-all, corrupted bindings, missing/reordered evidence and duplicate grant/outcome transitions.
- Source/assumption registers, input/output hashes, command failure/timeout records, newest-communication provenance scan.
- Fail-closed runner/gate preflights. Default preflights record blockers; explicit integration plans dispatch the public C-E1 runner. Final RQ adjudication remains unproved.
- Owned JSON-lines and direct-service lifecycle with finite budgets, file logs, digest-only transport transcripts, parser/frame rejection and owned-handle cleanup. Tests use real synthetic children; readiness probes must bound their own I/O and descendant supervision is not provided. These checks are not contract/service integration.
- ProVerif toolchain smoke only; the E correspondence model is an E2 deliverable after E1 integration.

Reproduce from the repository root:

```bash
uv sync --frozen
.venv/bin/python -m pytest evaluation/tests -q
.venv/bin/python -m evaluation.vectors interfaces/vectors/eip712-agent1-candidate.json
.venv/bin/python -m evaluation.peers --output /tmp/hmbc-peer-state.json
.venv/bin/python -m evaluation.run --rq E --profile repaired-e --output evaluation/runs/new-e0-preflight
.venv/bin/python -m evaluation.gate --rq E --run evaluation/runs/new-e0-preflight
```

The last two commands exit **2/BLOCKED** while real C-E1 integration remains unproved. Output directories must be new; existing evidence is never overwritten. Fetch `origin` separately before scanning peers. The scan reads every remote communication tree without switching branches; it preserves file-changing commit hashes and flags incomparable content. An immutable outbox message is delivered only after its sender pushes it.

`toolchain.json` records exact local versions, primary download/docs URLs and artifact hashes. The exact shared E0 toolchain/schema mapping is frozen; peer packaging/version ACKs are recorded in communication/E0_MAPPING_ACKS.json. Public vector keys are synthetic TEST-ONLY fixtures. Frozen schema/vector copies live under `interfaces/v1`; candidate copies remain untouched for byte provenance. The current validator still reads the identical proposal schema; the real C-E1 runner/lifecycle is now permitted; reviewed owner service READY and exact integration FREEZE ACKs precede actual services. Positive trace fixtures use abstract synthetic bindings to test the oracle; they are not executable live-chain transactions. The real C-E1 collector still must normalize native ledger/worker evidence after E1 unlock; root preflight retains legacy v0 metadata and BLOCKED status.

Read `reports/E0-progress.md` for completed evidence, missing requirements and next steps. Never use these unit/toolchain results as a two-chain service integration, measured ABE implementation or Byzantine-consensus claim.

Current E1 owner inputs: ledger9d6911d/A1-0030 public Alice/Bob bootstrap and protocol465aff5/A2-0016 exporter successor source-reviewed; Option A key custody preserved. Complete public runner is implemented; actual integration remains unproved. Named crash hooks are absent from the process adapter; E2/E3 is later work and external kill alone cannot prove named crash schedules. Exact integration FREEZE ACKs precede actual services.

C-E1 collector modules: `evm.py` (hash-bound public ABI), `native.py` (receipt/view joins), `rpc.py` (bounded loopback Cast commands), `worker_evidence.py` (redacted exporter consistency and response-cache commitments). They check supplied facts; the complete public runner now implements native/provider/nonce/expiry/denial joins, but actual integration remains unproved. Fresh265-test verification/evidence: `evaluation/evidence/e1/collector-20261008/`. No integration or gate result.

C-E1 bootstrap executor: `bootstrap.py` checks the immutable frozen schemas and
EIP-712 types against the exact deployment bytes, observed producer block and
authority versions. It independently checks all seven signatures, issuer/admin
roles, public fixture GIDs, recipient/certificate/bundle joins and expirations.
`chain.py` submits public ABI calldata with TEST-ONLY relay/CA-admin keys only,
binds native receipts to the locally signed hash/sender/call, and reads historical
views with block identity checks. `bootstrap_execution.py` runs wrong-admin H2
rejection before legitimate H2 publication, verifies rollback and all trust-list
event/state joins, then registers Alice and policy-denied Bob. No peer-owned
authority/GID/user/witness key is derived or loaded by these modules.

Verification:335 evaluator tests pass, including70 new synthetic checks; source
stable during the command. Evidence: `evaluation/evidence/e1/bootstrap-executor-20261008/`.
The bootstrap component has not run against services. Its controlled RPC replies
do not prove Anvil trace compatibility, fresh deployment correctness or integration.
The public access/JSON-lines runner is implemented; real9 E1 controls and exact
integration FREEZE ACKs are still required. Root preflight remains legacy/BLOCKED; every RQ gate is
NOT_RUN. WrongIssuerAdmin is baseline issuer restriction evidence, not a repair.

Current public C-E1 runner: `access_artifacts.py` verifies prepared request,
checkpoint and decision signatures against native observations.
`access_execution.py` joins ordered native request/log/credential state, policy,
grant/nonce/original-expiry/recipient and redacted worker cache/send evidence;
checks symbolic completion/outcome and denial rollback. `e1.py` orchestrates
pinned snapshots, tools/environment/dependencies, fresh default-slow two-chain
deployments/public bootstrap/adapter/exporter and all3 profiles.

411 full evaluator tests pass, source stable; synthetic controls are not real
chain integration. Evidence evaluation/evidence/e1/access-runner-20261008/; plan SHA-256 `1899126e37c683fd9b4334787f71131250d7950506d845286220249b526a4b31`, FREEZE A3-0027. Both exact
owner ACKs of that plan are required before snapshots/services. Their ACK index
has keys agent-1 and agent-2, each with real immutable Git commit/path/sha256;
headers/owner ancestry are checked. No fabricated ACK index is supplied.

After both exact ACKs, execute from the root with a fresh output directory:

```bash
.venv/bin/python -m evaluation.e1 --plan evaluation/evidence/e1/access-runner-20261008/integration-plan.json --acks /absolute/path/to/exact-ack-index.json --output /absolute/path/to/fresh-private-output
```

The coordinator must hold the scheduled guard and separate Git/service lock.
No ACKs means exit2/BLOCKED before startup. Changed runtime/tool/config bytes
require new plan review/ACKs. Occupied ports refuse. Only owned service handles
and fresh synchronous shell/Forge command groups are stopped; command timeout
and cancellation clean their group while the direct child is unreaped.
Real9 controls remain unrun; all catalog/RQ gates NOT_RUN; E2/E3/F/G stay gated.
Earlier bootstrap/collector paragraphs above retain historical verification counts.
