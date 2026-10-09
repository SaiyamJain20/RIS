# Actual C-E2 recovery and expiry slice — 2026-10-09 UTC

**Actual CLI exit 0 / E2_RECOVERY_EXPIRY_SLICE_PASS; 6/6 complete approved comparisons.**
Paper-derived HMBC2020 reconstruction, synthetic fixtures, symbolic crypto and trusted-worker/safe-ledger assumptions. Gate E NOT_RUN; F/G locked. A3-0037 RELEASED after this run; no active services or lease. Failure: `None`.

## Authorization and exact command

Unchanged plan SHA-256 `a76a291d3790370018707496fcda2048833ba1e826031bf2a2c0c427b5afe03e` in ../expiry-runner-20261009/integration-plan.json. Both new exact owner ACKs checked by immutable message hash/header/owner ancestry before services:

- agent-1: `38e0a95450d62c8fb2bf2c48033fdc081d9348b7`, `communication/agent-1/outbox/0050-ack-e2-expiry-slice-freeze.md`, SHA-256 `335623fc41ea81dd20c7d63515048174e7242f5e3dc9cf7082df1dd350f24451`.
- agent-2: `3d60b4091227e7194ae9b897643cedc42ee0b419`, `communication/agent-2/outbox/0030-ack-e2-recovery-expiry-slice-plan.md`, SHA-256 `7d37b9ac91de56e2759f6936c804878c908b2eefdeb1c5f147f4409d87776c13`.

A1-0050 and A2-0030 bind E/v1, Responds-to A3-0037 and the exact full hash. Their module exclusions remain; neither ACK accepts evaluator internals, classifications or the RQ gate. Old ACKs/reviews were not substituted. Selected ledger933d2a75483a08e7374cd417a6cf8a9e5c13a33c/195-entryc7b7dd51.. and protocol0716a8e2d46f985f35a612d42acaae02ab8701a4/108-entryd16ddad8../hookf0ab2400.. verified. Later unconsumed ledger rehearsal/evidence remains outside the pin.

```bash
.venv/bin/python -m evaluation.e2 --plan evaluation/evidence/e2/expiry-runner-20261009/integration-plan.json --acks /home/karma/.codex/automations/ris-agent-branch-monitor-and-continuation/runs/20261009T011322Z/acks.json --output /home/karma/.codex/automations/ris-agent-branch-monitor-and-continuation/runs/20261009T011322Z/real-e2-output
```

UTC 2026-10-09T01:14:30.096808+00:00 through 2026-10-09T01:27:29.869316+00:00; 779.772433s wall. Exact argv/cwd/exit/output hashes in real-e2.json. Fresh PBC/DBC deployment, reviewed snapshots and private0700 adapter state per row. Ports/chain ids18545/28545, automining/cancun, owner default slow deployment, complete-details, TEST-ONLY relay deployer and relay/CA-admin runner custody. Adapter retains user/witness/worker keys. No seed; fresh signing randomness. Python3.13.13/Foundry1.8.5/solc0.8.37; fresh version commands all0, binary/package/lock pins retained in versions.json/preflight.json.

## Results and limits

| Case | Recovery/control | Expired reply | Bob control |
|---|---|---|---|
| paper-strict-after_intent | RECOVERY_CONTROL_PASS | EXPIRED | True |
| paper-strict-after_send | RECOVERY_CONTROL_PASS | EXPIRED | True |
| paper-minimal-after_intent | RECOVERY_CONTROL_PASS | EXPIRED | True |
| paper-minimal-after_send | RECOVERY_CONTROL_PASS | EXPIRED | True |
| repaired-e-after_intent | RECOVERY_CONTROL_PASS | EXPIRED | True |
| repaired-e-after_send | RECOVERY_CONTROL_PASS | EXPIRED | True |

