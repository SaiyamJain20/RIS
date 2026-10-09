# C-E2 identical-request replay runner preparation

Paper-derived HMBC2020 reconstruction, synthetic fixtures, E/RQ1 only.
**No live replay trial.** New plan `a7732650007e9b06a3de49bbe5cc36c1baed674f67eb4e947da9cbbef851d652` /A3-0041 requires both exact new peer ACKs.
Gate E remains NOT_RUN; F/G locked. No active service/lease.

Independent oracle and public ACSC collector replay the original accepted
policyEnf/consumeDecision call before first release. They require a prior allowed
native grant; checked original ABI/caller/address/calldata; a distinct mined
transaction hash with increased relay transaction nonce; status0/Rejected8/no
receipt logs; complete unchanged request, grant, nonce, access count, worker and
both-chain contract histories. The original Alice release/completion/outcome,
Bob policy9 denial and wrong-admin16 control remain mandatory in each fresh
profile. Paper deduplication is by identical accepted reference; repaired-e also
has an already-consumed nonce. This is not a new-reference experiment. Identical-reference replay alone does
not establish rejection of a different request digest sharing (gid,nonce); the
frozen fresh-reference nonce-replay control remains a separate unrun schedule.

[Plan](integration-plan.json) pins85 evaluator/config/fixture inputs,303 owner
blobs at ledger933d2a7/c7b7dd51.. and protocol0716a8e/d16ddad8..,
exact binaries/packages/locks/environment/custody/mining/ports/budgets and three
fresh chain pairs. Owner inventories and15 frozen copies were reverified;
[source bracket](source-bracket.json) checks99 inputs remained stable across the
full evaluator suite. [Source choices](source-choices.json) binds frozen scenarios,
source map/assumptions and native owner source hashes. Existing schema/ABI bytes
and tools/custody are unchanged. Planned classifications are paper SUPPORTED as
reconstruction behavior and repaired-e REPAIR_SUPPORTED, conditional on actual
future observations. Synthetic checks do not establish these live results.

[Commands](commands.json) and [versions](versions.json) record commands/exits/
output hashes and Python3.13.13/Foundry1.8.5/solc0.8.37 observations; exact installed dependency hashes
are in integration-plan.json.
Oracle RED34failed→GREEN34; public collector RED12failed/34passed→GREEN46;
plan guards RED7failed/20passed→GREEN27; fresh full suite584passed in109.48s,
exit0. False-evidence controls cover deny-all/no original grant, wrong identity,
nonce/profile errors, changed state/history/worker/access count, successful or
wrong-code replays, receipt logs, altered calls/caller/destination, reused hash/
nonce and expiry boundary. These are synthetic observations and child-process
unit checks; no integrated matrix evidence follows.

Actual CLI command in commands.json returned2/BLOCKED, with [manifest](no-ack-manifest.json)
showing no cases/services/snapshots. Missing A3-0041 exact Type ACK/From owner/
To agent3-or-all/RQE/v1/Responds-to A3-0041/Accepted-plan-sha256 `a7732650007e9b06a3de49bbe5cc36c1baed674f67eb4e947da9cbbef851d652`
from BOTH peers blocks services. Old execution/supplement ACKs and reviews do not
substitute. Once both arrive, verify exact message content hashes/owner ancestry,
plan/binary/input hashes, and run the saved CLI with a fresh private output and
exact ACK index under both guards. Retain every failed/expired trial, all native
receipts/views/traces, actual transaction bodies, redacted worker snapshots,
commands/process lifecycle and source stability; release freeze after the result.

A1-0053 at8c991dec60d2039be21c67e713a5775e6a59da55 and A2-0033
ate6a8927aff6d8ca4a8e70114e0c0f56273142814 found no discrepancy in their
stated ledger/protocol scopes of the prior duplicate slice. Their exact message
copies and hashes are retained. Agent2 correctly distinguishes equal idle-worker
snapshots from worker retry/idempotence. Neither is a report or new plan ACK.
Historical6 recovery/expiry+3 duplicate results stay separate;47 schedules,
live mutants, windows, report/all3same-report-source ACKs/every gateE criterion
remain. Four paper crash classifications remain BLOCKED/unproved. No original
implementation, delivery, ABE, consensus, power-loss or OS-kill proof.

Author review only under the explicit human ban on extra agents/worktrees.
Rulings: reuse confirmed checkout and self-review (cost: no fresh independent
review); retain pre-expiry failure rather than extending permission (cost:
possible classified availability failure); publish a bounded replay slice (cost:
rest of E still unproved); normal owned agent-3 push uses existing authorization.
No deferred material finding from author review. Timing adds native reads before
release; actual repaired-e margin is unmeasured and expiry must fail visibly.

[Stale-lock decision](stale-lock-decision.json) preserves PID803334/start ticks
7059292, absent owner process and >90min age. Original metadata preserved externally
at /home/karma/.codex/automations/ris-agent-branch-monitor-and-continuation/runs/20261009T041355Z/stale-scheduled-lock/.
New live scheduled guard plus separate coordinator acquired before fetch; cleanup
and publication are retained externally and in automation memory. No unrelated
untracked scheduled-run evidence was staged. No peer modules/mailboxes/archive/
frozen copies/main/history rewrite touched. No human action needed.
