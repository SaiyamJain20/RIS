# Agent 1 handoff

## Current (2026-11-04, ~01:00): agent 2's revision 3 ACKed in ledger scope (A1-0097)

**A2-0043** (origin/agent-2 d4d5ff0, manifest 22e88c23..):

| File | sha256 |
|---|---|
| D50-DEPLOYMENT-BINDING.md | 73e6493a.. |
| SIGNING-RULES.md | c982ec8a.. |
| SUCCESSOR-WIRE.md | 54abfaa2.. |
| INVENTORY.md | ca65e530.. |
| vectors/d50_binding_vector.json | edd8d633.. |

**A1-0097:** ACK scoped to the ledger-facing items:
- the masked-build contract;
- the Governance contract-set rules;
- the wiring and sealed checks;
- the ledger-code mapping of the reason table.

It does not cover protocol internals or vector values.

**My side:**
- `check_masked_runtime.py` hardened: concatenation after validation. `offline-replay-hardened.txt` gives exit 0 and is identical; the negative control still exits 1.
- Design 2.2 §8: successor numbers are decimal strings.

**All F0 inputs are reviewed:**
- matrix rev 2 (A1-0091);
- design 2.2;
- A2 rev 3 (A1-0097).

**Next:** agent 3's final source/interface plan and exact ACK request.

## Previous (2026-11-04, later): design 2.2 export rule and offline replay (A1-0096)

**A3-0058** (origin/agent-3 0ed33c5) reviewed agent 2's input:
- it gave agent 2 five more amendments;
- it recorded A1-0095;
- it asked agent 1 for the immutable ranges and byte length.

**A1-0096:**
- `ledger/f0/A-F1-DESIGN.md` revision 2.2 §8: the exact `immutableReferences` rule and the masked-check acceptance conditions. Attestation scope: all 35 immutables are public, so the masked check plus the getters attest the constructor values; E CA-Admin sets are the exception.
- `ledger/tools/check_masked_runtime.py` gained `--save-code` and `--code-dir` and range validation.
- `ledger/evidence/f0-d50-masked/`:
  - `replay/` holds the raw code and deployment manifests;
  - `offline-replay.txt`: 18/18 match, equal to the online run;
  - `offline-negative-control.txt`: a flipped byte is detected.

**Not changed:** production and interfaces.

**Next:** review agent 2's next amended revision separately, then agent 3's final plan.

## Previous (2026-11-04): agent 2's revision 2 ACKed in ledger scope (A1-0095)

**A2-0042** (origin/agent-2 09dbb5b): manifest b606a335.., SIGNING-RULES 85887e38.., D50 cff58c3e.., INVENTORY 659ed463...
- C1–C4 verified in the diff.
- `TMSC.governance()` confirmed as a public view in design 2.1 §3.

**A1-0095:** ACK scoped to the ledger-facing items. It is not a freeze, choice, migration or protocol-internals ACK.

**All F0 inputs are now published:**
- matrix revision 2 (aded280a.., A1-0091);
- A-F1 design 2.1 (0d66f89a..);
- A2 F0 revision 2 (b606a335.., A1-0095).

**Next:** agent 3's final source/interface plan and exact ACK request. A-F1 code only after the F0 freeze.

## Previous (2026-11-03, late night): agent 2's F0 input reviewed (A1-0094)

**A2-0040/0041** (origin/agent-2 39af20f):

| File | sha256 |
|---|---|
| INVENTORY.md | 6210006e.. |
| SIGNING-RULES.md | 3d5ca717.. |
| D50-DEPLOYMENT-BINDING.md | f615e0f9.. |
| MANIFEST.sha256 | 2d9395aa.. |

**A1-0094:** not an ACK yet.
- Confirmed against the code: the §3 validation duties, the §5 receipt block rule, the §6 death predicates, F-30, and the D50 views for six contracts plus Governance per design 2.1.
- Corrections:
  - **C1:** min(request, checkpoint) is effect-equivalent, not "largest acceptable".
  - **C2:** monotone timestamps apply to the live ledger, not to `vm.warp`.
  - **C3:** add the storage wiring views `TMSC.psc/rsc`, `LSC.rsc/tmsc/psc`, and under F `TMSC.governance` and `Governance.target`.
  - **C4:** require `configured() == true`.
- Provenance: commit 39af20f is authored as `karma-skz`. Raised for the record, not as a finding.

**New tool:** `ledger/tools/check_masked_runtime.py`.

**New evidence:** `ledger/evidence/f0-d50-masked/`:
- masked live code equals the compiled runtime 18/18;
- on fresh chains the addresses are the same across repaired-e, paper-strict and mutant-no-nonce, but the raw code differs for TMSC, PSC, ACSC and KSSC;
- the Anvil chains were my own processes, stopped afterwards; the deployment outputs were kept out of the repository.

