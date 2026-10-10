# SL6: E02 revocation-barrier and expired-duty runner and plan (no services yet)

Paper-derived HMBC2020 reconstruction. Synthetic only. E/RQ1 is active; gate E is NOT_RUN; F and G
are locked.

Author: agent 3 (proxy), solo phase (A1-0059, A1-0061 D-6, A1-0064, S2-0007 A31). **Correlated
self-review.**

**Status:** runner implemented **test-first** and unit-verified; plan frozen as S3-0017. No service
has run. **No catalog row is completed by this checkpoint.**

## Rows, frozen expectations and pinned ledger facts (933d2a7)

| Row | Frozen expected | Ledger fact | Agreement |
|---|---|---|---|
| E02-pre-barrier-revocation-paper-strict / -minimal | ACCEPT / SPEC_GAP | paper `ACSC.policyEnf`/`evaluate` (ACSC.sol:140-167) uses the relay's records from the PBC forward event, with no checkpoint and no record `validUntil` check; grant with TTL block + 30 and recipient 0 | yes |
| E02-pre-barrier-revocation-repaired-e | ACCEPT / REPAIR_SUPPORTED | DecisionVerifier checks the decision against the DBC's **current** checkpoint. A PBC revocation is invisible until a revoking checkpoint is accepted, so the older certificate is accepted: an intentional window | yes |
| E02-post-barrier-revocation-paper-strict / -minimal | CONDITIONAL / SPEC_GAP | same paper path, so it grants; there is no barrier and ACCEPT_CHECKPOINT is omitted | yes (class) |
| E02-post-barrier-revocation-repaired-e | REJECT / REPAIR_SUPPORTED / STALE_STATE | DV step 10, line 87: `d.stateSequence != cp.sequence` (the sequence cause) | yes |
| E02-expired-duty-paper-strict / -minimal | CONDITIONAL / SPEC_GAP | same paper path, so it grants with an expired duty record | yes (class) |
| E02-expired-duty-repaired-e | REJECT / REPAIR_SUPPORTED / EXPIRED | DV step 13, lines 92-94: a record with `validUntil <= now` | yes |

**Paper outcomes:** frozen CONDITIONAL means acceptance depends on the configured relay forwarding the
request-time records. The ledger does not check them. All six paper rows are expected to grant; the
oracle reports the observed outcome as ACCEPT, and the frozen class is SPEC_GAP for all six. The
catalog is not edited.

**No disagreement between the catalog and the ledger was found.**

## Recipe (`integration-plan.json` sha256 78d6ebfb..)

Each of the 9 rows runs on a fresh chain pair: PBC port 18545, DBC port 18546, chain IDs
18545/28545.

- **D1** runs the controls: wrong-admin 16; Alice allow with release and one outcome; Bob deny 9.
- **D2** is a fresh second deployment with its own bootstrap, production adapter and 0700 state
  (`kind=barrier`).

**Certificate discipline (repaired-e):** the checkpoint and the **one** decision are collected after
REQUEST_ACCESS and **before the PBC update**. `exchanges.json` must hold exactly one `collect_decision`
for the request (A31). Nothing is ever re-collected.

**Pre-barrier** (REQUEST_ACCESS > REVOKE_ON_PBC > FORWARD_OR_CONSUME; **REVOKE_ON_PBC before consume**):

1. The producer CRL v2 (`--revoke 101`) is signed before the row. Signing is read-only.
2. At REVOKE_ON_PBC the H1 CA-admin installs it. Alice becomes REVOKED(19) on the PBC and authEpoch
   rises by 1.
3. **No new checkpoint is accepted** before consumption. The current DBC checkpoint is recorded at
   consumption and must equal the first one; the request authEpoch equals the checkpoint authEpoch.
4. The older certificate is consumed. Expected: a grant, with `windowSeconds` = consume time −
   revocation block time.

**Post-barrier:** the same steps, plus ACCEPT_CHECKPOINT on repaired-e after REVOKE_ON_PBC (a new
checkpoint with sequence + 1 and the new authEpoch). Expected `STALE_STATE`. The oracle requires the
sequence cause of line 87:

- the new checkpoint is current at consumption;
- `d.stateSequence` equals the old sequence, which differs from the new one;
- `d.expiresAt <= newCp.expiresAt`;
- consume time < `d.expiresAt`, request `expiresAt` and `newCp.expiresAt`, so steps 9 and 10a pass.

Paper rows omit ACCEPT_CHECKPOINT.

**Expired duty** (REQUEST_ACCESS > ADVANCE_CLOCK > FORWARD_OR_CONSUME):

