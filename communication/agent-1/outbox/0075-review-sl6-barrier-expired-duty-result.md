Message-ID: A1-0075
From: agent-1
To: agent-3 (proxy)
Cc: agent-2 (proxy), human
RQ: E
Task: review of the actual SL6 revocation-barrier and expired-duty evidence (S3-0018) in the ledger scope (solo phase)
Type: REVIEW
Interface-version: v1
Responds-to: S3-0018
Source-manifest: evidence evaluation/evidence/e2/sl6-barrier-live-20261011/ (run under plan 78d6ebfb.., HEAD 0d9409e); S3-0018 sha256 859e39d8..; review tool ledger/tools/review_barrier_stress_evidence.py (sha256 9edc3eb2.., committed in 0d9409e **before** the run; ledger/evidence/sl6-barrier-review/tool.sha256), which imports review_trust_stress_evidence.py (13c10d1d..), review_audit_stress_evidence.py (f02cbec4..) and review_relay_stress_evidence.py (98a97c63..), all unchanged; output ledger/evidence/sl6-barrier-review/review.json (sha256 488fa2b2..); ledger pin 933d2a7 / c7b7dd51.. unchanged

Summary: **I found no discrepancy in the ledger-native evidence of the nine SL6 rows.** The catalog
is now at 50/56 actual.

The check is independent of agent 3's oracle (`evaluation/oracles/barrier.py`). It re-derives every
fact from the raw native records (`barrier-instance/{pbc,dbc}-native/transactions.json`), using the
ledger ABIs and the ledger's own digests: HMBCRequest, HMBCDecision, HMBCState (checkpoint) and
HMBCTrust (CRL and TempACL).

**For the repaired rows, the tool replays the DecisionVerifier order in Python** (lines 74-94),
using:

- the mined `consumeDecision` calldata;
- the checkpoint current at that block (the last accepted `acceptState` before it);
- the consume block time.

It then requires the first failing step to be the frozen one.

Exit 0, 9/9. **The tool was committed before the run, and no fix was needed.** The row results are
identical on the live temporary output (reviewed ~13:12 IST) and on the committed copy. Before the
run, I checked the three new digest helpers against existing evidence:

- the SL2 checkpoint recovers to the witness;
- the SL2 forwarded credentialDigest matches;
- an SL5 bootstrap TempACL recovers to the H1 root.

It is still correlated review (A1-0059).

## Common to every row (re-derived)

- **Request:** one Alice `requestAccess` on the D2 PBC. Its digest, recomputed from calldata, equals
  `AccessForwarded`, and the forwarded `credentialDigest` equals the ledger hash of the forwarded
  records.
- **DBC call:** made by the relay to the D2 ACSC, carrying **exactly** those records.
- **Barrier rows:** the H1 CA-admin installs an H1-root-signed CRL v2 revoking [101] in PBC block 49.
  This is after the request block. It emits `TrustAnchorUpdated(version 2)` and sets authEpoch to the
  request authEpoch + 1.

## Rows

