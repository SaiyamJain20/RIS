# Masked runtime check — D-f / D50 input (agent 1, F0, 2026-11-03)

**Purpose.** A2-0041 (D50) section 4 says the live code hash includes constructor immutables. It also says that showing the deployed code is the compiled build needs a comparison that masks those immutables, using agent 1's `immutableReferences`. This measures that premise on the **E code** (pin 933d2a7). No contract, export format or interface changed; the export of `immutableReferences` is still a successor-schema proposal (A1-0094).

## Method

- **Tool:** `ledger/tools/check_masked_runtime.py`, standard library only.
- **Per contract:**
  1. read `eth_getCode`;
  2. zero every `deployedBytecode.immutableReferences` range of the Forge artifact (`ledger/out/<C>.sol/<C>.json`);
  3. compare the sha256 with the compiled runtime and with the deployment manifest's `runtimeSha256`.
- **Chains:** local Anvil 1.8.5, chain ids 18545 and 28545, `--block-time 1`, ports 38545 and 48545. Agent 1's own processes, stopped afterwards.
- **Deployment:** `ledger/tools/deploy_local.sh ... <profile> complete-details <run-id>` with `LEDGER_DEPLOY_FAST=1` and the Anvil default dev key 0. The key is not recorded. Outputs were moved out of `exports/`, so no deployment directory was added to the repository.

## Runs and results

| Run | Deployments | Masked live code = compiled = manifest `runtimeSha256` | Raw live hash |
|---|---|---|---|
| Same chain pair (`same-chain-three-deployments.json`) | repaired-e, paper-strict, mutant-no-nonce at different addresses | 18 of 18 | 5 contracts differ; LSC is identical (its immutables, `detailMode` and `deployer`, are equal) |
| **Fresh chain pair per profile** (`fresh-chain-*.json`, `fresh-run.sh.txt`) | the same three profiles, **identical addresses** for all six contracts | 18 of 18 | TMSC, PSC, ACSC and KSSC each differ across the three profiles (profile and mutations are immutables); LSC and RSC are identical (no profile immutables) |

**Reading:**
- On fresh chains the addresses repeat. This confirms A2-0039 D-2: an address-only fingerprint cannot separate the profiles.
- The **raw live code hash does separate them**, through the four profile-carrying contracts.
- The **masked comparison establishes the compiled build** for every contract.

So D50's live-code identity and the masked build check both work on the E code, and `immutableReferences` from the Forge artifact are sufficient for the mask.

## Limits

- E code only, not the F code: Governance does not exist yet.
- One local host and one trial per profile.
- The compiler settings are those of `foundry.toml`, with metadata hash `ipfs`. Any change to settings changes the compiled runtime.
- The raw hashes of LSC and RSC alone would not separate profiles; the binding relies on TMSC, PSC, ACSC and KSSC, plus addresses and the storage reads of D50.

Commands, exit codes: every deploy exited 0 and every check exited 0 (see the `fresh-run.sh.txt` loop output, reproduced in A1-0094). Versions are in `versions.txt`.
