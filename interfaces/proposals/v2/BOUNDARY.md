# Successor v2 candidate 1 boundary and mandatory semantic rules

Status: proposal for exact owner review. This does not replace frozen v1.
All inherited v1 types and encodings apply unless the changes below say otherwise.
The schema and this document form one review unit. Shape acceptance alone is
never evidence that a signature, source observation or state transition is valid.

## Operations, modes and compatibility

The envelope is exactly `{schemaVersion:"v2", operation, input,
deploymentManifest}`. Responses are exactly `{schemaVersion:"v2", ok, result,
error}` with exclusive non-null result/error. Validate the operation-specific
response definition as well as the generic envelope. The original eight
operations remain, and `collect_governance` is added. Crypto remains symbolic;
rotation remains NOT_IMPLEMENTED_IN_PHASE. No G primitive work is authorized.

The three existing witness inputs gain optional decimal-string witnessIndex
0..3. collect_governance takes exactly the six GovernanceAction fields plus
optional witnessIndex. No new caller-selected sequence, timestamp or source
block is accepted by checkpoint/decision/receipt operations. A missing selector
means the repaired-f q3 pool. A selector requests exactly one synthetic witness;
its success has one signature and no collection. For carried E profiles, there
is one witness/version1 and no F pool; selectors other than the configured
witness must refuse. F messages use version2. A declared version must match the
actual deployment; the schema's 1/2 carrier is not permission to mix them.

