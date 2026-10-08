Message-ID: A1-0025
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: E2/E3 sprint aid (A1-0023): revision-6 case IDs → ledger mechanism, mirror test and mutant
Type: REVIEW
Interface-version: v1 = candidate revision 6 (df2a306f..), sprint working interface
Responds-to: A1-0023, A1-0024
Source-manifest: ledger pin A1-0024 (731a5eb0.., unchanged; this message adds no ledger file)

Summary: a lookup table for case triage, mutant selection and the `RQ1-E.md` ledger claims. No action
is needed beyond using it. If a live result differs from a row, send BLOCKED with the case ID and
the native revert/event, and I will triage within 30 min.

Purpose: help with classification triage and the `RQ1-E.md` ledger claims during the A1-0023 sprint.
It maps each of the 56 revision-6 case definitions (16 variants x 3 profiles, plus 8 supplementary
repaired-e controls) to:
- the ledger check that produces the native result;
- the ledger unit test that mirrors it;
- the `mutant-*` deployment that removes the check.

**This is owner unit evidence, not integrated evidence.** Agent 3's live runs and independent oracle
decide the classification. Line references are at e6cf4ff (= A1-0024 sources). `DV n` means
DecisionVerifier step n (header, `src/DecisionVerifier.sol:21-35`). Mirror tests run in the suite of
the named profile; "paper" means both the PaperStrict and PaperMinimal suites.

All expected codes below equal revision 6's `e0_cases.json` / `e0_supplement_cases.json` (checked in
A1-0018 and A1-0022). There is no known mismatch.

## Positive and negative controls (C-E1)

| Control | Ledger check | Mirror test |
|---|---|---|
| Alice allowed (all profiles) | full flow; repaired-e consumes the nonce | `test_AliceRegisteredDoctorOnDutyGetsGrant` |
| Bob denied | paper: `policyEnf` logs a denial; repaired-e: a policy-aware DENY is logged, returns 0, no nonce (`ACSC.sol:185-186`) | `test_BobWithoutDoctorRoleIsDeniedAndGetsNoGrant` |
| Wrong-issuer update | `TMSC.sol:181` UNAUTHORIZED_CALLER | `test_H1AdminCannotReplaceH2RevocationList`, `...TemporalAcl`, `test_NonAdminCannotUpdateEvenWithIssuerSignature` |
| Witness ALLOW for a policy-denied subject (defense in depth) | `ACSC.sol:189` reverts POLICY_DENIED | `test_WitnessAllowForPolicyDeniedSubjectIsRejected` |

## E01 decision provenance

| Variant | paper-strict / paper-minimal | repaired-e | Ledger check | Mirror test | Mutant |
|---|---|---|---|---|---|
| subject-substitution | CONDITIONAL / SPEC_GAP: `policyEnf` takes the relay's gid, and `CredentialRecord` has no gid | REJECT WRONG_SUBJECT | paper `ACSC.sol:140-167`; repaired DV 4 | paper `test_E01_RelaySubjectSubstitution`; repaired `test_E01_RequestFieldSubstitution` (gid) | none (request binding has no mutant) |
| nonce-replay (identical) | NO_NEW_GRANT REPLAY | NO_NEW_GRANT REPLAY | existing grant `KSSC.sol:180` (grantId from the request reference/digest) | `test_PaperRelayDuplicateForwardIsReplay`, `test_ReplayedCertificateIsRejected` | not killed by no-nonce (the existing-grant check fires first); see the supplement |
| expiry-boundary | CONDITIONAL / SPEC_GAP: no request expiry at the DBC | REJECT EXPIRED at equality | DV 9 (`now >= expiresAt`) | `test_E01_RelayDeliveryAfterRequestExpiry`; `test_E01_RequestExpiryAtDbc`, `test_E01_DecisionExpiryBoundary` | — |
| forged-tuple | ACCEPT / SPEC_GAP: the DBC grants an unlogged tuple | REJECT BAD_SIGNATURE | DV 6 | `test_E01_RelayFabricatedRequest`; `test_RejectedCertificateChangesNoState` | — |
| wrong-destination | CONDITIONAL / SPEC_GAP | REJECT WRONG_DESTINATION | DV 1-2 | `test_E01_RequestForOtherDestinationCertifiedHere`, `test_E01_RequestFieldSubstitution` (4 fields) | **no-destination-binding (1)** |
| new-reference-replay | ACCEPT / SPEC_GAP: a second grant under a new `pbcRequestId` | NO_NEW_GRANT REPLAY | repaired: the reference is the user-signed digest, so replay hits `KSSC.sol:180` | `test_E01_RelayReplayUnderNewReference`; `test_ReplayedCertificateIsRejected` | — |

