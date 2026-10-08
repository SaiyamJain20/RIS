E1 OWNER REHEARSAL (A1-0032/A1-0033) - owner evidence, NOT a C-E1 result, NOT gate evidence.
Agent 1, 2026-10-08 ~22:55 IST, agent 1's machine. Agent 3 (C-E1 owner) was paused; nothing here replaces its runner or oracle.

What ran: ledger/tools/e1_rehearsal.py (this commit). It starts a private Anvil pair (18545/28545, --block-time 1), and for
paper-strict, paper-minimal and repaired-e:
  agent-1 deploy_local.sh (LEDGER_DEPLOY_FAST=1) -> agent-1 bootstrap_fixture.sh (A1-0030) ->
  WrongIssuerAdmin: H2 list from H1-ca-admin first (A2-0015 section 3) -> trust lists and registrations ->
  agent-2's UNMODIFIED adapter process (`python -m hmbc_protocol.adapter --state-dir <0700 dir> --deployment <file>`) for every
  user/witness signature and worker action (encrypt_record, prepare_request, collect_checkpoint, collect_decision, release,
  finish_decryption, attest_grant) -> the runner role is played by the script with ONLY the TEST-ONLY relay and H1/H2-ca-admin
  keys (Option A): requestAccess, acceptState, consumeDecision / policyEnf, reportAttestedOutcome / reportOutcome.
Each control is compared with the frozen interfaces/v1/scenarios/e_positive.json expectedEvents/expectedError, plus native checks:
  - WrongIssuerAdmin: a mined status-0 tx with Rejected(16), no events, authEpoch unchanged, H2 anchor unpublished.
  - Bob: DBC AccessLog allowed=false code 9 (POLICY_DENIED), no grant, nonceConsumed(bob, 7) == false.
  - Alice: AccessForwarded with requestLogId != 0; AccessLog allowed plus GrantIssued; worker RELEASE_INTENT/RELEASE_SENT for that
    grant plus finish_decryption decryptable; AttestedOutcomeRecorded/OutcomeRecorded plus PSC.getRequest status 2.

Command (repository root):
  <venv: CPython 3.13.5 + protocol/requirements.txt (eth-account 0.14.0, jsonschema 4.26.0, pytest 9.0.2)>/bin/python -I \
    ledger/tools/e1_rehearsal.py --protocol <git archive of origin/agent-2 dbfefee>/protocol --out <dir>
  -> exit 0, 84 s; run-output.txt: 9/9 MATCH; summary.json allMatch true; privateKeysInOutputs [].
Inputs: ledger = this commit (contract sources byte-identical to 91add8c/9d6911d); agent-2 = dbfefee2dd079b400191eba7bca4b3e117e2caef,
  archive verified against its protocol/evidence/source-manifest.sha256 (02676d6e.., `sha256sum -c` 0 failures), not edited.
  Foundry v1.8.5, solc 0.8.37. Frozen expectations: FREEZE f700292e.. (E0-v1-r6-20261008).

Per profile: deployment.json, bootstrap.json, ledger-evidence.json (every tx hash, block, status, expected revert and decoded
events), worker-log.json (agent 2's read-only export), adapter-transcript.json (adapter requests/responses; release tokens are
replaced by keccak256(token) - no raw token, no private key).

Integration finding F-1 (agent 2's to fix; no ledger impact): A2-0014 section 2 says to read evidence with
`python -m hmbc_protocol.worker_log --state-dir <same dir>` as the adapter's --state-dir. The adapter keeps the worker database
in <state-dir>/worker (adapter.py `_worker`), so the documented command exits 1 ("no worker.sqlite"). The rehearsal passes
<state-dir>/worker.

Limits: one machine; private Anvil pair; the runner and the collector are agent 1's script (not agent 3's independent oracle);
one trial per control; symbolic mode; TEST-ONLY synthetic keys; E1 controls only (no E2 schedule ran). Machine-local addresses
and timestamps.
