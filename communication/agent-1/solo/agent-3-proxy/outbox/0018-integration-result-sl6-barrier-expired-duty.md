Message-ID: S3-0018
From: agent-3 (proxy)
To: agent-1, agent-2 (proxy)
RQ: E
Task: C-E2 SL6 E02 revocation barrier and expired duty (pre-barrier x3, post-barrier x3, expired duty x3), actual fresh two-chain integration result; FREEZE S3-0017 released
Type: INTEGRATION_RESULT
Interface-version: v1
Responds-to: S3-0017, A1-0074, S2-0017
Source-manifest: plan evaluation/evidence/e2/sl6-barrier-runner-20261011/integration-plan.json sha256 78d6ebfbe041d4db3733d56d8eab0ee2872e3803d1771151d9cac52e432aa1ba at HEAD 0d9409e7d879e78d89e51a0327bff1315b54b826 (unchanged before and after); evidence evaluation/evidence/e2/sl6-barrier-live-20261011/ (393 files; README a18e8c28.., catalog-coverage b3bec98c.., live-result-audit 3938e56c.., real-e2 2630cde8.., source-bracket 64b996da.., selected-manifest d3191575..)

Summary: **The actual run passed: exit 0, `E2_BARRIER_STRESS_SLICE_PASS`, 9/9 rows, 736.64 s**
(2026-10-11T07:28:59Z to 07:41:15Z UTC, PID 3999843). All 9 rows match the frozen catalog
classification and error.

| Row | Class | Observed | `decisionCollections` (A31) |
|---|---|---|---|
| pre-barrier, paper-strict | **SPEC_GAP** | `policyEnf` grant after the PBC revocation | 0 |
| pre-barrier, paper-minimal | **SPEC_GAP** | same | 0 |
| pre-barrier, repaired-e | **REPAIR_SUPPORTED** | grant on the unchanged checkpoint (intentional window) | **1** |
| post-barrier, paper-strict | **SPEC_GAP** | `policyEnf` grant (no barrier exists) | 0 |
| post-barrier, paper-minimal | **SPEC_GAP** | same | 0 |
| post-barrier, repaired-e | **REPAIR_SUPPORTED** | `Rejected(6)` STALE_STATE, sequence cause | **1** |
| expired duty, paper-strict | **SPEC_GAP** | `policyEnf` grant at DBC time = duty end | 0 |
| expired duty, paper-minimal | **SPEC_GAP** | same | 0 |
| expired duty, repaired-e | **REPAIR_SUPPORTED** | `Rejected(7)` EXPIRED at step 13 | **1** |

- **Controls:** every row's D1 passed: wrong-admin 16, Alice allow with one outcome, Bob deny 9.
  Every D2 bootstrap also gave wrong-admin 16.
- **Owner producer:** 9 calls, all exit 0 in 1.9 s or less.
- **Worker:** verified never-instantiated after every step, 49 probes in total.
- **Host condition:** memory was low, about 3.2 GiB available with 4.4 GiB swap in use before and
  after. I kept the host idle during the run.
- Tested reconstruction results, **never HMBC exploits**. Correlated solo review.

Evidence: `evaluation/evidence/e2/sl6-barrier-live-20261011/`:

- `README.md`;
- `real-e2.json`, `cli.json`, `cli.stdout.json`, `cli.stderr.txt` (empty);
- `host-before.txt`, `host-after.txt`;
- `acks.json` (A1-0074, S2-0017 and FREEZE S3-0017 at 0d9409e; solo-verified before services);
- `catalog-coverage.json` (per-row timing blocks and `decisionCollections`);
- `live-result-audit.json`, `source-bracket.json`;
- `versions.json` (recorded before the run);
- `selected-manifest.json` (379 JSON files, 0 refused);
- `external-public-inventory.json`.

**Copy check:** every selected file is byte-identical to the run output, checked with `cmp` (379/379).
That includes the full per-row keep-set (162 files):

- `barrier-instance/{deployment,bootstrap-checked}.json`;
- `barrier-instance/{pbc,dbc}-native/*`;
- all of `barrier-stress/*`: signed-list, public-call, stress-transaction, revocation-transaction or
  duty-transaction, before/after (+ blocks), facts, timeline, exchanges, result.

**Excluded:** every raw producer file (`barrier-sign-list-NN.{json,txt}`, and every `.txt`), and
`private-adapter-state`.

**Never-publish scan:** a substring scan of all 393 files found **0 hits**. It checked:

- the TEST-ONLY keys of 15 labels (relay, alice, bob, H1-H4 root and CA-admin, witness-1..4);
- every frozen-vector `signerPrivateKey`;
- the 9 release tokens from the private worker databases (D1 Alice controls only).

Impact:

- **Catalog progress: 50/56 actual** (41 + 9). **6 remain**: SL7.
- Gate E stays NOT_RUN. F and G stay locked.
- **FREEZE S3-0017 is RELEASED.** No services or lease remain.

Action requested:
- **agent 1:** a ledger REVIEW, then commit.
- **agent 2 (proxy):** a protocol REVIEW covering:
  - the checkpoint and decision timing (the decision while on duty, before the revocation);
  - one decision per request;
  - the never-instantiated worker after every step;
  - the key and token scans.

## Exact command

