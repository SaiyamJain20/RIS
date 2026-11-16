# Cross-run 2: agent 3's checkers on REAL decision, receipt and governance evidence (agent 2, Fork J, 2026-11-08)

PAPER-DERIVED RECONSTRUCTION; symbolic mode; synthetic TEST-ONLY keys; one host (Linux x86_64); local automine Anvil; one trial per scenario; same-model review (a forked sub-agent wrote and ran this; the parent re-runs it before citing anything).
Purpose: find interface mismatches between my real processes and agent 3's published checkers BEFORE the execution FREEZE, for the record types the first cross-run (`../af2-a3-crossrun/`) did not produce: AccessDecision, GrantReceipt, GovernanceAction, a numeric death with a real `eth_call` death getter. It does not prove agent 3's modules correct. **Nothing of agent 3's was edited or run as its own test suite; no repository file except this directory was written; no git write was made in the repository** (the record run used a throw-away local clone in the scratch directory, see Provenance).

## Findings, most severe first
All verdicts below are from the record run (`results.json`, run 5) and reproduced by run 4 (same driver, live working tree): every verification verdict is identical, only pids, hashes, timestamps and the index of the `silent` witness differ.

### F1. `checkpoint_rpc_v2.collect` REFUSES real checkpoints whenever the caller's `pbcHead` is later than a change of `authEpoch`; the evidence does not say which head is right. Side: AGENT 3 (collector contract and documentation), not a defect of the verifier. REAL, 4 of 4 witnesses, reproduced in runs 3, 4 and 5.
- Setup (record run S9): after two checkpoints (sequences 1 and 2) the real `Governance.execute` of an ADD changed the PBC `authEpoch` (S6). `checkpoint_rpc_v2.collect` with `selections[].pbcHead` = the PBC latest block at selection time (mode A) gives `ValueError: Invalid checkpoint state: semantic freshness authEpoch` for **all four** witnesses (2 digests each). The refusal is correct for that head: `checkpoint_state_v2.py` line 100-101 requires `message[field] == latest` read at `pbc_head`.
- With `pbcHead` = each checkpoint's own source block (mode B; the real service derives a checkpoint from the PBC latest block and writes it into `effect.sourceBlockNumber/Hash`) the same call is **ACCEPTED 8 of 8** (4 witnesses, both digests each).
- Why it matters: the witness store records only the DBC observation for a checkpoint (TARGET table), so the caller has nothing in the evidence to choose the PBC head from, and an F scenario that changes authority, policy or witness-set state after a checkpoint turns the naive choice into a refusal. A runner must pick each checkpoint's own source block (or agent 3 documents another rule). Not an agent 2 defect: recording a PBC head per checkpoint would change the export layout (interface) and I did not propose it.

### F2. (measured scenario fact for the F cases) a governance ADD changes the PBC `authEpoch` and thereby makes every earlier request stale. Side: NEITHER (intended ledger behaviour), but F-case design must order for it. REAL, run 2 (superseded) and by construction in run 3-5.
- In run 2 (governance executed BEFORE the second decision request) the adapter answered the second `collect_decision` with `STALE_STATE: request authEpoch/policyVersion differ from the DBC checkpoint`; no decision death could be produced until governance was moved after the re-request (runs 3-5). Kept in `superseded/run2/`.

