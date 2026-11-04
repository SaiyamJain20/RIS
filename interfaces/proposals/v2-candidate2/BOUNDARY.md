# Successor v2 candidate 2 boundary and mandatory semantic rules

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
means the repaired-f q3 pool (the carried E path retains its single witness). A selector requests exactly one synthetic witness;
its success has one signature and no collection. For carried E profiles, there
is one witness/version1 and no F pool; selectors other than the configured
witness must refuse MALFORMED with no reason, even for a well-formed but unconfigured selector. F messages use version2. A declared version must match the
actual deployment; mismatch is STALE_STATE with reason WITNESS_SET_MISMATCH. The schema's 1/2 carrier is not permission to mix them.

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
19 reasons and their only legal codes, exactly from SUCCESSOR-WIRE revision8
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
skipped_validity when adopted.message.expiresAt*1000 minus
(ledgerNowAtStart*1000+snapshotClosedAtMs)<=2000; otherwise sent. Exactly2000
is skipped,2001 is sent. A hard-stop snapshot still selects from received
reports, but no second round runs and lateReports is absent. A sent second round
has its own 5s reply bound inside the original deadline. No host clock declares
a digest dead and no retry extends a request, proposal, grant or collection.
All earlier digests must be observed dead on mined target-ledger state before
conflicting reuse; this cannot be established from the response schema.

## Deployment exports and D50

Both successor E and F deployment carriers use hmbc-ledger-deployment/v2 and
interfaceVersion v2. Historical v1 E exports and all frozen v1 bytes stay fixed.
LedgerAbiEntry and LedgerAbiContracts retain their exact v1 definitions. Successor
six-entry and seven-entry ABI containers are LedgerAbiContractsV2 and
LedgerAbiContractsFV2; both reference LedgerAbiEntryV2. An opt-in owner exporter
is required after freeze; no producer is switched by this proposal.

Each successor runtime (six E, seven F) requires canonical decimal-string
runtimeBytes, immutableReferences=[{start,length}], and immutableRefsSha256.
Both range members are below2^32; every length is32, sorted/disjoint/in-bounds;
empty lists are allowed. Enforce actual uint widths through semantic validators,
not advisory JSON Schema format alone. Immutable hash preimage is UTF-8 canonical
JSON of the OBJECT LIST (sorted keys, compact separators, ensure_ascii).
Hash decoded bytecode bytes and require exact live length; mask only trusted
compiled ranges. No source/constructor attestation follows from masked equality.

F has profile repaired-f/enum3; live mutation masks identify mutants, never
mutantNote. Baseline is mask0/q3, runner-crafted q2 control mask0/q2, code mutants
nonzero mask/q3; reject nonzero mask/q2. Multiple bits remain representable up to
511 but do not identify a single-removal experiment without a separate schedule.
The ordinary pool always collects3; q2 is assembled from distinct single-witness
responses sorted by recovered address. All3 complete ORDERED sets from PSC,
KSSC, Governance must match the fixture and each other (n4/version2/threshold2or3).
Compare all5 mutation getters (TMSC/PSC/KSSC/ACSC/Governance), all4 profile
getters=3, Governance.target(), governanceChainId(), witnessSetVersion(),
maxGovernanceTtl() and the compiled MAX_ADMINS=8 attestation. The fixture requires
governance.maxGovernanceTtl=120 and maxAdmins=8; no measurement is asserted.
Native GovernanceApplied/AuthorityAdded/AuthorityRemoved/CaAdminsSet events
must be retained under the owner-compiled ABIs for FL-10/F-28.

