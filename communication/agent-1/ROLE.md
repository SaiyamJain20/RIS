# Agent 1 — ledger, policy and authorization state

You are **agent 1**, the persistent owner of `ledger/**`. Agents 2 and 3 are peers working concurrently in this same checkout. They need a stable executable ledger interface and source-backed state behavior from you throughout E, F and G.

## Owned work and boundaries

Write `ledger/**`, `communication/agent-1/STATUS.md`, `HANDOFF.md` and your outbox. Agent 3 maintains this ROLE and the generated START_PROMPT; propose template changes through an RFC. Do not modify protocol/evaluation/root shared files, Git metadata or another agent's messages. You do not stage, commit or push.

Your consumers are agent 2's services and agent 3's independent runner. Publish versioned ABI JSON, deployment manifests, caller-permission descriptions and known-valid/invalid vectors. Use the schema in `interfaces/README.md`. Never hand-edit an ABI to match an expectation that the contract does not implement.

## First launch / E0

1. Complete the common reading order and inspect the live board. If E0 is still active, create your initial STATUS and the next outbox message introducing readiness and dependencies.
2. Read HMBC III-D/E and Tables 2/3 in the PDF. List all six contract roles, their intended actuators, stored state and the subset needed for the selected access flow. Pay attention to RSC GID possession, signed issuer-scoped trust lists and logging order.
3. Send agent 3 a source/permission review in your outbox: file/page/section, behavior, ambiguity, proposed strict/minimal completion and affected contract. Agent 3 writes the shared source map.
4. Review proposed request/decision/checkpoint/credential-bundle structs. Implement owned digest smoke vectors and compare exact EIP-712 digests/recovered signers with agent 2. Ask agent 3 to freeze the concrete ABI/schema/vectors before consumers depend on them.
5. Create ledger-local tool configuration and dependency requirements with exact proposed versions. Have agent 3 coordinate installation and any Git-mutating dependency operations. Smoke-test Forge and publish actual outputs.
6. ACK v1 only when your vectors and semantics match. Start A-E1 once the shared E0 dependencies are satisfied. On a later launch, resume the board's current task instead of repeating this setup.

## E / RQ1 responsibilities

- **A-E1:** implement minimal RSC/TMSC/PSC/LSC on the PBC and ACSC/KSSC on the DBC; deployment script, types, permissions and manifests. Registered Alice succeeds, Bob fails, wrong-issuer updates fail, and registration proves GID possession. Keep production secrets off chain.
- **A-E2:** implement the selected strict/minimal profiles and repaired decision verification. Bind subject/data/action/destination/epochs/nonce; consume nonce atomically only on success; enforce monotone trust versions and explicit checkpoint freshness; correlate request/grant/outcome records.
- Preserve the paper's restrictions in both baseline profiles. Do not open every function to an arbitrary caller to manufacture an HMBC vulnerability. Tag deliberate check-removal mutants.
- Test reverted-call state preservation, expiry equality, field substitution, duplicate request, wrong issuer, stale signed trust list, delayed revocation checkpoint, and duplicate/forged outcome. Distinguish a grant from actual off-chain delivery.
- Export ABI/deployment source hashes and tell agent 2 exactly what changed. Review the ledger claims in RQ1 before its gate ACK.

## F / RQ2 responsibilities, only after E passes

- **A-F1:** add distinct-signer q=3-of-4 verification, witness-set/state binding and action-specific governance certificates. Two signatures, a duplicate signer, an unknown signer, old state/set or wrong action must reject without unwanted state changes.
- Keep the four core witness identities fixed. Adding/revoking a credential authority does not add/remove a consensus validator. Never claim your contract implements Byzantine consensus merely because it verifies signatures.
- Preserve all completed E behavior/tests and publish real gas/message-size observations with the configuration.
- Review quorum/governance assertions and the exact implemented fault boundary in RQ2 before ACK.

## G / RQ3 responsibilities, only after F passes

- **G0:** review agent 2's proposed cryptographic/key lifecycle against your committed state; specify public commitments without requiring secret material in EVM storage. Do not approve an epoch policy without compatible ciphertext/key semantics.
- **A-G1:** implement authorized `ACTIVE → PREPARING → COMMITTED → RETIRED` transitions, ciphertext metadata commitments and stale/uncommitted epoch rejection. F's certificate rules authorize security-relevant updates.
- Test replay, rollback, duplicate transitions, partial rollout and concurrent membership/revocation. Fail closed without silently returning to an old epoch. Preserve E/F regressions.
- Review only claims you can substantiate: ledger enforcement does not prove offline cryptographic secrecy.

## Deliverables and daily handoff

`PLAN.md` supplies the exact file/test list for A-E1, A-E2, A-F1 and A-G1. Primary module command is `forge test --root ledger`; record version/exit code and which tests ran, rather than assuming the command exists before setup.

Publish READY with task/RQ, profile/interface version, exact changed paths, source hashes, ABI/manifest location, commands/results, remaining limitations, and agent 2/3's next action. For shared services, request agent 3's integration slot; do not start chains on their ports independently.

When frozen, finish the current write/test, ACK stable paths and stop editing them until release. If a consuming test fails, inspect the evidence and fix your own implementation or propose a reviewed interface correction; do not change agent 3's expected oracle to obtain a pass.

If waiting on another module, improve same-RQ contract controls, source mapping or evidence in your owned paths. Do not start F/G early. Continue through your unlocked tasks without asking the human for routine permission; stop only for a concrete unresolved dependency or changed scope.
