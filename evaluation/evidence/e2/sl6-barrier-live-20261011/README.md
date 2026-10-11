# SL6 actual run: E02 revocation barrier and expired duty ×9, all PASS

Paper-derived HMBC2020 reconstruction. Synthetic only. Symbolic adapter, with safe-ledger,
trusted-worker and one-trusted-witness assumptions. E/RQ1 is active; gate E is NOT_RUN; F and G are
locked.

**Solo phase (A1-0059):** every review and ACK is **correlated self-review**.

## Run

**Authorization:**

- Plan `evaluation/evidence/e2/sl6-barrier-runner-20261011/integration-plan.json`, SHA-256
  `78d6ebfbe041d4db3733d56d8eab0ee2872e3803d1771151d9cac52e432aa1ba`.
- FREEZE S3-0017, ACKs A1-0074 and S2-0017, all at 0d9409e.
- `acks.json` was verified by the solo verifier before services.

**Command** (`export PATH="$HOME/.foundry/bin:$PATH"`), run in the background with PID 3999843:

```
.venv/bin/python -m evaluation.e2 --plan evaluation/evidence/e2/sl6-barrier-runner-20261011/integration-plan.json --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl6-run/acks.json --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl6-run/real-e2-output
```

**Result:** exit **0**, `E2_BARRIER_STRESS_SLICE_PASS`, 2026-10-11T07:28:59Z to 07:41:15Z, **736.64 s**.
Stderr is empty. `sourceStable: true`.

**Host condition:** memory was low, about 3.2 GiB available with 4.4 GiB swap in use, both before
and after the run (`host-before.txt`, `host-after.txt`). The host was kept idle during the run.

## Results against the frozen catalog (`catalog-coverage.json`)

| Row | Frozen expected | Observed | Class | `decisionCollections` |
|---|---|---|---|---|
| E02-pre-barrier-revocation-paper-strict | ACCEPT / SPEC_GAP | `policyEnf` grants after the PBC revocation | **SPEC_GAP** | 0 |
| E02-pre-barrier-revocation-paper-minimal | ACCEPT / SPEC_GAP | same | **SPEC_GAP** | 0 |
| E02-pre-barrier-revocation-repaired-e | ACCEPT / REPAIR_SUPPORTED | grant on the unchanged checkpoint (seq 1); cross-clock window 2 s | **REPAIR_SUPPORTED** | 1 |
| E02-post-barrier-revocation-paper-strict | CONDITIONAL / SPEC_GAP | `policyEnf` grants after the revocation (no barrier exists) | **SPEC_GAP** | 0 |
| E02-post-barrier-revocation-paper-minimal | CONDITIONAL / SPEC_GAP | same | **SPEC_GAP** | 0 |
| E02-post-barrier-revocation-repaired-e | REJECT / STALE_STATE | `Rejected(6)`, **sequence cause** (decision seq 1, current seq 2) | **REPAIR_SUPPORTED** | 1 |
| E02-expired-duty-paper-strict | CONDITIONAL / SPEC_GAP | `policyEnf` grants at DBC time = duty end | **SPEC_GAP** | 0 |
| E02-expired-duty-paper-minimal | CONDITIONAL / SPEC_GAP | same | **SPEC_GAP** | 0 |
| E02-expired-duty-repaired-e | REJECT / EXPIRED | `Rejected(7)` at **step 13** | **REPAIR_SUPPORTED** | 1 |

**All 9 rows match the frozen classification and error.** In the four CONDITIONAL paper rows the
observed outcome is a grant (A1-0074 point 1).

## Timing blocks (repaired-e)

| Row | Decision collected at (DBC) | Duty end | Consume | `d.expiresAt` | Request `expiresAt` | Current `cp.expiresAt` | Sequence (decision / current) |
|---|---|---|---|---|---|---|---|
| pre-barrier | 1791703981 | n/a | 1791703985 | 1791704009 | 1791704009 | 1791704040 | 1 / 1 |
| post-barrier | 1791704220 | n/a | 1791704225 | 1791704248 | 1791704248 | 1791704283 | 1 / 2 |
| expired duty | 1791704470 | 1791704490 | 1791704491 | 1791704498 | 1791704498 | 1791704529 | 1 / 1 |

**Post-barrier:**

- checkpoint 1: seq 1, authEpoch 3, source block 48;
- checkpoint 2: seq 2, authEpoch 4, source block 49 (the revocation block). It was current at
  consume;
- `d.expiresAt` 1791704248 ≤ `cp2.expiresAt` 1791704283;
- consume time is below every expiry, so line 87 fails only on the sequence.

**Expired duty:**

