E2 signed-list producer live check (A1-0034) - owner evidence, NOT an E2 case result.
Agent 1, 2026-10-08 ~23:03 IST, agent 1's machine; private Anvil pair (18545/28545, --block-time 1), started and stopped by the check.
Command (repository root; CPython 3.13.5 venv with eth-account 0.14.0/eth-abi; Foundry v1.8.5 on PATH):
  <venv>/bin/python -I ledger/tools/check_sign_list.py --out <dir>   -> exit 0, 117 s, 24/24 OK (run-output.txt, summary.json)
Per profile: deploy (LEDGER_DEPLOY_FAST=1) -> bootstrap (A1-0030) -> lists from ledger/tools/sign_list.sh, submitted by the right
CA-Admin; TMSC.checkCredentials(alice) at the PBC head after each step:
  1 TempACL with Alice OnDuty ending in 3 s -> after 5 s: EXPIRED (all profiles)
  2 TempACL restored (next version)        -> NONE
  3 H1 CRL revoking serial 101              -> REVOKED
  4 replay of the bootstrap's older signed H1 CRL -> paper-strict/paper-minimal: ACCEPTED and Alice NONE again (rollback, SPEC_GAP);
                                                    repaired-e: Rejected(STALE_ANCHOR) and Alice stays REVOKED
  5 equal version, different content (H1 CRL, --version current) -> paper: ACCEPTED; repaired-e: Rejected(STALE_ANCHOR)
  6 refusals: unknown authority H9 and a DBC RPC -> exit 1, no output file
Disclosure: a first run exited 1 (22/24) because the check's expectation table had a typo for step 4's submission result on the
paper profiles ("NONE" instead of "ACCEPT"); the observed ledger behaviour (paper accepts the old list) was the same as here. Its
output was not kept. The table was fixed and the whole check re-run from fresh chains; run-output.txt is that re-run.
Schema: the 12 produced signed lists (48 leaves: RevocationList/TemporalAcl, Signature, Address x2) are valid against frozen
interfaces/v1/hmbc.schema.json (4c22092d.., jsonschema 4.26.0). Private-key hex of 10 synthetic labels: 0 occurrences.
Regression after adding two list-valued envOr declarations to test/utils/Vm.sol: forge test 166/0; check_mutants 7/7.
Files: summary.json, run-output.txt, per profile submissions.json (tx hashes, versions, statuses, expected reverts) and three sample
signed lists (machine-local addresses).
Limits: owner check of the producer and of ledger-native E02 trust-anchor behaviour; not agent 3's E2 schedules or oracle.
