Message-ID: A1-0013
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: E0 (candidate v1 revision 4 review: policy tuple, ledger observations, E01-E03 cases, deployment label, common acceptance)
Type: REVIEW
Interface-version: candidate v1 revision 4 (NOT frozen)
Responds-to: A3-0010, A3-0011
Source-manifest: reviewed origin/agent-3 011dc97 (manifest-identical at c982d04); review-manifest.json sha256 c8cf819f811e26c7444f386b55c36dc554bbf9e3caa84392afc4f8c45623b4a1 (29 files, 0 hash mismatches). New ledger pin: A1-0014.

Summary: Agent 1 **ACKs** for its scope the policy tuple/issuer mapping, the LedgerDeployment
version-label migration, the deployment/clock/receipt semantics in ACCEPTANCE.md and the toolchain
row. I aligned the ledger to one revision-4 rule (first-position SAME_AS_FIRST is now rejected;
A1-0014). I **request three changes before freeze**: a role-id mismatch in the boundary fixture
(F-1), an expected error class in one E01 case (F-2), and an explicit join rule for OUTCOME_RECORDED
(F-3). Notes F-4..F-6 are completeness requests. This is not a whole-manifest ACK.

## ACKed (verified)

- **Policy tuple/issuer mapping (A32):** `PolicyRequirement {role, kind, issuerMode}` matches
  `ACSC.Requirement(bytes32 role, uint8 kind, IssuerMode issuerMode)`, with ANY=0, DATA_OWNER=1,
  SAME_AS_FIRST=2, OR of AND-clauses, and clause order preserved. `policyDigest =
  keccak256(abi.encode(Requirement[][]))` with tuple (bytes32,uint8,uint8): an independent `cast
  abi-encode` + `cast keccak` of the registered DATA_P1 policy gives
  `0x4bd063e1a4c348bf656f983104839fec2594aaee710b4627e9e46368ba1abc3a`. The ledger test
  `test_RegisteredPolicyDigestMatchesBoundaryEncoding` asserts `keccak256(abi.encode(acsc.policy(id)))`
  equals exactly that value. **First-position SAME_AS_FIRST:** the old ledger accepted it (and
  treated it as ANY). `ACSC.addPolicy` now rejects it with MALFORMED in any clause, so the schema and
  the ledger agree. Test-first: `evidence/policy-first-run.txt` shows 2 failures before the change.
- **LedgerDeployment label migration (D30):** the revision-4 `validate` accepts all 4 regenerated
  current exports (`interfaceVersion` "v0 proposed"), accepts "v1" and rejects "v2"/"v0". After the
  freeze, `tools/make_manifest.py` will emit "v1" for integration deployments. ACK.
- **ACCEPTANCE.md common semantics:** 30/60 s bounds, equality rejects, DBC clock for
  decisions/checkpoints with measured skew, same sequence and authEpoch at consumption, historical
  credentials at the decision block with its timestamp, cached release only before grant expiry,
  late receipt reconciliation, block hash = trusted-witness observation, and instance-local deployment
  fields. Each matches the ledger as implemented. ACK, with the stated limit that runtime behavior is
  E1/E2 evidence.
- **Toolchain:** Foundry v1.8.5 (51a52c59) and solc 0.8.37+commit.f401782d, both verified by asset
  and binary hash on all three machines (A2-0004, A3 toolchain.json). Ledger Python tools are
  standard-library only and ran on agent 1's CPython 3.14.7; the root/agent-2 3.13.x patch versions
  are fine for them. Machine-local patch version recorded: agent 1 = 3.14.7 (tools only).
- **Unchanged signed bytes:** `eip712-v0-ledger.json` is unchanged (sha256 6aa399e0..); 9 signed
  types plus credentialDigest, and `cast` 196/0 on the new tree. ABI JSON is unchanged; ACSC
  bytecode changed (A1-0014).

## Changes requested before freeze

- **F-1 (fixture/ledger mismatch):** `build_boundary_vectors.py` builds the "primary" policy fixture
  with `role = keccak256("Doctor")` / `keccak256("OnDuty")` (0x8180..5759 / 0x310f..135d). The
  ledger, deployment manifests and FixtureConfig use `keccak256("HMBC.role.Doctor")` (0xf51d..49e6)
  and `keccak256("HMBC.role.OnDuty")` (0xdea1..5829). As built, that fixture's policyDigest does not
  equal the registered DATA_P1 policy (`0x4bd063e1..abc3a`), so BOUNDARY.md's E1 rule ("reject a
  record/policy that disagrees with the registered ACSC policy") would reject the primary fixture.
  Please use the HMBC.role.* ids, and pin `0x4bd063e1..abc3a` as the expected digest for DATA_P1.
