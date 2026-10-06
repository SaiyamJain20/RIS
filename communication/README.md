# Start the three coding agents

Open three agent sessions on the **same local repository** `/home/karma/Documents/RIS-course-project`. Each link below is a **complete prompt containing the common context and that agent's role**. Paste the entire corresponding file into the agent's chat. No previous conversation or second pasted prompt is needed.

1. [Agent 1: ledger and policy](agent-1/START_PROMPT.md)
2. [Agent 2: protocol and key services](agent-2/START_PROMPT.md)
3. [Agent 3: evaluation and integration](agent-3/START_PROMPT.md)

If the agent already has filesystem access, an equivalent one-message launch is: “Read `/home/karma/Documents/RIS-course-project/communication/agent-1/START_PROMPT.md` and execute it as your complete assignment.” Use `agent-2` or `agent-3` for the other sessions. Giving the prompt as the assignment includes its scoped implementation/verification authorization and agent 3's reviewed Git checkpoint workflow. Agents 1/2 never stage, commit or push.

Initially all three start at **E0**, then A-E1/B-E1/C-E1. Later launches resume the live board rather than resetting the project. These sessions have not been launched by the prompt-writing task. Do not assign E to agent 1, F to agent 2 and G to agent 3.

Read [PROTOCOL.md](PROTOCOL.md). The coordinator, agent 3, maintains [BOARD.md](BOARD.md), [GATES.md](GATES.md), [DECISIONS.md](DECISIONS.md), and [INTEGRATION.md](INTEGRATION.md). Each agent owns its own `STATUS.md`, `HANDOFF.md`, and immutable `outbox/` messages.

There is no shared writable inbox. A message is published in the sender's outbox with recipients in its header. Recipients read the other agents' outboxes and acknowledge in their own. This keeps one writer per file.

## Maintaining the prompts

The canonical common file is [COMMON_AGENT_CONTEXT.md](COMMON_AGENT_CONTEXT.md). Role-specific source files are [agent 1](agent-1/ROLE.md), [agent 2](agent-2/ROLE.md) and [agent 3](agent-3/ROLE.md). Agent 3 maintains these templates; runtime STATUS/HANDOFF/outboxes stay owned by their respective agents.

Rebuild the three combined prompts after an agreed instruction change:

```bash
python communication/build_prompts.py
python communication/build_prompts.py --check
```

Generated prompts contain hashes of their two sources. Do not hand-edit them or maintain three divergent copies of shared rules. The builder generates documentation only; it does not launch agents, install tools, run project tests or contact GitHub.
