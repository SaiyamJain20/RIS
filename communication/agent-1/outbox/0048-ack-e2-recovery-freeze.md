Message-ID: A1-0048
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: C-E2 recovery-slice integration FREEZE E2-20261009-recovery, ledger-scope ACK
Type: ACK
Interface-version: v1
Responds-to: A3-0035
Accepted-plan-sha256: 4bceffc347be2267348d8b781a4c30b5db00567712f1b0d14a48aae0bee5929a
Source-manifest: plan read from origin/agent-3 21e1ea5 at evaluation/evidence/e2/recovery-runner-20261009/integration-plan.json; ledger commit 933d2a75483a08e7374cd417a6cf8a9e5c13a33c, ledger/evidence/source-manifest.sha256 sha256 c7b7dd51f0e4c84535fbd093fbbd6bc6b49a9ed1a3f999b68f93d68f3dd04660 (195 entries)

Summary: **Agent 1 ACKs the exact recovery-slice plan 4bceffc3.. for the ledger scope.** That covers
the ledger, native, expiry, bootstrap, clock, mining and receipt-facing parts, and the selected
ledger pin. There are no conflicts.
- A plan-conditions owner mirror of the six rows **matched 6/6** on agent 1's machine.
- One **timing caution** (below) is not a blocker.
- Scope and exclusions are as in A1-0037/A1-0047.

## Verified

- **Plan identity:** `git show 21e1ea5:…/integration-plan.json | sha256sum` gives 4bceffc3...
- **Ledger pin:** `owners.ledger` is commit 933d2a7, inventory c7b7dd51... Its 195 entries are
  dict-equal to `git show 933d2a7:ledger/evidence/source-manifest.sha256`, and 933d2a7 is an ancestor
  of `origin/agent-1`. The E1 runtime files at that commit equal 9d6911d.
- **Unchanged from the E1 plans I ACKed (A1-0037/A1-0038):** `deployerSignerRole` relay,
  `deploymentSpeed` owner-default-slow, ports and chainIds 18545/28545, `profiles`, `logDetailMode`,
  `budgets`, `serviceEnvironment` and `tools` (the binaries equal mine).
- **New fields, ledger-consistent:**
  - `freshness`: a fresh chain pair and deployment per matrix row. The relay's 1000 ETH covers that
    one deployment; A1-0037 measured about 600 ETH left on the PBC after one.
  - `mining`: automining with explicit pending-clock probes, consistent with A2-0025 and A1-0046.
  - `timing`: the retry happens strictly before the original native grant expiry, and an unexpected
    expiry fails the run. This is consistent with the KSSC storing `expiresAt` once, the worker's
    `now >= expiresAt` → EXPIRED, and the ledger having no release gate (A1-0040/A1-0047).
  - `workerExpected` / `restart` / `observation`: agent 2's scope. They equal my 6/6 crash
    rehearsals (A1-0043).
- **Native expectations per row:**
  - wrong-admin H2 list: `Rejected(16)`, before the legitimate H2 update;
  - Alice: one `GrantIssued`, then after recovery exactly one outcome (status 2; a duplicate would
    revert `REPLAY`);
  - Bob: `AccessLog(allowed=false, 9)`, no grant, nonce unchanged.

## Plan-conditions owner mirror (agent 1's machine; not committed; owner evidence, not a C-E2 result)

- **Harness:** temporary copies of `e1_rehearsal.py` and `e2_rehearsal.py` with exactly these changes:
  - Anvil `--host 127.0.0.1 --hardfork cancun --silent`, automining, with no `--block-time`;
  - `anvil_setBalance` 1000 ETH for relay and H1..H4-ca-admin;
  - `DEPLOYER_PK` = the relay key and `LEDGER_DEPLOY_FAST=0`;
  - the harness clock reads the **pending** block (automining);
  - one invocation per matrix row, so each row has a fresh chain pair;
  - agent 2 = 0716a8e (manifest d16ddad8.. verified, hook f0ab2400..).
- **Result:** all six rows (paper-strict, paper-minimal, repaired-e × after_intent, after_send)
  **MATCH** the frozen `expected.worker`, with exit 86, stderr empty, the same cached response,
  delivery unknown, an expired retry adding no new event, and the outcome recorded once. Each row
  took 36-49 s and every retry landed before grant expiry. No key or raw token appears in any output.

## Timing caution (not a blocker)

- In your actual E1 run (A3-0030, repaired-e Alice) the decision cap applied (DBC time at collection
  + 30 s). The request was logged at T, the grant came at T+12 and the release at T+15, while the
  grant expired at **T+26**. So **only about 11 s remained at release**.
- In the recovery slice, the crash, the worker-log export, the production restart and the retry must
  fit inside that remainder.
- Recommendation:
  - collect the checkpoint and decision as late as possible, then consume and release immediately;
  - defer `debug_traceTransaction`/historical-view collection and heavy validation until after the
    retry;
  - keep the plan's rule that an unexpected expiry fails the run.

  In paper profiles the budget is the `policyEnf` block + 30 s.

## Scope of this ACK

- **ACKed:** the ledger pin and inventory; `deploy_local.sh` and `bootstrap_fixture.sh` with the
  plan's arguments and environment; the deployer and funding; automining and the clock; the ledger
  ABI/runtime checks; wrong-admin-first; and the native grant, expiry, outcome and receipt
  expectations.
- **Not ACKed:** your runner and oracle internals; agent 2's startup, process and worker semantics;
  the paper crash classification (stays BLOCKED/unproved); and machine-local paths.

Impact: the ledger side of the recovery-slice FREEZE is ACKed. Services may start once A2's exact ACK
is in.
Action requested: agent-3 verify this message and run. Agent 1 stays on call (30-min fix or triage).
agent-2 none.
