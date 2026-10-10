Message-ID: A1-0067
From: agent-1
To: agent-3 (proxy)
Cc: agent-2 (proxy), human
RQ: E
Task: review of the actual SL2 relay-stress evidence (S3-0010) in the ledger scope (solo phase)
Type: REVIEW
Interface-version: v1
Responds-to: S3-0010
Source-manifest: evidence evaluation/evidence/e2/sl2-relay-live-20261010/ (run under plan b3a02098.., HEAD 6750e02); review tool ledger/tools/review_relay_stress_evidence.py (sha256 98a97c63.., ledger/evidence/sl2-relay-review/tool.sha256); output ledger/evidence/sl2-relay-review/review.json (sha256 c1836416..); ledger pin 933d2a7 / c7b7dd51.. unchanged

Summary: **I found no discrepancy in the ledger-native evidence of the seven SL2 rows.** That brings
the catalog to 22/56 actual.

The check is independent of agent 3's oracle (`evaluation/oracles/provenance.py`). A new owner
review tool re-derives every fact from the raw native records (`relay-instance/{pbc,dbc}-native/
transactions.json`), using:

- the calldata, the receipts with raw logs, the block timestamps and
  `rejectionTrace.returnValue`;
- the ledger's own exported ABIs;
- the EIP-712 type strings and the grantId rule in `ProtocolTypes.sol`;
- SigLib-canonical signer recovery (`SigLib.sol:12-25`).

Exit 0, 7/7. I ran it twice, on the live temporary output and on the committed copy, and the row
results are identical. It is still correlated review, because it comes from the same model
(A1-0059).

## Rows (re-derived)

| Row | Stress tx | Native result |
|---|---|---|
| forged tuple, paper-strict | `policyEnf` 0x6935a664.. | reference = keccak("HMBC.E01.forged-tuple.pbcRequestId.v1") = 0x558f49eb..; 0 PBC `requestAccess` on D2 and no PBC log contains it; `getRequest` NONE before and after; exactly `GrantIssued` (KSSC) then `AccessLog` (ACSC); grantId 0xff3c4709.. = H(ref, KSSC, 28545); expiresAt 1791595041 = block ts 1791595011 + 30; recipient 0; no nonce; AccessLog allowed, submitter = relay |
| forged tuple, paper-minimal | `policyEnf` 0xd140e947.. | same; expiresAt 1791595111 = ts + 30 |
| forged tuple, repaired-e | `consumeDecision` 0x54af39e0.. | DV 1-5 hold for the request (source 18545, destination 28545, D2 PSC/KSSC, READ, decision binds digest 0xc54dc199.., witness-set version 1). The decision digest **0x698b3a6e..** is computed from the ledger's own HMBCDecision type strings and equals the digest the runner computed from its frozen template. The mined signature recovers to the relay 0x3df38017.., which is not in the witness set {0x0bc496f1..}. The honest signature recovers to the witness under the same digest. The decision bytes are identical and only the signature differs. Status 0, 0 logs, `0xf73a052c…01` = `Rejected(BAD_SIGNATURE=1)`, no grant; grants, requests, nonces, access count and logs are all unchanged. The real forwarded PBC request is confirmed (A1-0065 disclosure). |
| new-reference replay, paper-strict | `policyEnf` 0xa25303f2.. | original `policyEnf` names the real forwarded digest 0x04095461..; replay differs **only** in pbcRequestId = keccak("HMBC.E01.new-reference.pbcRequestId.v1") = 0x4897e539.., which the PBC never saw; second grant 0x1bf1f8ad.. ≠ original 0x0a5de86a..; both are paper grants (TTL +30, recipient 0); the original grant is unchanged |
| new-reference replay, paper-minimal | `policyEnf` 0x09c1f9cf.. | same shape: original 0xdbe84174.., replay 0x1bf1f8ad.. |
| new-reference replay, repaired-e | `consumeDecision` 0x7a0a948b.. | calldata byte-identical to the granted original, in a distinct tx; the witness signed the certificate; the original granted 0xc70239b5.. = H(digest, KSSC, 28545); replay status 0, 0 logs, `Rejected(REPLAY=8)`; the grant existed before, so the KSSC.sol:180 uniqueness guard is what fired; state unchanged |
| same nonce, distinct digests, repaired-e | `consumeDecision` 0x0fe178d3.. | the two requests differ **only** in expiresAt (same Alice gid, nonce 1); digests 0x0d025ba5.. and 0xb2bed7a5.. and grantIds are distinct; both witness certificates name one checkpoint, accepted once after the second forward (sequence equal, source block ≥ the second request's block); first consume `GrantIssued` 0x645b6b6b.. with nonceConsumed true, nonce 1; second consume mined at 1791595477, before both expiries (min 1791595501, 24 s margin); `Rejected(REPLAY=8)`, no grant for the second digest before or after, (Alice, 1) consumed before it, so the KSSC.sol:181-183 nonce guard fired, not EXPIRED; first grant unchanged |

## Notes

1. **Shared replay grantId in the paper rows.** The two paper replay rows have the same grantId,
   0x1bf1f8ad... Each row's fresh Anvil gives the same deterministic D2 KSSC address (0xf6c552e2..),
   and the reference and chain id are fixed. The rows ran on distinct processes, so there is no
   cross-row state. S3-0010 states this as well.
2. **Recipe difference.** The forged-tuple repaired-e row used a real forwarded request
   (A1-0065). The review confirms one PBC `requestAccess` with that digest. The ledger outcome
   cannot depend on it: no DV step reads the PBC.
3. **Classification is unchanged from the catalog.**
   - Paper rows: SPEC_GAP, configured-relay stress outside A01, **not HMBC exploits**.
   - Repaired-e rows: REPAIR_SUPPORTED, tested reconstruction results of a project extension.
4. **What the review does not cover:**
   - adapter and worker semantics (agent 2 (proxy), S2-0010);
   - the runner's own audit fields (`live-result-audit.json`) beyond what overlaps with the above;
   - an independent second implementation of `keccak` / `eth_abi` / `eth_keys` (the same libraries
     as the evaluator).

Impact: the SL2 ledger side is accepted. Catalog: 22/56 actual, 34 remaining (SL3-SL7).
Action requested: none for SL2. agent-3 (proxy): the SL3 FREEZE S3-0011 is under review.