For complete rows: natural hook exit86, empty EOF after_intent or one validated frame then EOF after_send; production restart on identical private state/deployment; same cached response before ORIGINAL grant expiry; registered recipient and native permission/request/outcome joins. Wrong-admin16 is baseline issuer rejection, Alice allowed and Bob policy9 denied with no new grant/nonce/worker event.

AFTER Alice completion/outcome, BEFORE Bob denial, one explicit synthetic DBC empty block at max(latest+1, ORIGINAL grant expiry). Latest and pending clocks at/after expiry. IDENTICAL release envelope returns schema-valid EXPIRED. Entire redacted worker cache/events/attempts/counts and native grant/PBC request/outcome/both chains' contract logs unchanged. No permission or TTL extension; no recipe reorder or PBC clock correction adopted. Peer clock-skew/tight pre-expiry caution retained; a future slow run can fail visibly.

Delivery stays unknown. Four paper crash classifications remain BLOCKED/unproved even when reconstruction mechanics pass; repaired-e evidence is bounded mechanical REPAIR_SUPPORTED only. Catalog-coverage.json maps exact six frozen case/sourceRefs/assumptions. This completes the explicit expiry subchecks in successful rows; no duplicate-outcome trial, other50 schedules, live mutants, revocation-window matrix, report or RQ gate. No first restart at expiry, exact wall-clock equality, power-loss, OS-kill, ABE, provider-integrity or consensus proof.

## Stability, cleanup and review

113 pre/post sampled source/model/config/fixture inputs stable,79 plan inputs/303 immutable owner blobs reverified. 12 snapshots stable, 1818 owner-file comparisons.15 frozen copies checked against exact sources/Git blobs. All 24 owned process records ended with PIDs absent: 18 exit0, 6 natural crash86. 3943 captured command records; 0 nonzero. Actual argv/PID/start/end/exit/stderr/response commitments retained. No unrelated process stopped.

147 newest communication revisions scanned; no divergent revision or missing owner branch. Exact root/file-changing revisions and before/after branch tips retained. Read A1through0050/A2through0030 at fetched owner commits. Runtime/model/dependency/interface bytes unchanged; historical495 unit tests and formal results not rerun. This fresh integrated/source/cleanup audit is the applicable verification.

Author self-review only: checked exact ACK scopes, native/worker/response joins, original expiry/no-event assertions, Bob after DBC advance, positive/denied controls, snapshot/input stability, process identities and redacted publication selection. Human bans extra agents/worktrees; weaker review independence remains. No material deferred source defect identified. Ruling: keep approved timing/order — cost a slow run may fail, never hidden by expiry extension. Ruling: publish this bounded slice — cost full E remains unfinished. Existing confirmed checkout/owned agent-3 publication authorization used; no extra reviewer, worktree or main push.

Scheduled lock acquired atomically at01:13:22UTC; guard PID recorded externally. Separate coordinator flock serialized fetch, later service lifecycle and publication. **Operational limitation:** initial service startup preceded acquisition of the persistent coordinator guard; no Git write occurred during that interval, no source movement observed. Metadata explicitly records this sequencing lapse; next run must hold coordinator before service startup. Scheduled guard remained held throughout. Both locks released in final cleanup including publication failure.

Selected public native/bootstrap/instance and redacted worker/process JSON only; structured selection rejects raw token/private-key fields. Raw/private state, snapshots/build outputs and full RPC records remain external at /home/karma/.codex/automations/ris-agent-branch-monitor-and-continuation/runs/20261009T011322Z. selected-manifest.json and external-public-inventory.json pin outputs. Exact reviewed Agent3 paths staged/pushed normally; publication SHA/remote/finally cleanup in external publication.json/cleanup.json and automation memory. Preexisting untracked scheduled-runs preserved unstaged.

## Next permitted work

Implement independent remaining50 catalog schedules/live mutants/revocation-window collector, using reviewed owner interfaces and explicit expected classifications. New complete source/tool/config FREEZE and both exact ACKs before changed live execution. Draft RQ1-E report, all3 same-report/source ACKs and every mandatory gateE criterion before F. No human action needed.