**Agreed:** the `immutableReferences` export for the successor schema (sorted `{start, length}`).

**Next:**
- agent 2's revision with C1–C4, which I will ACK;
- agent 3's final source/interface plan.

## Previous (2026-11-03, night): design revision 2.1 (A1-0093) after A3-0056

**A3-0056** (origin/agent-3 393d5ae):
- A1-0091 recorded as a scoped ledger ACK of revision 2 (aded280a..);
- design revision 2 reviewed: R1/R2/R3/R5 addressed, R4's core resolved.

**A1-0093 (revision 2.1)** changes two things:
- **Calldata claim:** authorization binds the decoded values; raw calldata is not canonical, trailing bytes are not rejected; no canonical-calldata claim.
- **Bit 7 control:** uses a repeatable SET_CA_ADMINS action. The baseline gives REPLAY with no repeated effects; the mutant repeats the effects; both have positive controls.

**Not changed:** source, tests and ABI.

**Waiting for:**
- agent 2's inventory, R6 and D50 for seven runtimes;
- then agent 3's final source/interface plan and the exact ACK request.

## Previous (2026-11-03, later): matrix revision 2 ACKed in ledger scope (A1-0091); design revision 2 (A1-0092)

**A3-0055** (origin/agent-3 80439e9):
- matrix revision 2, manifest aded280a.., with 29 scenarios;
- DESIGN-REVIEW.md, R1–R6.

**A1-0091:** a scoped ACK, covering ledger scope and revision 2's exact hashes.
- f_matrix.json 73b892ef..;
- fault-model.csv 6df6d357..;
- DESIGN-REVIEW.md 62a12dcd...
- It is not a freeze, choice or migration ACK.

**A1-0092:** `ledger/f0/A-F1-DESIGN.md` revision 2 (dda3914b..):

| Review item | Answer |
|---|---|
| R1 | Exact assertion-preserving E test edits: 8 `virtual`, 9 `isRepaired`, fixture parameters, q-aware signing of `witnessPk` |
| R2 | Tombstone: a removed root can never be re-added |
| R3 | Mutators take the signed nonce; nonce is set before the call; log binding; full events and getters; `IPolicyVersion` path |
| R4 | Typed `GovernanceAction` struct with `address[] admins`; no bytes payload; full precedence; bit 6 control signed over action=0; vector list |
| R5 | Interface v2 successor; seven runtimes for D-f |

**Not changed:** source, tests and ABI.

**Next:**
- agent 3's response and its exact source/interface plan;
- agent 2's R6, D50 and inventory, which are still missing.

## Previous (2026-11-03, evening): A3-0054 matrix reviewed; A-F1 design for review (A1-0090)

**A3-0054:** agent 3's F0 draft, at origin/agent-3 91062fd:
- `evaluation/evidence/fault-model.csv` has 14 components;
- `evaluation/scenarios/f_matrix.json` has 27 cases, all NOT_RUN;
- it accepts A1-0089.

**A1-0090:** my review. Not an ACK. It requests 7 changes:
1. evidence for F-14;
2. evidence for F-15;
3. evidence for F-21;
4. F-18 as a `mutant-f-q2` configuration;
5. F-24 split by e1;
6. new row F-28: authority removal across the barrier;
7. new row F-29: governance nonce after expiry, depending on the clock bound.

**`ledger/f0/A-F1-DESIGN.md`:** exact design for review only, not implemented:
- REPAIRED_F profile sites;
- `Governance.sol` type, payloads, nonce and expiry, check order and codes;
- TMSC governance mutators plus a `caAdmins` view;
- the KSSC policyVersion pin, through `IPolicyVersion` with no ABI change;
- mutation bits 6–8;
- vectors and the manifest;
- the E regression plan;
- conflict keys built on the domain separator. This withdraws the `(chainId, nonce)` shorthand.

**No code, test or ABI changed.**

**Next:** agent 3's revised matrix and design comments, and agent 2's D50 RFC and key inventory, which are still the gating input.

## Previous (2026-11-03): F0 quorum characterization addendum (A1-0089)

**What changed:**
- `ledger/test/F0Quorum.t.sol` adds 10 tests: 9 measure the **existing** QuorumLib with a test-only 4-witness KSSC at q=3, and 1 covers `sourceBlockNumber` poison.
- `ledger/tools/f0_controls.sh` now runs 12 controls.
- `ledger/f0/README.md`:
  - L8 and L12 are now tested;
  - the FL table has a column for the E test that measures each row;
  - the decision summary is corrected to defer to A1-0088.
- `actor-powers.csv` A05 evidence is updated.
- Successor manifest 96c9909d.. (301 entries).

**Commands and results:**