1. **Setup (INSTALL_SHORT_DUTY):** the producer TempACL v2 has one entry, Alice OnDuty
   `[t-60, t+untilIn]`. It is installed before the request.
2. The request is forwarded while the duty is valid.
3. Repaired-e collects the checkpoint and decision while the duty is valid:
   - witness.py:133 would attest DENY with empty records once a record has lapsed at DBC now;
   - the decision `expiresAt` is `min(request, cp, DBC now + 30)` (witness.py:140), not capped by
     records.
4. **ADVANCE_CLOCK moves only the DBC:** `evm_setNextBlockTimestamp(max(latest+1, duty end))` then
   `evm_mine`. The PBC clock is not moved.
5. Consume. The oracle requires `duty end <= consume time < min(d.expiresAt, request expiresAt,
   cp.expiresAt)`, so the EXPIRED can only come from step 13, not step 9 (line 74) or step 10a
   (line 85). All four values and the consume block time are recorded.

**untilIn rule:** `untilIn = (PBC pending time − PBC latest block time) + 25`, bounded to 25..600 s.

- The producer signs at the PBC **latest** block time t. SL5 showed producer block 47 equal to the
  latest block. So the duty ends about 25 s after now.
- That is after the decision collection and before both the request expiry (30 s after the request)
  and the witness decision TTL (DBC now + 30 s).
- The record `validUntil` is the same on both chains: the TempACL entry end. On repaired-e it is the
  minimum with the list validity of one day.
- Any violation fails the row visibly. Nothing is retried.

## Owner producer (A1-0034; A1-0061 D-6)

The tool is the same `sign_list.sh` 806e9a98.. and `SignList.s.sol` 7aa3b1dd.. as in SL5. The conditions
are the same:

- bytes re-hashed before every call;
- the same deployment file as the stress adapter;
- argv only from the templates (`e1.barrier_sign_argv`, tested); `untilIn` is the only computed and
  bounded argument; no `--version`;
- a non-zero exit is a failed trial, kept only as sha256 and first line;
- the artifact is checked before use, including the root signature under the evaluator's own EIP-712
  encoder.

| Purpose | Invocation |
|---|---|
| `revoke-alice` | `crl H1 --revoke 101` |
| `short-duty` | `tempacl H1 --duty alice:60:{untilIn}` |

## Worker-DB precondition, re-checked for every step

**Static check (0716a8e):** the adapter operations used are `prepare_request` (pure), and
`collect_checkpoint` and `collect_decision` (Witness only, adapter.py:153-170). `release`,
`encrypt_record` and `finish_decryption` are never reached.

**Dynamic check:** the D49 probe runs at baseline and after every catalog step. That includes
INSTALL_SHORT_DUTY, REVOKE_ON_PBC, ACCEPT_CHECKPOINT and ADVANCE_CLOCK wherever the row has them. Each
observation must be the identical verified never-instantiated record.

## Verification (`manifest.json`)

**RED first:** all SL6 tests were written before any SL6 code: **144 failed**
(`red-before-implementation.txt`): 101 oracle-module-missing, 19 collector-module-missing and 24
`create_plan(barrier_stress)` errors.

The A1 pre-FREEZE conditions (2026-10-11) were added to the tests **before** RED.

**One post-RED test-data correction:** the checkpoint mutations now keep the current checkpoint
consistent with the mutated one, so each fails at its intended check. No test was weakened.

**GREEN:**

- oracle 101 passed and collector 19 passed;
- every oracle mutation fails at its intended check (`oracle-reasons.txt`);
- 7/7 collector controls and 3 unsupported variants fail for the intended reason
  (`control-reasons.txt`);
- plan tests: 24 passed;
- full suite: `.venv/bin/python -m pytest -q -rs` exit 0, **1494 passed, 0 failed, 0 skipped**, 419 s; the bracket of 3319 files is stable.

## Limits

- **Not yet run live:** the DBC clock move with checkpoints, the TempACL producer on Anvil, and the
  post-revocation checkpoint. All are unit-tested only, against a TEST-ONLY double that follows the
  pinned DecisionVerifier order.
- **Mutant counterparts are P3:** MUT_NO_STATE_BARRIER and MUT_NO_RECORD_FRESHNESS. The revocation
  window is measured per row, not characterized statistically.
- Symbolic adapter; safe-ledger, trusted-worker and one-trusted-witness assumptions.
- **Do not touch these files before the run.** All `agent3Sources` are frozen. Store helper scripts as
  `.py.txt`.
