Message-ID: A1-0077
From: agent-1
To: agent-3 (proxy)
Cc: agent-2 (proxy), human
RQ: E
Task: review of the actual SL7 wrong-destination and expiry-boundary evidence (S3-0020) in the ledger scope; catalog complete (solo phase)
Type: REVIEW
Interface-version: v1
Responds-to: S3-0020
Source-manifest: evidence evaluation/evidence/e2/sl7-destination-live-20261011/ (run under plan d4fa294e.., HEAD f1c1e52); S3-0020 sha256 98f714b1..; review tool ledger/tools/review_destination_stress_evidence.py (sha256 9e788ce9.., committed in f1c1e52 **before** the run; ledger/evidence/sl7-destination-review/tool.sha256), which imports review_barrier_stress_evidence.py (9edc3eb2..) and, through it, the SL5/SL3/SL2 tools, all unchanged; output ledger/evidence/sl7-destination-review/review.json (sha256 3ec78ed0..); ledger pin 933d2a7 / c7b7dd51.. unchanged

Summary: **I found no discrepancy in the ledger-native evidence of the six SL7 rows. The catalog is
complete: 56/56 comparisons have actual runs.**

The check is independent of agent 3's oracle (`evaluation/oracles/destination.py`). It re-derives
every fact from the raw native records of:

- the receiving deployment A (`destination-instance/`);
- the source deployment B (`source-instance/`).

It uses the ledger ABIs and digests. DecisionVerifier steps 1-2 and 9 are replayed in Python on the
mined calldata, against A's deployment.

Exit 0, 6/6. **The tool was committed before the run, and no fix was needed.** The row results are
identical on the live temporary output (reviewed ~19:29 IST) and on the committed copy. It is still
correlated review (A1-0059).

## Rows

| Row | Re-derived from the raw records | Native result |
|---|---|---|
| wrong destination, paper-strict / paper-minimal | B shares A's chain pair but has another PSC/KSSC/ACSC (B PSC 0xbc8a9d0d.., A PSC 0xd5eeb095..). B mined one relay `requestAccess` on B's PSC; its digest, recomputed, equals `AccessForwarded`, and the request binds B's PBC/PSC and DBC/KSSC. A's PBC has no request with that digest. B's DBC has no `consumeDecision`/`policyEnf`. A's `policyEnf` carries pbcRequestId = B's digest and exactly B's forwarded records. | Grant at A (0xc538a0da.. / 0xcad47c07..): grantId = H(B digest, A KSSC, DBC chain), expiresAt = block + 30, recipient 0, no nonce. |
| wrong destination, repaired-e | Same B/A facts (B KSSC 0xe51ef867.., A KSSC 0x0c3ced2b..). A received B's request field-for-field (**no signed field rewritten**) with B's records. The certificate is an honest ALLOW that recovers to the witness under **B's** HMBCDecision/KSSC domain, and not to the witness under A's. **The replayed verifier first fails at step 1** (r.psc = B's PSC). Step 2 also mismatches. | `Rejected(WRONG_DESTINATION=3)`, no logs (0xffa505f6..). |
| expiry boundary, paper-strict / paper-minimal | One Alice request on A. **The consume block timestamp equals r.expiresAt exactly** (1791726931 / 1791727014), and every earlier DBC transaction is below it. `policyEnf` carries the forwarded tuple and records. | Grant, expiresAt = r.expiresAt + 30 (1791726961 / 1791727044). |
| expiry boundary, repaired-e | Consume block time = r.expiresAt = 1791727102. The decision is witness-signed under A's domain, with d.expiresAt = 1791727102 and stateSequence equal to the current, witness-signed checkpoint, whose expiry is 1791727133. **The replayed verifier first fails at step 9** (equality, `>=`). | `Rejected(EXPIRED=7)`, no logs (0x1f29861e..). |

## Notes

1. **The cause attribution is checked on calldata.**
   - Wrong destination: the replay names step 1 (source binding), not step 2. The signature fact
     confirms what A1-0076 point 1 said: the witness signed for B, and that signature is never
     evaluated at A.
   - Expiry boundary: the replay names step 9, and the mined timestamps show the equality directly.
2. **This catalog row cannot detect MUT_NO_DESTINATION_BINDING (1)**, as stated before the run. How
   it is detected is decided in A1-0078 D-P3-2: the ledger unit suite kill, the ProVerif mutant, and a
   live code-separation row. No live accept-vs-reject kill is claimed.
3. **Paper wrong destination:** A grants on a pbcRequestId that A's PBC never saw. This is a chosen
   completion under compromised-relay stress, outside A01: a SPEC_GAP, not an HMBC exploit (A1-0076
   point 2).
4. **Expiry boundary:**
   - The repaired rejection at the exact instant follows from `>=` and matches every other ledger
     validity check (A1-0076 point 3).
   - Acceptance at `expiresAt − 1` was not run in SL7. That optional `eth_call` was skipped.
   - The paper grants at that same instant show that paper `policyEnf` never sees the request expiry.
5. **B's funding:** after the 1000 ETH reset, B's deployment used about 400 ETH (599.99 ETH left, per
   S3-0020). That is within the A1-0039 budget. I did not independently re-read the balances; they
   are in the run manifest.
6. **Never-publish:** my own substring scan of the 285 published files plus my 3 review files (288)
   looked for the 13 distinct TEST-ONLY keys. It found 0 hits, including in `source-instance/`. No
   private adapter state is present for A or B.
7. **What the review does not cover:**
   - B's adapter, witness timing and the A31 count (agent 2 (proxy), S2-0020);
   - the runner and oracle internals.

## Catalog total (actual, solo phase and earlier)

| Slice | Rows |
|---|---|
| recovery and expiry ×6, duplicate ×3, identical replay ×3 (pre-solo); subject ×3 (SL1) | 15 |
| SL2 relay stress | 7 |
| SL3 audit stress | 6 |
| SL4 receipt controls | 7 |
| SL5 trust freshness | 6 |
| SL6 barrier and expired duty | 9 |
| SL7 wrong destination and expiry boundary | 6 |
| **Total** | **56** |

Each slice was independently reviewed by agent 1 with an owner tool. For SL6 and SL7, the tool was
committed before the run.

## Command

```
.venv/bin/python -I ledger/tools/review_destination_stress_evidence.py evaluation/evidence/e2/sl7-destination-live-20261011/run > ledger/evidence/sl7-destination-review/review.json
```

Exit 0; 6/6 rows pass.

Impact: the SL7 ledger side is accepted. **Catalog 56/56 actual.** Gate E stays NOT_RUN until P3
(A1-0078) and P4 are done; F and G stay locked.
Action requested: agent-3 (proxy) start P3 under A1-0078 (the P3-mutants FREEZE first).
