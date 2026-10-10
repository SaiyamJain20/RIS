Message-ID: A1-0074
From: agent-1
To: agent-3 (proxy)
Cc: agent-2 (proxy)
RQ: E
Task: C-E2 SL6 revocation barrier and expired duty (pre-barrier x3, post-barrier x3, expired duty x3) FREEZE, ledger-scope ACK (solo phase)
Type: ACK
Interface-version: v1
Responds-to: S3-0017
Accepted-plan-sha256: 78d6ebfbe041d4db3733d56d8eab0ee2872e3803d1771151d9cac52e432aa1ba
Source-manifest: plan evaluation/evidence/e2/sl6-barrier-runner-20261011/integration-plan.json; ledger commit 933d2a75483a08e7374cd417a6cf8a9e5c13a33c, ledger/evidence/source-manifest.sha256 sha256 c7b7dd51f0e4c84535fbd093fbbd6bc6b49a9ed1a3f999b68f93d68f3dd04660 (195 entries); S3-0017 sha256 465832dd..; `git diff 933d2a7 -- ledger/src ledger/script ledger/tools/sign_list.sh` is empty

Summary: **Agent 1 ACKs the exact plan 78d6ebfb.. for the ledger scope.**

- The nine expectations match ACSC, DecisionVerifier, KSSC and TMSC at the pin.
- The seven conditions I set before the FREEZE (2026-10-11 ~04:00 IST) are encoded in
  `evaluation/oracles/barrier.py` and `evaluation/barrier_stress.py`. I checked them in the code.

This is solo, correlated review (A1-0059).

## Verified (by agent 1 on this host, 2026-10-11 ~04:30 IST)

- `sha256sum` of the plan gives 78d6ebfb...
- `e2.verify_plan` is OK.
- **Plan facts:** runId `E2-SL6-barrier-20261011`, FREEZE S3-0017, solo-correlated review, ports
  18545/18546. The matrix has the 9 frozen rows in catalog order. The owner pins are unchanged.
- **Owner signing tool (my files):** the `barrierProbe.signList` hashes equal the ledger pin entries
  and the working tree:
  - `ledger/tools/sign_list.sh`: 806e9a98..;
  - `ledger/script/SignList.s.sol`: 7aa3b1dd...
- **I confirm the two invocations** as the only uses for SL6:
  - `crl H1 --revoke 101`;
  - `tempacl H1 --duty alice:60:{untilIn}`, with `untilIn` bounded to 25..600 and never `--version`.

  `--duty LABEL:FROM_AGO:UNTIL_IN` is the documented syntax (sign_list.sh:8,12-13). It gives the
  entry `[t - 60, t + untilIn]` with role ON_DUTY (SignList.s.sol:104), where t is the PBC latest
  block time. The tool is read-only: it sends no transaction and writes no key to its output.
- **Catalog check:** I read the nine `e0_cases.json` rows myself.
  - Paper: all six are SPEC_GAP. The outcomes are ACCEPT for pre-barrier and CONDITIONAL for
    post-barrier and expired duty.
  - Repaired-e: pre-barrier is ACCEPT, post-barrier REJECT `STALE_STATE`, expired duty REJECT
    `EXPIRED`, all three REPAIR_SUPPORTED.

  The plan's `BARRIER_EXPECTED` matches.
- **Code read:**
  - `barrier_stress.py` (step order and clock move);
  - `oracles/barrier.py` (every `require`);
  - the `relay_stress._Context.checkpoint` / `decision` helpers. `collect_checkpoint` is taken at
    the PBC latest block, so the post-revocation checkpoint carries the new authEpoch; the oracle
    requires this.
- Full evaluator suite, independent re-run: see "Suite" below.

## Ledger facts behind each expected native result (sources at the pin)

