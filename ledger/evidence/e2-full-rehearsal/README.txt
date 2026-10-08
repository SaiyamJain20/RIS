Complete E2 catalog OWNER rehearsal (A1-0043; A1-0041 W-1). Owner evidence only: NOT C-E2, NOT gate evidence; classification is agent 3's.
Agent 1, 2026-10-09 ~03:15-03:33 IST, agent 1's machine; Foundry/Anvil v1.8.5, solc 0.8.37, CPython 3.13.5 venv (agent 2's requirements).
Command (repository root):
  <venv>/bin/python -I ledger/tools/e2_rehearsal.py --protocol <git archive of agent-2 0716a8e>/protocol \
      --cases <f7b8f3f e0_cases.json> --supplement <f7b8f3f e0_supplement_cases.json> --out <dir> --mutants
  -> exit 0: REHEARSED 56, MATCHED 56 (all 48 catalog cases x profiles + 8 repaired-e supplement controls); 1 extra non-catalog row
     (kssc-only rewrite on repaired-e -> WRONG_DESTINATION); mutant probes 5/6 DETECTED, no-destination-binding NOT killed by the
     catalog recipe (DV step 1 first) with a code-level distinction under the kssc rewrite (guard WRONG_DESTINATION, mutant
     WRONG_SUBJECT); no key or raw token in outputs.
Inputs: agent 2 0716a8e2d46f985f35a612d42acaae02ab8701a4 (manifest d16ddad8.., verified; production hmbc_protocol/exports/abi byte-identical
  to the E1 pin 465aff5) including the CANDIDATE TEST-ONLY crash hook `testtools.faulty_adapter` (A2-0020), which agent 3 has not decided on.
Crash cases (6): grant -> encrypt_record + release on the faulty process (after_intent: EOF + exit 86; after_send: one response + exit 86;
  stderr empty) -> worker_log -> PRODUCTION adapter on the same state dir -> release -> worker_log -> REPORT_OUTCOME (status 2) -> wait
  for grant expiry -> retry EXPIRED with 0 new events. All six equal the frozen expected.worker
  (intent 1, sent 1 | 2, sameCachedResponse true, delivery unknown, expiredRetryError EXPIRED). The paper crash classification stays
  agent 3's (frozen BLOCKED/UNPROVED); the rehearsal only reports observations.
Files: summary.json, run-output.txt, per world ledger-evidence.json + deployment.json (incl. second-destination worlds and mutant worlds).
Limits: one machine; agent 1's runner/collector; one trial per case; symbolic mode; TEST-ONLY keys; machine-local addresses.
