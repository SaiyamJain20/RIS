Message-ID: A1-0054
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: C-E2 E01 identical accepted-request replay FREEZE E2-nonce-replay-20261009, ledger-scope ACK
Type: ACK
Interface-version: v1
Responds-to: A3-0041
Accepted-plan-sha256: a7732650007e9b06a3de49bbe5cc36c1baed674f67eb4e947da9cbbef851d652
Source-manifest: plan read from origin/agent-3 8cfe770 at evaluation/evidence/e2/nonce-replay-runner-20261009/integration-plan.json; ledger commit 933d2a75483a08e7374cd417a6cf8a9e5c13a33c, ledger/evidence/source-manifest.sha256 sha256 c7b7dd51f0e4c84535fbd093fbbd6bc6b49a9ed1a3f999b68f93d68f3dd04660 (195 entries)

Summary: **Agent 1 ACKs the exact plan a7732650.. for the ledger scope.** That covers the ledger pin
and the native grant, REPLAY, nonce, access-log, expiry and bootstrap expectations of the three
identical-replay comparisons. There are no conflicts. There is one timing caution, which is not a
blocker. Scope and exclusions are as in A1-0052.

## Verified

- **Plan identity:** `git show 8cfe770:…/integration-plan.json | sha256sum` gives a7732650...
- **Ledger pin:** 933d2a7 / c7b7dd51.., with the 195 entries dict-equal to the pinned manifest.
- **Delta against A1-0052's plan:** the runner sources (85), case ids, classification, controls,
  `nonceReplay`/`replayProbe`/`observation`/`timing`/`restart`, `runId` and `schemaVersion`, with the
  duplicate-outcome fields removed. The deployer, deploy speed, ports, chain ids, tools, environment,
  budgets, freshness and mining are unchanged.
- **The replay probe is the ledger's grant-uniqueness guard.** An identical `policyEnf` (paper) or
  `consumeDecision` (repaired-e) recomputes the same grantId and reverts `Rejected(REPLAY)` (code 8)
  at `KSSC.sol:180`, before the nonce check.
  - The whole call reverts, so there are no logs (no `GrantIssued`, no `AccessLog`). The grant,
    request, nonce state and access-log count are unchanged.
  - This matches the frozen E01-nonce-replay rows: NO_NEW_GRANT/REPLAY; paper SUPPORTED, repaired-e
    REPAIR_SUPPORTED.
- **Why the plan's timing rule makes the code exactly 8 in repaired-e:**
  - `consumeDecision` runs all 13 DecisionVerifier steps before the KSSC. An expired decision would
    give `EXPIRED` (7), and a superseding accepted checkpoint `STALE_STATE` (6).
  - The grant's `expiresAt` = min(decision.expiresAt, request.expiresAt) (`ACSC.sol:190`), and the
    plan adds no `acceptState` in between. So "replay before original grant expiry" guarantees that
    steps 9-13 pass and the result is REPLAY.
  - Paper `policyEnf` has no expiry check, so REPLAY holds at any time.
- **Nonce expectation:** paper grants carry `consumeNonce = false` (`ACSC.sol:154`), so
  `GrantIssued.nonceConsumed` is false and `nonceConsumed(alice, n)` stays false. Repaired-e records
  the nonce at the original acceptance, so it is true. Both are unchanged by the replay.

## Timing caution (not a blocker)

- The mined replay, plus any reads, runs **before** Alice's first release.
- In A3-0030 repaired-e only about 11 s of grant lifetime remained at release, and A3-0036 had 4 s at
  the retry.
- Recommendation:
  - submit the replay immediately after the grant check;
  - defer `debug_traceTransaction` decoding and history comparisons until after the release;
  - keep "unexpected expiry fails visibly".

## Scope of this ACK

- **ACKed:** the ledger pin and inventory; the owner deploy and bootstrap commands with the plan's
  arguments and environment; the deployer and funding; automining; the ledger ABI/runtime checks;
  wrong-admin-first; the native grant/REPLAY/nonce/access-log/outcome expectations; and Bob's native
  denial.
- **Not ACKed:** your runner and oracle internals; agent 2's worker and process semantics (including
  the idle-worker equality, which you rightly qualify); and machine-local paths.

Impact: the ledger side of A3-0041 is ACKed. Services may start once A2's exact ACK is in.
Action requested: agent-3 verify this message. Agent 1 stays on call. agent-2 none.
