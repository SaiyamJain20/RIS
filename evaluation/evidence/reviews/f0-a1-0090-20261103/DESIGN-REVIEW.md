# F0 revision 2 and A1-0090 design review — 2026-11-03

**DRAFT / NOT FROZEN / NOT EXECUTABLE.** This revision incorporates A1-0090's
seven matrix corrections. It is a review of proposed reconstruction choices,
not an interface ACK, F implementation, fresh ledger test or F result.
The original alternatives and trust model in
`../f0-planning-20261103/F0-DRAFT.md` still apply. No choice is selected here.

## Exact inputs and matrix changes

Owner commit: `5992a0af38485ecb817b10d025145f81d51ee348`.
Owner design: `ledger/f0/A-F1-DESIGN.md`, SHA-256
`02447d023c7976ad13c2e98387228508ab4cd784443747963a9db1d8e8e49cc3`.
A1-0090 explicitly withholds ACK. Agent2 remains at the common baseline
`376347d9b0979d1e46824a30197b935ffe91e4fb`, with A2-0039 latest original message.

1. F-14 cites the four existing q1 repaired-e expiry/checkpoint tests.
2. F-15 cites the five existing trust replay/barrier tests, distinguishing
   pre-barrier acceptance from post-barrier refusal.
3. F-21 cites repaired-e signed-content refusal, paper-profile relay stress and
   the distinct trusted-witness forgery boundary. These are historical E tests,
   not measured F independent validation.
4. F-18 uses `mutant-f-q2`, a proposed configuration with threshold 2 in PSC,
   KSSC and Governance. No mutation bit; divergent honest views remain required.
5. F-24 separates proposed e1 policyVersion refusal from other monotone poison
   beyond the fault bound. Bit 8 `MUT_NO_POLICY_PIN` is a proposed sensitivity
   control, not an existing measured mutant.
6. New F-28 reserves authority removal across the DBC checkpoint barrier,
   including global authEpoch availability loss and expiry qualifications.
7. New F-29 reserves expired unexecuted governance and checkpoint proposals.
   Recovery/re-signing is unresolved; no safe clock rule is assumed.

There are now 14 component rows and 29 scenarios, all NOT_RUN; exactOwnerAcks
remains empty. The original revision-1 manifest is preserved as historical
evidence. `draft-manifest.json` in this directory binds the new active files.

## Source/schema review — changes required before exact migration ACK

**R1 — the regression migration is incomplete.** Section 7 proposes subclasses
of existing repaired tests. Their `profile()` overrides are not `virtual` (for
example `DecisionBinding.t.sol:93`, `Freshness.t.sol:176`), so direct subclass
overrides need explicit source changes. Test helpers also distinguish E by
equality: `Freshness.t.sol:26-27`, `AccessFlow.t.sol:50/208/258`,
`Audit.t.sol:54/57`, `TrustAnchors.t.sol:110`, and
`test/utils/Fixture.sol:421/471`. F subclasses otherwise take paper branches.
The signature-encoding test at `DecisionBinding.t.sol:207` constructs one- and
two-signature failures with q1-specific expectations. State explicitly which
helpers/expectations become profile-aware while preserving the E assertions;
do not claim the sources/assertions for all 198 existing tests can remain unchanged. Preserve
the historical E snapshot and demonstrate equivalence in the future regression
run. This is a proposed test-plan incompatibility, not an observed F failure.

**R2 — remove/re-add semantics need a rule.** Section 3 retains removed authority
lists as history but also says a newly added authority starts unpublished.
Existing TMSC uses `_crl[root]`, `_acl[root]` and `isAuthority[root]`
(`TMSC.sol:71-78/294-307/317-327`). Re-adding a previously removed root can
therefore revive retained state unless the new implementation distinguishes a
new incarnation or explicitly invalidates/reactivates it. Specify root
remove/re-add, old certificates, CRL/ACL versions/generations and stale lists;
add controls for both a fresh root and a previously removed root. Keep the
choice explicit; it is a design ambiguity, not a paper vulnerability.

**R3 — governance ABI/log binding is not fully specified.** Section 3's TMSC
mutator examples log `governanceNonce`, but only Governance declares that state,
and Governance advances it after calling TMSC. Specify exact mutator signatures
and how the log obtains the current signed action nonce, not the previous
stored nonce. Bind the log/event to the action actually authorized; specify
whole-transaction rollback and tests. Also specify all new public getters,
constructor/wiring types, event argument types and `IPolicyVersion` source path
in the final affected-file/ABI inventory.

**R4 — payload and mutant signing rules need byte-exact vectors.** Section 2
must define refusal of malformed/trailing/noncanonical encoded payloads and
zero/duplicate/out-of-order admins, including the exact error precedence for a
signed payload that fails decoding. `abi.decode` alone is not a canonical-byte
check. Keep proposed admin limit 8 and TTL 120 unresolved until agreed. For bit6,
the negative-control certificate must be signed over action=0 as the mutant
verifier hashes it; a normal certificate followed by an action change would
still fail recovery. Include successful baseline and mutant controls, all
domain/type/payload fields and boundary expiry/nonce vectors. None exist yet.

**R5 — runtime schema migration is not an additive v1 edit.** The frozen schema
permits profileEnum 0..2 and E profiles; its PBC contracts object is closed,
and witness fixture constraints are E-specific. The proposed `repaired-f`,
Governance entry, four witnesses/set2, bits6..8 and `mutant-f-q2` need a versioned
successor and consumer/exporter migration with both exact affected ACKs. Add D50
runtime/immutable identity coverage for the new Governance contract as well as
the existing six contracts. The adapter operations and runner profile whitelist
must be included in the exact source plan. No shared schema is changed here.

**R6 — conflict lifetime and expiry remain Agent2 dependencies.** Full EIP-712
domain separation corrects the old `(chainId, nonce)` shorthand. Add explicit
typed namespaces to persisted conflict records; Governance/Checkpoint/Decision
keys still need exact canonical-value and persistence rules; GrantReceipt is
unresolved. Re-signing after a local wall clock passes an expiry is not enough:
the old certificate must be impossible to accept on the relevant safe ledger,
with numeric observation/skew/finality assumptions. Cover both governance nonce
and checkpoint sequence after an unexecuted proposal. If re-signing is allowed,
state agreement over simultaneously live/acceptable values rather than claiming
the signer never signs two different values at any time. TLC and runtime checks
must use the same lifetime rule; neither has run.

The proposed minimal scope and QuorumLib reuse remain reasonable candidates,
but R1–R6 and Agent2's inventory/D50 prevent a full migration ACK. These comments
request exact owner revisions through A3-0055; Agent3 does not edit peer code.

## Evidence and boundaries

`owner-review.json` verifies 302 manifest entries against 303 exact owner blobs;
17 production files still match E pin `933d2a7`. Since the previous review only
the design and its manifest changed under ledger/. All 15 cited historical test
names exist. Existing q1 tests were read against the unchanged source; no Forge,
TLC, live services, full evaluator suite or integrated F test was rerun.
`communication-provenance.json` records all 283 paths across the four fetched
refs with file-changing commits; no incomparable content conflict was found.
The read-only audit helper is retained as `audit-owner.py.txt`.

This is correlated same-model review under the no-extra-agents rule. Historical
E qualified PASS and signed/frozen evidence stay unchanged. F gate NOT_RUN;
G locked. Next: owner design revision and Agent2 exact key/state/D50 input,
then resolve choices and obtain exact matrix/source/interface ACKs before F
implementation. A later execution requires its own complete run FREEZE/ACKs.
