# A-F1 ledger design for the minimal core F scope (agent 1, F0, for review) — revision 2

**Status: DESIGN FOR REVIEW. NOT IMPLEMENTED. NOT ACKED.**
- Revision 1 (sha256 02447d02.., commit 5992a0a, A1-0090) was reviewed in A3-0055 / DESIGN-REVIEW.md as R1–R6.
- Revision 2 answers R1–R5. R6 belongs to agent 2; section 9 only gives the ledger bindings.
- Scope: C0, D-a a1, D-b b1, D-c c1, D-d d1 and D-e e1, with `QuorumLib` reused. None of these is selected.
  - The alternatives e2, c2 and d2 are in A1-0088.
  - D-f waits for agent 2's D50.
- No code is written until the F0 freeze ACKs.
- Values marked **(proposed)** are unresolved, including all numeric bounds.

Base: `ledger/src` and `ledger/test` at 5992a0a. Production is identical to 933d2a7. Line numbers refer to that tree.

## 1. Profile carrier (C0)

**`src/types/ProtocolTypes.sol`:**
- Append `REPAIRED_F` to `enum Profile` (index 3); indices 0–2 do not move.
- Add a free function `isRepaired(Profile p)`, true for REPAIRED_E and REPAIRED_F.

**Production behaviour gates** that become `isRepaired(profile)`, each keeping its error code:

| File | Lines |
|---|---|
| TMSC.sol | 188, 301, 319, 327 |
| PSC.sol | 113, 204, 222, 246 |
| KSSC.sol | 105, 140 |
| ACSC.sol | 133, 145, 179 |

**Mutation guards** (`TMSC.sol:95`, `PSC.sol:110`, `KSSC.sol:102`, `ACSC.sol:91`):
- bits 0–5 are allowed in either repaired profile;
- bits 6–8 (section 6) only in REPAIRED_F;
- anything else gives MALFORMED, as today.

## 2. Governance (D-a a1, D-b b1) — new `src/Governance.sol`, PBC only

**R4 change: the action is a fully typed EIP-712 struct.** There is no free-form `bytes` payload, so there is nothing to decode and no trailing or non-canonical byte case. Solidity's ABI decoder rejects malformed calldata, including dirty high bits in address fields, before any check runs. It reverts without a `Rejected` code; tests assert a revert.

```
struct GovernanceAction { uint8 action; address root; address[] admins; uint64 nonce; uint64 witnessSetVersion; uint64 expiresAt; }
typehash: GovernanceAction(uint8 action,address root,address[] admins,uint64 nonce,uint64 witnessSetVersion,uint64 expiresAt)
structHash = keccak256(abi.encode(TYPEHASH, action, root, keccak256(abi.encodePacked(admins)), nonce, witnessSetVersion, expiresAt))
```

- `address[]` is hashed per EIP-712: `abi.encodePacked` pads array elements to 32 bytes, the same convention as `roles` in `hashRoleCertificate`.
- Domain: name `"HMBCGovernance"`, version `"1"`, `chainId = block.chainid`, `verifyingContract` = this Governance.

**Actions and structural rules.** Any violation gives MALFORMED.

| action | name | `admins` rule |
|---|---|---|
| 1 | ADD_AUTHORITY | 1..MAX_ADMINS entries, non-zero, strictly ascending (which excludes duplicates) |
| 2 | REMOVE_AUTHORITY | must be empty |
| 3 | SET_CA_ADMINS | 0..MAX_ADMINS entries, non-zero, strictly ascending. Empty means the authority's list publishing is suspended. |

- For every action, `root != 0`.
- MAX_ADMINS = 8 **(proposed)**.

**Constructor** (Governance is not `Bootstrapped`; it needs no wiring):

```
constructor(Config memory c)
struct Config { address target; uint64 witnessSetVersion; address[] witnesses; uint256 threshold; uint64 maxGovernanceTtl; uint256 mutations; }
```

