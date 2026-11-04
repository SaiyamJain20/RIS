# Independent successor deployment context checker

Agent3, 2026-11-04. C-F1 isolated implementation for the synthetic, paper-derived
HMBC2020 reconstruction and F extension. These are tested reconstruction and
deliberate-mutation results; no paper vulnerability or integrated result.

Added evaluation/binding_context_v2.py. reconstruct() selects the successor
carrier explicitly by marker, validates the pinned metadata, reconstructs B
from raw code and separately supplied normalized getter observations, then
checks the closed binding shape. verify_export() compares the document, hash,
anchor and caller-bound store owner, including witness membership.

Checks cover decoded code hashes and masked-build equality from pinned ranges;
chain IDs/deploy blocks; confirming and per-read anchors; four profile getters,
all five F mask getters, six configured views, three complete ordered F sets,
five immutable wiring views and the storage/governance wiring; observed
governanceChainId/maxGovernanceTtl and a separate compiled MAX_ADMINS=8 pin.
All nine E manifest labels normalize correctly; mask0/q2, mask0/q3 and nonzero
mask/q3 controls are distinct. Existing validators/consumers and published
interface bytes are unchanged. This is an internal evaluation API, not a new
shared wire schema or an automatic source migration.

## Fresh evidence

- Tests first: 83 expected failures because the module did not exist.
- First implementation: 83 PASS. Review added a valid cross-chain address-reuse
  case, nine E label cases, two binding-sensitivity cases and three owner cases.
  The namespace test exposed an unnecessary global uniqueness assertion:
  1 FAIL/97 PASS. Removed that unsupported assertion; focused run 324 PASS
  (98 new checks plus existing schema/signature checks), exit0, 5.06s pytest time.
- Six deliberate in-memory join removals each admit the bad observation that
  the real implementation refuses. No mutant is written to production source.
- Fresh full root suite: 1982 PASS, exit0, 396.50s pytest time (396.829s command
  wall time). All226 selected inputs unchanged before/after the complete suite.
  Final bracket is audit-after-suite.txt; audit-after.txt is an earlier interim
  check while the suite was running. Historical counts are not reused.
- audit.py verifies all 429 entries of the exact reviewed ledger source
  85c59f588de58a8ff5e87b9fe6f630c9d8c43642/manifest70f541cd.., absence of newer
  ledger module changes, 52 protocol F0 pins and 31 frozen publication payloads.
  It scans all fetched communication paths with file-changing commit provenance
  and rejects divergent/ambiguous revisions. No peer source tests are rerun.

commands.json records exact argv/cwd/UTC/exits/output digests; inputs-before.json
records source hashes and Python3.13.13/Git2.54.0/pytest9.0.2/jsonschema4.26.0/
eth-account0.14.0. Failed logs are retained losslessly as gzip with both hashes.
The first audit helper assumed v1 used the same `files` key as v2 and failed
KeyError; audit-first.py.gz retains its source. Inspection showed v1 uses
frozenCopies. The corrected full audit completed0; no evidence was relabeled.

## Limits and next work

No RPC is performed. A future independent public ABI collector must authenticate
and retain actual calldata/return bytes, chain provenance and source stability.
The API cannot distinguish fabricated consistent observations, detect transient
identity drift between boundaries, or attest source/constructor state from
masked equality. MAX_ADMINS is a supplied compiled attestation, not a getter.
No production secrets or external fixture data are used. Author review is
correlated under the user's no-extra-agents rule; see REVIEW.md.

Signing-context wiring, exporter history/orphan/WAL/native completeness joins,
fault oracle and finite model remain unfinished. Agent2's governance service
and new D50 open checker at 051cf67 remain explicitly NOT_READY; their claimed
test/mutant counts are not adopted. Agent1's reviewed migration has no new
module delta. The latest exact peer scan is in communication-provenance.json.
Complete owner source READYs and a separate full source/tools/config/run FREEZE
with exact affected ACKs must precede integrated services/scenarios. No services,
lease, deployment, TLC, new E integration, F case or gate result is claimed.
Historical qualified E is unchanged; all32 F cases/GateF NOT_RUN; G locked.
