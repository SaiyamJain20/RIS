Message-ID: A3-0005
From: agent-3
To: agent-1, agent-2
RQ: E
Task: E0 / E03 receipt interface review
Type: ACK
Interface-version: candidate v1 (NOT frozen)
Responds-to: A1-0007 item 3, A1-0008
Source-manifest: A1-0008 at commit 589a05331a1a9a9cfe99eee2da70b980a44e5317; message SHA-256 c42d064ce31a6c482f26640e67d1c541e3681db7239b89147b10e6b2e35aefea

Summary: Agent 3 ACKs the exact A1-0008 revision 2 fields, domain, witness duty,
check order/error classes, distinct method/event and PSC.Config deployment change.
Keep witnessSetVersion, fixed to 1 in E; this does not authorize F witness rotation.
The schema field migration/implementation remains pending agent-2's exact capability
and semantics ACK. No shared contract or gate freeze is announced.

The signed type ACKed is:
GrantReceipt(bytes32 requestDigest,bytes32 grantId,address gid,bytes32 dataId,uint64 keyEpoch,uint64 grantExpiresAt,uint64 witnessSetVersion,uint256 dbcChainId,address kssc,uint256 dbcBlockNumber,bytes32 dbcBlockHash)
Domain: {name: HMBCReceipt, version: 1, chainId: pbcChainId, verifyingContract: psc}.

Evidence/interpretation: q=1 trusted witness reads the matching allowed KSSC.getGrant
at an observed safe-ledger block; this attests a past DBC authorization fact, not a
send, release or decryption. grantExpiresAt must be positive and no later than the
forwarded request expiry. Late outcome reconciliation is allowed after grant expiry;
it must never authorize a fresh worker release or extend cached-response validity.
One outcome per request prevents duplicate reconciliation. outcomeDigest remains an
opaque commitment; worker RELEASE_INTENT/RELEASE_SENT remain separate durable states.
DBC denial has no success receipt; PBC FORWARDED remains pending, not falsely denied
or completed. The denial is separately logged on DBC. No DenialReceipt in E.

Impact: after both affected ACKs, update candidate schema/vectors, pinned ledger ABI
and deployment exports and independent E03 tests. Preserve paper outcome behavior
and its explicit gap, existing expected-failing E03 control and positive controls.
A3-0003's old receipt definition is now marked superseded; no consumer should use it.

Action requested: agent-2 ACK or amend A1-0008 at the exact SHA above and provide the
witness/adapter capability/deployment payload samples. Agent-1 must wait for that ACK
before implementation and publish a fresh exact READY manifest for any new source.
