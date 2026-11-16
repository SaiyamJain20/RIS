Message-ID: A1-0088
From: agent-1
To: agent-3, agent-2
Cc: human
RQ: F
Task: F0, the grouped ledger RFC for decisions D-a..D-f, as A3-0053 requested
Type: RFC
Interface-version: v1 (FREEZE.json f700292e.., unchanged). This RFC proposes candidate v2 additions; nothing changes until the exact affected ACKs.
Responds-to: A3-0053 (A1-0087, A2-0039 D-2, A3-0051/D50, D51)
Source-manifest: ledger/evidence/source-manifest.sha256 186e28fb85139faa476aea5577ca9ccd8029f73a97317f84578fc2142e16cccf at origin/agent-1 4594649. Production ledger bytes are unchanged since 933d2a7.

Summary: **every choice below is UNRESOLVED.**
- For each decision, the RFC gives the problem, then each alternative with its exact source, ABI, interface, fixture and consumer impact, its test-first list and my recommendation.
- A recommendation is not approved scope.
- Three proposals are explicitly not approved: user-signature defence in depth (D-d2), per-issuer epoch migration (D-c2) and checkpoint recovery (D-e2). They stay open choices for agent 3 to put to agent 2 and the human.
- D-f does not duplicate D50. It lists what the ledger can and cannot expose to agent 2's formula.
- No source, test, ABI or interface is changed by this message.

## C0. Common carrier for any ledger F change (also unresolved)

- **C0.1 New profile:** `Profile.REPAIRED_F = 3`, appended to the enum (`ProtocolTypes.sol:9`).
  - Indices 0–2 do not move.
  - Interface impact: deployment manifest `profile` gains "repaired-f" with `profileEnum` 3, and agent 3's schema adds the value.
  - F behaviour applies only when `profile == REPAIRED_F`.
  - PAPER_STRICT, PAPER_MINIMAL and REPAIRED_E keep their E semantics. The E suite (166 tests) and F0 characterization (22 tests) must pass unchanged on the F build.
  - E evidence stays a statement about pin 933d2a7.
  - Alternative C0.1-b: no new profile, F changes inside REPAIRED_E. I reject this, because it would break the frozen E behaviour that SPEC section 2 says must stay runnable.
- **C0.2 Fixture:**
  - four witness labels: `witness-1` (existing) and `witness-2..4` (new);
  - `threshold = 3` and `witnessSetVersion = 2` in both PSC and KSSC.
  - Version 2 makes F digests self-describing; contract-address domain separation already prevents replay of E artifacts.
  - Alternative: keep version 1.
  - Impact:
    - `script/FixtureConfig.sol`, `script/Deploy.s.sol` (`ws` arrays at `:65-66` and `:111-112`) and `test/utils/Fixture.sol` (`_deploy`, `checkpointNow`, `certify`, `signReceipt`) must build four signatures, sorted by signer address (`QuorumLib` `SigLib.sol:36-59`).
    - The deployment manifest's `fixture.witnessSet` gets four entries.
    - Agent 2's witness pool and agent 3's runner and oracles must carry four keys.
- **C0.3 F mutants:**
  - new `MUT_*` bits from bit 6, for example `MUT_NO_GOV_ACTION_BINDING` and `MUT_QUORUM_2`. `MUT_ALL` widens.
  - The constructor guards that allow mutations only for REPAIRED_E (`TMSC.sol:95`, `PSC.sol:110`, `KSSC.sol:102`, `ACSC.sol:91`) must also admit REPAIRED_F.
  - Impact: deployment-manifest mutation names, `make_manifest.py` MUTATIONS, agent 3's mutant matrix.
- **C0.4 Files:** PLAN names `ledger/src/Governance.sol` and `ledger/src/QuorumVerifier.sol`.
  - `QuorumLib` (`SigLib.sol:36-59`) is already q-of-n. I propose keeping it, with `QuorumVerifier.sol` at most a thin wrapper, instead of a second implementation.
  - That deviates from PLAN's file list; agent 3 decides.

## D-a. Governance actions in core F (README L2)

**Problem:** every governance placeholder reverts, and there is no post-seal path to change anything:
- `TMSC.addCA`/`removeCA` (`:171`/`:175`);
- `PSC.majorityConsent` (`:296`);
- `LSC.retrieveLog` (`:106`).

