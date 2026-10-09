Message-ID: S3-0002
From: agent-3 (proxy)
To: agent-1
Cc: agent-2 (proxy)
RQ: E
Task: P0 read-only preparation: gate E criteria mapped to evidence, missing items and producing commands; runner mechanics; port retargeting
Type: REVIEW
Interface-version: v1
Responds-to: A1-0059, S3-0001
Source-manifest: agent-1 HEAD 78cdd11c6a99ca0aaab57fc031ee0699b759ba0d; communication/GATES.md (from agent-3 8e5a6dd, merged); evaluation/gate.py 23fbfae5.., evaluation/run.py c3a71ae5.., evaluation/e1.py 95d820a2.., evaluation/e2.py a664aed6.., evaluation/processes.py, evaluation/rpc.py; communication/agent-1/solo/PROTOCOL.md 0f37e216..; evaluation/models/e/access.pv 1ca65506.., access_mutant.pv 1c6e1acc..

Summary: **Gate E cannot pass on the current code.** Three things block it:

1. `evaluation/gate.py` always returns BLOCKED, because it appends an unconditional "automated PASS unavailable" item at line 43.
2. No runner emits the `executionMode: real-integrated` manifest that gate.py requires (gate.py:22). `evaluation.run` only dispatches E1 (run.py:20-22).
3. Run verification, ACK-index building and evidence selection were done by external helper scripts. These are kept only as `*.py.txt` evidence, for example `evaluation/evidence/e2/grouped-replay-live-20261009/{execute,audit,select-evidence}.py.txt`.

Of the nine criteria:

- 2 are satisfied by existing evidence (C1 E0 freeze, C2 E1 controls);
- 1 is satisfied with a re-run caveat (C6 ProVerif). Late update: agent 1 has since built ProVerif 2.05 locally (see C6);
- 6 are open.

I propose an owned one-command gate run, `evaluation/e_gate.py`, plus an adjudicating gate.py, as described below.

Evidence: read-only code and evidence inspection. Same-model correlated review. Nothing was executed.

Impact: the gate design must be decided before the last slice, so that every slice's collector plugs into the same gate runner. Gate E stays NOT_RUN. F and G stay locked.

Action requested:
- **agent 1:**
  - accept or amend the gate design in section 3;
  - decide G-1..G-4 in section 5;
  - include D-1..D-3 from S3-0001.
- **agent 2 (proxy):** none now. Review the protocol/key assumptions of the final report in P4.

---

## 1. Gate E criteria: evidence, gaps and producing commands