### F3. Which death kinds REAL evidence can contain: only `expiry` (cross-run 1) and `overtaken-decision-sequence` (this run). The others cannot be produced through the real service. Side: agent 2 service design (documented), consequence for agent 3's native checks. REAL, attempted.
| Kind | Attempt through the real service | Result |
|---|---|---|
| `overtaken-decision-sequence` | request D2 decided at checkpoint sequence 1 (not consumed), checkpoint sequence 2 accepted, D2 requested again | **PRODUCED**: the second decision carries `stateSequence` 2; every store holds a `superseded` AccessDecision row with that death; `history_rpc_v2.collect` ACCEPTED it with **1 native `eth_call` death getter checked per witness** (`nativeCallsChecked` 1, `nativeDeathsChecked` 1) |
| `overtaken-checkpoint` | S13, real `witness_main` processes: after the ledger accepted sequence 3, (a) a proposal for sequence 3 with a different source block, (b) the exact accepted proposal again | NOT PRODUCED: both refused at the service as `STALE_STATE` / `PROPOSAL_MISMATCH` before the store is reached |
| `overtaken-governance` | S6: the consumed nonce again, (a) a different root, (b) the same action, after the real contract executed it | NOT PRODUCED: all four witnesses refuse both as `STALE_STATE` (the pool reports `QUORUM_UNAVAILABLE`) |
| `executed-receipt` | S4: the same receipt requested again after the real PSC recorded the outcome | NOT PRODUCED: refused `WRONG_SUBJECT` ("the PBC record does not match the DBC grant"); `witness_service.py` line 13 says the store's `executed-receipt` evidence is not used by the service |
| `overtaken-decision-grant` | no attempt | NOT PRODUCED: `witness_service.py` never supplies this kind (grep: only `overtaken-decision-sequence`, `overtaken-governance`, `overtaken-checkpoint` are passed) |
So agent 3's native-death branches for `overtaken-checkpoint`, `overtaken-governance`, `overtaken-decision-grant` and `executed-receipt` (`witness_native_v2.py`) can only be exercised by synthetic evidence in an F run, never by real witness output. A refused retry after execution is also `STALE_STATE`, not the recorded value (F-13's "recorded value on restart" holds only until the ledger has moved on).

### F4. No receipt RPC collector and no decision state checker exist on agent 3's side at 6358f7c. Side: agent 3 (scope), informational.
- `receipt_history_v2.verify_receipt_history` takes closed captures `{digest, dbcObservation, blocks, calls, logs}`; there is no `receipt_rpc_v2`. AccessDecision has no `*_state_v2` module: decisions are covered only by `verify_export_snapshot` / `witness_history_v2` (signature and context binding) and `history_rpc_v2` (death getters).
- My captures (built by THE DRIVER from raw RPC, `build_receipt_captures` in the driver; NOT agent 3 code) are **ACCEPTED 4 of 4** (1 receipt signature checked per witness). So the real receipt evidence satisfies every join `receipt_state_v2` makes: PBC observation chain of the stored record, pending request at that observation, allowed grant, `GrantIssued` log (one, with block reference), issuance timestamp, expiry bound. Limit: the store records no DBC observation for a receipt, so `dbcObservation` is a caller choice (here the DBC latest block at selection time); my builder is not a test of agent 3's future collector.

### F5. (informational, not a mismatch) every witness holds every record, whichever one was `silent`.
- In each successful pool call one witness was reported `silent` (index 3, 2, 0, 2, 1 in the five pool calls whose outcomes the record run keeps (S2, S3 decision, S3 receipt, S5, S6); it varies); after a 1.5 s pause all four stores hold the same 7 records (6 live + 1 superseded). `silent` still means only "not heard before quorum" (A2-0075).

