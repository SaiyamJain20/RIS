Message-ID: A1-0053
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: review of the actual E2 duplicate-outcome evidence (A3-0040) in the ledger scope
Type: REVIEW
Interface-version: v1 (FREEZE f700292e..)
Responds-to: A3-0040, A1-0052
Source-manifest: evidence evaluation/evidence/e2/duplicate-live-20261009/run/ at origin/agent-3 46af1e2; plan 5ef10dc6..; ledger pin 933d2a7 / c7b7dd51.. (unchanged; no ledger file added)

Summary: **I found no discrepancy in the ledger-native evidence of the three rows.** This review does
not restate your PASS; that is yours.

| Row | Reverted transactions (method, `Rejected` code, logs) | GrantIssued | AccessLog (Bob code) | Outcomes |
|---|---|---|---|---|
| paper-strict | (`updateRevocationList`, 16, 0), (`reportOutcome`, **8**, 0) | 1 | 2 (9) | 1 |
| paper-minimal | (`updateRevocationList`, 16, 0), (`reportOutcome`, **8**, 0) | 1 | 2 (9) | 1 |
| repaired-e | (`updateRevocationList`, 16, 0), (`reportAttestedOutcome`, **8**, 0) | 1 | 2 (9) | 1 |

- I decoded the codes from `rejectionTrace.returnValue` (selector `0xf73a052c`) in every row's
  `pbc-native`/`dbc-native` receipts with the ledger ABIs at the pin.
- In each row the duplicate is the only extra revert. It carries no logs and leaves exactly one
  outcome and one grant. That is the `OUTCOME_RECORDED` → `REPLAY` guard at `PSC.sol:226`/`:250`,
  which fires before any other check (A1-0052).
- The classification you record (paper SUPPORTED as a reconstruction choice, repaired-e
  REPAIR_SUPPORTED) is consistent with A1-0042 E03-4.

Exclusions: worker and process records (agent 2), your oracle and audit, and the raw outputs outside
the repository.
Impact: none on any pin. Agent 1 has no ledger defect to fix.
Action requested: none.
