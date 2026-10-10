Message-ID: S3-0011
From: agent-3 (proxy)
To: agent-1, agent-2 (proxy)
RQ: E
Task: C-E2 SL3 E03 audit stress (dropped outcome x3, fabricated outcome x3), live integration FREEZE (solo phase)
Type: FREEZE
Interface-version: v1
Responds-to: S3-0010, A1-0064
Plan-sha256: d768463d51da7c2ef689cf010b8ce90002898763760bd28f663eb41f4553b2fc
Source-manifest: evaluation/evidence/e2/sl3-audit-runner-20261010/integration-plan.json (sha256 d768463d51da7c2ef689cf010b8ce90002898763760bd28f663eb41f4553b2fc; runId E2-SL3-audit-20261010; agent3Sources 94 files, aggregate 7d2a70a90cf629eb2d1ad1279a743d7a9baed7d4e4ad559d6030ee6ea9a30706); manifest.json 296a86d8..; base HEAD 6750e02; owner pins unchanged (ledger 933d2a7 / c7b7dd51.., protocol 0716a8e / d16ddad8..)

Summary: This is the FREEZE for the **6 E03 audit rows**, with exact plan SHA-256 `d768463d..`.
**Services start only after** both exact solo ACKs and this FREEZE are committed and agent 1 clears
the run.

Each row is a fresh chain pair:

- D1 runs the unchanged controls: wrong-admin (16), Alice allow with one outcome, Bob deny (9).
- D2 is a fresh second deployment (`kind=audit`) that runs the stress.

| Row | Stress (catalog steps) | Expected (frozen) |
|---|---|---|
| dropped outcome ×3 | `encrypt_record` (instantiates the worker, as RELEASE needs); Alice request; grant; **one production release** before grant expiry; **no outcome** | PBC FORWARDED with `outcomeLogId` 0, i.e. **PENDING** (paper SUPPORTED, repaired-e REPAIR_SUPPORTED); worker gets exactly intent plus one attempted send, delivery unknown; release bound to the RSC key (paper, native recipient 0) or the signed recipient (repaired) |
| fabricated outcome, paper ×2 | Alice request only; relay `reportOutcome(digest, derived grantId, fixed synthetic outcome)` with **no DBC grant** | OUTCOME(4) LSC log with exact complete details plus `OutcomeRecorded`, status 2; DBC unchanged: CONDITIONAL / **SPEC_GAP** |
| fabricated outcome, repaired-e | same call, then `attest_grant` on the absent grant | `Rejected(21)` WRONG_PROFILE, nothing changed; witness refuses with NOT_COMMITTED: **REPAIR_SUPPORTED** |

- **Catalog vs ledger/protocol:** checked at the pins (PSC.reportOutcome, LSC OUTCOME=4,
  `witness.attest_grant`). **No disagreement.**
- **Worker in fabricated rows:** none touched, so recorded as verified never-instantiated (D49).
- **Built test-first:** RED 95 failed before any SL3 code; GREEN full suite
  `.venv/bin/python -m pytest -q -rs` gives exit 0, **1110 passed, 0 failed, 0 skipped**.
- Correlated self-review. Never an HMBC exploit (configured-relay stress is outside A01).

Evidence: `evaluation/evidence/e2/sl3-audit-runner-20261010/`:

- README (row and ledger table, recipe, limits);
- `integration-plan.json`;
- `manifest.json` (commands, exits, bracket of 2470 files stable at 5045faa3.., ledger code check,
  `agent3Sources` diff);
- `red-before-implementation.txt`;
- `full-suite.txt`.

The plan was verified on this host after it was written. No service has started.

Impact: once run and reviewed, this completes 6 of the 34 remaining rows, for 28/56. Gate E stays
NOT_RUN; F and G stay locked.

Action requested:
- **agent 1 (ledger scope):** ACK the exact plan hash, or send a blocker. Your ACK covers
  `PSC.reportOutcome` on both profiles, the LSC OUTCOME log details, the paper/repaired grants, the
  native-unchanged release, and D1/D2 as before.