- It rejects with MALFORMED when:
  - target is zero;
  - the threshold is outside `1..witnesses.length`;
  - a witness address is zero;
  - `maxGovernanceTtl == 0`;
  - `mutations` contains a non-F bit.
- Repeated witnesses give DUPLICATE_SIGNER, as in KSSC.
- `maxGovernanceTtl` = 120 s **(proposed)**.

**Public getters:**
- `target() returns (address)`;
- `governanceChainId() returns (uint256)`, which is `block.chainid` at construction;
- `witnessSetVersion() returns (uint64)`;
- `threshold() returns (uint256)`;
- `witnesses() returns (address[])`;
- `maxGovernanceTtl() returns (uint64)`;
- `mutations() returns (uint256)`;
- `governanceNonce() returns (uint64)`, starting at 0.

**Entry point:** `execute(GovernanceAction calldata a, bytes[] calldata signatures)`.
- Any caller may submit.
- The first failure wins, and the whole transaction reverts.

| Step | Check | Rejection |
|---|---|---|
| 1 | `a.witnessSetVersion != witnessSetVersion` | STALE_STATE |
| 2 | `a.action` not in {1, 2, 3} | MALFORMED |
| 3 | `a.root == 0`, or `admins` breaks the action's rule | MALFORMED |
| 4 | `a.nonce <= governanceNonce` | REPLAY |
| 4 | `a.nonce > governanceNonce + 1` | MALFORMED |
| 5 | `now >= a.expiresAt` | EXPIRED |
| 5 | `a.expiresAt > now + maxGovernanceTtl` | MALFORMED |
| 6 | `QuorumLib.verify(digest, signatures, witnesses, threshold)` | BAD_SIGNATURE, DUPLICATE_SIGNER, INSUFFICIENT_QUORUM or MALFORMED |
| 7 | set `governanceNonce = a.nonce`, then call TMSC | — |
| 8 | TMSC preconditions (section 3) | MALFORMED or UNKNOWN_AUTHORITY |
| 9 | emit `GovernanceApplied` | — |

- Step 7 updates state before the interaction. If TMSC reverts, EVM atomicity also restores `governanceNonce`.
- Event: `GovernanceApplied(uint64 indexed nonce, uint8 indexed action, address indexed root, bytes32 structHash, address submitter)`.

**Action binding (FL-10):** `action` is inside the digest. A certificate signed over action 3 but submitted as action 2 recovers different addresses, giving BAD_SIGNATURE.

**Signers (b1):** the four witness keys, q=3. They are the same set as PSC and KSSC; D-f checks the equality.

## 3. TMSC additions (REPAIRED_F; views in all profiles)

**Wiring:**
- `wireGovernance(address governance_)` (onlyBootstrap).
- `_checkWiring` adds `profile == REPAIRED_F && governance == 0` → MALFORMED.

**Mutators.** Each carries the **signed action's nonce** passed by Governance (R3). All are `whenSealed`.
- A caller other than `governance` gives UNAUTHORIZED_CALLER; a profile other than REPAIRED_F gives WRONG_PROFILE.

```
function govAddAuthority(uint64 nonce, address root, address[] calldata admins) external;
function govRemoveAuthority(uint64 nonce, address root) external;
function govSetCaAdmins(uint64 nonce, address root, address[] calldata admins) external;
```

**Remove and re-add rule (R2): a tombstone.**
- New state: `mapping(address => bool) public removedAuthority`.

| Mutator | Precondition | Effect |
|---|---|---|
| `govAddAuthority` | `isAuthority[root]` or `removedAuthority[root]` → MALFORMED | sets `isAuthority`, pushes `_authorities`, sets the admin flags and `_caAdminList[root]` |
| `govRemoveAuthority` | `!isAuthority[root]` → UNKNOWN_AUTHORITY | clears `isAuthority`; sets `removedAuthority`; swap-pops `_authorities`, so the order of `authorities()` changes and D-f must sort; clears every admin flag and `_caAdminList[root]` |
| `govSetCaAdmins` | `!isAuthority[root]` → UNKNOWN_AUTHORITY | clears the old admin flags and sets the new ones |

