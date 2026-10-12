# agent 3 (proxy): handoff

Paper-derived HMBC2020 reconstruction. Synthetic only.

Phase: E / RQ1 done, solo mode (A1-0059, `../PLAN.md`, `../PROTOCOL.md`, rulings A1-0061). **Gate E PASS (solo
phase)**, recorded in `communication/GATES.md` on 2026-10-12 after the three same-source ACKs A1-0085, S2-0023 and
S3-0024. Board at **F0**. **F is not started**: it needs its own plan and the human's go-ahead. G locked. All proxy
reviews and ACKs are correlated self-review (same model as agent 1); S3-0024 is a self-sign-off.

## Current state (2026-10-12 IST)

| Step | Result | Message / evidence |
|---|---|---|
| SL0 portability | done | S3-0004; `evaluation/evidence/e2/sl0-portability-20261009/` |
| SL1 subject substitution ×3 | **actual PASS 3/3** | FREEZE S3-0005, plan 6fd5809b..; result S3-0006; `evaluation/evidence/e2/sl1-subject-live-20261010/` |
| SL2 relay stress ×7, first run | **FAILED** (runner defect: worker DB never created, D49) | S3-0007 plan d67f1786..; S3-0008; `evaluation/evidence/e2/sl2-relay-failed-20261010/` |
| SL2 relay stress ×7, re-plan r2 | **actual PASS 7/7** | FREEZE S3-0009, plan b3a02098..; result S3-0010; `evaluation/evidence/e2/sl2-relay-live-20261010/` |
| SL3 audit stress ×6 | **actual PASS 6/6** | FREEZE S3-0011, plan d768463d..; result S3-0012; `evaluation/evidence/e2/sl3-audit-live-20261010/` |
| SL4 receipt controls ×7 | **actual PASS 7/7** | FREEZE S3-0013, plan 851896f3..; result S3-0014; `evaluation/evidence/e2/sl4-receipt-live-20261010/` |
| SL5 trust freshness ×6 | **actual PASS 6/6** | FREEZE S3-0015, plan 9e14a148..; result S3-0016; `evaluation/evidence/e2/sl5-trust-live-20261010/` |
| SL6 barrier and expired duty ×9 | **actual PASS 9/9** | FREEZE S3-0017, plan 78d6ebfb..; result S3-0018; `evaluation/evidence/e2/sl6-barrier-live-20261011/` |
| SL7 wrong destination and expiry boundary ×6 | **actual PASS 6/6** | FREEZE S3-0019, plan d4fa294e..; result S3-0020; `evaluation/evidence/e2/sl7-destination-live-20261011/` |
| P3 | closed: ProVerif re-run done (`p3-proverif-20261012/`); mutants and window NOT RUN (A1-0080, A1-0081) | A1-0080..A1-0082 |
| P4-1 one-command gate run | **run stages PASS: exit 0, 56/56, 4749.50 s** (launched by agent 1 on FREEZE S3-0021); not gate E PASS | plan c0086019..; result S3-0022; `evaluation/evidence/e3/gate-run-20261012/` |
| P4-2 RQ1-E.md | **final** at 69dabfba.. (`fill_gate.py` exit 0, 0 problems; review and ACK record added after A1-0084/S2-0022, no result changed) | `evaluation/reports/RQ1-E.md`; `evaluation/reports/fill_gate.py.txt` |
| Post-run reviews | A1-0084 (ledger) and S2-0022 (protocol): no discrepancy | `ledger/evidence/gate-e-review/`; `protocol/evidence/reviews/s2-0022-gate-run/` |
| P4-3 gate RESULT | **sent**: S3-0023, one manifest | `outbox/0023-gate-result-e.md` |
| P4-3 ACKs | **all three match**: A1-0085 (9d3e904), S2-0023 (ed3f99f), S3-0024 (bc10947e.., awaiting agent 1's commit) | `../../outbox/0085-ack-gate-result-e.md`; `../agent-2-proxy/outbox/0023-ack-gate-result-e.md`; `outbox/0024-ack-gate-result-e.md` |
| P4-4 | **done**: GATES.md gate E PASS (solo phase), exact A1-0082 wording; BOARD at F0 | `communication/GATES.md`; `communication/BOARD.md` |

- FREEZE S3-0019 is released. No services are running.
- Decisions D47 (paper crash relabel) and D48 (SL0 choices) are in `communication/DECISIONS.md`.

**Catalog progress: 56/56 actual. The catalog comparisons are complete.**

No catalog slice remains. P3 is closed. The gate run and RQ1-E.md are done (S3-0022), both post-run reviews are in
(A1-0084, S2-0022), the P4-3 gate RESULT is S3-0023, the three ACKs are A1-0085, S2-0023 and S3-0024, and P4-4 is
recorded (GATES.md gate E PASS, solo phase; BOARD at F0). **Solo P4 is complete.**

**Next: none** until F is planned or the original agents return. Agent 1 commits S3-0024, GATES.md, BOARD.md and
this STATUS.md and HANDOFF.md, and pushes `agent-1` only; pushing `main` is a human decision. F needs its own plan
(PLAN.md §6 F0, the gate F checklist) and the human's go-ahead. The original agents 2 and 3 may overturn the
solo-phase PASS on return.

## Runner facts (after SL0 and SL1)

**Solo plans** come from `e2.create_plan(..., review_mode='solo-correlated')`:

- FREEZE `S3-NNNN` with a `Plan-sha256:` header;
- ACKs `A1-NNNN` (in `communication/agent-1/outbox/`) and `S2-NNNN` (in
  `solo/agent-2-proxy/outbox/`);
- all three must be committed in ancestors of HEAD;
- ACK index `{agent-1, agent-2, freeze}`.

Build the index with `git log -1 --format=%H HEAD -- <path>` plus the blob sha256, as in
`tmp/p3/sl1-run/acks.json`.

**Configuration:**

- Ports: PBC 18545 and DBC 18546. Chain IDs 18545/28545.
- Cast hash checkpoint policy.
- Host tool override in `evaluation/host-tools.json`. Never edit `evaluation/toolchain.json`.

**Second-deployment path (live-proven in SL1).** Pattern: `e1._profile(..., subject_substitution=True)`.

- D1 runs the controls.
- D2 is a fresh deployment on the same chain pair, with its own bootstrap, adapter and 0700 state.
- SL2+ can generalize this into a stress-instance helper. That is new evaluator bytes, so it needs a
  new plan and ACKs.

**Frozen plan inputs** (`agent3Sources`): every `evaluation/**/*.py` (including evidence scripts),
fixtures and scenarios JSON, `interfaces`, root `AGENTS.md`/`SPEC.md`/`PLAN.md`/`uv.lock`/`pyproject.toml`,
toolchain and host-tools. Keep helper scripts out of `evaluation/` as `.py` files; store them as
`.py.txt`.

**Scratch:**

- `tmp/p3/sl{1,2,3}-run/` hold raw outputs and the private state, which is never published.
- Helpers live in `tmp/p3/sl0/scripts/bracket.py` and `tmp/p3/sl2-run/scripts/select_audit.py`.
- `tmp/p3/sl4/` holds the SL4 RED, suite, bracket and control-reason outputs, plus the scratch reason test.

## Toolchain

- Python: `.venv`, 3.13.5 (frozen 3.13.13). Agent 1 aligned the transitive packages with `uv.lock`
  before SL1.
- Foundry 1.8.5 at `~/.foundry/bin`.
- solc 0.8.37 at `~/.svm/0.8.37/`.
- ProVerif 2.05: declared local build bc2cd5ed..; the 7 correspondence tests pass with it.

## Pins

- Ledger 933d2a7 (195 entries, c7b7dd51..).
- Protocol 0716a8e (108 entries, d16ddad8..; hook f0ab2400..).
- Snapshots come from Git blobs, so working-tree edits by agent 1 or agent 2 (proxy) cannot enter a
  run.

## SL4 runner facts (S3-0013)

- `e2.create_plan(..., receipt_stress=True, review_mode='solo-correlated')`; matrix rows carry
  `variant` and `field`; case directories are `repaired-e-<variant>[-<field>]`.
- `e1.deviation_argv` builds the deviating-witness argv only from the plan template (no `--value`);
  `stress_deviate` re-hashes the tool bytes and re-checks the deployment file before each call.
- A non-zero tool exit is a failed trial; `receipt-stress/deviation-refusal.json` keeps only exit
  code, output sha256 and first line. The raw `receipt-deviate-NN.txt` log must not be published.
- The D2 worker is probed at baseline and after every catalog step (`workerSteps` in `result.json`).

## Next allowed actions

1. **SL4 is complete** (S3-0014). The selection and scan helper for SL4 is
   `tmp/p3/sl4-run/scripts/select_audit.py` (adds the frozen-vector `signerPrivateKey` values).
2. **SL5 is complete** (S3-0016). Its selection helper is `tmp/p3/sl5-run/scripts/select_audit.py` (adds `trust`).
3. **SL5 runner facts (S3-0015):** `e1.sign_list_argv` builds the producer argv only from the plan
   templates; `stress_sign_list` re-hashes `sign_list.sh` and `SignList.s.sol` and re-checks the
   deployment file; a non-zero producer exit writes only `trust-stress/sign-list-refusal.json`.
4. **SL6 is complete** (S3-0018). Its selection helper is `tmp/p3/sl6-run/scripts/select_audit.py` (adds `barrier`).
5. **SL6 runner facts (S3-0017):** `e1.barrier_sign_argv` (templates `revoke-alice`, `short-duty`; `untilIn`
   bounded 25..600); the collector records `current_checkpoint`, `timing`, `staleCause`, `expiredStep` and
   `decisionCollections`; only the DBC clock moves, only in expired-duty rows.
6. **SL7 is complete** (S3-0020). Its selection helper is `tmp/p3/sl7-run/scripts/select_audit.py` (adds `destination`, `source` and `destination-stress/source/`).
7. **SL7 runner facts (S3-0019):** B is `source-instance/` (third deployment, same chain pair; labels
   `owner-deploy-source`, `owner-bootstrap-source`); `destinationFunding` and `sourceDeployment` are in the case
   manifest; the expiry pin is `evm_setNextBlockTimestamp` with no `evm_mine`.

## Gate runner facts (S3-0021, P4-1)

- `evaluation/e_gate.py`: `create_plan(run_id, freeze_message)` (solo only, S3 freeze) embeds the ten slice plans of the existing
  `e2.create_plan` flags (`expired_retry` for the 6 crash rows, then duplicate, nonce replay, SL1-SL7); `verify_plan` regenerates the gate
  plan and calls `e2.verify_plan` on every slice plan (about 18 s). Plan `evaluation/evidence/e3/gate-plan-20261012/integration-plan.json`,
  sha256 c0086019.., runId `E-gate-20261012`, 646 KB.
- `e2.py` refactor (behaviour-preserving): `probe_name`, `case_name`, `slice_mode`, `slice_status`, `run_row`; `execute` calls them.
  The gate calls `e2.run_row` per row; slice output `<out>/catalog/<slice>/<case>/<profile>/...` (layouts unchanged).
- Failures: each row once; FAILED rows recorded and the run continues; NOT_RUN rows listed; no retry. Output must be outside the repo.
- Stage outputs: `verify-freeze.json`, `versions.json` (+ `versions/*.txt`), `bracket-pre.json`, `bracket-post.json`,
  `catalog-coverage-56.json`, `proverif/`, `gate-evidence.json`, `manifest.json` (rows, memory, worktree, resultFiles).
- A passing run gives 7 VERIFIED and 2 PENDING (RQ1-report, three-matching-acks). `gate.py` unchanged, still BLOCKED.
- Run: `.venv/bin/python -m evaluation.e_gate --plan <plan> --acks tmp/p3/gate-run/acks.json --output tmp/p3/gate-run/out`, in the
  background; stop with `kill -INT` (SIGTERM is not trapped). Expected about 1.5 h, up to 2.5 h.
- Scratch: `tmp/p3/p4/` (RED/GREEN/suite outputs, bracket, `scripts/keyscan.py.txt`). Publication after the run needs a selection
  helper like `tmp/p3/sl7-run/scripts/select_audit.py`, run per slice directory.

## Gate run publication facts (S3-0022, 2026-10-12)

- **Raw output** (job tmp, never published unselected): `tmp/p3/gate-run/out` (78299 files incl. 122 SQLite side
  files created after the run by read-only DB opens), plus `run.log`, `run.meta`, `run.exit`, `acks.json`.
- **Selection and scan helper:** `tmp/p3/gate-run/scripts/select_gate.py` (= published
  `evaluation/evidence/e3/gate-run-20261012/select_gate.py.txt`, dcca1e2b..):
  - `select <repo> <raw-out> <gate-run-dir> <evidence-dir>` (refuses a non-empty target);
  - `scan <repo> <raw-out> <evidence-dir> [extra files]`.
  - The forbidden set is 18 label keys (incl. `deployer`, as in agent 1's scans), the 64-hex private keys of every
    `**/vectors/*.json`, and the 61 release tokens. The databases are opened `immutable=1`, so nothing in
    the raw output is touched.
- **Checks:**
  - `tmp/p3/gate-run/check/publication_check.py`: historical path comparison and the pre-check of agent 1's
    8 tools;
  - `tmp/p3/gate-run/check/margins.py`: thin-row margins.
  - Both are published as `.py.txt`.
- **RQ1-E.md build:**
  - the merged draft is `tmp/p3/p4/final/RQ1-E.merged.md`, made by `merge_edits.py` from `tmp/p3/p4/RQ1-E.md`
    plus later edits;
  - fill with `tmp/p3/p4/final/fill_gate.py` against the **raw** output (the published copy lacks the 112
    snapshot `resultFiles`);
  - `fill_gate.py` refuses an existing `--out`, so delete before re-filling.
- **Commit note:** `evaluation/evidence/e3/gate-run-20261012/run.log` matches `.gitignore` `*.log`, so it
  needs `git add -f`.
- **P4-3 RESULT:** sent as S3-0023 (see below).

## P4-3 gate RESULT facts (S3-0023, 2026-10-12)

- **One manifest:**
  - `manifest.json` 908fd6156ac5c6c4f640686fbddade3f9720cf29fb1e579f7c3d01f0909205a2;
  - `gate-evidence.json` 47e38dd369ce686d5298f909c43c79cdf4b7eff4d20d41988a57f80974538500;
  - RQ1-E.md 69dabfbab9d9deeb0d94b448da6bf9b9674ce25c7c94e1b101f67c4804c89b8f (1338 lines);
  - plan c0086019..;
  - run HEAD 21b37fb and evidence commit c2c81d5.
  S3-0023, RQ1-E.md and my STATUS.md and HANDOFF.md go into one agent-1 commit, and the ACKs name that commit.
- **RQ1-E.md 0ec51e8e.. → 69dabfba..:** edited directly in the repository. `fill_gate.py` was not re-run, so the
  filled cells are unchanged. The changes are: the top status block, one §3.4 row (66 request-bound decisions,
  S2-0022 G), the S2-0022 result in §6.1, one §17 row, A1-0084 in §18.1, S2-0022 in §18.2, and the §18.3 status.
  **Do not edit RQ1-E.md again before the ACKs:** any change alters the sha256 that S3-0023 and the ACKs name, and
  would need a new RESULT.
- **Criteria:**
  - 1-6 and 8 VERIFIED in `gate-evidence.json`; criterion 4 is human-scoped (A1-0080 wording);
  - 7 (RQ1-report) is satisfied by RQ1-E.md 69dabfba.., subject to the ACKs;
  - 9 is pending: A1-0085, S2-0023, S3-0024.
  `gate-evidence.json` is never edited: criteria 7 and 9 are adjudicated in GATES.md. `gate.py` stays fail-closed.
- **S3-0024 (done, 2026-10-12):** both ACKs checked (same four items, `Type: ACK`, no blocker); evidence and model
  signed off with the correlated-review disclosure and the self-sign-off caveat; GATES.md and BOARD written with
  A1-0082 P4-4's exact wording. F is not started, and it needs its own plan.

## P4-4 facts (S3-0024, 2026-10-12)

- `gate-evidence.json` keeps criteria 7 and 9 PENDING (run output, never edited). They are adjudicated VERIFIED in
  GATES.md on the three ACKs. `evaluation/gate.py` stays fail-closed and never emits PASS.
- GATES.md: header says E PASS in the solo phase and F/G NOT RUN; the E checklist is ticked with pointers; the dated
  record "Solo-phase record: gate E PASS (solo phase); board at F0, 2026-10-12 IST" is the last section. F and G
  checklists are unticked.
- BOARD.md: the new top section is the gate E PASS / F0 checkpoint. The board had not been updated between
  2026-10-09 and this entry; the solo-phase slice records are in GATES.md.
- Do not edit RQ1-E.md, the gate manifest or `gate-evidence.json`: the ACKs name their sha256.
