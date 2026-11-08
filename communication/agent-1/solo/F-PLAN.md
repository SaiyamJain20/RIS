# Phase F solo plan (agent 1 + two proxy subagents)

Paper-derived HMBC2020 reconstruction. Synthetic fixtures and TEST-ONLY keys only. G stays locked
until gate F actually passes.

## Why this exists

Human directive, 2026-11-08 ~22:50 IST, recorded in A1-0119. The machines running agents 2 and 3
have reached their usage limits. Agent 1 works as agent 1 and runs two subagents for the other two,
"like before", which means solo Phase E (A1-0059, `PLAN.md` and `PROTOCOL.md` in this directory).

`PROTOCOL.md` here still governs, with these F adaptations:

- **Phase.** F is the current phase. F0 was accepted in A3-0073: `F0_ACCEPTANCE_CANDIDATE2.json`
  03dcf485.., `interfaces/v2/FREEZE.json` 7bb1d243.., and v2.1 FREEZE 232b84bb... Owned
  implementation is authorized; integrated execution needs a separate execution FREEZE with exact
  ACKs.
- **Rule 9 in PROTOCOL.md** ("F and G stay locked until gate E really passes") is satisfied: gate E
  passed on 2026-10-12. G stays locked until gate F passes.
- **Message IDs** continue the solo series: S2-0024 onwards (proxy-2), S3-0025 onwards (proxy-3) and
  A1-0119 onwards (agent 1, normal outbox).
- **Mailboxes** are the same: `agent-2-proxy/` and `agent-3-proxy/` in this directory, each with
  `STATUS.md`, `HANDOFF.md` and `outbox/`.

## Baseline

| Item | Value |
|---|---|
| Merged tree | agent-1 7e51f5e = agent-1 959fda9 + origin/agent-3 6358f7c (84f46f9) + origin/agent-2 9d56d2c (7e51f5e) |
| Ledger | reviewed at 85c59f5, manifest 70f541cd.. (429 entries); A3-0077, A3-0080 |
| Protocol | runtime READY A2-0076 (7d97b90, manifest 7de8f334..), deltas A2-0078 and A2-0079; cumulative 7 non-evidence files since 7d97b90 |
| Evaluation | C-F1 WORKING; v2 checkers A3-0098..0104; no F runner, no oracle for the 32 cases, no TLA+ model |
| F plan of record | `evaluation/evidence/reviews/f0-revision8-20261104/SOURCE-INTERFACE-PLAN.md` 76069506.., `f_matrix.json` 2230daf3.. (32 cases FL-1..FL-11, F-12..F-32), `fault-model.csv` |
| Interface | v2 wire family, schema v2.1 d43c3a9a.. |

## Open items taken over

**Agent 3's (proxy-3):**

- review A2-0076, A2-0078 and A2-0079;
- decide A2-0077 F1 (BindingExport anchor selection in `collect`) and F2 (worker store lock, which
  touches the E-listed `worker.py`);
- answer A2-0080: the `checkpoint_rpc_v2` pbcHead after an authEpoch change; only `expiry` and
  `overtaken-decision-sequence` can be produced from real evidence; a governance ADD makes earlier
  requests stale;
- give an exact ACK of, or amendments to, A2-0074 O1..O6;
- close its own A3-0096 and A3-0097;
- build the C-F1 deliverables:
  - F runner and fault oracles;
  - `evaluation/models/f/DecisionQuorum.tla` and `.cfg`, checked with TLC (pinned jar hash);
  - `evaluation/reports/RQ2-F.md`;
- execution FREEZE(s), integrated runs and the gate F run.

**Agent 2's (proxy-2):**

- answer agent 3's decisions, including any protocol amendment test-first, with a delta READY;
- add any fault hook the runner needs and the owner has not built;
- protocol-scope ACK of each FREEZE and review of each result;
- open facts agent 2 recorded:
  - `binding_open` converts deployBlock with `int()` after the network step;
  - the stale E0/E1 labels in the pinned `exports/adapter.json`;
  - the H5 worker variant is reachable only through the alternate entry.

**Agent 1's:**

- ledger-scope checks and ACKs;
- any ledger fix the runs expose, as a new commit plus a fresh READY. Reviewed bytes are never
  rewritten.
- Carry the A1-0117 sequence paragraph into the ledger findings at the next ledger revision.

## Phases

| Phase | Content | Exit |
|---|---|---|
| P0 | read-only inventory: proxy-3 maps the 32 cases to existing evaluator, protocol and ledger support and drafts the work order, slices and positions on the open items; proxy-2 maps the cases to protocol hooks and fault injection, and lists gaps. Agent 1 runs the integrated baseline suites in the background. | S3 and S2 inventories; baseline exits recorded |
| P1 | open decisions and reviews (list above), then proxy-2 amendments test-first and an S2 delta READY | decisions published; delta READY checked by agent 1 (ledger-facing) and proxy-3 |
| P2 | proxy-3 builds the F runner, oracles and TLA+ model test-first, with no services. proxy-2 supplies missing hooks with READYs. | runner READY with focused and full-suite counts |
| P3 | per slice: proxy-3 execution FREEZE with the exact plan SHA-256; ACKs from agent 1 (ledger) and proxy-2 (protocol); live run from fresh state; INTEGRATION_RESULT; reviews from agent 1 and proxy-2; agent 1 commits and pushes | every case actual, failed and timed-out trials recorded |
| P4 | TLC runs; RQ2-F.md; gate F run from fresh state; three ACKs on the same report and manifest; GATES and BOARD advance to G0 **only if every mandatory F criterion passes**, otherwise FAIL or BLOCKED with reasons | gate record |

Proxy-3 proposes the slice split in P0 and agent 1 accepts or amends it.

## Rules (carried from PROTOCOL.md, plus F specifics)

- **Git.** Only agent 1 runs Git write commands. Proxies may run read-only Git commands only. Agent 1
  commits exact reviewed paths and pushes to `agent-1`. No push to `main` or to a peer branch.
- **Ports and scratch:**

  | Who | Ports | Scratch |
  |---|---|---|
  | agent 1 | 17545-17599 | `/home/saiyamjain/.claude/jobs/aed51961/tmp/a1/` |
  | proxy-2 | 19545-19599 | `/home/saiyamjain/.claude/jobs/aed51961/tmp/p2/` |
  | proxy-3 | 18545-18599 | `/home/saiyamjain/.claude/jobs/aed51961/tmp/p3/` |

- **Host.** 16 cores, about 7 GiB of memory available and 16 GB of disk free. Never run two full
  suites or two live runs at once. Delete scratch clones after use. After stopping any runner, check
  `ps` for orphaned pytest or anvil processes, and kill them by exact PID, never with `pkill -f`.
- **Long jobs** run in the background (`run_in_background`), and you wait for the completion notice.
  No foreground sleeps (agent 2's human process rule of 2026-11-08).
- **Secrets.** The anvil dev key is never written to any output or evidence file. It is passed only
  through the `ANVIL_DEV_KEY` environment variable. TEST-ONLY witness keys stay TEST-ONLY.
- **Safety-classifier rule.** If a safety classifier stops an action, stop that item, leave the tree
  consistent, report plainly, and do not retry or rephrase.
- **Honesty.** Classify every finding. Keep refuted hypotheses and failed trials. Never mark DONE on
  compile alone. Bounded TLC exploration is not a proof of production consensus. Every proxy review
  and ACK is correlated self-review.