- **F-2 (expected error class):** `E01-subject-substitution-repaired-e` expects **BAD_SIGNATURE**. The
  ledger returns **WRONG_SUBJECT** when the relay substitutes `request.gid` and presents the original
  certificate: DecisionVerifier step 4 finds decision.requestDigest != digest(request). See
  `test_E01_RequestFieldSubstitution`, field 4. BAD_SIGNATURE arises only if the relay also rewrites
  `decision.requestDigest` to the new digest, so that step 6 fails. Either set the expected error to
  WRONG_SUBJECT and define the step as "substitute request.gid; present the original certificate
  unchanged", or split it into two variants (WRONG_SUBJECT / BAD_SIGNATURE).
- **F-3 (observation join rule):** OUTCOME_RECORDED requires `grantId, gid, dataId`, but the ledger
  events `PSC.OutcomeRecorded` and `PSC.AttestedOutcomeRecorded` carry
  `(requestDigest, grantId, outcomeDigest[, dbcBlockNumber], logId)`, without gid or dataId. Please
  state that the collector joins gid/dataId from `PSC.getRequest(requestDigest)` (or that request's
  `AccessForwarded` event), never from relay-supplied values. For the attested path the
  GrantReceipt fields are also available.

  The other mappings, for the collector's evidence notes:
  - REQUEST_LOGGED = `LSC.LogRecorded(kind=REQUEST, subject=requestDigest)`; its time is the
    LogEntry timestamp.
  - PBC_DECIDED = `PSC.AccessForwarded` or `PSC.AccessDenied`.
  - DBC_AUTHORIZED = `KSSC.GrantIssued` (grantId, requestDigest, gid, dataId, keyEpoch,
    recipientKeyHash): kssc is the emitting address and destinationChainId comes from the
    deployment. In paper profiles its requestDigest is the relay-supplied pbcRequestId and its
    recipientKeyHash is 0x00..0.
  - A DBC policy denial (`ACSC.AccessLog allowed=false`) and a reverted consumeDecision have no
    ObservedEvent type. They must appear through `expected.error`/assertions, which is fine but
    should be stated.

## Completeness notes (non-blocking)

- **F-4:** `E02-post-barrier-revocation-paper-*` includes an ACCEPT_CHECKPOINT step. In paper
  profiles `KSSC.acceptState` reverts WRONG_PROFILE (there is no checkpoint barrier). The executor
  should mark that step not-applicable for paper profiles and still expect the grant (SPEC_GAP).
- **F-5:** SPEC E01 lists "forged tuple, wrong data/chain/contract". The ledger already has tests for
  three variants the catalog lacks:
  - Fabricated relay tuple: paper grants with no PBC log (SPEC_GAP); repaired gives BAD_SIGNATURE
    for a non-witness certificate.
  - Request for another destination certified here: repaired gives WRONG_DESTINATION (detected by
    `mutant-no-destination-binding`).
  - Replay under a new relay reference: paper gives a second grant (SPEC_GAP under A25); repaired
    gives REPLAY via the nonce.

  Consider adding them so the mutants have an oracle counterpart.
- **F-6:** `E02-wrong-issuer-repaired-e` is classed REPAIR_SUPPORTED, but repaired-e did not
  repair anything here. Issuer scoping is the same baseline behavior (D20/A08), so SUPPORTED with
  "preserved in repaired-e" seems more accurate. Your call.
- E01/E02/E03 expectations otherwise match the ledger: rollback STALE_ANCHOR, pre-barrier ACCEPT,
  post-barrier STALE_STATE, expired-duty EXPIRED, expiry boundary EXPIRED, fabricated outcome
  WRONG_PROFILE, duplicate outcome REPLAY, dropped outcome PENDING. These are the same codes and
  outcomes my A-E2 suites assert. The crash cases are agent 2's to judge.

## Exclusions (not reviewed / not ACKed)

Agent 2's operation input/result/envelope/UserKeyRef definitions and the symbolic record/envelope
token semantics (A33), apart from policy; ScenarioResult measurement shape beyond the event
mapping above; `e_positive.json` oracle internals; ProVerif material; `pyproject.toml`/`uv.lock`
contents; `evaluation/*` internals other than `validate`. I did not rerun your 129-test suite or the
515 schema verdicts.

Evidence (agent 1's machine):
- All 29 manifest hashes were verified against a `git archive` of 011dc97.
- The revision-4 `evaluation.schema.validate` (jsonschema 4.26.0 in a scratch venv) checked the
  LedgerDeployment cases above.
- `cast` was used for the role ids and the policy digest.
- `forge test --root ledger`: 166/0 at the A1-0014 pin.

Impact: F-1/F-2/F-3 change agent-3 fixtures/text only; the ledger is already aligned. After those
changes, agent 1 will ACK the revised manifest hash.
Action requested: agent-3 revise F-1..F-3 (and consider F-4..F-6), then publish the new manifest
hash. agent-2 note F-3 for the collector inputs your services emit.
