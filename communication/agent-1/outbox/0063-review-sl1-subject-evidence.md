Message-ID: A1-0063
From: agent-1
To: agent-3 (proxy)
Cc: agent-2 (proxy), human
RQ: E
Task: review of the actual SL1 subject-substitution evidence (S3-0006) in the ledger scope (solo phase)
Type: REVIEW
Interface-version: v1
Responds-to: S3-0006
Source-manifest: evidence evaluation/evidence/e2/sl1-subject-live-20261010/ (run under plan 6fd5809b.., HEAD 77a7c1f); review tool ledger/tools/review_subject_evidence.py (sha256 in ledger/evidence/sl1-subject-review/tool.sha256); output ledger/evidence/sl1-subject-review/review.json; ledger pin 933d2a7 / c7b7dd51.. unchanged

Summary: **I found no discrepancy in the ledger-native evidence of the three rows.** The check is independent of agent 3's oracle: a new owner review tool decodes the raw substituted calldata with the ledger's own exported ABIs and re-derives each fact from it (exit 0, 3/3). It is still correlated review, because it comes from the same model (A1-0059).

| Row | Call | What changed in the calldata | Native result (re-derived) |
|---|---|---|---|
| paper-strict | `policyEnf` tx 0x792571bf.. | fwd.gid Alice 0xc4ff..956d → Bob 0xac5a..e59a | one `GrantIssued`: gid = Bob, recipientKeyHash 0, nonceConsumed false, expiresAt 1791575136 = block ts 1791575106 + 30 |
| paper-minimal | `policyEnf` tx 0xc21b9e44.. | same | same as paper-strict, with expiresAt 1791575217 = block ts + 30 |
| repaired-e | `consumeDecision` tx 0x3575b671.. | **only** `gid` differs from the signed original request; the certificate's `requestDigest` equals the original prepared digest | status 0x0, 0 logs, `rejectionTrace.returnValue` = `0xf73a052c…02` = `Rejected(WRONG_SUBJECT=2)` |

Further detail on the paper rows:

- Each paper row has exactly one `AccessLog`, with allowed=true and gid Bob.
- The logged grantId equals my recomputation of `keccak256(abi.encode(pbcRequestId, KSSC, 28545))` (ProtocolTypes.sol:447). The id is independent of gid, so it is the original derived id.
- The DBC logs that existed before the call are unchanged.
- Alice's PSC request stays FORWARDED (1), and the nonces of both subjects are unchanged.

Further detail on repaired-e:

- grant, request, both nonces, access count and the logs are each equal before and after.
- No grant exists, and Alice's request stays FORWARDED (1).
- The other two reverts in the evidence (code 16) are the wrong-admin controls on D1 and D2.

**Stated limit of this review:** the evidence stores DBC logs already decoded by agent 3's decoder. I re-derived every value I checked from the raw calldata and the transaction's block timestamp, but I did not re-decode raw log topics.

Classification (agent 3's) is consistent with the ledger facts:

- paper SPEC_GAP: the grant was issued to a gid the relay asserted, under compromised-relay stress outside A01;
- repaired-e REPAIR_SUPPORTED: DV step 4, request binding.

Exclusions:

- worker routing, decryption and completion (agent 2 (proxy));
- the oracle, audit and timing interpretation;
- raw outputs outside the repository.

Impact: none on any pin. No ledger defect. SL1 counts toward 15/56 actual.
Action requested: none.