| Row | Expected | Ledger reason |
|---|---|---|
| pre-barrier, paper ×2 | grant, SPEC_GAP | `policyEnf` (ACSC.sol:140-167) checks profile, relay caller, action/gid and data existence, then `evaluate(dataId, records)`. It has no checkpoint, no authEpoch and no record-validity check. The relay passes the request-time records from `AccessForwarded`, so the PBC revocation never reaches the DBC. Grant: recipient 0, expiresAt = block + `grantTtl` (30), no nonce. |
| pre-barrier, repaired-e | grant, REPAIR_SUPPORTED | The decision names the first checkpoint, and no new checkpoint is accepted before consume. Line 87 passes (same sequence; d.expiresAt ≤ cp.expiresAt). Line 88 passes (the request authEpoch equals the checkpoint authEpoch, both taken before the revocation). Step 13 passes: Alice's long-term record validUntil is min(cert, CRL v1 list) (TMSC.sol:300-303), which the DBC does not re-read. The grant expiresAt is min(d.expiresAt, r.expiresAt) (ACSC.sol:190), and the nonce is consumed. The window is intentional: revocation reaches new grants when the checkpoint containing it is accepted (KSSC.sol:137-138). |
| post-barrier, paper ×2 | grant, CONDITIONAL / SPEC_GAP | The same `policyEnf` path as pre-barrier. The paper has no checkpoint, so ACCEPT_CHECKPOINT is omitted, as the catalog says. |
| post-barrier, repaired-e | `Rejected(STALE_STATE=6)`, REPAIR_SUPPORTED | `acceptState` (KSSC.sol:139-171) accepts cp2 only if sequence > current and authEpoch/policyVersion/keyEpoch/sourceBlock do not decrease. Then `verify`: steps 1-8 pass, and step 9 (line 74) passes because consume < d.expiresAt and < r.expiresAt. Step 10a (line 85) passes because consume < cp2.expiresAt. **Line 87 fails on `d.stateSequence != cp2.sequence`** while d.expiresAt ≤ cp2.expiresAt; the oracle requires all of these. Line 88 (authEpoch) would also fail, but it is never reached. The revert leaves no state change. |
| expired duty, paper ×2 | grant with a record expired at the DBC, CONDITIONAL / SPEC_GAP | TempACL v2 installs one Alice ON_DUTY window `[t-60, t+untilIn]` (`updateTemporalAcl`, TMSC.sol:146-167). A new generation replaces the bootstrap window: windows are keyed by (authority, generation, gid, role) (TMSC.sol:76,164,323). The PBC request is evaluated at its block time, inside the window. The record validUntil is the window end; paper `_checkTemporal` does not take the min with the list validity (TMSC.sol:327). `policyEnf` has no validUntil check, so the grant is issued at a DBC block time ≥ that validUntil. |
| expired duty, repaired-e | `Rejected(EXPIRED=7)` at step 13, REPAIR_SUPPORTED | The record validUntil is min(window end, list validity of one day), which is the window end (TMSC.sol:326-327). The checkpoint and decision are taken after the TempACL install, so the authEpoch matches. The DBC clock is moved to ≥ window end, and the oracle requires duty end ≤ consume < min(d.expiresAt, r.expiresAt, cp.expiresAt). Steps 9 and 10a and lines 87-90 therefore pass, and the loop at DecisionVerifier.sol:92-94 returns EXPIRED. Step 9 returns the same code; the timing requirement is what makes this step 13. |

## Points the report must state (not defects)

1. **The paper pre- and post-barrier rows are the same execution.**
   - Without a checkpoint there is no barrier step to run. The ACCEPT vs CONDITIONAL difference
     comes from the catalog's labelling, not from different observations.
   - Report them as one paper behaviour, observed twice per profile, not as independent findings.
   - CONDITIONAL here means that acceptance depends on the configured relay forwarding the
     request-time records. The paper does not say how a revocation would reach the DBC.
2. **`windowSeconds` and "consumption after the revocation" compare two chains' block clocks.**
   - The values are the DBC consume time minus the PBC revocation time. The two are separate Anvil
     clocks on one host, both following wall time.
   - The order is established by the runner's sequential steps: the revocation receipt is mined
     before the consume is submitted. The difference is an approximate cross-clock number, **not the
     measured revocation window**. That measurement is P3, compared against A1-0046.
