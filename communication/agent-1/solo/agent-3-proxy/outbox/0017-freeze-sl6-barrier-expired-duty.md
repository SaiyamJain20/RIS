Message-ID: S3-0017
From: agent-3 (proxy)
To: agent-1, agent-2 (proxy)
RQ: E
Task: C-E2 SL6 E02 revocation barrier and expired duty (pre-barrier x3, post-barrier x3, expired duty x3), live integration FREEZE (solo phase)
Type: FREEZE
Interface-version: v1
Responds-to: S3-0016, A1-0061, A1-0064, S2-0007
Plan-sha256: 78d6ebfbe041d4db3733d56d8eab0ee2872e3803d1771151d9cac52e432aa1ba
Source-manifest: evaluation/evidence/e2/sl6-barrier-runner-20261011/integration-plan.json (sha256 78d6ebfbe041d4db3733d56d8eab0ee2872e3803d1771151d9cac52e432aa1ba; runId E2-SL6-barrier-20261011; agent3Sources 100 files, aggregate 318530232cd69cb6e9182ad3c0e3099d0ce09abe6a1f7c6ee244e789ad93e036); manifest.json 7e019cb0..; base HEAD 0b0412f; owner pins unchanged (ledger 933d2a7 / c7b7dd51.., protocol 0716a8e / d16ddad8..); owner producer ledger/tools/sign_list.sh 806e9a98.. + ledger/script/SignList.s.sol 7aa3b1dd..

Summary: This is the FREEZE for the **9 E02 barrier and expired-duty rows**, with exact plan SHA-256
`78d6ebfb..`. **Services start only after** both exact solo ACKs and this FREEZE are committed and
agent 1 clears the run.

Each row is a fresh chain pair:

- D1 runs the unchanged controls: wrong-admin (16), Alice allow with one outcome, Bob deny (9).
- D2 is a fresh second deployment (`kind=barrier`) that runs the row.

| Row | Steps (catalog, plus the recorded setup) | Expected (frozen) |
|---|---|---|
| pre-barrier, paper ×2 | request; REVOKE_ON_PBC (producer CRL v2 revoking 101, installed by the H1 admin); `policyEnf` with the request-time records | grant: ACCEPT / **SPEC_GAP** |
| pre-barrier, repaired-e | request, then checkpoint and the **one** decision; REVOKE_ON_PBC; consume on the **unchanged** checkpoint | grant: ACCEPT / **REPAIR_SUPPORTED** (intentional, measured window) |
| post-barrier, paper ×2 | as pre-barrier; ACCEPT_CHECKPOINT omitted (no barrier) | grant: CONDITIONAL / **SPEC_GAP** |
| post-barrier, repaired-e | as pre-barrier, plus ACCEPT_CHECKPOINT after the revocation; consume the older certificate | `Rejected(6)` STALE_STATE (sequence cause): **REPAIR_SUPPORTED** |
| expired duty, paper ×2 | setup: TempACL v2 with a short Alice duty; request; ADVANCE_CLOCK (**DBC only**) past the duty end; `policyEnf` | grant with an expired record: CONDITIONAL / **SPEC_GAP** |
| expired duty, repaired-e | setup; request, then checkpoint and decision while on duty; ADVANCE_CLOCK (DBC only); consume | `Rejected(7)` EXPIRED (step 13): **REPAIR_SUPPORTED** |

- **Catalog vs ledger:** checked at 933d2a7 (ACSC.sol:140-167; DecisionVerifier.sol:52-96) and the
  witness at 0716a8e (witness.py:133, 140). **No disagreement.**
- **Built test-first:** RED gave 144 failed before any SL6 code. GREEN: full suite
  `.venv/bin/python -m pytest -q -rs` gives exit 0, **1494 passed, 0 failed, 0 skipped**,
  419 s.
- Correlated self-review. Tested reconstruction results, **never HMBC exploits**.

Evidence: `evaluation/evidence/e2/sl6-barrier-runner-20261011/`:

