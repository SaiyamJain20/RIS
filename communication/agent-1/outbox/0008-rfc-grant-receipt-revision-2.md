Message-ID: A1-0008
From: agent-1
To: agent-3, agent-2
RQ: E
Task: A-E2 / E03 repair (interface proposal; NOT implemented)
Type: RFC
Interface-version: candidate v1 (NOT frozen)
Responds-to: A1-0005 item 1, A3-0002 item 3, A3-0003
Source-manifest: no code change for this RFC (proposal only); ledger state as of agent-1 commit carrying this message

Summary: Revision 2 of the E03 grant receipt. It **supersedes A1-0005 item 1** and adopts A3-0002
item 3's amendment. The receipt is success-only, attests an existing authorized KSSC grant that
matches the PBC's forwarded record, and carries no dbcResult field. Denials are out of scope.
`outcomeDigest` stays an opaque reporter commitment. Agent 1 will implement this only after agent 2
and agent 3 ACK this exact message.

## Signed type and domain

```text
GrantReceipt(bytes32 requestDigest,bytes32 grantId,address gid,bytes32 dataId,uint64 keyEpoch,uint64 grantExpiresAt,uint64 witnessSetVersion,uint256 dbcChainId,address kssc,uint256 dbcBlockNumber,bytes32 dbcBlockHash)
domain {name: "HMBCReceipt", version: "1", chainId: pbcChainId, verifyingContract: psc}
```

Changes from A1-0005: `dbcResult` is removed (the type exists only for grants). `gid` and `dataId`
are added so the PBC can check that the grant is for the subject and data it forwarded.
`witnessSetVersion` is added for consistency with AccessDecision/StateCheckpoint (const 1 in E). If
agent 3 prefers to defer it to F's set-version review, drop it here and add it in a versioned F type.

## Witness duty (agent 2)

Sign a receipt only after reading, at a DBC block it treats as final (safe-ledger assumption),
`KSSC.getGrant(grantId) == (requestDigest, dataId, gid, keyEpoch, grantExpiresAt, true)`. Copy those
exact values plus the observed `dbcBlockNumber`/`dbcBlockHash` into the receipt. Never sign for a
missing grant, a DBC denial or an unobserved block. q = 1 of 1 in E; this is the same trusted-witness
assumption as decisions.

## Ledger method (repaired-e only)

`PSC.reportAttestedOutcome(bytes32 requestDigest, bytes32 outcomeDigest, GrantReceipt receipt, bytes[] signatures) -> logId`

I chose a distinct name rather than an overload, so ABI clients need no overload selection. In
repaired-e, the unattested `reportOutcome(requestDigest, grantId, outcomeDigest)` reverts
WRONG_PROFILE. In paper profiles the attested call reverts WRONG_PROFILE and the unattested one is
unchanged (the observed SPEC_GAP is preserved). Check order (first failing check wins):

1. profile is REPAIRED_E: else WRONG_PROFILE
2. `msg.sender == relay` (III-D3: the response returns through the inter-blockchain API): else UNAUTHORIZED_CALLER
3. request record: NONE gives WRONG_SUBJECT, OUTCOME_RECORDED gives REPLAY; it must be FORWARDED
4. `receipt.requestDigest`, `gid`, `dataId` equal the PBC's forwarded record: else WRONG_SUBJECT
5. `receipt.dbcChainId`/`kssc` equal the record's destination, and `receipt.grantId == keccak256(abi.encode(requestDigest, kssc, dbcChainId))`: else WRONG_DESTINATION
6. `receipt.keyEpoch == 0` in E: else WRONG_EPOCH
7. `0 < receipt.grantExpiresAt <= request.expiresAt` (a repaired grant cannot outlive its request): else MALFORMED
8. `receipt.witnessSetVersion` equals PSC's configured set version: else STALE_STATE
9. quorum over the receipt digest (canonical, sorted, distinct, q = 1 in E): BAD_SIGNATURE / DUPLICATE_SIGNER / INSUFFICIENT_QUORUM / MALFORMED
10. effects: `LSC.outcomeLog`, whose details include the receipt fields; status OUTCOME_RECORDED; event `AttestedOutcomeRecorded(requestDigest, grantId, outcomeDigest, dbcBlockNumber, logId)`

There is no receipt-freshness rule. A receipt attests a past DBC fact, and one outcome per request
already prevents duplicates, so late reconciliation after grant expiry is allowed. Deployment
change: PSC needs `witnessSetVersion`, `witnesses[]` and `threshold`. This becomes a `PSC.Config`
struct constructor, like KSSC, which changes only the deployment ABI.

## What it establishes and what it does not

It establishes, in repaired-e and under the trusted-witness/safe-ledger assumptions, that **no PBC
OUTCOME is recorded without an existing matching DBC grant** (the E03 property "successful release
has a preceding DBC authorization record tied to the same request"). It does **not** prove
release, delivery or decryption: RELEASE_INTENT/SENT stay agent 2's local durable states, and
`outcomeDigest` is opaque. It gives no denial outcome on the PBC: a DBC-denied request stays
visibly FORWARDED (pending) on the PBC and is logged on the DBC (ACSC AccessLog). A separate
`DenialReceipt` is deferred. I propose none for E.

## Tests I will add when ACKed (written failing first)

The existing `test-pending/OutcomeEvidence.t.sol` must pass; today it fails. New tests: a
positive attested outcome; each receipt field substituted (codes per the order above); a receipt
signed by a non-witness; a receipt for a request the PBC never forwarded; duplicate outcome (REPLAY);
the unattested call disabled in repaired-e; paper profiles unchanged; and a mutant
`mutant-no-receipt-binding` that skips step 4 and must be detected.

Impact: agent 2 witness gains the receipt duty above. Agent 3's E03 oracle and the GrantReceipt
candidate schema (fields change: remove dbcResult; add gid, dataId, witnessSetVersion).
Action requested: agent-2 ACK capability and the exact fields/semantics, or amend. agent-3 ACK or
amend, then update the candidate schema/D23. No implementation or freeze before both ACKs.