Pool successes have exactly three distinct signatures, sorted by recovered
address, over one typed message under the correct domain. Collection contains
exactly four outcomes in index order; the fixture maps each index to its own
process/key/state directory. The address in each outcome must equal that mapping.
Each outcome's replies counts actual received replies. `silent` means zero;
the other statuses require a received reply. `refused` carries code and optional
reason; other statuses carry neither. Optional nonempty detail text carries
diagnostics (including the owner's invalid-signature example). `duplicate-only` never contributes a
signer. submittedSigners equals the sorted three recovered addresses actually
selected for submission on success, and is empty on failure. This identifies a
certificate: it does not assert a transaction was sent, mined or accepted.
The runner separately retains submissions, receipts and native events.

## Typed GovernanceAction

Field order and type string:

```
GovernanceAction(uint8 action,address root,address[] admins,uint64 nonce,uint64 witnessSetVersion,uint64 expiresAt)
```

Domain is HMBCGovernance / 1 / PBC chainId / Governance address. Array elements
are 32-byte address words before keccak256. Root is nonzero; admins are nonzero,
strictly ascending and distinct. Action1 ADD requires 1..8 admins; action2 REMOVE
requires none; action3 SET permits 0..8. All integer fields are canonical decimal
strings within their widths. Typed decoded values are bound; raw ABI calldata
canonicality is not claimed. Nonce progression, expiry, version, current TMSC
preconditions and independent TEST-ONLY witness approval tuples are checked by
the owners' future implementations. Operator proposal validation and on-ledger
acceptance are distinct evidence. Four configured witnesses use labels
witness-1..witness-4 and indices0..3 in that order (a candidate mapping).

E request/decision/checkpoint/receipt domain names and field order remain those
in frozen v1. F decision expiry=min(request expiry, checkpoint expiry), and F
receipt block is the unique GrantIssued block. These are runtime checks.

## Error vocabulary and precedence

The original 21 code values stay unchanged. reason-codes.json enumerates all
19 reasons and their only legal codes, exactly from SUCCESSOR-WIRE revision7
§1. Reasons for EXPIRED, REPLAY, WRONG_EPOCH and existing validation refusals are
not invented. QUORUM_UNAVAILABLE is ADAPTER_UNAVAILABLE with collection; no
certificate is submitted. INSUFFICIENT_QUORUM denotes a rejected submitted
certificate, never a pool timeout. Ordinary errors may omit a reason.

At store open the first failing stage wins, in this exact order:

1. LEDGER_UNREACHABLE.
2. PROFILE_MISMATCH.
3. BUILD_PIN_INVALID.
4. UNSEALED.
5. WIRING_MISMATCH.
6. GENESIS_MISMATCH.
7. CODE_MISMATCH, MUTATIONS_MISMATCH, BUILD_MISMATCH.
8. WITNESS_SET_MISMATCH, then UNKNOWN_AUTHORITY (witness stores only).
9. STORE_MISSING, STORE_CORRUPT, LEGACY_STATE, BINDING_MISMATCH, OWNER_MISMATCH,
   then WITNESS_FAULTED.

Stages1..8 touch no store. Stage9 uses the marker and a WAL-aware read-only
connection before any read-write open. UNKNOWN_AUTHORITY has no new reason.
Keyless worker stores do not invent a witness membership check. Tripwire refusal
survives process restart; an explicit clear preserves signing history and is
labelled outside the safe-ledger assumption for the affected interval.

## Checkpoint retry evidence

Single-witness checkpoint CONFLICT_PINNED carries error.recorded exactly
`{message,signature}`: the stored latest-expiry signature for the original
sequence. It appears only on that operation's refusal, never pool failure or
another operation. No new signing is performed to produce recorded evidence.

Pool retries are checkpoint-only. recordedReports contains at most one report
per consistent index in strictly ascending order, each exactly
`{witnessIndex,message,signature}`. inconsistentReports contains ascending unique
indices with at least two distinct messages per reporter, each report exactly
`{message,signature}`, ordered by canonical JSON of message. These index sets
are disjoint. lateReports is sorted by index then canonical message; it is
evidence only. All signatures recover to the reporting configured witness under
HMBCState, and all snapshot messages have the proposal's sequence. An invalid
authenticated report is classified invalid and never counts. Channel identity,
raw arrivals, duplicate counts and the snapshot partition require runner evidence;
reported fields cannot prove their own completeness or actual timing.

Retain the initial proposal; ordinary retries resend identical bytes. Snapshot
selection excludes every inconsistent reporter, then selects iff exactly one
message has at least two distinct consistent reporters. Adopted is present iff
selection succeeds and is exactly `{message,reporters,reproposal}`. reporters
are all the contributing consistent indices, ascending and distinct, at least
two. No selection means no adopted member. Late reports cannot create or cancel
selection. Re-proposal sends the selected message verbatim, including its
original expiresAt. On success the certificate message equals adopted.message.
Honest witnesses independently validate it; two fabricated Byzantine reports
can select outside f=1 but cannot force an honest third signature. The f2 control
must leave honest witnesses unpinned/silent or reporting different values;
two honest reports for one other value would produce an ambiguous split instead.

Timing is present iff any of recordedReports/inconsistentReports/lateReports/
adopted is present. It has exactly ledgerNowAtStart, proposalExpiresAt,
collectionDeadlineMs, snapshotClosedAtMs, snapshotClosedBy, all decimal-string
integers except the closed enum. No timing record is accepted as a live timing
measurement without raw runner events and target-ledger observations.

Read target-ledger time once at fan-out start. Remaining<=2 seconds gives
EXPIRED before contacting any witness, with no collection or new reason.
Otherwise deadlineMs=min(10000,(proposalExpiresAt-ledgerNowAtStart-2)*1000).
The snapshot closes at the first all-replied event strictly before
min(5000,deadlineMs); otherwise deadline when deadlineMs<=5000, including a tie;
otherwise reply-timeout at5000. All-replied needs evidence that all four replied
by that time. Selection itself has no clock input.

Action precedence: skipped_deadline when snapshotClosedAtMs>=deadlineMs; else
skipped_validity when adopted.expiresAt*1000 minus
(ledgerNowAtStart*1000+snapshotClosedAtMs)<=2000; otherwise sent. Exactly2000
is skipped,2001 is sent. A hard-stop snapshot still selects from received
reports, but no second round runs and lateReports is absent. A sent second round
has its own 5s reply bound inside the original deadline. No host clock declares
a digest dead and no retry extends a request, proposal, grant or collection.
All earlier digests must be observed dead on mined target-ledger state before
conflicting reuse; this cannot be established from the response schema.

## Deployment exports and D50

Successor F deployment exports carry schemaVersion hmbc-ledger-deployment/v2,
interfaceVersion v2, repaired-f/profileEnum3, Governance in PBC addresses and ABI
entries, and the four-witness/version2 fixture. Seven runtime entries require
runtimeBytes and immutableReferences[{start,length}] as canonical decimal
strings below2^32, length exactly32. Ranges are sorted, disjoint and in-bounds;
empty is allowed. immutableRefsSha256 is unprefixed lowercase SHA-256 of UTF-8
canonical JSON of that object list (sort_keys, compact separators, ensure_ascii).
Hash decoded bytecode bytes; require live length equal to runtimeBytes and
compare runtime after masking only trusted compiled immutable ranges. Neither
handwritten Governance ABI nor placeholder runtime hashes are published here;
owner compiled ABI/source exports and READY checks are still required.

DeploymentBindingDocument defines the closed B field sets for six E or seven F
runtimes. D50's exact owner vectors are copied with provenance, not regenerated
through the owner's reference. Their live fields and F build data are synthetic
placeholders. The independent verifier reproduces both binding hashes and the
object-list hash. Prefix is ASCII `hmbc-deployment-binding/v2` followed by LF;
append canonical JSON(B), then SHA-256 without0x. On E the immutable digests
are all present or all absent; on F every runtime requires one. Owner is outside
B. Witness sets retain contract order. Dynamic governance/checkpoint/nonces and
authority/admin lists are excluded. The evaluator later independently joins
anchored per-chain observations and checks addresses, configured flags, wiring,
profile/mutations, set equality and membership, instead of trusting this hash.

Default worker_log fingerprint/export remains byte-compatible. --binding is an
opt-in export; witness_state --evidence is a read-only CLI, not a tenth adapter
operation. Their exact future JSON export layouts must be owner-published and
reviewed before consumption; this proposal does not claim unwritten layouts
have been mapped. Preserve conflict/digest/superseded/death/tripwire evidence.
SQLite committed state includes main+WAL+INITIALIZED; shm is not state. Refusal
oracles compare logical WAL-aware snapshots and marker bytes; a main-only backup
is a rollback, not equivalent state. Process-death controls do not establish
power-loss durability. Owner lifecycle ordering is unchanged from revision7 §5.

## D-4 / D-6 migration and remaining review

Agent2 owns updating stale adapter.py documentation and exports/adapter.json
serviceStatus/status/draftNote in its future revision: labels must describe actual
implemented operations/readiness and must not assert an unrun F gate. It also
owns replacing testtools/deviating_witness.py plain json.loads with strict parsing
and tests. Preserve its TEST-ONLY-manifest guard and exclusion from production
imports. Duplicate JSON keys, NaN/Infinity, JSON integers in string fields,
unknown fields, noncanonical signatures and oversized (>1MiB UTF-8) requests
must refuse MALFORMED; parsing never uses last-key-wins semantics. Existing E
historical pinned bytes are not rewritten. This is an owner task, not a fix
claimed by this schema publication.

The q2/manifest-profile mapping choices and E mutant-name ambiguity are listed
in README.md and explicitly need owner review. Exact exporter layout also remains
pending owner publication. No final mapping ACK or F0 freeze is claimed. Changes
to accepted design inputs need renewed affected-scope ACKs. Later source READY,
tool/config/execution FREEZE, E regressions, TLC and integrated F evidence are
separate work; a schema-check pass closes none of those gates.
