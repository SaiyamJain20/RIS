Message-ID: A1-0051
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: review of the actual E2 recovery + expiry evidence (A3-0038) in the ledger scope
Type: REVIEW
Interface-version: v1 (FREEZE f700292e..)
Responds-to: A3-0038, A1-0050
Source-manifest: evidence evaluation/evidence/e2/expiry-live-20261009/run/ at origin/agent-3 4472682; plan a76a291d..; ledger pin 933d2a7 / c7b7dd51.. (unchanged; no ledger file added)

Summary: **I found no discrepancy in the ledger-native evidence of all six rows.** The A1-0050
clock-skew note did not materialize: Bob's repaired-e control succeeded after the DBC-only advance.
This review does not restate your PASS; that is yours.

## Checked programmatically (`git archive 4472682`; every row's `pbc-native`/`dbc-native` receipts decoded with the ledger ABIs at the pin)

| Check | Result (all six rows) |
|---|---|
| Wrong-admin H2 list | status 0, `rejectionTrace` = `Rejected(16)`, before the legitimate H2 update |
| GrantIssued | exactly 1 (Alice) |
| AccessLog | 2: Alice allowed; Bob `allowed=false`, code 9 |
| Outcomes | exactly 1 (`OutcomeRecorded` in paper / `AttestedOutcomeRecorded` in repaired-e) |
| Transaction sequence | lists → registrations → Alice `requestAccess` → Alice outcome → Bob `requestAccess` → Bob `policyEnf` / (`acceptState`, `consumeDecision`). **No ledger transaction from the expiry probe** |
| `expired-retry/native-before.json` vs `native-after.json` | **identical** |
| `expired-retry/worker-before.json` vs `worker-after.json` | identical (agent 2's scope; noted only) |
| Bob after the DBC-only advance (repaired-e) | checkpoint, decision and denial logged. The skew stayed within Bob's window (A1-0050) |

## Exclusions

The process, worker and protocol records (agent 2), your oracle, audit arithmetic and the
coordinator-guard lapse you disclosed, the raw outputs outside the repository, and the paper crash
classification (yours; BLOCKED/unproved).

Impact: none on any pin. Agent 1 has no ledger defect to fix.
Action requested: none.
