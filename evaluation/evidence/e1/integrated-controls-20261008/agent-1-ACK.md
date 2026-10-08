Message-ID: A1-0038
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: C-E1 revised integration FREEZE E1-20261008-port-recovery, ledger-scope ACK
Type: ACK
Interface-version: v1
Responds-to: A3-0029
Accepted-plan-sha256: 78e195f57872e0732394e3c546f665e1062b4a360083d2ee0a407d5def33b008
Source-manifest: ledger commit 9d6911d9a35c7d20b3e0226400f8f0fcc99ef256, ledger/evidence/source-manifest.sha256 sha256 ec213160ffccf2affb3d6556f8d62b6f35aaec44249a21fd065e997e6c586f98 (106 entries); plan read from origin/agent-3 95392cc at evaluation/evidence/e1/port-recovery-20261008/integration-plan.json

Summary: **Agent 1 ACKs the exact revised plan 78e195f5.. for the ledger scope.** The scope and
exclusions are those of A1-0037, which covered only the old bytes 1899126e... There are no conflicts.
The A3-0028 paper-strict live result (wrong-admin code 16, Alice allowed through release and outcome,
Bob code 9 with no grant and no nonce) matches the ledger's native expectations; no ledger defect was
involved.

## Verified (`git show 95392cc:…/integration-plan.json`, sha256 78e195f5..)

- **Plan delta against 1899126e..** Exactly three top-level fields differ:
  - `agent3Sources`, where only `evaluation/e1.py` changes;
  - `freezeMessage`;
  - `runId` (`E1-20261008-public-access` → `E1-20261008-port-recovery`).
- **Unchanged:** `deployerSignerRole` (relay), `deploymentSpeed` (owner default slow), `ports`,
  `chainIds`, `profiles`, `logDetailMode`, `budgets`, `tools` (same binary hashes as mine) and
  `serviceEnvironment`.
- **`evaluation/e1.py` diff (553ee21..95392cc):** one hunk, in the port probe:
  `setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)` before `bind`. No ledger command, argument or environment
  changes.
- **Ledger pin:** `owners.ledger` is commit 9d6911d, inventory ec213160... Its 106 entries are
  dict-equal to my 9d6911d manifest. As before, use the 9d6911d snapshot, not my branch tip.
- **Run id:** the deploy run-id becomes `E1-20261008-port-recovery-<profile>`, which matches
  `deploy_local.sh`'s `[A-Za-z0-9._-]+` rule.

## Accepted scope (unchanged from A1-0037)

- **Accepted:**
  - the ledger owner pin and inventory;
  - `deploy_local.sh` (relay `DEPLOYER_PK`, `LEDGER_DEPLOY_FAST=0`, pinned `FOUNDRY_SOLC`, chain
    ids 18545/28545, `complete-details`) and `bootstrap_fixture.sh`;
  - the relay-deployer choice and the 1000 ETH funding, with a **fresh chain pair per profile**
    (A1-0037 measured about 600 ETH left on the PBC after one relay-signed deployment);
  - the ledger ABI/runtime checks;
  - the wrong-admin-first sequencing;
  - the ledger-native expectations of the 9 controls.
- **Not accepted (outside agent 1's scope):** the runner/oracle internals, package pins, agent 2's
  scope, and machine-local paths.

Impact: with A2-0019 (same hash), the revised plan has both exact owner ACKs.
Action requested: agent-3 verify this message and run the fresh nine-control E1. Agent 1 stays on
call, with a 30-min fix or triage for any ledger defect. agent-2 none.
