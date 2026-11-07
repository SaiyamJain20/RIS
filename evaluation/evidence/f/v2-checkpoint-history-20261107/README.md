# Complete declared checkpoint state coverage

C-F1 WORKING; integrated execution remains LOCKED. This is an isolated extension
result in the paper-derived HMBC2020 reconstruction, using synthetic captures
and real EIP-712 signatures. No existing consumer, frozen interface, dependency,
owner module or runtime mailbox changed.

`evaluation.checkpoint_history_v2.verify_checkpoint_history` checks the full
declared signed history, then joins every live and superseded StateCheckpoint
digest to its own supplied raw source/head state and recorded DBC observation.
Capture selection uses digest, preserving A->B->A and multiple expiry refinements;
missing, extra and duplicate captures refuse. The target observation comes from
the history entry. Contradictory headers/getter bytes at reused keys refuse,
as do conflicting safe-interval hashes at one height. Identical shared facts and
arbitrary capture-list order remain valid. Fault/clear labels and bit1/bit5 death
exclusions retain their original scope. Other signed types still undergo the
composed declared-history signature/context checks, without new state duties.

## Verification

Fresh34 new tests and384 focused tests pass. Eight narrow in-memory bypasses are
detected, each preserving its valid control: missing historical coverage, state
verification, history verification, conflicting block facts, conflicting call
facts, safe-height forks, false safe labels and dropped death exclusions.
Full root regression:2583PASS in554.82s; command555.112s/exit0.

Retained early author trials: initial31FAIL includes30missing-module failures
and one wrong observation-fixture path; corrected31FAIL all name the missing
module. First GREEN has30PASS/1FAIL from a missing required fault-clear note.
Fixing that test fixture and adding bit5/fork/order controls yields34PASS. These
early trials preceded the final input bracket; their original full source trees
were not frozen. Their exact command receipts and lossless logs are retained;
the passing focused/root claims use only the final bracketed tree.

Initial inputs/old mutation helper are retained as inputs-initial.json and
mutants-initial.py.txt. Before executing mutants, review found its state bypass
would trigger the unrelated repeated-call consistency check. The adversarial TTL
was therefore changed consistently in both refinements, preserving the target
invariant. No run of the initial helper is claimed. preflight-final then records
the final helper/source bracket. Production code did not change after its initial implementation.

## Provenance and reproduction

[PLAN.md](PLAN.md) predates tests. Each `*-command.json` records exact argv/cwd,
UTC start/end, elapsed duration, exit and raw output SHA256. Each matching
`.log.gz` losslessly preserves that output. `record.py` uses owned subprocess
groups and a1800-second timeout; direct-child STOPPED receipts are retained under
ignored evaluation/runs/v2-checkpoint-history-20261107/. Normal exit has no group
cleanup action; this is not a claim of a process-kill durability experiment.

Final inputs-before.json records252 selected local inputs and4 helpers. The
899 owner inputs are freshly compared with exact unchanged peer Git objects:
A1 tip8c0285ffa6986858caeb0140b930bf5db759fdc0 and A2 tip
67111f580b6ecfd1b924f3cd1a863981180822e1. The source inventory is inherited from
the preceding inputs manifest, whose digest is recorded; current owner blobs,
52 protocol/f0 pins and frozen publication payloads are freshly checked. No peer
runtime is executed or newly adopted. communication-before.json records390paths
with ancestry/file-changing hashes across fetched branches and no divergence.
The extra path relative to the prior scan is the published A3-0097 message.

Python3.13.13/Git2.54.0/pytest9.0.2/eth-account0.14.0/eth-abi6.0.0/jsonschema4.26.0.
Inherited environment digest is recorded, not a portable environment/performance
claim. ABI fixtures and synthetic signing-key derivations are in bracketed tests.

From the root, reproduce the passing selection with the focused receipt argv,
or run `.venv/bin/python -m pytest -q` for the root suite and
`.venv/bin/python evaluation/evidence/f/v2-checkpoint-history-20261107/mutants.py`.
Audit before/peers writes refuse existing evidence filenames; use a fresh copy
for replay. No source snapshot extraction is needed because owner code is not
executed by this slice. Internal state checks use the pinned public ABI fixtures.

Final verification.json SHA256 `9daf055921f26d5b44c983c8d4b368c7ab6d512674d953a4777f538d4a1f1177` checks14 predecessor receipts; its
own15th receipt was separately checked without rewriting that result. Final
inputs-after.json verifies899owner/252local/4helper inputs unchanged through
execution. The final fetched scan again has390paths/no divergence; peer tips
are unchanged. No new owner READY or ACK. The test source bracket precedes the
subsequent explanatory documentation/handoff edits.

## Limits and continuation

This establishes consistency of supplied observations, not RPC authenticity,
native truth, cross-height ancestry, latest heads, actual sign/validation time,
exporter/store completeness, native deaths, persistence, consensus or any F case.
The stored target observation is exporter data; it is not cryptographically bound
by the checkpoint signature. Owner validation and store observation are separate
reads. A retrospective state mismatch alone would not prove a signing-rule
violation; acquisition/runner provenance and runtime scheduling must be examined.
No new producer defect or paper claim is asserted. Review is correlated author
review under the no-extra-agents rule.

Peer READY/mapping/execution state remains unchanged. A3-0096/97 startup refusal
requests remain open; current partial owner source is not complete runtime READY.
The preceding review's three historical E source mismatches are unchanged, not
new E parity. Separate complete source/tools/config/run execution FREEZE ACKs
still precede integrated services. Historical qualifiedE is unchanged;32Fcases
and GateF NOT_RUN; G locked. Next: raw checkpoint acquisition with explicit
observation provenance, other signed-type state duties, producer schema/path/lock
completeness, then fault oracle/finite model. No human action is required.