**Why a fresh root cannot revive old state:** `_crl`, `_acl`, `_revoked` and `_temp` can only be written while `isAuthority[root]` is true (`_authorizeUpdate`, `TMSC.sol:180`). A never-added root therefore has empty state, and a removed root can never be re-added.

**The returning hospital** uses a **new root key** and re-issues its certificates. Certificates of the removed root give UNKNOWN_AUTHORITY at the PBC forever (`TMSC.sol:294`, `:317`). Its admins give UNKNOWN_AUTHORITY when publishing (`:180`).

**Retained history:**
- The removed root's lists stay unreachable for validation.
- The views `revocationListState`, `temporalAclState`, `isRevoked` and `temporalWindow` still return them as history; this is documented, not hidden.
- In repaired profiles a fresh root starts unpublished: STALE_ANCHOR until its first CRL.

**The alternative**, an incarnation counter that allows re-use of a root address, is not proposed. It would add a field to validation keys.

**Every mutator:**
- increments `authEpoch` (the DBC barrier applies, see F-28);
- appends `lsc.updateLog(keccak256(abi.encode(root, action, "HMBC.governance")), abi.encode(action, nonce, root, admins, msg.sender))`. The log hash therefore binds the authorized action and its signed nonce. `admins` is empty for REMOVE.

**Events:**

```
AuthorityAdded(uint64 indexed governanceNonce, address indexed root, address[] admins, uint64 authEpoch)
AuthorityRemoved(uint64 indexed governanceNonce, address indexed root, uint64 authEpoch)
CaAdminsSet(uint64 indexed governanceNonce, address indexed root, address[] admins, uint64 authEpoch)
```

**New views, all profiles (additive ABI):**
- `governance() returns (address)`;
- `caAdmins(address root) returns (address[])`, filled by the constructor and by governance;
- `removedAuthority(address) returns (bool)`.

**Unchanged:** `addCA`, `removeCA` and `PSC.majorityConsent` still revert NOT_IMPLEMENTED_IN_PHASE.

## 4. KSSC: pin policyVersion (D-e e1)

- **New file `src/interfaces/IPolicyVersion.sol`:** `interface IPolicyVersion { function policyVersion() external view returns (uint64); }`. ACSC already has a matching public getter (`ACSC.sol:58`).
- **Change in `acceptState`,** inserted after the keyEpoch check (`KSSC.sol:150`) and before the monotonicity block (`:151-158`):
  - when `profile == REPAIRED_F`, bit 8 is clear, and `c.policyVersion != IPolicyVersion(acsc).policyVersion()`, reject with STALE_STATE.
  - There is no constructor or ABI change.

## 5. Unchanged

- `LSC`, `RSC`, `DecisionVerifier` and `QuorumLib` have no change.
- `ACSC` and `PSC` keep their ABI; only the section 1 gates change.

## 6. Mutation bits and the configuration mutant

| Bit | Name | REPAIRED_F effect | Sensitivity control |
|---|---|---|---|
| 6 | `MUT_NO_GOV_ACTION_BINDING` | Governance hashes `action := 0` and dispatches the calldata `action` | see below |
| 7 | `MUT_NO_GOV_NONCE` | step 4 skipped; the nonce is not advanced | replay of an executed certificate succeeds |
| 8 | `MUT_NO_POLICY_PIN` | section 4 skipped | the P-WIT-4 analogue is accepted |

**Bit 6 control (R4):**
- **Mutant run:** in the mutant fixture the witnesses sign the **action=0** digest, as the mutant verifier hashes it. A certificate for SET_CA_ADMINS(Hx, []) (suspend) is then submitted as REMOVE(Hx, []). The mutant removes Hx.
- **Baseline run:** with bit 6 clear, a certificate signed over action=3 and submitted as action=2 gives BAD_SIGNATURE.
- **Mutant positive control:** a matching action still succeeds under the mutant.

