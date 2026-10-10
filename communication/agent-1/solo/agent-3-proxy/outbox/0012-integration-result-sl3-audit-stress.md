Message-ID: S3-0012
From: agent-3 (proxy)
To: agent-1, agent-2 (proxy)
RQ: E
Task: C-E2 SL3 E03 audit stress (dropped outcome x3, fabricated outcome x3), actual fresh two-chain integration result; FREEZE S3-0011 released
Type: INTEGRATION_RESULT
Interface-version: v1
Responds-to: S3-0011, A1-0068, S2-0011
Source-manifest: plan evaluation/evidence/e2/sl3-audit-runner-20261010/integration-plan.json sha256 d768463d51da7c2ef689cf010b8ce90002898763760bd28f663eb41f4553b2fc at HEAD 9a4d9a560acaf8a6a9097a9998cb86d281ef339c (unchanged before and after); evidence evaluation/evidence/e2/sl3-audit-live-20261010/ (246 files; README 8543e094.., catalog-coverage ce348795.., live-result-audit 24aa6b14.., real-e2 cdbc9735.., source-bracket a7ed620a.., selected-manifest e5b5e82c..)

Summary: **The actual run passed: exit 0, `E2_AUDIT_STRESS_SLICE_PASS`, 6/6 rows, 459.88 s**
(2026-10-10T06:15:14Z to 06:22:54Z UTC). All 6 rows match the frozen catalog expectations.

| Row | Class | Observed |
|---|---|---|
| dropped outcome, paper-strict | **SUPPORTED** | PENDING |
| dropped outcome, paper-minimal | **SUPPORTED** | PENDING |
| dropped outcome, repaired-e | **REPAIR_SUPPORTED** | PENDING |
| fabricated outcome, paper-strict | **SPEC_GAP** | outcome without any DBC grant |
| fabricated outcome, paper-minimal | **SPEC_GAP** | same |
| fabricated outcome, repaired-e | **REPAIR_SUPPORTED** | WRONG_PROFILE(21); witness NOT_COMMITTED |

- Every row's D1 controls passed: wrong-admin 16, Alice allow with one outcome, Bob deny 9.
- These are tested reconstruction results. The fabricated rows use configured-relay stress outside
  A01, **never HMBC exploits**. Correlated solo review.

Evidence: `evaluation/evidence/e2/sl3-audit-live-20261010/`:

- `README.md`;
- `real-e2.json`, `cli.json`, `cli.stdout.json`, `cli.stderr.txt` (empty);
- `acks.json` (A1-0068, S2-0011 and FREEZE S3-0011 at 9a4d9a5; solo-verified before services);
- `catalog-coverage.json`;
- `live-result-audit.json`, `source-bracket.json`, `versions.json`;
- `selected-manifest.json` (233 redacted JSON files, 0 refused);
- `external-public-inventory.json`.

Every row's `audit-instance/{deployment,bootstrap-checked}.json`, `audit-instance/{pbc,dbc}-native/*.json`
and `audit-stress/*` are byte-identical to the run output. I verified this again after the restart,
with `cmp` and sha256 against `selected-manifest.json`. `private-adapter-state` is excluded.

**Secret scan:** a substring scan of all 246 files for the TEST-ONLY keys of 15 labels and the **9
release tokens** from the private worker databases (3 dropped-row releases and 6 D1 control releases)
found **0 hits**.

Impact:

- **Catalog progress: 28/56 actual** (22 + 6). **28 remain**: SL4 7, SL5 6, SL6 9, SL7 6.
- Gate E stays NOT_RUN. F and G stay locked.
- **FREEZE S3-0011 is RELEASED.** No services or lease remain.

Action requested:
- **agent 1:** a ledger REVIEW. Your independent re-derivation already agrees, 6/6. Then commit.
- **agent 2 (proxy):** a protocol REVIEW covering:
  - the release routing and worker delta in the dropped rows;
  - the `attest_grant` NOT_COMMITTED;
  - the never-instantiated workers in the fabricated rows.

## Exact command

```
export PATH="$HOME/.foundry/bin:$PATH"
.venv/bin/python -m evaluation.e2 --plan evaluation/evidence/e2/sl3-audit-runner-20261010/integration-plan.json --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl3-run/acks.json --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl3-run/real-e2-output
```

Exit **0**; wall **459.88 s**; stderr empty; `sourceStable: true`; 12 services started.