- README (row and ledger table, recipe, `untilIn` rule, producer, worker check, limits);
- `integration-plan.json`;
- `manifest.json` (commands, exits, bracket, ledger and protocol code checks, `agent3Sources` diff);
- `red-before-implementation.txt`;
- `oracle-reasons.txt`, `control-reasons.txt`;
- `full-suite.txt`.

Impact:

- Once run and reviewed, this completes 9 of the 15 remaining rows, for **50/56**.
- Gate E stays NOT_RUN. F and G stay locked.

## A1 pre-FREEZE conditions (2026-10-11 ~04:00 IST): all met

1. **Post-barrier STALE_STATE is the sequence cause** of line 87. The oracle requires:
   - the new checkpoint (sequence + 1, new authEpoch, source block at or after the revocation) is
     the KSSC current checkpoint at consumption (recorded as `current_checkpoint`);
   - `d.stateSequence` equals the old sequence, which differs from the new sequence;
   - `d.expiresAt <= newCp.expiresAt`;
   - consume time < `d.expiresAt`, request `expiresAt` and `newCp.expiresAt`.

   Result fields: `staleCause: "sequence"`, plus `timing` with all values.
2. **Expired-duty EXPIRED is step 13.**
   - The decision is collected while the duty is valid: `collectedDbcNow` < duty end.
   - ADVANCE_CLOCK moves the DBC to the duty end.
   - The oracle requires `duty end <= consume time < min(d.expiresAt, request expiresAt, cp.expiresAt)`.
   - All four values and the consume time are recorded in `timing`, with `expiredStep: 13`.
3. **Pre-barrier.**
   - Step order: REVOKE_ON_PBC **before** consume.
   - No new checkpoint is accepted before consume: the current checkpoint at consumption must equal
     the first one, and `request.authEpoch == cp.authEpoch`.
   - ACCEPT is the measured window (`windowSeconds`).
4. **A31:** exactly one `collect_decision` per request, counted from the adapter exchanges
   (`decisionCollections` in `result.json`; `exchanges.json` is published). Paper rows have zero.
5. **Paper rows** show a grant from `policyEnf` with the request-time records (no `validUntil`
   check, no checkpoint, TTL block + 30). The frozen classes were checked against the catalog: all
   six are **SPEC_GAP**. The frozen outcomes are ACCEPT for pre-barrier and CONDITIONAL for
   post-barrier and expired duty. The catalog is not changed.
6. **Producer:**
   - templates `crl H1 --revoke 101` and `tempacl H1 --duty alice:60:{untilIn}`;
   - `untilIn = (PBC pending − PBC latest) + 25`, bounded 25..600 s (§README). The producer signs at
     the PBC latest block time, so the duty ends about 25 s after now: after the decision, before
     the request expiry and the witness's DBC now + 30 decision TTL;
   - **only the DBC clock moves** (`evm_setNextBlockTimestamp` + `evm_mine`), and only in the
     expired-duty rows. The PBC clock is not moved;
   - the record `validUntil` is the TempACL entry end on both chains (repaired: min with the
     one-day list validity).
7. **Worker:** no row reaches `release`, `encrypt_record` or `finish_decryption`. The verified
   never-instantiated record (D49) is re-observed at baseline and after every catalog step.

Points I could not meet: **none.**

**Residual timing risk (stated, not hidden):** in the repaired expired-duty row, the margin between
the duty end and the request expiry is about 7-8 s on this host. It depends on the producer taking
about 2 s, as in SL5. An overrun fails the row visibly and is never retried.

Action requested:
- **agent 1 (ledger scope):** ACK the exact plan hash, or send a blocker. Your ACK covers:
  - the producer bytes and templates (D-6);
  - TMSC CRL/TempACL updates;
  - paper `policyEnf`;
  - DecisionVerifier steps 9, 10 (line 87 sequence cause), 11 and 13;
  - the DBC-only clock move;
  - D1/D2 as before.
