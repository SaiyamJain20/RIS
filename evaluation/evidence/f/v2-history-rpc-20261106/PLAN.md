# Native history RPC capture implementation plan

> Execute inline with executing-plans. User requires three persistent agents;
> no extra agents or worktrees. This implements the existing accepted F0 plan.

**Goal:** acquire raw block and death-getter captures for the native history checker.
**Spec:** SPEC.md section 5; communication/F_SOURCE_READY.md; accepted F0 freeze.
**Architecture:** a separate internal collector plans reads from verified declared
history, acquires hash-selected headers and EIP-1898 calls, checks both deployment
identities before and after all reads, then composes verify_native_history.
**Stack:** existing Python/pytest/owner ABIs; no dependencies or schema changes.

## Constraints and choices
Synthetic transports only this run; no owner runtime/services/live RPC. Caller pins
manifest, observations, owner and ABI paths. Exact RPC params/results retained on
failure. EIP-1898 hash selectors requireCanonical=true for declared safe intervals,
false for explicitly faulted/cleared intervals. No numeric fallback if unsupported.
https://eips.ethereum.org/EIPS/eip-1898 specifies these semantics. This is an internal
acquisition choice, not a new shared interface or claim about pinned-node support.
Default timeout10s/maxCalls1024 are API budgets, never experimental timing bounds.
Partial failed output never publishes result.json. Both identity checks encompass
all cross-chain acquisition. This cannot authenticate RPC or prove source-state,
sign-time, store completeness, timing, consensus or persistence.

## Review focus
Wrong endpoint/genesis/deploy/anchor; same-height forks; missing/trailing ABI bytes;
input/ABI mutation during acquisition; failure/deadline/call-budget raw receipts.

### Task 1: capture and verify native history
Files: evaluation/history_rpc_v2.py; evaluation/tests/test_history_rpc_v2.py.
Consumes verify_signed_history and verify_native_history; produces
collect(evidence, *, manifest, observations, expected_owner, abi_paths, rpcs,
output, compiled_max_admins=None, timeout=10.0, max_calls=1024).
- [x] Write synthetic RPC behavior tests for all deaths, empty profiles, fork labels,
  exact request selectors, two-boundary identity checks, failure logs and drift.
- [x] Run missing-module RED and retain it.
- [x] Implement collector with prevalidated pins and finite budgets, raw transcripts,
  complete required reads, and unchanged-input/ABI guards before publication.
- [x] Run focused GREEN; deliberately remove narrow checks and prove tests detect.
- [x] Freeze all inputs; fresh complete root pytest; verify stable hashes/frozen bytes.
- [x] Review exact owned diff; retain honest author review (no-extra-agent rule).
- [ ] Fetch latest peers, record exact provenance, publish owned checkpoint normally
  to agent-3, verify remote, save memory and release both locks.

Acceptance: all scoped positive/refusal controls and root suite pass on stable inputs;
no gate promotion or peer consumer switch. No change to qualified historical E;
32Fcases/GateF remain NOT_RUN; G locked. Full READYs and separate exact execution
FREEZE ACKs precede integrated services.

Execution ledger: single inline task;59scoped/2498rootPASS; seven bypass controls;
all source brackets stable. Author review under user no-extra-agent instruction;
publication/remote/lock completion receipt belongs to automation memory.
