# Agent 3 evaluation — E1 runner under construction

This is a **paper-derived HMBC2020 reconstruction**. E0 v1 bytes are frozen after exact affected reviews and compatibility checks; both exact frozen mapping ACKs are verified, closing E0 and unlocking E1; the real C-E1 runner/service integration remains pending. No E/F/G gate has passed. See interfaces/v1/FREEZE.json and communication/E0_ACCEPTANCE.md.

Implemented owned preparation:

- Independent EIP-712/array hash/signature/mutation verification using eth-account/eth-abi, not ledger imports.
- Strict candidate schemas with integer widths, canonical encodings, signatures and ordering; candidate control/result record envelopes.
- Positive/denial access oracles that reject grant-all/deny-all, corrupted bindings, missing/reordered evidence and duplicate grant/outcome transitions.
- Source/assumption registers, input/output hashes, command failure/timeout records, newest-communication provenance scan.
- Fail-closed runner/gate preflights. These record blockers; they do **not** implement the real C-E1 provider runner or final RQ adjudication.
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

The last two commands exit **2/BLOCKED** while the real C-E1 provider runner/service integration remains incomplete. Output directories must be new; existing evidence is never overwritten. Fetch `origin` separately before scanning peers. The scan reads every remote communication tree without switching branches; it preserves file-changing commit hashes and flags incomparable content. An immutable outbox message is delivered only after its sender pushes it.

`toolchain.json` records exact local versions, primary download/docs URLs and artifact hashes. The exact shared E0 toolchain/schema mapping is frozen; peer packaging/version ACKs are recorded in communication/E0_MAPPING_ACKS.json. Public vector keys are synthetic TEST-ONLY fixtures. Frozen schema/vector copies live under `interfaces/v1`; candidate copies remain untouched for byte provenance. The current validator still reads the identical proposal schema; the real C-E1 runner/lifecycle is now permitted; reviewed owner service READY and exact integration FREEZE ACKs precede actual services. Positive trace fixtures use abstract synthetic bindings to test the oracle; they are not executable live-chain transactions. The real C-E1 collector still must normalize native ledger/worker evidence after E1 unlock; root preflight retains legacy v0 metadata and BLOCKED status.

Read `reports/E0-progress.md` for completed evidence, missing requirements and next steps. Never use these unit/toolchain results as a two-chain service integration, measured ABE implementation or Byzantine-consensus claim.

Current E1 owner inputs: ledger91add8c/A1-0028 and protocol34de384f/A2-0014 reviewed. Native collector/actual runner and signed public Alice/Bob bootstrap input are pending. A3-0024 requests the owner bootstrap producer while preserving Option A key custody. Named crash hooks are absent from the process adapter; E2/E3 is later work and external kill alone cannot prove named crash schedules. Exact integration FREEZE ACKs precede actual services.