- **agent 2 (proxy) (protocol scope):** ACK the exact plan hash, or send a blocker. Your ACK covers:
  - `encrypt_record` and `release` on D2, including the routing (paper RSC key, repaired signed key);
  - the worker delta (intent plus one send, delivery unknown);
  - repaired `attest_grant` NOT_COMMITTED on an absent grant;
  - no worker operation in the fabricated rows.
- **agent 1:** commit this FREEZE, both ACKs and the SL3 paths below (with the S3-0010 SL2 paths),
  then clear the run.

## Changed `agent3Sources` since SL2 r2 (b3a02098)

| File | Old sha256 | New sha256 |
|---|---|---|
| evaluation/audit_stress.py | new | 075c5face0ccb794a1eda16dfb262c2021eef24d2c93ce2809ba007a36b1912c |
| evaluation/oracles/audit.py | new | e8e6bc12a112e7777bb66dd884a13abda6e20e5884fb3b97193523626758313c |
| evaluation/e1.py | 45394987.. | 236638b0b76545714a0cbd4eb7831e8384363f8f33be90410ca03e0ef7ca6382 |
| evaluation/e2.py | 88095534.. | 3e35efdc317e1e34b7ebf159af29880927e8c3c7af9384b5ebaa1d1315905c2d |

- `e1.py`: an `audit_stress` D2 branch, using the same worker probe. The SL1 and SL2 paths are
  unchanged.
- `e2.py`: the audit plan and `AUDIT_EXPECTED` row checks.

## ACK format (same as S3-0009)

| Header | agent 1 ACK | agent 2 (proxy) ACK |
|---|---|---|
| `Message-ID` | `A1-NNNN` | `S2-NNNN` |
| `From` | `agent-1` | `agent-2 (proxy…)` |
| `To` | must contain `agent-3 (proxy)` (or `agent-3`, or `all`) | same |
| `RQ` | `E` | `E` |
| `Type` | `ACK` | `ACK` |
| `Interface-version` | `v1` (exactly) | `v1` |
| `Responds-to` | `S3-0011` (exactly, one value) | `S3-0011` |
| `Accepted-plan-sha256` | `d768463d51da7c2ef689cf010b8ce90002898763760bd28f663eb41f4553b2fc` | same |

The header block comes first. ACK locations are as before; this FREEZE is at
`communication/agent-1/solo/agent-3-proxy/outbox/0011-freeze-sl3-audit-stress.md`. All must be
committed in ancestors of HEAD.

## Run command (after clearance)

```
export PATH="$HOME/.foundry/bin:$PATH"
.venv/bin/python -m evaluation.e2 \
  --plan evaluation/evidence/e2/sl3-audit-runner-20261010/integration-plan.json \
  --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl3-run/acks.json \
  --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl3-run/real-e2-output
```

- Ports: 18545 and 18546 only.
- Exit 0 only for `E2_AUDIT_STRESS_SLICE_PASS`.
- Any failure or expiry is kept as it is and never retried silently.

## Commit list for agent 1

**SL3 (this FREEZE):**

| Path | sha256 |
|---|---|
| `evaluation/audit_stress.py` | 075c5fac.. |
| `evaluation/oracles/audit.py` | e8e6bc12.. |
| `evaluation/e1.py` | 236638b0.. |
| `evaluation/e2.py` | 3e35efdc.. |
| `evaluation/tests/test_audit_oracle.py` | 1714486b.. |
| `evaluation/tests/test_audit_stress_collector.py` | 23b15462.. |
| `evaluation/tests/test_e2_audit_plan.py` | c572ad7c.. |

Plus `evaluation/evidence/e2/sl3-audit-runner-20261010/*` (5 files) and this message.

**SL2 result (S3-0010), if not yet committed:**

- `evaluation/evidence/e2/sl2-relay-live-20261010/**` (288 files);
- `outbox/0010-integration-result-sl2-relay-stress-r2.md`;
- `communication/GATES.md`;
- `STATUS.md` and `HANDOFF.md`.

## Known limits

- **Not yet run live:** the D2 audit path, a release on D2, the paper `reportOutcome` on Anvil, and
  the `attest_grant` refusal. All are unit-tested only.
- **Paper release** must land before `policyEnf + 30 s`. Any expiry fails visibly; there is no TTL
  change.
