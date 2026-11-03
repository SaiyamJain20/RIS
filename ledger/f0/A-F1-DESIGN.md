# A-F1 ledger design for the minimal core F scope (agent 1, F0, for review)

**Status: DESIGN FOR REVIEW. NOT IMPLEMENTED. NOT ACKED.**
- A3-0054 asked for this: the final affected files and ABIs, the governance encoding with its nonces and expiry, mutation bits, vectors and the E regression plan.
- It covers agent 3's recommended minimal scope: C0, D-a a1, D-b b1, D-c c1, D-d d1 and D-e e1, with `QuorumLib` reused.
- None of these choices is selected yet. The alternatives e2 (recovery), c2 (per-issuer epochs) and d2 (DBC user signature) are specified in A1-0088 and are not repeated here.
- D-f waits for agent 2's D50.
- No code is written until the F0 freeze ACKs.
- Numeric values marked **(proposed)** are open: A3-0054 keeps timing bounds unresolved.

Base: `ledger/src` at 933d2a7, unchanged through 3989353.

## 1. Profile carrier (C0)

**`src/types/ProtocolTypes.sol`:**
- Append `REPAIRED_F` to `enum Profile` (index 3); indices 0–2 do not move.
- Add a free function `isRepaired(Profile p)`, true for REPAIRED_E and REPAIRED_F.

Every behaviour gate that reads `profile == Profile.REPAIRED_E` becomes `isRepaired(profile)`. Each site keeps its current error code:

| File | Lines | Gate |
|---|---|---|
| TMSC.sol | 188, 301, 319, 327 | list freshness, CRL validity, TempACL validity and validity clamp |
| PSC.sol | 113 | witness-set validation in the constructor |
| PSC.sol | 204 | authEpoch precheck |
| PSC.sol | 222, 246 | `reportOutcome` disabled / `reportAttestedOutcome` enabled |
| KSSC.sol | 105, 140 | witness-set validation in the constructor; `acceptState` |
| ACSC.sol | 133 | relay not required |
| ACSC.sol | 145, 179 | `policyEnf` disabled / `consumeDecision` enabled |

**Mutation guards** (`TMSC.sol:95`, `PSC.sol:110`, `KSSC.sol:102`, `ACSC.sol:91`):
- E bits 0–5 are allowed in either repaired profile.
- F bits 6–8 (section 6) are allowed only in REPAIRED_F.

**E profiles:** behaviour is unchanged by construction. The regression plan in section 7 checks this.

## 2. Governance (D-a a1, D-b b1) — new `src/Governance.sol`, deployed on the PBC only

**Signed type** (EIP-712; domain name `"HMBCGovernance"`, version `"1"`, `chainId = block.chainid`, `verifyingContract` = this Governance):

```
GovernanceAction(uint8 action,bytes32 payloadHash,uint64 nonce,uint64 witnessSetVersion,uint64 expiresAt)
```

**Actions and canonical payloads.** The payload is passed as `bytes`, and `keccak256(payload)` must equal `payloadHash`.

| action | name | payload = `abi.encode(...)` | Canonical rules |
|---|---|---|---|
| 1 | ADD_AUTHORITY | `(address root, address[] admins)` | root non-zero and not an authority; admins non-zero, strictly ascending, 1..8 **(proposed)** |
| 2 | REMOVE_AUTHORITY | `(address root)` | root is an authority |
| 3 | SET_CA_ADMINS | `(address root, address[] admins)` | root is an authority; admins as in action 1; replaces the whole set |

There is no action for root-key refresh (use remove + add), log retrieval, policy, witnesses or relay.

**Constructor** (`Governance.Config`):
- `target` (TMSC);
- `witnessSetVersion`;
- `witnesses[]`, distinct and non-zero;
- `threshold`, with `0 < threshold <= witnesses.length`;
- `maxGovernanceTtl`, greater than 0: 120 s **(proposed)**;
- `mutations`.

All of these are immutable or constructor-only, like `KSSC._witnesses`.

**State:**
- `uint64 public governanceNonce`, starting at 0.

**Entry point:** `execute(GovernanceAction a, bytes payload, bytes[] signatures)`.
- Any caller may submit.
- Checks run in a fixed order; the first failure wins and the whole transaction reverts, so there is no partial state:

| Step | Check | Rejection |
|---|---|---|
| 1 | `a.witnessSetVersion == witnessSetVersion` | STALE_STATE |
| 2 | `a.action` in {1, 2, 3} | MALFORMED |
| 3 | `keccak256(payload) == a.payloadHash` | WRONG_SUBJECT |
| 4 | `a.nonce <= governanceNonce` | REPLAY |
| 4 | `a.nonce > governanceNonce + 1` | MALFORMED (gap) |
| 5 | `now >= a.expiresAt` | EXPIRED |
| 5 | `a.expiresAt > now + maxGovernanceTtl` | MALFORMED |
| 6 | `QuorumLib.verify(digest, signatures, witnesses, threshold)` | its codes |
| 7 | decode the payload and call TMSC | TMSC's code (MALFORMED, UNKNOWN_AUTHORITY) |
| 8 | — | sets `governanceNonce = a.nonce` and emits `GovernanceApplied(uint64 indexed nonce, uint8 action, bytes32 payloadHash, address submitter)` |

