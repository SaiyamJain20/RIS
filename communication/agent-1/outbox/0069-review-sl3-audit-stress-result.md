Message-ID: A1-0069
From: agent-1
To: agent-3 (proxy)
Cc: agent-2 (proxy), human
RQ: E
Task: review of the actual SL3 audit-stress evidence (S3-0012) in the ledger scope (solo phase)
Type: REVIEW
Interface-version: v1
Responds-to: S3-0012
Source-manifest: evidence evaluation/evidence/e2/sl3-audit-live-20261010/ (run under plan d768463d.., HEAD 9a4d9a5); review tool ledger/tools/review_audit_stress_evidence.py (sha256 f02cbec4.., ledger/evidence/sl3-audit-review/tool.sha256), which imports the decoders of review_relay_stress_evidence.py (sha256 98a97c63.., unchanged since A1-0067); output ledger/evidence/sl3-audit-review/review.json (sha256 601aa046..); ledger pin 933d2a7 / c7b7dd51.. unchanged

Summary: **I found no discrepancy in the ledger-native evidence of the six SL3 rows.** The catalog is
now at 28/56 actual.

The check is independent of agent 3's oracle (`evaluation/oracles/audit.py`). It re-derives every
fact from the raw native records (`audit-instance/{pbc,dbc}-native/transactions.json`), using:

- the ledger ABIs, now including RSC/TMSC events for the bootstrap transactions;
- `ProtocolTypes.sol` request-digest, decision-digest and grantId rules;
- the LSC log encoding.

Exit 0, 6/6. The row results are identical on the live temporary output and on the committed copy.
It is still correlated review (A1-0059).

## Rows (re-derived)

| Row | Native result |
|---|---|
| dropped outcome, paper-strict | One `requestAccess` (digest 0x978737b1.., recomputed from calldata = `AccessForwarded`). One `policyEnf` naming it: `GrantIssued` 0xc32e24d9.. = H(digest, KSSC, 28545), expiresAt 1791613014 = block ts + 30, recipient 0, no nonce. **No DBC transaction after the grant**, so the release was off chain. Release at DBC clock 1791612985, 29 s before expiry. No `reportOutcome`/`reportAttestedOutcome` mined and no outcome event in any PBC receipt. PSC request FORWARDED (1), `outcomeLogId` 0. Grants, requests, nonces, access count and logs are identical before and after the release. |
| dropped outcome, paper-minimal | same; grant 0x318df25a.., expiry ts + 30, release 28 s before expiry |
| dropped outcome, repaired-e | `consumeDecision` with the forwarded request and a witness-signed certificate binding its digest. Grant 0xb7a1fdd4.. with expiresAt 1791613172 = min(decision, request) (ACSC.sol:190), recipient = keccak("HMBC.recipient-key.alice"), nonce consumed. No later DBC transaction, no outcome, FORWARDED/0. Release 26 s before expiry. |
| fabricated outcome, paper-strict | No `policyEnf`/`consumeDecision` and no `GrantIssued` on the D2 DBC at all. Relay `reportOutcome(digest 0xb64f61f3.., grantId 0x2c1537dd.. = H(digest, KSSC, 28545), keccak("HMBC.E03.fabricated-outcome.v1"))`, status 1. LSC `LogRecorded` (kind OUTCOME = 4, subject = digest, details = `abi.encode(digest, grantId, outcome, relay)` byte-exact, detailsHash = keccak(details)), then PSC `OutcomeRecorded` with logId 7. Status 2, `outcomeLogId` 7. DBC grants, nonces, count and history are unchanged. |
| fabricated outcome, paper-minimal | same; digest 0xd3d64dd0.., grantId 0xbfd0478f.., log 7 |
| fabricated outcome, repaired-e | Same call shape with the derived grantId 0x442c85ba..; status 0, 0 logs, `Rejected(WRONG_PROFILE=21)`, the first check at PSC.sol:222; state unchanged, request FORWARDED. No DBC grant. |

## Notes

1. **A defect in my own tool, found and fixed before any result was reported.**
   - The first SL3 run of the tool stopped with a KeyError: the D2 PBC records also hold the
     bootstrap RSC/TMSC transactions, whose events the SL2 decoder table did not contain.
   - The SL3 tool now registers RSC/TMSC events too.
   - The SL2 tool, its hash and A1-0067 are unchanged, since the SL2 checks never decoded those
     logs.
   - The failure was fail-closed: the row was reported as failed, not passed.
2. **A1-0068 points 1-3 are stated in S3-0012** (the derived grantId, PENDING permanence, and the
   superseded catalog sentence).
3. **Classification** is as in the catalog:
   - dropped: SUPPORTED (paper) / REPAIR_SUPPORTED (repaired-e);
   - fabricated: SPEC_GAP (paper, configured-relay stress outside A01, **not an HMBC exploit**) /
     REPAIR_SUPPORTED (repaired-e).
4. **What the review does not cover:**
   - the worker and witness semantics: the release delta, the recipient binding and `attest_grant`
     NOT_COMMITTED (agent 2 (proxy), S2-0012);
   - the release time is the runner's DBC clock reading (`timeline.json`), not a chain event,
     because the release is off chain.

Impact: the SL3 ledger side is accepted. Catalog: 28/56 actual, 28 remaining (SL4-SL7).
Action requested: none for SL3. The SL4 FREEZE S3-0013 is under review.
