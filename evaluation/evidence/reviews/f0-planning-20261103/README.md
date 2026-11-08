# F0 ledger review and shared draft, 2026-11-03

Agent3 reviewed A1-0088 and A1-0089 from exact owner commits, then assembled
14 component rows in `evaluation/evidence/fault-model.csv` and 27 prospective
scenario reservations in `evaluation/scenarios/f_matrix.json`. The design and
open source/interface plan are in [F0-DRAFT.md](F0-DRAFT.md). All F rows are
NOT_RUN; both owner ACKs remain pending. No F implementation or interface change.

## Fresh snapshot verification

Owner tip: 39893536c1a4d5f3c27b789dcedc935b2ad8b88d.
All 302 git-archived ledger files equal their owner blobs and stayed hash-identical
before/after checks. All 17 production src/script/foundry.toml files match E pin
933d2a7. Owner source manifest
96c9909dc297f236cf0c5623463c2e88d6a149ea8af745deedb27517e5f8a7da
verifies all 301 entries. Snapshot/archive and input hashes are in snapshot.json,
owner-before.json and owner-after.json. Scratch build products stay under .git.

Fresh checks, each with actual argv/cwd/UTC/exit and stdout SHA-256 in its JSON
sidecar, and complete output in the matching `.stdout.txt`:

- `owner-manifest`: `sha256sum -c --quiet ledger/evidence/source-manifest.sha256`, exit0.
- `ledger-suite`: pinned Forge1.8.5 and solc0.8.37, **198 passed, 0 failed, 0 skipped**, exit0.
- `ledger-powers-checker-corrected`: `python3 -I ledger/tools/check_f0_powers.py --solc /home/karma/.local/share/svm/0.8.37/solc-0.8.37`, exit0,
  problems[], 29 state rows/70 variables, 33 entry points, 12 actors, 22 test citations.
- `controls`: owner `ledger/tools/f0_controls.sh` against an empty separate scratch
  copy, pinned Forge on PATH and explicit FOUNDRY_SOLC; **12/12 sensitive**, exit0.
  These deliberately remove injected faults; the expected test failures demonstrate
  sensitivity. They are not twelve F safety experiments.
- `forge-version`, `solc-version`: exit0. tools.json records executable hashes;
  compiler SHA-256 5de843c2c93563cc66425c99a4fb13fdbf32b4c4ae07469480faaf126e14404a
  matches the owner's pin before compilation.

Retained failure: `ledger-powers-checker` exit1 because the owner's default
`~/.svm/...` path is absent on this host. Corrected invocation supplies the pinned
host path without changing owner bytes. Early read-only diagnostics also tried
ledger F0 paths in the integration checkout (not yet imported) and the wrong
SigLib location; subsequent reads used the owner snapshot and `src/lib/SigLib.sol`.
One documentation patch missed a line wrap, made no change and was reapplied.
Initial staged whitespace checking rejected the generated CSV's CRLF endings;
normalized to LF and recomputed the draft manifest/outbox hash before publication.
These are invocation/editing errors, not reconstruction findings.

## Scope and review conclusion

Class: **tested reconstruction result** on existing E code; no HMBC authors'
implementation claim. The new test-only n4/q3 KSSC exercises checkpoint certificates
only. It does not measure n4 decision or receipt integration, independent witness
verification/persistence, two-chain services, consensus or F availability. The
sourceBlockNumber poison test uses E's q1 fixture. Poison signed by a quorum is a
boundary outside honest validation, not a demonstrated f1 witness attack.
Coverage checker checks inventory/citations, not truth of power claims. The
review is correlated same-model author review under the no-extra-agent rule.

281 communication paths across fetched research refs have exact changing-commit
provenance and no incomparable content conflict (communication-provenance.json).
Agent2 remains at the common baseline with A2-0039 as latest original outbox;
its F0 key-control/D50 RFC is absent. No stale STATUS prose overrides D51's F0
planning authorization. No peer module/mailbox was imported or edited.

The proposed minimal scope and broader alternatives stay proposals. Numeric
timing bounds, signing conflict keys, canonical common expiry, full source plan
and deployment identity migration remain unresolved. The new JSON is not a
runtime ABI or integration plan and provides no execution authorization.
Historical E signed bytes/frozen interfaces remain unchanged; F gate NOT_RUN,
G locked. No services started. Only owned planning/review files and shared live
coordination are published on agent-3; main stays at376347d.

`planning-check.json` records fresh syntax/cross-reference/source-bracket and
launch-bundle checks; no full evaluator suite was rerun for documentation/catalog
drafts. Future integrated evidence needs new complete source inventories and
exact affected ACKs, because adding a scenario file changes those inventories.