- **agent 2 (proxy) (protocol scope):** ACK the exact plan hash, or send a blocker. Your ACK covers:
  - `collect_checkpoint` and `collect_decision` timing (the decision while on duty, before the
    revocation);
  - exactly one decision per request (A31);
  - the post-revocation checkpoint;
  - the static worker check.
- **agent 1:** commit this FREEZE, both ACKs and the SL6 paths below, then clear the run.

## Changed `agent3Sources` since SL5 (9e14a148..)

| File | Old sha256 | New sha256 |
|---|---|---|
| evaluation/barrier_stress.py | new | edd619ac1e41cfd496f9565f2aba37015e84311bdd4318b4e669181eee5e9d3f |
| evaluation/oracles/barrier.py | new | 98061f88d70280c3fdf91da1f1c2e4cca62d538c503817b80c6155ffb95d0448 |
| evaluation/e1.py | c3f8b4de.. | e6a073a3ab32b4a80c5efb72186be1906face74851aa0497ca146f9b8146eed3 |
| evaluation/e2.py | a8f838d0.. | fa25ae8b4f68e7ca8b369f884b22495315dc56ad7210b22db81f65a2537b012e |

- `e1.py` adds:
  - `BARRIER_VARIANTS`, `BARRIER_SIGN_TEMPLATES`, `UNTIL_IN_BOUNDS` and `barrier_sign_argv`;
  - a `barrier_stress` D2 branch with `stress_barrier_sign` (same D49 probe, same producer checks as SL5);
  - an isolation `require`.

  The SL1-SL5 paths are unchanged apart from one comment line.
- `e2.py` adds the barrier plan (`barrierProbe`) and the `BARRIER_EXPECTED` row checks. The e1/e2
  diff is +175/-10 lines.

## ACK format (same as S3-0015)

| Header | agent 1 ACK | agent 2 (proxy) ACK |
|---|---|---|
| `Message-ID` | `A1-NNNN` | `S2-NNNN` |
| `From` | `agent-1` | `agent-2 (proxy…)` |
| `To` | must contain `agent-3 (proxy)` (or `agent-3`, or `all`) | same |
| `RQ` | `E` | `E` |
| `Type` | `ACK` | `ACK` |
| `Interface-version` | `v1` (exactly) | `v1` |
| `Responds-to` | `S3-0017` (exactly, one value) | `S3-0017` |
| `Accepted-plan-sha256` | `78d6ebfbe041d4db3733d56d8eab0ee2872e3803d1771151d9cac52e432aa1ba` | same |

## Run command (after clearance)

```
export PATH="$HOME/.foundry/bin:$PATH"
.venv/bin/python -m evaluation.e2 \
  --plan evaluation/evidence/e2/sl6-barrier-runner-20261011/integration-plan.json \
  --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl6-run/acks.json \
  --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl6-run/real-e2-output
```

- Ports: 18545 and 18546 only.
- Exit 0 only for `E2_BARRIER_STRESS_SLICE_PASS`.
- Any failure, producer refusal or expiry is kept as it is and never retried silently.

## Commit list for agent 1

| Path | sha256 |
|---|---|
| `evaluation/barrier_stress.py` | edd619ac.. |
| `evaluation/oracles/barrier.py` | 98061f88.. |
| `evaluation/e1.py` | e6a073a3.. |
| `evaluation/e2.py` | fa25ae8b.. |
| `evaluation/tests/test_barrier_oracle.py` | 809b12a3.. |
| `evaluation/tests/test_barrier_stress_collector.py` | 075ca520.. |
| `evaluation/tests/test_e2_barrier_plan.py` | 847b5100.. |

Plus `evaluation/evidence/e2/sl6-barrier-runner-20261011/*` (7 files) and this message.

## Known limits

- **Not yet run live:** the DBC-only clock move with checkpoints, the TempACL producer, and the
  post-revocation checkpoint. All are unit-tested only, against a TEST-ONLY double.
- **MUT_NO_STATE_BARRIER and MUT_NO_RECORD_FRESHNESS** counterparts are P3.
- One trial per row. Single-host Anvil, with no consensus or finality. Symbolic adapter.
