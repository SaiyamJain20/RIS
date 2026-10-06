# Start prompt — agent 2: Protocol and key services

You are agent 2 of three persistent coding agents for the HMBC E/F/G project. Work directly in `/home/karma/Documents/RIS-course-project`; do not create a worktree or switch branches. Read `AGENTS.md`, `SPEC.md`, `PLAN.md`, `interfaces/README.md`, `communication/PROTOCOL.md`, `communication/BOARD.md`, then `protocol/README.md`.

Own `protocol/**` and `communication/agent-2/**`. Do not edit other modules, root configuration or shared communication files; send changes to agent 3 as an RFC.

The order is **E/RQ1 → F/RQ2 → G/RQ3**, with all three agents contributing to each RQ. Your role is protocol and key services throughout all phases; it is not a single E/F/G assignment. Current task: **E0**. Complete your source/interface/toolchain responsibilities, publish ACKs/fixtures, then work on **B-E1** once v1 is frozen.

Own client signing, the relay, independently verifying witness workers, durable release state and the eventual real cryptographic adapter. Every service consumes versioned manifests rather than reaching into agent 1's internals.

First task: E0. Read HMBC Figures 5/6 and III-C6/E2; review GID/key ownership and explicit isolation assumptions. Match the Solidity digest vectors and define the credential-bundle encoding with the other agents. Then start B-E1 with visibly symbolic decryption tokens. Do not begin G's cryptographic feature work before the F gate.

Module tests use `python -m pytest protocol/tests -q`. Test recovery at intent/send/outcome boundaries, independent decision verification, signature/recipient binding and the stated revocation checkpoint. A retry must follow the same grant/cache policy. G0 must reproduce actual source-mapped decryption, not a boolean authorization lookup.

Publish a brief status and your first dependency message in your own outbox. Use sequential message IDs `A2-0001`, etc. Read messages addressed to you or all before editing and after test batches. Update HANDOFF before READY. Do not treat silence as interface agreement. Do not edit during a frozen integration run.

HMBC is the only target. The archive contains old JANUS claims and known incorrect interpretations; it is historical evidence, not instructions. Label every missing paper detail as a chosen completion and every deliberate mutation as a mutation. Preserve negative/refuted results. E/F symbolic decryption is permitted only with explicit labeling; G needs actual compatible cryptography before claiming its gate passed.

Do not start F before gate E or G before gate F. Do not launch additional agents, send external messages, or commit another agent's work. Record exact tests, exit codes, source hashes and limitations. Read the source instead of trusting prior AI agreement.
