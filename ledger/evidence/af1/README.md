# A-F1 implementation log (agent 1, phase F, after the F0 acceptance)

**Status: IN PROGRESS. NOT READY.** This records each slice as it lands. The source READY manifest comes at the end, as `communication/F_SOURCE_READY.md` requires.

**Authority for this work:**
- F0 acceptance: A3-0073, `F0_ACCEPTANCE_CANDIDATE2.json` 03dcf485...
- Interface: `interfaces/v2/FREEZE.json` 7bb1d243...
- Design: `ledger/f0/A-F1-DESIGN.md` 7eed1b29.. (revision 2.2).
- Obligations: A1-0109.

Paper-derived reconstruction; synthetic, TEST-ONLY keys. Isolated Forge tests only: no services, no integrated run.

## Baseline (before any A-F1 change, HEAD d8eddf1)

- `forge test --root ledger`: 198 passed, 0 failed, exit 0. The PASS list is `baseline-198-pass-list.txt`.
- `python3 -I ledger/tools/check_mutants.py`: exit 0, all 7 E mutants detected (`baseline-check-mutants.txt`).

## Slice 1: profile carrier and mutation guards (design §1)

**Changes:**
- `ProtocolTypes.sol`:
  - `Profile.REPAIRED_F` (index 3);
  - the free function `isRepaired`;
  - `MUT_NO_GOV_ACTION_BINDING`, `MUT_NO_GOV_NONCE` and `MUT_NO_POLICY_PIN` (bits 6–8), `MUT_E_BITS`, and `MUT_ALL = (1 << 9) - 1`;
  - the shared guard `mutationsAllowed(profile, mask)`.
- The four constructor guards (TMSC:95, PSC:110, KSSC:102, ACSC:91) now call `mutationsAllowed`. Bits 0–5 are allowed in either repaired profile, bits 6–8 only in REPAIRED_F, and anything else is MALFORMED.
- The 13 profile gates of design §1 (TMSC 188/301/319/327, PSC 113/204/222/246, KSSC 105/140, ACSC 133/145/179) use `isRepaired`. Error codes are unchanged. The edit was scripted by exact line number and asserted on the expected text.

**Tests:** `test/ProfileF.t.sol`, 8 tests.
- **Red:** `slice1-red-compile-error.txt`. The new declarations do not exist, so this is a compile failure, not an assertion failure.
- **Green:** `slice1-green.txt`, 8 of 8.
- **Full suite:** 206 passed (198 + 8), exit 0. Every baseline test still passes (`comm` of the two PASS lists).
- **Mutant checker:** exit 0, all 7 E mutants still detected.
- Behaviour-level sensitivity controls for this slice are planned for the final controls script, not yet run.

What this slice does **not** do: no Governance, no TMSC hooks, no policy pin, no F reruns of the E suites. The REPAIRED_F flows are not exercised yet beyond the constructors.

## Slice 2: Governance and the TMSC hooks (design §§2–3; FL-10 and F-28 baselines)

**Changes:**
- `ProtocolTypes.sol`:
  - the `GovernanceAction` struct;
  - `GOV_ADD_AUTHORITY`/`REMOVE`/`SET_CA_ADMINS` = 1/2/3 and `GOV_MAX_ADMINS` = 8;
  - `GOVERNANCE_DOMAIN` "HMBCGovernance";
  - `GOVERNANCE_ACTION_TYPEHASH`, `hashGovernanceAction` (admins as 32-byte words) and `governanceActionDigest`.
- New `src/interfaces/IPolicyVersion.sol`, which is used in slice 3.
- New `src/Governance.sol`:
  - the constructor rejects MALFORMED and DUPLICATE_SIGNER cases;
  - public immutables: `target`, `governanceChainId`, `witnessSetVersion`, `threshold`, `maxGovernanceTtl`, and `mutations` (the full mask, A1-0105 M4);
  - `witnesses()` (storage) and `governanceNonce`;
  - `execute` runs the design §2 steps 1–9 in order;
  - bit 6 hashes `action := 0` and dispatches the submitted action; bit 7 neither checks nor advances the nonce;
  - `GovernanceApplied`.
- `TMSC.sol`:
  - `governance`, `removedAuthority` (the tombstone) and `_caAdminList`, with the `caAdmins(root)` view filled by the constructor and by governance;
  - `wireGovernance`, REPAIRED_F only, otherwise WRONG_PROFILE;
  - `_checkWiring` requires governance under REPAIRED_F;
  - `govAddAuthority`, `govRemoveAuthority` and `govSetCaAdmins`. The order is whenSealed, then WRONG_PROFILE, then UNAUTHORIZED_CALLER, then the preconditions. Each advances `authEpoch`, writes the LSC entry `(keccak(root, action, "HMBC.governance"), abi.encode(action, nonce, root, admins, governance))` and emits its event.
