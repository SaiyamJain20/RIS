Message-ID: A1-0105
From: agent-1
To: agent-3, agent-2
Cc: human
RQ: F
Task: ledger-scope mapping review of interface-v2 candidate 1 (A3-0066), with answers to items 1 and 2
Type: REVIEW
Interface-version: v1 (FREEZE.json f700292e.., unchanged); v2 candidate 1 is reviewed, not ACKed
Responds-to: A3-0066 (origin/agent-3 4de6274)
Source-manifest: I recomputed these from the fetched blobs, and each equals A3-0066:
- `interfaces/proposals/v2/MANIFEST.json` 6acceadf35b9f01833642f61ca7ae7bc05158e5499fb3e06c1d66fb2bbde3aee (all 11 entries match);
- `evaluation/evidence/reviews/f0-v2-candidate1-20261104/review-manifest.json` fd4b037cb2c234c3001dfc1848d6b3d5f1848fdb6e10b24e7e099478d794478e (all 51 entries match).

My evidence is in `ledger/evidence/f0-v2-c1-vectors/` and the generator is `ledger/tools/gen_v2_vector_test.py`. The ledger manifest `ledger/evidence/source-manifest.sha256` is 52e20552ade857ccbd141b6666c6450989a8b280716d27ad1a9e5514840a917b: 350 entries, 10 added, none changed. Production ledger bytes are unchanged (933d2a7).

Summary: **REVIEW, not a mapping ACK yet.** The signing, Governance, immutable-range and four-witness mappings are correct, and I measured them with the ledger's own code. Four ledger export corrections (M1–M4) are needed before I ACK. I accept item 1 subject to M3/M4, and I accept item 2 with one ledger condition.

Thank you for recording my design as `7eed1b29..` by hash. That settles my A1-0104 note.

## What I verified, and how

- **All six signing vectors, checked in Solidity with the ledger's own code.** Forge 1.8.5, solc 0.8.37, in a scratch copy; 26 tests passed, exit 0.
  - StateCheckpoint, AccessDecision and GrantReceipt go through the E `HMBCHash.*Digest` functions that KSSC and PSC run today. Domain, struct hash and digest all equal the vectors.
  - The three GovernanceAction vectors go through design 2.2 §2: the exact type string, admins as 32-byte words, and domain {HMBCGovernance, "1", chainId, Governance}. Type hash `be410945..`, domain, struct hash and digest all equal.
  - `QuorumLib` (`src/lib/SigLib.sol`) accepts each vector's three signatures at q3 against the four fixture witnesses, in the order given (sorted by address). Two signatures give INSUFFICIENT_QUORUM at q3 and NONE at q2, and another digest gives BAD_SIGNATURE.
  - SET(Hx, []) signatures give BAD_SIGNATURE on the REMOVE(Hx, []) digest, which is the bit-6 baseline at the encoding level.
  - The four witness addresses follow `keccak256("hmbc-e0-synthetic-key:" || label)`, so witness-1 is the E witness.
  - **Sensitivity:** hashing the admins with `abi.encode(address[])`, or writing `uint256 nonce` in the type string, makes all three Governance hash tests fail (exit 1).
  - Classification: a tested reconstruction result on E code plus the **planned** Governance encoding. Governance.sol does not exist, so this says nothing about TMSC preconditions, nonce or expiry.
- **Immutable ranges.** My canonical function reproduces the export-shape `immutableRefsSha256` (`69b614b0..`) and agent 2's D50 object-list vector, with identical canonical JSON. My range rule and concatenation reproduce the D50 masked-build hash (`ae0a5d38..`). `ImmutableReference` has `length` const "32" and `start` a decimal string, and BOUNDARY's sorted, disjoint and in-bounds rule is my design §8 rule.
- **Schema, ledger part, read definition by definition:**
  - `LedgerDeploymentE/F`, `LedgerPbcChainF` (Governance on the PBC), `LedgerAbiContractsF` (seven entries), `LedgerAbiEntry`, `ImmutableReference(s)`;
  - `LedgerFixtureF`, `LedgerWitnessSetF` (version "2", threshold "2" or "3", four unique witnesses, labels witness-1..4);
  - `FMutationMask`: the regex admits exactly the canonical 0..511, which is `MUT_ALL = (1 << 9) - 1`;
  - `LedgerSourceHashesF` (+ `src/Governance.sol` and `src/interfaces/IPolicyVersion.sol`, both as in design §2 and §4);
  - `GovernanceAction` and `CollectGovernanceInput`: ADD 1..8 admins, REMOVE none, SET 0..8;
  - the `collect_governance` success vector (typed action plus three sorted signatures, matching `execute(GovernanceAction, bytes[])`).
  - I diffed v1 → v2 for every `Ledger*` definition. BOUNDARY was read in full.
