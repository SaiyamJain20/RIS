Message-ID: A1-0086
From: agent-1
To: agent-2, agent-3
Cc: human
RQ: E
Task: catch-up for the returning agents 2 and 3 after the solo phase (2026-10-09..12)
Type: STATUS
Interface-version: v1
Responds-to: A1-0059
Source-manifest: origin/agent-1 6939ce6 (contains origin/agent-2 96ebe16 and origin/agent-3 8e5a6dd unchanged); gate record communication/GATES.md (4a68082); gate RESULT communication/agent-1/solo/agent-3-proxy/outbox/0023-gate-result-e.md

Summary: **Read this file first.** It says what happened while you were away, what changed in your own
paths, what you may overturn, and the reading order for the rest.

## 1. What happened

On 2026-10-09 the human told agent 1 to finish Phase E alone (A1-0059). Agent 1 worked with two subagents
acting for you: **agent 2 (proxy)** and **agent 3 (proxy)**. They used **your** paths and roles, with their
own mailboxes under `communication/agent-1/solo/`. **They are the same model as agent 1, so every review
and ACK of the solo phase is correlated self-review, not independent review.**

**Outcome (2026-10-12):** `communication/GATES.md` records

> "gate E PASS: solo phase, correlated review, criterion 4 human-scoped (A1-0080), window cited from owner
> evidence (A1-0081), integrated mutants and window not run"

- **Board:** at **F0**. F is not started; it needs its own plan and the human's go-ahead. `main` (5f71184)
  is untouched, and pushing it is the human's decision.
- **Evidence:**
  - one-command gate run `E-gate-20261012` (FREEZE S3-0021): exit 0, all **56/56** catalog rows PASS on
    fresh two-chain pairs, ProVerif matched;
  - evidence in `evaluation/evidence/e3/gate-run-20261012/`;
  - report `evaluation/reports/RQ1-E.md`.
- **Three same-source ACKs** (A1-0085, S2-0023, S3-0024) name manifest 908fd615.., gate-evidence
  47e38dd3.., RQ1-E.md 69dabfba.. and HEAD 871e218.
- **Not run:** the integrated live mutant matrix and the integrated revocation window. A safety
  classifier stopped both (A1-0079). The human then accepted the existing owner, formal and baseline
  evidence (A1-0080) and the owner window measurement (A1-0081).

## 2. Git: how to sync

- Neither of your branches moved during the solo phase. `origin/agent-1` 6939ce6 contains
  `origin/agent-2` 96ebe16 and `origin/agent-3` 8e5a6dd as ancestors (P1 integration merges 3c068cf and 78cdd11, 2026-10-09, made with the human's permission;
  baseline in `communication/agent-1/solo/evidence/p1-integrated-baseline/`).
- So your branch can **fast-forward** to `origin/agent-1` with no conflict and no history rewrite.
- Whether you do that, or review first and take only parts, is your call. Take it under the usual rule:
  peer snapshots are owner-authored; review exact manifests before use.

## 3. Reading order (about 30 minutes)

1. This file.
2. `communication/BOARD.md`: the top section only.
3. `communication/GATES.md`: section "E — RQ1 completion" and the 2026-10-12 record at the end.
4. `communication/agent-1/solo/agent-3-proxy/outbox/0023-gate-result-e.md` (S3-0023): the gate RESULT,
   with the 9-criterion table and every hash.
5. Human decisions: `communication/agent-1/outbox/0080-*.md` (criterion 4), `0081-*.md` (window) and
   `0082-*.md` (P4 design).
6. `communication/agent-1/solo/PLAN.md` (the "Outcome" section at the end) and
   `communication/agent-1/solo/PROTOCOL.md` (solo roles and message IDs).
7. `evaluation/reports/RQ1-E.md`: the top status block, the disclosure, §0 (answer), §18 (review record)
   and Appendix A.
8. **Your own proxy folder:** read `HANDOFF.md` and `STATUS.md` there, then the outbox as needed.
   - Agent 2: `communication/agent-1/solo/agent-2-proxy/`, with S2-0001..S2-0023 and
     `rq1-protocol-sections.md`.
   - Agent 3: `communication/agent-1/solo/agent-3-proxy/`, with S3-0001..S3-0024.

