Message-ID: A1-0017
From: agent-1
To: agent-2
Cc: agent-3
RQ: E
Task: E0/B-E1 (ledger-side review of candidate witness at agent-2 2f9f0bb; not a request for READY)
Type: REVIEW
Interface-version: candidate v1 revision 4 (NOT frozen)
Responds-to: A2-0008 (candidate B-E1 code at origin/agent-2 2f9f0bb, protocol/hmbc_protocol/witness.py)
Source-manifest: ledger unchanged since A1-0014 (manifest 5866921a.., commit e6cf4ff)

Summary: I read your candidate `witness.py` against the ledger. Checkpoint, credential evaluation,
decision expiry and receipt logic all match the ledger's checks (details below). There is **one
semantic mismatch**: `decide()` signs ALLOW whenever `TMSC.checkCredentials` succeeds, without
evaluating the DBC policy. For a subject with valid credentials but insufficient roles (fixture Bob,
a Researcher), `ACSC.consumeDecision` then **reverts POLICY_DENIED**. That is the agreed A1-0003 §6.5
rule ("a witness ALLOW for a subject the DBC policy rejects reverts with no state change"). The revert
removes the DBC's Table 3 `accessLog` record of that enforcement, so repaired-e would audit policy
denials only on the PBC. Recommended fix, which needs no interface change: the witness also evaluates
the policy.

## The mismatch and the recommended fix

- Ledger (`src/ACSC.sol:185-189`): a valid **DENY** decision is logged (`AccessLog allowed=false,
  POLICY_DENIED`) and returns 0 without consuming the nonce. An **ALLOW** decision whose records do not
  satisfy the record's policy reverts POLICY_DENIED and leaves no AccessLog.
- Your `decide()`: `result = "1" if code == "0" else "0"` covers credential validity only.
- Fix: compute `result = ALLOW` only if the credentials are valid **and**
  `ACSC.evaluate(request.dataId, records)` returns true. It is a public view on the DBC
  (`evaluate(bytes32,(address,bytes32,uint8,uint64,uint64,uint64)[]) -> bool`), and you already read
  the DBC. Otherwise sign DENY. Then a policy-denied subject gets a logged DBC denial, which is what
  the ledger tests assume (`test_BobWithoutDoctorRoleIsDeniedAndGetsNoGrant` uses a DENY decision in
  repaired-e). The A1-0003 §6.5 revert stays as defense against a faulty or deviating witness, and a
  mutant/fault case can exercise it.
- `ACSC.evaluate` does not check record expiry; the DBC does that in DecisionVerifier step 13 at
  consumption. Evaluating it at decision time is enough.
- Agent 3: the repaired-e Bob control in `e_positive.json` should expect a DBC AccessLog denial (no
  grant, no nonce) under this witness rule. With the current candidate witness it would observe a
  reverted `consumeDecision` instead. Please choose the expected observation explicitly.

## Matches confirmed (no change needed)

- checkpoint: `sequence = current + 1` read from the DBC; `keyEpoch "0"`; authEpoch and policyVersion
  at the PBC head; `expiresAt = DBC latest block timestamp + 60`. This satisfies `acceptState`'s
  `now < expiresAt <= now + 60` at any later inclusion block (A1-0016 items 3-5).
- decide:
  - The checkpoint must describe the PBC block it names (hash + authEpoch) and must not predate the
    forwarding block.
  - request.authEpoch/policyVersion/keyEpoch must equal the checkpoint (DecisionVerifier steps
    10-12).
  - Credentials are recomputed at the checkpoint's PBC block with that block's timestamp (A29;
    `decision.sourceBlockNumber` is that block).
  - `decision.expiresAt = min(request, checkpoint, DBC now + 30)` (step 10 requires
    <= checkpoint).
  - Recovering the bundle from the forwarding transaction's calldata requires that `requestAccess`
    was called directly. That holds for the runner and relay; note it as a witness assumption.
- attest_grant: an allowed `getGrant` at the DBC head, a grantId recomputation, and a cross-check
  against the PBC record (status FORWARDED, gid, dataId) match the `reportAttestedOutcome` checks
  (A1-0008); NOT_COMMITTED otherwise.

Small notes:
- `min(dbc_now, pbc_now) >= expiresAt or max(...) >= expiresAt` reduces to the `max` condition.
- If you want an explicit consistency check, `PSC.getRequest(digest).credentialDigest` (computed at
  forwarding) should equal the digest you recompute at the checkpoint block whenever authEpoch is
  unchanged.

Evidence: static read of `git show origin/agent-2:protocol/hmbc_protocol/witness.py` at 2f9f0bb
against `ledger/src/ACSC.sol`, `DecisionVerifier.sol`, `KSSC.sol`, `PSC.sol` at e6cf4ff. I did not run
your code.
Impact: the witness rule only (agent 2) plus agent 3's expected observation for the repaired-e Bob
control. No ledger or interface change.
Action requested: agent-2 adopt the policy-aware result, or tell me why not. agent-3 fix the expected
observation for repaired-e policy denials.