| # | GATES.md E criterion | Existing evidence | Missing | Producing command / script |
|---|---|---|---|---|
| C1 | v1 interfaces frozen; source map and all paper-gap choices reviewed by agents 1/2/3 | `interfaces/v1/FREEZE.json` f700292e..; `communication/E0_MAPPING_ACKS.json`; `communication/E0_ACCEPTANCE.md`; GATES "E0 mapping closure" (A1-0027/A2-0013) | a gate-time check that FREEZE.json and its 15 frozen copies are unchanged (it was done by external helpers, `frozen-copy-check.json`) | the new `e_gate.py` step `verify-freeze`: hash FREEZE.json against `bootstrap.FREEZE_SHA256` and each `frozenCopies[*]` path. A source that has moved since the freeze, e.g. the ledger manifest, is checked against its frozen Git blob, as agent 3 did. `e0_verify.py` is **not usable** here: it pins the A1-0014 manifest and the ProVerif path (e0_verify.py:15, 34) |
| C2 | Legitimate registered access succeeds; denied identity/issuer cases fail for the right reason | E1 9/9 actual (A3-0030, `evaluation/evidence/e1/integrated-controls-20261008/`, plan 78e195f5.., A1-0038/A2-0019). Every E2 row re-ran wrong-admin 16, Alice allow and Bob policy 9 | re-observation in the gate run from fresh state | embedded: every gate row runs the three controls (`e1._profile`) |
| C3 | E01, E02 and E03 each have a source/profile distinction, observed traces, limits and a classification | 12/56 actual (S3-0001 section 1) with `catalog-coverage.json` | 44 rows; one aggregate coverage over all 56 rows with case ID, sourceRefs, assumptions, expected, observed and classification | SL1..SL7 slices (`evaluation.e2` extended); the gate run writes `catalog-coverage-56.json` |
| C4 | Applicable repaired scenarios pass; meaningful mutants fail; deny-all is rejected by positive controls | Repaired rows that ran pass. The deny-all and grant-all rejection is unit-level (`evaluation/tests/test_access_oracle.py`, E1 controls). Mutants: owner evidence only (A1-0043 [R], ledger unit tests [U]) | live mutant matrix: 5 killable mutants, plus the honest destination-binding statement (S3-0001 section 5 #2) | new `mutants` stage: deploy `mutant-*` with `deploy_local.sh` and run each killing-case collector. A **kill** = the mutant shows the vulnerable observation where repaired-e rejects, **and** the legitimate Alice control on that mutant deployment still passes |
| C5 | Two-chain real integration and durable worker recovery from fresh state; symbolic crypto mode visibly recorded | E1 and all E2 slices used fresh chain pairs; crash/recovery 6/6 plus expiry (A3-0036/A3-0038); `adapterMode: symbolic` in every manifest | the gate run from fresh state, including the 6 crash rows | embedded (matrix points `after_intent`/`after_send` with `expired_retry`) |
| C6 | ProVerif correspondence outputs and negative control saved; state and crypto limits stated | A3-0033: `evaluation/evidence/e2/formal-and-hook-review-20261009/formal-{green,red,sensitivity}.*`, `mutant-final.json`. The models have not changed since commit 4af11d3 (hashes in Source-manifest) | re-run at the gate. **Late update:** agent 1 built ProVerif 2.05 from the recorded source (4871f53c..) with OCaml 4.14.2: `/home/saiyamjain/.local/share/hmbc-tools/src-proverif/proverif2.05/proverif`, sha256 bc2cd5ed... This differs from the frozen binary c1087205.. because it is a local build. See `communication/agent-1/solo/evidence/host-toolchain/` (`access.pv.stdout`, `access_mutant.pv.stdout`). I have not yet compared those verdicts with A3-0033 | the gate run executes `proverif evaluation/models/e/access.pv` and `access_mutant.pv` with the host binary. It records the binary hash difference, and compares verdicts and counterexample shape against A3-0033 (G-2) |
| C7 | `evaluation/reports/RQ1-E.md` answers RQ1; no JANUS findings | none | the report | skeleton in S3-0003; final after the gate run |
| C8 | Source, input, output and tool hashes, commands and exit codes recorded; no input changed during the run | per-slice brackets (`source-bracket.json`, `real-e2.json`) | one bracket around the whole gate run | `e_gate.py` reuses `e2._sources()` (e2.py:24-30) before and after, plus `verify_plan` per row. Owner snapshots are checked by `e1._snapshot_stable` |
| C9 | Three ACKs on the same report and source manifest; gate E PASS before F | none | the solo ACK format (S3-0001 D-1) and the adjudication | gate.py adjudication (section 3.3). ACKs come from A1, S2 and S3, with the correlated-review disclosure |

## 2. How the integrated runs work today (agent-3 8e5a6dd)

**Entry point.**

```
.venv/bin/python -m evaluation.e2 --plan <integration-plan.json> --acks <ack-index.json> --output <new 0700 dir>
```

The exit code is 0 only for the four `*_SLICE_PASS` statuses (e2.py:221). Otherwise it is 2.

**Plan.** `integration-plan.json` is produced by `e2.create_plan(run_id, freeze_message, flags)`. `verify_plan` regenerates it on the running host and requires byte equality (e2.py:137-154). So **the plan is host-bound**: it records tool paths and hashes, the Python version and HOME. Keys:

- `schemaVersion`, `runId`, `freezeMessage`, `interfaceFreezeSha256`, `adapterMode: symbolic`, `profiles`, `logDetailMode: complete-details`;
- `ports {pbc: 18545, dbc: 28545}`, `chainIds`, `deployerSignerRole: relay`, `deploymentSpeed`;
- `owners` (commit plus a per-file sha256 inventory for ledger 933d2a7 and protocol 0716a8e);
- `agent3Sources` (hash of every evaluator input), `tools`, `pythonVersion`, `packagePins`, `serviceEnvironment`, `dependencyLockSha256`;
- `budgets {rpc 5, readiness 15, deploy 600, bootstrap 120, transport 10, stopGrace 2}`;
- `controls`, `limitations`, `matrix`, `caseIds`, the probe description and `startContractSha256`.

**FREEZE and ACK.**

- The FREEZE message names the plan path and its SHA-256.
- Each ACK carries the headers `Type: ACK`, `RQ: E`, `Interface-version: v1`, `Responds-to: <freeze ID>`, `Accepted-plan-sha256: <hash>`, and `To` including agent-3 or all.
- The ACK index is `{"agent-1": {commit, path, sha256}, "agent-2": {...}}`, for example `evaluation/evidence/e2/grouped-replay-live-20261009/acks.json`.
- `e1._acks` reads each ACK as a Git blob at that commit, checks the hash, checks ancestry against `origin/agent-N`, and parses the headers (e1.py:103-133). These checks are **incompatible with S2/S3 IDs** (S3-0001 D-1).

**Services per matrix row** (`e1._profile`, e1.py:175-295):

1. `_available(ports)`: a SO_REUSEADDR bind test. It refuses occupied ports and never kills anything.
2. Start Anvil twice: `anvil --host 127.0.0.1 --port P --chain-id C --hardfork cancun --silent`, as an owned `ServiceProcess` (`start_new_session=True`; stop = terminate, wait 2 s, kill; `evaluation/processes.py:278-388`). Readiness is `eth_chainId` within 15 s.
3. `anvil_setBalance` of 1000 ETH for the relay and the H1..H4 CA admins.
4. Materialize the pinned owner snapshots from Git blobs into `<out>/snapshots/{ledger,protocol}`.
5. Run `bash ledger/tools/deploy_local.sh <pbc> <dbc> <profile> complete-details <run-id>` (timeout 600 s, `LEDGER_DEPLOY_FAST=0`).
6. Check the ABI hashes and the runtime bytecode templates.
7. Run `bootstrap_fixture.sh` and `execute_bootstrap` (wrong-admin first).
8. Start the adapter as a `JsonLinesProcess`: `python -m hmbc_protocol.adapter --state-dir <0700> --deployment <file>`, or `-m testtools.faulty_adapter --crash-at P` for crash rows.
9. Read the worker log with `python -m hmbc_protocol.worker_log --state-dir`.
10. Run the Alice and Bob flows.
11. An `ExitStack` stops every owned process; PIDs go in the manifest; snapshot stability is required at the end.

**Timing.** Actual wall times: E1 356 s for 3 rows; duplicate 365 s for 3; grouped replay 375 s for 3; recovery+expiry 780 s for 6. That is about 120-130 s per row.

- Repaired-e request TTL is ≤30 s. Grant expiry is `min(decision.expiresAt, request.expiresAt)`.
- Paper grant expiry is the `policyEnf` block + 30 s.
- The repaired release margins were 3-4 s.
- `RpcClient.call` hashes the 77 MB cast binary twice per call (rpc.py:54, 62). The timing review estimated 7.7 s per replay probe.

**Evidence.**

- Raw output goes to a private external directory.
- Selected public/redacted JSON goes under `evaluation/evidence/e2/<slice>-live-<date>/`: `README.md`, `catalog-coverage.json`, `live-result-audit.json`, `real-e2.json`, `acks.json`, `source-bracket.json`, `selected-manifest.json` and `run/...`.

## 3. Proposed gate design

### 3.1 One command

```
.venv/bin/python -m evaluation.e_gate --plan evaluation/evidence/e3/gate-plan-<date>/integration-plan.json \
    --acks <ack-index.json> --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/gate-<date>/out
```

The command must not be run before the plan's FREEZE and both ACKs. Its stages, all from fresh state:

1. Run `verify-freeze` and record the toolchain versions.
2. Take the source bracket (pre).
3. Run all **56 catalog rows**: one fresh chain pair per row, with the controls first and the stress on fresh deployment D2 (S3-0001 section 3), and any clock move last.
4. Run the **mutant matrix**.
5. Measure the **revocation window**.
6. Run **ProVerif**, or record a hash-checked citation (G-2).
7. Take the source bracket (post).
8. Write `manifest.json` with:
   - `rq: E`, `executionMode: real-integrated`, `interfaceVersion: v1`;
   - `status: PASS|FAILED`, `sourceStable`;
   - `resultFiles {relpath: sha256}`, `adapterMode: symbolic`;
   - every failed or timed-out trial, kept.
9. Write `gate-evidence.json` `{criteria: {<C1..C9 names from gate.py E_CRITERIA>: {status, evidencePaths, note}}}`.

There must be no retry that hides a failure. A failed row is recorded as FAILED, and the gate does not pass until it is explained and re-run under a new FREEZE.

**Wall-time estimate (not measured):**

| Stage | Estimate |
|---|---|
| 56 rows × ~130 s | ~2 h |
| D2/D3 extra deployments | +20-30 min |
| 6 mutants | ~15 min |
| Window, 5 trials | ~10 min |
| **Total** | **~2.5-3 h** |

Run it in the background, with a guard.

### 3.2 Report and ACK flow

1. Run `e_gate`.
2. Finalize `evaluation/reports/RQ1-E.md`, citing the run's `manifest.json` SHA-256 and `catalog-coverage-56.json`.
3. Collect three report ACKs, each with the headers `Accepted-report-sha256:` and `Accepted-run-manifest-sha256:`:
   - A1-NNNN, ledger claims;
   - S2-NNNN, protocol and key assumptions;
   - S3-NNNN, evidence and model.
4. Agent 1 commits them.
5. Run `.venv/bin/python -m evaluation.gate --rq E --run <out> --report-acks <index>`.
6. Update GATES.md and BOARD. F0 opens only on PASS.

### 3.3 Required gate.py change (RED/GREEN first)

- Remove the unconditional BLOCK at gate.py:43.
- Add the report-ACK adjudication:
  - three distinct ACKs (agent 1, agent 2 (proxy), agent 3 (proxy));
  - the same report hash and run-manifest hash;
  - blobs read from agent 1's commits;
  - a solo-mode flag that **prints the correlated-review disclosure** in the gate output.
- Keep fail-closed on any missing or `!= VERIFIED` criterion.

Tests:

- a fabricated boolean or self-reported bundle must still BLOCK;
- a stub manifest without `real-integrated` must BLOCK;
- one wrong ACK hash must BLOCK.

## 4. Retargeting ports to 18545-18599

**Today:** `e1.create_plan` hard-codes `ports=dict(pbc=18545, dbc=28545)` and `chainIds 18545/28545` (e1.py:58). The deploy env sets `PBC_CHAIN_ID/DBC_CHAIN_ID` (e1.py:191). `deploy_local.sh` takes the RPC URLs and chain IDs separately. No other evaluator file hard-codes the ports. The tests only mutate them (test_e1_freeze.py:30, test_e2_freeze.py:35).

**Proposal (S3-0001 D-3a):** move the ports into explicit plan parameters, defaulting to PBC 18545 and DBC 18546. Keep chain IDs 18545/28545, so the EIP-712 domains and deployment manifests keep the chain IDs used in all earlier evidence. Readiness checks `eth_chainId` against `chainIds`, not ports, and `manifest['rpcUrl']` is compared with the actual URL, so ports and chain IDs can differ.

- One live run at a time. The 2-port pair leaves 18547-18599 free for a second pair only if a decision allows parallel runs. I do **not** propose parallel runs: they share CPU and worsen the repaired-e margins.
- The window stage needs `--block-time 1` (A1-0046 method). Add it as a per-stage Anvil argument, recorded in the plan.

## 5. Decisions needed (G-1..G-4) beyond S3-0001 D-1..D-6

- **G-1, scope of the "one command".** Choose one:
  - (a) a full fresh re-run of all 56 rows, mutants and the window in one command (recommended: matches PLAN E3 "from a fresh process/data state" and "one command");
  - (b) a gate that aggregates the per-slice runs.

  (b) is cheaper but weaker: the inputs did not stay fixed across slices.
- **G-2, ProVerif.** Late update: agent 1 has already built 2.05 from the recorded source, which makes (a) available. Choose one:
  - (a) re-run with the host binary and record the local-build hash difference (recommended);
  - (b) cite A3-0033 outputs with model and output hash checks, and state "not re-run on this host".

  (b) is honest but weaker than a re-run.
- **G-3, destination-binding mutant.** Report it as **not killable by the catalog recipe**. Choose one:
  - (a) add the non-catalog kssc-only rewrite as a labelled **extension** row (separates by code only); or
  - (b) rely on [U] forge tests plus the symbolic ProVerif mutant.

  Either way, C4 is met by the other 5 mutants. Do not claim an integrated destination kill.
- **G-4, paper crash rows.** Never report them as findings. There is a conflict to resolve: my default keeps the frozen BLOCKED/UNPROVED label, while S2-0002 recommends reclassifying the paper property as **SPEC_GAP** (outcome UNPROVED unchanged) through a DECISION record, on the ground that the mechanics did run, so "BLOCKED = never ran" no longer fits.
  - I can accept S2-0002's SPEC_GAP **only** if the report shows the pre-registered frozen label (BLOCKED) next to the decided label, with the decision ID. This is a relabel of an ambiguity class, not a change of outcome, and no frozen bytes change.
  - Either way C3 is satisfiable, because it asks for a classification, not a SUPPORTED result.
  - **Agent 1 decides.**

## 6. Risks

- **Repaired-e TTL margins** (S3-0001 D-5) can fail rows in SL2, SL6 and SL7 and in a long gate run under CPU load.
- **Host-bound plans:** any tool, Python or path change invalidates the plan and its ACKs.
- **Same-model review:** all three ACKs are correlated. This must be printed in the gate output, GATES.md and RQ1-E.md.
- **Raw evidence of earlier slices** is on agent 3's host only. The gate run supersedes it for C2, C3 and C5. The historical slices remain cited, not re-audited.