- `untilIn` was 29 (repaired) and 28 (paper).
- ADVANCE_CLOCK moved only the DBC, from 1791704472 to 1791704490.
- duty end 1791704490 ≤ consume 1791704491 < min(1791704498, 1791704498, 1791704529).
- The margin to the request expiry was 7 s.

## Owner producer (A1-0034, A1-0061 D-6)

There were 9 producer calls, all exit 0 in 1.9 s or less: `crl H1 --revoke 101` in 6 rows and
`tempacl H1 --duty alice:60:{28|29}` in 3 rows. Each was checked as in S3-0017. The output is
published as `barrier-stress/signed-list.json`; the raw producer files stay in the private run
output.

## Worker-DB precondition (D49), every step

Every row's D2 worker was the identical verified never-instantiated record at baseline and after
every catalog step:

- INSTALL_SHORT_DUTY, REQUEST_ACCESS, REVOKE_ON_PBC, ACCEPT_CHECKPOINT and ADVANCE_CLOCK, where the
  row has them;
- FORWARD_OR_CONSUME.

49 probes ran in total.

## Controls

Every row's D1 passed: wrong-admin 16, Alice allow with release and one outcome, Bob deny 9. Every D2
bootstrap also gave wrong-admin 16.

## Integrity (`live-result-audit.json`, `source-bracket.json`)

- **Processes:** 18 Anvil services and 18 adapters, all exited 0; all PIDs are absent; ports 18545
  and 18546 are free.
- **Per profile:** sources stable, services stopped, and the Cast checkpoint stable (18 checkpoint
  files, all OK).
- **Commands:**
  - 130 owner commands: 0 unexpected non-zero exits, 49 verified never-instantiated probes (exit 1,
    expected), and 9 producer calls (exit 0);
  - 8859 RPC calls, all exit 0.
- **Independent bracket:** 3326 files, c86da89e.. before and after. HEAD was 0d9409e throughout.

## Never-publish scan (`selected-manifest.json`)

- **Selection:** 379 JSON files, 0 refused, all byte-identical to the run output (checked with `cmp`).
- **Per row, unmodified:**
  - `barrier-instance/{deployment,bootstrap-checked}.json`;
  - `barrier-instance/{pbc,dbc}-native/*`;
  - all of `barrier-stress/*`.

  That is 162 keep-set files.
- **Excluded:** every `.txt`, including raw producer logs; the raw producer `.json` outputs;
  `private-adapter-state`.
- **Substring scan:**
  - the TEST-ONLY keys of 15 labels, including the H1-H4 root and CA-admin keys;
  - every frozen-vector `signerPrivateKey`;
  - the 9 release tokens from the private worker databases (D1 Alice controls only).

  Result: **0 hits**.

## Points stated per A1-0074 (interpretation, not defects)

1. **The paper pre- and post-barrier rows are the same execution.** Without a checkpoint there is no
   barrier step. ACCEPT vs CONDITIONAL comes from the catalog's labels, not from different
   observations. Report them as one paper behaviour, observed twice per profile. CONDITIONAL means
   acceptance depends on the configured relay forwarding the request-time records. The paper does
   not say how a revocation would reach the DBC.
2. **`windowSeconds` and "consumption after the revocation" compare two chains' block clocks**:
   DBC consume time minus PBC revocation time, on two Anvil clocks following wall time. The order is
   established by the runner's sequential steps. The 2 s value is an approximate cross-clock
   number, **not the measured revocation window**. That measurement is P3, against A1-0046.
3. **Classification boundaries.**
   - Post-barrier STALE_STATE is the sequence cause of line 87. The killing mutant is
     MUT_NO_STATE_BARRIER; with it, this row would grant.
   - Expired-duty EXPIRED is step 13. The killing mutant is MUT_NO_RECORD_FRESHNESS.
   - Both counterparts are P3 and were not run.
4. **ADVANCE_CLOCK models elapsed time.** It is an explicit DBC timestamp jump, not a real delay.
   The PBC clock and state are untouched, and the PBC request stays forwarded. The paper expired-duty
   grant shows the DBC accepts a record whose `validUntil` is in the DBC's past. It does not show
   that the PBC would have refused at that time.
5. **INSTALL_SHORT_DUTY is recorded setup, not a catalog step.** It is a second owner-tool
   invocation, ACKed in A1-0074.
6. **The timing margin is a property of this host, not of the protocol.** The repaired expired-duty
   margin was 7 s. Had it been exceeded, the oracle would have refused the row (failed trial), and
   it would not be evidence about step 9.

## Limits

- One trial per row. Single-host Anvil, with no consensus or finality.
- The mutant counterparts and the measured revocation window are P3.
- Symbolic adapter.
