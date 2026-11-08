# Governance history implementation plan

Goal: complete the next Agent 3 C-F1 declared governance state slice under SPEC.md,
PLAN.md, the accepted F0 candidate2 boundary and A3-0100. No new assumption or
shared contract. Existing author-approved ownership/execution method applies.

Architecture: compose verify_signed_history with verify_governance_signature for
every declared live/superseded digest. Captures are closed {digest,blocks,calls};
PBC observation comes only from that digest. The caller supplies a separate list
of TEST-ONLY approvals; it is not extracted from or authenticated by the export.
Check repeated headers/getters for consistent facts and, only in declared safe
intervals, one hash per height. Preserve fault/clear labels and bit1/bit5 death
exclusions. No actual sign-time, latest-head, RPC truth, native death/completeness,
producer policy, quorum, consensus, E parity or gate follows.

Alternative considered: switching consumers or extending frozen schemas requires
separate exact RFC/ACKs. This internal composition implements the accepted plan.
No agents, worktrees, peer edits, services, new dependencies or main push.

Files: evaluation/governance_history_v2.py; its test file; this evidence directory;
evaluation/README.md; shared live state and Agent 3 STATUS/HANDOFF/outbox only.

Review focus: omitted old/refinement captures; contradictory shared facts;
unsigned observation override; invented/omitted approval; unsafe interval labels.

- [ ] Write synthetic tests: all actions, q2, recurrence A-B-A, refinements, empty
  subset, malformed coverage, every state join, caller approvals, context,
  conflicting facts, fault/clear and bit1/bit5 scope; retain valid controls.
- [ ] Record missing-module RED with exact test hashes before implementation.
- [ ] Implement minimal composition; bracket source/helpers/all carried inputs
  and unchanged exact owner sources before and after recorded checks.
- [ ] Run GREEN, focused composition suite, narrow in-memory mutants with valid
  controls, full root pytest. Verify command receipts/log hashes and frozen pins.
- [ ] Correlated author review (extra reviewers prohibited); fetch/review peers,
  write handoff and one immutable READY; stage exact paths, normal agent-3 push,
  independently verify remote SHA and release both original lock descriptors.

Ruling: the persistent scheduled lock was successfully acquired before reads;
the first non-TTY holder immediately saw EOF and released, then a TTY holder
reacquired before context work. No inode replacement or unlocked work occurred.
