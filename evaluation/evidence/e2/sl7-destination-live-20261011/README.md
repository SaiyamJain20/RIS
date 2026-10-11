# SL7 actual run: E01 wrong destination ×3 and expiry boundary ×3, all PASS (catalog complete)

Paper-derived HMBC2020 reconstruction. Synthetic only. Symbolic adapter, with safe-ledger,
trusted-worker and one-trusted-witness assumptions. E/RQ1 is active; gate E is NOT_RUN; F and G are
locked.

**Solo phase (A1-0059):** every review and ACK is **correlated self-review**.

## Run

**Authorization:**

- Plan `evaluation/evidence/e2/sl7-destination-runner-20261011/integration-plan.json`, SHA-256
  `d4fa294edd954a137abbb62e34ebfffee2119a87eb6490b81777a555daeb5908`.
- FREEZE S3-0019, ACKs A1-0076 and S2-0019, all at f1c1e52.
- `acks.json` was verified by the solo verifier before services.

**Command** (`export PATH="$HOME/.foundry/bin:$PATH"`), run in the background with PID 203137:

```
.venv/bin/python -m evaluation.e2 --plan evaluation/evidence/e2/sl7-destination-runner-20261011/integration-plan.json --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl7-run/acks.json --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl7-run/real-e2-output
```

**Result:** exit **0**, `E2_DESTINATION_STRESS_SLICE_PASS`, 2026-10-11T13:47:57Z to 13:57:59Z,
**602.24 s**. Stderr is empty. `sourceStable: true`.

**Host condition:** memory was low, about 2.8-2.9 GiB available with 3.8 GiB swap in use, before and
after the run (`host-before.txt`, `host-after.txt`). The host was kept idle during the run.

## Results against the frozen catalog (`catalog-coverage.json`)

| Row | Frozen expected | Observed | Class | firingStep / step2Mismatch | `decisionCollections` |
|---|---|---|---|---|---|
| E01-wrong-destination-paper-strict | CONDITIONAL / SPEC_GAP | A grants on B's tuple; A's PBC has no such request | **SPEC_GAP** | n/a | 0 |
| E01-wrong-destination-paper-minimal | same | same | **SPEC_GAP** | n/a | 0 |
| E01-wrong-destination-repaired-e | REJECT / WRONG_DESTINATION | `Rejected(3)` at A; A and B unchanged | **REPAIR_SUPPORTED** | **1 / true** | 1 |
| E01-expiry-boundary-paper-strict | CONDITIONAL / SPEC_GAP | grant at DBC time == `r.expiresAt`; grant expiry `r.expiresAt` + 30 | **SPEC_GAP** | n/a | 0 |
| E01-expiry-boundary-paper-minimal | same | same | **SPEC_GAP** | n/a | 0 |
| E01-expiry-boundary-repaired-e | REJECT / EXPIRED | `Rejected(7)` at consume time == `r.expiresAt` | **REPAIR_SUPPORTED** | **9 / n/a** | 1 |

**All 6 rows match the frozen classification and error. With SL7 the catalog comparisons are 56/56.**

## Timing

| Row | Request time | `r.expiresAt` | Consume (mined) | `d.expiresAt` | `cp.expiresAt` | Grant expiry |
|---|---|---|---|---|---|---|
| wrong destination, paper-strict | 1791726584 | 1791726614 | 1791726588 | n/a | n/a | consume + 30 |
| wrong destination, paper-minimal | 1791726697 | 1791726727 | 1791726700 | n/a | n/a | consume + 30 |
| wrong destination, repaired-e | 1791726815 | 1791726845 | 1791726821 | 1791726845 | n/a | none |
| expiry boundary, paper-strict | 1791726902 | 1791726931 | **1791726931** | n/a | n/a | 1791726961 |
| expiry boundary, paper-minimal | 1791726984 | 1791727014 | **1791727014** | n/a | n/a | 1791727044 |
| expiry boundary, repaired-e | 1791727073 | 1791727102 | **1791727102** | **1791727102** | 1791727133 | none |

In the expiry-boundary rows, `evm_setNextBlockTimestamp(r.expiresAt)` ran on the DBC only, with no
`evm_mine`. The consume was the next mined block, and its timestamp was verified to equal `r.expiresAt`.

## Deployment B (wrong-destination rows)

**Placement:** B is a third deployment on the same chain pair, with the same chain ids (18545/28545)
and different contract addresses:

