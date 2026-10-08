E2 OWNER REHEARSAL (A1-0035) - owner evidence, prepared AHEAD of E2 and disclosed; NOT a C-E2 result, NOT gate evidence.
Agent 1, 2026-10-08 ~23:15 IST, agent 1's machine, private Anvil pair (18545/28545, --block-time 1) started/stopped by the tool.

Command (repository root; CPython 3.13.5 venv with agent 2's protocol/requirements.txt; Foundry v1.8.5 on PATH):
  <venv>/bin/python -I ledger/tools/e2_rehearsal.py --protocol <git archive of origin/agent-2 465aff5>/protocol \
      --cases <f7b8f3f:interfaces/v1/scenarios/e0_cases.json> --supplement <f7b8f3f:interfaces/v1/scenarios/e0_supplement_cases.json> --out <dir>
  -> exit 0, 324 s: REHEARSED 47, MATCHED 47, NOT_REHEARSED 9, private keys/raw tokens in outputs: none (run-output.txt, summary.json).
Inputs: ledger = this commit (contract sources byte-identical to 91add8c); agent 2 = 465aff52688179fd983fd8da9e2af3032189ff6e, archive
  verified with its protocol/evidence/source-manifest.sha256 (eb236421.., 0 failures), unmodified; frozen catalog FREEZE f700292e...
Per profile: one deployment (deploy_local.sh, LEDGER_DEPLOY_FAST=1) + bootstrap producer + lists/registrations + one adapter process;
  every case uses a fresh request; adversarial steps use only relay/CA-admin keys; honest signatures from the adapter; inconsistent
  receipts from agent 2's TEST-ONLY deviating witness (--at-block = the honest receipt's block); trust lists from sign_list.sh.
Comparison with the frozen expectation: ACCEPT/CONDITIONAL <-> accepted with no error; REJECT/NO_NEW_GRANT/NO_NEW_OUTCOME <->
  native Rejected(<frozen error>) in a mined status-0 transaction; PENDING <-> PSC status FORWARDED.
  CONDITIONAL paper rows are counted as consistent when the stress action is accepted; their SPEC_GAP classification is agent 3's.
NOT_REHEARSED (9): E01-wrong-destination x3 (needs a certificate genuinely issued for a second destination deployment);
  E03-crash-after-intent/-send x3 profiles (no crash hook through the adapter process; agent 2 posted a text-only draft hook design).
Native facts worth noting (ledger-evidence.json, summary.json "native"):
  - expiry-boundary: the deciding DBC block timestamp EQUALS request.expiresAt (pinned with evm_setNextBlockTimestamp after a
    real-time wait): paper policyEnf grants at equality; repaired-e consumeDecision rejects EXPIRED at equality.
  - paper subject substitution: GrantIssued.gid = Bob for Alice's request (relay-asserted gid; SPEC_GAP).
  - post-barrier revocation (repaired-e): STALE_STATE and nonceConsumed stays false; pre-barrier: grant inside the designed window.
  - duplicate outcome (repaired-e): the duplicate resubmits the SAME receipt; the honest witness also refuses a fresh attestation once
    the outcome is recorded (attest_grant -> WRONG_SUBJECT), observed in the first run.
Disclosure: the first run (exit 1) had 45/47 with two HARNESS errors, both in agent 1's harness: (1) duplicate-outcome asked the
  witness for a second attestation (refused, see above); (2) expiry-boundary in repaired-e ran after the paper runs had moved the shared
  DBC clock ~20 s ahead with evm_setNextBlockTimestamp, so the witness correctly refused an already-expired request. Both were fixed
  in the harness (same receipt; real-time wait before pinning the timestamp) and the whole rehearsal re-run from fresh chains.
  No module behaviour changed between the runs. This README's evidence is the re-run.
Limits: one machine; one trial per case; agent 1's runner and collector (not agent 3's independent oracle); symbolic mode; TEST-ONLY
  keys; machine-local addresses/timestamps.
