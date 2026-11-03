# A1-0091 scoped ACK and A1-0092 design review — 2026-11-03

F0 remains DRAFT / NOT FROZEN. No implementation or execution is authorized by
this review. The matrix stays at revision 2: 14 components, 29 scenarios, all
NOT_RUN. Its original manifest and embedded publication-time empty ACK lists
remain byte-identical. `scoped-ack.json` records the later **ledger-scope review
ACK only**, A1-0091; it is not an F0 freeze, migration or execution ACK.

Exact owner commit: `3842213febaed7e946925797a769fb20e9d43393`.
Design revision 2 SHA-256:
`dda3914ba3acaf721df32d9fd1233baeb0d23f21a6d023e2c389acd2ae841fe9`.
Ledger manifest SHA-256:
`5f7203e247fcaa94174638633579e4470831643e32514a179a83f95009df7877`.
Agent2 stays `376347d9b0979d1e46824a30197b935ffe91e4fb` / A2-0039.

## Review disposition

- **R1 addressed at design level.** The eight virtual profile overrides, nine
  repaired-profile branches, fixture version/threshold/list parameters and
  q-aware signing helpers are now explicit. Preserve all E assertions and
  compare complete per-test outcomes before/after (198 existing tests); do not
  claim equivalence before running. Reading `src/lib/SigLib.sol:42-65` supports
  the predicted duplicate/high-s/compact/unknown-signer codes before final
  threshold counting. Domain-negative signatures remain negative. The F
  subclasses and helpers have not been compiled or executed.
- **R2 addressed at design level.** Removed roots are permanently tombstoned;
  a returning organization uses a new root and new credentials. Old root lists
  remain historical views; fresh roots need fresh anchors. This is an explicit
  reconstruction choice, not a paper-prescribed rule. Removal takes effect at
  the DBC checkpoint barrier under F-28, subject to all other checks/expiry.
- **R3 addressed at design level.** TMSC mutators receive the signed nonce;
  Governance advances its nonce before the external call, with whole-EVM
  rollback on failure. Typed event/getter/config/wiring/log fields and the
  policy-version interface/insertion point are listed. Runtime rollback and
  log correspondence still require the proposed tests.
- **R4 substantially addressed.** Typed GovernanceAction and sorted nonzero
  admin arrays remove the opaque payload decoder. The action=0 mutant signing
  rule is correct for the proposed dropped-action check. Vectors, positive
  controls and numeric bounds remain prospective, not verified cross-language
  bytes. Clarify the decoder wording: typed ABI calls do not by themselves
  require a unique raw calldata encoding or reject every trailing byte. Hash
  decoded typed values; do not advertise raw-calldata canonicality. If that
  stronger property is intended, specify a separate check and tests.
- **R5 addressed at design level.** A versioned v2 successor and seven-runtime
  D50 identity coverage, including Governance, are explicitly required. Frozen
  v1 is untouched. Agent3/Agent2 consumer migration still belongs in the exact
  affected-file/source/interface plan after protocol input arrives.

One mutation test clarification: **bit 7 replay must use an action whose TMSC
precondition remains satisfied**, e.g. SET_CA_ADMINS on an existing authority.
Repeating ADD fails existing-root validation; repeating REMOVE fails unknown-root
validation even with nonce checks removed. Use fresh matched baseline/mutant
fixtures, a positive SET, a replay that baseline refuses with REPLAY, and assert
the mutant repeats the epoch/log transition. This is a proposed sensitivity-test
design correction, not a measured mutation or an HMBC finding.

**R6 remains open.** Agent2 must provide its independent key/state/correlation
inventory, canonical conflict values/typed domain keys, receipt equivalence,
durable signing/recovery rules, target-ledger expiry/finality observations and
D50 identity RFC for all seven runtimes. A1's target-ledger expiry suggestion
is useful input, not an agreed numeric finality or re-signing rule. No full
migration ACK, scope selection or F0 freeze is issued here. Any new matrix
revision requires fresh exact affected reviews; preserve A1-0091's narrow scope.

## Evidence and limits

`python3 .git/ris-a1-0092-review.py` exit 0; reproducible helper retained as
`audit-owner.py.txt`. Fresh read-only audit verifies 302 manifest entries against
303 owner blobs; 17 production files equal E pin `933d2a7`. Only design and its
manifest changed under ledger since `5992a0a`. Fifteen earlier requested test
names verify. `communication-provenance.json` covers 286 communication paths
across four exact fetched refs, using file-changing commit ancestry, with no
incomparable content conflicts. New owner STATUS/HANDOFF/outboxes were read.

`verification.json` records focused hash/protected-path/planning/launch checks,
commands, UTC, exits and tool/output hashes. No Forge/full evaluator/protocol
suite, TLC, live service or integrated F run is repeated. Historical E qualified
PASS and frozen/signed bytes are unchanged. F gate NOT_RUN; G locked. Review is
correlated same-model under the no-extra-agents rule. Navigation initially tried
two nonexistent QuorumLib paths, then located `src/lib/SigLib.sol` from its import;
no source was modified by those failed reads.

Next: owner clarification plus Agent2 exact input, then resolve the source and
interface choices and obtain exact affected ACKs before F implementation.
