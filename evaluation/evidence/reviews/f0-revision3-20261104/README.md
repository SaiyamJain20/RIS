# F0 revision 3 review and next shared candidate — 2026-11-04

**REVIEW, NOT AN ACK OR FREEZE.** The new owner amendments largely answer
A3-0058. Agent3 independently reproduced the two binding hashes and masked
vector, and all 18 published runtime instances. Candidate3 now supplies the
source/interface plan and 14-component/30-case matrix for exact owner review.
Three narrow design amendments remain below. No implementation or F gate result.

Exact inputs: Agent1 3b5c4140ba41240d1df7384ef7201bae7684c489 (A1-0096/97,
design 2.2), Agent2 d4d5ff0eea1cb94c4f486bfeb3f52968e085a32f (A2-0043,
revision3). owner-review.json records every owner blob/manifest and pinned refs.
communication-provenance.json records latest file-changing commit/ancestry for
298 paths, no incomparable content conflict. Owner STATUS/HANDOFF and new
outboxes reviewed. A1-0097 is a genuine exact **ledger-facing** ACK; its hashes
verify in scoped-ack.json. It excludes protocol internals, vectors, freeze,
migration, interface and execution. It does not approve Agent3's candidate3.

## Disposition of A3-0058

The successor reason table/collection/witness selector and FAULTED recovery are
now specified; keyless worker versus witness ownership is explicit; build ranges
and compiled length/constructor limits are specified; canonical closed B/vector
and 25-entry manifest are supplied. The earlier zero-extra-RPC claim was
withdrawn. Startup caching and a live-worker chain-replacement residual are
explicit. These are design improvements, not runtime verification. The
remaining startup count and lifecycle evidence details need correction.

## Required owner amendments (proposed-extension ambiguities)

**R1, complete S0 accounting.** D50 section2 promises to cross-check
PSC.rsc/tmsc/lsc and RSC.tmsc/lsc against manifest addresses. Its section3 total
43(E)/50(F) sums 8 chain requests +6/7 code +4 profile +4/5 mutations +6/9
witness-set +9/11 storage wiring +6 configured. The **five immutable getter
cross-checks** are not included. If each is a separate eth_call, the complete
total is at least **48/55**, before setup/retry overhead. Either explicitly add
them or specify a build-pin derivation that eliminates those calls while
actually checking the asserted named addresses. A raw hash alone does not
decode/assert their values. State whether these counts are per Ledger instance
(four witness processes plus worker may each perform S0), including the clear
command/evidence exporter and which calls reuse existing reads. No timings have
been measured; candidate3 retains that limitation and the F-13 cold-start budget.

**R2, WAL is committed state.** SUCCESSOR-WIRE section5 calls -wal/-shm side
files "not state" and proposes comparing main-database/marker hashes on refused
opens. A SQLite WAL can hold committed signing records not yet checkpointed.
The main-file-only oracle can therefore falsely pass a write-on-refusal mutant.
reproduce.py.txt demonstrates this on a disposable synthetic database: main DB
and marker SHA-256 stay identical while a second read-only connection sees the
inserted row in a 4152-byte WAL (SQLite 3.47.2, exit0). This is a **tested oracle
negative control**, not an observed defect in unimplemented protocol code.

Correct the state model: distinguish committed WAL from the recreatable shared
index. Specify consistent pre/post logical snapshots under the store lock,
database+marker+WAL recovery coverage, and a refusal mutant that commits a row
only to WAL and must be detected. Legitimate checkpoint/side-index creation
must not be mistaken for signing-state mutation. Preserve all committed WAL
when copying/restoring F-27 state; do not use immutable=1 to ignore it. State the
crash guarantee (process death versus power loss) explicitly; fsync settings
alone are not a measured power-loss result. Return the exact corrected rule.

**R3, initialization ordering wording.** SUCCESSOR-WIRE section5 step1 creates
the directory and .init.lock, while step2 says "before creating any file".
Distinguish permitted lock/directory metadata from database/marker creation.
Name restart behavior after marker rename but before directory fsync, and
which crash mode is tested. Keep signing gated by committed bound DB plus marker;
refused *existing* stores must not be silently initialized.

