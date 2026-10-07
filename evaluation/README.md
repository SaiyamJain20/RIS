# Agent 3 evaluation — E0 candidate foundation

This is a **paper-derived HMBC2020 reconstruction**. E0 remains open; no E/F/G gate has passed. Agent 1's exact READY handoff has been reproduced locally; Agent 2's E0 public adapter and scoped review are available and independently reproduced; final E0 boundary acceptance remains pending.

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

`toolchain.json` records exact local versions, primary download/docs URLs and artifact hashes. The shared toolchain/schema freeze is still pending. Public vector keys are synthetic TEST-ONLY fixtures. Candidate schemas live under `interfaces/proposals/v1`; they do not change the normative v0 interface. Positive trace fixtures use abstract synthetic bindings to test the oracle; they are not executable live-chain transactions. Agent-2's frozen result/deployment/input schemas are required before the real collector can normalize ledger/worker events.

Read `reports/E0-progress.md` for completed evidence, missing requirements and next steps. Never use these unit/toolchain results as a two-chain service integration, measured ABE implementation or Byzantine-consensus claim.
