# Agent 1 handoff

Status: **READY FOR REVIEW (E0 deliverables, A-E1 draft, A-E2 preparation); not DONE.** Interface v0
is not frozen and no integration has run. Full detail: outbox A1-0004 (E0/A-E1) and A1-0006 (A-E2 prep).

- **RQ/task and interface version:** E / E0 (toolchain, vectors, ABI, source review), an A-E1 draft, and
  A-E2 preparation done before E1 integration. Interface v0 proposed; ledger proposals A1-0003 and A1-0005.
- **Changed owned files and source manifest:** `ledger/**` (86 files) listed with SHA-256 in
  `ledger/evidence/source-manifest.sha256` (file sha256
  4d7802b70d731cf5ba3ac3b38fac32ffddaf0400d5b0e7fccfb9117815bfd577). Messages A1-0001..A1-0006.
  Branch `agent-1` on origin (user's multi-machine instruction, A1-0001).
- **Exported artifacts and consumers:** `ledger/exports/abi/*.json` + `manifest.json` (agent 2,
  agent 3); `ledger/exports/vectors/eip712-v0-ledger.json` + `typed/*.json` (agent 2 digest check,
  agent 3 freeze); `ledger/exports/deployments/sample-{repaired-e,paper-strict}/deployment.json`
  (sample manifest schema; machine-local addresses); `ledger/tools/deploy_local.sh` (agent 3 runner).
- **Exact commands, exit codes, evidence:** run from the repository root, Foundry v1.8.5, solc 0.8.37:
  - `forge test --root ledger` -> exit 0, 151 passed / 0 failed (`ledger/evidence/forge-test.txt`)
  - A-E2 first run -> 63/63 matched pre-written expectations (`ledger/evidence/ae2-first-run.txt`)
  - `python3 -I ledger/tools/check_mutants.py ledger/evidence/ae2-mutants.json` -> exit 0, 6/6 suites detected
  - `FOUNDRY_PROFILE=pending forge test --root ledger` -> exit 1 as expected (E03 outcome-evidence control)
  - `forge script ledger/script/ExportVectors.s.sol:ExportVectors --root ledger` -> exit 0
  - `python3 -I ledger/tools/crosscheck_cast.py` -> exit 0, 166 checks / 0 failures
  - `python3 -I ledger/tools/mutation_smoke.py ledger/evidence/ae1-mutation-smoke.json` -> exit 0, 15/15 detected (baseline 151/0)
  - `forge build --root ledger && python3 -I ledger/tools/export_abi.py` -> exit 0
  - `DEPLOYER_PK=<anvil key 0> ledger/tools/deploy_local.sh http://127.0.0.1:38545 http://127.0.0.1:48545 <profile> complete-details sample-<profile>`
    for paper-strict, paper-minimal, repaired-e, mutant-no-nonce, then `ledger/tools/e2e_smoke.sh ... 1` -> all exit 0
    (two Anvil chains, `--block-time 1`)
- **Valid controls and deliberately failing mutants:** Alice positive grant in all 3 profiles and on
  live chains; Bob, temporal-only and unregistered denials. `mutant-*` deployments (5) are detected by
  named repaired-e tests (`tools/check_mutants.py`). 15 throwaway source edits are separately detected
  (`tools/mutation_smoke.py`). Case-to-property results: `ledger/evidence/ae2-property-matrix.md`.
- **Remaining assumptions, failures and blockers:** the A-E1 tests were not written failing-first
  (stated in A1-0004). Waiting on: the agent 3 v1 freeze and decisions (A1-0002 section 4, A1-0003
  section 6, the clock-domain rule) and agent 2's Python vector check. The KSSC holds no secrets
  (SPEC section 3). Single DBC. The live smoke signs inside Forge. A first live run failed STALE_STATE
  because of a cross-chain clock skew (explained in A1-0004).
- **Interface RFCs/ACK message IDs:** RFCs A1-0001 (Git convention), A1-0003 (v1 ledger types) and
  A1-0005 (GrantReceipt, mutant profiles, clock domain); REVIEW A1-0002; READY A1-0004 and A1-0006.
  No ACKs received yet.
- **Reproduction steps for the receiving agent:** install Foundry v1.8.5 (verify the release-asset
  hash in `ledger/toolchain.json`), `git fetch origin agent-1`, check out `ledger/` in a scratch
  clone, and run the commands above. Python tools need only the standard library; cast must be on
  PATH for the crosscheck.
- **Files to freeze and integration prerequisites:** `ledger/src/**`, `ledger/script/**`,
  `ledger/foundry.toml`, `ledger/exports/abi/**` once v1 is frozen. Integration needs two chains with
  ids 18545/28545 and interval mining (or a runner-controlled clock), and a funded deployer key on
  both.

Writer: agent 1 only. This snapshot never replaces the immutable READY message.
