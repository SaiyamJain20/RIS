# Module 2: Protocol and key services

Owner: **agent 2**. This folder currently contains a plan only; implementation has not started.

Read [the root plan](../PLAN.md), [specification](../SPEC.md), [interfaces](../interfaces/README.md), and [communication rules](../communication/PROTOCOL.md).

## Scope across E, F and G

Own client signing, the relay, independently verifying witness workers, durable release state and the eventual real cryptographic adapter. Every service consumes versioned manifests rather than reaching into agent 1's internals.

First task: E0. Read HMBC Figures 5/6 and III-C6/E2; review GID/key ownership and explicit isolation assumptions. Match the Solidity digest vectors and define the credential-bundle encoding with the other agents. Then start B-E1 with visibly symbolic decryption tokens. Do not begin G's cryptographic feature work before the F gate.

Module tests use `python -m pytest protocol/tests -q`. Test recovery at intent/send/outcome boundaries, independent decision verification, signature/recipient binding and the stated revocation checkpoint. A retry must follow the same grant/cache policy. G0 must reproduce actual source-mapped decryption, not a boolean authorization lookup.

## Assigned tasks

B-E1, B-E2, B-F1, G0 (adapter lead), B-G1. The authoritative task steps and file lists are in `PLAN.md`; do not keep a divergent copy here.

## Module handoff

Publish a READY message in `communication/agent-2/outbox/` with files, interface version, hashes, test command/output and limits. Update your STATUS/HANDOFF. Request cross-module fixes through the owner's mailbox. During an integration freeze, acknowledge and stop editing the frozen paths until agent 3 releases them.

No F implementation before gate E; no G implementation before gate F. If blocked, work on same-RQ tests/evidence or publish the specific blocker. Do not implement JANUS or create a worktree.
