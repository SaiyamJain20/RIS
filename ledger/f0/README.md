# F0 — ledger states a faulty organization can change (agent 1)

**What this is.** Agent 1's F0 input under PLAN.md section 6: "Agent 1 enumerates which contract/ledger states a faulty organization can change". It was assigned in A3-0052 and authorized by the human in D51.

It is planning evidence for agent 3's `evaluation/evidence/fault-model.csv` and `evaluation/scenarios/f_matrix.json`. It is **not** F implementation:
- no production ledger byte changed;
- `ledger/src`, `ledger/script` and `foundry.toml` are identical to the E pin 933d2a7;
- nothing here is an ACKed F expectation.

**What is behind each claim.** Every power below is either:
- **measured** by a characterization test on the E code, or
- **read** from source and labelled as such.

Agents 1, 2 and 3 are the same model, so peer review of this file is correlated review.

## Files

| File | Content |
|---|---|
| `ledger-state.csv` | Every state variable of the six contracts and `Bootstrapped`, 29 rows covering all 70 variables. Each row gives its kind (immutable, constructor-only, bootstrap, operational), writers, caller rule, keys needed, profiles and `file:line`. |
| `entry-points.csv` | Every constructor and every external or public non-view function (33). Each row gives the caller rule, the signatures checked, the state written and the power of a faulty key holder. |
| `actor-powers.csv` | Twelve actors and the keys they hold. For each: what it changes alone, what needs others, what it cannot change, the evidence tests and a classification. |
| `../test/F0Powers.t.sol` | 22 characterization tests: 5 in each of the 3 profiles plus 7 repaired-e only. Expectations were written before the first run. |
| `../tools/check_f0_powers.py` | Recompiles `ledger/src` with the pinned solc (hash-checked). It verifies that every state variable and entry point is covered exactly once, that every `file:line` declares what it names, and that every cited test and id exists. |
| `../tools/f0_controls.sh` | Sensitivity controls: removes each injected fault in a scratch copy and requires the matching test to fail. |
| `../evidence/f0-powers/` | First run, full suite, controls (including the first, non-matching run), checker run and checker negative control. |

## Reproduce (repository root, Foundry 1.8.5 on PATH)

```
forge test --root ledger --match-path test/F0Powers.t.sol            # 22 passed
forge test --root ledger                                             # 188 passed (166 E + 22 F0)
ledger/tools/f0_controls.sh <empty scratch dir>                      # 7/7 controls sensitive
python3 -I ledger/tools/check_f0_powers.py                           # problems: []
```

## Findings

Classes follow AGENTS.md. "Tested" means a passing characterization test with a sensitive control.

### L1 — Bootstrap is a single-key trusted setup

**Evidence:**
- tested after seal: `test_F0_DeployerPowerEndsAtSeal`;
- read before seal.

**Before `seal()`, the deployer alone chooses everything** (rows A01, E01–E33). That includes:
- profile and mutations, so it could deploy a `mutant-*` build;
- both witness sets and thresholds;
- the relay;
- authority roots and CA-Admins;
- policies, record owners and destinations.

**After seal, nobody can change any of it.** The fixture uses one deployer account on both chains.

**F impact:** state this as a trusted-setup assumption, or have every organization verify the deployment manifest before use. The manifest check covers runtime code hashes, constructor arguments and witness sets, and overlaps D50.

### L2 — No post-seal change path exists

**Class:** paper-supported, with an explicit E omission (source map S22, S27, S28, S30).

**Fixed for the deployment's life** (S10, S16, S17, S21, S22, S26, S28):
- the authority set;
- CA-Admin sets and root keys;
- both witness sets and thresholds;
- the relay;
- policies and record owners;
- `policyVersion`.

The four governance placeholders revert with `NOT_IMPLEMENTED_IN_PHASE`: `retrieveLog`, `addCA`, `removeCA` and `majorityConsent`.

**Consequence:** a compromised root, CA-Admin, witness or relay key cannot be replaced, and a faulty authority cannot be removed, without redeploying.

**F impact:** this is A-F1's governance scope.

### L3 — One authority alone authorizes its own GIDs for another hospital's record

**Evidence:** `test_F0_OneAuthorityAloneAuthorizesItsOwnGidForAnotherHospitalsRecord`, in all three profiles.

**Class:**
- tested reconstruction result;
- paper-supported under the fixture's conservative Rule 2 policy: Doctor from **any** issuer, plus OnDuty from the same issuer.

**What happens:** H3 issues a Doctor certificate and an OnDuty entry to a GID it controls, and gets a grant for H2's P1.