- `MUT_ALL` becomes `(1 << 9) - 1`.
- `mutant-f-q2` (F-18) is a deployment configuration with threshold 2 in PSC, KSSC and Governance. It has no code bit.

## 7. Test plan and E regression (R1: revised; my "all sources unchanged" claim is withdrawn)

Running the E properties under REPAIRED_F needs **mechanical, assertion-preserving edits to E test sources**. No assertion, expected code or message text changes. The exact sites, at 5992a0a:

1. **`virtual` on `profile()`** in the 8 E repaired test contracts:
   - `Audit.t.sol:132` and `:155`;
   - `AccessFlow.t.sol:318`;
   - `DecisionBinding.t.sol:93`;
   - `Freshness.t.sol:176`;
   - `OutcomeEvidence.t.sol:27`;
   - `Policy.t.sol:52`;
   - `TrustAnchors.t.sol:177`.
2. **9 equality branches** become `isRepaired(profile())`:
   - `Audit.t.sol:54` and `:57`;
   - `AccessFlow.t.sol:50`, `:208` and `:258`;
   - `Freshness.t.sol:27`;
   - `TrustAnchors.t.sol:110`;
   - `utils/Fixture.sol:421` and `:471`.
3. **Fixture parameters**, in `utils/Fixture.sol`:
   - new virtual `witnessSetVersion()`, returning 1 in E and 2 in F, replacing the constant at `:160`, `:165`, `:371`, `:400`, `:455` and `OutcomeEvidence.t.sol:133`;
   - `threshold()`, 1 or 3, at `:160` and `:165`;
   - `witnessAddresses()`, 1 or 4, used by `_deploy`;
   - Governance is deployed and wired for REPAIRED_F.
4. **Signing helpers** `certify`, `signCheckpoint` and `signReceipt`:
   - when `pk == witnessPk` under REPAIRED_F, they return the quorum signatures of the first 3 witnesses, sorted by address;
   - any other key signs alone. That keeps the 3 non-witness negative tests valid: `OutcomeEvidence.t.sol:88` and `:137`, and `Freshness.t.sol:246`. An unknown first signer gives BAD_SIGNATURE before the count at q=3 as well.
5. **`test_E01_SignatureEncodings` (`DecisionBinding.t.sol:207`).** I predict the same codes at q=3:
   - `[s0, s0]` gives DUPLICATE_SIGNER at index 1;
   - `[]` gives INSUFFICIENT_QUORUM;
   - single high-s and 64-byte signatures give BAD_SIGNATURE.
   - Each is detected per signature, before the count. This is a prediction to confirm by run. If it fails, the test becomes E-only and an F analogue goes into `Quorum.t.sol`.

**Evidence of equivalence:**
- Run the E profiles before and after the edit. The per-test name and PASS list must be identical: 198 tests now, from 166 E plus 32 F0.
- The edit's diff must touch only the listed sites.
- The historical E snapshot (933d2a7) stays the evidence for gate E.

**F reruns:** 8 `*RepairedFTest` subclasses with `profile() = REPAIRED_F`.
- Predicted identical; any difference is a regression to explain.
- `F0Powers` and `F0Quorum` remain E characterization and are not subclassed.

**New A-F1 suites:**
- **`Quorum.t.sol`:** decisions, checkpoints and receipts at q=3 of 4 (the FL-2..FL-7 analogues on all three paths), plus the P-WIT-4 analogue (STALE_STATE).
- **`Governance.t.sol`:**
  - the A1-0088 D-a list;
  - F-28 (removal across the barrier);
  - R2 controls: a fresh root (STALE_ANCHOR, then valid after its CRL), tombstoned re-add (MALFORMED), the removed root's certificate (UNKNOWN_AUTHORITY), the removed root's admin publishing (UNKNOWN_AUTHORITY), the history views;
  - R3 rollback: after a failing `execute`, `governanceNonce`, `authEpoch`, `authorities()`, `caAdmins`, `lsc.logCount()` and the events are all unchanged;
  - log binding: the details hash of `updateLog` equals the expected encoding with the signed nonce.
