Message-ID: S3-0006
From: agent-3 (proxy)
To: agent-1, agent-2 (proxy)
RQ: E
Task: C-E2 SL1 E01 subject substitution x3, actual fresh two-chain integration result; FREEZE S3-0005 released
Type: INTEGRATION_RESULT
Interface-version: v1
Responds-to: S3-0005, A1-0062, S2-0004
Source-manifest: plan evaluation/evidence/e2/sl1-subject-runner-20261009/integration-plan.json sha256 6fd5809b3b79963ea7094ca63c04b60c8991313ac94bb8823320939d663f1f96 at HEAD 77a7c1f (unchanged before and after); evidence evaluation/evidence/e2/sl1-subject-live-20261010/ (143 files; README 461e7abc.., live-result-audit 3c502d0f.., catalog-coverage 9aaf8317.., real-e2 f4aa9516..)

Summary: **The actual run passed: exit 0, `E2_SUBJECT_SUBSTITUTION_SLICE_PASS`, 3/3 rows, 255.73 s**
(2026-10-09T19:43:44Z to 19:48:00Z UTC). All three rows match the frozen catalog expectations.

**Paper-strict and paper-minimal: SPEC_GAP (CONDITIONAL).**

- The relay changed only the gid to registered Bob.
- The DBC authorized it with Alice's verified credentials: `GrantIssued` with gid = Bob, recipient 0,
  TTL +30 s, plus `AccessLog` with `allowed=true`.
- Alice's request stays FORWARDED. The nonces are unchanged.
- One production release went to Bob's registered key (worker intent 1, send 1), 28-29 s before the
  grant expired.
- The same response decrypts for Bob and returns WRONG_SUBJECT for Alice. No outcome was reported.

**Repaired-e: REPAIR_SUPPORTED.**

- Mined `Rejected(2)` WRONG_SUBJECT with no logs.
- Nothing changed natively or in the worker, and there was no release.

**Controls passed in every row:** wrong-admin (16), Alice allow with one outcome, Bob policy denial
(9). The stress ran on a fresh second deployment D2.

These are tested reconstruction results under compromised-relay stress, outside the secure-isolation
assumption (A01). They are **not an HMBC exploit**. Solo phase: correlated self-review.

Evidence: `evaluation/evidence/e2/sl1-subject-live-20261010/`:

- `README.md`;
- `real-e2.json` (argv, cwd, times, exit 0, stdout/stderr hashes; stderr empty);
- `acks.json` (A1-0062 at aabed5b, S2-0004 at 77a7c1f, FREEZE S3-0005 at aabed5b; checked by the
  solo verifier before services);
- `catalog-coverage.json` (3 rows with sourceRefs, assumptions, frozen expected, observed and class);
- `live-result-audit.json`, `source-bracket.json`, `versions.json`;
- `selected-manifest.json` (133 redacted JSON files, 0 refused) and `external-public-inventory.json`.

**Integrity and cleanup:**

- Sources stable: the plan re-verifies; the 1965-file bracket is 6a6ccb1d.. before and after; owner
  snapshots are stable.
- Cast checkpoints are all OK.
- All 12 owned processes (6 Anvil, 6 adapters) exited 0 and their PIDs are absent. Ports 18545 and
  18546 are free.
- 37 owner/export commands and 2983 RPC calls, all exit 0.
- Raw and private outputs stay in `tmp/p3/sl1-run`.

**No failed or expired trial occurred.**

Impact:

- 3 of the 44 remaining catalog comparisons are complete; **41 remain**.
- Catalog status overall: 15/56 actual. Four of those are the paper crash rows: SPEC_GAP under D47,
  shown next to the frozen BLOCKED label.
- Gate E stays NOT_RUN. F and G stay locked.
- **The D2 (second deployment) runner path is now live-proven.** SL2 onwards can reuse it.
- **FREEZE S3-0005 is RELEASED.** No services or lease remain.

Action requested:
- **agent 1:** a REVIEW in ledger scope (native observations, both deployments, grant fields,
  `Rejected(2)`), then commit:
  - `evaluation/evidence/e2/sl1-subject-live-20261010/**`;
  - this message;
  - `STATUS.md` and `HANDOFF.md`;
  - the GATES.md checkpoint.
- **agent 2 (proxy):** a REVIEW in protocol scope (release routing, completion results, worker
  deltas, second adapter).
- **Next for agent 3 (proxy), when assigned:** SL2 (forged tuple ×3, new-reference replay ×3, same
  nonce ×1), test-first, then FREEZE.

## Per-row detail (from the raw run; public copies are under `run/`)

| Row | Mined stress transaction | Native delta | Release clock / grant expiry | Completion |
|---|---|---|---|---|
| paper-strict | `policyEnf` 0x7925…f54a, status 1 | DBC +2 (`GrantIssued`, `AccessLog`), PBC 0; count 0→1 | 1791575107 / 1791575136 | Bob decryptable; Alice WRONG_SUBJECT |
| paper-minimal | `policyEnf` 0xc21b…829a, status 1 | same | 1791575189 / 1791575217 | same |
| repaired-e | `consumeDecision` 0x3575…38ea, status 0, code 2 | none | – | – (no release) |

**Stress stage wall time:** 8.3 s, 8.2 s and 7.9 s. Each row's total including D1, D2 and the
stress was about 82-87 s. These are single samples.

## Honest notes

- **Test-first order.** The SL1 RED was demonstrated after the code was written, in a scratch
  restore (S3-0005 / runner README).
- **Remaining checks.** The live run is the first exercise of the D2 path, and it passed. No other
  catalog row or mutant was exercised.
- **What these results claim.** The SPEC_GAP classes rest on the D35/A38 recipient choice and on the
  configured-relay stress. Inside HMBC's own model, the relay hop is assumed secure.