- B's PSC is 0xbc8a9d0d..;
- B's KSSC is 0xe51ef867.. (repaired-e) or 0xe7f32227.. (paper);
- A's PSC is 0xd5eeb095.., and A's KSSC is 0x0c3ced2b.. or 0xf6c552e2...

**Owner commands** (pinned ledger snapshot; exact argv in `commands.json`):

- `deploy_local.sh http://127.0.0.1:18545 http://127.0.0.1:18546 <profile> complete-details E2-SL7-destination-20261011-wrong-destination-<profile>-source`
  (label `owner-deploy-source`);
- `bootstrap_fixture.sh http://127.0.0.1:18545 <B deployment.json> <out>` (label
  `owner-bootstrap-source`).

Both exited 0 in all three rows. Every B bootstrap gave wrong-admin 16.

**Funding** (`destinationFunding` in each case manifest):

| Point | Relay balance on the PBC |
|---|---|
| after A's deploy and bootstrap | 599.99 ETH |
| reset before B | 1000 ETH |
| after B's deploy | 599.99 ETH |

B used about 400 ETH, which fits.

**B deployment sha256** (`sourceDeployment`; `source-instance/deployment.json` is published):

| Profile | sha256 |
|---|---|
| paper-strict | 3988303b.. |
| paper-minimal | 0f18e2d9.. |
| repaired-e | 11105cc3.. |

## Worker-DB precondition (D49), every step

The workers of A and, in the wrong-destination rows, B were the identical verified
never-instantiated record at baseline and after every catalog step. 45 probes ran in total.

## Controls

Every row's D1 passed: wrong-admin 16, Alice allow with release and one outcome, Bob deny 9. Every A
and B bootstrap gave wrong-admin 16.

## Integrity (`live-result-audit.json`, `source-bracket.json`)

- **Processes:** 12 Anvil services and 15 adapters (3 of them B's), all exited 0; all PIDs are
  absent; ports 18545 and 18546 are free.
- **Per profile:** sources stable, services stopped, and the Cast checkpoint stable (12 checkpoint
  files, all OK).
- **Commands:**
  - 99 owner commands: 0 unexpected non-zero exits, and 45 verified never-instantiated probes
    (exit 1, expected);
  - 6641 RPC calls, all exit 0.
- **Independent bracket:** 3731 files, 4e359a06.. before and after. HEAD was f1c1e52 throughout.

## Never-publish scan (`selected-manifest.json`)

- **Selection:** 271 JSON files, 0 refused, all byte-identical to the run output (checked with `cmp`).
- **Keep-set** (123 files), unmodified:
  - per row, `destination-instance/` and, for wrong destination, `source-instance/`
    `{deployment,bootstrap-checked}.json` and `{pbc,dbc}-native/*`;
  - all of `destination-stress/*`, including `destination-stress/source/*`, B's snapshots and
    exchanges.
- **Excluded:** every `.txt`, and the private adapter state of A and B.
- **Substring scan** (including `source-instance/`):
  - the TEST-ONLY keys of 15 labels;
  - every frozen-vector `signerPrivateKey`;
  - the 6 release tokens (D1 Alice controls only).

  Result: **0 hits**.

## Points stated per A1-0076 (interpretation, not defects)

1. **The repaired wrong-destination rejection is the source binding (step 1, line 60), not the
   destination binding.** Step 2 (lines 61-64) also mismatches but is never reached. The row cannot
   kill MUT_NO_DESTINATION_BINDING (`killsNoDestinationBindingMutant: false`). How mutant 1 is
   detected is a P3 decision (A1-0039).
2. **The paper wrong-destination grant references a request that does not exist on A's PBC**
   (`getRequest` status 0). It is a chosen completion under compromised-relay stress, outside A01: a
   SPEC_GAP, not an HMBC exploit. The forwarded paper tuple omits both destination and source.
3. **"Exactly at expiry" is a property of `>=`.** The boundary instant is already expired, consistent
   with the other ledger validity checks. This is not a test of `expiresAt − 1`: the supplementary
   `eth_call` was skipped, so acceptance one second earlier is not shown in SL7.
4. **The clock pin is the DBC only.** The paper rows show the DBC grants at the PBC request's expiry
   instant. That expiry is not visible to paper `policyEnf`.
5. **B is a third deployment on the same chain pair.** Its records, deployment file (sha256 bound)
   and adapter state are separate from A's. The never-publish scan covered `source-instance/`.

## Limits

- One trial per row. Single-host Anvil, with no consensus or finality.
- MUT_NO_DESTINATION_BINDING detection, the other mutants and the revocation window are P3.
- Symbolic adapter.
