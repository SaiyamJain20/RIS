Ledger E2 READY evidence (A1-0039). Agent 1, 2026-10-09 ~02:00-02:12 IST, agent 1's machine; Foundry/Anvil v1.8.5, solc 0.8.37,
CPython 3.13.5 venv (agent 2's protocol/requirements.txt) for the rehearsal, Python 3.14.7 stdlib for the ledger tools.
Contract sources, tests, Deploy/BootstrapFixture/FixtureConfig scripts, deploy_local.sh, bootstrap_fixture.sh, foundry.toml and the
ABI/vector/deployment exports are byte-identical to 9d6911d (the E1 pin) and to 91add8c's contract code.

Fresh runs at this tree (repository root):
  forge test --root ledger --offline                                   -> exit 0, 166 passed / 0 failed         (forge-test.txt)
  python3 -I ledger/tools/check_mutants.py <out>                        -> exit 0, 7/7 mutant suites detected     (check-mutants.txt)
  python3 -I ledger/tools/mutation_smoke.py <out>                       -> exit 0, 17/17 source mutants detected, 300 s (mutation-smoke.*)
  python3 -I ledger/tools/crosscheck_cast.py                            -> exit 0, 196 checks / 0 failures       (crosscheck-cast.txt)
  <venv>/bin/python -I ledger/tools/check_sign_list.py --out <dir>      -> exit 0, 24/24, 119 s                   (check-sign-list.txt)
  <venv>/bin/python -I ledger/tools/e2_rehearsal.py --protocol <git archive of agent-2 465aff5>/protocol \
      --cases <f7b8f3f e0_cases.json> --supplement <f7b8f3f e0_supplement_cases.json> --out <dir> --mutants
                                                                        -> exit 0: REHEARSED 50, MATCHED 50; the 6 crash cases
      not rehearsed (no hook); 1 extra non-catalog baseline row (kssc rewrite on repaired-e: WRONG_DESTINATION); live mutant probes:
      5 of 6 DETECTED (no-nonce, no-receipt-binding, no-state-barrier, no-record-freshness, no-version-monotone);
      mutant-no-destination-binding NOT killed by the catalog recipe (DV step 1 rejects first), code-level distinction under a
      kssc-only rewrite (guard WRONG_DESTINATION vs mutant WRONG_SUBJECT). No key or raw token in outputs.   (rehearsal/)
The rehearsal ran while forge test/check_mutants/crosscheck ran in the same ledger directory; all runs exited 0 and the
rehearsal's deployments passed their runtime use. rehearsal/ keeps summary.json, run-output.txt and per-world ledger-evidence.json
and deployment.json (adapter transcripts and produced lists are not copied; tokens were redacted at source anyway).
Limits: owner evidence; agent 1's runner/collector; one trial per case; machine-local addresses; not C-E2 or gate evidence.
