Message-ID: A1-0021
From: agent-1
To: agent-2, agent-3
RQ: E
Task: C-E0 (A2-0010 X-1: paper-grant facts and the paper-mode release decision)
Type: REVIEW
Interface-version: candidate v1 revision 5 + supplement revision 2 (NOT frozen)
Responds-to: A2-0010
Source-manifest: ledger pin A1-0014 / e6cf4ff / manifest 5866921a.. (unchanged)

Summary: **Confirmed: the paper-grant facts in X-1 match the ledger as intended.** For X-1 I
recommend a third option, **(c)**, which is closer to HMBC than (a) or (b). In paper mode the worker
binds the response to the requesting GID's **registered** recipient key, read from the PBC
(`RSC.recipientKeyHash(grant.gid)`). That mirrors III-D3: the PSC encrypts the DBC response "to the
user, encrypted with the user's public key". It makes the 8 cases observable without an unbound
release. The decision itself is agent 3's. No ledger change is needed for any option.

## Facts (ledger at e6cf4ff)

- `ACSC.policyEnf` (paper profiles, relay-only) creates the grant with
  `KSSC.GrantParams(fwd.pbcRequestId, fwd.dataId, fwd.gid, keyEpoch 0, uint64(block.timestamp) + grantTtl, recipientKeyHash = bytes32(0), consumeNonce false, nonce 0)`
  (`ledger/src/ACSC.sol:154`). `grantTtl = 30` (`script/FixtureConfig.sol:15`).
- Grant expiry is **30 s after the DBC block that includes `policyEnf`**, in DBC time. It is not
  derived from the request's expiresAt. Fill A1-0002 C21 = A24.
- The paper tuple carries no recipient (Fig. 6 step 4), so `recipientKeyHash = 0` is deliberate. The
  grant's `gid` is the **relay-asserted** forwarded GID; in E01 subject substitution it can differ
  from the requester.
- `RSC.recipientKeyHash(gid)` (PBC, view) returns the value the GID itself signed at registration
  (A35 convention).

## X-1 options, from the ledger/source side

- **(a) BLOCKED/out of scope:** honest but loses 8 observable cases. (The crash cases would be
  BLOCKED for two reasons.)
- **(b) recipientKeyHash 0, unverifiable recipient:** observable, but it releases a response bound
  to nobody. The paper does not say that: III-D3 encrypts the response to the user.
- **(c) recommended:** the paper-mode worker binds the response to `RSC.recipientKeyHash(grant.gid)`
  read from the PBC, and finish_decryption verifies against that.
  - This is the reconstruction of III-D3's PBC-side encryption to the user's key, and it keeps the
    gap visible: the binding follows the **relay-asserted** grant gid, so in
    `E01-subject-substitution-paper-*` the response is bound to the substituted subject. That is
    exactly the SPEC_GAP E01 records, with no new hidden assumption.
  - Record it as a fill: "paper-mode response recipient = PBC-registered key of the grant's gid
    (III-D3); the DBC grant itself carries none (C21/A24)."
  - Unregistered gid: the worker refuses (WRONG_SUBJECT), as today. A relay that fabricates a tuple
    for an unregistered subject therefore gets a grant but no release. This is consistent with
    `E01-forged-tuple-paper-*` expecting a grant (DBC_AUTHORIZED), not a release.
- With (c) or (b): the paper dropped/duplicate-outcome and crash schedules must RELEASE within 30 s
  of the `policyEnf` block, per the facts above.

## X-2 / X-3

X-2: agreed. Paper profiles have no decision certificate; the paper realization substitutes `gid` in
the relay's `ForwardedRequest` (ledger mirror: `test_E01_RelaySubjectSubstitution`). X-3: consistent
with the ledger.

## Also noted from A2-0010

- Your measured supplement outcomes match the ledger and my mirrors. One fact you observed is ledger
  behavior and correct: in `mutant-no-nonce` the nonce is never *recorded*, not just unchecked.
  `KSSC.requestData` skips both the check and the write under MUT_NO_NONCE (`if (p.consumeNonce &&
  mutations & MUT_NO_NONCE == 0)`), exactly as designed for that mutant.
- The witness operations answering WRONG_PROFILE on paper deployments matches the ledger. Paper
  `KSSC.acceptState` reverts WRONG_PROFILE, and paper PSC has no attested-outcome path.

Evidence: `ledger/src/ACSC.sol:154`, `script/FixtureConfig.sol:15`, `ledger/src/RSC.sol:82`, KSSC
`requestData`; HMBC2020 III-D3 (PDF p.10: "the PSC will send the response to: i) the user, encrypted
with the user's public key"). Static review only.
Impact: X-1's decision is agent 3's. Option (c) needs only agent-2 worker logic and a fill/assumption
row, with no interface field change.
Action requested: agent-3 choose (a)/(b)/(c) and record the fill. agent-2 tell me if (c) conflicts
with your worker's evidence model.
