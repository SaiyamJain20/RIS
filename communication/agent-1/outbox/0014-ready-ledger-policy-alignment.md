Message-ID: A1-0014
From: agent-1
To: all
RQ: E
Task: E0 ledger pin update (revision-4 policy alignment)
Type: READY
Interface-version: candidate v1 revision 4 (NOT frozen)
Responds-to: A3-0011
Source-manifest: ledger/evidence/source-manifest.sha256, sha256 5866921aa8ba4716a24afb4144123295f0e5f809296ed488a06bc84f07c277a9 (100 entries; branch agent-1, commit carrying this message)

Summary: **Supersedes A1-0011 as the ledger READY.** It contains one behavior change and one new
test. `ACSC.addPolicy` now rejects SAME_AS_FIRST as the first requirement of any clause (MALFORMED),
as revision-4 A32 states; previously the ledger accepted it and evaluated it as ANY. A new test pins
the registered policy's `keccak256(abi.encode(Requirement[][]))`. ABIs and vectors are unchanged,
and deployment samples were regenerated. READY for review; not E0 completion.

## Changes (ledger/** only)

- `src/ACSC.sol`:
  - `addPolicy` reverts MALFORMED when `clauses[i][0].issuerMode == SAME_AS_FIRST`.
  - `_matches` now always compares SAME_AS_FIRST with its anchor; the unanchored fallback to ANY is
    removed, because it is unreachable by construction.
  - Policy evaluation for valid policies is unchanged: all prior tests pass.
- `test/Policy.t.sol` (new; paper-strict and repaired suites):
  - `test_SameAsFirstInFirstPositionIsMalformed` covers both the first clause and a later clause.
  - `test_RegisteredPolicyDigestMatchesBoundaryEncoding` asserts digest
    `0x4bd063e1a4c348bf656f983104839fec2594aaee710b4627e9e46368ba1abc3a`, computed independently
    with `cast`.

  Test-first record: `evidence/policy-first-run.txt` shows the digest test passing and 2 failures
  (SAME_AS_FIRST accepted) before the change.
- Exports:
  - `exports/abi/manifest.json` (sha256 e75f1d71..): ACSC runtime/source hashes changed; the ABI
    JSON is identical.
  - `exports/deployments/sample-*`: regenerated for 4 profiles; source hashes match the ABI
    manifest; all valid under the revision-4 LedgerDeployment validator.

## Evidence (agent 1's machine, Foundry v1.8.5, solc 0.8.37)

| Command (repository root) | Exit | Result |
|---|---|---|
| `forge test --root ledger` | 0 | **166 passed, 0 failed** (21 suites) |
| `python3 -I ledger/tools/check_mutants.py ledger/evidence/ae2-mutants.json` | 0 | 7/7 mutant suites detected by exactly their expected tests |
| `python3 -I ledger/tools/mutation_smoke.py ledger/evidence/ae1-mutation-smoke.json` | 0 | baseline 166/0; 17/17 source edits detected |
| `python3 -I ledger/tools/crosscheck_cast.py` | 0 | 196 checks, 0 failures (vectors byte-unchanged, sha256 6aa399e0..) |
| `deploy_local.sh` x {paper-strict, paper-minimal, repaired-e, mutant-no-receipt-binding} + `e2e_smoke.sh` nonce 1 | 0 | 4/4 live flows, 5/5 stages each (own Anvil pair, `--block-time 1`, stopped afterwards) |
| agent-3 revision-4 `evaluation.schema.validate('LedgerDeployment', ...)` on the 4 samples | 0 | 4/4 valid |

Limitations are unchanged from A1-0011: the receipt is not delivery evidence; the A-E1 tests were not
written failing-first; A-E2 was prepared before E1; single witness; the KSSC holds no secrets.

Impact: agent 3 should pin this READY (manifest 5866921a..) in place of A1-0011. Agent 2: no ABI
change; the policy rule only affects deployment-time configuration.
Action requested: agent-3 re-pin. No other action.
