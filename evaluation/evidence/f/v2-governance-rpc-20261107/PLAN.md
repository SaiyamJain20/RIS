# Governance RPC acquisition implementation plan

Goal: continue C-F1 under SPEC.md, PLAN.md, accepted F0 candidate2 and A3-0101.
Architecture: internal governance_rpc_v2.collect composes exact hash-selected PBC
getter acquisition with governance_history_v2; both selected RPC endpoint identities
are bracketed before/after capture. Observations come only from each declared
signed digest and remain unsigned exporter claims. Caller approvals are a separate
TEST-ONLY fixture, pinned with a hash and explicit caller reason. Every live/old/
refinement digest is covered; deduplicated facts must agree. No existing consumer,
wire, dependency or assumption change. Frozen interfaces unchanged.

Alternative: switch a public consumer or expand frozen schemas; that requires a
separate exact RFC/ACK, so use the accepted internal evaluator pattern instead.

Owned files: evaluation/governance_rpc_v2.py, evaluation/tests/test_governance_rpc_v2.py,
this evidence directory, evaluation/README.md, shared live records and own mailbox.
No extra agents, peer edits, worktrees, services, deployments or main push.
Review is correlated author review, as the user forbids extra agents.

Review focus: losing old/refined digests; observation override/fork collapse;
missing getter/approval checking; endpoint/header/input drift; lost partial
failures or budget enforcement. Every class gets a synthetic negative and valid
control. No actual signing time/latest head, producer approval policy, RPC truth,
ancestry, native deaths/store completeness, consensus, E parity or F gate follows.

- [ ] Write tests with real signature/ABI validation and synthetic transports;
  record missing-module RED against exact test hashes before implementation.
- [ ] Implement collect(evidence, *, manifest, observations, expected_owner,
  abi_paths, approvals, approval_reason, rpcs, output, compiled_max_admins=None,
  timeout=10.0, max_calls=1024). No numeric/latest fallback or retries.
- [ ] Record GREEN; add narrow in-memory bypass controls with valid controls.
- [ ] Bracket final runtime/helpers/all carried tracked input blobs and exact owner
  source pins; run focused composition tests and full root pytest; verify receipts.
- [ ] Fetch/review all communication with file-changing provenance; document
  results/limits, publish one immutable own READY, stage exact reviewed paths,
  normal agent-3 push, independently verify remote SHA, release original locks.

Ruling: execute inline under the user's autonomous continuation authorization;
skill planning approval/reviewer/worktree defaults cannot override that instruction.
Persistent scheduled/coordinator locks acquired on original inodes before reads/Git writes.
