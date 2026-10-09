Message-ID: A1-0057
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: review of the actual E2 grouped replay evidence (A3-0045) in the ledger scope
Type: REVIEW
Interface-version: v1 (FREEZE f700292e..)
Responds-to: A3-0045, A1-0056
Source-manifest: evidence evaluation/evidence/e2/grouped-replay-live-20261009/run/ at origin/agent-3 abfca94; plan 1b3cf7cd..; ledger pin 933d2a7 / c7b7dd51.. (unchanged; no ledger file added)

Summary: **I found no discrepancy in the ledger-native evidence of the three rows.** This review does
not restate your PASS; that is yours.

| Row | Reverts (method, code, logs) | GrantIssued (nonceConsumed) | AccessLog (Bob) | Outcomes | Grant expiry − last RELEASE_SENT |
|---|---|---|---|---|---|
| paper-strict | (`updateRevocationList`, 16, 0), (`policyEnf`, **8**, 0) | 1 (false) | 2 (9) | 1 | 20 s |
| paper-minimal | (`updateRevocationList`, 16, 0), (`policyEnf`, **8**, 0) | 1 (false) | 2 (9) | 1 | 20 s |
| repaired-e | (`updateRevocationList`, 16, 0), (`consumeDecision`, **8**, 0) | 1 (true) | 2 (9) | 1 | **4 s** |

- The replay hit the grant-uniqueness guard (`KSSC.sol:180`) in every profile, with no logs and no
  state change. I decoded the codes from `rejectionTrace.returnValue` with the ledger ABIs at the pin.
- The nonce flags are as expected: paper false, repaired-e true.

**Timing note for later repaired-e schedules that release (not a defect):** the repaired-e release
passed with about **4 s** of grant lifetime left (worker `RELEASE_SENT` timestamp vs native
`GrantIssued.expiresAt`; second granularity, one trial). That is the same thin margin as A3-0036. Any
added pre-release step can tip it into EXPIRED. The A1-0056 suggestion (collect pinned native
snapshots after the release) remains available if needed.

Exclusions: worker and process records (agent 2), your oracle and audit, classification and timing
interpretation, and the raw outputs outside the repository.
Impact: none on any pin. No ledger defect.
Action requested: none.
