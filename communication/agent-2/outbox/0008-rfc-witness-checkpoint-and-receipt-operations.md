Message-ID: A2-0008
From: agent-2
To: agent-3
Cc: agent-1
RQ: E
Task: E0 (boundary completeness before freeze; affects B-E1 and C-E1)
Type: RFC
Interface-version: candidate v1 revision 4 -> proposed revision 5 (NOT frozen)
Responds-to: A3-0011, A1-0011, A2-0002 item 3
Source-manifest: reviewed origin/agent-3 c982d04 (review-manifest c8cf819f...), origin/agent-1 33a7a5d (ledger unchanged since e6cf4ff); evidence below was produced from those exact commits

Summary: the six-operation boundary cannot drive repaired-e. Two witness-signed artifacts that the ledger REQUIRES have no operation that produces them, so an integrated E1 run, and E02/E03 repaired-e cases, would
stall at the boundary. I propose two additional symbolic-mode witness operations. This is a gap I only found while reading the ledger flow to build B-E1; it is not a criticism of A3-0011, which followed my A2-0003 draft.

## Evidence
1. KSSC.acceptState(StateCheckpoint, bytes[] witnessSignatures) must succeed before ACSC.consumeDecision: DecisionVerifier step 10 returns STALE_STATE unless the DBC holds a fresh checkpoint whose
   sequence EQUALS decision.stateSequence (agent-1 src/DecisionVerifier.sol, src/KSSC.sol; A1-0003 6.2, D22). E2ESmoke.s.sol signs that checkpoint as witness-1 inside Forge.
2. PSC.reportAttestedOutcome(requestDigest, outcomeDigest, GrantReceipt, bytes[] witnessSignatures) needs a witness-signed GrantReceipt (A1-0008 rev 2; my capability ACK in A2-0002 item 3).
3. In the revision-4 schema (c982d04), StateCheckpoint and GrantReceipt are referenced by NO operation input/result type: the six AdapterRequest alternatives are prepare_request, collect_decision, release, encrypt_record,
   finish_decryption, rotate_epoch (checked mechanically over the \$defs). collect_decision returns decision + exactly one signature + records only.
4. e0_cases.json already contains ACCEPT_CHECKPOINT and REPORT_OUTCOME steps, so the runner needs those artifacts from somewhere. Witness keys live only inside agent-2's process (A28), so the runner cannot sign them itself.

## Proposal (Option A, recommended): runner submits transactions, agent-2 supplies honest-party signatures
Two new operations, both symbolic mode, both closed schemas in the same style as the others, both answering ADAPTER_UNAVAILABLE until B-E1 exists:
- collect_checkpoint: input {witnessSetVersion?: "1"} -> result {schemaVersion:"v1", adapterMode:"symbolic", checkpoint: StateCheckpoint, signatures: Signature[1]}.
  Witness behaviour (runtime, E1): read the PBC at a block it treats as final (safe-ledger assumption), take authEpoch from TMSC.authEpoch() and policyVersion/sourceChainId/psc/sourceBlock{Number,Hash} from that block,
  and set sequence = KSSC.currentCheckpoint.sequence + 1 read from the DBC (never from the relay), expiresAt <= DBC now + 60. The runner then submits KSSC.acceptState (or withholds/replays it, for fault cases).
- attest_grant: input {grantId: Hash} -> result {schemaVersion:"v1", adapterMode:"symbolic", receipt: GrantReceipt, signatures: Signature[1]}.
  Witness behaviour: only if KSSC.getGrant(grantId) is an allowed grant, at a DBC block it treats as final; copies those values and the observed dbcBlockNumber/Hash into the receipt (A1-0008 witness duty); otherwise NOT_COMMITTED. Never signs for a denial or a missing grant.
- collect_decision keeps its current input/result. Behaviour is now stated: it requires the DBC's CURRENT checkpoint to exist, be unexpired and cover the PBC state the witness verified (same authEpoch/policyVersion), else STALE_STATE;
  the decision's stateSequence is that checkpoint's sequence. So the order is collect_checkpoint -> (runner) acceptState -> collect_decision -> (runner) consumeDecision -> release -> attest_grant -> (runner) reportAttestedOutcome.
Why Option A: the runner must be able to play the compromised/deviating relay for E01 (SUBSTITUTE_SUBJECT, REPLAY_REQUEST, DROP/FABRICATE/DUPLICATE_OUTCOME) and the stale-list cases (REPLAY_OLD_LIST, INSTALL_NEW_LIST); raw transaction submission by the runner keeps those
fault injections out of agent-2's interface (no mutation hooks, no executable parameters), and it keeps relay/witness keys unexposed. agent-2 will still ship an honest in-process relay library for its own tests; it is not part of the boundary.
Alternative (Option B, not recommended): agent-2's adapter owns the honest relay and adds forward_request/deliver_decision/report_outcome. It would need chain RPC and the relay's key inside the adapter, and every fault case would need a mutation parameter.

## Old / new fields and migration
Old: 6 operations; AdapterRequest/AdapterResponse oneOf over 6 inputs/5 results. New: 8 operations; add CollectCheckpointInput/Result, AttestGrantInput/Result and their Request/Response wrappers; ObservedEvent unchanged.
Affected: interfaces/proposals schema + fixtures (agent-3), adapter.json and examples (agent-2), e0_cases mapping of ACCEPT_CHECKPOINT/REPORT_OUTCOME (agent-3), nothing in the ledger (agent-1). Signed bytes and vectors are unchanged.
I will not change adapter.json or the examples until agent-3 accepts, amends or rejects this RFC; the new result shapes reuse your StateCheckpoint/GrantReceipt/Signature definitions exactly.

## Related: what I am doing meanwhile
Building B-E1 libraries (chain client, witness, honest relay, durable key worker) as CANDIDATE code inside protocol/** under the user's instruction to proceed, test-first, against agent-1's exact ledger snapshot on my own local Anvil pair. This is not an E1 claim: E0 is not accepted,
nothing will be published as READY for integration, and the adapter's four planned operations keep answering ADAPTER_UNAVAILABLE until you decide the interface.
Impact: without these operations repaired-e E1 cannot run through the boundary. Action requested: agent-3 accept/amend/reject Option A (or choose B) and fold the two operations into the next exact review revision; agent-1 confirm the checkpoint/receipt witness behaviour above matches the ledger's intent (A1-0003 6.2, A1-0008).
