# Correlated author review and exact peer source review

No extra reviewer/agent was launched: the user's three-persistent-agent rule
overrides the review skill's subagent workflow. This is correlated author review.

## Owned checker

The separate API verifies one configured owner's real EIP-712 signature under
reconstructed deployment context. It checks every supplied required block and
public getter by exact chain/hash/contract/calldata; the existing ABI codec
rejects trailing/noncanonical results. q2 remains explicitly selected by context;
one stored signature is never called a certificate. Same source/head reads share
one capture. An older source with unchanged epochs is a positive control, while
changed head epochs refuse. No invented numeric lag is introduced.

Exact next sequence accepts uint64 max from max-1 and refuses any representable
successor after saturation. The current checkpoint's source-number floor and
same-height source/head hash comparison are explicit. keyEpoch=0 is already a
schema constraint; the local guard is redundant. Expiry uses the public KSSC
maxCheckpointTtl at the supplied DBC observation, with strict lower and inclusive
upper bounds. It does not assert that this was the latest observation at signing.

Seven deliberately disabled gates each preserve a valid control and are caught
by the intended refusal test; detection requires pytest's DID NOT RAISE outcome,
not an unrelated exception. No on-disk production mutation is performed.

The first44 RED failures are all the absent module. The next20FAIL/24PASS expose
the author's wrong schema name (BlockObservation instead of EvidenceObservation)
and one test's missing ValidationError allowance. Both are corrected without
weakening the predicate. The original44 then pass, and seven more context checks
are included in the frozen51-test scope. Logs retain the failed trials.

Limits: no RPC authenticity, cross-height ancestry, actual sign-time attestation,
history/row/marker completeness, native state acquisition or fault/clear coverage.
Other signed types are not covered. Existing consumers, shared schema, acceptance
and source READYs remain untouched. No finding about the paper itself follows.

## Agent2 partial source67111f5

Exact commit67111f580b6ecfd1b924f3cd1a863981180822e1, eleven changed paths since
7915d532ff17c9e782bd23d4887374c01601154f. Complete source and file-changing
provenance are in inputs-before.json; owner-delta.patch.gz retains the source and
runtime-mailbox delta. No new READY or outbox ACK is present in this delta.

The witness entry point exists: a TEST-ONLY synthetic key checked against the
declared index, D50 witness-store startup and four service dispatches over JSON
lines. Forty-eight no-node owner tests were independently rerun with the
no_services fixture guard. The live test file was excluded. Owner142combined
tests,30mutants and live process/restart/governance results are static-reviewed
claims only; none is independently rerun or adopted. No pool ProcessTransport or
CLI witness-operation wiring exists in this publication.

**Open robustness finding, extending A3-0096:** witness_main.py:149 calls int on
deployment chainId before canonical type/width validation; its exception tuple
does not include OverflowError. For either PBC or DBC chainId as JSON number
1e999, the CLI exits1 with an OverflowError traceback, no stdout and no created
state. Expected local startup behavior is the documented closed JSON refusal,
exit2. This is corrupt local operator configuration; no remote control, leaked
key, wrong authorization or successful malformed startup is shown. Agent2 owns
the fix; apply canonical chainId validation at both entry points and test both
chain slots. The earlier adapter schema[]/null request remains open at this pin.

The allow-list parser accepts empty object and empty string as an empty list;
null cleanly refuses MALFORMED. These are permissive shape observations only:
empty approval grants nothing. No governance bypass or new HIGH claim follows.

The new partial source remains outside A2-0063/64's isolated READY manifests.
Complete runtime READY/mapping and separate exact execution FREEZE ACKs still
precede integrated services. Historical E changes remain exactly worker.py,
worker_log.py and testtools/deviating_witness.py; this run does not prove E parity.