**F impact:**
- A q=3 witness quorum does **not** limit this. Honest witnesses verify the same genuinely valid credentials.
- This is a per-issuer trust residual for the F trust matrix.
- The only ledger-side lever is the policy: a DATA_OWNER or two-issuer clause. That is a policy choice, not a quorum property.

### L4 — An authority controls its own revocation history

**Evidence:** `test_F0_AuthorityUnrevokesBySerialOmission`.

**Class:** paper-supported (authority-signed lists).

- A new CRL replaces the old one wholesale, so omitting a serial un-revokes it.
- Repaired-e only requires the version to increase.
- The change is visible (LSC TRUST_UPDATE entries, the Fig. 4 block pointer, `TrustAnchorUpdated`) but cannot be prevented.

### L5 — One authority's updates invalidate every user's in-flight request

**Evidence:** `test_F0_UnrelatedAuthorityUpdateInvalidatesOtherUsersRequests`.

**Class:** tested reconstruction result. The single global `TMSC.authEpoch` is the repaired-e project choice.

**Mechanism:**
- Every accepted list update by **any** authority increments one global counter.
- Repaired-e requires `request.authEpoch` to equal the PBC's current value and the checkpoint's value.
- So H3 or H4, unrelated to Alice, make her signed request STALE_STATE at the PBC, and her already-forwarded request STALE_STATE at the DBC.

**Effect of a faulty authority that keeps updating:** availability is lost for all users. Safety is preserved.

**F impact:** decision D-c below.

### L6 — List lifetime has no upper bound

**Evidence:** `test_F0_AuthorityListValidityHasNoUpperBound`.

**Class:** tested reconstruction result.

Repaired-e's bounded list validity holds only if each issuer chooses a short lifetime. A century-long list is accepted.

**F option:** a deployment-wide maximum list TTL. This is a ledger-only behaviour change; struct bytes are unchanged.

### L7 — The DBC takes request authenticity and credential content from the witness quorum

**Evidence:**
- `test_E03_TrustedWitnessBoundaryUnloggedRequest`: a request never logged on the PBC;
- `test_F0_SingleWitnessAttestsFabricatedRecords`: a Researcher granted on fabricated Doctor and OnDuty records.

**Class:** tested reconstruction result, at the E trusted-witness boundary.

**What the DBC does and does not check:**
- `consumeDecision` checks quorum signatures and bindings.
- It does **not** check the user's request signature.
- It does **not** re-verify the records.
- Any caller may submit (`test_F0_AnyAccountSubmitsCheckpointAndCertificate`).

**Consequence:**
- **In E**, one witness key is full DBC authority.
- **In F**, the ledger enforces only quorum arithmetic and bindings. Safety therefore requires each honest witness to check the PBC record and credentials itself (SPEC section 5).

**F option (D-d):** verify the user's request signature in `consumeDecision`. That removes "fabricated request for any GID, with any recipient key" from the witness-quorum power. It is an ABI change, so an RFC is needed.

### L8 — Poison checkpoints block the DBC permanently

**Evidence:** `test_F0_PoisonCheckpointSequenceBlocksTheDbc`, `...AuthEpochBlocksTheDbc`, `...PolicyVersionBlocksTheDbc`.

**Class:** tested reconstruction result (availability), under a violated E assumption.

**Mechanism:**
- `acceptState` requires sequence, authEpoch, policyVersion, keyEpoch and sourceBlockNumber to be monotone, but sets no upper bound and has no reset.
- A single quorum-signed extreme value is accepted and blocks every later checkpoint.
- Once that checkpoint expires, every decision is STALE_STATE.
- `sourceBlockNumber` follows the same code path but is untested.

**In E:** one witness can do this.

