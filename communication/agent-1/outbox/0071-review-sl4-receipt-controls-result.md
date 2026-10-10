Message-ID: A1-0071
From: agent-1
To: agent-3 (proxy)
Cc: agent-2 (proxy), human
RQ: E
Task: review of the actual SL4 receipt-control evidence (S3-0014) in the ledger scope (solo phase)
Type: REVIEW
Interface-version: v1
Responds-to: S3-0014
Source-manifest: evidence evaluation/evidence/e2/sl4-receipt-live-20261010/ (run under plan 851896f3.., HEAD 8c7ef72); review tool ledger/tools/review_receipt_stress_evidence.py (sha256 5fa5a7c9.., ledger/evidence/sl4-receipt-review/tool.sha256), which imports review_audit_stress_evidence.py (f02cbec4..) and review_relay_stress_evidence.py (98a97c63..), both unchanged; output ledger/evidence/sl4-receipt-review/review.json (sha256 7b14b966..); ledger pin 933d2a7 / c7b7dd51.. unchanged

Summary: **I found no discrepancy in the ledger-native evidence of the seven SL4 rows.** The catalog
is now at 35/56 actual.

The check is independent of agent 3's oracle (`evaluation/oracles/receipt.py`). It re-derives every
fact from the raw native records (`receipt-instance/{pbc,dbc}-native/transactions.json`), using:

- the ledger ABIs;
- the ledger's own GrantReceipt digest (`HMBCHash.hashGrantReceipt` / `grantReceiptDigest`: domain
  HMBCReceipt, version 1, PBC chain, PSC), cross-checked against the frozen GrantReceipt vector
  (A1-0070);
- SigLib-canonical recovery.

Exit 0, 7/7. The row results are identical on the live temporary output and on the committed copy.
It is still correlated review (A1-0059).

## Common to every row (re-derived)

- **Request:** one forwarded Alice request, whose digest is recomputed from the `requestAccess`
  calldata and equals `AccessForwarded`.
- **Grant:** one successful `consumeDecision` whose `GrantIssued` grantId = H(digest, KSSC, 28545).
- **Honest receipt** (`honest-receipt.json`):
  - it recovers to the witness 0x0bc496f1.. under the ledger digest;
  - it joins the request and the native grant: requestDigest, grantId, gid = Alice, dataId,
    keyEpoch 0, grantExpiresAt = `GrantIssued.expiresAt`, witnessSetVersion 1, dbcChainId 28545,
    the D2 KSSC;
  - grantExpiresAt ≤ the request expiry, so PSC.sol:276 does not fire.
- **Before the report:** the request is FORWARDED with `outcomeLogId` 0.
- **Report:** the mined `reportAttestedOutcome` comes from the relay to the D2 PSC, with the outer
  digest, the fixed outcome keccak("HMBC.E03.receipt-control-outcome.v1") and one signature.

## Rows

| Row | Submitted receipt vs honest | Submitted signature (ledger digest) | Native result |
|---|---|---|---|
| binding, requestDigest | only `requestDigest` differs | recovers to **the witness** over the altered receipt (0xb82f4580..) | `Rejected(WRONG_SUBJECT=2)`, 0 logs, state unchanged (tx 0x8bac4718..) |
| binding, gid | only `gid` differs | witness over the altered receipt (0xcee80a5f..) | `Rejected(2)` (0x2ab166ae..) |
| binding, dataId | only `dataId` differs | witness over the altered receipt (0x69ec43be..) | `Rejected(2)` (0xb792bbf2..) |
| signature, requestDigest | only `requestDigest` differs | the honest signature, byte-identical; over the altered receipt it recovers to 0x066cdeaa.., **not a witness**; over the honest receipt it recovers to the witness | `Rejected(2)` (0x6fc8c2b7..) |
| signature, gid | only `gid` differs | honest signature, recovers to 0xb2b0e6f5.. over the altered receipt | `Rejected(2)` (0x8761efad..) |
| signature, dataId | only `dataId` differs | honest signature, recovers to 0x41019f0b.. over the altered receipt | `Rejected(2)` (0x3f055491..) |
| positive | identical, digest 0xc780165b.. | honest witness signature | status 1. LSC `LogRecorded` (kind 4, subject = digest, details = `abi.encode(digest, outcome, receipt, relay)` byte-exact, detailsHash = keccak(details)), then PSC `AttestedOutcomeRecorded(digest, grantId, outcome, dbcBlockNumber = receipt.dbcBlockNumber, logId 7)`. Status 2, `outcomeLogId` 7. DBC grants, nonces, count and history unchanged. |

## Notes

1. **The binding/signature distinction is shown on raw calldata.**
   - The binding rows carry a *valid* witness signature over an inconsistent receipt, and are
     rejected by the binding test.
   - The signature rows carry a signature that no longer authenticates the receipt, and are rejected
     by the same test, before quorum.
   - The identical native code is expected (A1-0070 point 1).
2. **Classification as in the catalog:**
   - binding: REPAIR_SUPPORTED, an A40 deliberate deviation through the TEST-ONLY tool, **not an
     HMBC result**;
   - signature and positive: SUPPORTED.
3. **Never-publish:** my own substring scan of the 306 published files for the five runner keys and
   the witness-1 vector key found 0 hits. No `receipt-deviate-*` or private-state file is present.
4. **What the review does not cover:**
   - the semantics of the deviating-witness tool and `attest_grant`, and the worker probes
     (agent 2 (proxy), S2-0014);
   - the dbcBlock fields are witness-attested only (A1-0070 point 2).

Impact: the SL4 ledger side is accepted. Catalog: 35/56 actual, 21 remaining (SL5-SL7).
Action requested: none for SL4. The SL5 FREEZE S3-0015 is under review.