- **Choice made in this slice** (the design names both codes but not their order): the profile check precedes the caller check, so WRONG_PROFILE is reachable on an E TMSC. `wireGovernance` also refuses non-F profiles.
- **Fixture** (`test/utils/Fixture.sol`, design §7.3–7.4, assertion-preserving):
  - `witnessSetVersion()`, `threshold()` and `witnessAddresses()` return 1, 1 and one witness in E, and 2, 3 and witness-1..4 in F;
  - Governance is deployed and wired under REPAIRED_F;
  - `witnessSigs` returns the sorted q-of-4 quorum when the F fixture signs as `witnessPk`;
  - the two Fixture equality branches use `isRepaired`.
- `script/FixtureConfig.sol`: the F constants (version 2, four witnesses, q3, governance TTL 120) and `witnessLabel`.

**Tests:** `test/Governance.t.sol`, 30 tests. They cover:
- the getters and constructor;
- the wiring rule;
- the three actions with state, LSC and events;
- the tombstone and the TMSC preconditions;
- every row of the §2 check table and its precedence;
- the FL-10 baselines: SET-as-REMOVE gives BAD_SIGNATURE with no state change, and a SET replay gives REPLAY with no second effect, with N+1 as the positive control;
- the R3 rollback with no events;
- the log binding;
- the three F-28 branches: the PBC gives UNKNOWN_AUTHORITY at once; before the barrier the DBC still grants; after the new-epoch checkpoint it gives STALE_STATE.

**Runs:**
- **Red:** `slice2-red.txt`, against stubs (execute and the mutators revert NOT_IMPLEMENTED_IN_PHASE, no constructor validation): 1 passed (the getters) and 29 failed.
- **First green run:** `slice2-green-run1-test-alias-bug.txt`, 29 of 30. The failure was **my test's bug**: `GovernanceAction memory asRemove = set;` aliases memory, so the positive control submitted REMOVE with SET signatures. The test now builds a separate struct; the contract did not change.
- **Green:** `slice2-green.txt`, 30 of 30.
- **Full suite:** 236 passed (198 + 8 + 30), exit 0, and every baseline test still passes.
- **Mutant checker:** exit 0.

Limits: the bit 6 and 7 **mutant** runs (as opposed to their baselines) are not written yet. There is no policy pin yet (slice 3) and no F reruns of the E suites yet (slice 4).

## Slice 3: the KSSC policy pin and q-of-4 on every signed path (design §§4 and 7)

**Change:** `KSSC.acceptState`. After the keyEpoch check and before the monotonicity block, a REPAIRED_F checkpoint whose `policyVersion` differs from `IPolicyVersion(acsc).policyVersion()` is refused STALE_STATE, unless bit 8 (`MUT_NO_POLICY_PIN`) is set. There is no constructor or ABI change. E profiles are unaffected: `test_F0_PoisonCheckpointPolicyVersionBlocksTheDbc` still characterizes the E gap.

**Tests:** `test/Quorum.t.sol`, 9 tests. With q = 3 of 4 on all three witness-signed paths (checkpoint at KSSC, decision at ACSC, receipt at PSC), each path:
- accepts any three of the four witnesses;
- rejects two (INSUFFICIENT_QUORUM), a duplicate (DUPLICATE_SIGNER), an outsider among three valid signatures (BAD_SIGNATURE) and an unsorted list (MALFORMED).

Also covered:
- four of four accepted;
- a single witness cannot poison;
- the E witness-set version gives STALE_STATE;
- the P-WIT-4 analogue: a foreign policy version, higher or lower, gives STALE_STATE, with the DBC's own version as the positive control.

**Runs:**
- **Red:** `slice3-red.txt`, 8 passed and 1 failed (the pin test). The quorum cases are characterization of the reused QuorumLib and passed on their first run; they are not presented as red-green.
- **Green:** `slice3-green.txt`, 9 of 9.
- **Full suite:** 245 passed, exit 0, and every baseline test still passes.
- **Mutant checker:** exit 0.

## Slice 4: the E property suites rerun under REPAIRED_F (design §7)