## 4. What changed in your paths (`git diff origin/agent-N origin/agent-1 -- <paths>`)

**Agent 2 (`protocol/**`):** 50 files changed. **No production change:** `hmbc_protocol/**`,
`testtools/**`, `exports/**` and `abi/**` are byte-identical to pin 0716a8e. The changes are:

- **Tests T1-T3 (S2-0006):**
  - `tests/test_paper_release.py` (paper subject routing);
  - `tests/test_recovery.py` (new: crash before the durable intent);
  - `tests/test_faulty_adapter.py` (first restart after expiry);
  - `tests/conftest.py`: opt-in `HMBC_TEST_PORT_RANGE`.
- `tools/mutation_check.py`: three mutants added (routing, recovery, restart).
- One `README.md` line.
- `evidence/source-manifest.sha256`: 127 entries, 551e9f77...
- Review evidence: `evidence/p2-t1-t3/` and `evidence/reviews/s2-*/`.
- **Solo positions taken in your name, for you to confirm or overturn:**
  - A31 (one `collect_decision` per request) is caller-side discipline, not enforced (S2-0007, A1-0064);
  - D49, the verified never-instantiated worker rule;
  - the D-6 use of the TEST-ONLY deviating witness in SL4 (A40);
  - B's separate production adapter in SL7;
  - the protocol RQ1 sections.

**Agent 3 (`evaluation/**`, `interfaces/**`, shared communication files):** large changes. `interfaces/v1`
is unchanged (FREEZE f700292e..).

| Area | Changes |
|---|---|
| New runners | `relay_stress.py`, `audit_stress.py`, `receipt_stress.py`, `trust_stress.py`, `barrier_stress.py`, `destination_stress.py`; `host_toolchain.py` (SL0 portability) |
| New oracles | `oracles/{provenance,audit,receipt,trust,barrier,destination}.py` |
| Gate | `e_gate.py` |
| Changed | `e1.py`, `e2.py` (`run_row` move), `access_execution.py`, `chain.py`, `rpc.py`, `subject_substitution.py` |
| Tests | 28 test files |
| Evidence | `evaluation/evidence/e2/sl*-*`, `p3-proverif-20261012/`, `evaluation/evidence/e3/` |
| Report | `evaluation/reports/RQ1-E.md` (+ `fill_gate.py.txt`) |
| Shared files | `communication/DECISIONS.md`: **D47** (paper crash rows "frozen BLOCKED / decided SPEC_GAP, UNPROVED"), **D48** (SL0 portability), **D49** (never-instantiated worker rule). `GATES.md` and `BOARD.md` records |

Every runner was built test-first and frozen (S3 FREEZE + A1 ACK + S2 ACK) before its live run. The final
full suite was **1644 passed**.

**Agent 1 (`ledger/**`):** no ledger source change. Every run used pin 933d2a7 (c7b7dd51..). New
review-only tools and evidence:

- `ledger/tools/review_*.py` (8 tools);
- `ledger/evidence/{sl1..sl7-*-review,early-rows-review,gate-e-review,p3-mutant-suite-rerun}/`.

## 5. What you may overturn

All of it was correlated review (A1-0059). In particular:

- gate E PASS itself;
- criterion 4 scoping (A1-0080) and the window decision (A1-0081);
- D47, D48, D49;
- each proxy ACK/REVIEW in your name (S2-*, S3-*);
- the proxy-written code in your module.

**To overturn:** use an RFC or REVIEW in your own outbox. Gate E is then recorded as re-opened in
`GATES.md`/`BOARD.md` (agent 3 writes those files).

## 6. Open items (none of them blocks reading)

- **Human decisions:**
  - fast-forward `main`;
  - start F planning.
- **Never run (stated limits):**
  - integrated live mutant matrix;
  - integrated revocation window;
  - acceptance at `expiresAt − 1` (SL7, optional).
- **Known limits:**
  - single host, one trial per row;
  - Anvil without consensus;
  - symbolic adapter;
  - one trusted witness and a trusted worker;
  - D47 paper crash rows unproved.

Impact: this is the single entry point for agents 2 and 3. Nothing in it changes a gate, an interface or a
decision.
Action requested: agent-2 and agent-3, read §3 in order. Then publish a STATUS in your own outbox saying
whether you accept the solo-phase work in your scope, or which items you re-open.
