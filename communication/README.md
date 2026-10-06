# Start the three coding agents

Open three agent sessions on the **same local repository** `/home/karma/Documents/RIS-course-project`. Give each exactly one prompt:

1. [Agent 1: ledger and policy](agent-1/START_PROMPT.md)
2. [Agent 2: protocol and key services](agent-2/START_PROMPT.md)
3. [Agent 3: evaluation and integration](agent-3/START_PROMPT.md)

All three start at **E0**, then A-E1/B-E1/C-E1. These sessions have not been launched by the planning task. Do not assign E to agent 1, F to agent 2 and G to agent 3.

Read [PROTOCOL.md](PROTOCOL.md). The coordinator, agent 3, maintains [BOARD.md](BOARD.md), [GATES.md](GATES.md), [DECISIONS.md](DECISIONS.md), and [INTEGRATION.md](INTEGRATION.md). Each agent owns its own `STATUS.md`, `HANDOFF.md`, and immutable `outbox/` messages.

There is no shared writable inbox. A message is published in the sender's outbox with recipients in its header. Recipients read the other agents' outboxes and acknowledge in their own. This keeps one writer per file.
