Message-ID: A1-0081
From: agent-1
To: agent-3 (proxy), agent-2 (proxy)
Cc: human
RQ: E
Task: human decision on the revocation window after the D-P3-3 pause; P3 closed (solo phase)
Type: DECISION
Interface-version: v1
Responds-to: A1-0078, A1-0079, A1-0080
Source-manifest: human answer in the agent 1 session, 2026-10-12 ~01:25 IST ("Use existing window evidence"); ledger/evidence/revocation-window/ (A1-0046); evaluation/evidence/e2/sl6-barrier-live-20261011/ (A1-0075); communication/agent-1/solo/agent-3-proxy/STATUS.md (D-P3-3 stop)

Summary: **The D-P3-3 window FREEZE was also stopped by a safety classifier in agent 3 (proxy). It
was paused and not retried. The human decided to use the existing window evidence. P3 is closed.**

## The question and the answer

- **Question:** the window is not one of the nine gate E criteria; it only decides what RQ1-E.md
  claims.
- **Options offered:**
  - use the existing evidence;
  - record the window as a gap;
  - the human handles it.
- **Answer (human): use the existing window evidence.**

## What RQ1-E.md may claim about the window

1. **Owner integrated measurement (A1-0046, `ledger/evidence/revocation-window/`):**
   - Setup: repaired-e on two Anvil chains with interval mining, agent 2's **unmodified production
     adapter** (8b7caf5 = E1 pin 465aff5) collecting checkpoints and decisions, and the owner runner
     and collector.
   - Barrier delay d = 0 / 5 / 10 / 20 s gives refusal in the barrier block itself (STALE_STATE),
     with W = 2 / 6 / 11 / 21 s.
   - With no barrier, refusal comes exactly at `request.expiresAt` (EXPIRED), W = 26 s, which is the
     TTL left at T0.
   - A new request after T0 is refused at the PSC at once (REVOKED).
   - **Paper-strict:** a pre-revocation tuple is still grantable at T0 + 5, + 35 and + 65 s.
2. **The integrated C-E2 runner, SL6:** this is an ordering result, not a measured window.
   - Before the DBC accepts the revoking checkpoint, the older certificate is accepted
     (pre-barrier, REPAIR_SUPPORTED, intentional).
   - After it, the older certificate is rejected with STALE_STATE from the line 87 sequence cause
     (post-barrier).
   - The 2 s SL6 value is a cross-clock difference and is **not** a window measurement (A1-0074
     point 2).
3. **What W is:** W = min(time until the DBC accepts a post-revocation checkpoint, remaining
   request/decision TTL) ≤ 30 s. It is a runner/witness cadence parameter, not a ledger constant.

## What must not be claimed

- **No window measured by the integrated C-E2 runner.** D-P3-3 was not run; record it as not run,
  with the reason (A1-0079/A1-0081).
- **No statistics.** There was one trial per delay, on one host, with 1 s granularity.

## P3 status: closed

| Item | Outcome |
|---|---|
| D-P3-1/D-P3-2 live mutant matrix | **NOT RUN** (safety-classifier stop). Criterion 4 rests on owner, formal and baseline evidence (A1-0080) |
| D-P3-3 integrated window | **NOT RUN** (safety-classifier stop). The report uses A1-0046 and SL6 (this message) |
| D-P3-4 ProVerif | **DONE**: `evaluation/evidence/e2/p3-proverif-20261012/`, byte-identical to A3-0033 |

Impact: P3 is closed with two items not run, each stated with its reason and a human decision. P4
starts (A1-0082).
Action requested: agent-3 (proxy) carry these statements into RQ1-E.md exactly.
