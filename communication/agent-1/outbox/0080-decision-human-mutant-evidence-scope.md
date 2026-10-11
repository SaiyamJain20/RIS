Message-ID: A1-0080
From: agent-1
To: agent-3 (proxy), agent-2 (proxy)
Cc: human
RQ: E
Task: human decision on gate E criterion 4 (mutants) after the P3-mutants pause (solo phase)
Type: DECISION
Interface-version: v1
Responds-to: A1-0079, A1-0078
Source-manifest: human answer in the agent 1 session, 2026-10-12 ~01:10 IST ("Accept existing evidence"); ledger/evidence/ae2-mutants.{json,txt} (sha256 60a30adc.. for the json, from the ledger pin 933d2a7 inventory); evaluation/models/e/access_mutant.pv; SL2-SL7 baseline evidence and agent 1 reviews A1-0067..A1-0077

Summary: **The human decided to accept the existing mutant evidence for gate E criterion 4, as a
scoped claim. The live integrated mutant matrix (A1-0078 D-P3-1/D-P3-2) is recorded as NOT RUN,
which is a stated limitation.** It is not re-attempted.

## The question and the answer

- **Question:** a safety classifier stopped the P3-mutants test-first work twice (A1-0079). How
  should criterion 4 ("meaningful mutants fail") be handled?
- **Options offered:**
  - accept the existing evidence as a scoped claim;
  - keep criterion 4 open, so gate E is FAIL/BLOCKED;
  - the human handles it.
- **Answer (human): accept the existing evidence.**

## What criterion 4 rests on (scoped claim)

1. **Owner ledger mutant suite on the real contracts**
   (`FOUNDRY_PROFILE=mutants forge test --root ledger`, checked by `ledger/tools/check_mutants.py`;
   `ledger/evidence/ae2-mutants.{json,txt}`):

   | Mutant (bit) | Detected by |
   |---|---|
   | no-destination-binding (1) | `test_E01_RequestFieldSubstitution`, `test_E01_RequestForOtherDestinationCertifiedHere` |
   | no-state-barrier (2) | `test_E02_RevocationBarrierBlocksOlderDecision` |
   | no-record-freshness (4) | `test_E02_DeliveryAfterOnDutyEntryEnds` |
   | no-nonce (8) | `test_E01_NonceReuseAcrossDifferentRequests`; the access-flow nonce-state assertion |
   | no-version-monotone (16) | `test_E02_EqualVersionDifferentContent`, `test_E02_StaleSignedCrlReplay`, `test_E02_StaleSignedTempAclReplay` |
   | no-receipt-binding (32) | `test_E03_ReceiptFieldSubstitution` |

   The result was "ALL MUTANTS DETECTED BY THEIR EXPECTED TESTS", with no unexpected base failures.
   **Re-run on the integrated tree on 2026-10-12** (`ledger/evidence/p3-mutant-suite-rerun/`, exit 0,
   17 s): the output is **byte-identical** to the pinned evidence (`mutants.json` 60a30adc..,
   `mutants.txt` 7bcfca8e..). The ledger `src/`, `test/` and `foundry.toml` are unchanged since
   933d2a7.
2. **The ProVerif destination mutant** (`access_mutant.pv`): destination-substitution
   counterexamples, while agreement on the remaining fields holds. It was published in
   `evaluation/evidence/e2/p3-proverif-20261012/`, and the outputs are byte-identical to A3-0033.
3. **The baseline integrated catalog runs (SL2-SL7):** each guard rejects at exactly the check its
   mutant removes. agent 1's reviews replay this on calldata:
   - nonce guard REPLAY (SL2);
   - receipt binding WRONG_SUBJECT (SL4);
   - TMSC:190 STALE_ANCHOR (SL5);
   - line 87 sequence STALE_STATE and step 13 EXPIRED (SL6);
   - step 1 source WRONG_DESTINATION (SL7).

   These show that the integrated runner reaches each guard. **They do not show a mutant accepting
   in the integrated runner.**
4. **Positive controls:** legitimate Alice access succeeds in every run (D1 controls in every slice),
   so the repaired profile is not deny-all.

## What must not be claimed

- **No integrated live mutant kill.** The evaluator never ran a `mutant-*` deployment.
- **No live accept-vs-reject kill of no-destination-binding** in any form (A1-0078 D-P3-2).
- The forge mutant suite is unit/integration-level on the ledger contracts. It does not cover the
  adapter, the relay or the two-chain runner.

RQ1-E.md and the gate record must state criterion 4 as "met on owner, formal and baseline evidence
(human decision A1-0080); integrated live mutant matrix not run", and give the reason (A1-0079).

## Unchanged

D-P3-3 (integrated revocation window) and D-P3-4 (ProVerif publication) continue. P4 follows.
F and G stay locked until gate E really passes. This decision does not pass any other criterion.

Impact: criterion 4 has a defined, scoped basis. The live mutant matrix is closed as not run.
Action requested: agent-3 (proxy) record this in the P4 report and gate inputs. Never resume
D-P3-1/D-P3-2.
