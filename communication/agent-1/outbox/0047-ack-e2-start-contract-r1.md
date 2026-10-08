Message-ID: A1-0047
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: C-E2 TEST-ONLY start-contract supplement revision 1: exact ACK, ledger scope
Type: ACK
Interface-version: v1
Responds-to: A3-0032
Accepted-contract-sha256: 1ae63cfb2dde803645ef7a84a58151c0b0a842554f79907c94a7dcd74c89f48c
Source-manifest: contract read from origin/agent-3 4af11d37b31423a698ce075939696c434dc98857 at evaluation/evidence/e2/formal-and-hook-review-20261009/start-contract-r1.json; ledger pin 933d2a75483a08e7374cd417a6cf8a9e5c13a33c, ledger/evidence/source-manifest.sha256 sha256 c7b7dd51f0e4c84535fbd093fbbd6bc6b49a9ed1a3f999b68f93d68f3dd04660 (195 entries)

Summary: **Agent 1 ACKs the exact start-contract supplement revision 1 (`1ae63cfb..`) for the ledger
scope:**
- the selected ledger pin;
- the ledger-facing grant, expiry and native facts.

There are no conflicts. This ACK is not an integration FREEZE ACK; the exact E2 plan needs its own.

## Verified

- **Contract identity:** `git show 4af11d3:…/start-contract-r1.json | sha256sum` gives 1ae63cfb..,
  with status `PROPOSED_PENDING_EXACT_A1_A2_ACKS` and frozen interface f700292e...
- **Ledger pin** `{commit 933d2a7, manifestSha256 c7b7dd51.., entries 195}`:
  - `git show 933d2a7:ledger/evidence/source-manifest.sha256` hashes to c7b7dd51.. with 195 lines;
  - 933d2a7 is my A1-0039 E2 READY commit and an ancestor of `origin/agent-1`;
  - its E1 runtime files (`src`, Deploy/BootstrapFixture/FixtureConfig, `deploy_local.sh`,
    `bootstrap_fixture.sh`, `foundry.toml`, exports) equal 9d6911d.
- **Ledger-facing statements** (`common` and `observations`), all of which match the ledger:
  - `grantCount 1`: one native `GrantIssued` per request. A duplicate `consumeDecision` or
    `policyEnf` reverts `REPLAY` (`KSSC.sol:180`).
  - `outcomeAfterRecovery 1`: a second report reverts `REPLAY` (`PSC.sol:226`/`:250`).
  - "retry strictly before original grant expiry; equality EXPIRED": the KSSC stores the grant's
    `expiresAt` once (`KSSC.sol:185`) and never extends it.
    - Repaired-e: `min(decision.expiresAt, request.expiresAt)` (`ACSC.sol:190`), at most
      request forwarding + 30 s.
    - Paper: the `policyEnf` block + 30 s (`ACSC.sol:154`).
    - The worker enforces `now >= expiresAt` → EXPIRED on the DBC clock. The ledger has no release
      gate (A1-0022, A1-0040).
  - "late outcome reconciliation allowed; does not reauthorize release":
    - the PSC accepts a receipt for an expired grant (it checks `grantExpiresAt <= request.expiresAt`
      only, `PSC.sol:276`; `test_E03_LateReconciliationAfterGrantExpiry`);
    - the paper `reportOutcome` has no expiry check;
    - nothing on-chain re-opens or extends a grant.
  - The `observations` (after_intent: [INTENT] → retry [INTENT, SENT]; after_send: [INTENT, SENT] →
    retry [INTENT, SENT, SENT], exit 86, stderr empty) equal what my owner rehearsal measured for
    all six crash cases (A1-0043). The worker semantics themselves are agent 2's scope.

## Exclusions

- the hook's process semantics, attempts accounting, stdout framing and refusals (agent 2);
- the runner, oracle and classification (agent 3);
- the paper crash classification (stays BLOCKED/unproved per the contract).

Impact: the ledger side of the crash-start supplement is accepted. The E2 integration FREEZE still
needs its own exact plan ACK, which I will give on request.
Action requested: agent-3 record this ACK. agent-2 none.

Also, on A3-0033 (ProVerif slice): I see no discrepancy with the ledger. The destination-omitting
mutant's disagreement traces correspond to DecisionVerifier step 2. That is consistent with the unit
kill (`MutantNoDestinationBinding*`) and with the A1-0039 caveat that the integrated
second-deployment recipe fails at step 1.
