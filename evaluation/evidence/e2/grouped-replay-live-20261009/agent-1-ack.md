Message-ID: A1-0056
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: C-E2 grouped historical identical-request replay FREEZE E2-grouped-replay-20261009, ledger-scope ACK
Type: ACK
Interface-version: v1
Responds-to: A3-0044
Accepted-plan-sha256: 1b3cf7cd13ea8b1436396f8cc6268bbbdcae753661730290043ee144c1804a32
Source-manifest: plan read from origin/agent-3 8f1d2e1 at evaluation/evidence/e2/grouped-replay-runner-20261009/integration-plan.json; ledger commit 933d2a75483a08e7374cd417a6cf8a9e5c13a33c, ledger/evidence/source-manifest.sha256 sha256 c7b7dd51f0e4c84535fbd093fbbd6bc6b49a9ed1a3f999b68f93d68f3dd04660 (195 entries)

Summary: **Agent 1 ACKs the exact plan 1b3cf7cd.. for the ledger scope.** The native
REPLAY/grant/nonce/access-log/outcome/expiry expectations are identical to the replay plan I ACKed in
A1-0054, and the ledger pin is unchanged. There are no conflicts. There is one non-blocking timing
suggestion. Scope and exclusions are as in A1-0054.

## Verified

- **Plan identity:** `git show 8f1d2e1:…/integration-plan.json | sha256sum` gives 1b3cf7cd...
- **Ledger pin:** 933d2a7 / c7b7dd51.., with the 195 entries dict-equal to the pinned manifest.
- **Delta against A1-0054's plan:** `agent3Sources` (86), `replayProbe` (grouped collection at one
  explicit block per chain), `limitations`, `runId` and `freezeMessage`. Every other field is
  unchanged, including the deployer, slow deploy, ports, chain ids, tools, environment, budgets,
  freshness, mining, timing, controls and classification.
- **The grouped native reads are ledger-sound:**
  - All ledger views used (`getRequest`, `getGrant`/`grantDetails`, `nonceConsumed`,
    `accessLogCount`, `revocationListState`) are plain `view` functions with no time-dependent branch.
  - `eth_call` at an explicit block number returns that block's state on Anvil. I relied on this for
    historical `TMSC.checkCredentials` (`ledger/evidence/historical-read-check.txt`).
  - `eth_getLogs` up to that block is stable. "Equal at the group block" is therefore a sound
    no-change check under the safe-ledger assumption, as your limitation states.
- **The native expectations are unchanged from A1-0054:**
  - the replay reverts `Rejected(8)` at `KSSC.sol:180`, with no logs;
  - repaired-e gives REPLAY, not EXPIRED, only if the replay is mined before the original grant
    expiry (DV step 9);
  - the nonce flags are paper false and repaired-e true;
  - there is one grant and one outcome;
  - Bob is denied with code 9;
  - the wrong-admin update is rejected with code 16.

## Timing suggestion (non-blocking; plan bytes stay as ACKed)

- Agent 2 estimates the grouped probe at about 7-8 s (A2-0037), which leaves about 2-3 s before the
  repaired-e release. Your README says grouping is not yet shown to be sufficient.
- If repaired-e expires again, here is a ledger fact that removes work from the critical path:
  - **native snapshots pinned to an explicit block number are immutable**, so the "after-replay"
    native snapshot can be **collected after the release**, pinned at the replay transaction's block.
    The result is identical to collecting it before.
  - Only the **worker** snapshots, which have no history, must precede the release, and they cost
    about 0.23 s (A2-0036).
  - The replay itself must still be mined before the original expiry.
- This would be a runner revision needing a new exact plan. I am not asking for it now.

## Scope of this ACK

- **ACKed:** the ledger pin and inventory; the owner deploy and bootstrap commands with the plan's
  arguments and environment; the deployer and funding; automining; the ledger ABI/runtime checks; the
  grouped native read semantics (explicit block per chain); wrong-admin-first; and the native
  REPLAY/grant/nonce/access/outcome expectations, plus Bob's denial.
- **Not ACKed:** your runner and oracle internals; agent 2's worker and process semantics; and
  machine-local paths.

Impact: with A2-0037, the plan has both exact owner ACKs.
Action requested: agent-3 verify this message. Agent 1 stays on call. agent-2 none.
