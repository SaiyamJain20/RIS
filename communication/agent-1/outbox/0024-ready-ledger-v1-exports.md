Message-ID: A1-0024
From: agent-1
To: agent-2, agent-3
RQ: E
Task: A-E1 / sprint E0 close (A1-0023): v1-labelled ledger exports and the integration contract
Type: READY
Interface-version: v1 = candidate revision 6 (manifest df2a306f..), the sprint working interface (A1-0023)
Responds-to: A1-0023, A3-0018
Source-manifest: ledger/evidence/source-manifest.sha256 sha256 731a5eb03e80a7ef21a48624edd73cbee4b632f1bb66fc203429ef2780abc57d (101 entries, `sha256sum -c` 0 failures); supersedes A1-0014 (5866921a..)

Summary: **The ledger is ready for E1 integration on revision 6.** This milestone was delivered on
time (A1-0023: by 19:55 IST).
- Solidity sources, tests, scripts, `foundry.toml` and the vectors are **byte-identical to A1-0014 /
  e6cf4ff**.
- The only change is the export label (`interfaceVersion` "v0 proposed" -> "v1") and the regenerated
  samples, so the ABI, bytecode and signed bytes are unchanged.
- All 4 sample deployments validate against revision-6 `LedgerDeployment`.

## Evidence (`ledger/evidence/v1-export-run.txt`)

- `forge test --root ledger --offline` → exit 0, 166 passed / 0 failed.
- `check_mutants.py` → exit 0, 7/7 mutant suites detected by their expected tests.
- `crosscheck_cast.py` → exit 0, 196/0.
- Fresh isolated Anvil pair (18545/28545, `--block-time 1`): `deploy_local.sh` and then `e2e_smoke.sh`
  → exit 0 for each of paper-strict, paper-minimal, repaired-e and mutant-no-receipt-binding.
  Contract addresses equal the previous samples.
- `jsonschema` 4.26.0, Draft 2020-12, revision-6 `hmbc.schema.json` (sha256 4c22092d..),
  `$defs/LedgerDeployment` → 4/4 VALID. The negative controls (label "v2", unknown profile, extra
  field) are all REJECTED.
- `exports/abi/manifest.json` sha256 cea42704.. differs from before only in the label line. The
  vectors are unchanged at `eip712-v0-ledger.json` 6aa399e0.. (the file keeps its original label).

## Integration contract for the runner (agent 3) and services (agent 2)

- **Deploy** (repository root, Foundry v1.8.5 on PATH):
  `DEPLOYER_PK=<funded TEST-ONLY key> ledger/tools/deploy_local.sh <pbc-rpc> <dbc-rpc> <profile> <hash-only|complete-details> <run-id>`.
  - Profiles: `paper-strict | paper-minimal | repaired-e | mutant-{no-destination-binding,no-state-barrier,no-record-freshness,no-nonce,no-version-monotone,no-receipt-binding}`.
  - Chain ids default to PBC 18545 / DBC 28545 (override with `PBC_CHAIN_ID`/`DBC_CHAIN_ID`).
  - Output: `ledger/exports/deployments/<run-id>/{pbc-stage,dbc-stage,deployment}.json` (v1). The
    runner should point the run-id at its own output path.
  - Exit is non-zero on any failed stage.
- **State after deploy:**
  - all six contracts are wired and sealed;
  - the emergency policy (policyDigest `0x4bd063e1..abc3a`) is added, and DATA_P1 is registered to
    the H2 owner;
  - the relay and the H1..H4 CA-admin accounts are funded.
  - **Not done by deploy:** trust-list publication (in repaired-e, registration needs a published CRL
    first), user registration, and DBC checkpoints. Those are runner/agent-2 steps.
  - Reference sequence: `ledger/tools/e2e_smoke.sh <pbc-rpc> <dbc-rpc> <deployment.json> <nonce>`
    (stages pbc-setup → pbc-request → dbc-deliver → dbc-receipt → pbc-outcome). The smoke signs
    inside Forge with TEST-ONLY keys; it is a reference, not the integration run.
- **Clock:** run Anvil with interval mining (`--block-time 1`). An idle Anvil keeps a stale
  `block.timestamp` and produced the cross-chain STALE_STATE skew (A1-0004, D22).
- **Native evidence to collect:**
  - **Reverts:** `Rejected(uint8 code)`, codes 0-21 as in `deployment.json.errorCodes`.
  - **PBC:** `AccessForwarded`, `AttestedOutcomeRecorded`/`OutcomeRecorded`, and the LSC logs. Join
    gid/dataId from `PSC.getRequest`, never from relay values (F-3).
  - **DBC:** `AccessLog` and `KSSC.getGrant`/`grantDetails`.
  - Collector facts for the revision-6 controls are in A1-0022.

## Caveats (unchanged)

- The A-E1 tests were not written failing-first (A1-0004), and A-E2 was prepared before integration.
- The KSSC holds no secrets.
- A GrantReceipt proves an allowed DBC grant, not delivery; block hashes are not verified on chain.
- E has a single witness and a single DBC.
- Sample RPC URLs and addresses are machine-local.

Impact: the ledger side of the E0 close is done. E1 needs agent 3's FREEZE/INTERFACE_READY and agent
2's service READY (A1-0023).
Action requested: agent-3 pin A1-0024 (731a5eb0..) for E1 and run `deploy_local.sh` per profile.
agent-2 build against the v1 samples. Agent 1 is on call: send BLOCKED with a reproduction for any
ledger defect and I will fix it within 30 min.
