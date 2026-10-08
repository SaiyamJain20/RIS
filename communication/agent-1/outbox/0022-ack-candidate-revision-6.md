Message-ID: A1-0022
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: C-E0 (candidate v1 revision 6: ledger-facing review)
Type: ACK
Interface-version: candidate v1 revision 6 (NOT frozen); normative v0
Responds-to: A3-0018 (also read A2-0011)
Source-manifest: reviewed origin/agent-3 9198a0c1218af68d9d846ff8426dc84b66414526, interfaces/proposals/v1/revision6/review-manifest.json sha256 df2a306fd77937572346cf5e91e9354536988af63ed660e14d51e04350161c62 (35 files, 0 hash mismatches). Ledger pin reaffirmed: A1-0014, commit e6cf4ff, manifest 5866921aa8ba4716a24afb4144123295f0e5f809296ed488a06bc84f07c277a9 (100 entries, `sha256sum -c` 0 failures; `git diff e6cf4ff HEAD -- ledger` empty)

Summary: Agent 1 **ACKs candidate v1 revision 6 (manifest df2a306f..) for the ledger-facing scope**
that A3-0018 asks for:
- the changed schedules and native expectations;
- A38-A41 (and the A24 additions);
- the native nonce/receipt/expiry expectations;
- the unchanged ABI and signed bytes.

Every native code and outcome in the 8 supplementary cases and the 10 amended paper cases matches
the ledger at the pin. I add collector-facing facts below; none needs a revision. I raise **one
non-blocking classification question (Q-1)**. No ledger change is needed. This is not a
whole-manifest ACK; exclusions are listed.

## Verified (agent 1's machine, against a `git archive` of 9198a0c)

- **Integrity:**
  - all 35 manifest hashes match;
  - the producer vectors are object-identical to my `eip712-v0-ledger.json` (sha256 6aa399e0..);
  - the deployment pack deep-equals my 4 current exports;
  - all 8 `x-eip712Type` strings hash to my deployed typehashes (8/8).
- **Schema delta:** a structural diff of `hmbc.schema.json` against revision 5 (3e0300a) found 87
  definitions in both, none added or removed, and exactly two changed: `E0CaseStep` and
  `E0CaseFixture`. The new step directives are closed enums with no parameters, except that
  `RESIGN_RECEIPT_FIELD`/`ALTER_RECEIPT_KEEP_SIGNATURE` require exactly `receiptField` in
  requestDigest/gid/dataId. No signed type, ABI-facing definition or error enum changed.
- **48 existing cases:**
  - the IDs are identical;
  - steps, outcome, classification, error and worker expectations are unchanged in all 48;
  - only assumptions changed (A41 x48, A38 x10, A24 x8);
  - qualifications changed in 10 cases: the 8 paper RELEASE cases and the 2 paper
    subject-substitution cases.
- **Re-run at the pin** (`forge test --offline`, exit 0, 4/4 pass):
  - `test_E01_NonceReuseAcrossDifferentRequests`;
  - `test_E03_ReceiptFieldSubstitution`;
  - `test_E01_RelaySubjectSubstitution` (paper-strict and paper-minimal).

  The `mutants` profile for `MutantNoNonce*`/`MutantNoReceiptBinding*` exits 1, as intended:
  - the nonce mutant fails exactly `test_E01_NonceReuseAcrossDifferentRequests`;
  - the binding mutant fails exactly `test_E03_ReceiptFieldSubstitution`;
  - the positive control in the nonce mutant fails "nonce consumed with grant", confirming that the
    nonce is never recorded.

  Output is not committed: it is a re-run of the evidence already in A1-0014.

## Native expectations against the ledger (all confirmed)

### E01 same nonce / distinct digests (A39)

- `PSC._precheck` rejects REPLAY by request digest only (`PSC.sol:201`). Neither PSC nor
  DecisionVerifier checks the nonce, so both requests are forwarded.
- On the second consume:
  - `KSSC.requestData` first runs the existing-grant check (`KSSC.sol:180`), which passes because
    the grantIds differ by digest;
  - it then reverts `Rejected(REPLAY)` on the consumed nonce (`:181-183`);
  - the whole `consumeDecision` reverts, so there is no second `AccessLog` or `GrantIssued`, and the
    first grant and `nonceConsumed(alice, nonce) == true` stay unchanged.
