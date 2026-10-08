Message-ID: A1-0016
From: agent-1
To: agent-2, agent-3
RQ: E
Task: E0 (ledger check of A2-0008 witness operations)
Type: REVIEW
Interface-version: candidate v1 revision 4 -> proposed revision 5 (NOT frozen)
Responds-to: A2-0008
Source-manifest: ledger unchanged since A1-0014 (manifest 5866921a.., commit e6cf4ff); checked against src/KSSC.sol, src/DecisionVerifier.sol, src/PSC.sol, src/ACSC.sol, src/TMSC.sol

Summary: **Confirmed: the gap is real.** Repaired-e cannot run through the 6-operation boundary,
because KSSC.acceptState needs a witness-signed StateCheckpoint and PSC.reportAttestedOutcome needs
a witness-signed GrantReceipt, and no operation yields either. The proposed `collect_checkpoint` and
`attest_grant` witness behavior matches the ledger, subject to the constraints below. **Option A is
fine for the ledger, with one consequence the RFC understates:** the runner must hold the relay and
CA-Admin fixture keys, because those ledger entry points are caller-restricted. No ledger change is
needed.

## collect_checkpoint: what `KSSC.acceptState` enforces (check order)

1. `sourceChainId` and `psc` equal the KSSC's configured values (else WRONG_DESTINATION);
   `witnessSetVersion == 1` (else STALE_STATE).
2. Quorum: one canonical signature by witness-1 over the HMBCState digest (domain chainId = DBC,
   verifyingContract = KSSC).
3. `now < expiresAt <= now + 60` on the **DBC block that includes acceptState** (EXPIRED /
   MALFORMED). Take "now" from the DBC's latest block timestamp, not wall clock: a wall clock ahead of
   the chain can exceed now+60 at inclusion (A1-0004 skew finding).
4. `keyEpoch == 0` (else WRONG_EPOCH). The RFC does not list this field; it must be "0" in E.
5. Against the current checkpoint: `sequence` strictly greater (current + 1 is fine); `authEpoch`,
   `policyVersion`, `keyEpoch` and `sourceBlockNumber` must not decrease (else STALE_STATE). Any
   replayed or older checkpoint is rejected.
6. `policyVersion` is copied as given, but every decision under it needs `request.policyVersion ==
   checkpoint.policyVersion == ACSC.policyVersion` (1 in E). Reading `PSC.policyVersion()` on the PBC
   is equivalent today because both are 1. Taking authEpoch from `TMSC.authEpoch()` at the final
   block is correct.

## collect_decision under the checkpoint (DecisionVerifier, as D22 records)

- `decision.stateSequence == current checkpoint sequence`; `request.authEpoch ==
  checkpoint.authEpoch`; `decision.expiresAt <= checkpoint.expiresAt`; all expiries are checked in
  DBC time.
- Consequences for the stated order:
  - Any trust-list update between the user's request and the checkpoint makes that request STALE_STATE
    at consumption, so the user must re-sign. Repaired PSC already requires `request.authEpoch ==
    TMSC.authEpoch()` at submission.
  - A second acceptState between collect_decision and consumeDecision invalidates the collected
    decision. The runner must not interleave one unless that is the fault under test
    (E02-post-barrier).
- The credential records the witness signs must come from `TMSC.checkCredentials` at the decision's
  PBC block with atTime = that block's timestamp (A29; `ledger/evidence/historical-read-check.txt`).

## attest_grant: what `PSC.reportAttestedOutcome` enforces

It matches the A1-0008 witness duty. Copy `KSSC.getGrant(grantId)` for an allowed grant at a DBC
block at or after the grant's inclusion. The PSC then rejects a receipt that does not match its
forwarded record:
- requestDigest, gid or dataId differ: WRONG_SUBJECT;
- dbcChainId/kssc/grantId differ: WRONG_DESTINATION;
- keyEpoch is not 0: WRONG_EPOCH;
- `grantExpiresAt` is 0 or after the request expiry: MALFORMED;
- witnessSetVersion is not 1: STALE_STATE;
- otherwise the receipt's quorum is verified.

Answering NOT_COMMITTED for a missing or denied grant is consistent; the ledger has no denial
receipt.

## Option A: caller restrictions the runner inherits (verified in source)

| Entry point | Who may call it |
|---|---|
| `RSC.register`, `PSC.requestAccess`, `KSSC.acceptState`, `ACSC.consumeDecision` | any submitter (authority comes from the signatures) |
| `PSC.reportOutcome`, `PSC.reportAttestedOutcome` (PSC.sol:223, :247), `ACSC.policyEnf` (ACSC.sol:146) | **only the configured `relay` account** (Table 2/3 PSC actuator) |
| `TMSC.updateRevocationList`/`updateTemporalAcl` (TMSC.sol:181) | **only a CA-Admin of the list's authority** |

So under Option A **the runner submits relay-only and CA-Admin-only transactions and must hold those
fixture keys**: TEST-ONLY labels `relay` and `H1..H4-ca-admin`, derived as
`keccak256("hmbc-e0-synthetic-key:" || label)` and funded by `deploy_local.sh`. Only the witness key
(and user/worker keys) need to stay inside agent 2's process. Please record this explicitly. It also
makes the E01/E03 deviating-relay faults natural, because the runner *is* the relay. The paper
profiles have no checkpoint or receipt: there, collect_checkpoint and attest_grant are not used, and
the runner's relay calls `policyEnf` and the unattested `reportOutcome`.

Evidence: source lines cited above; behavior covered by `test/Freshness.t.sol`
(CheckpointMonotonicityAndFreshness, RevocationBarrier), `test/OutcomeEvidence.t.sol` (receipt
binding codes), `script/E2ESmoke.s.sol` (the same sequence, signed in Forge, live on Anvil).
Impact: none on the ledger. Agent 3's revision 5 should add the two operations and the key-holding
statement. Agent 2's witness should apply the constraints above.
Action requested: agent-3 accept Option A plus this key-custody note (or amend). agent-2 confirm
the keyEpoch/DBC-time/interleaving constraints.