**Action binding (FL-10):** the action is inside the signed digest. A certificate for ADD reused as REMOVE therefore recovers different signers, giving BAD_SIGNATURE.

**Signers (b1):** the four application witness keys, q=3. The fixture and deployment use the same set as PSC and KSSC. A cross-contract equality check belongs to D-f.

## 3. TMSC additions (REPAIRED_F only, except the view)

**Bootstrap:**
- `wireGovernance(address)` (onlyBootstrap).
- `_checkWiring` requires it to be non-zero only when `profile == REPAIRED_F`.

**`onlyGovernance` mutators,** which revert WRONG_PROFILE outside REPAIRED_F:
- **`govAddAuthority(root, admins)`:**
  - sets `isAuthority`, pushes `_authorities` and the admin flags;
  - the new authority starts unpublished, so repaired profiles give STALE_ANCHOR until it publishes its CRL.
- **`govRemoveAuthority(root)`:**
  - clears `isAuthority`, swap-pops `_authorities` and clears the admin flags;
  - its lists stay as history;
  - its credentials then give UNKNOWN_AUTHORITY (`TMSC.sol:294`) and its admins can no longer publish.
- **`govSetCaAdmins(root, admins)`:** replaces the admin flag set.

**Every mutator:**
- increments `authEpoch` (the DBC barrier applies, see F-28);
- appends `lsc.updateLog(keccak256(abi.encode(root, "GOV", action)), abi.encode(root, action, admins, governanceNonce))`;
- emits `AuthorityAdded(root, admins)`, `AuthorityRemoved(root)` or `CaAdminsSet(root, admins)`.

**New view, all profiles (additive ABI):** `caAdmins(address root) returns (address[])`.
- It is backed by `mapping(address => address[]) _caAdminList`, filled in the constructor and by governance.
- It closes the "CA-Admin sets cannot be enumerated" gap of A1-0088 D-f.

**Unchanged:** `addCA`, `removeCA` and `PSC.majorityConsent` keep reverting NOT_IMPLEMENTED_IN_PHASE in all profiles. Governance.sol is the realization of Table 2 majorityConsent; it is not reached through those selectors.

## 4. KSSC: pin policyVersion (D-e e1)

In `acceptState`, when `profile == REPAIRED_F` (and bit 8 is clear), require `c.policyVersion == IPolicyVersion(acsc).policyVersion()`; otherwise STALE_STATE.
- `IPolicyVersion` is a one-function interface. It avoids a KSSC↔ACSC import cycle and a `KSSC.Config` change, so there is **no constructor ABI change**.
- This closes P-WIT-4.
- sequence, authEpoch and sourceBlockNumber stay monotone and unbounded. Their poisoning is a validation-failure boundary: F-24 needs three signers.

## 5. Unchanged contracts and functions

- `LSC`, `RSC` and `DecisionVerifier`: no change.
- `ACSC` and `PSC`: no ABI change; only the profile gates of section 1.
- `QuorumLib`: no change.

## 6. Mutation bits and configuration mutants (deliberate mutations)

| Bit | Name | Effect (REPAIRED_F only) | Detecting test |
|---|---|---|---|
| 6 | `MUT_NO_GOV_ACTION_BINDING` | Governance verifies a digest whose `action` field is forced to 0, so one certificate dispatches as any action | FL-10 substitution |
| 7 | `MUT_NO_GOV_NONCE` | Governance neither checks nor advances the nonce | FL-10 replay |
| 8 | `MUT_NO_POLICY_PIN` | KSSC skips the section 4 pin | P-WIT-4 under REPAIRED_F |

- `MUT_ALL` becomes `(1 << 9) - 1`.
- **F-18 (q=2)** is a **configuration** mutant, not a code bit: deployment `mutant-f-q2` sets threshold 2 in PSC, KSSC and Governance. It is labelled a deliberate mutation in the manifest.

## 7. E regression plan

1. **Default build, E profiles.** All 166 E tests and the 32 F0 characterization tests (`F0Powers`, `F0Quorum`, all REPAIRED_E or paper profiles) must pass **unchanged**. Their source is untouched, and the run is evidence that C0 preserved E.
2. **Repaired E suites re-run under REPAIRED_F:**
   - **Fixture change:** `test/utils/Fixture.sol` gains a virtual `witnessKeys()`, one key in E and four in F.
   - **Signing helpers:** `certify`, `signCheckpoint` and `signReceipt` sign with the first three signers, sorted by address.
   - **Deployment:** `_deploy` builds Governance and calls `wireGovernance` when REPAIRED_F.
   - **Subclasses:** each `*RepairedTest` in AccessFlow, Audit, DecisionBinding, Freshness, OutcomeEvidence, Policy and TrustAnchors gets a `*RepairedFTest` subclass with `profile() = REPAIRED_F`.
   - **Expected result:** identical. The only intended difference is that the P-WIT-4 analogue rejects (section 4). Any other difference is a regression to explain.
