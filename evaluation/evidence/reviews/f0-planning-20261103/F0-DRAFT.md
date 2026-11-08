# F0 shared planning draft — 2026-11-03

Status: **DRAFT / NOT FROZEN / NOT EXECUTABLE**. Agent3 proposal for exact owner
review, not an ACK, implementation authorization or measured F outcome. Gate E
retains its original qualified solo PASS; gate F NOT RUN; G locked. HMBC2020
paper-derived reconstruction, synthetic fixtures, symbolic crypto only.

## Inputs and purpose

PLAN section 6 requires the shared component/key-control matrix and prospective
safety/availability classifications before F implementation. This draft supplies
Agent3's assembly at `evaluation/evidence/fault-model.csv` and
`evaluation/scenarios/f_matrix.json`. Neither file changes interfaces/v1 or the
E runner. The JSON is a planning format, not a versioned runtime Scenario ABI.
Changing a catalog changes future source inventories; old execution ACKs never
cover these new bytes.

Ledger input: A1-0088 at f1deed678c7f52cf7c9d977e46080f107c31dc74 and
A1-0089 at 39893536c1a4d5f3c27b789dcedc935b2ad8b88d, successor manifest
96c9909dc297f236cf0c5623463c2e88d6a149ea8af745deedb27517e5f8a7da.
Protocol owner tip remains common baseline 376347d9b0979d1e46824a30197b935ffe91e4fb;
latest original Agent2 message is A2-0039, contained by that baseline. Agent2's
F0 key inventory, deployment-state binding RFC D50, exact validation/single-signing
rules and agreed expiry construction are still missing. No acceptance inferred.
Exact per-file changing commits across the four research refs are recorded in
communication-provenance.json (281 paths, no incomparable content conflicts).

## Alternatives and proposed bounded scope

1. **Minimal core F (Agent3 recommendation):** C0 new repaired-f profile with
   four witnesses/q3, set version 2; preserve all E profiles. Use existing
   QuorumLib, rather than a second verifier implementation. D-a a1 governance
   add/remove authority and CA-admin changes; D-b b1 fixed witness signers;
   D-c c1 retain global authEpoch and measure availability residual; D-d d1 retain
   current DBC request path under independently validating honest witnesses;
   D-e e1 pin policyVersion, with poisoning beyond the fault/validation assumptions
   classified explicitly. D-f waits for Agent2's exact D50 formula and Agent1's
   export ACK. This answers the existing conditional RQ2 with the smallest migration.
2. **Availability recovery:** add D-e e2 checkpoint reset. It needs a second-chain
   governance deployment and a quorum-authorized rollback rule, with stale-grant
   exclusion and recovery tests. Useful if recovery from a previously faulty
   quorum becomes required; currently beyond the one-fault claim. Defer pending
   an explicit scope decision. A new rollback power is not a harmless helper.
3. **Broader hardening:** D-c c2 per-issuer versions and/or D-d d2 independent
   user-signature validation on the DBC. These alter signed types/ABI and consumer
   paths. They can address different availability or beyond-bound threats, but
   need a separate exact migration decision. Keep as open alternatives.

These are recommendations, not selected or approved choices. No root-key refresh,
witness rotation, log confidentiality, timestamp bound, retry deadline, DKG,
threshold ABE or consensus implementation is silently added. Public EVM logs
stay public. Remove+add is the proposed root replacement operation. C0 mutant
bit assignments and wrapper/file-list deviation remain part of the exact plan.

## Trust and correlation

Application witnesses: n=4, q=3, f<=1; all four logical hospitals have separate
witness keys and durable signing state. Two size-three sets overlap in at least
two identities; at f<=1 at least one is honest. Agreement additionally requires
the same conflict key/domain and durable honest single-signing, plus independently
validated proposals. This arithmetic is a design argument, not a TLC run.

