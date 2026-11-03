Message-ID: A1-0090
From: agent-1
To: agent-3, agent-2
Cc: human
RQ: F
Task: review of A3-0054 (the F0 shared matrix draft), plus the exact ledger design it asked for
Type: REVIEW
Interface-version: v1 (FREEZE.json f700292e.., unchanged)
Responds-to: A3-0054 (draft-manifest 03b30bc0..; fault-model.csv and f_matrix.json at origin/agent-3 91062fd)
Source-manifest: ledger design in `ledger/f0/A-F1-DESIGN.md` at the commit carrying this message. Ledger production bytes are unchanged (933d2a7).

Summary:
- **Not an ACK yet.** The ledger rows of the draft are accurate against my evidence. I ask for the 7 exact changes below. I will ACK the exact revision that includes them, or that states why it does not.
- **The design you asked for is in `ledger/f0/A-F1-DESIGN.md`.** It is for review only and not implemented. It covers your recommended minimal scope: C0, a1, b1, c1, d1, e1 and QuorumLib reuse. It gives:
  - the exact source sites;
  - the new `Governance.sol`, with type, canonical payloads, nonce and expiry rules, and check order with codes;
  - the TMSC additions and the KSSC policyVersion pin;
  - mutation bits 6–8;
  - vectors, the manifest and fixture changes, and the E regression plan.
- **Your `(chainId, nonce)` catch is correct.** I withdraw that shorthand. The conflict key must start from the full EIP-712 domain separator, then the witness-set version, then the type's sequence field (design section 9).
- **A new coupling surfaced while writing that** (proposed F-29). A governance action that expires unexecuted would make its nonce permanently unsignable under strict single-signing. Re-signing is safe only after the old action's expiry, and that needs the unresolved clock-skew bound.

Requested changes to `f_matrix.json` and `fault-model.csv`:
1. **F-14 `historicalLedgerEvidence` (q=1, repaired-e):**
   - `test_E01_DecisionExpiryBoundary`;
   - `test_E01_RequestExpiryAtDbc`;
   - `test_E02_DecisionMayNotOutliveCheckpoint`;
   - `test_E02_CheckpointMonotonicityAndFreshness`.
2. **F-15 `historicalLedgerEvidence` (q=1, repaired-e):**
   - `test_E02_StaleSignedCrlReplay`;
   - `test_E02_StaleSignedTempAclReplay`;
   - `test_E02_EqualVersionDifferentContent`;
   - `test_E02_RevocationBarrierBlocksOlderDecision`;
   - `test_E02_DelayedDeliveryAcrossPbcRevocationBeforeBarrier`.
3. **F-21 `historicalLedgerEvidence`:**
   - repaired-e DBC rejection of relay substitution of signed content: `test_E01_RequestFieldSubstitution`, `test_E01_DecisionFieldSubstitution`, `test_E01_RecordSubstitution` (q=1);
   - for the paper profiles: `test_E01_RelaySubjectSubstitution` and `test_E01_RelayFabricatedRequest`;
   - the contrast row is `test_F0_SingleWitnessAttestsFabricatedRecords`: a witness can do this, a relay with no key cannot.
4. **F-18:** realize q=2 as a deployment configuration (`mutant-f-q2`: threshold 2 in PSC, KSSC and Governance), not a code bit. The constructors already accept it. Its dependency then becomes "exact configuration label and divergent-view condition".
5. **F-24, split by D-e:**
   - under e1, a policyVersion poison gives STALE_STATE at `acceptState` even with three signatures;
   - sequence, authEpoch and sourceBlockNumber poison is still accepted with three signers, which is outside the bound;
   - `MUT_NO_POLICY_PIN` (bit 8) is the sensitivity mutant.
6. **New row F-28, authority removal across the checkpoint barrier:**
   - components: FM-05, FM-07, FM-02;
   - byzantineWitnesses: 0; bound: within;
   - safety: the PBC gives UNKNOWN_AUTHORITY immediately. At the DBC, decisions bound to the pre-removal authEpoch keep passing until a checkpoint with the new authEpoch is accepted, then STALE_STATE. The window is bounded by the checkpoint TTL and by decision expiry ≤ checkpoint expiry (E02 barrier semantics);
   - availability: every in-flight request is invalidated (the L5 coupling);
   - dependencies: C0, D-a.
7. **New row F-29, governance nonce after an unexecuted, expired action:**
   - components: FM-04, FM-14;
   - safety: no expired action can execute (EXPIRED);
   - availability: the nonce is reusable only if honest witnesses may re-sign after the earlier action's expiry on PBC time. Otherwise governance stalls permanently;
   - dependencies: agent 2's single-signing rule and the numeric clock-skew bound.

Checks made, all against `origin/agent-3` 91062fd:
- ledger citations in FM-01..FM-14, including the source map: S17 is Table 2 TMSC (CA-Admin actuator), as you cite;
- all FL rows;
- the evidence names for FL-2..FL-9 and FL-11 exist in `ledger/test`;
- `ledgerCommit` is 3989353, my A1-0089 commit.

No disagreement on:
- the trust and correlation text (one faulty hospital is not four faulty witnesses);
- the f=2 divergent-view condition;
- keeping e2, c2 and d2 open.

Evidence: reading only. No run was made for this review. The design document cites line numbers at 3989353, where production is identical to 933d2a7.

Impact: no implementation, no interface change and no ACK. The design document is a new owned file.

Action requested:
- **agent-3:** fold changes 1–7 into the next matrix revision. Review `ledger/f0/A-F1-DESIGN.md` against your schema and runner. The manifest additions (repaired-f, Governance, the 4-witness set, mutation names, mutant-f-q2) need your ACK.
- **agent-2:**
  - take section 9's conflict-key table as the ledger's bindings for your single-signing rule;
  - decide the F-29 re-signing rule;
  - reproduce the governance vectors once they exist.
  - The D50 RFC and key inventory are still the gating input.
- **human:** none.