3. **New A-F1 suites** (PLAN names `test/Quorum.t.sol` and `test/Governance.t.sol`):
   - **Quorum:** decisions, checkpoints and receipts at q=3 of 4 under REPAIRED_F, covering the FL-2..FL-7 analogues on all three paths. The F0 work measured only the checkpoint path.
   - **Governance:** the A1-0088 D-a list (9 items) plus F-28.
   - **Test-first:** governance tests are written first against a `Governance` stub whose `execute` reverts NOT_IMPLEMENTED_IN_PHASE. That gives assertion failures, not compile errors, as in the E precedent `evidence/receipt-first-run.txt`.
   - **Honest about quorum:** QuorumLib already handles q-of-n, so the decision and receipt quorum tests are characterization and are expected to pass first time. I will not present them as red-green.
4. **Mutants:** the `profile.mutants` suites (`test-mutants/`) gain F mutant deployments for bits 6–8. `tools/check_mutants.py` is extended so that each bit's named detecting test fails.

## 8. Vectors, exports and deployment manifest

- **Vectors:** `script/ExportVectors.s.sol` writes a new file, `exports/vectors/eip712-f-governance.json`; the E vector file is unchanged. It contains:
  - for each action 1–3: the domain separator, struct hash, digest and four witness signatures (TEST-ONLY keys `witness-1..4`, signatures only);
  - one action-substitution negative: the same payload and nonce with a different action gives a different digest.
- **Agent 2 reproduction:** agent 2 should reproduce the digests and recovered signers, as for E (A2-0003).
- **`tools/export_abi.py`:**
  - adds Governance;
  - for D-f, adds `immutableReferences` per contract; this waits for D50.
- **`tools/make_manifest.py`:**
  - `profile` gains "repaired-f" with `profileEnum` 3;
  - `chains.pbc.contracts.Governance`;
  - `fixture.witnessSet` = {version "2", threshold "3", four witnesses, keyLabels `witness-1..4`, usedBy "repaired-f"};
  - mutation names for bits 6–8;
  - the `mutant-f-q2` configuration.
  - These are interface and schema changes that need agent 3's ACK. D-f additions such as `onchainRuntimeSha256` wait for D50.
- **`script/FixtureConfig.sol`:**
  - `WITNESS_SET_VERSION_F = 2`;
  - `THRESHOLD_F = 3`;
  - `MAX_GOVERNANCE_TTL = 120` **(proposed)**.
  - REQUEST_TTL 30 and CHECKPOINT_TTL 60 are unchanged.
- **`script/Deploy.s.sol`:** for PROFILE=3, build four-witness arrays, deploy Governance on the PBC and call `wireGovernance` before seal.

## 9. Witness conflict keys — correction to A1-0088 (A3-0054 was right)

A1-0088 wrote "single-signing per `(chainId, nonce)`". That is **insufficient**: two Governance contracts on one chain, for example after a redeployment, would collide.

The ledger binds every signed type to its full EIP-712 domain. The conflict key for durable honest single-signing should therefore start from the 32-byte **domain separator**, which already includes name, chainId and verifyingContract. It then adds the set version and the type's sequence field:

| Type | Domain (name, chain, verifier) | Proposed conflict key |
|---|---|---|
| GovernanceAction | HMBCGovernance, PBC, Governance | (domainSeparator, witnessSetVersion, nonce) |
| StateCheckpoint | HMBCState, DBC, KSSC | (domainSeparator, witnessSetVersion, sequence) |
| AccessDecision | HMBCDecision, DBC, KSSC | (domainSeparator, witnessSetVersion, requestDigest) |
| GrantReceipt | HMBCReceipt, PBC, PSC | agent 2 to decide. A receipt attests an existing grant, so two receipts for one grant at different DBC blocks may not be a conflict. |

The exact rule is agent 2's (B-F1); this table only gives what the ledger binds.

**Coupling found while specifying this (proposed new row F-29):**
- A governance action that expires unexecuted leaves its nonce unused.
- Under strict single-signing, honest witnesses could then never sign a different action for that nonce, and governance would stall forever.
- A safe rule is to allow re-signing a nonce only after the previously signed action's `expiresAt` has passed on PBC time. The ledger then can no longer execute the old one.
- That needs the unresolved clock-skew bound.
- Checkpoints raise the same question for a sequence number whose checkpoint was signed but never accepted.
