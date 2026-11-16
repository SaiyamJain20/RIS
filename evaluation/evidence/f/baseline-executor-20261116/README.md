# A3-0162: pinned baseline recipes and isolated command executor

Agent 3 / C-F1, paper-derived HMBC2020 reconstruction. **Offline component
evidence only. Gate F and all 32 integrated cases remain NOT_RUN; G LOCKED.**
The exact reviewed report, partial packet, execution-plan DRAFT and frozen
interfaces are unchanged. This receipt neither requests nor supplies an ACK.

Implemented [f_baselines.py](../../../f_baselines.py) with
[synthetic tests](../../../tests/test_f_baselines.py). Commands use absolute,
hash-pinned lexical tool paths (preserving venv lookup), explicit environments,
a selected source-root inventory and optional external runtime-file pins. It
checks the recipe and all declared inputs before launch and before/after each
command. Unexpected extra files in selected roots, altered/missing inputs and
tool/runtime drift fail closed. Known Python caches and ledger out/cache outputs
are excluded; the caller must choose complete input roots. Evidence lives outside
the snapshot and is never overwritten.

Each command retains separate stdout/stderr bytes and hashes, argv/cwd,
timestamps, elapsed time, real exit/signal, timeout/output-budget flags and owned
PID/group/reaping facts. A failed command or changed input prevents later commands
from launching. Expected counterexamples require both their expected exit and
output marker. A declared DRAFT or blocked recipe is refused even with its exact
hash. This is **not** an ACK verifier: the future coordinator must validate the
actual FREEZE/owner ACKs before calling it for real baselines.

The direct child remains unreaped (`waitid`/`WNOWAIT`) until its newly created
process group has received TERM then KILL. This avoids signaling a reused PID and
cleans ordinary inherited-group stragglers on success as well as timeout. An
unrelated process survives the timeout control. This is Linux/POSIX process
ownership, not a sandbox: a deliberately escaping process or a malicious command
can evade these boundaries. Output size is a polled stop threshold, with possible
overshoot between polls, not a disk quota. No persistence or service correctness
claim follows.

## Verification and retained examples

- Initial test-first command: `.venv/bin/python -m pytest -q evaluation/tests/test_f_baselines.py`
  exited **1**, with 23 setup errors explicitly reporting the missing component
  ([red log](red.txt.gz)); these were absent-module fixture errors, not runtime results.
- Initial implementation: same command exited **1**, 22 passed / one recipe-marker
  mismatch ([initial output](green-initial.txt)). Recipe review added the missing
  Foundry/port environment check; two probes failed before the correction
  ([recipe review RED](recipe-review-red.txt.gz)). Initial green: 24 passed, exit 0
  ([green](green.txt)).
- Additional self-review reproduced two failures: the builder omitted DRAFT
  metadata, and a declared DRAFT recipe could execute with a matching hash
  ([DRAFT review RED](draft-review-red.txt.gz)). Both are corrected. The generic
  synthetic-command API remains a low-level runner, not an authority boundary.
- Final focused command:
  `.venv/bin/python -m pytest -q evaluation/tests/test_f_baselines.py evaluation/tests/test_owned_command.py evaluation/tests/test_manifests.py evaluation/tests/test_f_preflight.py`
  exited **0**, **52 passed in 12.41s**, including 31 new executor probes
  ([final focused log](focused-final-v2.txt)). Previous 51-pass focused run is
  superseded by this final run.
- The first root evaluator run was intentionally interrupted to test the DRAFT
  guard correction from a fresh process: **1030 passed**, no test failure,
  exit **2** after 261.03s ([interrupted run](evaluation-suite.txt)). It is not a
  completed suite result. Final root run: **3059 passed in 704.28s, exit 0**
- `.venv/bin/python -m evaluation.evidence.f.baseline-executor-20261116.probe`
  exited **0**. Retained [synthetic recipes, manifests and streams](sample/summary.json)
  cover positive/expected-exit controls, source-pin refusal, unexpected exit,
  timeout and later-command blocking. These signatures/exit markers are ordinary
  fixture text, not protocol evidence.
- `.venv/bin/python -m evaluation.evidence.f.baseline-executor-20261116.build_draft`
  exited **0**. [Owner recipe DRAFT](owner-recipe-draft.json) has eight proposed
  commands and **2,824 exact expected source-file hashes**, derived in memory from
  the accepted ledger/protocol and parent integration Git archives. **No owner
  command was executed.** The builder records Git archive hashes/provenance;
  [audit.json](audit.json) records actual tool versions/hashes and package versions.

The recipe names the 316-test ledger baseline, complete mutant-check marker,
protocol `pytest -c protocol/pytest.ini --rootdir protocol -p no:cacheprovider -rs -q`
with the expected 3,226/201 summary, and five TLC controls (expected exits 0/0/12/12/12).
These are **expected control outcomes**, not new measurements. Protocol tests
include services, so the recipe is deliberately unexecuted here. Its explicit
Foundry PATH/directory and test port range incorporate S2-0026 §9; some live
protocol tests still choose OS ephemeral ports outside that range.

## New peer evidence, received during this run

Read A1-0143 and the updated peer handoff at `origin/agent-1`
`26e523572b5f8b7204f3a3900fdde795eea415c1`; message first published at
`a0f4d7ca` (full changing commit in [audit](a1-0143-audit.json)). All **27**
attachment hashes verify against that exact Git publication. Read the manifests,
exit records and threshold readback. Agent 1 reports four deploys exit 0 and
PSC/Governance/KSSC thresholds 3/3/3 versus 2/2/2. This receipt verifies attachment
identity and manifest fields, not the deployment execution. No local deploy ran.

Future deployment code must bind F-18 by manifest threshold 2 **and** on-chain
PSC/Governance/KSSC `threshold()` values; repaired-f uses 3. Both manifests say
`repaired-f`, so profile strings/addresses alone are insufficient. Keep disposable
source extracts and Forge cache/broadcast output outside the FREEZE run-evidence
scan directory; the pinned sources contain public TEST-ONLY Anvil key literals.
Item 5 checkpoint/decision/receipt/governance calls through the future runner
remain outstanding. A1-0143 is **not an ACK** and does not close Gate F.

## Remaining work and limits

This advances stage-3 **implementation**; it does not complete stage 3 execution,
stages 4–7, the F runner or the F gate. The draft snapshot is not materialized.
The protocol suite needs pinned Git objects reachable from its snapshot. Installed
Python distributions, Java libraries and other transitive tool/configuration
inputs are not fully inventoried by an interpreter/executable hash plus uv.lock.
The explicit runtime-file pin API can carry these inputs, but no complete runtime
closure has been established here. Stdout marker checks are bounded control
assertions, not an independent parser/proof of package test semantics.

**Next concrete Agent-3 code:** implement closed snapshot materialization and
runtime/tool inventory for this recipe, tested using synthetic Git/input fixtures;
retain separate source and run-evidence directories and validate required Git
object reachability without executing owner suites. Then connect family drivers,
native signing-time observations/capture completeness, oracle verdicts,
post-bracket and E regression. Do not substitute unchanged-branch checks for this
unfinished independent work. Exact execution FREEZE/role ACKs still precede real
services, baselines with services and integrated cases. No new peer/human action
is needed for the current component.

Classification: tested reconstruction result from synthetic processes;
correlated self-review by the same author, no extra agents/worktrees. Source
and receipt SHA-256 manifests are post-verification identities, not an integrated
source bracket. No ledger/protocol/peer-mailbox/archive/frozen-interface edits,
main push, external messages or deployment. Four preexisting untracked pitch and
update artifacts remain untouched.
