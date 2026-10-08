# Agent 1 handoff

Status: **READY FOR INTEGRATION; not DONE.** Current ledger READY is **A1-0030** (producer); latest inventory **A1-0034** (manifest b99b83e5..,
143 entries; adds the E1 owner rehearsal (A1-0033) and the E2 signed-list producer; contract code unchanged since 91add8c). Interface: candidate
v1 revision 6 (df2a306f..), adopted as the Phase E sprint working interface in A1-0023 (human
directive: complete E by 00:10 IST 2026-10-09). Agent-1 revision-6 ledger ACK: A1-0022. No integrated
run has happened yet.

- **RQ/task and interface version:** E / sprint E0 close -> E1 integration (A1-0023). The ledger has: E0 deliverables, an A-E1
  draft, and A-E2 suites prepared before E1 integration, including the E03 GrantReceipt repair
  (A1-0008 revision 2, ACKed by agent 3 in A3-0005 and agent 2 in A2-0002, implemented in A1-0011).
- **Changed owned files and source manifest:** `ledger/**` (100 files) with SHA-256 in
  `ledger/evidence/source-manifest.sha256` (143 entries; file sha256
  b99b83e509a4ce42992df63a6fdbf42300756cef07942720e8a711ebed697fe7). Solidity sources, tests,
  scripts, foundry.toml and vectors are byte-identical to e6cf4ff (A1-0014). A1-0024 changes only the
  export label "v0 proposed" -> "v1" and regenerates the samples (`ledger/evidence/v1-export-run.txt`).
  A1-0026 adds the opt-in fast deploy (`tools/deploy_local.sh`). A1-0030 adds the TEST-ONLY bootstrap producer
  (`script/BootstrapFixture.s.sol`, `tools/bootstrap_fixture.sh`, `tools/check_bootstrap.py`; evidence
  `bootstrap-check.txt`). A1-0033 adds `tools/e1_rehearsal.py` and `evidence/e1-rehearsal/` (owner rehearsal,
  9/9 frozen E1 controls with agent 2's adapter). A1-0034 adds `script/SignList.s.sol`, `tools/sign_list.sh`, `tools/check_sign_list.py` and
  `evidence/signed-list-check/`. Messages A1-0001..A1-0034.
- **Exported artifacts and consumers:**
  - ABIs: `ledger/exports/abi/*.json` + `manifest.json` (cea42704.., label v1; ABI JSON unchanged since 54262c2).
  - Vectors: `ledger/exports/vectors/eip712-v0-ledger.json` (6aa399e0..; 9 signed types incl.
    GrantReceipt, plus credentialDigest) + `typed/*.json`.
  - Samples: `ledger/exports/deployments/sample-{paper-strict,paper-minimal,repaired-e,mutant-no-receipt-binding}/`
    (labelled `interfaceVersion: "v1"`, valid against revision-6 `LedgerDeployment`; machine-local RPC/addresses).
  - Tools: `ledger/tools/deploy_local.sh` and `e2e_smoke.sh`.
  - Consumers: agent 2 (relay, witness, worker), agent 3 (runner, schema).
- **Exact commands, exit codes, evidence** (repository root, Foundry v1.8.5, solc 0.8.37):
  - `forge test --root ledger` -> exit 0, 166 passed / 0 failed (`ledger/evidence/forge-test.txt`)
  - policy test-first run -> 2 expected failures before the ACSC change (`policy-first-run.txt`)
  - receipt test-first run against a stub -> 11 expected failures (`receipt-first-run.txt`);
    A-E2 first run -> 63/63 matched pre-written expectations (`ae2-first-run.txt`)
  - `python3 -I ledger/tools/check_mutants.py ledger/evidence/ae2-mutants.json` -> exit 0, 7/7 mutant suites detected
  - `python3 -I ledger/tools/mutation_smoke.py ledger/evidence/ae1-mutation-smoke.json` -> exit 0, 17/17 detected (baseline 166/0)
  - `python3 -I ledger/tools/crosscheck_cast.py` -> exit 0, 196 checks / 0 failures
  - `forge build --root ledger && python3 -I ledger/tools/export_abi.py` -> exit 0
  - `DEPLOYER_PK=<anvil key 0> ledger/tools/deploy_local.sh <pbc-rpc> <dbc-rpc> <profile> complete-details sample-<profile>`
    then `ledger/tools/e2e_smoke.sh <pbc-rpc> <dbc-rpc> <deployment.json> 1` -> exit 0 for all 4 samples
    (Anvil `--block-time 1`, 5 stages including `dbc-receipt`)
  - historical `TMSC.checkCredentials` read across a revocation (`historical-read-check.txt`)
  - independent reproduction by peers: agent 3 (A3-0008) re-ran 162/0, 196/0, 7 mutants and 33
    export checks at 54262c2; agent 2 (A2-0003) reproduced all 9 signed vectors including GrantReceipt
- **Valid controls and deliberately failing mutants:** Alice's positive grant and outcome in all
  profiles and on live chains; Bob, temporal-only and unregistered denials. 6 `mutant-*` deployments
  (bits 1/2/4/8/16/32) are detected by named repaired-e tests. 17 throwaway source edits are detected
  separately. Results matrix: `ledger/evidence/ae2-property-matrix.md`.
- **Remaining assumptions, failures and limits:**
  - The A-E1 tests were not written failing-first (A1-0004).
  - A-E2 was prepared before E1 integration.
  - The KSSC holds no secrets (SPEC section 3). Single DBC, single witness (E).
  - The GrantReceipt proves an allowed DBC grant existed. It does not prove delivery. Block hashes
    are not verified on chain.
  - The live smoke signs inside Forge.
  - A first live run was rejected with STALE_STATE because of cross-chain clock skew (A1-0004). This
    led to the DBC-time rule (D22).
- **Interface RFCs/ACK message IDs:**
  - Agent 1 sent: RFCs A1-0001/0003/0005/0008; REVIEWs A1-0002/0007/0013; ACKs A1-0009/0012;
    READYs A1-0004/0006/0010/0011/0014.
  - Peer ACKs received: A3-0001/0005/0008/0010 (agent 3); A2-0002/0003/0005 (agent 2, scoped).
- **Reproduction steps for the receiving agent:** install Foundry v1.8.5 (verify the asset hash in
  `ledger/toolchain.json`). Extract `ledger/` from the A1-0014 commit into a scratch directory and run the
  commands above. Python tools use only the standard library; `cast` must be on PATH for the
  crosscheck.
- **Files to freeze and integration prerequisites:** `ledger/src/**`, `ledger/script/**`,
  `ledger/foundry.toml` and `ledger/exports/**` at the pinned commit once v1 is frozen. Integration
  needs two chains with ids 18545/28545, interval mining (or a runner-controlled clock), a funded
  deployer key, and a node that serves historical state (witness reads).

Writer: agent 1 only. This snapshot never replaces the immutable READY message.
