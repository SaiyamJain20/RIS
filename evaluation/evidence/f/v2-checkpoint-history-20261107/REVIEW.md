# Correlated author review

No extra agent was dispatched, as required by AGENTS.md. This is author review,
not independent peer approval. The review compares the new70-line internal
composition and its tests with the accepted source-state/history requirements.

- Coverage is by signed digest, not effect hash. The composed history checker
  first rejects duplicate digests and validates every declared type, binding,
  owner, signature and generation. The new layer requires exact capture coverage
  for every checkpoint digest, including superseded rows and expiry refinements.
- The message passed to the state checker is rebuilt from the same effect/key/
  expiry as the history checker. Target observations come from history entries;
  extra capture fields cannot substitute another target. Captures do not choose
  their owner, membership, domain, ABI pins or threshold.
- Every checkpoint gets the existing source/head/sequence/source-floor/key-epoch/
  TTL/window checks. Shared raw fact keys must agree even across otherwise valid
  per-signature checks. Canonical raw parsing is delegated to the state checker
  before the composition compares number/timestamp or getter bytes.
- Identical repeated facts are legal. The tests retain mixed signed types,
  q2 explicitly pinned controls, A->B->A source effects, expiry refinements,
  capture permutation and zero checkpoint subsets. Zero checked signatures is
  reported as zero; it is not a nonempty checkpoint certificate or state proof.
- A declared fault/clear permits cross-capture alternative hashes without
  promoting the interval to safe. Contradictions at the identical hash/call key
  still refuse. Both bit1 and bit5 excluded deaths survive unchanged. Native
  death facts and other signed types' new state duties are outside this API.
- No producer runtime, public schema, dependency or existing consumer changes.
  The current A2 source remains partial. Its previously reviewed test counts and
  runtime claims were not freshly executed or newly adopted here.

The stored observation is not a signed checkpoint field. The exact reviewed
owner witness service validates state and later supplies a separate observation
to its signing store. This new API checks consistency relative to that supplied
observation; it does not establish which block every earlier validation read used.
Acquisition and runtime scheduling must be examined before interpreting a future
mismatch. No new vulnerability or actual producer failure is inferred.

The accepted source evidence, raw history/death join, store snapshot/export join
and actual runner observation provenance remain distinct obligations. Combining
the supplied checkpoint checks closes one declared-history coverage gap only.
Full source READY/mapping plus exact execution FREEZE ACKs still precede services;
TLC/fault-oracle/integrated F evidence remains outstanding.
