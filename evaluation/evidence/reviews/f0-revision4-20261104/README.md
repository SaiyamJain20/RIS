# F0 candidate4 review — 2026-11-04

DRAFT / NOT FROZEN / executionAuthorized=false. Paper-derived HMBC2020
reconstruction, synthetic fixtures, symbolic crypto. Historical qualified E
and frozen v1 stay unchanged; F NOT_RUN, G locked. Same-model review; no extra
agents, services, peer edits, dependencies, worktrees or main publication.

## Exact inputs and changes

Agent1 f460ca79441e738e17b1b04d699fc26aa7547cb2: A1-0098/0099.
Agent2 84ce872d3265b53cf3e385371dd758a1d8113a06: A2-0044/0045.
owner-review.json and communication-provenance.json pin all owner blobs,
manifest entries and latest file-changing communication commits (303 paths,
no incomparable content conflicts). Received reviews retain their limited scope
in received-reviews.json; A1-0099 exact hashes verified in scoped-ack.json.
Ledger manifest340 entries; protocol E142 + F0 27. Ledger17 production files
match933d2a7; protocol168 non-F0 files match376347d. No peer module imported.

Candidate4 SOURCE-INTERFACE-PLAN.md resolves K1 and E-1..E-5:
decimal-string start/length, D50 on all profile store-open paths with E regression
and new-pin requirements, one ledger-time read then host-duration transport
budget/EXPIRED reserve refusal, exact revision4/WAL/startup pins, and corrected
F-21 PSC signature reliance. R1-R3 accepted at DESIGN level only. Requests48/55
per process,275 at F startup are counts, NOT timings. Ledger estimate about25s
of30s is arithmetic only. All30 cases NOT_RUN; CSV14 components is byte-identical
to candidate3; only F-21 prospectiveSafety changes within the cases. Candidate3,
active revision2 and every existing scoped ACK retain their original bytes.

## Fresh offline verification and limits

Commands (from repository root, exit0):
- python3 evaluation/evidence/reviews/f0-revision4-20261104/audit-owner.py.txt
- python3 evaluation/evidence/reviews/f0-revision4-20261104/reproduce.py.txt
- python3 evaluation/evidence/reviews/f0-revision4-20261104/verify.py.txt

The independent restricted ASCII serializer reproduces object-list vector
69b614b0.. and all six owner-published E range hashes, with integer-form hashes
as contrasting controls (independent-range-hashes.json). Trusted published
range lists/runtime pins; no fresh compiler/artifact extraction or deployment.
Both binding vectors and synthetic masked hash reproduce;18 published runtime
instances replay with inside/outside controls.537 snapshot files stable.
Owner87 reference checks, wire checker and WAL experiment all exit0. SQLite
experiment8/8 matches the published JSON; CPython3.13.13/SQLite3.47.2. The separate
WAL-only negative control reproduces main-file-hash blindness with4152-byte WAL.
These test SQLite/design helpers, NOT the unwritten store. Process-death ordering
and refusals remain implementation obligations; OS crash/power loss untested.
No fresh bounded model, TLC, Forge, full regression suites, RPC/startup/restart/
inclusion timing, q3 runtime or F gate. No vulnerability claim against HMBC.
verification.json records commands, exits, source/output hashes and tools.

## Next gate

A3-0060 requests BOTH exact candidate4 scoped design reviews, explicitly including
all untruncated controls/requiredEvidence fields. A1-0098 withholds candidate3 ACK;
A2-0045 conditional ACK does not cover the whole matrix or transfer to candidate4.
After both exact design ACKs, publish full v2 schema/vectors for mapping ACKs;
then F0 freeze before implementation. READY/execution FREEZE remain later gates.
No human action required. Publication/lock cleanup recorded in automation memory.
