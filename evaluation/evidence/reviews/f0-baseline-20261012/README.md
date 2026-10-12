# Shared F0 baseline regression and merge review, 2026-10-12

Human-authorized merging of all three published branches into main, followed by
normal fast-forward convergence of agent-1/2/3. Source merge:
75003bbc4094b53e1fbf74f37f027bb24d8841c7. Input refs in before-refs.json. Branch
normalization is one-time authorization (D51), not continuing peer-module ownership.
The common baseline is the commit that first adds communication/F0_BASELINE.json;
all four remote refs must resolve to that commit after publication. Exact push/
remote/cleanup logs are preserved externally in .git/ris-main-sync-20261012 and
automation memory, avoiding self-referential commit metadata.

## Merge and source provenance

Agent1 6911478 and main5f71184 were already ancestors of Agent3 ce300b0. Agent2
79bfb4a is merged as a second parent. A2-0039/A3-0051 reviewed the successor pin.
Merge preview and actual merge exited1 with exactly three conflicts:
protocol/README.md, evidence/source-manifest.sha256, tools/mutation_check.py.
Resolution preserves exact owner 79bfb4a blobs (A2's published recommendation).
All168 protocol files and all24 added/changed merge paths equal the owner commit.
No authored peer source/mailbox edits, worktrees, reset/rebase/stash/clean or extra
agents. Ledger/interfaces/archive unchanged in the source merge; frozen v1 and
historical gate/report hashes in merge-review.json still match original bytes.
Implementation-inputs.json hashes source/config/test/vector/fixture paths as of
the verified merge commit; baseline active documentation later clarifies F0.

## Fresh verification on the merged tree

- Evaluator full suite: **1658 passed**, exit0,395.34s.
- Protocol full suite: **1383 passed,201 skipped**, exit0,360.14s. Skip reasons are
  exactly100 ScenarioResult +100 ScenarioResult +1 FileHash owned by Agent3;
  no missing-Foundry/missing-pin/live-test skip. Includes new exporter and D49 tests.
- Forge ledger suite: exit0;21 Solidity files compiled with solc0.8.37 in13.18s.
  Quiet Forge output does not supply a test count; no count is inferred.
- Protocol owner manifest:142/142 entries match, exit0; exports9 match, exit0.
- Launch prompts --check before coordination edits: exit0 (later rebuilt and
  checked again after the shared current-phase instruction changed).
- Full source bracket:7088 tracked files identical before/after suites. Tools
  match frozen executable hashes; checked during validation and again afterward.
  Suite fixtures stopped: no Anvil executable processes remain. No integrated
  gate lease or production deployment; services were synthetic owner-test fixtures.
- Communication scan:275 latest paths, no divergent revisions. Exact file-changing
  commits/branches are recorded, not inferred from branch-tip timestamps.
- git diff --cached --check: exit2 ONLY for existing owner captured terminal logs
  with trailing spaces. Exact hashed evidence preserved. The same check excluding
  protocol/evidence/** passes0; owned new documentation is checked separately.

Each command's argv/cwd/UTC/exit/output SHA256 is in its .json sidecar, raw output
in .stdout.txt (renamed from .log to respect publication ignores). run.py is the
recorder. Environment: Python3.13.13/pytest9.0.2, eth-account0.14.0, eth-utils6.0.0,
jsonschema4.26.0, SQLite3.47.2, Foundry1.8.5/solc0.8.37; pins in tool-hashes.json.
Source stability here proves unchanged inputs for these suites, not a new live
integrated gate run or cryptographic/consensus/power-loss guarantees.

## F0 starting status

Qualified historical E PASS stays about its original pinned source/report, with
correlated review, human-scoped mutants/window, UNPROVED paper crash properties,
symbolic crypto and all original limitations. Exporter successor and evaluator
checks are now common baseline source; later integrated execution requires new
exact source/tool/interface plan FREEZE and affected ACKs.

F0 planning is next: component/key-control/attacker matrix and expected boundary
classifications under n4/q3/f1, including safe-ledger/trusted-worker and correlated
host limits. D50 stronger worker binding needs an exact RFC/migration review;
D-4/D-6 are owner backlog. Persistent single-signing, one certificate expiry digest,
TLC pinning and negative controls remain planned deliverables. No F implementation,
F matrix freeze/ACKs, F experiment or F gate result is claimed. G remains locked.

Agents must fetch/fast-forward their local assigned checkouts from origin without
throwing away unpublished work. Remote tracked-file equality does not synchronize
private databases, ignored evidence, credentials, tools or environments. Single
session/same model review; no claim of independent cryptographic confirmation.