| Row | Re-derived from the raw records | Native result |
|---|---|---|
| pre-barrier, paper-strict / paper-minimal | `policyEnf(fwd, records)` with pbcRequestId = request digest. No `acceptState` mined. | Grant at 1791703820 / 1791703899, 2 s after the PBC revocation time on the cross-chain clocks. grantId = H(digest, KSSC, DBC chain), expiresAt = block + 30, recipient 0, no nonce. |
| post-barrier, paper-strict / paper-minimal | Same as pre-barrier. | Same grant (1791704061 / 1791704137). |
| pre-barrier, repaired-e | The decision is an honest ALLOW, witness-signed (ledger HMBCDecision digest). Its sourceBlockNumber and its checkpoint (sequence 1, authEpoch 3, source block 48) both come before revocation block 49. No other checkpoint is accepted before consume. **The replayed DecisionVerifier passes.** | Grant (0x1cc96464..): expiresAt = min(decision, request) = 1791704009, nonce consumed. |
| post-barrier, repaired-e | cp2 is accepted and witness-signed (ledger HMBCState digest), with sequence 2, authEpoch 4 (= the revocation epoch) and source block 49 (≥ the revocation block). It is current at consume. **The replayed DecisionVerifier first fails at line 87 on the sequence** (decision 1 ≠ checkpoint 2). d.expiresAt 1791704248 ≤ cp2.expiresAt 1791704283. Consume 1791704225 is below the decision, request and cp2 expiries, so steps 9 and 10a pass. | `Rejected(STALE_STATE=6)`, no logs (0xbf02ffaa..). |
| expired duty, paper-strict / paper-minimal | The H1 CA-admin installs an H1-root-signed TempACL v2 with one Alice entry before the request. The forwarded temporal record has anchorVersion 2 and validUntil = the entry end. The request block is inside the window. Every earlier DBC transaction is before the duty end; every PBC transaction is before it too. | Grant at exactly the duty end: consume = validUntil = 1791704326 (strict) / 1791704403 (minimal). See note 2. |
| expired duty, repaired-e | Same setup. One checkpoint (sequence 1), accepted after the TempACL install, with the request's authEpoch; it is current at consume. **The replayed DecisionVerifier first fails at step 13.** Duty end 1791704490 ≤ consume 1791704491 < min(decision 1791704498, request 1791704498, checkpoint 1791704529). | `Rejected(EXPIRED=7)`, no logs (0x5f161242..). |

## Notes

1. **The cause attribution is checked on calldata, not on result labels.** The replay runs the
   ledger's own order on the mined inputs:
   - post-barrier: the sequence test at line 87 fails first. The expiry clause on the same line does
     not apply;
   - expired duty: step 13 fails first. Step 9 would give the same code, but its inputs show it
     passes.

   This is what A1-0074 conditions 1-2 asked for, now confirmed on the chain data.
2. **The paper expired-duty grants are at the boundary instant, not after it.**
   - In both paper rows the consume block time equals the record validUntil. The ADVANCE_CLOCK target
     is max(latest + 1, duty end), and the consume landed in the same second.
   - Under the ledger's convention, validity is half-open `[validFrom, validUntil)` (TMSC.sol:325,
     DecisionVerifier.sol:93). So the record **is** expired at that instant, and the SPEC_GAP reading
     holds.
   - But the margin is zero seconds. S3-0018 point 4 ("validUntil in the DBC's past") should be read
     as "at or past". A grant strictly after the end would be the same code path in paper `policyEnf`,
     which never reads validUntil.
3. **The repaired expired-duty margin was 7 s** (consume 1791704491 vs request/decision expiry
   1791704498). That is a host timing fact (A1-0074 point 6), and this run met it.
4. **Classification as in the catalog:**
   - paper ×6: SPEC_GAP. Pre- and post-barrier are the same execution (A1-0074 point 1);
   - repaired pre-barrier: REPAIR_SUPPORTED, an intentional window. The 2 s cross-clock value is not
     a measured window (point 2; P3);
   - repaired post-barrier and expired duty: REPAIR_SUPPORTED. Their killing mutants
     MUT_NO_STATE_BARRIER (2) and MUT_NO_RECORD_FRESHNESS (4) are P3.

   These are tested reconstruction results, not HMBC exploits.
5. **Never-publish:** my own substring scan of the 393 published files plus my 3 review files (396)
   looked for the 13 distinct TEST-ONLY keys: the label keys, including H1-H4 root and ca-admin, and
   every frozen-vector `signerPrivateKey`. It found 0 hits. The 9 `signed-list.json` files are the
   evaluator's validated artifacts and contain no key. No raw producer file or private adapter state
   is present.
6. **What the review does not cover:**
   - witness/adapter behaviour, the A31 count and the worker probes (agent 2 (proxy), S2-0018);
   - the runner and oracle internals.

## Command

```
.venv/bin/python -I ledger/tools/review_barrier_stress_evidence.py evaluation/evidence/e2/sl6-barrier-live-20261011/run > ledger/evidence/sl6-barrier-review/review.json
```

Exit 0; 9/9 rows pass.

Impact: the SL6 ledger side is accepted. Catalog: 50/56 actual, 6 remaining (SL7). Gate E stays
NOT_RUN; F and G stay locked.
Action requested: none for SL6. agent-3 (proxy): the SL7 FREEZE (S3-0019) is in progress.
