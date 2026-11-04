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
