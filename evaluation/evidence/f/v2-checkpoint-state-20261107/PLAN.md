# Checkpoint state and supplied signing-window implementation plan

> Execute inline with executing-plans and TDD. User authorizes continuing accepted
> F work and prohibits extra agents/worktrees. No new approval or interface change.

**Goal:** independently check a checkpoint signature against exact supplied PBC
source/head state and the supplied DBC validation observation.
**Spec:** SPEC.md section 5, PLAN.md C-F1, F_SOURCE_READY.md and frozen R6 sections
3/4. These already require independent source-state and sign-time joins.
**Architecture:** separate internal `evaluation/checkpoint_state_v2.py` exposes
`verify_checkpoint_signature(message, signature, *, owner, manifest, observations,
abi_paths, pbc_head, dbc_observation, blocks, calls, compiled_max_admins=None)`.
Compose the existing bound-signature checker with exact block/getter captures.
**Stack:** existing Python/pytest/eth-abi/public owner ABIs, no dependency changes.

## Scope and choices

Use only repaired-f (including its explicit q2 control), synthetic captures, and
the caller's independently selected context/owner/ABI pins. Verify source <= head,
same-height hash equality, source >= current checkpoint source, exact next sequence,
keyEpoch=0, source authEpoch/policyVersion/witnessSetVersion, semantic freshness at
the supplied PBC head, and DBC time < expiry <= time + public maxCheckpointTtl.
Reads are exact chain/blockHash/contract/calldata tuples; no duplicate/unused
captures, ABI substitution or trailing ABI bytes. Identical required reads may
share a capture. No numeric source lag or invented timing tolerance.

Approaches: extend existing history checker (would change its established scope),
or a separate per-signature checker. Choose separate API, consistent with the
existing internal slices; history/acquisition wiring remains subsequent work.
This does not prove that the supplied heads were latest/contemporaneous with
actual signing, RPC authenticity, ancestor membership across heights, native
state truth, store completeness, liveness, consensus or a gate. It is one stored
signature, not a quorum certificate. Fault/clear/history labels are not consumed
or upgraded here. Existing consumers and frozen wire bytes remain unchanged.

## Review focus

Valid signatures over wrong state; expired/overlong expiry at exact boundaries;
max sequence and absent current; stale source with unchanged versus changed
epochs; wrong-chain/block/callee/calldata/raw bytes; unused/duplicate captures;
caller input mutation and correlated author review limits.

### Task 1: independent raw checkpoint-state checker

- [ ] Write tests in evaluation/tests/test_checkpoint_state_v2.py, retain missing-module RED.
- [ ] Implement only the separate internal API and run focused GREEN.
- [ ] Add narrow in-memory deliberate bypasses and demonstrate sensitivity.
- [ ] Freeze complete relevant inputs/tools; run focused and root regressions.
- [ ] Review exact new peer source/static claims, retain exact provenance and owner limits.
- [ ] Verify stable input brackets/frozen pins, write evidence/shared state and A3 outbox.
- [ ] Publish exact owned checkpoint to agent-3, verify remote/status and release locks.

Acceptance: source/getter/signature/window controls and root regressions pass on
unchanged inputs; honest limits retained. No E parity claim, F case/Gate F remain
NOT_RUN, G locked. Full runtime READY/mapping plus separate complete exact
execution FREEZE ACKs still precede integrated services.
