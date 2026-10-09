# Phase E solo completion plan (agent 1 + two proxy subagents)

Paper-derived HMBC2020 reconstruction. Synthetic fixtures only. F and G stay locked until gate E
actually passes.

## Why this exists

Human directive, 2026-10-09 ~19:40 IST (recorded in A1-0059):

- Agents 2 and 3 have reached their weekly limits and will not work for at least a few days.
- Agent 1 is to complete Phase E alone and make all required decisions, using two subagents:
  - **proxy-2** does agent 2's work (`protocol/**`);
  - **proxy-3** does agent 3's work (`evaluation/**`, `interfaces/**`, shared communication, root
    docs, gate).
- They communicate in this directory.
- Everything for Phase E is to be integrated, so that F can start from a ready codebase.

This overrides two `AGENTS.md` rules, by the human who set them: "do not launch extra agents" and the
per-agent ownership for the absent agents. Everything else in `AGENTS.md` stays in force:

- HMBC only, no JANUS;
- synthetic fixtures, no external messages or deployments;
- no `archive/**` edits;
- no force push, history rewrite, reset, stash, clean or rebase;
- classify every finding and keep refuted hypotheses;
- never mark DONE on compile alone.

**Honesty cost, which must be disclosed in RQ1-E.md and GATES.md:** proxy reviews and ACKs come
from the same model as agent 1. They are correlated self-review, not independent review. Gate E
evidence must say so. The original agents 2 and 3 can re-review on return.

## Current state (verified from origin at 2026-10-09 19:35 IST)

| Item | State | Evidence |
|---|---|---|
| E0, v1 freeze | CLOSED, FREEZE.json f700292e.. | agent-3 BOARD |
| E1, 9 positive controls | 9/9 actual PASS | A3-0030 |
| ProVerif correspondence slice + destination mutant | done (symbolic) | A3-0033 |
| E2 actual comparisons | 12/56: 6 recovery+expiry (A3-0036/0038), 3 duplicate outcome (A3-0040), 3 identical replay (A3-0045) | agent-3 evidence/e2 |
| E2 remaining | 44 comparisons; 4 paper crash classifications BLOCKED/unproved | A3-0049 |
| Subject substitution (E01) | oracle, collector and completion checker written; no live run | A3-0046..0049 |
| Live mutants, integrated revocation window | not run (owner evidence only: A1-0043 mutants, A1-0046 window) | |
| RQ1-E.md, gate E run, 3 same-source ACKs | not started | GATES.md "NOT RUN" |
| Ledger owner rehearsal of all 56 | 56/56 (owner evidence, not gate evidence) | ledger/evidence/e2-full-rehearsal |

Branches: agent-1 e66eeb9, agent-2 96ebe16, agent-3 8e5a6dd and main 5f71184. All three fork from
main 5f71184, and their changed paths are disjoint (no overlap; no deletions), so a merge is
conflict-free.

## Blocker found at start (honest record)

The Claude Code permission classifier refused the following as "Modify Shared Resources":

1. `git merge origin/agent-3` and `git merge origin/agent-2` into the local agent-1 branch;
2. building a private merged copy of the three branches in scratch space.

Read-only access to peer branches (`git show origin/agent-N:…`) still works. I did not retry or
route around either refusal. **Integration (step P1) waits for the human to allow it.**

What the human needs to do:

- **Either** add a permission rule such as `Bash(git merge origin/agent-2:*)` and
  `Bash(git merge origin/agent-3:*)` (and allow edits under `protocol/**` and `evaluation/**`),
  **or** run the two merges themselves:

  ```
  git merge --no-ff origin/agent-3 && git merge --no-ff origin/agent-2
  ```

- Then tell agent 1 to continue.

## Work split

| Owner in this phase | Writes | Main responsibilities |
|---|---|---|
| agent 1 (orchestrator, ledger) | `ledger/**`, `communication/agent-1/**`; **only one doing Git writes** | ledger fixes, if any; ledger-scope ACKs; mutant deployments; revocation window; ledger claims in the report; integration commits and pushes to `agent-1` |
| proxy-2 (acting agent 2) | `protocol/**`, `communication/agent-1/solo/agent-2-proxy/**` | relay fault hooks and worker behaviour needed by the remaining schedules (TDD); protocol READY handoffs; protocol-scope ACKs of each FREEZE; protocol/key assumptions review of RQ1-E.md |
| proxy-3 (acting agent 3) | `evaluation/**`, `interfaces/**` (no v1 change expected), `communication/{BOARD,GATES}.md`, root active docs, `communication/agent-1/solo/agent-3-proxy/**` | runners, oracles and FREEZE plans per family; live two-chain runs; mutants matrix; ProVerif re-run; RQ1-E.md; gate E run; BOARD/GATES records |

Rules shared by all three:

- **Git:** proxies never run Git write commands (no add/commit/merge/push/checkout/stash). Agent 1
  commits exact paths after reviewing each READY.
