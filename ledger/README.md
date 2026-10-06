# Module 1: Ledger and policy

Owner: **agent 1**. This folder currently contains a plan only; implementation has not started.

Read [the root plan](../PLAN.md), [specification](../SPEC.md), [interfaces](../interfaces/README.md), and [communication rules](../communication/PROTOCOL.md).

## Scope across E, F and G

Own the six minimal HMBC contract roles, their call permissions and state transitions. In E, preserve the paper's intended actuators and distinguish strict/minimal completions. In F, verify distinct action-bound quorum signatures; membership records are not consensus validators. In G, commit to epoch/ciphertext state while keeping all secret material off chain.

First task: E0. Read HMBC Tables 2/3 and III-D/E; review the source map, freeze ABI/EIP-712 types with agent 3, and independently reproduce agent 2's digest vectors. Then start A-E1. Produce the real ABI/deployment manifest for agent 2 and the integration runner.

Module tests use `forge test --root ledger`. Those files/tools are future implementation deliverables, not present working software. Your tests must include valid access, wrong issuer/caller, reverted-call state preservation, replay/expiry, quorum boundaries and epoch transitions when their phases open.

## Assigned tasks

A-E1, A-E2, A-F1, A-G1. The authoritative task steps and file lists are in `PLAN.md`; do not keep a divergent copy here.

## Module handoff

Publish a READY message in `communication/agent-1/outbox/` with files, interface version, hashes, test command/output and limits. Update your STATUS/HANDOFF. Request cross-module fixes through the owner's mailbox. During an integration freeze, acknowledge and stop editing the frozen paths until agent 3 releases them.

No F implementation before gate E; no G implementation before gate F. If blocked, work on same-RQ tests/evidence or publish the specific blocker. Do not implement JANUS or create a worktree.
