# Module 1: Ledger and policy

Owner: **agent 1**. Paper-derived reconstruction of the six HMBC2020 contract roles. It is not the
authors' code (which is unavailable). Interface status: **v0 proposed**; my concrete v1 proposal is
message A1-0003. Phase: E (RQ1). F and G work is locked until their gates pass.

Read [the root plan](../PLAN.md), [specification](../SPEC.md), [interfaces](../interfaces/README.md),
and [communication rules](../communication/PROTOCOL.md). Source and actuator choices are in
[A1-0002](../communication/agent-1/outbox/0002-review-e0-contract-source-permissions.md).

## Layout

| Path | Content |
|---|---|
| `src/types/ProtocolTypes.sol` | Structs, `ErrorCode` + `Rejected(uint8)`, profiles, EIP-712 hashing (`HMBCHash`) |
| `src/{RSC,TMSC,PSC,LSC}.sol` | PBC roles: registration, trust anchors, proxy, logging |
| `src/{ACSC,KSSC}.sol` | DBC roles: policy enforcement, grant/checkpoint/nonce state |
| `src/DecisionVerifier.sol` | repaired-e decision-certificate checks (fixed check order) |
| `src/lib/` | canonical signature recovery + quorum check, one-time bootstrap wiring |
| `test/` | `AccessFlow.t.sol`, `TrustAnchors.t.sol` (each runs under all three profiles), fixture, cheatcode interface |
| `script/` | `Deploy.s.sol` (staged two-chain deployment), `ExportVectors.s.sol`, `E2ESmoke.s.sol`, `FixtureConfig.sol` |
| `tools/` | `deploy_local.sh`, `e2e_smoke.sh`, `export_abi.py`, `crosscheck_cast.py`, `mutation_smoke.py` (stdlib Python) |
| `exports/abi/` | Compiler-generated ABIs + `manifest.json` (source/ABI hashes). Never hand-edited. |
| `exports/vectors/` | EIP-712 vectors + standard typed-data JSON for independent tools |
| `exports/deployments/sample-*` | Sample deployment manifests from agent 1's local Anvil smoke (addresses are local, not integration) |
| `evidence/` | Agent-1 test evidence (mutation smoke report) |
| `toolchain.json` | Pinned Foundry/solc versions and hashes |

## Profiles (deployment-time, immutable)

`0 PAPER_STRICT`, `1 PAPER_MINIMAL`, `2 REPAIRED_E`. Deliberate check-removal mutants for A-E2 have
not been added yet. The `tools/mutation_smoke.py` edits are throwaway test-sensitivity checks, not
deployment profiles. `LogDetailMode`: `0 HASH_ONLY` (V-B3), `1 COMPLETE_DETAILS` (III-D4).

## Commands (run from the repository root; Foundry v1.8.5, solc 0.8.37)

```bash
forge test --root ledger                                   # contract suite
forge script ledger/script/ExportVectors.s.sol:ExportVectors --root ledger   # regenerate vectors
python3 -I ledger/tools/crosscheck_cast.py                 # vectors vs cast's EIP-712 encoder
python3 -I ledger/tools/mutation_smoke.py ledger/evidence/ae1-mutation-smoke.json
forge build --root ledger && python3 -I ledger/tools/export_abi.py           # regenerate ABIs
# Two running chains (owned by the caller). Never run this against chains you do not own:
DEPLOYER_PK=0x... ledger/tools/deploy_local.sh <pbc-rpc> <dbc-rpc> <profile> <log-mode> <run-id>
ledger/tools/e2e_smoke.sh <pbc-rpc> <dbc-rpc> ledger/exports/deployments/<run-id>/deployment.json <nonce>
```

The ledger has no Solidity dependencies: no forge-std and no submodules, so nothing mutates Git.

## Known limits

- The KSSC holds authorization state only. The off-chain key worker holds temporal keys (SPEC
  section 3); this is a deliberate change from HMBC's isolated on-chain keys.
- Single DBC, four fixed synthetic authorities. addCA/removeCA/majorityConsent/retrieveLog revert
  `NOT_IMPLEMENTED_IN_PHASE` (phase F).
- A grant authorizes a release. It is not evidence of delivery. Outcome logging depends on the
  relay reporting it.
- The witness/relay/user signing in `E2ESmoke.s.sol` runs inside Forge with TEST-ONLY keys. It is a
  ledger smoke, not the integration run.

## Assigned tasks

A-E1, A-E2, A-F1, A-G1. The authoritative task steps and file lists are in `PLAN.md`. Status and
evidence live in `communication/agent-1/STATUS.md`, `HANDOFF.md` and the outbox.

## Module handoff

Publish a READY message in `communication/agent-1/outbox/` with files, interface version, hashes,
test command/output and limits. Under the user's multi-machine instruction (A1-0001), agent 1
pushes these to branch `agent-1`. During an integration freeze, acknowledge it and stop editing the
frozen paths.
