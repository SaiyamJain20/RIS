# SL3: E03 audit-stress runner and plan (no services yet)

Paper-derived HMBC2020 reconstruction. Synthetic only. E/RQ1 is active; gate E is NOT_RUN; F and G
are locked.

Author: agent 3 (proxy), solo phase (A1-0059, A1-0064, S2-0007). **Correlated self-review.**

**Status:** runner implemented **test-first** and unit-verified; plan frozen as S3-0011. No service
has run. **No catalog row is completed by this checkpoint.**

## Rows, frozen expectations and pinned ledger facts (933d2a7)

| Row | Frozen expected | Ledger/protocol fact | Agreement |
|---|---|---|---|
| E03-dropped-outcome-paper-strict / -paper-minimal | PENDING / SUPPORTED | no `reportOutcome` call, so `PSC.getRequest` keeps status FORWARDED(1) and `outcomeLogId` 0 | yes |
| E03-dropped-outcome-repaired-e | PENDING / REPAIR_SUPPORTED | no `reportAttestedOutcome`, same | yes |
| E03-fabricated-outcome-paper-strict / -paper-minimal | CONDITIONAL / SPEC_GAP | `PSC.reportOutcome` checks the relay, status FORWARDED and the derived grant id only, never DBC state; it writes an LSC OUTCOME(4) log (complete details `abi.encode(digest, grantId, outcomeDigest, relay)`) plus `OutcomeRecorded` | yes |
| E03-fabricated-outcome-repaired-e | REJECT / REPAIR_SUPPORTED / WRONG_PROFILE | `reportOutcome` on REPAIRED_E gives `Rejected(21)`; the honest witness's `attest_grant` without an allowed grant gives NOT_COMMITTED | yes |

**No disagreement between the catalog and the ledger was found.**

## Recipe (`integration-plan.json` sha256 d768463d..)

Each of the 6 rows runs on a fresh chain pair: PBC port 18545, DBC port 18546, chain IDs
18545/28545. D1 runs the controls (wrong-admin 16; Alice allow with release and one outcome; Bob
deny 9). D2 is a fresh second deployment with its own bootstrap, production adapter and 0700 state
(`kind=audit`).

**Dropped outcome** (catalog steps exactly; **includes RELEASE**, per A1-0064 and S2-0007 R2):

1. `encrypt_record` registers the record commitments; this instantiates the worker, as release
   needs.
2. Alice's request.
3. The grant: paper `policyEnf`; repaired checkpoint, decision and `consumeDecision`.
4. A live pre-release snapshot, including the idle worker export.
5. **One** production `release`, strictly before grant expiry. It is bound to the RSC registered key
   (paper: native recipient 0, D35/A38) or to the signed recipient (repaired).
6. **No outcome.** A post-release snapshot.

The oracle requires:

- PBC FORWARDED with `outcomeLogId` 0 (PENDING), and no outcome event;
- native state unchanged by the release;
- worker delta of exactly intent plus one attempted send, delivery unknown;
- every step inside the grant lifetime.

The timeline is recorded.

**Fabricated outcome:**

1. Alice's request only (no forward or consume).
2. The relay calls `PSC.reportOutcome(digest, derived grantId, keccak("HMBC.E03.fabricated-outcome.v1"))`.

Expected:

- **Paper:** OUTCOME(4) log with exact details and hash, then `OutcomeRecorded`; status 2; DBC
  grant, count, nonces and history unchanged.
- **Repaired-e:** `Rejected(21)` with nothing changed, then `attest_grant` refused with NOT_COMMITTED.

No worker operation occurs, so the worker is recorded as verified never-instantiated (D49).

## Verification (`manifest.json`)

**RED first:** all SL3 tests were written before any SL3 code: **95 failed**
(`red-before-implementation.txt`; all missing-feature errors).

**GREEN.**

- Oracle 67 and collector 16 passed.
- 8/8 negative controls fail for the intended reason: an outcome leak, an expired release, the wrong
  recipient, a double send, a rejected paper outcome, another repaired code, a witness that attests,
  and an unsupported variant.
- Plan tests: 29 passed.
- Full suite `.venv/bin/python -m pytest -q -rs`: exit 0, **1110 passed, 0 failed, 0 skipped**,
  316 s. Bracket of 2470 files stable.

**`agent3Sources` changed since SL2 r2:**

- new `evaluation/audit_stress.py` and `evaluation/oracles/audit.py`;
- changed `evaluation/e1.py` (the `audit_stress` D2 path) and `evaluation/e2.py` (the audit plan).

## Limits

- **Not yet run live:** the D2 audit wiring, a release on D2, the paper `reportOutcome` path on
  Anvil, and the repaired `attest_grant` refusal. All are unit-tested only, with a TEST-ONLY double.
- **Paper release** must land before `policyEnf + 30 s`. Any expiry fails visibly; there is no TTL
  change.
- **Assumptions:** delivery unknown; symbolic adapter; safe-ledger, trusted-worker and
  one-trusted-witness assumptions; configured-relay stress outside A01.
- **Do not touch these files before the run.** All 94 `agent3Sources` are frozen, including every
  `evaluation/**/*.py`. Store helper scripts as `.py.txt`.
