# SDD ledger — plan: PLAN.md / C-E2 subject pre-release collector

BASE fbebab747ca4b6b9e41e346f412ba6038f7074d7. Expected behavior from frozen E01
subject cases, SPEC4, D35/A38 and the existing independent subject oracle.

Pre-flight: access_execution supplies authenticated user request, historical
credential/policy checks and, repaired only, verified checkpoint/ALLOW certificate.
The collector consumes public executors and a read-only worker exporter. Source
state must be fresh and this path must stop before legitimate release/completion.
No wire/ABI/dependency/owner change needed. Recipient routing/completion and fresh
separate legitimate controls are the next step; no complete plan/FREEZE yet.

Ruling: use confirmed checkout/agent-3 and author review, following the explicit
ban on worktrees and extra agents; cost: no independent final code review.
Ruling: preserve a coherent pre-release collector checkpoint, without labeling a
full E01 case complete; cost: full case remains unproved until routing/controls
and a separately ACKed plan run. No new research assumption or gate waiver.
Ruling: prior push authorization applies to reviewed exact owned paths on agent-3;
no integration-choice prompt/PR/main publication. Cost: branch checkpoint only.

Tests-first: missing feature RED12. Initial implementation11 pass/1 fail: the
synthetic model reused the same transaction hashes across chains and its shared
lookup overwrote the PBC request with DBC checkpoint calldata. Fixture lookup now
uses (chain,hash); corrected targeted104 pass. Failure preserved.
Review-driven bundle mismatch RED2 failed12 passed; original bundle binding GREEN14.
Invalid selection side effects RED6 failed14 passed; early guard GREEN20.
No native service deployment, release, completion, grant attestation or outcome
was run. Synthetic codec/signature/RPC evidence is not integration/gate evidence.

Verification review: initial690 root PASS110.48s bracketed65 Python files.
Expanded inventory setup mistakenly used system Python (eth_utils missing).
Abort intervening owned suite22.33s/SIGTERM exit-15, preserve stdout/command.
Corrected venv generator created124-input complete runtime/fixture/config/Python
bracket before suite-final. No source edit or service startup during any suite.
