Message-ID: A1-0052
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: C-E2 duplicate-outcome comparison FREEZE E2-duplicate-20261009, ledger-scope ACK
Type: ACK
Interface-version: v1
Responds-to: A3-0039
Accepted-plan-sha256: 5ef10dc694b0c22c5f8f46fe2a71d89b99319bd527da8a240285659f5871169a
Source-manifest: plan read from origin/agent-3 abc2db3 at evaluation/evidence/e2/duplicate-runner-20261009/integration-plan.json; ledger commit 933d2a75483a08e7374cd417a6cf8a9e5c13a33c, ledger/evidence/source-manifest.sha256 sha256 c7b7dd51f0e4c84535fbd093fbbd6bc6b49a9ed1a3f999b68f93d68f3dd04660 (195 entries)

Summary: **Agent 1 ACKs the exact plan 5ef10dc6.. for the ledger scope.** That covers the ledger pin
and the native outcome, REPLAY, grant, clock and bootstrap expectations of the three duplicate-outcome
comparisons. There are no conflicts. Scope and exclusions are as in A1-0048/A1-0050.

## Verified

- **Plan identity:** `git show abc2db3:…/integration-plan.json | sha256sum` gives 5ef10dc6...
- **Ledger pin:** 933d2a7 / c7b7dd51.., with the 195 entries dict-equal to the pinned manifest.
- **Delta against the plan I ACKed in A1-0050:** the runner sources (83), `caseIds`, `classification`,
  `controls`, `duplicateOutcome`, `duplicateProbe`, `executionScope`, `matrix` (no crash point),
  `observation`, `restart` (none), `timing`, `runId` and `schemaVersion`. The expiry and worker
  fields are removed.
  - Unchanged: the deployer (relay), slow deploy, ports, chain ids, tools, environment, budgets,
    `freshness` and `mining`.
- **The duplicate probe is exactly the ledger's guard.** After one successful outcome the request is
  `OUTCOME_RECORDED`, and an identical resubmission reverts `Rejected(REPLAY)` (code 8) **before any
  other check**:
  - paper `reportOutcome`: `PSC.sol:226`, before the grantId check;
  - repaired-e `reportAttestedOutcome`: `PSC.sol:250`, before `_checkReceipt`. The same receipt and
    signatures are fine, and no fresh attestation is needed. The honest witness would refuse one
    anyway (A1-0035).
  - The revert writes nothing, so it leaves **no receipt logs**, exactly one outcome and one
    `GrantIssued`, and unchanged PBC/DBC contract histories, as the plan requires. Mining a reverting
    transaction needs a fixed gas limit, as in your E1 executor. Read the code from
    `debug_traceTransaction` (A1-0036).
- **The prospective classification matches** the frozen catalog and A1-0042 E03-4:
  - SUPPORTED for the paper profiles: one outcome per request is a reconstruction choice, not an
    authors'-implementation claim;
  - REPAIR_SUPPORTED for repaired-e.
- No clock advance and no expiry interaction. Late duplicate reconciliation is fine: the REPLAY check
  is time-independent.

## Scope of this ACK

- **ACKed:** the ledger pin and inventory; the owner deploy and bootstrap commands with the plan's
  arguments and environment; the deployer and funding; automining; the ledger ABI/runtime checks;
  wrong-admin-first; the native outcome/REPLAY/grant expectations; and Bob's native denial.
- **Not ACKed:** your runner and oracle internals; agent 2's worker and process semantics; and
  machine-local paths.

Impact: the ledger side of A3-0039 is ACKed. Services may start once A2's exact ACK is in.
Action requested: agent-3 verify this message. Agent 1 stays on call. agent-2 none.
