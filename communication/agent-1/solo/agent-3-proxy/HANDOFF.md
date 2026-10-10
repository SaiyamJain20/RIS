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
| SL2 relay stress ×7, re-plan r2 | FREEZE S3-0009, plan b3a02098..; **waiting for ACKs** | `evaluation/evidence/e2/sl2-relay-runner-r2-20261010/`; `e1.observe_worker_export` |

- FREEZE S3-0005 is released. No services are running.
- Decisions D47 (paper crash relabel) and D48 (SL0 choices) are in `communication/DECISIONS.md`.

**Catalog progress: 15/56 actual, 41 remaining.**

| Remaining slice | Rows |
|---|---|
| SL2 | forged tuple ×3, new-reference ×3, same nonce ×1 |
| SL3 | dropped / fabricated outcome ×6 |
| SL4 | receipts ×7 |
| SL5 | wrong issuer, rollback ×6 |
| SL6 | barriers, expired duty ×9 |
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

- `tmp/p3/sl1-run/` holds raw SL1 outputs and the private state, which is never published.
- Helpers live in `tmp/p3/sl0/scripts/bracket.py` and `tmp/p3/sl1-run/scripts/select_audit.py`.

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

## Next allowed actions

1. SL2 r2 run, after A1 and S2 ACKs of S3-0009 are committed:
   - build the ACK index at `tmp/p3/sl2-r2-run/acks.json` (keys agent-1, agent-2 and freeze);
   - run the S3-0009 command;
   - audit with `tmp/p3/sl2-run/scripts/select_audit.py` (it already handles the relay files, the
     secret and token scan, and verified never-instantiated probes);
   - audit with `tmp/p3/sl1-run/scripts/select_audit.py`, after extending its `SELECT` patterns for
     the relay-stress files (`timeline`, `forged-certificate`, `stress-transaction`, the
     `before-second`/`after-second` snapshots);
   - publish S3-0008.
2. Next is SL3. S2-0007 notes apply: the `deviating_witness` invocation for SL4, and A31 discipline
   for SL6.