### Driver mistakes of this stretch (kept in `superseded/`)
- Run 1: requests with TTL 420 were refused by the real PSC as MALFORMED (`maxRequestTtl` is 30); fixed to 25 (S2 prints it). Run 2: the governance-before-D2 ordering of F2. Run 3: S9 used only the "latest now" head (F1's mode A) and was refused; S9 now runs both modes. Runs 1-3 stages that depended on the failed flow are therefore not the record.

## Per-stage verdicts of the record run (run 5)
| Stage | What | Result |
|---|---|---|
| S0 | real F ledger (agent 1, 85c59f5) on two real Anvil nodes | deployed |
| S1 | fixtures + the REAL adapter (`adapter_v2_main`), four supervised `witness_main` children, `--allow-governance FILE` | ready |
| S2 | two real user requests forwarded by the real relay; pool checkpoint sequence 1 accepted by the real KSSC | 3 signed + 1 silent; accepted |
| S3 | decision D1 consumed by the real ACSC; receipt reported to the real PSC (status 2) | accepted by the real contracts |
| S4 | decision D2 at sequence 1 (not consumed); receipt requested again after execution | D2 signed; receipt again REFUSED `WRONG_SUBJECT` |
| S5 | checkpoint sequence 2 accepted; D2 requested again | signed, `stateSequence` 2 (the numeric death) |
| S6 | governance ADD (allow-listed) executed by the real Governance; stale nonce twice | executed; both stale attempts `STALE_STATE` x4 |
| S7 | real exporters under agent 3's `locked_store`; `verify_export_snapshot(WitnessEvidence)` | exit 0, stderr 0 bytes, **4/4 ACCEPTED**, 7 records / 7 signatures each, 1 superseded row (`overtaken-decision-sequence`) |
| S8 | `history_rpc_v2.collect` | **4/4 ACCEPTED**, 9 blocks, **1 native `eth_call` death getter checked** |
| S9 | `checkpoint_rpc_v2.collect`, two head selections | A (latest now) **4/4 REFUSED** (F1); B (own source block) **4/4 ACCEPTED** |
| S10 | `governance_rpc_v2.collect` (caller TEST-ONLY approval = the `--allow-governance` tuple) | **4/4 ACCEPTED**, 1 governance state signature checked |
| S11 | `receipt_history_v2.verify_receipt_history` with driver-built captures | **4/4 ACCEPTED** (F4) |
| S12 | stop the adapter | exit 0, stderr empty, no witness process left |
| S13 | overtaken-checkpoint attempt on real `witness_main` processes | refused `STALE_STATE`/`PROPOSAL_MISMATCH` twice (F3) |
| S14 | stop the Anvil nodes | closed |
Every adapter reply was also validated by the test fixture against the PUBLISHED schema (`agent3-v2.1-hmbc.schema.json`) inside `Adapter.ask`; none failed. `DONE 15 passed, 0 failed` means the measurement ran; the verdicts above are the data.

## NOT PRODUCED / NOT EXERCISED, plainly
- The four death kinds of F3 marked NOT PRODUCED; only one native death getter per witness ran (the `overtaken-decision-sequence` one, kind `KSSC.currentCheckpoint`).
- Anvil ACCEPTS `{blockHash, requireCanonical}`; with no reorg this does not show it ENFORCES canonicality.
- No governance or receipt row with a death, no fault/clear evidence with these record types, no BindingExport and no worker store (known F1/F2 of the first cross-run), no real reorg, no heartbeat case.
- Agent 3's receipt collector does not exist, so the receipt path tests my capture builder against agent 3's verifier, not an agent 3 acquisition path.
- I did not run agent 3's test suite, any mutation runner, or the full protocol suite.

## Limits
One host, one trial per scenario, automine Anvil (no consensus), symbolic mode (no ABE, no confidentiality or performance claim), TEST-ONLY keys derivable from public labels, no power-loss or OS-kill durability, same model family for author and reviewer. A re-run of this driver shows reproducibility of the driver, not correctness of either side.

## Commands, provenance, versions
- Record run: `HOME=$SCR/home HMBC_FOUNDRY_DIR=$SCR/foundry-1.8.5 flock -x $SCR/live.lock $SCR/venv/bin/python -I crossrun2.py SCR REPO OUTDIR` where `crossrun2.py` is `scripts/crossrun2.py.txt` (sha256 `51df68f567ced906cc5f1f84ee346e1025bd3bc8f62feed97d878af2ae8a1b91`), `SCR` holds `a3tree/` (below), the venv and `foundry-1.8.5/`, `REPO` is a git repository containing the pinned ledger commit 85c59f5 (the shared live fixture runs `git archive` on it). **Exit 0, `DONE 15 passed, 0 failed`, 2026-11-08T07:30:05Z** (`run5-output.txt`); `results.json` sha256 `8b029e752155e5f754f8dab02ed373f68e1261fbe01349028abcd95daad79582`. Whole run 80.6 s of stage time, 34 s of it the ledger deployment. Raw exporter stdout, deployment manifest, receipt captures and collector transcripts: `outputs/`.
- **Agent 2 code under test:** a throw-away local clone of this repository made in the scratch directory (`git clone --local --no-checkout` then a checkout of **fec8ea0** inside that clone; the repository itself was not touched). The protocol source of fec8ea0 equals d375dda (`git diff d375dda fec8ea0 -- protocol ':!protocol/evidence'` is empty). Run 4 (`superseded/run4-live-working-tree/`, results sha256 `497aef4d29bef29812d1c739342cc197a8ec1f9367905415618eacc36d4a3c73`) used the live working tree while the parent was committing `ca7766a` (a change to `witness_state.py`); its verification verdicts are identical to run 5, but run 5 is the record because its source is exactly pinned.
- **Agent 3 code:** an extracted COPY of `origin/agent-3` 6358f7c8c4f9 (`evaluation/`, `interfaces/`, `communication/`); 400 of 400 files hash-equal to `git show origin/agent-3:<path>` (re-checked by this fork). sha256 prefixes: checkpoint_rpc_v2 832195f0, checkpoint_state_v2 3014c120, export_snapshot_v2 cf18e895, governance_history_v2 7cb48e38, governance_rpc_v2 1295b059, governance_state_v2 db7333f1, history_rpc_v2 8a5e108b, public_observations_v2 c14cf3b0, receipt_history_v2 1176ce0a, receipt_state_v2 6663e2c9, store_snapshot_v2 1859c8a3, witness_history_v2 1a2b9921, witness_native_v2 b5296ed4.
- Tools: CPython 3.13.12 from the frozen root `uv.lock`, pytest 9.0.2, jsonschema 4.26.0, eth-account 0.14.0, SQLite 3.50.4, Foundry 1.8.5 (cast sha256 `1eb1eecf..` = the pin), profile `repaired-f`, `compiled_max_admins` 8, `maxRequestTtl` 30, `maxGovernanceTtl` 120.
- Superseded runs 1-3 (driver, output and `results.json` each) and the live-tree run 4 are kept under `superseded/`.

## Independent re-run by agent 2 (the same session, 2026-11-08)
A forked sub-agent wrote this driver and ran it five times. **I did not adopt its verdicts.** I re-ran the unmodified driver (`scripts/crossrun2.py.txt`, sha256 51df68f5.., the same bytes) on my own fresh chains, ports and a clean clone of origin/agent-2 `be472bf` (the protocol source differs from the fork's pinned `fec8ea0` only by the store-recovery fix of `ca7766a` in `witness_state._classify`, which does not touch these flows), under `flock`, with agent 3's tree hash-verified against `origin/agent-3` 6358f7c (400 of 400 files): **exit 0, `DONE 15 passed, 0 failed`** (`rerun-by-agent-2/run.txt`, `results.json` sha256 f8faf08e..; the fork's record is 8b029e75..).
Compared stage by stage with the fork's `results.json`, modulo block hashes, ports, pids and clock timestamps: **all 15 stages give the same verdicts**, including the finding of F1 (S9: the caller head "PBC latest now" refused after the governance ADD, each checkpoint's own source block accepted), the decision death verified through a real `eth_call` death getter (S8), the refused stale checkpoint (S13) and all four collectors' ACCEPTED verdicts. The only differences are process ids (S1) and WHICH witness is `silent` in a successful pool reply (S3, S5, S6: three signed, one not heard before quorum, a different index each run, as already documented in A2-0075 item 1).
Same limits as above: one host, one trial per scenario, automine Anvil, same model family for author and reviewer; a re-run shows the driver is reproducible, not that either side is right.
