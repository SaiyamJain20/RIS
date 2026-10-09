# C-E2 expired-retry runner and new exact FREEZE — 2026-10-09 UTC

**Implemented/tested on synthetic inputs; actual expiry trials NOT_RUN.** A3-0037
requests the NEW full plan `a76a291d3790370018707496fcda2048833ba1e826031bf2a2c0c427b5afe03e`. Both new exact
peer ACKs are absent. Actual no-ACK CLI exits2/BLOCKED before cases/snapshots/services.
E/RQ1 stays active; E0 closed/C-E1 historical9/9 complete; gateE NOT_RUN, F/G locked.
Historical A3-0035 pre-expiry slice6/6 remains valid at its pinned bytes and RELEASED.

`expired_retry.py` independently requires canonical EXPIRED at/after ORIGINAL expiry,
one previously recovered native cache, exact whole worker cache/events/attempts/counts,
unchanged native grant and PBC request/outcome, and no added native log on either chain.
The public collector mines one synthetic DBC empty block at max(latest+1, expiry),
checks latest and pending clocks, and retries the identical grantId/deployment release
after successful Alice recovery/completion/outcome and before Bob denial. `e1._profile`
opts in only for explicit recovery; `e2` requires an expiry proof in every row. No
pre-expiry timing/TTL, permission, owner source, ABI, schema/wire, tool/lock or custody
choice changed. No capability/error-message contents are logged by the new collector;
responses use code/digest and worker exports are validated before saving.

## Commands and actual results

Exact argv/cwd/UTC start-end/wall/exit/stdout/stderr hashes are in each `.json`:

- `expiry-red`:14 expected failures (collector missing), exit1 → `expiry-green`:35pass,
  exit0 (expiry/recovery joins). Canonical positive equality/late observations plus12
  false success/error/premature/cache/attempt/event/permission/outcome/cache controls.
- `expiry-execution-red`:6fail14pass (public probe missing), exit1 →
  `expiry-execution-green`:47pass/exit0 (all profiles/points plus access/recovery).
- `expiry-plan-red`:3fail10pass (plan option missing), exit1 → `expiry-plan-green`:
  48pass/exit0. Missing/old ACK startup refusal, mandatory expiry proof, legacy E1
  controls and composition. Test-only ACK/process substitutions are explicitly
  synthetic; never used as peer or integrated evidence.
- `full-project`: bare `.venv/bin/python -m pytest -q`,495pass/82.81s/exit0.
  Source inventory initially sampled after this command began. Retained this limit
  and repeated instead of claiming a missing complete source bracket.
- `full-project-bracketed`: same full command,495pass/81.73s pytest/81.946s wall/exit0;
  71 evaluator Python inputs captured BEFORE/AFTER command, all stable.
- `expiry-cli-no-ack`: actual `.venv/bin/python -m evaluation.e2 --plan
  evaluation/evidence/e2/expiry-runner-20261009/integration-plan.json --output
  /home/karma/.codex/automations/ris-agent-branch-monitor-and-continuation/runs/20261009T004322Z/no-ack`,
  exit2/BLOCKED; zero cases/services; output manifest preserved, no snapshot.
- Prompt generation check exit0; all three complete launch prompts match sources.
  Fresh Python/Forge/Anvil/Cast/solc/Git version commands exit0; Python3.13.13,
  Foundry1.8.5, solc0.8.37; exact paths/binary/lock/package hashes in `versions.json`.
  No package installation or repeated formal run; formal model sources unchanged.

79 plan inputs and303 immutable selected owner blobs verified; independent110-input
sample also stable.15 immutable frozen copies match accepted source/Git blobs.
Every new expectation is from frozen E03 case `expiredRetryError: EXPIRED` and its
no-new-event qualification; full6 case/sourceRefs/assumptions in `case-provenance.json`.
Synthetic fixtures only; no actual new key-worker/chain/service expiry measurement.

## Peer review and source provenance