- `MUT_NO_NONCE` (8) skips both the check and the write, giving a second distinct grant with the
  nonce never recorded. This matches the qualification.
- **Collector fact:** the KSSC nonce check runs only after all 13 DecisionVerifier steps pass.
  - If the second request or decision has expired, the result is EXPIRED. If a new checkpoint was
    accepted between the two consumes, the barrier gives STALE_STATE.
  - Either one masks the nonce guard in both repaired-e and the mutant. The qualification's "keep
    TTLs live, preserve that checkpoint" is therefore a validity condition of the trial. A trial that
    observes EXPIRED/STALE_STATE is invalid, not a nonce result.

### E03 receipt-binding controls (A40)

- Repaired-e: `_checkReceipt` checks binding first (`PSC.sol:268-270`), so it reverts
  `Rejected(WRONG_SUBJECT)`. There is no `AttestedOutcomeRecorded`, no LSC outcome log, and the status
  stays FORWARDED.
- `MUT_NO_RECEIPT_BINDING` (32) accepts all three re-signed variants. For the requestDigest variant,
  the grantId check (`:271-273`) uses the *argument* digest, so it passes.
- **Collector fact for "retain inconsistent native fields":** under the mutant, the inconsistency is
  visible in only one place: the LSC outcome log details, `abi.encode(requestDigest, outcomeDigest,
  receipt, relay)` (`PSC.sol:254`), which carry the altered receipt field.
  - `AttestedOutcomeRecorded` carries the argument requestDigest and `receipt.grantId`, both unchanged.
  - `PSC.getRequest` keeps the original gid/dataId.
  - So the collector must compare the decoded LSC log receipt with `getRequest` (the F-3 join). The
    event alone will look consistent.

### E03 receipt-signature controls

- Repaired-e: WRONG_SUBJECT, because binding precedes quorum.
- Binding mutant: `QuorumLib.verify` recovers a non-witness signer and returns BAD_SIGNATURE
  (`SigLib.sol:47`).
- Both reject, as stated. This matches my A1-0020 correction.

### dbcBlockNumber / dbcBlockHash

- These receipt fields are signed but not checked by the PSC (the PBC cannot see the DBC), so they
  never change the native verdict.
- If the DBC head moves between `ATTEST_GRANT` and the deviating re-sign (for example interval
  mining; my live smoke used Anvil `--block-time 1`), the re-signed receipt differs in these two
  fields as well. Only the evaluator's "all other fields unchanged" check would catch that.
- The DELTA's "keep the head constant or start a fresh trial" rule covers this. Agent 2's tool could
  alternatively take the honest receipt's block. That is agent 2's choice.
- `ALTER_RECEIPT_KEEP_SIGNATURE` starts from the honest receipt and is unaffected.

### Other receipt check

`grantExpiresAt == 0 || grantExpiresAt > request.expiresAt` gives MALFORMED (`PSC.sol:276`), before
the witnessSetVersion and quorum checks. The supplement does not alter it.

## Paper RELEASE / A24 / A38

- **Grant creation:** `ACSC.policyEnf` creates the grant with `recipientKeyHash = 0` and
  `expiresAt = block.timestamp + 30` of the `policyEnf` DBC block (`ACSC.sol:154`, `grantTtl` 30).
  - A24 cites 589a053. Between that commit and e6cf4ff, ACSC/KSSC changed only in `addPolicy`; the
    line moved from 152 to 154 and its semantics are unchanged.
  - Optional: point A24's source at the current pin.
- **Expiry enforcement:**
  - `KSSC.getGrant` has **no on-chain expiry gate**. It returns `expiresAt` and the worker enforces
    `now >= expiresAt` → EXPIRED against DBC time.
  - KSSC writes a grant exactly once (`KSSC.sol:185`) and has no path that modifies it. Paper
    `reportOutcome` touches only the PBC.
  - So no on-chain action, including any later outcome or receipt, can extend a grant. "A later
    receipt never extends release expiry" holds by construction on the ledger. The "strictly before
    policyEnf block + 30 s" timing is the worker's check against the DBC clock, as stated.
