# Actual C-E2 logical recovery slice — 2026-10-09 UTC

**Actual runner exit 0 / E2_RECOVERY_SLICE_PASS: six of six approved comparisons.**
This is a tested paper-derived HMBC2020 reconstruction using synthetic fixtures,
symbolic crypto, local safe ledgers and a trusted worker. Gate E remains NOT_RUN;
F/G stay locked. A3-0035 is RELEASED after this completed source-stable run.

## Exact authorization and execution

Plan SHA-256 `4bceffc347be2267348d8b781a4c30b5db00567712f1b0d14a48aae0bee5929a`
at ../recovery-runner-20261009/integration-plan.json remains unchanged. Full plan
ACKs, independently checked against exact Git blobs and fetched owner ancestry:

- A1-0048: commit `83c084c13f182525c5ca9055f736a2a92a92abee`,
  communication/agent-1/outbox/0048-ack-e2-recovery-freeze.md,
  SHA-256 `d678342bdc2dec0661ec9ed2ff5132dfd7efd99231aac10c15147682bd03265d`.
- A2-0028: commit `902a95be319757625e8a1874e94db0e753a38f44`,
  communication/agent-2/outbox/0028-ack-e2-recovery-slice-plan.md,
  SHA-256 `7d2e9136e7dc0a1f13fdeb23f55bd78d5d7833a928f0fde502b6f01189ee2bd8`.

Headers bind Type ACK, owner From, agent-3 recipient, E/v1, Responds-to A3-0035
and Accepted-plan-sha256. Scoped exclusions remain: neither peer accepts evaluator
internals or results; startup supplement acceptance is separate. Exact accepted
ledger 933d2a75483a08e7374cd417a6cf8a9e5c13a33c /195-entry c7b7dd51..,
protocol 0716a8e2d46f985f35a612d42acaae02ab8701a4 /108-entry d16ddad8..
and hook f0ab2400.. were checked before execution and remain owner-authored.

The exact command, cwd, UTC times, output hashes and exit are in real-e2.json:

```bash
.venv/bin/python -m evaluation.e2 --plan evaluation/evidence/e2/recovery-runner-20261009/integration-plan.json --acks /home/karma/.codex/automations/ris-agent-branch-monitor-and-continuation/runs/20261009T001322Z/acks.json --output /home/karma/.codex/automations/ris-agent-branch-monitor-and-continuation/runs/20261009T001322Z/real-e2-output
```

Actual 2026-10-09T00:14:52.086520Z through 00:27:50.560010Z,
778.4734255 s wall, exit 0, empty stderr. Every row has a fresh chain pair,
deployment, reviewed snapshots and private 0700 state. Ports/IDs 18545/28545;
Anvil automining/cancun/default slow owner deployment, complete-details, funded
TEST-ONLY relay deployer and relay/CA-admin runner custody. User/witness/worker
keys stay in adapter processes. Fixture seed none; fresh signing randomness.
Python 3.13.13, Foundry 1.8.5, solc 0.8.37; actual version commands, package pins,
binary/lock hashes in versions.json/preflight.json and exact plan.

## Measured comparisons and independent joins

| Profile | Point | Mechanical result | Crash attempts / completed | Retry attempts / completed | Research scope |
|---|---|---|---|---|---|
| paper-strict | after_intent | PASS | 0 / 0 | 1 / 1 | paper crash BLOCKED; chosen reconstruction mechanics tested |
| paper-strict | after_send | PASS | 1 / 0 | 2 / 1 | paper crash BLOCKED; chosen reconstruction mechanics tested |
| paper-minimal | after_intent | PASS | 0 / 0 | 1 / 1 | paper crash BLOCKED; chosen reconstruction mechanics tested |
| paper-minimal | after_send | PASS | 1 / 0 | 2 / 1 | paper crash BLOCKED; chosen reconstruction mechanics tested |
| repaired-e | after_intent | PASS | 0 / 0 | 1 / 1 | REPAIR_SUPPORTED for these bounded logical checks only |
| repaired-e | after_send | PASS | 1 / 0 | 2 / 1 | REPAIR_SUPPORTED for these bounded logical checks only |

