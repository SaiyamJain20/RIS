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