## Per-row native results vs the frozen catalog

| Row | Frozen expected | Native and worker result | Release margin to grant expiry | Class |
|---|---|---|---|---|
| dropped, paper-strict | PENDING / SUPPORTED | `policyEnf` grant (recipient 0, TTL +30, expires 1791613014); one release to the RSC registered key 0x98d796e3.. (intent plus 1 attempted send, delivery unknown); **no outcome**: PSC FORWARDED(1), `outcomeLogId` 0, no outcome event; native state unchanged by the release | 29 s | SUPPORTED |
| dropped, paper-minimal | PENDING / SUPPORTED | same (expires 1791613091) | 28 s | SUPPORTED |
| dropped, repaired-e | PENDING / REPAIR_SUPPORTED | `consumeDecision` grant (expiry min(decision, request) 1791613172, signed recipient 0x98d796e3..); one release to it; no attested outcome; PSC FORWARDED, 0 | 26 s | REPAIR_SUPPORTED |
| fabricated, paper-strict | CONDITIONAL / SPEC_GAP | `reportOutcome` 0x6738f952.. (block 49) with the derived grant id: LSC OUTCOME(4) log 7 (`abi.encode(digest, grantId, outcome, relay)`, detailsHash checked), `OutcomeRecorded`, PSC status 2; no DBC grant, DBC history unchanged | n/a | SPEC_GAP |
| fabricated, paper-minimal | CONDITIONAL / SPEC_GAP | same, 0xad69675c.. (49) | n/a | SPEC_GAP |
| fabricated, repaired-e | REJECT / WRONG_PROFILE | `reportOutcome` 0x4bff4b37.. (49): status 0, `Rejected(21)`, no logs, whole state unchanged; `attest_grant` refused with NOT_COMMITTED | n/a | REPAIR_SUPPORTED |

## Worker observation per row

- **Dropped ×3:** instantiated by `encrypt_record`, as RELEASE requires. The worker was an idle
  export before the release, and after it showed exactly prior + [RELEASE_INTENT, RELEASE_SENT], with
  one release row (sendAttempts 1, completedAttempts 1, delivery unknown) inside the grant lifetime.
- **Fabricated ×3:** verified never-instantiated before and after: exporter exit 1 with its exact
  message, both database paths absent. 6 probes in total (D49).

## Points stated per A1-0068 (interpretation, not defects)

1. **The paper fabricated outcome is "outcome without a grant", not "arbitrary outcome".**
   - The relay must supply the public deterministic grant id `H(digest, KSSC, dbcChainId)`. With any
     other value the report reverts WRONG_DESTINATION (PSC.sol:227-229).
   - `outcomeDigest` is opaque to the ledger.
   - So the gap is a correctly *shaped* PBC outcome for which no DBC grant exists.
2. **PENDING is a ledger-permanent state.** There is no time-based transition. Reconciliation
   ("eventual delivery and an honest reporter") is a liveness assumption the ledger does not enforce.
3. **Superseded catalog sentence.** The paper dropped rows' frozen qualification says "Current
   production owner still refuses paper grants".
   - That E0-era sentence is superseded by the production D35/A38 path `Worker._recipient_for`
     (worker.py:106-124). For PSC.profile ≠ 2 the release is bound to `RSC.recipientKeyHash(grant.gid)`,
     and the native grant recipient stays 0 (S2-0011, which also lists the earlier live uses).
   - The frozen catalog is not edited.

## Source bracket and hashes

- **Plan:** d768463d.., unchanged; it re-verifies after the run.
- **Independent bracket:** 2475 files, 26300d0d.. before and after (`source-bracket.json`). HEAD
  9a4d9a5 throughout.
- **Snapshots and hashing:** owner snapshots stable in all rows; Cast checkpoints all OK (12 clients).
- **Processes:** all 24 owned processes (12 Anvil, 12 adapters) exited 0; PIDs absent; ports 18545
  and 18546 free.
- **Commands:** 60 owner commands exited 0, plus 6 verified never-instantiated probes (exit 1,
  expected). 5618 RPC calls, all exit 0.

## Limits

- **Delivery unknown.** The PENDING rows show that local durable intent and send logs exist without
  a PBC outcome. They do not show delivery.
- Symbolic adapter; safe-ledger, trusted-worker and one-trusted-witness assumptions.
- One trial per row. Single-host Anvil, with no consensus or finality.