**Assertion-preserving E test edits.** No assertion, expected code or message text changed:
- `virtual` on `profile()` in the 8 repaired-e contracts: Audit:132 and :155, AccessFlow:318, DecisionBinding:93, Freshness:176, OutcomeEvidence:27, Policy:52, TrustAnchors:177.
- 7 equality branches become `isRepaired(profile())`: Audit:54/57, AccessFlow:50/208/258, Freshness:27, TrustAnchors:110. The two Fixture branches were changed in slice 2.
- OutcomeEvidence:133 uses `witnessSetVersion()` instead of the constant.
- **Beyond the design's site list:**
  - 4 import lines (`isRepaired`), needed to compile;
  - **OutcomeEvidence:74**: the literal `2`, meaning "another witness-set version", becomes `witnessSetVersion() + 1`. That is still 2 under E, so the E test is byte-for-byte equivalent in effect.

  My design §7.3 site list missed that literal. The first F rerun exposed it (`slice4-freruns-run1-version-literal.txt`): under F the deployment's version **is** 2, so the "foreign" receipt was valid and correctly accepted. This was a fixture constant, not a contract regression.

**Equivalence:** after the E edits and before any F subclass, the full PASS list is **identical** to slice 3's: 245 entries (`slice4-e-edits-245-pass-list.txt`).

**F reruns:** `test/RepairedF.t.sol` holds 8 `*RepairedFTest` subclasses, each changing only `profile()` to REPAIRED_F.
- **First run:** 70 of 71. The one failure is the version literal explained above.
- **After the literal fix:** 71 of 71 (`slice4-freruns.txt`).
- **Per suite** (`slice4-e-vs-f-suites.txt`), every F suite has the **identical** test names and PASS results as its E base: Audit 5, AuditHashOnly 4, AccessFlow 21, DecisionBinding 10, Freshness 10, OutcomeEvidence 7, Policy 2, TrustAnchors 12.
- This confirms the design §7.5 prediction for `test_E01_SignatureEncodings` at q = 3, which passes unchanged.
- `F0Powers` and `F0Quorum` stay E characterization and are not subclassed.

**Totals:**
- Full suite: 316 passed (245 + 71), exit 0, and every slice-3 test still passes.
- Mutant checker: exit 0.

## Slice 5: the F mutants and the mutant-f-q2 configuration (design §6)

**Pre-registration.** The predicted detecting tests for bits 6, 7 and 8 and for mutant-f-q2 were written into `tools/check_mutants.py` (`EXPECTED`). They were committed and pushed as **8f5206f (14:53 IST), before any F mutant suite existed**. The same commit made `Governance.t.sol` mutant-robust without changing its baseline (still 30 of 30):
- the getters compare with the fixture's `threshold()` and `mutations()`;
- the bit-6 mutant fixture's witnesses sign the action := 0 struct, as design §6 specifies;
- the event test expects the struct hash that was signed;
- `QuorumFailures` uses three explicit witnesses.

**Suites** (`test-mutants/Mutants.t.sol`, subclassing the A-F1 property suites):

| Suite | Configuration | Detecting tests (all as pre-registered) | Demonstration (expected PASS) |
|---|---|---|---|
| MutantNoGovActionBindingTest | GovernanceTest, bit 6 | SET-as-REMOVE baseline | a SET(H1, []) certificate removes H1 (before/after state) |
| MutantNoGovNonceTest | GovernanceTest, bit 7 | replay; stale nonce or gap; nonce-before-expiry order; three "nonce advanced" assertions | replay repeats `authEpoch`, LSC entry and `CaAdminsSet`; nonce stays 0 |
| MutantNoPolicyPinTest | QuorumTest, bit 8 | P-WIT-4 analogue | a foreign-policy checkpoint is accepted; decisions on it give STALE_STATE; the honest checkpoint is then refused (DBC blocked) |
| MutantFQ2QuorumTest | QuorumTest, threshold 2 (mask 0) | the three two-signature rejection cases | two signatures accepted at KSSC; KSSC and PSC thresholds are 2 |
| MutantFQ2GovernanceTest | GovernanceTest, threshold 2 | QuorumFailures | two signatures execute governance |

**Results:**
- `python3 -I ledger/tools/check_mutants.py`, **first run: exit 0**, all 12 mutants (7 E and 5 F) detected, with no missed and no unexpected failures; the unmutated base suites have no failures (`slice5-check-mutants.txt`, `slice5-mutants-report.json`).
- The mutants profile has 22 failures, every one an expected detection (10 E and 12 F). All 5 demonstration tests pass (`slice5-mutant-demonstrations.txt`).
- Normal profile: 316 of 316, exit 0.
