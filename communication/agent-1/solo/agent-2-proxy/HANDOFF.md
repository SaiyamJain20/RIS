# agent-2 (proxy-2) handoff

## Current (2026-11-14): proxy-2 for absent agent 2 (A1-0130)

- **Pins:** HEAD 8efc291 on agent-1; `protocol/**` byte-identical to origin/agent-2 9d44754f7db364e4c39150c699b1e38bedded559 (merge 563fbc7). Ledger pins 91add8c, 85c59f5 in the object store.
- **Done:** T0 (this block). T1 S2-0024 NOTE written: `outbox/0024-note-signing-rule-reading-a3-0121.md` sha256 262eef21..c398. Result: agent 3's reading of the store confirmed point by point; correction: ALLOW-then-DENY after a grant is NOT reachable through an honest witness (§2 step 1 + §3 row (b), code REPLAY `witness_service.py:146-147` before `store.sign`; the service passes only `overtaken-decision-sequence`, :316-318). Targeted tests 6 passed (exit 0).
- **T2 (S2-0025) in progress. Working-tree changes (uncommitted, 4 files, all under protocol/):**
  - `hmbc_protocol/witness_state.py` (sha256 1a878799..; was c6184a61.. at 9d44754): two inert hook calls in `_sign_in_txn`: `self._hook("after_pin")` after the conflict INSERT block (before `signer(digest)`), `self._hook("after_digest")` after the digests INSERT (before the observed INSERT). `self._hook` is a no-op unless `crash_hook` is passed; faulty_witness's hook fires only on its own point names (`testtools/faulty_witness.py:36-39`), so the F alternate entry is unaffected. Mutation anchors S1 (`run_state_mutants.py:20`) and M1 (`testtools/mutant_tree.py:50`) still match once (checked by reading; runners not yet rerun).
  - `tests/state_kill_child.py` (ad59580f..): new mode `sign-pause` (hook prints STAGE lines and BLOCKS at the nth occurrence of a named point, optionally only inside a superseding transaction; prints `PAUSED <stage> <nth> <sup_in_txn> <sup_before>`; END after 60 requests).
  - `tests/test_witness_state_kill.py` (16888a37..): new `test_kill_between_the_signing_statements_leaves_a_whole_record` (3 kills: after_pin #1, after_digest #1, after_pin inside a supersede; asserts stored digests == replies, superseded count unchanged, supersede non-vacuous, full `violations()` I1-I4 empty). Existing tests unchanged.
  - `tools/run_state_kill_mutants.py` (90b9f072..): docstring of K1 only (anchors unchanged).
- **T2 evidence so far** (scratch `/home/saiyamjain/.claude/jobs/aed51961/tmp/p2/t2/out/`; driver `t2/bin/k1_trials.py` runs one node id N times in a runner-style minimal copy with the runner's own K1 edits):
  - RED 1 (existing stage test, base 9d44754, K1 applied): **K1 detected 1 of 40** on this host (agent 3: 29/40); control 40/40 pass. `red-k1-existing-test-40.json`, `red-control-existing-test-40.json`.
  - RED 2 (new test before the hook): exit 1, "the child never reached store point 'after_pin'" (`red-new-test-before-hook.txt`).
  - Failed trials of my own test (kept): run 1 `I3 a stored digest was never requested` (my request count deduped repeats; fixed to count REPLY/REFUSED lines), run 2 a mis-written assertion `AssertionError: True` (removed). Run 3 passed (`green-new-test-third.txt`).
  - GREEN job (background, `t2/bin/green.sh`, snapshot `t2/green/protocol`, hashes in `t2/out/green-snapshot-hashes.txt`, equal to the working tree): **new test with K1: detected 40 of 40** (every run fails at case `after_pin-1` with "I3 a pin without a live digest"; mutated witness_state sha256 093acb7c..); **control 40 of 40 pass** (`green-k1-new-test-40.json`, `green-control-new-test-40.json`). Then `run_state_kill_mutants.py` ×5 on the snapshot (`-B -I`, HMBC_KILL_TRIALS default 40 in the runner): **5 of 5 runs exit 0: control passes, K1 DETECTED, K2 DETECTED, E1 survives (equivalent)**, 132-136 s each (`t2/out/run_state_kill_mutants-run{1..5}.txt`). Job finished (`green.done`); no processes left (checked `ps`).
  - **Open claim to verify:** the new test's docstring says K1 makes EVERY case fail; the 40 runs only show case 1 (the test stops at the first failure). `t2/bin/percase.sh` (written, NOT yet run) runs each case alone, K1 ×5 and control ×5, in scratch copies → `t2/out/probe-case{0,1,2}-{k1,control}-5.json`. If a case does not detect K1 alone, correct the docstring (do not weaken the test).
  - **Per-case probe DONE (proxy-2 #2):** `percase.sh` exit 0; each case ALONE detects K1 5 of 5 (case0 after_pin "I3 a pin without a live digest"; case1 after_digest "left 1 record(s)"; case2 supersede "a supersede of the killed request survived it (0 -> 1)"); control 5 of 5 pass per case. Docstring claim confirmed, no change. `t2/out/probe-case{0,1,2}-{k1,control}-5.json`.
  - **Other runners' anchors (proxy-2 #2):** `t2/bin/anchors.py` exit 0: all 10 witness_state.py anchors of `run_witness_hooks_mutants.py` (W1-W6, live-only) and `testtools/mutant_tree.py` (M1, M2 x2, M3) match exactly once in the final bytes.
  - **Evidence dir CREATED (partial):** `protocol/evidence/af2-kill-k1-deterministic/outputs/` (23 files copied from `t2/out/`: RED-1/RED-2, failed trials 1-2, GREEN 40/40 + control, 5 runner runs, 6 PROBE json, E-listed/F0/export checks, anchors) and `drivers/` (5 scratch scripts as .txt). README NOT yet written; neutral outputs not yet copied.
  - **Behaviour-neutral proof DONE (proxy-2 #2, `t2/bin/neutral.sh`, working tree, hashes equal start/end):** state tests 81 passed 0 skipped exit 0; witness/pool/mutant-tree/process tests (14 files) 459 passed 0 skipped exit 0; run_state_mutants 42/42 exit 0; run_state_kill_mutants control pass, K1 DETECTED (2 failed tests), K2 DETECTED, E1 survives, exit 0; run_mutant_tree_mutants 7/7 exit 0. No orphans. Copied to evidence `outputs/NEUTRAL-*` (30 files in outputs/ now; driver `drivers/fullsuite.sh.txt` added).
  - **Full suite DONE:** exit 0, **3226 passed, 201 skipped** (200 ScenarioResult + 1 FileHash), 1571 s; hashes equal start/end; Python 3.13.5, forge/anvil 1.8.5; ephemeral range 32768-60999 disclosed. No orphans.
- **T2 DONE (written, uncommitted):** S2-0025 READY `outbox/0025-ready-delta-k1-deterministic.md` (sha256 7693da92..); evidence `protocol/evidence/af2-kill-k1-deterministic/` (40 files + `SHA256SUMS` f0be4141.., `sha256sum -c` 40 OK).
- **T3 DONE (written, uncommitted):** S2-0026 (sha256 809f8f0f..).
- **Running:** nothing. Tree consistent. origin/agent-2 still 9d44754, origin/agent-3 still ae7635e at finish.
- **Exact next step:** none for proxy-2; agent 1 reviews and commits exact paths (4 protocol files, the evidence dir, outbox 0025 and 0026, STATUS, HANDOFF).
- **T3 S2-0026 WRITTEN (proxy-2 #2, while neutral.sh ran):** `outbox/0026-review-f-execution-plan-draft-protocol-scope.md` (§1 pin + preflight provenance conflict, §2 entries, §3 schema flags incl. `--schema-revision v2|v2.1`, §4 layout, §5 ports/chain ids, §6 hook table, §7 lock rule, §8 `--evidence` export as observation source, §9 stage 3 + ACK checks). Its §9 says "the S2-0025 READY gives this host's count": fill that in S2-0025, no edit to S2-0026 needed.
- **T3 notes gathered (proxy-2 #2):** plan-draft sha256 7a212c55..; its `protocolSourceCandidate` is origin/agent-2 55f180e (protocol/** identical to 9d44754: `git diff --stat 55f180e 9d44754 -- protocol/` empty). `evaluation/f_preflight.py` (origin/agent-3 ae7635e) checks the protocol candidate is an ancestor of `origin/agent-2` (:287, :328-330): a proxy commit on agent-1 would FAIL that check -> raise in S2-0026. Plan does not name: adapter entry, alternate entry, supervisor layout (A2-0074 §2 O1-O6, pid `<state>/witness-<i>.pid`, stderr `<state>/witness-<i>.stderr`, store `<state>/witness-<i>/`), ports, protocol stage-3 expected counts (201 skips), snapshot-lock rule (A3-0105 §2, §4). Chain ids: deployment json chainId checked against node by `chain.py:106-111`. Copy durable outputs from `t2/out/` into `protocol/evidence/af2-kill-k1-deterministic/outputs/` (they are in scratch only now), with `t2/bin/k1_trials.py` and `percase.sh` as `.txt`.
- **Next steps for T2:** (1) read GREEN results; (2) behaviour-neutral proof on the final bytes: state suite (`tests/test_witness_state*.py`), `run_state_mutants.py` (42/42), `run_state_kill_mutants.py`, the witness/pool tests touching the store (`test_witness_service*.py`, `test_faulty_witness.py`, `test_witness_main*.py`, `test_mutant_tree*.py`), `run_mutant_tree_mutants.py`; (3) DONE on the delta tree 2026-11-14: E-listed `sha256sum -c protocol/evidence/source-manifest.sha256` (repo root) 139 OK + exactly 3 FAILED (worker_log.py, worker.py, deviating_witness.py; witness_state.py is not listed), exit 1 as expected (`t2/out/e-listed-check.txt`); `sha256sum -c protocol/f0/MANIFEST.sha256` 52 OK exit 0 (`f0-manifest-check.txt`); `PYTHONPATH=protocol .venv/bin/python -B -m hmbc_protocol.export --check` exit 0 "exports match 9 files" (`export-check.txt`); (4) full suite once in the background (expect 201 skips only: 200 ScenarioResult + 1 FileHash); (5) evidence dir `protocol/evidence/af2-kill-k1-deterministic/` (README + outputs + driver as .py.txt); (6) S2-0025 READY (delta vs 9d44754, exact paths + sha256, commands + exits, failed trials).
- **Port trap for the full suite (found 2026-11-14, not yet resolved):** set `PATH="$HOME/.foundry/bin:$PATH" HMBC_FOUNDRY_DIR="$HOME/.foundry/bin" HMBC_TEST_PORT_RANGE=19545-19599 PYTHONDONTWRITEBYTECODE=1`. Only `tests/conftest.py` honours `HMBC_TEST_PORT_RANGE`. Seven test sites bind port 0 only to get an UNREACHABLE URL (no listener: `test_adapter_v2_main.py:113,165`, `test_divergent_witness.py:171`, `test_delayed_witness.py:71`, `test_faulty_adapter_v2.py:359`, `test_faulty_witness.py:99`, `test_witness_main.py:94`), which is harmless. But `tests/test_rpc_binding_view_live.py:55` has its own `_free_port()` (:53-56) and starts Anvil on that OS-chosen port (:70 onward; confirmed by reading), outside 19545-19599. Options: run the full suite with `--ignore tests/test_rpc_binding_view_live.py` and disclose it, or ask agent 1 first. Do not edit that test inside the K1 delta.
- **Then T3:** S2-0026 protocol-scope review of A3-0127 (`git show origin/agent-3:evaluation/evidence/f/execution-plan-draft-20261114/{README.md,plan-draft.json}`), mirroring A1-0129.
- **Rules:** write only `protocol/**` and this mailbox; no Git writes; ports 19545-19599; scratch `/home/saiyamjain/.claude/jobs/aed51961/tmp/p2/`; Anvil dev key only via env; check origin/agent-2 before each task and before the first write in each task.

## History (solo Phase E, 2026-10-12 and earlier)

## agent-2 (proxy-2) handoff (2026-10-12, P4-3 ACK done, after S2-0023)

Paper-derived HMBC2020 reconstruction, solo phase, synthetic fixtures only. Correlated self-review (A1-0059).

## Current pins
- **E2 FREEZE pin, used by every integrated run:** protocol 0716a8e / d16ddad8.. (108 entries). faulty_adapter f0ab2400.., deviating_witness 0511ba57...
- **Working protocol tree:** `protocol/evidence/source-manifest.sha256` sha256 551e9f774b91f8a0d55c60b85088de0e29b2c597682145f6d755a02c93649ae3 (127 entries; T1-T3 tests added in S2-0006). `sha256sum -c` exit 0 on 2026-10-12.
- `hmbc_protocol/**`, `testtools/**`, `exports/**`, `abi/**`: byte-identical to the pin at HEAD ec426c6 and again at 5c4c487 (S2-0021 review). The A1-0046 window adapter (8b7caf5) has byte-identical `hmbc_protocol/**` and `abi/**` too.

## Where things stand
- **Catalog 56/56 actual.** SL1-SL7 each have my protocol-scope ACK and REVIEW (S2-0004..S2-0020), no discrepancy. Review scripts and outputs: `protocol/evidence/reviews/s2-00{05,10,12,14,16,18,20}-*/`, each `problems: []`.
- **P3 closed** (A1-0081): ProVerif re-published byte-identical; live mutant matrix and integrated window **NOT RUN** by human decision after safety-classifier stops (A1-0080, A1-0081). Never resume them.
- **P4 in progress** (A1-0082). My part:
  1. `rq1-protocol-sections.md`: **refreshed 2026-10-12** (this handoff). It adds P14-P16 (prepare_request purity and verbatim authEpoch; lazy worker and D49; one adapter per deployment with shared label keys), per-slice adapter operations and A31 counts, D49 probe counts and never-publish scans, witness timing rules with measured margins, protocol text for every E01/E02 row, SL3/SL4 [I] text for §7.3, criterion-4 and window wording in protocol scope (A1-0080/A1-0081), process errors, "what the evidence does not show", and a 15-item must-not-claim list. The §7.2 figure placeholder is replaced by the A1-0064 citation.
  2. **S2-0021 sent** (`outbox/0021-ack-e-gate-run-freeze.md`): ACK of plan c0086019.., no blocker. Self-check OK (S2-0021; a wrong hash is refused). Review: `protocol/evidence/reviews/s2-0021-gate-freeze/` (`review_gate_freeze.py.txt`, exit 0, `problems: []`; `faulty-adapter-tests.txt`, 15 passed on this host). It establishes:
     - the pin;
     - the embedded plans equal the historical ones except runId/freezeMessage/agent3Sources, plus the SL0 host fields for the pre-solo slices;
     - the pinned production code has no port, env or HOME dependency;
     - the pre-solo adapter call sequence is unchanged; only the evaluator files access_execution/chain/e1/e2/rpc changed, by branch-isolated additions and the Cast checkpoint.
     It also has the margin table: agent 3's host repaired recovery retry 2.1-5.4 s, grouped replay 3.44 s, first replay −0.05 s; this host's repaired control release 25.0-26.4 s before expiry.
  3. **Done: S2-0022 sent** (`outbox/0022-review-e-gate-run-result.md`, committed in 35ae6c3). It is the post-run REVIEW of S3-0022 on the published copy `evaluation/evidence/e3/gate-run-20261012/` (manifest 908fd615.., gate-evidence 47e38dd3..; RQ1-E.md 0ec51e8e..).
     - **Result:** no discrepancy in 56/56 rows. No gate row failed.
     - **Review:** `protocol/evidence/reviews/s2-0022-gate-run/` (script bf3e5e8d.., output 58101735.., commands 5d403fb4..), exit 0, `problems: []`.
       - Part A re-runs my seven slice scripts unchanged on byte-identical copies in job tmp `tmp/p2/s2-0022/run-*`.
       - Part B covers all rows: adapters and deployment join, A31, D49, crash hook, SL4 deviation and refusal record, witness timing for all 66 decisions, release margins, and all 152 `prepare_request` calls against the mined calldata.
       - Part C is the never-publish scan (19 label keys, token preimages, paths).
       - Part D compares RQ1-E.md with my sections.
     - **RQ1-E.md:** P1-P16 identical. Only the SL7 timing row is reworded ("at least 1 s"), and it is accurate. Optional notes for agent 3 (proxy): the §6.1 "will re-check" sentence; §3.4 "which term binds" can now say all 66 decisions.
     - **Not verified:** raw-token substring absence (I did not read the private DBs; digest preimages only); on-disk worker absence; the witness's exact clock; byte identity of the adapter's loaded deployment file (joined by run id and sha256 records).
  4. **Done: S2-0023 sent** (`outbox/0023-ack-gate-result-e.md`, sha256 9b5869f8.., uncommitted). It is the P4-3 same-source ACK of the gate RESULT S3-0023 (1906a3c0..) for the protocol and key claims. **No blocker.**
     - It names exactly: manifest 908fd6156ac5c6c4f640686fbddade3f9720cf29fb1e579f7c3d01f0909205a2, gate-evidence 47e38dd369ce686d5298f909c43c79cdf4b7eff4d20d41988a57f80974538500, RQ1-E.md 69dabfbab9d9deeb0d94b448da6bf9b9674ce25c7c94e1b101f67c4804c89b8f, and HEAD of record 871e21812877ff1f9a00b8877236f9970714bf57. It also cites plan c0086019.., run HEAD 21b37fb and evidence commit c2c81d5.
     - The hashes were verified with `git show 871e218:<path> | sha256sum`. HEAD 9d3e904 adds only A1-0085.
     - No evidence file changed after c2c81d5. The RQ1-E.md diff 0ec51e8e..→69dabfba.. adds review-record text only.
     - I ran Part D inline, read-only, on the final bytes. The script is in the ACK's appendix. It matched S2-0022, and no new risk-word line appeared.
     - Parts A-C were not re-run, because the evidence bytes are unchanged.
     - The "not verified" list and the correlated-review disclosure are carried in the ACK.

## What I checked for S2-0021 (from A1-0082 P4-1; done)
- `owners.protocol` = 0716a8e / d16ddad8.. (108), materialized from git blobs.
- Aggregation only: the gate calls the same slice runners and oracles (`e2.create_plan` slice flags), no new oracle logic; slice directory layouts unchanged.
- Every stress deployment gets its own production adapter, 0700 state and pinned deployment (D2; A and B for wrong destination); D49 probes as in the slices; A31 counts still oracle-enforced in SL6/SL7.
- Mutant and window stages dropped; ProVerif re-run compared with A3-0033 and p3-proverif-20261012.
- Failed or timed-out rows kept, never silently retried; nothing writes in the repo during the run.
- Thin margins: SL7 expiry boundary ~1-2 s request-binding margin; SL6 expired-duty consume ~7 s. Overruns must fail visibly.
- Never-publish: no key, no raw token (`tokenSha256` only), deviating-witness raw logs private.
- Self-check the ACK with `e1._verify_solo_ack_message(raw, agent='agent-2', plan=..., plan_sha256=...)`.

## Reproduce (repo root)
```
export PATH="$HOME/.foundry/bin:$PATH" HMBC_FOUNDRY_DIR="$HOME/.foundry/bin" HMBC_TEST_PORT_RANGE=19545-19599 PYTHONDONTWRITEBYTECODE=1
# protocol owner suite (S2-0006): exit 0, 1375 passed, 201 skipped (~6 min)
.venv/bin/python -m pytest -q -rs -p no:cacheprovider -c protocol/pytest.ini --rootdir protocol --basetemp=<scratch> protocol/tests
# one slice review (example SL7): exit 0, problems []
.venv/bin/python -I protocol/evidence/reviews/s2-0020-sl7/review_sl7.py.txt evaluation/evidence/e2/sl7-destination-live-20261011 <repo>/protocol
# manifest
sha256sum -c --quiet protocol/evidence/source-manifest.sha256
```
Host memory is low: do not run a full suite unless asked.

## Limits
- Correlated self-review throughout; the original agent 2 has reviewed none of SL1-SL7.
- Symbolic adapter crypto; no ABE or real encryption; TEST-ONLY keys derivable from labels; one trusted witness; trusted worker; no consensus; not the authors' implementation.
- Logical crash points only; delivery unknown; key-substring scans only for SL4-SL7.
- Witness clock readings are bounded, not observed.

## Next action
- Agent 1 commits `communication/agent-1/solo/agent-2-proxy/{outbox/0023-ack-gate-result-e.md,STATUS.md,HANDOFF.md}`. S2-0022 and its review directory are already committed (35ae6c3).
- **Proxy-2: nothing further** until the original agent 2 returns or F planning starts. F stays locked until GATES.md records gate E (after S3-0024; A1-0082 P4-4). If a GATES.md draft cites S2-0023, check that it names the same four items.
- Gate review reproduce (repo root): `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -I protocol/evidence/reviews/s2-0022-gate-run/review_gate_run.py.txt evaluation/evidence/e3/gate-run-20261012 $PWD <job-tmp scratch>`. It gives exit 0 and `problems []`.
