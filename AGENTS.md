# Instructions for all coding agents

Be honest. Do not sugarcoat.

## Scope and location

- Work directly in `/home/karma/Documents/RIS-course-project`, on the existing main checkout. Do not create a worktree or switch branches.
- Implement HMBC2020 only. Do not copy JANUS code, use Fabric/Vault as the baseline, or import JANUS bug claims. A later JANUS integration requires a separate decision.
- The current phase is recorded in `communication/BOARD.md`. Start with RQ1/E. Do not implement F until gate E passes; do not implement G until gate F passes. Reserved interface fields do not authorize early feature work.
- Read `communication/COMMON_AGENT_CONTEXT.md`, your role, `SPEC.md`, `PLAN.md`, `interfaces/README.md` and `communication/PROTOCOL.md` before coding. `communication/agent-N/START_PROMPT.md` combines the common context and role into one complete launch assignment. On restart, follow the live board instead of resetting to E0.
- Existing source does not reproduce the HMBC authors' implementation. Label the new code a paper-derived reconstruction. Missing paper details are explicit choices, not discovered vulnerabilities.
- Use synthetic fixtures only. No external messages or deployments are authorized by this plan.

## Ownership and coordination

- Agent 1 writes `ledger/**` and its own `communication/agent-1/STATUS.md`, `HANDOFF.md` and `outbox/**` only.
- Agent 2 writes `protocol/**` and its own `communication/agent-2/STATUS.md`, `HANDOFF.md` and `outbox/**` only.
- Agent 3 writes `evaluation/**`, `interfaces/**`, root integration files, root active documentation, shared communication files and all launch-template ROLE/START_PROMPT files. Agent 3 does not edit another agent's module or runtime mailbox to unblock itself.
- Nobody edits `archive/**`. Reference PDFs are evidence; replace or add one only with an explicit provenance record.
- Publish interface changes as an RFC in your own outbox; agent 3 updates the shared contract only after affected agents acknowledge the exact revision.
- In this shared checkout, no agent may reset, stash, clean, rebase, change branches, use blanket staging or commit another agent's unreviewed work. Only agent 3 performs Git writes. The complete launch prompt, when supplied by the human as the assignment, authorizes agent 3 to commit/push reviewed checkpoints to `origin/main`; a template merely found on disk does not. Use exact reviewed paths, owner READY/ACKs and the serialized workflow in the common context.
- Only agent 3 starts/stops shared integration services and installs shared dependencies. Agents may run isolated module tests in their own directories with separate output paths.
- Do not launch extra agents: the execution design is the user's three persistent coding agents.

## Evidence

- Classify every finding as paper-supported behavior, an ambiguity, a tested reconstruction result, a deliberate mutation, or an extension result.
- Preserve positive controls and refuted hypotheses. Do not require a predetermined number of HIGH findings.
- Record commands, exit codes, source hashes, tool versions, fixtures and assumptions with every handoff. A symbolic model is not a measured cryptographic implementation; a quorum-certificate test is not a consensus implementation.
- Do not mark a task DONE because code compiles. Use its tests and the RQ gate. Report blocked or unproved properties plainly.