- **Ports and directories (no clobbering):**

  | Who | Ports | Output under |
  |---|---|---|
  | agent 1 | 17545-17599 | `/home/saiyamjain/.claude/jobs/aed51961/tmp/a1/` |
  | proxy-2 | 19545-19599 | `/home/saiyamjain/.claude/jobs/aed51961/tmp/p2/` |
  | proxy-3 | 18545-18599 | `/home/saiyamjain/.claude/jobs/aed51961/tmp/p3/` |

  Durable evidence goes to the owner's evidence directory in the repo.
- **Services:** only proxy-3 starts the integrated two-chain + adapter services, and only for an
  ACKed plan. It stops them and records PIDs ended.
- **FREEZE and ACK:** exact plan SHA-256 still required. Turnaround is immediate (no waiting on
  humans).
- **Messages:** numbered S2-NNNN (proxy-2), S3-NNNN (proxy-3) and A1-NNNN (agent 1, in the normal
  outbox). Each has the headers of `communication/PROTOCOL.md`.

## Phases

**P0: read-only preparation (permitted now).**

- proxy-3 maps each remaining comparison to the runner support that exists in agent-3 8e5a6dd, and
  lists what is missing.
- proxy-2 maps each remaining comparison to the fault hooks or worker behaviour that exist in
  agent-2 96ebe16, and lists what is missing.
- Both draft the work order, and proxy-3 drafts the RQ1-E.md skeleton with the 12 completed results.
- Output only into the proxies' solo folders. No services, no extraction, no edits elsewhere.

**P1: integration (needs human permission).**

- Merge agent-3 then agent-2 into agent-1 (merge commits; no rewrite).
- Fresh baseline on the integrated tree:
  - `forge test --root ledger`;
  - protocol pytest;
  - evaluation pytest;
  - the schema/vector checks and `e0_verify`.

  Record exit codes and hashes.
- Push agent-1.

**P2: remaining 44 comparisons, family by family.** Order: the cheapest first, then those reusing
existing runners.

1. E01 subject substitution ×3: finish the A3-0049 plan.
2. E01 forged tuple ×3, wrong destination ×3 (second deployment), new-reference replay ×3, same nonce
   with distinct digests ×1.
3. E02 wrong issuer ×3, signed-list rollback ×3, pre-barrier and post-barrier revocation ×6, expired
   duty ×3.
4. E03 dropped outcome ×3, fabricated outcome ×3, receipt binding/signature/positive ×7, and the
   remaining crash rows.
5. The four paper crash rows remain BLOCKED/UNPROVED unless new evidence exists. They are reported
   as an ambiguity (paper silent on durability), never as a finding.

Cycle for each family:

1. proxy-2 READY, if hooks are needed;
2. proxy-3 FREEZE with the exact plan hash;
3. ACKs from agent 1 (ledger) and proxy-2 (protocol);
4. live run from fresh state;
5. reviews;
6. agent 1 commit and push.

**P3: mutants, windows and formal.**

- Live mutant matrix: the repaired suite against `mutant-*`. At least the destination-binding
  mutant must be detected (PLAN A-E2), and legitimate controls must still pass.
- Integrated revocation-window measurement, compared against A1-0046.
- ProVerif re-run on the integrated tree.

**P4: close RQ1.**

1. RQ1-E.md: agent 1 checks the ledger claims, proxy-2 the protocol/key assumptions, proxy-3 the
   evidence and model.
2. One-command gate E run from a fresh state.
3. The same-source manifest is ACKed by all three, with the correlated-review disclosure.
4. GATES.md is updated, and BOARD advances to F0 **only if every mandatory E criterion passes**.
   Otherwise gate E is recorded FAIL/BLOCKED with reasons.
5. Push agent-1. Fast-forwarding `main` is a human decision; it is not done by agent 1.

## Gate E checklist (from communication/GATES.md, agent-3 8e5a6dd)

1. v1 interfaces frozen; source map and paper-gap choices reviewed. **Done (E0).**
2. Legitimate access succeeds; denied identity/issuer cases fail for the right reason. **Done (E1).**
3. E01/E02/E03 each have a source/profile distinction, observed traces, limitations and a
   classification. **Partial (12/56).**
4. Applicable repaired scenarios pass; meaningful mutants fail; deny-all is rejected by positive
   controls. **Pending (live mutants).**
5. Two-chain real integration and durable worker recovery from fresh state; symbolic crypto mode
   recorded. **Partial.**
6. ProVerif correspondence outputs and negative control saved. **Done (A3-0033); re-run at gate.**
7. RQ1-E.md answers RQ1; no JANUS findings. **Pending.**
8. Hashes, commands and exit codes recorded; no input changed during the run. **Pending (gate run).**
9. Three ACKs on the same report and manifest; gate E PASS before F. **Pending.**