- **Test-first:**
  - Governance tests are written against a stub whose `execute` reverts NOT_IMPLEMENTED_IN_PHASE, giving assertion failures (precedent: `evidence/receipt-first-run.txt`).
  - QuorumLib tests are characterization and are expected to pass first time; they are not presented as red-green.
- **Mutants:** `test-mutants/` gains the bit 6–8 deployments, and `tools/check_mutants.py` names each detecting test.

## 8. Vectors, exports, schema (R4, R5)

**Vectors** (`script/ExportVectors.s.sol` → new `exports/vectors/eip712-f-governance.json`; the E vectors are unchanged). None exist yet; they are produced at implementation.
- For each action 1–3: domain separator, typehash, structHash, digest and 4 witness signatures (TEST-ONLY `witness-1..4`, signatures only).
- Boundary vectors:
  - nonce = current gives REPLAY; nonce = current + 2 gives MALFORMED;
  - `expiresAt = now` gives EXPIRED; `now + maxTtl` is accepted; `now + maxTtl + 1` gives MALFORMED;
  - admins `[0]`, a duplicate, descending order or 9 entries give MALFORMED;
  - REMOVE with non-empty admins gives MALFORMED.
- Bit 6 vectors signed over action=0, with their baseline counterparts.
- Agent 2 reproduces the digests and recovered signers.

**Schema (R5, agreed):** this is **not** an additive v1 edit. A versioned successor schema and manifest (interface v2) with the exact affected ACKs is required. The frozen v1 schema bounds `profileEnum` to 0..2, closes the PBC contracts object and has E-specific witness constraints.

Ledger-side exporter changes, which follow the successor schema:
- **`tools/make_manifest.py`:**
  - "repaired-f" with `profileEnum` 3;
  - `chains.pbc.contracts.Governance`;
  - `fixture.witnessSet` version "2", threshold "3", four witnesses;
  - mutation names for bits 6–8;
  - the `mutant-f-q2` configuration;
  - `fixture.governance` {maxGovernanceTtl, maxAdmins}.
- **`tools/export_abi.py`:** Governance.
- **D-f inputs**, pending D50: `immutableReferences`, and on-chain runtime hashes for **seven** runtimes (the six plus Governance), with Governance's witness list as storage.
- The runner's profile allow-list and the adapter operations are agent 3's and agent 2's parts of the source plan.

## 9. Witness conflict keys — ledger bindings for agent 2 (R6 is agent 2's)

| Type | Domain (name, chain, verifier) | Sequence field the ledger enforces | Acceptance rule on the ledger |
|---|---|---|---|
| GovernanceAction | HMBCGovernance, PBC, Governance | `nonce`, which must equal `governanceNonce + 1` | `now < expiresAt`, by PBC `block.timestamp` |
| StateCheckpoint | HMBCState, DBC, KSSC | `sequence`, which must be greater than the current one | `now < expiresAt`, by DBC `block.timestamp` |
| AccessDecision | HMBCDecision, DBC, KSSC | per `requestDigest`; grant and nonce once | `now < min(expiresAt)`, by DBC time |
| GrantReceipt | HMBCReceipt, PBC, PSC | per `requestDigest`; outcome once | no expiry (late reconciliation is allowed) |

- Durable records should be namespaced by the 32-byte domain separator plus the type name.
- **For F-29, a suggestion to agent 2, not a rule:** a governance action or checkpoint becomes impossible to accept once the **target ledger itself** shows a block with `timestamp >= expiresAt`, at the agreed confirmation depth. Re-signing a nonce or sequence could be conditioned on observing such a block, not on a local wall clock.
- That still needs a finality and confirmation assumption. It also needs the agreement claim stated over simultaneously acceptable values, as R6 says.
