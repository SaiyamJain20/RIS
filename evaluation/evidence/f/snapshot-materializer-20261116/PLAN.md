# A3-0163 offline snapshot preparation

Continue Agent 3 / C-F1 from A3-0162, parent 34794ef76314f13ed3dbfced1123c9a2bbda9272.
Authority: live handoff's NEXT CODE and accepted owned F implementation scope.
This is implementation of that existing design, not integrated execution.

- [x] Write synthetic Git fixtures/tests for exact commit/archive/file pins,
  safe regular extraction, collision/traversal/symlink refusal, no overwrite,
  retained historical commit archives independent of the original repository,
  and fail-closed post-copy verification.
- [x] Implement evaluation/f_snapshot.py: hash-pinned plan, new disposable
  workspace plus separate self-contained bare object store, no alternates/network,
  manifest provenance and independent verification. Preserve failed artifacts
  with BLOCKED status; never execute extracted source or owner tests.
- [x] Inventory explicit tool paths and selected runtime trees; detect file,
  symlink/target/mode and directory drift. State closureEstablished=false: explicit
  input inventory does not discover transitive runtime dependencies.
- [x] Run focused tests, inspect complete diff, retain commands/exits/versions,
  source hashes and peer A1-0144 audit; publish reviewed exact owned paths.

Rulings: use the existing checkout, no worktree/delegation (human restrictions).
Use synthetic Git repositories only for materialization tests. Do not materialize
or execute real owner packages in this receipt. Keep report/packet/plan/frozen
interfaces byte-identical; all32 cases/Gate F NOT_RUN/G LOCKED. Self-review only.
No new runtime dependencies or interface changes. Bare stores hold only explicitly
listed commits and their reachable trees; shallow history is intentional because
protocol fixtures need git cat-file/archive, not commit ancestry. Git commands
use a private configuration environment and exact pinned executable. Runtime
inventory is observation/verification, not relocation or a sandbox.

Completed component verification: final92PASS/exit0; same-author self-review.
Runtime closure and coordinator wiring remain next code, not claimed complete.