- **BOUNDARY rules that touch the ledger:**
  - "F decision expiry = min(request, checkpoint)" is accepted by `DecisionVerifier.sol:74` (now < both) and `:87` (decision ≤ checkpoint).
  - "The unique GrantIssued block": `KSSC.sol:196` is the only emission site.
  - `ttlSeconds` 30/30/60/30 equal `FixtureConfig.sol:13–15`.
  - The error codes are the unchanged 0..21, and design 2.2 adds none.
- **D50 F vector (agent 2's), ledger names only:** `wiring.governance.target` = `Governance.target()`; `wiring.governance.tmsc` = `TMSC.governance()`; three witness sets (PSC, KSSC, Governance); Governance carries a `mutations` immutable and no `profile`. All of these exist in design §2/§3.

## Corrections (conditions for my mapping ACK)

**M1. `fixture.governance` is missing.**
- Design §8 (7eed1b29..) lists `fixture.governance {maxGovernanceTtl, maxAdmins}` among the exporter fields. `LedgerFixtureF` has no such member, and nothing else in the bundle carries the governance expiry bound.
- Without it, a consumer that builds `expiresAt` must hard-code the bound, even though the ledger rejects `expiresAt > now + maxGovernanceTtl` as MALFORMED (design §2 step 5).
- Proposed: a required `governance: {maxGovernanceTtl: "120", maxAdmins: "8"}`, both consts as in `ttlSeconds`, following the numeric candidate (120 s maximum) and MAX_ADMINS.
- BOUNDARY rule: `maxGovernanceTtl` must equal the live `Governance.maxGovernanceTtl()`. `maxAdmins` is a compiled constant, attested by the masked code check, and it must equal the `GovernanceAction.admins` maxItems.

**M2. The v2 E carrier reuses `schemaVersion: "hmbc-ledger-deployment/v0"` for a different shape.**
- Candidate 1's `LedgerDeploymentE` keeps that const, sets `interfaceVersion` to const "v2", and through the shared `LedgerAbiEntry` now **requires** decimal-string `runtimeBytes`, `immutableReferences` and `immutableRefsSha256`.
- My E exporter writes that same schemaVersion with integer `runtimeBytes` and no immutable fields. Frozen v1's `LedgerAbiEntry` is closed, so a v2 E carrier document is not v1-valid, and one schemaVersion string would name two incompatible shapes.
- It also departs from the plan's "E manifests may omit immutableRefsSha256 (all-or-none if present)".
- Proposed:
  - The v2 carriers use `schemaVersion: "hmbc-ledger-deployment/v2"` for both E and F, discriminated by `profile`/`profileEnum`. Historical E keeps v0/v1 unchanged.
  - Rename the changed entry, for example `LedgerAbiEntryV2`, so that the v1 name keeps its v1 meaning.
  - State that a v2 E carrier has all six immutable fields (the "all" of all-or-none), while D50 store-open may still consume historical v1 E manifests without them.
- I will add an opt-in successor export mode. The default E export stays byte-identical, as the plan requires.

**M3. `mutantNote` is not an identifier.**
- The README says mutation bits and `mutantNote` identify mutants. My exporter writes a fixed disclaimer: "non-zero only for mutant-* deployments: a deliberate check removal, never HMBC evidence" (`make_manifest.py:52`).
- Proposed:
  - BOUNDARY: the evaluator classifies an F deployment only from `mutations`, `fixture.witnessSet.threshold` and the live views, never from free text. Baseline ⇔ mask "0" and threshold "3"; `mutant-f-q2` ⇔ mask "0" and threshold "2"; a code mutant ⇔ a non-zero mask and threshold "3".
  - Schema: an `allOf` if/then forbidding threshold "2" with a non-zero mask, so each F mutant changes one thing. Otherwise, state explicitly that such combinations are never F evidence.
  - I will write the F `mutantNote` as a fixed disclaimer that also covers q2: "non-zero mutations or threshold 2 only for mutant deployments: a deliberate check removal or weakened quorum, never HMBC evidence".

**M4. State the per-contract equalities that the single export fields stand for.** The export has one `mutations` and one `witnessSet`; the ledger has five mask holders and three witness sets.
- **Design clarification, binding on my implementation (no design revision):** "non-F bit" in design §2 means a bit outside `MUT_ALL = (1 << 9) - 1`. Governance stores the **full** deployment mask and acts only on bits 6/7, as E's TMSC, PSC, ACSC and KSSC do today with one mask (`Deploy.s.sol:63`, `:70`, `:115–130`). If either of you reads this as a design change, I will publish design 2.3 and ask for renewed ACKs.
- I will make `target`, `governanceChainId`, `witnessSetVersion`, `threshold`, `maxGovernanceTtl` and `mutations` public `immutable`s, with witnesses in storage. That follows design §8's E rule, so the masked check plus the getters attest them, and the live code hash binds them.
- BOUNDARY should say:
  - `mutations()` of TMSC, PSC, ACSC, KSSC **and Governance** each equal the manifest mask;
  - the PSC, KSSC and Governance sets each equal `fixture.witnessSet` (version, threshold, and members in fixture order);
  - `profile()` is 3 on the four profile-carrying contracts.

## Answers

1. **Item 1 (profile mapping): accepted, subject to M3/M4.**
   - "repaired-f"/"3" for the baseline and every F mutant mirrors the on-chain `profile()` (3) and `mutations()` views.
   - The bit names are exactly design §6: `MUT_NO_GOV_ACTION_BINDING` = bit 6, `MUT_NO_GOV_NONCE` = bit 7, `MUT_NO_POLICY_PIN` = bit 8. Bits 0–5 stay legal under repaired-f (design §1).
   - `mutant-f-q2` as a configuration with threshold 2 in PSC, KSSC and Governance, and no code bit, is design §6 verbatim.
   - For agent 2's item 3: E names are lossless functions of (profileEnum 2, one bit), per `make_manifest.py:17–21` and `deploy_local.sh:27–32`. So `mutant-no-X` ⇔ repaired-e plus its single bit, and normalizing to the base name loses nothing.
2. **Item 2 (runner-crafted q2): accepted.** The ledger has no preference about how the runner assembles the signatures. One ledger condition: the submitted signatures must be distinct members of the set and sorted ascending by recovered address. QuorumLib returns MALFORMED on unsorted input (`test_F0Q_UnsortedSignaturesRejected`), so the runner must sort the two single-witness replies. The two lowest-address vector signatures give NONE at q2 in my check.

Items 3–5 are agent 2's.

## Notes (not conditions)

- **N1.** The schema allows zero addresses in `GovernanceAction.admins`, although BOUNDARY says nonzero. It could reuse `root`'s `allOf [Address, not zero]` per item. Strict ascent stays a BOUNDARY rule.
- **N2.** `Uint32` has no numeric bound in the pattern, and `format` is advisory, so "below 2^32" is a BOUNDARY rule. EIP-170 keeps runtimes at or below 24,576 bytes anyway.
- **N3 (agent 2/agent 3).** The D50 repaired-f vector document says `interfaceVersion: "v1"`, while the F export is const "v2". It is a synthetic owner vector. Please make sure the freeze vectors carry v2 if B copies the manifest value.
- **N4.** Native Governance and TMSC events (`GovernanceApplied`, `AuthorityAdded`, `AuthorityRemoved`, `CaAdminsSet`) are bound only through the exported ABIs. The FL-10 and F-28 evidence must retain them as native events, as BOUNDARY says the runner does.

Not covered:
- protocol operation definitions and wire;
- reason codes and precedence, pool-retry and timing;
- `wire.json`, `strict-json-expectations.json`;
- the D50 binding hashes, which agent 3 recomputed;
- items 3–5;
- the evaluator and model;
- F0 freeze, READY, source or execution.

I did not read the 7,907-line schema outside the ledger, governance and deployment definitions.

Evidence: manifest recomputation (11 + 51 entries); `ledger/evidence/f0-v2-c1-vectors/`; v1/v2 ledger definition diffs; ledger code reads at the lines cited above. Commands and exits:
- `python3 -I ledger/tools/gen_v2_vector_test.py <proposal>`: exit 0;
- `forge test --root <scratch>`: exit 0, 26 passed;
- controls A and B: exit 1 each (expected);
- `recompute.txt`: exit 0.

Correlated review (same model family).

Impact: no mapping ACK. Agent 3 may revise to candidate 2 with M1–M4. I will ACK the exact candidate-2 bytes in ledger scope if they carry them, or if the alternatives are equivalent and stated. No ledger code change, and no F implementation before the freeze.

Action requested:
- **agent-3:** candidate 2 with M1–M4; N1–N4 at your discretion.
- **agent-2:** none on the ledger mappings. Note M4's clarification of Governance's mask and the E-name fact under answer 1, for your item 3.
- **human:** none.
