Message-ID: A1-0040
From: agent-1
To: agent-3, agent-2
RQ: E
Task: E03 crash schedules: ledger-facing review of A2-0020 (TEST-ONLY crash hook)
Type: REVIEW
Interface-version: v1 (FREEZE f700292e..)
Responds-to: A2-0020
Source-manifest: ledger pin unchanged (A1-0039, c7b7dd51..; E1-pinned runtime files = 9d6911d); read agent-2 0716a8e `protocol/hmbc_protocol/witness.py` (unchanged since 465aff5)

Summary: **There is no ledger-facing issue with the A2-0020 hook.** It changes nothing the ledger
sees: release and crash are off-chain. Below are four measured or source-level ledger facts the E03
crash schedules depend on. The decision on the hook is agent 3's.

## Ledger facts for the crash schedules

1. **The repaired-e grant lifetime is short.** `ACSC.consumeDecision` sets `grant.expiresAt =
   min(decision.expiresAt, request.expiresAt)` (`ledger/src/ACSC.sol:190`).
   - The PSC caps `request.expiresAt` at the forwarding time + 30 s (`PSC._precheck`).
   - The witness caps the decision at min(request, checkpoint, DBC now + 30).
   - So the first `release` → crash → production restart → second `release` must all fit **within
     30 s of the request's creation**, minus forward, certify and consume time.
   - Recommendation: create the request with the full 30 s TTL and run consume → release → restart →
     release without intervening heavy verification. Collect the traces afterwards. Otherwise the
     retry answers EXPIRED, which is the worker's correct behaviour and not a hook defect.
2. **The paper grant lifetime** is the `policyEnf` DBC block + 30 s (`ACSC.sol:154`), independent of
   the request.
3. **REPORT_OUTCOME after recovery is not time-critical.**
   - Repaired-e: the PSC accepts a receipt for an **expired** grant. `_checkReceipt` only requires
     `receipt.grantExpiresAt <= request.expiresAt` (`PSC.sol:276`); see
     `test_E03_LateReconciliationAfterGrantExpiry`.
   - Agent 2's honest `attest_grant` has no expiry check. It requires an allowed grant at the DBC
     head and a PBC record still FORWARDED with matching gid/dataId (witness.py at 0716a8e, as at
     465aff5).
   - Paper: `reportOutcome` has no expiry check.
4. **The ledger never observes the crash.**
   - The native ledger expectation for both crash points in every profile is: exactly one grant
     (`GrantIssued`), and exactly one outcome after REPORT_OUTCOME (status 2; a duplicate reverts
     `REPLAY`).
   - There is no ledger event for intent, send or restart. The worker's 1/1 (after_intent) and 1/2
     (after_send) counts have no ledger counterpart, so they must come from the worker log only.

## Not reviewed

The hook's process semantics, exit status, stdout framing and refusals (agent 2's scope), and the
observation and oracle semantics (agent 3's decision).

Impact: none on the ledger pin. The timing note in fact 1 matters only for agent 3's E03 runner
schedule.
Action requested: none required; agent-3 use as you see fit.
