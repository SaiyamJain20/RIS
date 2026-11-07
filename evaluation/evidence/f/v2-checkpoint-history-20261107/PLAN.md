# Checkpoint history state joins implementation plan

> Execute inline with writing-plans/executing-plans and TDD. The accepted F0
> design and user's continuation authorize this owned slice; no extra agents,
> worktrees, shared-interface change or integrated services.

**Goal:** check every declared checkpoint digest, live and superseded, against
its exact supplied source/head state and its recorded DBC observation.
**Spec:** PLAN.md C-F1, SPEC.md F assumptions, accepted frozen R6 source-state
duties, and the preceding checkpoint-state PLAN.md.
**Architecture:** internal `evaluation/checkpoint_history_v2.py` composes
`verify_signed_history` and `verify_checkpoint_signature`. Existing consumers and
wire schemas remain unchanged. Python/pytest/eth-abi already installed.

Approaches: change the established native-history scope, or add this separate
composition. Use the separate composition, consistent with earlier slices. It
consumes captures selected by digest, never by effect hash: legal A->B->A and
multiple expiry refinements must retain all signatures. Each capture has exactly
digest/pbcHead/blocks/calls; target observation comes from the signed-history row.
Require exact coverage, reject duplicate/extra captures, and reject conflicting
headers or getter bytes at the same cross-capture key. In declared safe intervals
also refuse two hashes at one height. Fault/clear labels and mutation death
exclusions pass through unchanged. No native death check is claimed.

## Review focus

- Missing superseded or second expiry digest must refuse, even when live passes.
- A target observation substituted through capture fields must refuse.
- Identical reused raw facts are allowed; contradictory reused facts refuse.
- Full declared history owner/signature/binding checks still apply to other types.
- Fault/clear and bit1/bit5 labels must never become safe by composition.

## Task 1 — complete declared checkpoint coverage

- [ ] Write `evaluation/tests/test_checkpoint_history_v2.py`, exercise real
  synthetic signatures and raw ABI bytes; retain missing-module RED.
- [ ] Implement `verify_checkpoint_history(evidence, *, manifest, observations,
  expected_owner, abi_paths, captures, compiled_max_admins=None)`.
- [ ] Run GREEN with empty/mixed histories, q2, A->B->A, expiry refinements,
  coverage/owner/observation/state/contradiction controls; retain failed trials.
- [ ] Run narrow deliberate bypasses with valid controls; bracket exact local
  source/tools/helpers and unchanged owner inputs/frozen pins.
- [ ] Run focused and root regressions; fetch/review all communication revisions.
- [ ] Write evidence, current shared state, own HANDOFF/STATUS and A3-0098; publish
  exact owned paths normally on agent-3, verify remote and release both locks.

Acceptance is consistency under supplied captures only. No actual sign-time or
latest-head attestation, RPC authenticity, ancestry, exporter/store completeness,
native deaths, persistence, consensus, E parity or F gate result. No new F cases
run; G remains locked. Correlated author review is explicit.