**In F (q=3):**
- It needs three signers, so at least two honest witnesses would have to sign a bad value.
- That is prevented only if honest witnesses validate each field against the PBC (agent 2's B-F1).

**F options (D-e):**
- a q=3, action-bound "checkpoint recovery" governance action;
- and/or a per-step bound on the sequence.

### L9 — Most ledger writes are permissionless; the relay key gates only outcome recording

**Evidence:**
- `test_F0_AnyAccountAppendsRequestLogEntries`;
- `test_F0_AnyAccountSubmitsCheckpointAndCertificate`;
- E01 and E03 tests.

**Class:**
- request logging is paper-supported (V-A5);
- the rest is a tested reconstruction result.

**Who can do what:**
- Any account appends request log entries and denials.
- Any holder of valid signatures submits checkpoints and decisions.

**Repaired-e:** the relay key gates only `reportAttestedOutcome`. A faulty relay can suppress the PBC outcome trail, and requests then stay visibly pending. That is an audit availability loss, not forgery.

**Paper profiles:** the relay alone creates grants and outcomes. This is the known E01/E03 SPEC_GAP.

### L10 — Registration is permanent and the recipient key is write-once

**Evidence:** `test_F0_RegistrationIsPermanentAndRecipientKeyWriteOnce`.

**Class:** tested reconstruction result.

- A compromised GID key cannot be rotated.
- Only the issuer's CRL stops its credentials.

**F impact:** GID and key rotation is not in core F; this note is for the G planning record.

### L11 — Two independent witness-set copies

**Evidence:** read (S17, S22).

PSC (receipts) and KSSC (decisions and checkpoints) each hold their own immutable witness list, version and threshold. Nothing checks across chains that they match.

**F impact:** F deployment verification must check that they are equal (D50 scope).

### L12 — QuorumLib is already q-of-n; n=4 and q=3 are untested

**Evidence:** read (`src/lib/SigLib.sol:36-59`).

**What it already enforces:** distinct signers in strictly increasing order. An unknown signer gives BAD_SIGNATURE, a repeat gives DUPLICATE_SIGNER, too few give INSUFFICIENT_QUORUM.

**Gaps:**
- E deploys only 1-of-1.
- One invalid or unknown signature anywhere rejects the whole certificate, even with q valid ones present. The submitter must filter, so a faulty witness causes rejection only if the submitter includes its signature.

**F impact:** A-F1's first failing tests cover n=4, q=3.

### L13 — Ledger operators sit outside the contract model

**Evidence:** none; assumption.

- Every expiry and freshness check uses `block.timestamp`.
- Core F assumes safe ledgers (SPEC section 5).

**F impact:** the F0 matrix should also state a timestamp-skew bound and an eventual-inclusion assumption (A10).

## Proposed ledger-side expectations for agent 3's scenario reservations

These are proposals for pre-registration. They are not ACKed, and agent 3 owns the matrix.

| Ref | Scenario (n=4, q=3) | Expected ledger outcome |
|---|---|---|
| FL-1 | 0 faulty witnesses, honest request | Grant (control) |
| FL-2 | 1 witness withholds, 3 sign | Grant |
| FL-3 | 2 withhold, 2 sign | INSUFFICIENT_QUORUM; no state change |
| FL-4 | One signer's signature included twice | DUPLICATE_SIGNER; no state change |
| FL-5 | Unknown signer among 3 | BAD_SIGNATURE; no state change |
| FL-6 | Old `witnessSetVersion` | STALE_STATE |
| FL-7 | 1 faulty witness signs a poison checkpoint alone | INSUFFICIENT_QUORUM; checkpoint unchanged |
| FL-8 | Faulty authority repeatedly updates its own lists | Safety preserved. In-flight requests are STALE_STATE while it continues. Measured, and depends on D-c. |
| FL-9 | Faulty authority credentials for its own GID | Grant: a residual, not a quorum failure (L3) |
| FL-10 | Governance certificate for `addCA` replayed as `removeCA` | Reject; action binding (A-F1) |
| FL-11 | Faulty relay withholds outcomes (repaired) | Request stays pending; no forged outcome |

## Decisions needed before the F0 freeze

Recommendations are mine. All of these are open.

- **D-a: governance actions in core F.**
  - In: `addCA` and `removeCA`, CA-Admin rotation, authority root-key refresh, and checkpoint recovery (L8).
  - Out: policy updates and witness rotation. SPEC keeps the four witness identities fixed.
  - Optional: relay replacement.
- **D-b: governance signers.** The four witness keys, q=3, under the **old** set (SPEC section 5). Record the correlation: each hospital's witness and its credential authority are one organization.
- **D-c: global `authEpoch` (L5).** Either keep it and measure the availability lever (FL-8), or bind per-issuer versions, which changes the interface. I recommend keeping it for core F and measuring FL-8, unless agent 3's RQ2 matrix needs availability under a faulty authority.
- **D-d: user-signature check on the DBC (L7).** Defence in depth, not required by the q=3 argument. It needs an RFC because the `consumeDecision` ABI changes.
- **D-e: poison-checkpoint mitigation (L8).** A q=3 recovery action, plus a sequence step bound.
- **D-f: deployment verification (L1, L11).** Fold into agent 2's D50 RFC: witness sets, thresholds, profile, mutations and runtime code hashes of all six contracts.

## Limits

- **Test setup:** the tests run in one EVM that simulates two chains (`test/utils/Fixture.sol`), with the E fixture of one witness at q=1. There is no live two-chain run, one trial per test, and a symbolic setting.
- **Read, not tested:** pre-seal deployer powers, ledger-operator powers, `sourceBlockNumber` poison, and QuorumLib at n=4.
- **Checker scope:** `check_f0_powers.py` proves coverage and citation accuracy only. It does not evaluate the power claims.
- **Review:** correlated same-model review.
