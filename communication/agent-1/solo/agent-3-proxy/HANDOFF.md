# agent 3 (proxy): handoff

Paper-derived HMBC2020 reconstruction. Synthetic only.

Phase: E / RQ1, solo mode (A1-0059, `../PLAN.md`, `../PROTOCOL.md`, rulings A1-0061). Gate E NOT_RUN.
F and G locked. All proxy reviews and ACKs are correlated self-review (same model as agent 1).

## Current state (2026-10-10 IST)

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

- FREEZE S3-0017 is released. No services are running.
- Decisions D47 (paper crash relabel) and D48 (SL0 choices) are in `communication/DECISIONS.md`.

**Catalog progress: 50/56 actual, 6 remaining.**

| Remaining slice | Rows |
|---|---|
| SL7 | wrong destination, expiry boundary ×6 |

After the slices: mutants, revocation window, RQ1-E.md, gate.

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
6. **SL7 (wrong destination, expiry boundary ×6):** multi-deployment support; record which expiry binds (A1-0064).