```
export PATH="$HOME/.foundry/bin:$PATH"
.venv/bin/python -m evaluation.e2 --plan evaluation/evidence/e2/sl6-barrier-runner-20261011/integration-plan.json --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl6-run/acks.json --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl6-run/real-e2-output
```

Exit **0**; wall **736.64 s**; stderr empty; `sourceStable: true`; 18 services started.

## Timing blocks (repaired-e; also in `catalog-coverage.json` and each `result.json`)

| Row | Decision collected (DBC) | Duty end | Consume | `d.expiresAt` | Request `expiresAt` | Current `cp.expiresAt` | Sequence (decision / current) |
|---|---|---|---|---|---|---|---|
| pre-barrier | 1791703981 | n/a | 1791703985 | 1791704009 | 1791704009 | 1791704040 | 1 / 1 |
| post-barrier | 1791704220 | n/a | 1791704225 | 1791704248 | 1791704248 | 1791704283 | 1 / 2 |
| expired duty | 1791704470 | 1791704490 | 1791704491 | 1791704498 | 1791704498 | 1791704529 | 1 / 1 |

**Pre-barrier:**

- checkpoint seq 1 (authEpoch 3, source block 48) and the one decision come before the revocation
  (PBC block 49, authEpoch 3 → 4, Alice REVOKED 19);
- no new checkpoint was accepted, and the current checkpoint at consume was seq 1;
- `consumeDecision` 0x1cc96464.. granted with expiry min(decision, request);
- cross-clock `windowSeconds` = 2.

**Post-barrier:**

- checkpoint 2 has seq 2, authEpoch 4 and source block 49. It was accepted after the revocation and
  was current at consume;
- `d.expiresAt` 1791704248 ≤ `cp2.expiresAt` 1791704283;
- consume time is below every expiry;
- 0xbf02ffaa.. gave `Rejected(6)`, with no grant and the nonce unchanged;
- `staleCause: "sequence"`.

**Expired duty:**

- `untilIn` 29;
- the decision was collected 20 s before the duty end;
- the DBC-only clock moved from 1791704472 to 1791704490;
- 0x5f161242.. gave `Rejected(7)`;
- `expiredStep: 13`;
- the margin to the request expiry was 7 s.

**Paper rows:**

- each `policyEnf` grant (recipient 0, TTL +30) used the request-time records: 0xa0598945..,
  0x7ef3faba.., 0x4fd57039.., 0x0b62cbee.., 0x811f74a7.., 0x9ae000fa..;
- in the barrier rows it came after the revocation (PBC block 49);
- in the expired-duty rows it came at DBC time = duty end (`untilIn` 28).

## Points stated per A1-0074 (interpretation, not defects)

1. **The paper pre- and post-barrier rows are the same execution.** Without a checkpoint there is no
   barrier step. ACCEPT vs CONDITIONAL comes from the catalog's labels, not from different
   observations. They are one paper behaviour, observed twice per profile. CONDITIONAL means
   acceptance depends on the configured relay forwarding the request-time records. The paper does
   not say how a revocation would reach the DBC.
2. **`windowSeconds` and "consumption after the revocation" compare two chains' block clocks.** The
   value is DBC consume time minus PBC revocation time, on two Anvil clocks following wall time. The
   order is established by the runner's sequential steps: the revocation receipt is mined before the
   consume is submitted. The 2 s value is an approximate cross-clock number, **not the measured
   revocation window**. That is P3, against A1-0046.
3. **Classification boundaries.**
   - Post-barrier STALE_STATE is the sequence cause of line 87. The killing mutant is
     MUT_NO_STATE_BARRIER; with it, this row would grant.
   - Expired-duty EXPIRED is step 13. The killing mutant is MUT_NO_RECORD_FRESHNESS.
   - Both counterparts are P3 and were not run.
4. **ADVANCE_CLOCK models elapsed time.** It is an explicit DBC timestamp jump
   (`evm_setNextBlockTimestamp` + `evm_mine`), not a real delay. The PBC clock and state are
   untouched, and the PBC request stays forwarded. The paper expired-duty grant shows the DBC accepts
   a record whose `validUntil` is in the DBC's past. It does not show the PBC would have refused at
   that time.
5. **INSTALL_SHORT_DUTY is recorded setup, not a catalog step.** It is a second owner-tool
   invocation, ACKed in A1-0074.
6. **The timing margin is a property of this host, not of the protocol.** The repaired expired-duty
   margin was 7 s. An overrun would have been refused by the oracle and reported as a failed trial,
   not as evidence about step 9.

## Source bracket and hashes

- **Plan:** 78d6ebfb.., unchanged; it re-verifies after the run.
- **Independent bracket:** 3326 files, c86da89e.. before and after. HEAD 0d9409e throughout.
- **Snapshots and hashing:** owner snapshots stable in all rows; Cast checkpoints all OK (18 files).
- **Processes:** all 36 owned processes (18 Anvil, 18 adapters) exited 0; their PIDs are absent;
  ports 18545 and 18546 are free.
- **Commands:**
  - 130 owner commands: 0 unexpected non-zero exits, plus 49 verified never-instantiated probes
    (exit 1, expected), and 9 producer calls with exit 0;
  - 8859 RPC calls, all exit 0.

## Limits

- One trial per row. Single-host Anvil, with no consensus or finality.
- The mutant counterparts and the measured revocation window are P3.
- Symbolic adapter; safe-ledger, trusted-worker and one-trusted-witness assumptions.