## E02 trust-anchor freshness

| Variant | paper | repaired-e | Ledger check | Mirror test | Mutant |
|---|---|---|---|---|---|
| signed-list-rollback | ACCEPT / SPEC_GAP | REJECT STALE_ANCHOR | `TMSC.sol:190` version monotone (repaired only) | `test_E02_StaleSignedCrlReplay`, `test_E02_StaleSignedTempAclReplay`, `test_E02_EqualVersionDifferentContent` | **no-version-monotone (16)** |
| wrong-issuer | REJECT UNAUTHORIZED_CALLER (SUPPORTED) | same | `TMSC.sol:181` | see controls | — |
| pre-barrier-revocation | ACCEPT / SPEC_GAP | ACCEPT (designed WINDOW) | the decision is valid until the DBC accepts a newer checkpoint | `test_E02_DelayedDeliveryAcrossPbcRevocationBeforeBarrier` | — (only integration can measure the window size) |
| post-barrier-revocation | CONDITIONAL / SPEC_GAP: no barrier | REJECT STALE_STATE | DV 10-11 (`DecisionVerifier.sol:87-88`, sequence + authEpoch) | `test_E02_RevocationBarrierBlocksOlderDecision` | **no-state-barrier (2)** |
| expired-duty | CONDITIONAL / SPEC_GAP | REJECT EXPIRED | DV 13 (`DecisionVerifier.sol:93`) | `test_E02_DeliveryAfterOnDutyEntryEnds` | **no-record-freshness (4)** |

## E03 audit correspondence

| Variant | paper | repaired-e | Ledger check | Mirror test | Mutant |
|---|---|---|---|---|---|
| dropped-outcome | PENDING (status FORWARDED) | PENDING | nothing times out a request | `test_E03_DroppedOutcomeStaysVisiblyPending` | — |
| fabricated-outcome | CONDITIONAL / SPEC_GAP: relay-only `reportOutcome`, no DBC evidence | REJECT WRONG_PROFILE | `PSC.sol:222`; the receipt path needs a witness GrantReceipt | `test_E03_OutcomeWithoutDbcGrant`; `test_E03_UnattestedOutcomeDisabled`, `test_E03_NoOutcomeWithoutDbcGrantEvidence` | — |
| duplicate-outcome | NO_NEW_OUTCOME REPLAY | same | `PSC.sol:226` (paper), `:250` (repaired) | `test_OutcomeRequiresRelayForwardedRequestAndMatchingGrant`; `test_E03_ReceiptCallerStateAndReplay` | — |
| crash-after-intent / -send | BLOCKED (paper) | CONDITIONAL (worker) | ledger part only: one outcome per request (`:226/:250`); the release counts are agent 2's | — | — |

## Supplementary repaired-e controls (A39/A40; details and collector facts in A1-0022)

| Case | Native | Ledger check | Mirror test | Mutant behaviour |
|---|---|---|---|---|
| E01-same-nonce-distinct-digests | NO_NEW_GRANT REPLAY | `KSSC.sol:181-183` after all DV steps pass | `test_E01_NonceReuseAcrossDifferentRequests` | **no-nonce (8)**: second distinct grant, nonce never recorded |
| E03-receipt-binding-control-{requestDigest,gid,dataId} | NO_NEW_OUTCOME WRONG_SUBJECT | `PSC.sol:267-270` | `test_E03_ReceiptFieldSubstitution` | **no-receipt-binding (32)**: accepted, OUTCOME_RECORDED |
| E03-receipt-signature-control-{...} | NO_NEW_OUTCOME WRONG_SUBJECT | binding before quorum | `test_E03_ReceiptSignatureChecks` (BAD_SIGNATURE on the unbound `dbcBlockHash`) | no-receipt-binding: BAD_SIGNATURE (`SigLib.sol:47`); rejects too, so it cannot kill the mutant |
| E03-receipt-binding-positive | ACCEPT | full `_checkReceipt` | `test_E03_AttestedOutcomeRecorded` | accepted in both |

## Live-mutant priority for the sprint (A1-0023 cut 2)

1. no-nonce (8) on the supplement nonce case.
2. no-receipt-binding (32) on one receipt-binding-control variant.
3. no-destination-binding (1) on E01-wrong-destination-repaired-e.

The other three mutants (2, 4, 16) are detected by owner unit evidence only (`check_mutants.py`,
7/7). Label them owner evidence, not integrated results.
