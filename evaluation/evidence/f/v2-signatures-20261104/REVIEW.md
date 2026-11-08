# Correlated author review

Reviewed the new helper/tests against accepted v2 BOUNDARY/SOURCE-MIGRATION and
the inherited frozen v1 types, using the requesting-code-review checklist.
The human forbids additional agents; this is author self-review, weaker than
independent review. Base is local6db895955472e02328539a9800acecde4b0ee6fe.

The four fixed type layouts match all six signing vectors, including ADD/REMOVE/
SET governance array hashing. Domain names and version are fixed by type; chain
and verifying contract are required caller context. No producer types/digest or
claimed signer is trusted. Recovery uses the existing locked eth-account library;
this is not a new cryptographic primitive or independent library implementation.

Message and signature encodings go through explicit v2 validation; governance
admins retain strict ordering. Configured addresses are canonical/nonzero/unique,
version must match, count is an actual integer, and recovered signers must be
configured, distinct and sorted. A q2 certificate is accepted only when the caller
explicitly requests the negative-control count, never as q3. Single F reporters
and the carried E version1 path are supported without migrating E consumers.

The checkpoint helper walks pinned error.recorded, recordedReports, each
inconsistent reporter's reports and lateReports. It verifies each against the
configured index; it never uses the report's claimed address. Late duplicates
may be checked repeatedly and never become quorum evidence in this helper.
The caller must supply the original selector for a pinned single refusal.

Positive controls include exact frozen digests/signer lists, all12 wire report
paths, explicit q2/single checks and a freshly signed synthetic version1 message.
Negative controls bind every signed field, chain/contract/name/version, wrong
sets/counts/order/membership, canonical signature rules and altered retry reports.
Some field mutations also violate shape/semantic rules; those reject earlier,
as required. Non-shape mutations exercise actual recovery with retained signatures.
No mock substitutes for cryptographic signing/recovery. No material code defect
found in this bounded slice. No minor code changes deferred.

Ruling on boundaries considered: source truth, domain-to-chain role/wiring, actual
set/threshold selection, runtime expiry/nonce/observation checks and export/store
completeness remain caller/runner duties. The API documents required anchored
context and does not infer it from self-reported bindings. There is no live
caller yet, so no full evidence acceptance is claimed. The checkpoint helper
checks declared reports only; a success certificate must separately be passed to
verify_certificate, and no-report responses return0, not a certificate verdict.

The existing schema_v2 shape helper deliberately keeps its narrower docstring;
the new module composes with it rather than suggesting shape checks now recover
signatures. E code, dependencies, owners' sources, frozen/proposal/published
contract bytes and research gate records stay unchanged. Remaining implementation:
anchored B/getter/wiring/fixture reconstruction, exporter history/orphan/WAL/native
joins, independent fault oracle/model and separately ACKed source/execution.

Network review limit: both owner refs and344 communication paths are CACHED.
Fresh fetch failed publickey; audit verifies exact cached blob hashes, not current
remote publication. No ACK, readiness, fresh remote state or owner execution is
inferred. Existing local checkpoint is preserved. Lock file existence was first
probed with mkdir incorrectly; persistent file flock was then acquired before
repository reads/edits, and its inode is retained. Next run must start with flock.