| Command | Result |
|---|---|
| `forge test --root ledger --match-path test/F0Quorum.t.sol` | exit 0, 10 passed. The first attempt failed to compile because of a test type bug; that output is kept. |
| `forge test --root ledger` | exit 0, 198 passed |
| `ledger/tools/f0_controls.sh <empty dir>` | exit 0, 12/12 sensitive |
| `python3 -I ledger/tools/check_f0_powers.py` | exit 0, `problems: []` |

**Not changed:** production ledger bytes (933d2a7), interfaces and gates.

**Waiting for:**
- agent 3's choices on A1-0088;
- agent 2's key-control enumeration and D50 RFC.

Neither has pushed since 2026-10-13.

## Previous (2026-10-14): grouped F0 RFC published (A1-0088); ledger F0 input accepted (A3-0053)

**A3-0053:** agent 3 accepted A1-0087 as reviewed F0 input.
- It ran on an exact snapshot: Forge 188 passed, the AST checker returned `problems: []`, and the manifest verified 296 of 296 entries.
- It did not re-run the 7 controls; it read them.
- It requested a grouped RFC.

**A1-0088 (RFC)** contains:
- C0, the common carrier:
  - a new `Profile.REPAIRED_F = 3`, with E profiles unchanged;
  - a 4-witness fixture with q=3 and set version 2;
  - F mutant bits;
  - keeping `QuorumLib`.
- D-a: governance actions, with a candidate `GovernanceAction` EIP-712 type.
- D-b: governance signers.
- D-c: global authEpoch.
- D-d: user-signature check on the DBC.
- D-e: poison checkpoints (pin policyVersion; recovery).
- D-f: what the ledger can expose to D50. Two things are not exposed today:
  - CA-Admin sets cannot be enumerated;
  - the exported `runtimeSha256` hashes compiled code with immutables zeroed, so it does not equal the on-chain code.

**Status of the choices:**
- Every choice in A1-0088 is UNRESOLVED; my recommendations are not approved scope.
- No source, test, ABI or interface changed.

**Next:** agent 3's choices and exact ACK requests. Then agent 2's D50 formula, which I ACK. A-F1 code starts only after the F0 freeze ACKs.

## Previous (2026-10-13): F0 ledger power matrix READY (A1-0087)

**Task:** F0, PLAN.md section 6, first bullet (agent 1 part), assigned in A3-0052. Base: common baseline 376347d (D51).

**Exported artifacts** (`ledger/f0/`, which README.md explains):

| File | Content |
|---|---|
| `ledger-state.csv` | 29 rows covering all 70 state variables |
| `entry-points.csv` | All 33 constructors and state-changing or placeholder entry points |
| `actor-powers.csv` | 12 actors |

**Consumers:**
- agent 3 for `fault-model.csv` and `f_matrix.json`;
- agent 2 for the B-F1 honest-witness checks and the D50 RFC.

**Commands and results** (repository root, Foundry 1.8.5, solc 0.8.37 hash 5de843c2..):

| Command | Result |
|---|---|
| `forge test --root ledger --match-path test/F0Powers.t.sol` | exit 0, 22 passed, expectations written before the first run |
| `forge test --root ledger` | exit 0, 188 passed |
| `ledger/tools/f0_controls.sh <empty scratch dir>` | exit 0, 7/7 sensitive. The first run matched no tests and is kept as `controls-run1-no-match.txt` |
| `python3 -I ledger/tools/check_f0_powers.py` | exit 0, `problems: []`. A negative control catches 3 injected errors |

**Evidence:** `ledger/evidence/f0-powers/`.

**Source manifest:** 186e28fb.. (296 entries). It only adds entries to 5b32e2c4... Production ledger bytes are unchanged since 933d2a7.

**Open decisions** (README D-a..D-f; agent 3 coordinates):

| Ref | Decision |
|---|---|
| D-a | Governance actions in core F |
| D-b | Old-set q=3 witness signers |
| D-c | Global authEpoch (L5) |
| D-d | User-signature check in `consumeDecision` (ABI change, needs an RFC) |
| D-e | Poison-checkpoint mitigation (L8) |
| D-f | Deployment verification, folded into D50 |

**Limits:**
- tests run in a single EVM with the E fixture (q=1);
- pre-seal deployer powers, ledger-operator powers, `sourceBlockNumber` poison and QuorumLib at n=4 are read, not tested;
- the checker proves coverage and citations, not the power claims;
- all review is correlated.

**Next action for the receiving agent:** read A1-0087 and `ledger/f0/README.md`. Agent 3 then folds the rows into the F0 matrix and asks for any RFCs it wants. A-F1 starts only after the F0 freeze ACKs.

## Previous (2026-10-12): gate E PASS (solo phase), board at F0

- **Decision recorded in `communication/GATES.md`:** "gate E PASS: solo phase, correlated review, criterion 4
  human-scoped (A1-0080), window cited from owner evidence (A1-0081), integrated mutants and window not run".
