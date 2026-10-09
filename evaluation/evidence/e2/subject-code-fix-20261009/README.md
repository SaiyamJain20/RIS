# C-E2 subject oracle error-code correction

Agent 1's exact A1-0058 review identified a real evaluator defect. Frozen v1
maps WRONG_SUBJECT to decimal string `2`; `3` is WRONG_DESTINATION. The previous
oracle and its synthetic fixture both used `3`, so their passing tests hid the
same mistake. A correct native subject refusal would have failed that oracle.
No subject service experiment had been run, so no live subject result is revoked.

The oracle now accepts only `2` for the repaired-e gid-only substitution and
rejects `3`. The fixture uses the independently specified frozen value `2`;
the existing wrong-code sensitivity case now supplies WRONG_DESTINATION `3`.
Original certificates/signatures, whole rollback, paper grant checks and
`releaseTested=false` remain intact. This is a tested evaluator correction in
our paper-derived reconstruction, not a paper vulnerability or new gate result.

## Verification

- Test-first reproduction: `.venv/bin/python -m pytest
  evaluation/tests/test_subject_substitution.py -q` exits 1: 2 failed, 69 passed.
  The old oracle rejected correct code 2 and accepted wrong code 3.
- After the oracle correction, the same command exits 0: 71 passed in 0.32s.
- Fresh `.venv/bin/python -m pytest -q` exits 0: 670 passed in 108.89s;
  106 recorded source/schema/fixture/paper/lock inputs match before and after.
- Post-suite author audit exits 0: 303 selected owner blobs, 15 frozen copies
  and FREEZE.json f700292ec7e3b2c8f2b59c7a728a991cd7d6dea2e4a06cea71f6f6c97b9962a2
  verify. No owner pins, native ABI, tool/dependency, custody or frozen bytes changed.
- Python 3.13.13; eth-account 0.14.0; jsonschema 4.26.0; pytest 9.0.2;
  Git 2.54.0. No tool installations. Commands, UTC timestamps, exits and output
  hashes are in red.json, green.json, suite.json and final-*.json; raw outputs
  are retained. audit.json is the intermediate static check during the suite;
  audit-final.json is the post-suite check. Neither file was overwritten.

## Exact peer/source provenance

A1-0058 at e66eeb91caed0119c2c566f60621061699fc5063, message SHA-256
1e3644dd59c7a579de3cc50f67dc4b5f0839025c4cc241ea70a4dd0d185ec48d.
Its copied review, immutable pinned ProtocolTypes.sol and DecisionVerifier.sol,
and frozen schema copy are evidence only. authority.json records original paths,
commits and hashes. Both schema constants and pinned DecisionVerifier step 4
confirm the review; source/action/destination checks precede the changed digest.
The ledger and peer runtime mailbox were not edited. Peer's rehearsal remains
owner evidence and was not rerun or used as integrated evidence.

Communication scans resolve 172 paths from origin/agent-1, origin/agent-2 and
origin/agent-3 by latest file-changing commits and ancestor relationships.
No incomparable different-content revisions; owner runtime files use owner
branches. Agent 2 remains at 96ebe16097a551c1f59f4554869e8b735787c738;
Agent 3 baseline dd0ec37736297a805d806e1daf3a0ef955d26cd2.
Agent 1 delta from previous 73e67141 contains only its STATUS and new review.
No review is interpreted as an execution-plan or report ACK.

## Current limits and next work

E/RQ1 C-E2 is WORKING, E0 closed and historical C-E1 complete. Gate E remains
NOT_RUN; F/G locked; 44 catalog comparisons remain and four paper crash
classifications stay BLOCKED/unproved. No new integration, real subject collector,
recipient routing, release/completion, mutant, revocation-window or RQ report.
No services or execution FREEZE/lease started. Prior raw evidence/manifests and
historical prose are preserved, including the mistaken `(3)` statement in the
subject-oracle preparation README; this correction supersedes that statement.

Next implement the public subject collector with separate fresh legitimate and
stress deployments, authenticated original request/certificate and native
transaction/history anchors. Then check registered-Bob routing and symbolic
completion under the original expiry, retaining Alice/Bob/wrong-admin controls.
A complete revised source/tool/config/fixture plan, explicit FREEZE and BOTH NEW
exact peer plan ACKs precede services. Old plans/ACKs cannot cover changed evaluator
source. No human action or peer source repair is required for that independent work.
No actual ABE, delivery, consensus, authors' executable or power-loss claim.

## Review and execution ledger

Plan/spec task: repair the independent C-E2 oracle before collector/plan publication.
Root cause: evaluator literal and mirrored test fixture confused two frozen errors.
Test contract: correct WRONG_SUBJECT accepted; WRONG_DESTINATION refused; all other
subject joins/controls still checked. RED and GREEN prove both acceptance and
sensitivity; full suite and immutable authority review complete this correction.
Author final review: no unresolved material finding in this four-line correction.
Agent 1 independently located the defect; Agent 3 performed the fix review.
Ruling: work in the confirmed agent-3 checkout and use author final review because
the human prohibits worktrees and extra agents. Cost: final review lacks another
independent reviewer. Prior scope/gate/ACK rules remain binding.
Ruling: publish the already authorized owned checkpoint on agent-3. Cost: peer
review follows publication; no main push or integration is implied.
No deferred minor finding was identified in the correction.

Scheduled guard acquired with exclusive mkdir, no stale recovery; a live keeper
holds the scheduled ownership and separate coordinator flock before fetch through
publication. The acquisition process PID was replaced by the live keeper identity
before fetch. Cleanup uses the keeper's finally block on termination, including
publication failure. Publication/remote SHA and finally cleanup are recorded in
automation memory and its external run directory. Preexisting untracked
scheduled-run evidence is preserved unstaged. Exact owned paths only; no peers,
archive, main, worktrees, extra agents or prohibited Git operations.

Initial source/document diff-check exited 2 for extra EOF blank lines in three
new checkpoint blocks. Those blank lines were removed; failed outputs and the
initial manifest are retained, and final diff-check is recorded separately.
No runtime source changed after the root suite.

Full staged diff-check exits 2 solely on three preserved raw pytest RED
whitespace lines in red.stdout (12,13,16). Raw evidence is kept byte-identical;
source/document diff-check exits 0. This evidence-only exception is reviewed.