These are not paper vulnerabilities or tested F failures. R1/R2 affect the
execution/evidence plan; R3 closes an ordering ambiguity. Agent2 owns amendments;
Agent3 does not patch its RFCs or source. No new generic human decision is needed.

## Candidate3 for exact review

SOURCE-INTERFACE-PLAN.md proposes O1-O6, E1, a v2 synthetic witness selector,
object-list range encoding, independent binding/evidence export consumption,
1s mining/5s replies/10s collection/2s inclusion reserve, and existing 30/60s
proposal windows. All timings are **unmeasured proposed parameters** requiring
owner feasibility ACKs and later execution-plan measurements. Source owner paths,
regression/control obligations and interface-before-consumer gates are explicit.

f_matrix.json and fault-model.csv alongside this README supersede neither active
revision2 path yet: they are the reviewable candidate, with 14 components/30
cases ALL NOT_RUN, empty actual results/ACKs and executionAuthorized=false.
F-30 separates honest refusal from crafted out-of-assumption rollback; F-25/26
are analysis only; F-27 distinguishes detectable corruption from consistent
rollback; F-29 requires every old digest dead; F-13 retains cold restart timing.
M1-M7 and three-witness common-digest positive controls are planned. Original
revision2 and A1-0091 reviewed bytes/hashes remain intact; ACKs never transfer.

Next: Agent2 returns R1-R3 and both owners review the exact candidate3 hashes.
Then Agent3 incorporates resolved changes, publishes full candidate v2 schema/
vectors for exact mapping ACKs, and records F0 freeze before implementation.
Implementation READY and execution FREEZE/ACKs are separate later gates.

## Fresh evidence and limits

- audit-owner.py.txt exit0: ledger337 entries/338 blobs,17production files still
  equal933d2a7; protocol142E+25F0 entries/194blobs,168non-F0 unchanged376347d;
  all manifests and A1-0097 exact hash references verify. No peer import.
- reproduce.py.txt exit0: independent restricted ASCII object serializer yields
  repaired-e 242f7ca6977e22c97b6c1940cbc225136e9d4af71932aa7b08f156d9ed14aede
  and repaired-f e6a14cab56592a94bcc2e581b6b3fa62a489acab0b750520b2c4c67981e0cc01;
  synthetic masked vector ae0a5d388d6c0a7282e239e021056a1980f53f167d05fd6dbf2dd3444bc4fbfa.
  Serializer does not import the owner encoder and checks exact canonical bytes;
  it is a vector reproduction, not a general production schema implementation.
- Per-byte independent masking recomputes raw/masked hashes on18 published
  instances, matching compiled/manifest hashes claimed in owner reports, with
  inside-slot and outside-slot perturbation controls. No compiler rebuild or
  live deployment: ranges and compiled hashes are trusted published inputs.
  It verifies their byte consistency, not authenticates Agent1's measurement.
- Owner D50 expectations and wire-document checker rerun exit0, with command
  UTC/cwd/output hashes in reproduction.json. All532 copied owner inputs stayed
  stable. Unchanged bounded model/evidence need not be rerun; not TLC or a gate.
- Initial replay helper exit1 mistakenly stripped a nonexistent 0x from raw
  .hex inputs. Actual file convention was inspected, corrected, and exit0
  rerun retained. No owner file/source affected. Draft self-review corrected
  an invented Profiled.sol path to actual ProtocolTypes/four carriers before
  publication. No independent reviewer (same-model, no-extra-agent rule).

verification.json/review-manifest.json retain final checks and exact selected
hashes. No full suite, Forge/Anvil/TLC, real RPC timings, new service, dependency,
interface file, peer-module/mailbox edit, worktree or main push. Historical E
qualified PASS/signed/frozen bytes unchanged; F gate NOT_RUN, G locked. Guards
are file flocks, released at completion; file existence is not an active run.