Each row also has wrong-admin H2 native code16 before legitimate H2 publication
(baseline issuer restriction), registered Alice permission/outcome and registered
Bob policy9 denial without a new grant/nonce/worker event. Those baseline controls
are not credited to a repair. The runtime joins public native receipts/views,
request/signature/policy/identity, original expiry, registered recipient, one
persisted intent, exact redacted cache/event prefix and attempt counters. Natural
hook exit86/empty stderr, empty EOF after_intent or one validated response then
EOF after_send, production restart on SAME state/deployment, and strictly
pre-expiry retry verified. After_send returns the identical cached full response;
all cache/token commitments stay stable. One later PBC outcome is recorded.
Repaired nonce/checkpoint/signed-grant/receipt checks remain explicit.

**Delivery is unknown in all rows.** A worker RELEASE_SENT records an attempted
send, not recipient delivery. Paper grants keep native zero recipient and use the
registered PBC key for symbolic responses under D35/A38. No paper implementation
defect, actual ABE, provider integrity, consensus, power-loss or OS-kill proof.

## Source stability, process cleanup and publication evidence

111 independently bracketed source/model/config/fixture files stayed byte-identical;
78 execution-plan inputs/tools/config and all303 owner blobs reverified. All12
materialized owner snapshots are stable (1818 per-file post-run comparisons).
All15 immutable frozen copies match their sources, using frozen Git blobs for
peer files absent from the coordinator checkout. Initial local-source lookup
failed with FileNotFoundError for ledger/evidence/source-manifest.sha256; corrected
immutable-owner lookup passed. This helper mistake is not a research result.

All24 service records ended with identities absent:12 chains and6 production
restarts exit0,6 intentional hook exits86. Owned stop/argv/PID/start/end/exchanges/
stderr hashes retained; no unrelated listener/process adopted or terminated.
3709 captured owner/export/RPC commands all exit0; direct command records selected,
full RPC records retained locally and hashed in external-public-inventory.json.
141 newest communication revisions/no divergence; post-run fetch delta empty.
No source patch or package/interface/custody change. Prior472 unit tests remain
historical; this fresh integration/source/cleanup audit is the applicable evidence.
Models unchanged, so no redundant formal rerun.

Selected public native/bootstrap/instance and redacted worker/transport/process
JSON under run/; raw logs/private state/module snapshots/build materials remain
local under the external run path above. Structured selection refuses token and
private-key fields; selected-manifest.json pins selected evidence. Exact reviewed
owned-path staging/normal agent-3 push and both-lock finally cleanup are recorded
in external publication.json/cleanup.json and automation memory after publication.
Preexisting untracked scheduled-run files remain unstaged.

## Separate author review and remaining acceptance

Author self-review: ACK scopes and ancestry, every native/control/oracle join,
crash EOF/exit/stderr vs forced death, same-state restart, expiry/cache/recipient,
source brackets/copies/snapshots, process cleanup, publication privacy and phase
boundaries. Weaker than an independent review; human prohibits extra agents.
No material deferred source defect was identified in this evidence-only slice.

Review found an acceptance omission: **the separate expired-retry refusal with no
new event is NOT_RUN in every row.** The published approved plan implements a
pre-expiry comparison, and check_recovery enforces that boundary; neither proves
the frozen catalog's separate expiredRetryError=EXPIRED trial. No duplicate-outcome
retry or complete catalog/mutant/revocation-window matrix was added to this run.
Consequently six catalog cases are partially exercised, not completed; other50
schedules are untouched. Immutable catalog status/expectation bytes stay unchanged.
This is an explicit remaining task, not a changed expectation or a gate pass.

Ruling: retain the accepted plan unchanged for this run — exact freeze authority
and source stability take precedence — cost: expired-retry and remaining catalog
acceptance need a new reviewed recipe. Ruling: use confirmed checkout and author
review under the no-agent/no-worktree instruction — cost: no independent reviewer.
Ruling: publish only the tested recovery slice — cost: E remains unfinished.

Next permitted: extend owned runner/oracles for explicit expired retry and the
remaining50 schedules/mutants/revocation-window measurements; source-bound full
FREEZE and both new exact ACKs before services. Preserve positive controls and
paper ambiguity qualifiers. Complete RQ1-E report/all3 same-report/source ACKs and
every gateE criterion before F. No human action needed now.
