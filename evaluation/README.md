# Module 3: Models, evaluation and integration

Owner: **agent 3**. This folder currently contains a plan only; implementation has not started.

Read [the root plan](../PLAN.md), [specification](../SPEC.md), [interfaces](../interfaces/README.md), and [communication rules](../communication/PROTOCOL.md).

## Scope across E, F and G

Own independent scenarios/oracles, formal models, integration, run manifests and RQ reports. You coordinate shared files; you do not fix another module by editing it. Keep expected behavior independent of observed implementation results.

First task: E0. Produce the source map/assumption register, versioned schemas and positive/mutated vectors; coordinate toolchain smoke tests and dependency locks. Require agents 1/2 to ACK matching digests before v1. Then start C-E1 and integrate the real modules as soon as their legitimate path is ready.

Module tests use `python -m pytest evaluation/tests -q`. Create `python -m evaluation.run` and `python -m evaluation.gate` as specified. You alone control integration processes, root dependencies, the board and gates. Require all three ACKs and stable source hashes before advancing from E to F or F to G.

## Assigned tasks

C-E1, C-E2, C-F1, C-G1; all E0/F0/G0 and gate coordination. The authoritative task steps and file lists are in `PLAN.md`; do not keep a divergent copy here.

## Module handoff

Publish a READY message in `communication/agent-3/outbox/` with files, interface version, hashes, test command/output and limits. Update your STATUS/HANDOFF. Request cross-module fixes through the owner's mailbox. During an integration freeze, acknowledge and stop editing the frozen paths until agent 3 releases them.

No F implementation before gate E; no G implementation before gate F. If blocked, work on same-RQ tests/evidence or publish the specific blocker. Do not implement JANUS or create a worktree.
