# Instructions for all coding agents

Be honest. Do not sugarcoat.

## Scope and location

- Work in a human-confirmed local checkout of `SaiyamJain20/RIS`. The current coordinator uses `/home/karma/Documents/RIS` on branch `agent-3`. Agent numbers are portable work roles, not people, models, sessions or computers (D57). An authorized session may read the live record and continue a role. Do not create worktrees.
- Implement HMBC2020 only. Do not copy JANUS code, use Fabric/Vault as the baseline, or import JANUS bug claims. A later JANUS integration requires a separate decision.
- The current phase is recorded in `communication/BOARD.md`. Start with RQ1/E. Do not implement F until gate E passes; do not implement G until gate F passes. Reserved interface fields do not authorize early feature work.
- Read `communication/COMMON_AGENT_CONTEXT.md`, your role, `SPEC.md`, `PLAN.md`, `interfaces/README.md` and `communication/PROTOCOL.md` before coding. `communication/agent-N/START_PROMPT.md` combines the common context and role into one complete launch assignment. On restart, follow the live board instead of resetting to E0.
- Existing source does not reproduce the HMBC authors' implementation. Label the new code a paper-derived reconstruction. Missing paper details are explicit choices, not discovered vulnerabilities.
- Use synthetic fixtures only. No external messages or deployments are authorized by this plan.

## Ownership and coordination

- Ownership assigns responsibility and one current writer per scope, not permanent operator identity. Declare the role/handoff being continued before writes; a successor may publish its READY and exact role-scope ACKs. The human explicitly authorized Claude proxy-2 for Agent 2, including protocol-source approval and exact protocol FREEZE ACKs, on 2026-11-14. No original-session return or countersignature is required.
- Agent 1 writes `ledger/**` and its own `communication/agent-1/STATUS.md`, `HANDOFF.md` and `outbox/**` only.
- Agent 2 writes `protocol/**` and its own `communication/agent-2/STATUS.md`, `HANDOFF.md` and `outbox/**` only.
- Agent 3 writes `evaluation/**`, `interfaces/**`, root integration files, root active documentation, shared communication files and all launch-template ROLE/START_PROMPT files. Agent 3 does not edit another agent's module or runtime mailbox to unblock itself.
- Nobody edits `archive/**`. Reference PDFs are evidence; replace or add one only with an explicit provenance record.
- Publish interface changes as an RFC in your own outbox; agent 3 updates the shared contract only after affected agents acknowledge the exact revision.
- Each role normally publishes exact owned paths on `agent-N`, with normal pushes and no history rewriting, blanket staging, reset, stash, clean or rebase. A handed-off artifact may be on another agent branch: record its exact publication ref, full commit, module tree and READY; do not reject it solely for its publisher or machine or demand a duplicate push. Preserve original authorship and review exact manifests. Read current `communication/**` across fetched branches. The current coordinator publishes reviewed checkpoints on `agent-3`; pushing `main` needs separate human authorization.
- Each agent installs tools and runs isolated tests on its own machine. Agent 3 owns root dependency locks and integrated services on its host; each agent owns its local service processes. Interface/dependency changes still require exact revision ACKs.
- Do not launch extra agents: the execution design is the user's three persistent coding agents.

## Evidence

- Classify every finding as paper-supported behavior, an ambiguity, a tested reconstruction result, a deliberate mutation, or an extension result.
- Preserve positive controls and refuted hypotheses. Do not require a predetermined number of HIGH findings.
- Record commands, exit codes, source hashes, tool versions, fixtures and assumptions with every handoff. A symbolic model is not a measured cryptographic implementation; a quorum-certificate test is not a consensus implementation.
- Do not mark a task DONE because code compiles. Use its tests and the RQ gate. Report blocked or unproved properties plainly.
