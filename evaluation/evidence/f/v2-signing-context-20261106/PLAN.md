# C-F1 anchored signing-context slice

Authority: accepted F0 candidate2, SPEC section 5, PLAN C-F1 and A3-0082's next
owned work. This is an internal evaluator implementation, with no shared
interface, dependency, source READY or execution-authority change.

Use the existing independent D50 reconstruction on caller-pinned manifest and
separately collected observations. Derive certificate domain, set version,
membership and exact quorum from that validated document. Check embedded PBC
chain/PSC fields in checkpoints and DBC chain/KSSC fields in receipts. Apply the
same context to every checkpoint retry report, including failures and late and
inconsistent reports. Do not allow artifact-supplied domains or quorum overrides.

Alternatives: accepting an export's B would trust the object under test; wiring
the existing unbound primitive into the default runner would change a consumer
before owner readiness. A separate evaluator wrapper preserves the old runner
and frozen bytes and gives future oracles one explicit, checked entry point.

This does not verify source-state truth, expiry, historical event membership,
receipt/request correspondence, exporter completeness or storage durability.
Observations remain caller-trusted; synthetic RPC does not attest a real chain.

- [x] Write tests for all four message types, q3/q2/E, valid signatures on wrong
  embedded identities, wrong domains/set/counts, invalid observations and every
  retry-report path. Include a collector-to-signature synthetic positive control.
- [x] Retain expected missing-module failure before implementation.
- [x] Implement evaluation/signing_context_v2.py without peer imports or edits.
- [x] Run focused tests, deliberate check-removal controls, author review and
  full root suite with complete discovered source inventory frozen throughout.
- [ ] Record exact peer provenance, source/output hashes, commands/exits/tools,
  failures/limits; publish only reviewed owned paths on agent-3 and verify remote.

Rulings: user requires no extra agents/worktrees and autonomous continuation;
review is correlated author review. Existing accepted design supplies authority;
no repeated human design approval is requested for this internal slice.