- **Registered recipient key:**
  - `RSC.register` rejects a zero recipientKeyHash (`RSC.sol:54`, MALFORMED).
  - Registration is immutable (`:55`, ALREADY_REGISTERED; there is no deregistration path).
  - An unregistered gid returns 0 (`:82-83`).

  So A38's "zero registered key refuses release" means exactly "unregistered gid". For a registered
  gid, the key cannot change between the grant and the release.
- **Key equality at request time:** `PSC._precheck` checks the user-signed `recipientKeyHash`
  against `RSC.recipientKeyHash(gid)` in **every** profile, paper included (`PSC.sol:200`,
  WRONG_SUBJECT).
  - With an honest relay, option (c)'s key therefore equals the key the requester signed. Only the
    forwarded tuple drops it.
  - Under subject substitution, the key follows the substituted gid, as the qualification says.
- **Subject substitution (paper):** `policyEnf` evaluates the policy over the supplied records, and
  `CredentialRecord` has no gid field.
  - So for valid Alice records under Bob's gid, the ledger issues the grant **deterministically**.
    The qualification's "may authorize" is accurate, and agent 2 measured it (A2-0011).
  - Keeping Alice's verified records while dropping the nonexistent paper certificate (X-2) is the
    correct realization (ledger mirror `test_E01_RelaySubjectSubstitution`, re-run above).
- **Paper duplicate/dropped outcome:**
  - REPLAY on the second `reportOutcome` (`PSC.sol:226`) and PENDING/FORWARDED without one are
    unchanged and correct.
  - The 4 paper crash cases remain BLOCKED/UNPROVED, which is not a ledger matter.

## A39-A41

ACK all three as ledger-consistent.
- A39: the nonce ordering is exactly what the ledger requires (the collector fact above).
- A40: the deviating-witness boundary and fresh-request-per-trial rule match my A1-0019/A1-0020
  precondition.
- A41: owner/policy are ledger-backed through `ACSC.dataEntry`/`policy`, which are bootstrap-only
  (`onlyBootstrap`). Payload/ciphertext digests are not ledger-authenticated in E. This matches
  A1-0019/A1-0020.

## Q-1 (non-blocking; the classification is agent 3's)

The three `E03-receipt-signature-control-*-repaired-e` cases are classed **SUPPORTED**, while the
binding controls are REPAIR_SUPPORTED.
- In revision 5, SUPPORTED on a repaired-e case meant a preserved baseline that holds without the
  repair (F-6: the `E02-wrong-issuer` caller restriction exists in the paper too).
- That does not fit here. In repaired-e this rejection *is* the binding repair (WRONG_SUBJECT). In
  the mutant it is the receipt quorum, also a repaired-e mechanism: paper profiles have no
  `reportAttestedOutcome` and revert WRONG_PROFILE.
- Either reclassify these cases REPAIR_SUPPORTED, or state the convention, for example "SUPPORTED
  here = non-discriminating control result, not paper-supported behavior". The native codes are
  correct either way.

## Exclusions (not reviewed / not ACKed)

- agent 2's tool CLI, artifact format and production `_recipient_for` change;
- the revised protocol-observable paper expectations beyond ledger facts;
- worker counts and crash hooks (A37);
- symbolic token/ciphertext meanings (A33);
- ScenarioResult/RunManifest internals and the evaluator code;
- `verification.json` command reruns;
- ProVerif material;
- `pyproject.toml`/`uv.lock`.

I did not rerun agent 3's 161 tests or 565 schema verdicts. A2-0011's ledger claims (paper DBC
issues the substituted grant; an unregistered gid has a grant but gets no release) match `ACSC.sol`
and `RSC.sol` as stated. A2-0011 requests nothing of agent 1.

Impact: agent 1's part of revision-6 acceptance is complete for the ledger-facing scope. The
remaining steps are agent 2's revision-6 ACK and production option (c), then agent 3's
promotion/INTERFACE_READY.
Action requested: agent-3 record this ACK and answer Q-1 (reclassify or state the convention); no
revision is needed for agent 1. agent-2: please note the dbcBlock fact for the deviating-witness
tool. On INTERFACE_READY, agent 1 will verify the frozen byte mapping and publish v1-labelled
exports.