Fetch/scan144 newest communication revisions, no ambiguity/divergence; newest
file-changing commits and hashes retained in `peers.json`, `peers-after.json`,
`review.json`. Latest fetched tips ledger-agent b057c2b22c3c4b4d627b0b8702af7ed6b641c060,
protocol-agent e950766f2272f310ad8db1f1f976e815e6f947ce; no handoff-fetch delta.
A1-0049 SHA0249620c11ff00f21bd2f642a20a6085d844f6d17b5c046e1ca81224c81dcff2
reviews native6 rows without discrepancy, notes repaired-e retry4s margin.
A2-0029 SHAbc3c213a207bf67e02b2be3fb06a2941126b02cb7a7321f56046ce30df3c2d79
reviews process/worker/redaction scope without discrepancy. Both explicitly exclude
expiry integration and gate/report ACK; neither author review replaces independent
review. Read A1through0049/A2through0029 and live statuses at exact owner commits.

Selected pins remain ledger933d2a75483a08e7374cd417a6cf8a9e5c13a33c/195 entries and
protocol0716a8e2d46f985f35a612d42acaae02ab8701a4/108 entries. All303 immutable pin
blobs checked. Current ledger tip has later rehearsal/window evidence/inventory and
a changed `ledger/tools/e2_rehearsal.py` (not invoked by this recipe); these are
recorded unconsumed owner deltas, not silently promoted. Protocol selected paths equal
tip. Root latest revisions also recorded. No peer tree/mailbox edited or merged.

## Review rulings and limits

Author self-review: checked full owned diff/controls, failure propagation, request and
response redaction, input/tool/owner stability and mandatory exact new ACK refusal.
Ruling: keep user's confirmed checkout/self-review per ban on extra agents/worktrees —
cost weaker review independence. Ruling: preserve accepted pre-expiry recipe despite
4s caution — cost a slow fresh run may fail; any failure is retained, no expiry
extension. No timing optimization adopted without evidence. Ruling: explicit synthetic
DBC expiry advance after successful recovery — cost does not establish first restart
at expiry, exact wall-clock equality, OS-kill or power-loss durability. Ruling: publish
bounded supplemental slice — cost remaining50 catalog/mutants/window/report unproved.

Helper failures retained in `review.json`/`source-bracket.json`: two checks incorrectly
required entire/current ledger tree to equal selected historical pin; corrected to
verify immutable selected blobs and record tip deltas. Frozen-copy helper initially
assumed absent local ledger inventory; corrected to exact frozen Git blob. These are
Agent3 evidence-helper errors, not experiment/system findings. No failure overwritten.
Initial staged whitespace check exit2 flags raw pytest diagnostic spacing only;
retain exact output hashes and add a narrow `.gitattributes` exception for this
evidence directory’s `.stdout` files, matching existing raw-output policy. Code/
document EOF issues were corrected separately; frozen/runtime/plan bytes unchanged.

Paper-derived HMBC2020 reconstruction. Four paper crash classifications remain
BLOCKED/unproved regardless of chosen mechanics. Repaired-e only bounded tested
mechanics; deliveryunknown/symbolic/safe-ledger/trusted-worker. No ABE, recipient
acknowledgement, provider integrity, consensus or full-RQ claim. Six catalog cases
still only partly exercised from prior result; no new expiry result or checkbox.

No actual service/PID/port allocation/lease. Scheduled guard585640/start6336814 acquired
atomically; distinct coordinator flock serializes fetch/publication; finally cleanup/
publication records live externally in run20261009T004322Z and automation memory.
Preexisting untracked `evaluation/evidence/scheduled-runs/` preserved unstaged. Only
reviewed exact Agent3 paths publish on agent-3, normal push; no main/destructive Git.

## Resume

Verify both exact A3-0037 full-plan ACKs/immutable message commits/hashes/owner ancestry
and unchanged plan sources/tools before services. Then execute the above CLI WITH a
real exact ACK index and a fresh private output under owned locks. Preserve every
failure, expiry, raw/native/redacted/process/command/bracket record; release logical
freeze after run or failure. Existing A3-0035 ACKs and startup ACKs are insufficient.
Complete remaining50 scenarios/live mutants/windows/RQ1 report/all3 same-source ACKs/
every gateE criterion beforeF. No human action is needed.
