# Returning Agent 3 branch review — 2026-10-12

Human request: pull all changes, gather context, verify them and fix issues.
Agent3 fast-forwarded from8e5a6dd to consolidated origin/agent-1 6911478 on its
own agent-3 branch.141 incoming history commits /4862 changed paths include the
previously separate owner modules and the solo-phase work. No history rewriting,
main push, worktree or extra agent. Preexisting scheduled-runs stays unmodified.

## Context and scope

Read the active AGENTS/common/role/spec/plan/interface/protocol/live records,
A1-0086 return handoff, solo plan/protocol/proxy STATUS/HANDOFF/S3-0023 and
A1-0080..0082, report RQ1-E.md and the changed evaluator code/test paths.
The272 newest communication revisions have no incomparable content divergence.
Ledger933d2a7 and protocol0716a8e production bytes are unchanged; new protocol
characterization tests/reviewer evidence are owner-authored. Frozen v1 and archive
are unchanged. Exact incoming branch tip and source provenance are in before.json
and communication-provenance.json; no ACK was inferred from silence.

The recorded qualified solo Gate E PASS remains accepted in its original scope:
56/56 catalog rows, correlated proxy reviews, criterion4 scoped by recorded human
A1-0080, owner window evidence under A1-0081. Integrated mutant matrix and
integrated revocation window remain NOT RUN. D47 paper crash properties remain
frozen BLOCKED / decided SPEC_GAP, UNPROVED. Anvil/symbolic adapter/trusted witness
and worker/single trial/unknown delivery are still limits. F0 needs a separate
plan and human go-ahead; F/G implementation was not started.

## Findings and fixes

1. The gate test required Agent1's rebuilt ProVerif bc2cd5ed.. even when the
   original frozen binary c1087205.. exists and is correctly selected. Baseline
   root1643 PASS/1 FAIL and the focused RED identify this assertion. It now checks
   the actual binary hash, the frozen pin and provenance of an allowed declared
   build; neither tool pin nor historical host override was changed.
2. e_gate._versions ignored failed command exit statuses. Real harmless probes
   for all8 tools returned1 while `ok` was true. Nonzero exits now prevent tools
   from being marked verified. Each binary is also hash-checked before running.
3. run_proverif detected binary/model mismatches after running, and did not catch
   binary changes during execution. Harmless sentinel executables reproduced the
   missing pre-execution refusal and incorrect post-drift matched verdict. Binary
   and model hashes now guard execution; binary drift prevents matched success.
4. Root/evaluation/interface entry points and original Agent3 runtime status
   were stale at44 remaining/E NOT_RUN. Updated current status in owned active
   files and this addendum. Signed RQ1-E.md remains an immutable snapshot; its
   pending ACK text is historical. The current ACK/adjudication record is GATES.md.

These are tested evaluator reconstruction issues/documentation inconsistencies,
not HMBC vulnerabilities. Initial regression-fixture environment omission and
one metadata read with system Python were corrected; raw failures/corrections
are retained. No package was installed or changed to mask them.

## Actual verification

- Baseline root:1643 PASS/1 FAIL, exit1/442.11s; only failure was the host-specific test.
- Final root:1658 PASS, exit0/447.11s;6272 bracketed inputs unchanged throughout.
- Protocol:1375 PASS/201 scoped SKIP, exit0/373.92s.200 ScenarioResult skips and
  1 FileHash skip are evaluator-owned types, not missing tools or hidden failures.
- Ledger suite:exit0; existing owner mutant checker:exit0, all7 expected mutant
  suite detections, no unexpected base failures. This is not the missing live
  two-chain mutant matrix. Mutant stdout matches the historical pinned output.


- Test-first tool probes: corrected RED11 failures/2 healthy controls; driftRED1;
  focused finalGREEN15. The initial fixture-error run is preserved separately.
- Published gate:2112 selected files +4 wrapper files hash-equal;376 resultFiles
  (264 present and112 ABI records reconstructed from pinned Git blobs);4047
  historical source blobs match runHEAD21b37fb. All56 catalog IDs, expectations
  and proof paths checked. Execution FREEZE/ACK blobs and three same-source report
  ACKs match. Frozen15 copies unchanged; signed manifest908fd615.., criteria
  47e38dd3.. and report69dabfba.. unchanged.
- All8 original native-evidence review tools re-executed on this host:56/56 pass.
  The original protocol-evidence reviewer re-executed:0 problems. This verifies
  published-data consistency; reusing the original check design does not make
  these checks independent.
- Protocol export check:9 files match. Protocol fixture processes ended; no
  unrelated process was terminated. Local versions/hashes in versions-local.json.

Commands, UTC times, exits, output hashes and source brackets are selected here.
Large raw data/private state stays in the original host's job directory; no
unavailable raw result was fabricated. The112 omitted ABI manifests were verified
from owner Git; omitted RPC transcripts/private worker DBs are not independently
available here. No full fresh80-minute two-chain gate run was done on this host.
Future integrated execution of changed evaluator bytes or this host's tool paths
requires a revised exact plan/FREEZE and both affected peer ACKs. Old plan ACKs
cannot authorize those changed inputs. The generic gate stays fail-closed.

## Review decisions

Ruling: original checkout/single-session review under the human no-worktree and
no-extra-agent instructions. Cost: no independent second reviewer; correlated
review limitations remain. Ruling: do not rewrite signed report/gate evidence to
fix current status prose; doing so would invalidate the same-source ACK hashes.
No evidence result or classification was changed. No additional material design
choice. Original Agent2 can still review/overturn its proxy's positions; this is
Agent3's return review in its own scope, not a substitute Agent2 ACK.

Publication and finally lock cleanup are recorded in the task's external review
log and automation memory. Only exact reviewed owned paths are staged and pushed
normally on agent-3. main/peer module/archive/frozen bytes are not changed.
