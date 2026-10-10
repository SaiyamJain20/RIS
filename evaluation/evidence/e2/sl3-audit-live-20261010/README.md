# SL3 actual run: E03 audit stress ×6, all PASS

Paper-derived HMBC2020 reconstruction. Synthetic only. Symbolic adapter, with safe-ledger,
trusted-worker and one-trusted-witness assumptions. E/RQ1 is active; gate E is NOT_RUN; F and G are
locked.

**Solo phase (A1-0059):** every review and ACK is **correlated self-review**.

## Run

**Authorization:**

- Plan `evaluation/evidence/e2/sl3-audit-runner-20261010/integration-plan.json`, SHA-256
  `d768463d51da7c2ef689cf010b8ce90002898763760bd28f663eb41f4553b2fc`.
- FREEZE S3-0011, ACKs A1-0068 and S2-0011, all at 9a4d9a5.
- `acks.json` was verified by the solo verifier before services.

**Command** (`export PATH="$HOME/.foundry/bin:$PATH"`):

```
.venv/bin/python -m evaluation.e2 --plan evaluation/evidence/e2/sl3-audit-runner-20261010/integration-plan.json --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl3-run/acks.json --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl3-run/real-e2-output
```

**Result:** exit **0**, `E2_AUDIT_STRESS_SLICE_PASS`, 2026-10-10T06:15:14Z to 06:22:54Z, **459.88 s**.
Stderr is empty.

## Results against the frozen catalog (`catalog-coverage.json`)

| Row | Frozen expected | Observed | Class | Release margin |
|---|---|---|---|---|
| E03-dropped-outcome-paper-strict | PENDING / SUPPORTED | `policyEnf` grant (recipient 0, TTL +30, expires 1791613014); **one** release to the RSC key 0x98d7.. (intent plus 1 attempted send, delivery unknown); no outcome; PSC FORWARDED, `outcomeLogId` 0; native state unchanged by the release | **SUPPORTED** (PENDING) | 29 s |
| E03-dropped-outcome-paper-minimal | PENDING / SUPPORTED | same (expires 1791613091) | **SUPPORTED** (PENDING) | 28 s |
| E03-dropped-outcome-repaired-e | PENDING / REPAIR_SUPPORTED | `consumeDecision` grant (expiry = min(decision, request) = 1791613172, signed recipient 0x98d7..); one release to it; no attested outcome; PSC FORWARDED, 0 | **REPAIR_SUPPORTED** (PENDING) | 26 s |
| E03-fabricated-outcome-paper-strict | CONDITIONAL / SPEC_GAP | request only; relay `reportOutcome` with the derived grant id: LSC OUTCOME(4) log 7 with complete details and hash, `OutcomeRecorded`, status 2; **no DBC grant at all**, DBC unchanged | **SPEC_GAP** | n/a |
| E03-fabricated-outcome-paper-minimal | CONDITIONAL / SPEC_GAP | same | **SPEC_GAP** | n/a |
| E03-fabricated-outcome-repaired-e | REJECT / WRONG_PROFILE | `reportOutcome` gives `Rejected(21)`, no logs, no change; `attest_grant` of the absent grant refused with NOT_COMMITTED | **REPAIR_SUPPORTED** | n/a |

**All 6 rows match their frozen expectations.**

**Worker observation:**

- Dropped rows: the worker was instantiated by `encrypt_record`. It was idle before the release and
  showed exactly one release delta after.
- Fabricated rows: verified never-instantiated before and after, 6 probes (D49).

**Controls passed in every row** (D1): wrong-admin (16, also in the D2 bootstrap), Alice allow with
release and one outcome, Bob deny (9).

## Points stated per A1-0068 (interpretation, not defects)

1. **The paper fabricated outcome is "outcome without a grant", not "arbitrary outcome".** The relay
   must supply the public deterministic grant id `H(digest, KSSC, dbcChainId)`; any other value
   reverts WRONG_DESTINATION (PSC.sol:227-229). `outcomeDigest` is opaque to the ledger. So the gap is
   a correctly *shaped* PBC outcome for which no DBC grant exists.
2. **PENDING is a ledger-permanent state.** There is no time-based transition. "Reconciliation
   requires eventual delivery and an honest reporter" is a liveness assumption; the ledger enforces no
   deadline.
3. **Stale catalog text.** The paper dropped rows' qualification still says "Current production owner
   still refuses paper grants". That is **superseded** by the production D35/A38 path,
   `Worker._recipient_for` (worker.py:106-124): for PSC.profile ≠ 2 the release is bound to
   `RSC.recipientKeyHash(grant.gid)`, and the native grant recipient stays 0 (S2-0011). The frozen
   catalog is unchanged.

## Integrity, processes and custody

- **Sources stable:**
  - the plan re-verifies after the run;
  - the independent bracket of 2475 files is 26300d0d.. both before and after;
  - HEAD was 9a4d9a5 throughout;
  - every row's owner snapshots are stable; Cast checkpoints are all OK (12 clients).
- **Processes:** all 24 owned processes (12 Anvil, 12 adapters) exited 0, and their PIDs are absent.
  Ports 18545 and 18546 are free.
- **Commands:** 60 owner commands exited 0, plus 6 verified never-instantiated probes (exit 1,
  expected). 5618 RPC calls, all exit 0.
- **Public evidence:** 233 redacted JSON files under `run/`, including every row's
  `audit-instance/{deployment,bootstrap-checked}.json`, `audit-instance/{pbc,dbc}-native/*.json` and
  `audit-stress/*`, byte-identical to the run output (`cmp` and sha256 against
  `selected-manifest.json`).
- **Secret scan:** the substring scan of all 241 files checked the TEST-ONLY keys of 15 labels and the
  **9 release tokens** in the private worker databases (3 dropped-row and 6 D1 releases). 0 hits.
  Worker exports carry token digests only.
- **Not published:** `private-adapter-state` and raw logs stay in `tmp/p3/sl3-run`, hashed in
  `external-public-inventory.json`.

## Limits

- Tested reconstruction results; configured-relay stress (fabricated rows) lies outside A01, never
  HMBC exploits.
- Delivery unknown: `RELEASE_SENT` is an attempted send.
- One trial per row. Single-host Anvil.
