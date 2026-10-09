# agent-2 local reproduction of agent-1 ledger 54262c2 (2026-10-07, agent-2 machine)

Not an integration run and not E1: ledger-only checks that agent 2's machine can build and drive agent 1's exact exports.
Snapshot: `git archive 54262c2e4a1cfad26ba3a9445fcbda584f6eb491` extracted to disposable scratch; no peer source edited, nothing added to this repository.

Toolchain (pins from agent-3 evaluation/toolchain.json, checksum-verified on this machine):
- Foundry v1.8.5 commit 51a52c59cffd940f76eddd0b4bb1791aa4b5ac7f; asset SHA-256 6c66ffcc55fa4249197721baa3098bc208014ea1d8aa04b2ed50ac6bccffb226 (OK)
- forge 06c477ae..., anvil 00f97668..., cast 1eb1eecf... binary SHA-256 all equal the toolchain.json values
- solc 0.8.37 fetched by forge (svm)

| Command (in the snapshot, repository root) | Exit | Result |
|---|---|---|
| `forge test --root ledger` | 0 | 19 suites, 162 passed, 0 failed (agent-1 reports the same count in A1-0011) |
| two Anvil nodes on 38545 (chain 18545) and 48545 (chain 28545), both started and stopped by agent 2 | - | both ports verified free before start and after stop; no other process touched |
| `DEPLOYER_PK=<anvil default account 0, public test key> ledger/tools/deploy_local.sh http://127.0.0.1:38545 http://127.0.0.1:48545 repaired-e complete-details a2-verify` | 0 | deployment.json sha256 7f02b24c17262b6d4c70d1baf9c808265408af7e640eca07f28cea4b51cc4618 |
| `ledger/tools/e2e_smoke.sh <pbc> <dbc> ledger/exports/deployments/a2-verify/deployment.json 1` | 0 | 5/5 stages ok: pbc-setup, pbc-request, dbc-deliver, dbc-receipt, pbc-outcome |

Smoke outputs: requestDigest 0x31c9e222..., grantId 0xed35eb73..., PBC request log 5 and outcome log 6 (LSC count 6), DBC `getGrant` returns the matching
request digest/dataId/gid, keyEpoch 0, positive expiry and allowed=true, DBC accessLogCount 1. This confirms the repaired-e legitimate flow including the GrantReceipt
path (A1-0011) on live chains from agent 2's machine.

Limits: the smoke signs as user/witness/relay inside Forge, so it exercises no agent-2 service; it is not the integration run. The deployment manifest's addresses/RPC URLs are
machine-local. `forge test` was run once; no mutant suites or cast cross-checks were re-run by agent 2.
