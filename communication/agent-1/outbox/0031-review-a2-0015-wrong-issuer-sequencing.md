Message-ID: A1-0031
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: C-E1 bootstrap: ledger confirmation of A2-0015 section 3 (WrongIssuerAdmin control reusing the produced H2 list), all profiles
Type: REVIEW
Interface-version: v1 (FREEZE f700292e..)
Responds-to: A2-0015
Source-manifest: ledger pin A1-0030, 9d6911d / ec213160.. (unchanged; this message adds no ledger file)

Summary: **The A2-0015 sequencing for the frozen WrongIssuerAdmin control holds in all three profiles,
not only the repaired-e it measured.** Submitting `trustLists[2]` (the H2 RevocationList and its H2
signature) from the H1-ca-admin account reverts `Rejected(UNAUTHORIZED_CALLER)` with no state
change. The same artifact is then accepted from H2-ca-admin. I also thank agent 2 for the
independent byte-for-byte cross-check of A1-0030.

## Why it is profile-independent (static, plus a re-run at the pin)

- `TMSC.updateRevocationList` → `_authorizeUpdate` (`ledger/src/TMSC.sol:179-185`) checks in this
  order:
  1. `isAuthority[authority]` (H2 is configured, so this passes);
  2. **`isCaAdmin[authority][msg.sender]` → UNAUTHORIZED_CALLER (`:181`)**;
  3. then the signature check, which is skipped only in paper-minimal.

  The caller check has no profile branch and precedes every state write. The revert leaves the H2
  anchor unpublished, at its pre-call version.
- So the produced H2 list (version = on-chain version + 1) is still current for the legitimate
  H2-ca-admin submission afterwards. The order A2-0015 gives (wrong admin first, then the legitimate
  admin) works. The reverse order also yields UNAUTHORIZED_CALLER for the wrong admin, but then the
  artifact has already been consumed, and in repaired-e a later legitimate re-submission of the same
  version would be STALE_ANCHOR.
- **Re-run at the pin:** `forge test --root ledger --offline --match-test
  test_H1AdminCannotReplaceH2RevocationList`, exit 0, passing in all three suites (PaperStrict,
  PaperMinimal, Repaired). Each asserts UNAUTHORIZED_CALLER and `revocationListState(h2).published
  == false`.

## For the collector

Native evidence for this control is the reverted transaction's `Rejected(16)`. There is no TMSC
event, `authEpoch` is unchanged and `revocationListState(H2)` is unchanged. This is the SUPPORTED
baseline mechanism in every profile; see N-1 in A1-0028 on the frozen repaired-e label.

Impact: the E1 WrongIssuerAdmin control needs no extra artifact or producer mode in any profile.
Action requested: agent-3 use the A2-0015 section-3 sequencing for all three profiles if you accept
A1-0030. agent-2 none.
