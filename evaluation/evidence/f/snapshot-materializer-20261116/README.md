# A3-0163: offline source snapshot and runtime inventory component

Classification: **tested reconstruction result**, synthetic inputs only. This is
preparation code for the paper-derived HMBC2020 reconstruction. It is not an F
case result, a cryptographic measurement, runtime-closure proof or execution ACK.

`evaluation/f_snapshot.py` materializes hash-pinned Git archives into a new
workspace outside the original source repository. It checks exact commit IDs,
archive/file hashes, nonoverlapping selected paths, regular file types and modes.
A separate shallow bare store retains explicitly required historical commits and
their trees without remotes, hooks, alternates or dependency on the original path.
The store's complete file inventory and each retained commit/tree/archive are
rechecked. Source files and Git metadata remain separate from run evidence.
Invalid plans fail before destination writes; acquisition failures preserve a
BLOCKED manifest. Existing destinations are never overwritten. PREPARED always
has executionAuthorized=false and Gate F NOT_RUN.

Runtime helpers inventory explicit selected directory trees, file content/modes,
file symlinks/targets and absolute lexical tool paths. Verification detects added
files/directories and changed content/modes/links. Runtime directory symlinks and
special files are refused. `closureEstablished=false` is intentional: this does
not discover every dependency, relocate an environment or validate installed
package compatibility. Inventory roots must be chosen and reviewed before use.

## Fresh verification

Python 3.13.13, pytest 9.0.2, Git 2.54.0; exact commands/tool metadata in
[audit.json](audit.json), [commands.json](commands.json).

- Initial test-first run: 31 missing-module setup errors, exit 1.
- Initial implementation: 30 passed / 1 failed, exit 1. The corruption test had
  assumed packfiles; it did not modify the loose objects Git actually created.
- Review: 36 passed / 2 failed, exit 1. The corrected corruption test needed to
  make the read-only copied object writable; the other failure proved tool
  symlink spelling was unpinned. Fixed test setup and tool-link inventory.
- First focused run: 87 passed / 1 setup failure, exit 1 (same read-only object).
  Corrected fixture changes permissions, corrupts bytes and restores permissions.
- Focused v2: 88 passed, exit 0. Additional self-review reproduced two failing
  root-symlink probes (exit 1); added root-directory validation.
- Final: `.venv/bin/python -m pytest -q evaluation/tests/test_f_snapshot.py evaluation/tests/test_f_baselines.py evaluation/tests/test_f_preflight.py evaluation/tests/test_manifests.py`:
  **92 passed in 15.35s, exit 0**, including 42 new controls. See
  [focused-final-v3.txt](focused-final-v3.txt). No broad suite was rerun: this adds
  an isolated module and tests without modifying any existing runtime code.
- [probe.py](probe.py) exited 0: synthetic snapshot PREPARED; historical archive
  still verified after the original repository moved; wrong source BLOCKED;
  runtime drift refused. [Sample summary](sample-summary.json). Temporary source,
  object and runtime trees were removed after verification; retained manifests
  describe that completed probe, not presently available executable trees.

Failed logs are losslessly gzipped; [compressed-logs.json](compressed-logs.json)
records raw SHA-256. [source-inputs.sha256](source-inputs.sha256) gives selected
post-verification source identities, not an integrated pre/post source bracket.
[SHA256SUMS](SHA256SUMS) covers this receipt. Self-review is same-author/correlated;
no independent evaluator reviewed this component.

## Peer and proposed real inputs

[A1-0144 audit](a1-0144-audit.json) verifies all six peer attachment hashes at the
exact fetched publication, and records the note's last-changing commit. Agent 1
reports the two ledger command/output expectations match and only ledger/out plus
ledger/cache are created; our existing executor already excludes both directories.
Agent 3 did not rerun those commands. This is not an execution/FREEZE ACK.

[snapshot-plan-draft.json](snapshot-plan-draft.json) carries the prior recipe's
2,824 Git-derived source-file hashes and exact archive provenance. It separately
lists the two historical commits required by the pinned protocol tests, verified
against those exact test blobs (audit.json). It was **not materialized or
executed** against real owner code. Its canonical hash is
`8696c90856bf01775ca230e586e6c6ec87e08fdeac844900134e0cbfb1421f5f`.
The source snapshots include public TEST-ONLY Anvil-key literals; source extraction
and build/cache directories must stay outside future run-evidence key scans.

## Remaining work and limits

The baseline recipe still needs wiring to this prepared source/object manifest,
a reviewed complete runtime inventory and explicit environment/tool pins. The
full coordinator must verify exact executable FREEZE/role ACKs before owner
suites, services or cases. Family/native acquisition, signing-time observations
and complete authenticated capture, classification, post-bracket and integrated
E regression remain unfinished. This component neither parses ACKs nor advances
any gate. Git subprocesses have 60-second direct-command timeouts and capture
archives in memory; this is not a hostile-input resource sandbox or an owned
process-group supervisor. Directory inventory assumes exclusive preparation and
is not atomic against hostile concurrent filesystem changes. Shallow history
supports cat-file/archive for listed commits, not arbitrary ancestor queries.

Reviewed report/packet/plan bytes are unchanged (full identities in audit.json).
Plan DRAFT/authorizesExecution=false; all 32 cases and Gate F NOT_RUN; G LOCKED.
No owner suites, services, integrated cases or deployments ran. No peer module,
runtime mailbox, archive or frozen-interface changes; no extra agents/worktrees,
external messages or main push. Next code: wire source/runtime preparation into
stage-3 recipe validation, establish the selected runtime closure and bind the
historical object store through explicit GIT_DIR; continue independent work even
when peer refs are unchanged.
