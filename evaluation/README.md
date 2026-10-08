# Agent 3 evaluation — E0 candidate foundation

This is a **paper-derived HMBC2020 reconstruction**. E0 v1 bytes are frozen after exact affected reviews and compatibility checks; both peer frozen mapping ACKs still precede E0 closure/E1 unlock. No E/F/G gate has passed. See interfaces/v1/FREEZE.json and communication/E0_ACCEPTANCE.md.

Implemented owned preparation:

- Independent EIP-712/array hash/signature/mutation verification using eth-account/eth-abi, not ledger imports.
- Strict candidate schemas with integer widths, canonical encodings, signatures and ordering; candidate control/result record envelopes.
- Positive/denial access oracles that reject grant-all/deny-all, corrupted bindings, missing/reordered evidence and duplicate grant/outcome transitions.
- Source/assumption registers, input/output hashes, command failure/timeout records, newest-communication provenance scan.
- Fail-closed runner/gate preflights. These record blockers; they do **not** implement the real C-E1 provider runner or final RQ adjudication.
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

The last two commands exit **2/BLOCKED** while E0/agent-2 dependencies are unresolved. Output directories must be new; existing evidence is never overwritten. Fetch `origin` separately before scanning peers. The scan reads every remote communication tree without switching branches; it preserves file-changing commit hashes and flags incomparable content. An immutable outbox message is delivered only after its sender pushes it.

`toolchain.json` records exact local versions, primary download/docs URLs and artifact hashes. The exact shared E0 toolchain/schema mapping is frozen; peer packaging/version ACKs are pending. Public vector keys are synthetic TEST-ONLY fixtures. Frozen schema/vector copies live under `interfaces/v1`; candidate copies remain untouched for byte provenance. The current validator still reads the identical proposal schema; wiring the real C-E1 runner waits for mapping ACKs. Positive trace fixtures use abstract synthetic bindings to test the oracle; they are not executable live-chain transactions. The real C-E1 collector still must normalize native ledger/worker evidence after E1 unlock; root preflight retains legacy v0 metadata and BLOCKED status.

Read `reports/E0-progress.md` for completed evidence, missing requirements and next steps. Never use these unit/toolchain results as a two-chain service integration, measured ABE implementation or Byzantine-consensus claim.