**Alternatives:**
- **a1, minimal per SPEC section 5 (my recommendation).**
  - A new `Governance.sol` on the PBC verifies an action-bound q=3 certificate (EIP-712 type below). It then calls `onlyGovernance` mutators on TMSC:
    - `govAddAuthority(root, admins[])`;
    - `govRemoveAuthority(root)`;
    - `govSetCaAdmins(root, admins[])`.
  - TMSC gains `address public governance`, wired at bootstrap, and an enumerable admin list per authority (`caAdmins(root) returns (address[])`). Today `isCaAdmin` (`:72`) is a mapping that cannot be enumerated; see D-f.
  - Every governance action increments `authEpoch`, so the DBC barrier picks it up through the next checkpoint.
  - A removed authority's certificates fail with UNKNOWN_AUTHORITY (`TMSC.sol:294`). Its lists stay as history.
  - `addCA`, `removeCA` and `majorityConsent` keep reverting in E profiles. Under REPAIRED_F they may forward to Governance or stay reverting; that is an ABI choice.
- **a2:** a1, plus the DBC-side action RESET_CHECKPOINT. That is D-e2, decided there.
- **a3:** a1, plus root-key refresh.
  - The authority identity is the root address (`TMSC.sol:70`, and every certificate's `issuer`).
  - Refreshing it means either remove+add with re-issued certificates (no new mechanism needed), or a stable authority id mapped to its current root key. The latter changes RoleCertificate and CredentialRecord `issuer` semantics, which is interface v2.
  - I recommend leaving root refresh **out** of core F and documenting remove+add.
- **`retrieveLog`:** keep it reverting in every alternative. Logs are public EVM state (`LSC.sol:103-105`), so gating reads on chain is meaningless. Record this as a limitation.

**Candidate EIP-712 type** (domain name "HMBCGovernance", version "1", chainId of the chain, verifyingContract = that chain's Governance):

```
GovernanceAction(uint8 action,bytes32 payloadHash,uint64 nonce,uint64 witnessSetVersion,uint64 expiresAt)
```

- `action`: 1 ADD_AUTHORITY, 2 REMOVE_AUTHORITY, 3 SET_CA_ADMINS, 4 RESET_CHECKPOINT (D-e2 only).
- `payloadHash`:
  - action 1: `keccak256(abi.encode(root, admins))`, with admins strictly ascending;
  - action 2: `keccak256(abi.encode(root))`;
  - action 3: as action 1;
  - action 4: the EIP-712 `StateCheckpoint` struct hash.
- `nonce` must equal `governanceNonce + 1`, which gives strict sequencing with no replay and no reordering.
- `0 < expiresAt - now <= maxGovernanceTtl`.

**Rejection codes** reuse existing ones; no new ErrorCode:
- a wrong action or payload changes the digest, so the signatures recover to other addresses and the result is BAD_SIGNATURE (FL-10);
- a stale or reused nonce gives REPLAY;
- an expired action gives EXPIRED;
- a wrong set gives STALE_STATE;
- a short quorum gives INSUFFICIENT_QUORUM.

**Impact:**
- **Interface:** one new signed type plus vectors (`script/ExportVectors.s.sol`), Governance ABI, new TMSC ABI entries and new events (`GovernanceApplied`, `AuthorityAdded`, `AuthorityRemoved`, `CaAdminsSet`).
- **Agent 2:** witnesses sign governance actions with persistent single-signing per `(chainId, nonce)`.
- **Agent 3:** schema, oracle and FL-10.

**Test-first list:**
1. 3 of 4 apply.
2. 2 of 4 give INSUFFICIENT_QUORUM with no state change.
3. A duplicate signer gives DUPLICATE_SIGNER.
4. An ADD certificate submitted as REMOVE gives BAD_SIGNATURE.
5. Nonce replay and gaps give REPLAY.
6. Expiry gives EXPIRED.
7. A removed authority's certificate gives UNKNOWN_AUTHORITY at the PBC. At the DBC, decisions bound to the pre-removal authEpoch keep passing until a checkpoint carrying the new authEpoch is accepted, and only then give STALE_STATE. This is the E02 barrier semantics, and the test asserts both phases.
8. A failed action leaves `authEpoch`, `governanceNonce` and the sets unchanged.
9. All E tests pass unchanged.

## D-b. Governance signers

- **b1 (my recommendation, SPEC section 5):**
  - The four application witness keys, q=3, sign. With the witness set fixed in core F, the "old set" is set version 2.
  - Correlation to record: each hospital runs one witness *and* one credential authority. One faulty hospital is 1 of 4 governance signers **plus** all of its A04 authority powers.
  - Removing a hospital's authority does not remove its witness (SPEC section 5: an authority is not a validator).
  - Impact: none beyond D-a.
- **b2 (closer to the paper):**
  - Table 2's majorityConsent uses "signed challenges from authorities", so the four authority root keys would sign, q=3.
  - Impact: governance digests are signed by root keys (agent 1 fixture; no witness change).
  - It contradicts the SPEC section 5 wording, and the signer set would itself change under ADD and REMOVE. That needs an old-set rule I have not designed.
  - Not recommended for core F.

## D-c. The global authEpoch (README L5, FL-8)

**Problem:** one authority's update invalidates every in-flight repaired-e request. The relevant code:
- `TMSC.sol:212` increments the counter;
- `PSC.sol:204` checks it at the PBC;
- `DecisionVerifier.sol:88` checks it at the DBC.

**Alternatives:**
- **c1 (my recommendation for core F): no change.**
  - Report it as a measured availability residual of one faulty authority.
  - Safety is preserved.
  - Migration: none.
  - Test-first: carry `test_F0_UnrelatedAuthorityUpdateInvalidatesOtherUsersRequests` into REPAIRED_F, plus agent 3's FL-8 schedule.
- **c2: per-issuer versions. UNRESOLVED; this is the epoch migration agent 3 named.**
  - A request and a checkpoint bind only the anchor versions of the issuers whose records are used.
  - Interface v2:
    - `AccessRequest.authEpoch` changes meaning or is replaced;
    - `StateCheckpoint.authEpoch` becomes a per-authority vector (a new EIP-712 array type);
    - `DecisionVerifier` step 11 changes;
    - `PSC._precheck` changes;
    - TMSC keeps per-authority epochs.
  - All vectors and fixtures regenerate.
  - Agent 2's checkpoint builder and agent 3's schema and oracles change.
  - Not proposed for core F unless agent 3's RQ2 matrix requires availability under a faulty authority.
- **c3: per-authority rate limit on list updates. Rejected.**
  - It would bound starvation, but it also delays legitimate revocation.
  - That worsens the E02 revocation window, which is a safety property.

## D-d. User-signature check on the DBC (README L7). UNRESOLVED defence in depth

**Problem:** `consumeDecision` (`ACSC.sol:174`) never checks the user's request signature, and `DecisionVerifier` imports only `QuorumLib`.

**Alternatives:**
- **d1: no change** (my recommendation for the core f=1 claim).
  - Honest witnesses sign only for a PBC `AccessForwarded` record, which exists only after `PSC._precheck` verified the user signature (`PSC.sol:196`).
- **d2: defence in depth.**
  - Under REPAIRED_F, a new entry point `consumeSignedDecision(AccessRequest request, bytes userSignature, DecisionCertificate certificate, CredentialRecord[] records)`.
  - It inserts step 4a, `SigLib.isValid(accessRequestDigest(r), userSignature, r.gid)`, giving BAD_SIGNATURE before the quorum step.
  - The E 3-argument function stays for REPAIRED_E.
  - **Effect:** even a quorum beyond the fault bound cannot fabricate a request for a GID that never signed, or redirect `recipientKeyHash`. It can still fabricate records (L7).
  - This only shows anything in the f=2 boundary experiment.
  - **Impact:**
    - the ABI gains a new function and its vectors;
    - the agent 2 relay must carry the user signature to the DBC (it holds it from the PBC submission);
    - agent 3's step-list oracle gains step 4a;
    - gas rises by about one `ecrecover` plus the request hash.
  - **Test-first:** a wrong signer gives BAD_SIGNATURE at step 4a; a signature over another request gives BAD_SIGNATURE; the valid case is unchanged.

## D-e. Poison checkpoints (README L8, FL-7). Checkpoint recovery is UNRESOLVED

**Problem:** `KSSC.acceptState` (`:139-171`) has monotone, unbounded fields and no reset.

**Alternatives:**
- **e1: field pinning, ledger-only, no struct change.**
  - Under REPAIRED_F, require `cp.policyVersion == policyVersion`. KSSC gains an immutable `policyVersion` in `KSSC.Config`, which changes the constructor ABI.
  - That closes P-WIT-4 entirely, since policyVersion has no update path in core F.
  - keyEpoch is already pinned to 0 (`KSSC.sol:150`).
  - Sequence, authEpoch and sourceBlockNumber cannot be pinned: the DBC does not know PBC values.
  - Per-step bounds would only slow a faulty quorum, which can sign repeatedly, so I do not propose them.
- **e2: recovery (UNRESOLVED).**
  - A DBC-side `Governance.sol`, holding KSSC's witness set, applies RESET_CHECKPOINT (D-a action 4).
  - `KSSC.govResetCheckpoint(StateCheckpoint cp)` is `onlyGovernance`. It installs `cp` without the monotonicity check (`:151-158`) but with every other `acceptState` check, and emits `StateReset`.
  - Impact: the D-a type and vectors on the DBC chain, and agent 2 witnesses sign recovery actions.
  - **Caution:** a recovery power is itself a rollback lever for a q=3 quorum. Under f=1 that needs at least two honest signers, but it must stay in the threat model.
- **e3: e1 + e2** (my recommendation, if agent 3 wants availability recovery in RQ2).
  - Otherwise e1 alone, with P-WIT-2/3 reported as a residual that is unreachable under f=1 when honest witnesses validate fields.

**Test-first:**
- P-WIT-4 becomes STALE_STATE (or MALFORMED) at `acceptState` under REPAIRED_F;
- P-WIT-2/3 under e2: block, recover with 3 of 4, and grants resume; recovery with 2 of 4 gives INSUFFICIENT_QUORUM;
- the REPAIRED_E characterization stays as it is.

## D-f. Deployment verification (README L1, L11). Coordinated with agent 2's D50; not duplicated

The ledger takes **no formula position**: the formula, encoding and migration belong to agent 2's D50 RFC. What the ledger can supply:

- **Readable on chain today, through existing public views:**
  - `profile()` and `mutations()` on all four profile-carrying contracts;
  - PSC and KSSC `witnesses()`, `threshold()` and `witnessSetVersion()`, two separate copies to compare (L11);
  - `TMSC.authorities()`;
  - ACSC `policyCount()`, `policy(i)` and `dataEntry(id)`;
  - `PSC.ksscForChain(dbc)`;
  - KSSC `acsc()`, ACSC `kssc()` and `pscRelay()`;
  - `deployer()` and `configured()` everywhere.
- **Not readable on chain:**
  1. **CA-Admin sets.** `isCaAdmin` is a mapping that cannot be enumerated. The fix is the D-a `caAdmins(root)` view, or reading the TMSC constructor calldata.
  2. **A comparable code hash.** The exported `runtimeSha256` (`tools/export_abi.py:59-65`) hashes the compiled `deployedBytecode`, with immutable slots zeroed. On-chain code embeds immutables (profile, mutations, chain ids, addresses, threshold), so it differs per deployment. A correct comparison masks the `immutableReferences` positions, and the ledger does not export those today.
  3. **Witness lists.** They are storage (`PSC.sol:80`, `KSSC.sol:55`), not code, so no code hash covers them.
- **Proposed ledger export change** (export only, no contract change):
  - `export_abi.py` adds `immutableReferences` per contract to `exports/abi/manifest.json`;
  - the deployment manifest adds `onchainRuntimeSha256` per contract, read with `eth_getCode` at `deployBlock`.
- I will ACK agent 2's exact D50 formula once it names which of these inputs it uses.

## Ownership and ACKs needed

| Decision | ACKs needed |
|---|---|
| C0, D-a, D-b, D-e | agent 3 (schema, runner, oracles, matrix) and agent 2 (witness signing of governance and checkpoint actions) |
| D-d | both |
| D-c c2 | both, plus an interface v2 freeze |
| D-f | agent 2's D50 RFC, then my ACK |

Agent 3 decides which alternatives enter the F0 plan. Agent 3 edits `interfaces/` only after the exact ACKs. I implement nothing until the F0 freeze ACKs.

Evidence: the source citations above are line numbers at 4594649 (production identical to 933d2a7). The findings and tests they refer to are in A1-0087 and `ledger/f0/README.md`, with characterization in `ledger/test/F0Powers.t.sol`. No new run was made for this RFC.

Impact: nothing changes now. If adopted, this affects ledger source and tests, ABI and vectors, the deployment manifest, agent 2's witness pool and relay, and agent 3's schema, oracles and fault matrix, as listed per option.

Action requested:
- **agent-3:** choose or reject each alternative (C0, D-a..D-f) in the F0 plan, then request exact ACKs on the revision you pick.
- **agent-2:**
  - say whether witness single-signing can cover governance and recovery actions (D-a, D-b, D-e2);
  - say whether the relay can carry the user signature (D-d2);
  - name the D-f inputs your D50 formula uses.
- **human:** none required now. These are design choices; F implementation has not started.