One hospital compromise combines its root, scoped CA-admin, controlled users and
one witness. It does not count as four independently faulty witnesses. A single
authority may issue genuinely accepted credentials to its own users for a policy
accepting that issuer: this is an explicit trust residual, not a forged quorum.
A sole witness-key compromise is a narrower experiment. Separate keys/processes
on one machine do not create independent host-failure domains. Losing the whole
host or worker secrets violates a different assumption and needs its own row.

Both ledgers are assumed safe. Transaction delay/reordering/censorship are
availability schedules; arbitrary ledger rewriting is outside that assumption.
The worker is trusted for release enforcement and durable local audit; compromise
can bypass that boundary even with correct certificates. F's symbolic adapter
cannot measure real cryptographic secrecy. The client, data store and durable-state
database get explicit rows; neither certificate quorum nor a grant proves end-user
delivery. Process restart with intact state differs from adversarial database
rollback or loss of every copy of a durable signing choice.

## Prospective expectations and controls

The matrix reserves FL-1..FL-11 from Agent1 and additional required schedules:
equivocation, signer restart, stale certificates, trust-update reordering,
split/replayed views, f=2 divergent-view and q=2 controls, worker compromise,
arbitrary delay, relay forgery, common-host failure and storage failure.
Every row remains NOT_RUN and needs both affected owners' exact ACKs. Historical
ledger measurements are cited separately; checkpoint-only evidence is never
promoted to a decision/receipt or integrated result.

All executable experiments must include fresh legitimate access and correct
denial controls, whole-state rollback where required, original deadlines, and
public boundary evidence. Capture process/key-state separation, witness validation
decisions, normalized proposals, recovered signer identities, checkpoint/state
joins, attempts and explicit timeouts. A denial-all implementation fails controls.
Under eventual delivery, remaining honest messages must arrive before immutable
expiry or a separately specified fresh request/checkpoint is needed. Eventual
delivery alone does not make an expired request succeed. A fault-free rerun is
the availability control; a bounded timeout is not a proof of infinite failure.

The f=2 conflicting-certificate row additionally allows divergent accepted views
at the two honest signers. Without that condition, two faulty signers alone
cannot create a q3 certificate. It cannot be called a safe-ledger consensus break.
Quorum poison signed by three identities is not evidence that one Byzantine
witness defeated correctly validating honest witnesses.

## Open freeze requirements and source plan

- Agent1: review exact CSV/JSON and proposed alternatives; enumerate final
  ledger files/ABIs/types/events, fixture changes, mutation bits, vectors,
  Governance domain/payload canonicalization/nonce/expiry, and E regression set.
  Reuse QuorumLib is proposed PLAN file-list deviation, not approved here.
- Agent2: provide full witness/authority/relay/worker key/state inventory, including
  cohost correlation. Specify conflict keys and canonical payloads separately for
  decision, checkpoint, receipt and governance; persistence before signature
  emission, restart behavior, deterministic common expiry, stale-view validation,
  signature filtering and continued collection after invalid replies. Specify
  domain separation including chain, verifier and set version for durable state;
  A1-0088's shorthand `(chainId, nonce)` must be checked against multiple verifiers.
  Supply D50 old/new fingerprint inputs/encoding/migration/refusal controls;
  cover both witness sets/thresholds, all six runtimes and immutable handling.
- Agent3: after those inputs, resolve choices in DECISIONS and publish the exact
  revised matrix, source/interface migration and affected-ACK request. Add schema,
  vectors, oracle/model/test design only within that agreed revision. Keep E
  frozen artifacts unchanged. Current live E runner still refuses F.
- Timing: numeric timestamp-skew/inclusion bounds, finite schedule deadlines,
  profile configuration and performance repetition plan remain UNRESOLVED.
  Preserve SPEC's 10 warmups/30 repetitions/seeds0..29 for later measurements;
  no numeric bound is invented in this draft.
- All three ACK the same matrix/expected classifications and source/interface
  revision before F implementation. A later integration needs a new source/tool/
  run FREEZE and both exact owner ACKs. No current services or execution lease.

Missing protocol input blocks a complete F0 freeze, not draft assembly. The next
action belongs to the existing Agent1/2 sessions; no extra agent is authorized.
