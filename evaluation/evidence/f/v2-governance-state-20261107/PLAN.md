# Governance supplied-state check implementation plan

Execute inline under accepted C-F1, using executing-plans and TDD. The human
authorizes continuation and forbids extra agents/worktrees/peer edits. Existing
F0 semantics settle the design; no interface, dependency or scope change.

Goal: check a single GovernanceAction signature against exact supplied PBC
state/window and the caller-pinned TEST-ONLY approval list. This is a
paper-derived HMBC2020 extension, not a reconstruction of paper consent policy.
Spec: SPEC section 5; accepted protocol/f0/SIGNING-RULES sections 3/4;
interfaces/v2/BOUNDARY and frozen owner Governance/TMSC ABIs.

Considered extending checkpoint_state_v2 versus a separate governance checker.
Choose a separate internal API to preserve the checkpoint consumer and limits.
Create evaluation/governance_state_v2.py and its independent synthetic tests.
verify_governance_signature(message, signature, *, owner, manifest, observations,
abi_paths, pbc_observation, blocks, calls, approvals, compiled_max_admins=None).
Reuse bound-signature/context/schema and canonical public ABI decoding. Capture
keys are exact chain/hash/callee/calldata; require every supplied capture used.
Read governanceNonce, witnessSetVersion, maxGovernanceTtl and TMSC.isAuthority at
the supplied observation. Read removedAuthority for ADD only. Nonce must be
current+1; ADD requires neither existing nor tombstoned; REMOVE/SET requires
existing; expiry is observation.timestamp < expiry <= timestamp+public maxTTL.
Approval entries are closed canonical {action,root,admins}, matched exactly.
Malformed irrelevant approval entries refuse, duplicates do not amplify consent.
One caller-selected owner approval fixture never represents a quorum or proves
the witness used it. No latest head/actual sign time/native authenticity inferred.

Review focus: ADD/REMOVE/SET controls, tombstones, empty SET, sorted admins and
MAX_ADMINS, maximum nonce, exact expiry bounds and nondefault public TTL,
signature/context substitution, wrong-chain/hash/getter/ABI bytes, duplicate or
unused captures and caller mutation. No existing consumer/wire is changed.

- [ ] Retain test-first missing-module RED; implement minimal independent checker.
- [ ] Run focused GREEN; review and narrow bypass controls with valid positives.
- [ ] Bracket full carried Git inputs plus new runtime inputs/tools/owner hashes;
  run focused and root pytest. Record commands, exits, raw output and hashes.
- [ ] Fetch/review exact communication provenance; retain unchanged peer claims
  without adopting owner runtime tests or fabricating READY/ACKs.
- [ ] Review/deliver exact owned checkpoint, independently verify remote/status,
  update memory and release original lock inodes.

History coverage/acquisition, AccessDecision/GrantReceipt state duties, producer
schema/path/lock completeness and finite model/oracle remain subsequent work.
Integrated execution still needs full runtime READY/mapping and separate exact
execution FREEZE ACKs. No E parity, F case/gate, consensus, persistence or G result.
Review is correlated author review under the no-extra-agent rule.