- **Three same-source ACKs**, each naming manifest 908fd615.., gate-evidence 47e38dd3.., RQ1-E.md 69dabfba.. and
  HEAD 871e218:
  - A1-0085 (agent 1);
  - S2-0023 (agent 2 (proxy));
  - S3-0024 (agent 3 (proxy)).
- **Gate run:** `evaluation/evidence/e3/gate-run-20261012/` (FREEZE S3-0021, plan c0086019.., exit 0, 56/56 rows,
  ProVerif matched).
- **Agent 1's independent review:** `ledger/evidence/gate-e-review/`. The eight tools in `ledger/tools/review_*.py`
  were committed before the FREEZE and pass 56/56 on the raw and the published copy (A1-0084).
- **Ledger code:** ledger pin 933d2a7 (c7b7dd51..) for every E2 and gate run. No ledger source change in the
  solo phase. New tools and evidence are review-only:
  - `ledger/tools/review_*.py`;
  - `ledger/evidence/sl*-review/`, `early-rows-review/`, `gate-e-review/`, `p3-mutant-suite-rerun/`.
- **Limits:**
  - all solo reviews are correlated self-review (A1-0059);
  - the integrated live mutant matrix and the integrated window were not run (A1-0079/A1-0080/A1-0081);
  - D47 paper crash rows;
  - single host, one trial per row, symbolic adapter.
- **Not done and not authorized:**
  - F work; it needs its own plan and the human's go-ahead;
  - pushing `main`, which is the human's decision.

The sections below are the earlier E0/E1 handoff snapshot, kept for history.

Status (2026-10-08 snapshot): **READY FOR INTEGRATION; not DONE.** Interface **v1 FROZEN** (E0-v1-r6-20261008, FREEZE.json
f700292e.. at agent-3 f7b8f3f); E0 closed and E1 unlocked by A3-0023; agent-1 mapping ACK A1-0027, A-E1 READY
A1-0028. Ledger READY items: A1-0030 (bootstrap producer, E1), **A1-0039 (E2 handoff: `ledger/E2_HANDOFF.md`, sign_list.sh, mutant kill map)**.
Latest inventory **A1-0046** (manifest 5b32e2c4.., 232 entries); contract code unchanged since 91add8c. Owner rehearsals (not C-E1/C-E2
results): E1 9/9 frozen controls with agent 2's adapter (A1-0033; agent 2 cross-ran 9/9), E2 47/47 rehearsable catalog
cases (A1-0035). **C-E1 COMPLETE: agent 3's actual integration 9/9 (A3-0030) under plan 78e195f5.. (A1-0038 ACK).** E2/E3 unlocked.

- **RQ/task and interface version:** E / sprint E0 close -> E1 integration (A1-0023). The ledger has: E0 deliverables, an A-E1
  draft, and A-E2 suites prepared before E1 integration, including the E03 GrantReceipt repair
  (A1-0008 revision 2, ACKed by agent 3 in A3-0005 and agent 2 in A2-0002, implemented in A1-0011).
- **Changed owned files and source manifest:** `ledger/**` (232 files) with SHA-256 in
  `ledger/evidence/source-manifest.sha256` (232 entries; file sha256
  5b32e2c47bc234192dc2bb98732ad1f00c9dfb81acc7f020d44806c2511c7ca7). Solidity sources, tests,
  scripts, foundry.toml and vectors are byte-identical to e6cf4ff (A1-0014). A1-0024 changes only the
  export label "v0 proposed" -> "v1" and regenerates the samples (`ledger/evidence/v1-export-run.txt`).
  A1-0026 adds the opt-in fast deploy (`tools/deploy_local.sh`). A1-0030 adds the TEST-ONLY bootstrap producer
  (`script/BootstrapFixture.s.sol`, `tools/bootstrap_fixture.sh`, `tools/check_bootstrap.py`; evidence
  `bootstrap-check.txt`). A1-0033 adds `tools/e1_rehearsal.py` and `evidence/e1-rehearsal/` (owner rehearsal,
  9/9 frozen E1 controls with agent 2's adapter). A1-0034 adds `script/SignList.s.sol`, `tools/sign_list.sh`, `tools/check_sign_list.py` and
  `evidence/signed-list-check/`. A1-0035 adds `tools/e2_rehearsal.py` and `evidence/e2-rehearsal/` (47/47 rehearsable catalog cases). A1-0039 adds `E2_HANDOFF.md`, live mutant probes in `e2_rehearsal.py` and `evidence/e2-ready/`. A1-0043 adds crash cases to `e2_rehearsal.py` and `evidence/e2-full-rehearsal/` (56/56 catalog). A1-0046 adds `tools/revocation_window.py` and `evidence/revocation-window/` (measured revocation window). Messages A1-0001..A1-0046.
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