D50 revision5 normalizes manifest names through its CLOSED profile table:
paper-strict=(0,0), paper-minimal=(1,0), repaired-e=(2,0); the six E mutants
mutant-no-destination-binding, mutant-no-state-barrier, mutant-no-record-freshness,
mutant-no-nonce, mutant-no-version-monotone, mutant-no-receipt-binding are
respectively (2,1/2/4/8/16/32); repaired-f=(3,0..511). B.profile.name is BASE[enum],
not manifest.profile. At open, unknown name or enum/live-profile mismatch is
PROFILE_MISMATCH at stage2 (WRONG_PROFILE); illegal/mismatching masks at stage7
are MUTATIONS_MISMATCH (WRONG_DESTINATION). Stage2 precedes stage7.
All reporting holders must be present. B's profile name/enum agree, witnesses
are unique and 1<=threshold<=set length. F B.interfaceVersion is v2; historical
E B may be v1 or v2. B retains contract order, excludes mutable governance/nonces/
authorities, and carries six E or seven F runtime entries. Immutable digests in
historical E B are all-or-none; all are required for F and successor E exports.
Reconstruct B from anchored observations; binding_v2 is SHA-256 of ASCII
hmbc-deployment-binding/v2 followed by LF and canonical JSON(B), unprefixed hex.
The copied owner F vector is now v2. OWNER-PINS.json identifies exact inputs.

## Read-only exporters and witness history

BindingExport, WitnessEvidence and ExporterError are SEPARATE closed definitions,
not adapter operations/responses. Exact fields, per-type effects/death variants,
wire canonicalization, CLI names and consistency rules are EXPORT-LAYOUTS
revision9 at the OWNER-PINS.json hash and its exact checker. Both owners must ACK
the COMPLETE mapping/layout unit before F0 freeze. This proposal retains the
owner's four synthetic evidence variants and two binding exports byte-for-byte.
Owner placeholders establish layout only, not signature recovery or execution.

Success: stdout is exactly one canonical JSON line plus one LF, stderr empty,
exit0. Refusal: stdout empty, stderr one canonical ExporterError line plus LF,
exit3. Usage errors exit2. Reasons are only STORE_MISSING/STORE_CORRUPT ->
ADAPTER_UNAVAILABLE, LEGACY_STATE -> WRONG_DESTINATION. Exporters make no RPC,
read one WAL-aware mode=ro transaction, never immutable=1, and expose no keys.
Default worker_log remains byte-compatible. Committed state includes main+WAL+
INITIALIZED; shm is not state. Compare logical WAL-aware snapshots AND marker
bytes. EvidenceSha256 is a before/after fingerprint, never authentication or a
substitute for the logical-state hash. Process death is not power-loss evidence.

For every K, preserve superseded generations in seq append order followed by the
live record. Adjacent vHash values must differ; A->B->A is permitted. In the no-
fault/no-clear interval every next-generation digest observation is not before
the prior generation's death in BOTH mined number and timestamp (equality is
allowed). Retain this revision9 ordering rule. For the same-block case join raw
block hashes too. A clear never deletes signing history and labels that interval
outside the safe-ledger assumption; it does not restore a safety claim.

The layout checker verifies declared internal relationships: closed effects,
hashes, canonical formats, sort orders, unique K/digests, append seq, target
chains, fault predicates/last observations/clear baselines, and death numeric
relations. Recompute all of them; JSON Schema alone is insufficient. Only ALLOW
(result1) can die by overtaken-decision-grant. DENY can die by expiry or a strictly
newer checkpoint sequence. Reconstruct each signed message from its K/effect/
liveness fields; independently recover owner, domain and EIP712 digest, check
actual ledger facts and observations, and compare export completeness to store
snapshots. In particular a superseded K requires its live successor under the
signing transition; the owner checker currently accepts an orphan history.
This is an explicitly additional runner completeness check, not a claim that
its layout checker enforces it. Hash self-consistency cannot prove store truth.

Mutant exclusions: under bit1 the state-barrier removal means sequence-based
death is not baseline safety evidence; under bit5 receipt binding removal means
executed-receipt death is not baseline safety evidence. Preserve them as mutant
controls with their changed acceptance rules. Trusted-ledger grant existence,
OUTCOME_RECORDED and all other death facts require raw owner-ABI observations.

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

M1-M4/P1-P7/N1-N4 are mapped in this candidate and its source migration
addendum. D4/D6 remain Agent2 implementation tasks after freeze. Exact complete
mapping/layout ACKs are pending; no previous design ACK transfers to this unit.
Later source READY, tool/config/execution FREEZE, E regressions, TLC and real
integrated F evidence remain separate work. All32 F cases are NOT_RUN; G locked.
