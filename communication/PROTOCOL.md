# Three-agent communication and integration protocol

Current phase: F0 planning from the human-authorized shared baseline (D51/A3-0052).
The one-time main/agent-branch convergence is an explicit human exception to the
ordinary owned-branch publication rules below. Future interface/source changes
still require exact affected ACKs; F gate NOT RUN, G locked.

## 1. Single-writer ownership

**D57, 2026-11-14:** agent names are portable responsibility roles, not a person,
model, session or computer. Another authorized session may read and declare the
live handoff, continue the role, and publish its exact role-scope ACKs. Claude
proxy-2 is authorized for Agent 2, including protocol-source approval and FREEZE
ACKs. No original-session return or countersignature is needed. Keep one current
writer per scope and truthful authorship/correlation labels. Continuing a role
does not transfer files between module responsibilities.

| Writer | Owned paths | Reads |
|---|---|---|
| Agent 1 | `ledger/**`, its STATUS/HANDOFF and `communication/agent-1/outbox/**` | shared contracts, board, agent 2/3 outboxes and exported manifests |
| Agent 2 | `protocol/**`, its STATUS/HANDOFF and `communication/agent-2/outbox/**` | shared contracts, board, agent 1/3 outboxes and exported manifests |
| Agent 3 | `evaluation/**`, `interfaces/**`, root configuration/docs, shared communication files, prompt builder and all ROLE/START_PROMPT templates, its own runtime mailbox | every handoff and module's exported artifacts |

Nobody writes `archive/**`. A module review proposes a change to the owner; it does not edit the reviewed file. To transfer ownership of a file, agent 3 records a dated decision after both affected agents acknowledge it. Only one current writer is permitted.

## 2. Message format

Publish a new immutable file in your own `outbox/` named `0001-<type>-<subject>.md`, then increase the sequence. Write a temporary file in your own directory and rename it into place when complete. Never overwrite a sent message.

```text
Message-ID: A1-0001
From: agent-1
To: agent-2, agent-3
RQ: E
Task: A-E1
Type: READY | BLOCKED | QUESTION | RFC | ACK | REVIEW | FREEZE | INTEGRATION_RESULT
Interface-version: v1
Responds-to: none | <Message-ID>
Source-manifest: <path and SHA-256, or not-yet-created>

Summary: <one concrete result or request>
Evidence: <paths, command, exit code and actual result>
Impact: <which task/consumer is affected>
Action requested: <exact decision or work, recipient, dependency>
```

Use `QUESTION` for a missing implementation detail, `RFC` for a shared interface change, and `BLOCKED` when no safe work on the owned task can proceed. A claim without reproducible evidence is not READY.

## 3. Work cycle for every agent

1. Read the board, your current task/dependencies, and new messages in all outboxes addressed to you or `all` before editing.
2. Update your `STATUS.md` with `WORKING`, `WAITING`, `BLOCKED`, `READY_FOR_INTEGRATION` or `DONE_FOR_RQ`. Include current RQ/task and interface version.
3. Work only on owned files and the current RQ. Run isolated tests; record failures, controls and actual results.
4. Read new messages after a test batch, before changing an interface consumer, and before handoff. An agent need not interrupt a running command every few seconds.
5. Publish messages for a dependency-ready artifact, blocker, interface proposal or review result. Acknowledge messages by ID in your own outbox; do not edit the sender's file.
6. Before READY, update `HANDOFF.md` with exact exported artifacts, hashes, commands, results, limitations and the consumer's next action.
7. If waiting, improve current-RQ tests/evidence within your ownership. When an active peer is producing the needed dependency, remain in the session using host waits or 30–60-second pauses between file/message checks and resume automatically on its handoff. Do not stop merely because one task batch finished or spin in a tight polling loop. If a missing producer/external blocker requires human action and no independent work remains, publish a restartable handoff with that concrete dependency. Do not start the next RQ early.

## 4. Shared interface changes

- The proposing agent sends an RFC containing old/new fields or signatures, reason, compatibility impact, affected tests and migration of fixtures.
- Agent 3 asks both producers and consumers to ACK the exact proposed version. Silence is not acceptance.
- Agent 3 edits `interfaces/`, records the decision, publishes versioned vectors and then announces `INTERFACE_READY` as a READY message.
- Agents update their own module against that version. No unilateral field additions, renamed errors or undocumented fallback semantics.
- A shared dependency addition follows the same pattern. Agent 3 owns the root Python environment/lock; agent 1 owns ledger-specific locks. No concurrent shared package installation.

## 5. Integration freeze

Agent 3 owns the service processes and the integration record. Shared ports start at PBC 18545 and DBC 28545. Check for availability; allocate another pair and publish it if occupied. Only terminate processes started and recorded by the coordinator.

For each integration run:

1. Agent 3 publishes FREEZE with RQ, candidate interface version, run ID and affected paths. Agents 1/2 finish their current write/test, publish READY or a blocker, and ACK pinned commits/manifests.
2. All agents publish source manifests/ACKs. Agent 3 hashes the complete relevant tree, including uncommitted files and dependency locks. A dirty checkout is expected, so a commit ID alone is insufficient.
3. Agent 3 runs fresh-state integration, formal commands and required mutations/positive controls, saving exact commands, logs, exit codes, hashes and tool versions.
4. Agent 3 compares pre/post source hashes. Changed input files invalidate the run; refresh the freeze and rerun affected checks. Never claim a result for a tree that changed underneath it.
5. Publish INTEGRATION_RESULT and explicitly release the freeze. Each failing module is repaired by its owner. Freeze again for required retests; do not mask failures by changing the oracle to observed behavior.

Selected gate evidence is copied to a versioned `evaluation/evidence/frozen/<rq>/<run-id>/` directory. `evaluation/runs/` is disposable local output. Never delete evidence referenced by a completed RQ report.

## 6. RQ gate and advancement

- Agent 3 drafts the report and gate result. Agents 1/2 review the exact evidence; all three ACK the report/source manifests.
- Agent 3 marks a gate PASS only when every mandatory criterion in `GATES.md` is satisfied. No agent can advance its own phase independently.
- If a hypothesis is refuted by a completed experiment, report REFUTED and explain it. If the experiment/tool never ran, report BLOCKED. These are different states.
- RQ progression is **E → F → G**. Reopening E/F later requires a decision describing the invalidated claim and regression work.
- The user may change scope. Record the instruction and update board/spec before implementing the change.

## 7. Distributed Git workflow

D57 supersedes identity/machine restrictions in the older workflow below. Branches
are default publication routes. A module READY on another fetched agent branch is
usable after exact ref/commit/module-tree and evidence review; do not require an
original operator or duplicate cross-branch push. Immutable earlier messages retain
their original labels; a role successor publishes a new message and names the role
it satisfies. The current coordinator publishes only on agent-3 in this session.

The human changed execution to separate machines and branches on 2026-10-07. Each agent fetches and pushes exact owned paths on `agent-N` at `SaiyamJain20/RIS`. Read the latest `communication/**` across branches, with file-changing commit provenance. Publish immutable outboxes on the sender branch; ACK in the recipient's branch. No peer mailbox edits, blanket staging, destructive resets, stashes, cleaning, rebases or force pushes.

Agent 3 uses pinned, hash-verified READY snapshots for integration and publishes owned/shared artifacts on `agent-3`. The full serialized workflow is in COMMON_AGENT_CONTEXT. Logical freezes bind exact commit manifests rather than stopping unrelated work on another machine. Interface changes still require affected owners' exact ACKs. This assignment does not authorize a push to `main`, issue/email messages, or deployments.