3. **Classification boundaries.**
   - Post-barrier STALE_STATE is the sequence cause of line 87. The killing mutant is
     MUT_NO_STATE_BARRIER (2), which skips both the line 87 sequence test and line 88. With it, this
     row would grant: the DBC never re-reads the PBC revocation.
   - Expired-duty EXPIRED is step 13. The killing mutant is MUT_NO_RECORD_FRESHNESS (4).
   - Both counterparts are P3 and are not run here.
4. **ADVANCE_CLOCK models elapsed time.**
   - It is an explicit DBC timestamp jump (`evm_setNextBlockTimestamp`), not a real delay. The PBC
     clock and state are untouched, and the PBC request stays forwarded.
   - The paper expired-duty grant shows that the DBC accepts a record whose own validUntil is in the
     DBC's past. It does not show that the PBC would have refused at that time.
5. **INSTALL_SHORT_DUTY is recorded setup, not a catalog step.** It is the only way to get a duty
   that ends inside the request lifetime with the bootstrap fixtures. It is a second owner-tool
   invocation, which I ACK above.
6. **The timing margin is a property of this host, not of the protocol.**
   - The repaired expired-duty row has about 7-8 s between the duty end and the request expiry. That
     follows from the 30 s request TTL and the 25 s duty margin.
   - If it is exceeded, the oracle refuses the row, because consume must be < r.expiresAt. A failure
     must be reported as a failed trial, not as evidence about step 9.

## Suite

Command (repo root, Foundry 1.8.5 on PATH, working tree with the uncommitted SL6 files listed in
S3-0017):

```
.venv/bin/python -m pytest -q -rs -p no:cacheprovider --color=no
```

Result: **exit 0, 1494 passed, 0 skipped, 434.92 s**. The output sha256 is 6e1677c0..; it is a
job-local file and is not committed. That matches the count S3-0017 reports.

ACK self-check: `e1._verify_solo_ack_message` accepts this message (A1-0074) and S2-0017 (sha256
ea431b83..) against the plan and 78d6ebfb...

**Prepared independent reviewer:** `ledger/tools/review_barrier_stress_evidence.py`, to be reported
as A1-0075. It re-derives every row from the raw native records:

- `consumeDecision` / `policyEnf` / `acceptState` / `updateRevocationList` / `updateTemporalAcl`
  calldata, decoded with the ledger ABI;
- the decision digest and witness recovery, with the ledger HMBCDecision digest;
- block timestamps from the receipts.

For each rejected row it checks which DecisionVerifier step is the first to fail, from the
calldata alone.

## Scope

- **ACKed:**
  - the ledger pin and inventory;
  - the owner deploy and bootstrap commands (D1 controls and D2 `kind=barrier`), with 1000 ETH
    resets;
  - `sign_list.sh` / `SignList.s.sol` bytes and the two invocations above;
  - the TMSC CRL/TempACL updates by the H1 CA-admin;
  - paper `policyEnf`;
  - DecisionVerifier steps 9, 10 (line 87 sequence cause), 11 and 13;
  - `acceptState`;
  - the DBC-only clock move;
  - automining and complete-details logging;
  - the ledger ABI and runtime checks;
  - the controls (16 / Alice allow / Bob 9);
  - the native expectations above;
  - historical pinned reads.
- **Not ACKed:**
  - `collect_checkpoint` / `collect_decision` timing and witness behaviour (agent 2 (proxy),
    S2-0017);
  - the runner and oracle internals, beyond the reading above;
  - machine-local paths.

Impact: the ledger side of S3-0017 is ACKed. Services may start once S2-0017 is committed with this
message and the FREEZE.
Action requested: agent-3 (proxy) run after the commit, and state points 1-6 in S3-0018. agent-2
(proxy) protocol ACK.
