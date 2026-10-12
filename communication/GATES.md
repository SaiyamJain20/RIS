## F0 baseline authorization — 2026-10-12

D51/A3-0052 record the human's branch convergence instruction and F0 planning
starting point. Fresh full-module regressions passed on the consolidated source;
they are baseline regression evidence, not an integrated F gate. Exact F0 matrix,
source/interface plan ACKs and mandatory F criteria remain open. Gate F NOT RUN;
G locked. Historical qualified E PASS and its signed evidence are unchanged.

# Sequential RQ gates

Writer: agent 3 (in the solo phase, agent 3 (proxy), A1-0059). Gate E is **PASS in the solo phase** (correlated review; record of 2026-10-12 at the end of this file). Gates F and G are **NOT RUN**. Evidence links and ACK IDs are supplied by actual runs, not by this planning task.

## E — RQ1 completion

`run:` = `evaluation/evidence/e3/gate-run-20261012/`.

- [x] v1 interfaces frozen; source map and all paper-gap choices reviewed by agents 1/2/3. — `run:verify-freeze.json` (FREEZE f700292e.. UNCHANGED, 15 frozen copies); closed E0 record `communication/E0_MAPPING_ACKS.json`, `communication/E0_ACCEPTANCE.md`.
- [x] Legitimate registered access succeeds; denied identity/issuer cases fail for the right reason. — all 56 rows ran the three D1 controls first (wrong admin 16, Alice allow with one outcome, Bob POLICY_DENIED 9): `run:catalog-coverage-56.json`, `run:catalog/`.
- [x] E01, E02 and E03 each have source/profile distinction, observed traces, limitations and supported/refuted/ambiguity classification. — `run:catalog-coverage-56.json` (e57e4983..: PASS 56, FAILED 0, NOT_RUN 0); RQ1-E.md §6-§9; the 4 paper crash rows are "frozen BLOCKED / decided SPEC_GAP, UNPROVED" (D47), never findings.
- [x] Applicable repaired scenarios pass; meaningful mutants fail; denial-of-all is rejected by positive controls. — human-scoped, A1-0080: met on owner, formal and baseline evidence; integrated live mutant matrix not run. `ledger/evidence/p3-mutant-suite-rerun/`, `evaluation/evidence/e2/p3-proverif-20261012/`, the 8 repaired-e guard rows under `run:catalog/`; RQ1-E.md §12.
- [x] Two-chain real integration and durable worker recovery run from fresh state. Symbolic crypto mode is visibly recorded. — `run:manifest.json` (`executionMode` real-integrated, `adapterMode` symbolic; fresh two-Anvil pair per row); `run:catalog/recovery-expiry/` (logical process-death crash points only).
- [x] ProVerif correspondence outputs and negative control are saved; state/cryptographic limits are stated. — `run:proverif/summary.json` (`matched` true, symbolic abstraction); `evaluation/evidence/e2/p3-proverif-20261012/`; RQ1-E.md §11, §15.
- [x] `evaluation/reports/RQ1-E.md` answers RQ1; no JANUS findings are imported. — RQ1-E.md 69dabfba.. (answer §0); ledger claims A1-0084/A1-0085, protocol claims S2-0022/S2-0023, evidence and model S3-0024; JANUS appears only in "not used" statements.
- [x] Source/input/output/tool hashes, commands and exit codes recorded; no input changed during the run. — `run:bracket-pre.json` = `run:bracket-post.json` (except label and time); `run:versions.json`; `run:manifest.json` (`sourceStable`, `worktreeUnchanged` with HEAD 21b37fb and empty status before and after, `planReverified`; `resultFiles` hashes).
- [x] Three ACKs refer to the same report and source manifest. Gate E PASS recorded before F starts. — A1-0085, S2-0023 and S3-0024 name the same four items (below); recorded 2026-10-12; F not started.

**Evidence run:** `evaluation/evidence/e3/gate-run-20261012/` (2126 files; evidence commit c2c81d5), from plan `evaluation/evidence/e3/gate-plan-20261012/integration-plan.json` sha256 c00860192aaa69fd2e5f7baf132f5ebf10bf14ebba377edada31c1d9372b6bb9, runId `E-gate-20261012`, FREEZE S3-0021 (plan ACKs A1-0083, S2-0021). Run HEAD 21b37fb; exit 0, 56/56 PASS, 4749.50 s (S3-0022). Gate RESULT S3-0023.

**ACKs:** A1-0085 (agent 1, ledger claims and every row), S2-0023 (agent 2 (proxy), protocol and key claims) and S3-0024 (agent 3 (proxy), evidence and model; self-sign-off). Each names exactly:

| Item | sha256 / commit |
|---|---|
| `evaluation/evidence/e3/gate-run-20261012/manifest.json` | 908fd6156ac5c6c4f640686fbddade3f9720cf29fb1e579f7c3d01f0909205a2 |
| `evaluation/evidence/e3/gate-run-20261012/gate-evidence.json` | 47e38dd369ce686d5298f909c43c79cdf4b7eff4d20d41988a57f80974538500 |
| `evaluation/reports/RQ1-E.md` | 69dabfbab9d9deeb0d94b448da6bf9b9674ce25c7c94e1b101f67c4804c89b8f |
| HEAD of record | 871e21812877ff1f9a00b8877236f9970714bf57 |

**Decision:** "gate E PASS: solo phase, correlated review, criterion 4 human-scoped (A1-0080), window cited from owner evidence (A1-0081), integrated mutants and window not run"

## F — RQ2 completion

- [ ] Gate E PASS and E regressions still pass.
- [ ] Component trust matrix distinguishes witness faults, ledger safety, worker/authority compromise and cohosted processes.
- [ ] q=3 of 4 signatures are unique, identity/action/state-bound and durable; wrong/duplicate/stale certificates reject.
- [ ] f=0/1 fault schedules preserve defined safety; one refusing witness permits legitimate progress under eventual delivery.
- [ ] Two-unavailable/f=2 controls exhibit or explain the advertised limit; residual worker compromise is included.
- [ ] TLC model, configuration, explored-state output and weakened-model controls recorded.
- [ ] `evaluation/reports/RQ2-F.md` answers the conditional core RQ2 without claiming Anvil is Byzantine consensus or admission is validator takeover.
- [ ] Integrated freeze run and three ACKs recorded. Gate F PASS before G starts.

Evidence run: not created. ACKs: none. Decision: NOT RUN.

## G — RQ3 completion

- [ ] Gate F PASS and E/F regressions still pass.
- [ ] G0 adapter/source/parameter/composition review passes with actual decryption vectors; `abe-real` mode verified.
- [ ] Future-data exclusion, no-history join, later key compromise and cached-output cases have separate offline/online outcomes.
- [ ] Epoch prepare/commit/retire, crash recovery, stale requests and partial rollout have tested state transitions.
- [ ] Payload/wrapper policy and metadata integrity are tested; key ownership, retention and regeneration paths are explicit.
- [ ] TLC/ProVerif outputs are saved with their bounded/symbolic limitations and negative controls.
- [ ] Real encryption/partial/final-decryption and rotation measurements reported; no symbolic adapter passed off as cryptographic evidence.
- [ ] `evaluation/reports/RQ3-G.md` answers RQ3 with supported and failed guarantees; no claim of plaintext recall or secrecy from merely renaming an epoch attribute.
- [ ] Integrated freeze run, source/tool hashes and three ACKs recorded. Study/reproduction guide assembled.

Evidence run: not created. ACKs: none. Decision: NOT RUN.

## E0 partial checkpoint (2026-10-07)

See `evaluation/reports/E0-progress.md` and A3-0003 for locally verified source/schema/vector/toolchain preparation. Exact three-agent ACKs and agent-2 service/flow support are unavailable. E0 is not closed; gate E remains NOT RUN. The runner/gate preflight exits 2/BLOCKED. Ledger-only tests and ProVerif toolchain smoke do not satisfy real integration/correspondence requirements above.

## Current E0 review — 2026-10-08

Both peers supplied E0 owner handoffs and scoped revision3 reviews. Agent3 revision4 adds strict operation/envelope/result/ScenarioResult definitions and39 prospective case fixtures. Exact affected-party ACKs, shared compatibility acceptance and frozen-interface publication remain required; see interfaces/proposals/v1/ACCEPTANCE.md. No checkbox in the RQ1 gate is closed by schema/module tests. Runner/gate preflights remain BLOCKED; no E1 unlock or real service integration. Earlier partial checkpoint text is historical.


## Current E0 review — revision5 (2026-10-08)

Revision4 scoped peer acceptance requested concrete changes. Revision5 addresses them and proposes two missing witness operations (A2-0008/Agent1 confirmation).148 evaluator tests,565 schema verdicts,393 signed checks and fresh166-test ledger reproduction are E0/module compatibility evidence only;48 case schedules remain NOT_RUN. The initial schema command timed out124, then an unchanged longer-budget retry passed; retain both. Exact revised peer acceptance and frozen publication/mapping still block E0/E1. No RQ gate checkbox above is closed by this work. See A3-0012 and revision-5-review evidence.

## A2-0009 scoped review (2026-10-08)

Agent3 reproduced618 non-live E0 tests/101 evaluator-only skips and16 examples at exact5e203d0/89-file pin. This closes the missing-operation/export dependency, not a gate checkbox. A2's32 paper expectation exclusions, owner export metadata correction and new exact supplement review still precede E0 promotion. Candidate services are NOT integration-ready. No live two-chain/worker/formal evidence, INTERFACE_READY or E1 unlock; all RQ gates remain NOT_RUN.

## Revision6 E0 delta review —2026-10-08

D35 selects registered-key paper responses after A1-0021/A2-0011; Agent2 production successor/exact materialized ACKs pending.35 package/94 peer inputs stable;161 evaluator tests,619 selected non-live protocol tests/101 skips,393 signed checks,565 schema verdicts/0 mismatches.56 schedules NOT_RUN; no live service/fault/recovery/formal query or RQ checkbox closed. Exact review: manifestdf2a306fd77937572346cf5e91e9354536988af63ed660e14d51e04350161c62; evidence evaluation/evidence/e0/revision-6-review-20261008/. E0 open; E1/F/G locked.

## A1 revision6 ACK and owner READY —2026-10-08

A1-0022/4689562 supplies the exact ledger-facing revision6 ACK with explicit exclusions. A1-0024/a172fd3 supplies owner READY for101-entry731a5eb0.., v1 labels and unchanged ledger source/ABI/signed bytes. Agent3 independently checks35 package hashes/295 owner blobs, four successor deployment schemas and12 rejection controls; no live owner tests or integrated scenarios rerun. A1-0025's case map remains owner evidence. Q-1 classification convention is D36; cases remain NOT_RUN. A1-0023's sprint RFC cannot replace Agent2's exact ACK or the existing freeze/mapping/integration/report gates. No gate checkbox is closed; E0 open/E1/F/G locked. Review: evaluation/evidence/e0/a1-revision6-ack-ready-20261008/.


## A1-0026 optional deployment successor —2026-10-08

Reviewed101-entry407c8633.. at91add8c;31 captured commands0,296 immutable owner blobs,35 unchanged candidate files,84 remote communication revisions/no divergence. Bash syntax/mock-forge flag checks/default-command comparison only; no live deployment, state/timing, service, recovery, model or integrated scenario evidence. ABI manifest already included in both owner inventories; prior omission note corrected with historical files preserved. Agent1 withdrew the waiver and accepts exact gate sequence/D36. Agent2 exact affected revision6 ACK is still absent. E0 open/E1/F/G locked; no RQ checkbox closed. Evidence: evaluation/evidence/e0/a1-0026-successor-20261008/.


## E0 v1 frozen publication —2026-10-08

All seven pre-publication E0 acceptance rows verified within exact affected scopes after A2-0012/f69e250. Frozen15-copy interfaces/v1/FREEZE.json SHA-256f700292ec7e3b2c8f2b59c7a728a991cd7d6dea2e4a06cea71f6f6c97b9962a2; A1-0022 and A2-0012 exact revision6 scope/exclusions plus unchanged prior ACKs recorded. Fresh161 evaluator/707 protocol checks (108 skips)/393 signing/565 schema/166 ledger/196 Cast evidence;195 owner inputs and35 candidate files stable;86 communication files/no divergence. ProVerif tool smoke only; no services/live catalog/recovery/correspondence/integrated gate evidence. Both frozen mapping ACKs are still absent, so E0 closure/E1 unlock pending. No RQ checkbox closed; all56 schedules NOT_RUN and all RQ gates NOT_RUN; F/G locked. See communication/E0_ACCEPTANCE.md and evaluation/evidence/e0/v1-freeze-20261008/README.md.

## E0 mapping closure —2026-10-08

Exact A1-0027/70f704d and A2-0013/e30d00d frozen mapping ACKs verified; E0 closes/E1 unlocks, with scope exclusions intact. Frozenf700292e.. remains immutable; live status and reviewed98-entry protocol successor recorded in communication/E0_MAPPING_ACKS.json. Static/source/export evidence only (12 non-live tests/9 regenerated exports/16 example verdicts); no real two-chain/services, recovery, correspondence, report or RQ gate run. Every mandatory RQ checkbox and gate decision above remains unchanged/NOT_RUN.


## C-E1 bootstrap/native executor checkpoint —2026-10-08

335 evaluator unit checks pass on stable inputs;211 selected owner blobs,
15 frozen copies and35 original reviewed inputs verify.70 new synthetic
bootstrap/transaction/view/execution checks do not close any RQ gate criterion.
No actual service, bootstrap transaction,9-control E1 run, catalog, recovery,
correspondence or RQ report/ACK executed. Full access runner and exact integration
FREEZE ACKs remain pending; E1 WORKING, E2/E3 waiting on actual E1, F/G locked.
Evidence evaluation/evidence/e1/bootstrap-executor-20261008/.

## C-E1 public access runner FREEZE request —2026-10-08 UTC

411 evaluator unit/process checks pass on74 stable explicit inputs. Complete
public runner is implemented, but both exact A3-0027 plan ACKs are absent and CLI
refuses startup. No real nine-control E1 run, catalog/recovery/formal correspondence
or research gate result. E2/E3 wait on actual E1; F/G locked; no checkbox changed.
Evidence evaluation/evidence/e1/access-runner-20261008/.


## 2026-10-08 UTC /2026-10-09 IST — partial live E1 / renewed FREEZE

A1-0037/79dacb0 and A2-0018/c8d89d8 exact A3-0027 ACKs verified. Actual paper-strict3/3 passes; CLI2/FAILED before paper-minimal startup due Agent3 TIME_WAIT port probe. Source stable, owned services stopped. Minimal fix RED→GREEN/full414 tests; no full E1 success, catalog/recovery/formal/RQ gate result. A3-0028 releases original freeze; A3-0029 requests revised 78e195f57872e0732394e3c546f665e1062b4a360083d2ee0a407d5def33b008 plan with same owner pins/configuration. Both new exact ACKs required; old ACKs rejected. E2/E3/F/G remain gated; no checkbox changes. Evidence evaluation/evidence/e1/port-recovery-20261008/.


## 2026-10-08 UTC /2026-10-09 IST — actual C-E1 completed

**Current checkpoint2026-10-08 UTC /2026-10-09 IST:** C-E1 COMPLETE: actual fresh two-chain/service controls9/9 across paper-strict, paper-minimal and repaired-e; CLI0/E1_CONTROL_PASS in356.061s. Exact A1-0038/2f5e376 and A2-0019/6d2c867 ACKs verified for A3-0029/78e195f5.. before services. Sources stable; all9 owned PBC/DBC/adapter processes exit0/absent. A3-0029 RELEASED after completed run. E2/E3 now permitted within E/RQ1; all56 catalog schedules and every RQ gate remain NOT_RUN, four paper crash cases BLOCKED/unproved; F/G locked. Evidence evaluation/evidence/e1/integrated-controls-20261008/README.md. This paragraph supersedes prior milestone status below; prior evidence remains historical.

This completes the PLAN C-E1 acceptance slice and permits E2/E3 within RQ E. No composite RQ gate checkbox is closed by E1 alone: identity/adversarial, repair/mutant, durable recovery, formal correspondence, report and same-manifest three-agent ACK evidence remain. Wrong-admin16 is baseline issuer restriction. Paper zero grant recipient plus registered-key symbolic response is D35/A38; repaired-e uses signed bindings/checkpoint and consumed nonce. This is a tested reconstruction result, not a new paper-supported security guarantee. No source/ABI/wire/dependency/key-custody change or blanket acceptance of later owner E2 tools. Exact E2 owner READY/hook RFC requested in A3-0031; no automatic gate or hook approval.


## C-E2 symbolic/start-contract checkpoint —2026-10-09 IST

C-E2 formal signature slice executed: full user/witness eight-field agreement true; positive path reachable, denied-data path unreachable; destination-omitting deliberate mutant has concrete counterexamples and remaining-field agreement.7 formal/sensitivity checks; final root421 tests0/80 stable inputs. Fixed synthetic names/non-injective/honest-key/witness abstraction; no mutable nonce/trust/recovery/encoding/implementation proof. Evidence evaluation/evidence/e2/formal-and-hook-review-20261009/README.md. All56 real Agent3 fault schedules and gate E remain NOT_RUN; four paper crash cases BLOCKED/unproved; F/G locked. No active service/freeze/lease. Exact offered owner303 blobs checked; A3-0032 both scoped ACKs pending and is not an integration FREEZE. Existing E1 evidence/pins/frozen copies immutable.


## Current checkpoint — actual C-E2 logical recovery slice, 2026-10-09 UTC

Six of six exact A3-0035 approved pre-expiry comparisons PASS; actual CLI0 /
E2_RECOVERY_SLICE_PASS /778.4734255s. A1-0048/83c084c/d678342b.. and
A2-0028/902a95b/7d2e9136.. exact plan4bceffc3.. ACKs verified before services.
111 bracket inputs stable;78 plan inputs/303 owner blobs reverified;12 snapshots/
1818 owner-file comparisons stable;15 frozen copies exact. All24 owned processes
ended/absent:18 normal exits0,6 natural crash exits86;3709 captured commands0.
A3-0035 RELEASED, no active services or lease. Evidence:
evaluation/evidence/e2/recovery-live-20261009/README.md.

Measured native permission/cache/intent/send-attempt/restart/original-expiry/
registered-recipient/one-outcome joins and allow/deny/wrong-admin controls across
strict/minimal/repaired profiles. Deliveryunknown; paper crash classification
BLOCKED/unproved, repaired-e supports bounded logical checks only. Author review
found separate catalog expired-retry trials NOT_RUN; six catalog cases partially
exercised, other50 untouched. No duplicate-outcome/full-matrix/mutant/window/report/
RQ gate claim. GateE NOT_RUN/F-Glocked; old frozen bytes/E1/formal evidence preserved.
141 newest communication/no divergence, post-run fetch delta empty; read A1through
0048/A2through0028. No source/tool/dependency/key/custody change; historical472 unit
suite not rerun. Raw/private/snapshots external, selected public/redacted evidence
published only on reviewed exact owned paths; publication SHA/remote and finally
scheduled guard505315/coordinator505507 cleanup in automation memory/external run
/home/karma/.codex/automations/ris-agent-branch-monitor-and-continuation/runs/20261009T001322Z.

Next: explicit expired-retry refusal/no-event checks and remaining50 scenarios,
mutants/revocation windows under a new complete source/tool/config plan/both ACKs;
report/all3 same-source ACKs/gate E before F. No human action needed. Author
self-review only under human ban on extra agents/worktrees; rulings/costs in evidence
README. No peer source/mailbox/archive/frozen/main/destructive Git change.


## Current checkpoint — C-E2 expiry runner awaiting exact ACKs, 2026-10-09 UTC

A3-0037 requests NEW recovery+expired-retry plan `a76a291d3790370018707496fcda2048833ba1e826031bf2a2c0c427b5afe03e`;
both exact new peer ACKs absent. Implemented independent expired original-grant
refusal/no-worker-or-native-change probe; synthetic RED/GREEN, final495 root tests
pass/exit0 with71 Python inputs stable;79 plan inputs/303 owner blobs/
15 frozen copies verified. Actual no-ACK CLI2/BLOCKED before services. No new
integrated expiry result; prior6 pre-expiry rows only partly exercise catalog.
A1-0049/A2-0029 scoped reviews read, no discrepancy; repaired-e4s caution retained.
No active services/lease. A3-0035 RELEASED; A3-0037 REQUESTED, not accepted.
E/RQ1 active; E0closed/C-E1 historical9/9complete/E2-E3permitted; gateE NOT_RUN,
F/Glocked. Four paper crash cases BLOCKED/unproved, deliveryunknown/symbolic.
Evidence: evaluation/evidence/e2/expiry-runner-20261009/README.md. Next: both exact
A3-0037 ACKs, source verification, fresh live6 expiry probes; remaining50/mutants/
windows/report/same-source three-agent ACKs/every E criterion beforeF. No human
input needed; no new source/tool/custody/interface choice beyond pending plan.


## Current checkpoint — actual C-E2 recovery and expiry slice, 2026-10-09 UTC

Actual CLI0/E2_RECOVERY_EXPIRY_SLICE_PASS: 6/6 complete approved recovery+EXPIRED/no-change comparisons, 779.772s. Exact A1-0050/38e0a95/335623fc.. and A2-0030/3d60b40/7d37b9ac.. ACKs of plan a76a291d.. verified before services. Fresh chain pair/state per row; Alice allow/recovery/outcome, Bob policy9 denial, wrong-admin16 controls. Sources stable;79 plan inputs/303 owner blobs/15 frozen copies, 12 snapshots verified; all24 process records ended/PIDs absent, 3943 commands/0 nonzero. A3-0037 RELEASED; no services/lease. Evidence: evaluation/evidence/e2/expiry-live-20261009/README.md.

Explicit original-expiry cached retry returns EXPIRED with entire worker log/cache/attempts and native grant/request/outcome/all contract logs unchanged. Deliveryunknown/symbolic/safe-ledger/trusted-worker; four paper classifications BLOCKED/unproved; repaired-e bounded mechanics only. No first restart at expiry/equality/power-loss/OS-kill/ABE/consensus/full-matrix or RQ gate claim. Other50 schedules/live mutants/windows/report/all3same-source ACKs/everyE criterion remain; E/RQ1 active, F/Glocked. Historical frozen/E1/formal evidence unchanged. Read A1through0050/A2through0030; no new module/source/tool/custody/interface choice. No human action needed.

Operational sequencing lapse: initial service startup before persistent coordinator guard; no Git writes/source movement during interval. Scheduled guard held throughout; record preserved, next run acquire coordinator before services. Author self-review weaker than independent under no-extra-agent instruction. Only reviewed exact owned paths/normal agent-3 push; publication and finally cleanup in external run20261009T011322Z/memory. Next: remaining50 independent public runner/oracles/mutants/windows and new complete FREEZE/both exact ACKs, then report and gateE.

## Current checkpoint — duplicate outcome runner awaiting exact ACKs, 2026-10-09 UTC

State: WAITING for exact A3-0039 full-plan ACKs; E/RQ1 active, C-E2/E3 permitted, F/G locked.

Independent duplicate-outcome collector/public runner implemented. Final531 root tests PASS/exit0; 93 sampled inputs stable,83 plan inputs/303 owner blobs/15 frozen copies verified. Synthetic RED21→GREEN34; mined-call review RED9→final whole-suite531. Actual no-ACK CLI2/BLOCKED before cases/services/snapshots. No new live catalog case; historical6 recovery/expiry rows remain, remaining50 schedules including duplicate3 NOT_RUN. GateE NOT_RUN.

A3-0039 plan `5ef10dc694b0c22c5f8f46fe2a71d89b99319bd527da8a240285659f5871169a` requests fresh3 production-adapter comparisons: wrong-admin16/Alice allow+one outcome, identical mined outcome call/fresh tx nonce/status0/Rejected8+entire native/worker/log no-change, then Bob policy9 denial. Exact pins unchanged; symbolic/safe-ledger/trusted-worker; no delivery/paper durability/ABE/consensus/gate claim. A1-0051/be91a24 and A2-0031/39fbeb4 historical evidence reviews read/no discrepancy in scopes; no report/plan ACK inferred.150 communication paths/no divergence/post-test fetch unchanged.

Evidence: evaluation/evidence/e2/duplicate-runner-20261009/README.md. No active service/lease; A3-0037 RELEASED, A3-0039 REQUESTED. Scheduled/coordinator guards held from prefetch through publication; cleanup finally externally recorded. Both exact new ACKs before live3; then remaining schedules/mutants/windows/report/all3same-source ACKs/everyE criterion. No human action needed. Author self-review only under no-extra-agent rule.


## Current checkpoint — actual C-E2 duplicate outcomes, 2026-10-09 UTC

Actual CLI0/E2_DUPLICATE_OUTCOME_SLICE_PASS: 3/3 fresh profile comparisons in 365.374s. Exact A1-0052/b3cfb15 and A2-0032/fbab2f2 ACKs of A3-0039 plan5ef10dc6.. verified before services. Identical mined outcome call/fresh nonce/status0/Rejected8/no whole native-worker-log change; wrong-admin16/Alice allow/Bob policy9 controls. Sources stable:83 plan inputs/303 owner blobs/118 bracket inputs/15 frozen copies/six snapshots. All9 owned processes exit0/absent;1829 captured commands exit0. A3-0039 RELEASED; no services/lease. Evidence: evaluation/evidence/e2/duplicate-live-20261009/README.md.

Tested reconstruction duplicate outcomes: paper SUPPORTED, repaired-e REPAIR_SUPPORTED; no authors-implementation/delivery/ABE/consensus/power-loss theorem. Historical6 recovery/expiry rows preserved; four paper crash classifications BLOCKED/unproved. Other47 schedules/live mutants/windows/report/all3same-report-source ACKs/every gateE criterion remain; E/RQ1 active, E0closed/C-E1complete/E2-E3permitted, F/Glocked. No source/tool/custody/interface change; historical531 unit tests not rerun as live evidence. Read through A1-0052/A2-0032; no human action needed. Scheduled/coordinator guards held before fetch/services/publication; finally cleanup/publication recorded in external run 20261009T021359Z/memory. Author self-review only, weaker than independent review.


## Current checkpoint — E01 replay runner awaits exact ACKs, 2026-10-09 UTC

A3-0041 requests NEW three-profile identical-request replay plan `a7732650007e9b06a3de49bbe5cc36c1baed674f67eb4e947da9cbbef851d652`.
Independent E01 oracle/public ACSC collector implemented: one prior allowed grant,
identical application calldata/fresh relay transaction nonce, mined status0/Rejected8/
no logs, entire request/grant/nonce/access count/worker/both-chain history unchanged.
Probe precedes first release; original Alice release/completion/outcome plus Bob
policy9 and wrong-admin16 controls remain mandatory. Paper nonce stays false;
repaired-e nonce already true. No new request reference, clock advance, worker
operation, crash or restart during replay. Unexpected expiry fails visibly.

Fresh584 evaluator tests PASS/exit0;99 bracket inputs stable;85 plan inputs/303
owner blobs/15 frozen copies verified. Actual no-ACK CLI2/BLOCKED before services,
cases or snapshots. Both NEW exact A3-0041 execution-plan ACKs absent. No new live
E01 trial; historical6 recovery/expiry+3 duplicate outcomes preserved; remaining47
schedules/live mutants/windows/report/all3same-report-source ACKs/everyE criterion
remain. E/RQ1 active; E0closed/C-E1complete/E2-E3permitted; gateE NOT_RUN/F-Glocked.

A1-0053/8c991dec and A2-0033/e6a8927a reviewed: no discrepancy in their stated
scopes. Equal idle worker logs in duplicate/replay stages are NOT worker retry
or idempotence evidence. Peer reviews are not report/plan ACKs. No interface/tool/
dependency/custody/owner-pin change; author self-review is weaker than independent.
Evidence: evaluation/evidence/e2/nonce-replay-runner-20261009/README.md.

Scheduled stale-lock recovery documented: old PID803334 absent, age5400+ seconds;
metadata preserved externally and decision retained. New scheduled guard and
separate coordinator held before fetch and through publication. No live services
or lease; A3-0039 RELEASED/A3-0041 REQUESTED. No peer source/mailbox/archive/frozen/
main edits, extra agents/worktrees or destructive Git. Publication SHA/remote and
finally cleanup recorded in automation memory/external run20261009T041355Z.
No human action needed; next exact peer ACKs, verify sources/tools, run fresh3
replay comparisons, then remainingE work. Original timing caveat remains.


## Current checkpoint — replay attempt FAILED at repaired release, 2026-10-09 UTC

Actual CLI2/FAILED in 341.181s. Paper-strict/minimal complete PASS; repaired-e replay subcheck PASS then first release EXPIRED; completion/outcome/Bob NOT_RUN. No three-profile success. Original expiry1791521422; probe10.210406s, release04:50:22.053340UTC at corresponding wall-clock second; worker effective-clock equality not directly measured. Failure preserved, no TTL extension. Exact A1-0054/194379c+A2-0034/ca1b8ce ACKs of A3-0041 plana7732650.. verified before services. A3-0041 RELEASED/no services/lease. Evidence evaluation/evidence/e2/nonce-replay-live-20261009/README.md.

All3 identical ACSC replays mined status0/Rejected8/no logs/whole request-grant-nonce-access-worker-both-history unchanged; grant uniqueness precedes nonce check. Paper2 catalog SUPPORTED as tested reconstruction; repaired composite BLOCKED/incomplete, different-digest same-(gid,nonce) controls unrun; idle-worker equality not retry/idempotence. Wrong-admin16 all3/Alice+Bob paper2 pass. Sources stable:85plan/303owner/121bracket/15frozen/six snapshots;9processes ended0/PIDs absent;1667commands0, CLI2 retained. Post-stop worker exporter same empty log; no full native post-refusal claim.

Historical6recovery-expiry+3duplicate preserved; paper2replay complete/repaired1incomplete/other44untouched:45 comparisons remain. Fourpaper crash classes BLOCKED/unproved; live mutants/windows/report/all3same-source ACKs/every gateE criterion remain. E/RQ1 active/E0closed/C-E1complete/E2-E3permitted/F-Glocked. Deliveryunknown/symbolic/safe-ledger/trusted-worker/no authors-implementation/ABE/consensus/power-loss theorem. ReadA1through0054/A2through0034,159communication/no divergence/postrun fetched branches unchanged. No runtime/tool/custody/interface change; historical584 unit tests not rerun. Author self-review weaker than independent.

Scheduled+separate coordinator held before fetch/services/publication; finally cleanup/publication external20261009T044325Z/memory. No human input/peer module repair needed. Next owned runner timing revision preserving snapshots/original expiry; RED/GREEN/source-complete new FREEZE/both exact ACKs before services, then remainingE/report/gateE.


## Current checkpoint — grouped replay completed, 2026-10-09 UTC

Actual CLI0/E2_NONCE_REPLAY_SLICE_PASS: 3/3 fresh comparisons PASS in 375.185s. Exact A1-0056/d89fc843/9bac585b.. and A2-0037/6ce46bd6/0c309f16.. ACKs of A3-0044 plan1b3cf7cd13ea8b1436396f8cc6268bbbdcae753661730290043ee144c1804a32 verified before services. A3-0044 RELEASED; no services/lease. Historical failed nonce-replay trial retained unchanged; no expiry extension. Probes: paper-strict 7.074894s, paper-minimal 6.999435s, repaired-e 6.995111s. Wall timing is not direct worker effective-clock margin.

All3 identical ACSC calls/fresh transaction nonce/mined status0/Rejected8/no logs; entire request/grant/nonce/access/idle-worker/both-history unchanged. One explicit block per chain/snapshot and individual ABI/calldata/return rows checked. Original Alice release/completion/one outcome plus Bob policy9 and wrong-admin16 pass all3. Existing grant uniqueness precedes nonce checking; distinct-digest same-(gid,nonce) and new-reference stress unrun. Equal idle-worker logs are not worker retry/idempotence. Paper-derived/symbolic/safe-ledger/trusted-worker; deliveryunknown/no authors-implementation/ABE/consensus/power-loss theorem. Boundary identity cannot detect transient drift restored between checks.

Sources stable:86 plan inputs/303 owner blobs/123 bracket inputs/15 frozen copies/six snapshots. All9 owned processes ended0/PIDs absent;1841 captured owner/RPC commands exit0, mined negative receipts retained.167 latest communication paths/no divergence. Historical599 unit tests not rerun; actual integration and read-only audit provide this run's evidence. Author self-review only under no-extra-agent rule, weaker than independent. Evidence: evaluation/evidence/e2/grouped-replay-live-20261009/README.md.

Historical6 recovery/expiry+3duplicate preserved; replay 3complete; 44 catalog comparisons still need completion. Four paper crash classifications BLOCKED/unproved. Live mutants/windows/RQ1 report/all3same-report-source ACKs/every E criterion remain; gateE NOT_RUN/F-Glocked. No human input or peer source repair needed. Next: earliest remaining E01 public runner/oracle schedule, preserve controls, full revised plan and BOTH new exact ACKs before services. Scheduled exclusive guard plus separate coordinator held before fetch/services/publication; finally cleanup/publication external20261009T061325Z/automation memory. No peer/module/mailbox/archive/frozen/main edits or worktrees/extra agents; preexisting untracked scheduled-runs preserved unstaged.


## Current checkpoint — subject oracle code corrected, 2026-10-09 UTC

C-E2 WORKING. Exact A1-0058/e66eeb91/1e3644dd.. identified a real evaluator
error: frozen WRONG_SUBJECT is `2`, not `3` (WRONG_DESTINATION). Fixed the oracle
and mirrored fixture; wrong-code control now supplies `3`. Test-first RED:
2 failed/69 passed; GREEN71; fresh root670 PASS/exit0 in108.89s,106 inputs stable.
Post-suite303 selected owner blobs/15 frozen copies verify. Earlier subject
preparation prose using `(3)` is superseded; historical raw evidence is preserved.

No new live subject collector, integration, release or gate result. E0closed/
C-E1complete; gateE NOT_RUN/F-Glocked;44 comparisons remain/four paper crash
classes BLOCKED. No services, execution FREEZE or lease. A1 review is not a plan
or report ACK; no peer module repair or human input needed. Next: public subject
collector in separate fresh stress/control states, recipient/symbolic completion,
complete revised plan/FREEZE/BOTH NEW exact peer ACKs before services.

Evidence: evaluation/evidence/e2/subject-code-fix-20261009/README.md.172 latest
communication paths/no divergence; final fetched peer tips unchanged. Frozen/
ABI/owner/tool/dependency/custody bytes preserved. Author final review under
no-extra-agent rule; scheduled+separate coordinator guards through publication,
finally cleanup/verified remote commit in automation memory. A3-0047 responds to
A1-0058 with the correction; no execution ACK requested. Preexisting untracked
scheduled-runs preserved unstaged; only reviewed owned agent-3 publication.

## Subject pre-release collector checkpoint —2026-10-09 UTC

Fresh root690 tests pass;124 complete runtime/fixture/config/Python inputs stable,
303 selected owner blobs/15 frozen copies verified. This is a public collector
with synthetic native inputs only; no subject release/completion, fresh integrated
controls or live full case. All gate checkboxes unchanged.44 catalog comparisons
remain; gateE NOT_RUN/F-Glocked. Next routing/completion/separate controls and full
new execution FREEZE/BOTH exact ACKs before services. Evidence:
evaluation/evidence/e2/subject-collector-20261009/README.md.


## Current checkpoint — subject completion checker prepared, 2026-10-09 UTC

C-E2 WORKING. Added independent paper-profile routing/completion checker:
recheck pre-release subject facts; require Bob registered nonzero key distinct
from Alice, unchanged native zero recipient/original pending Alice request,
response/token/cache/native-grant/record joins, one fresh intent/send strictly
within original expiry, Bob symbolic completion and Alice WRONG_SUBJECT refusal.
Release and both completions preserve whole native histories/nonces/count; both
completions leave the worker unchanged. No outcome is fabricated for Alice.

Tests-first missing-feature RED87 -> GREEN87. Fresh root777 PASS/exit0 in117.25s;
190 suite inputs unchanged. Six deliberate in-memory check-removal controls admit
false facts which the real checker rejects. Script import-path failure retained;
corrected invocation passes.303 selected owner blobs/15 frozen copies verified.

No live subject release/completion, collector extension, fresh integrated controls,
new FREEZE or lease.44 catalog comparisons remain/four paper crash classifications
BLOCKED/unproved; gateE NOT_RUN/F-Glocked. Next: public completion collector with
authenticated registered keys/ciphertext and same-response Bob/Alice key-reference
calls; separate fresh Alice/Bob/wrong-admin deployments; complete revised execution
plan/FREEZE and BOTH NEW exact owner ACKs before services. Old plan ACKs cannot
cover these new evaluator bytes. This pure checker is not a completed E01 case.

Evidence: evaluation/evidence/e2/subject-completion-oracle-20261009/README.md.
174 latest communication paths/no divergence; fetched peers e66eeb91/96ebe160
unchanged; read A1through0058/A2through0038. No new ACK inferred or requested,
owner source/ABI/frozen/dependency/custody change or human action needed. Author
review under explicit no-extra-agent rule is weaker than independent. Scheduled
exclusive guard + separate coordinator held before fetch through publication;
finally cleanup/publication recorded externally and in automation memory.
Preexisting untracked scheduled-runs preserved unstaged; exact owned agent-3 only.

## Solo-phase checkpoint: SL1 subject substitution actual, 2026-10-10 IST

Recorded by agent 3 (proxy) under the human solo directive A1-0059. **Correlated self-review**: agent 1 and both proxies are the same model.

**Run:** exit 0, `E2_SUBJECT_SUBSTITUTION_SLICE_PASS`, 3/3 rows, 255.73 s.

- Plan 6fd5809b..; FREEZE S3-0005; ACKs A1-0062 and S2-0004, verified by the evaluator's solo verifier before services.
- Each row used a fresh two-chain pair, PBC 18545 / DBC 18546 (chain IDs 18545/28545).

**Results:**

| Profile | Class | Observed |
|---|---|---|
| paper-strict | SPEC_GAP (CONDITIONAL) | Grant for the relay-asserted gid Bob, built from Alice's credentials; the response is routed to Bob's registered key (D35/A38); Bob decrypts, Alice gets WRONG_SUBJECT; no outcome |
| paper-minimal | SPEC_GAP (CONDITIONAL) | Same as paper-strict |
| repaired-e | REPAIR_SUPPORTED | `Rejected(2)` WRONG_SUBJECT; nothing changed |

**Controls:** wrong-admin (16), Alice allow with one outcome, and Bob policy denial (9) all passed. The stress ran on a fresh second deployment on the same chain pair.

**Integrity:**
- Sources were stable.
- All 12 owned processes exited 0 and their PIDs are absent.
- All 37 commands and 2983 RPC calls exited 0.

**Status:**
- Catalog progress: 15/56 actual (41 remain). The paper crash rows are classified per D47.
- Still missing: live mutants, the revocation window, RQ1-E.md and the three same-source ACKs.
- **Gate E: NOT_RUN.** F and G stay locked.
- These are tested reconstruction results under compromised-relay stress outside A01, not HMBC exploits.

Evidence: `evaluation/evidence/e2/sl1-subject-live-20261010/README.md`.

## Solo-phase checkpoint: SL2 relay stress run FAILED (runner defect), re-FREEZE pending, 2026-10-10 IST

Recorded by agent 3 (proxy) under the human solo directive A1-0059. **Correlated self-review.**

**Run:** plan d67f1786.. (FREEZE S3-0007; ACKs A1-0065 and S2-0008) gave exit 2, FAILED, 75 s, in row 1, before any stress transaction.

- The D1 controls passed: wrong-admin (16), Alice allow with one outcome, Bob deny (9).
- D2 was deployed and bootstrapped.
- The D2 worker export was then refused, because the worker database is created lazily (D49).

**Classification:** an evaluator recipe defect. **0 of the 7 SL2 rows are complete; no classification is claimed.**

**Integrity:**
- Sources were stable.
- All 4 owned processes exited 0 and their PIDs are absent.
- The secret scan found nothing (15 keys and 1 token checked).

**Status:**
- Fixed test-first, without any state-changing workaround, as re-plan b3a02098.. (S3-0009).
- Catalog progress: 15/56 actual (41 remain).
- **Gate E: NOT_RUN.** F and G stay locked.

Evidence: `evaluation/evidence/e2/sl2-relay-failed-20261010/README.md` and `evaluation/evidence/e2/sl2-relay-runner-r2-20261010/README.md`.

## Solo-phase checkpoint: SL2 relay stress r2 actual, 7/7, 2026-10-10 IST

Recorded by agent 3 (proxy) under the human solo directive A1-0059. **Correlated self-review.**

**Run:** plan b3a02098.. (FREEZE S3-0009; ACKs A1-0066 and S2-0009) gave exit 0, `E2_RELAY_STRESS_SLICE_PASS`, 7/7 rows, 544.93 s.

**Results:**

| Row | Class | Observed |
|---|---|---|
| forged tuple, paper ×2 | SPEC_GAP | grant to a reference the PBC never saw |
| forged tuple, repaired-e | REPAIR_SUPPORTED | BAD_SIGNATURE(1) after the honest `eth_call` simulation; same-digest proof |
| new-reference replay, paper ×2 | SPEC_GAP | second distinct grant |
| new-reference replay, repaired-e | REPAIR_SUPPORTED | REPLAY(8) from grant uniqueness |
| same nonce, distinct digests | REPAIR_SUPPORTED | REPLAY(8) at the nonce guard, 24 s margin |

**Controls:** wrong-admin (16), Alice allow with one outcome, and Bob deny (9) all passed. D2 workers were verified never-instantiated (D49).

**Integrity:**
- Sources were stable (bracket 143a3094.., HEAD 6750e02).
- All 28 owned processes exited 0 and their PIDs are absent.
- The secret scan found nothing (15 keys and 7 tokens checked).

**Status:**
- Catalog progress: **22/56 actual (34 remain).** The paper crash rows are classified per D47.
- Still missing: live mutants, the revocation window, RQ1-E.md and the three same-source ACKs.
- **Gate E: NOT_RUN.** F and G stay locked.
- The repaired-e forged-tuple recipe difference (A1-0065) is disclosed in S3-0010.

Evidence: `evaluation/evidence/e2/sl2-relay-live-20261010/README.md`.

## Solo-phase checkpoint: SL3 audit stress actual, 6/6, 2026-10-10 IST

Recorded by agent 3 (proxy) under the human solo directive A1-0059. **Correlated self-review.**

**Run:** plan d768463d.. (FREEZE S3-0011; ACKs A1-0068 and S2-0011) gave exit 0, `E2_AUDIT_STRESS_SLICE_PASS`, 6/6 rows, 459.88 s.

**Results:**

| Row | Class | Observed |
|---|---|---|
| dropped outcome, paper ×2 | SUPPORTED | PENDING after one release, routed per D35/A38 |
| dropped outcome, repaired-e | REPAIR_SUPPORTED | PENDING |
| fabricated outcome, paper ×2 | SPEC_GAP | outcome without any DBC grant |
| fabricated outcome, repaired-e | REPAIR_SUPPORTED | WRONG_PROFILE(21); witness NOT_COMMITTED |

**Controls:** wrong-admin (16), Alice allow with one outcome, and Bob deny (9) all passed.

**Integrity:**
- Sources were stable (bracket 26300d0d.., HEAD 9a4d9a5).
- All 24 owned processes exited 0 and their PIDs are absent.
- The secret scan found nothing (15 keys and 9 release tokens checked).

**Status:**
- Catalog progress: **28/56 actual (28 remain).**
- A1-0068 points 1-3 are stated in S3-0012: outcome without a grant needs the public derived grant id; PENDING is ledger-permanent; the E0-era catalog sentence is superseded by `Worker._recipient_for` (S2-0011).
- **Gate E: NOT_RUN.** F and G stay locked.

Evidence: `evaluation/evidence/e2/sl3-audit-live-20261010/README.md`.

## Solo-phase checkpoint: SL4 receipt controls actual, 7/7, 2026-10-10 IST

Recorded by agent 3 (proxy) under the human solo directive A1-0059. **Correlated self-review.**

**Run:** plan 851896f3.. (FREEZE S3-0013; ACKs A1-0070 and S2-0013) gave exit 0, `E2_RECEIPT_STRESS_SLICE_PASS`, 7/7 repaired-e rows, 601.60 s.

**Results:**

| Row | Class | Observed |
|---|---|---|
| receipt binding control ×3 (requestDigest, gid, dataId) | REPAIR_SUPPORTED | `Rejected(2)` WRONG_SUBJECT for a witness-signed receipt with one bound field changed (TEST-ONLY deviating witness; A40 deliberate deviation) |
| receipt signature control ×3 | SUPPORTED | `Rejected(2)` WRONG_SUBJECT for an altered receipt with the honest signature kept (binding precedes quorum) |
| receipt binding positive | SUPPORTED | honest receipt accepted: OUTCOME(4) log, `AttestedOutcomeRecorded`, status 2 |

**Controls:** wrong-admin (16), Alice allow with one outcome, and Bob deny (9) all passed.

**Integrity:**
- Sources were stable (bracket 04887294.., HEAD 8c7ef72).
- All 28 owned processes exited 0 and their PIDs are absent.
- The D2 worker was verified never-instantiated after every step (42 probes).
- All 3 deviating-witness calls exited 0 and passed the three-way check.
- The never-publish scan found nothing (15 key labels including the witness-1 vector key, and 7 release tokens). Raw tool logs are excluded.

**Status:**
- Catalog progress: **35/56 actual (21 remain).**
- A1-0070 points 1-4 are stated in S3-0014: binding and signature rows differ only in signature evidence; receipt DBC block fields are witness-attested (authorization, not delivery); there is no PBC report deadline; binding rows are A40 deliberate deviations.
- MUT_NO_RECEIPT_BINDING counterparts remain P3 work.
- **Gate E: NOT_RUN.** F and G stay locked.

Evidence: `evaluation/evidence/e2/sl4-receipt-live-20261010/README.md`.

## Solo-phase checkpoint: SL5 trust freshness actual, 6/6, 2026-10-10 IST

Recorded by agent 3 (proxy) under the human solo directive A1-0059. **Correlated self-review.**

**Run:** plan 9e14a148.. (FREEZE S3-0015; ACKs A1-0072 and S2-0015) gave exit 0, `E2_TRUST_STRESS_SLICE_PASS`, 6/6 rows, 531.40 s.

**Results:**

| Row | Class | Observed |
|---|---|---|
| wrong issuer ×3 (every profile) | SUPPORTED | `Rejected(16)` UNAUTHORIZED_CALLER at TMSC.sol:181; baseline caller restriction, not a repair |
| signed-list rollback, paper ×2 | SPEC_GAP | the bootstrap CRL v1 replay is accepted and un-revokes Alice; her request is forwarded with `anchorVersion` 1 |
| signed-list rollback, repaired-e | REPAIR_SUPPORTED | `Rejected(5)` STALE_ANCHOR at TMSC.sol:190 (the list was still valid, so not :192); v2 retained; Alice AccessDenied REVOKED(19) |

**Controls:** wrong-admin (16), Alice allow with one outcome, and Bob deny (9) all passed.

**Integrity:**
- Sources were stable (bracket 2e444340.., HEAD 7eed12d).
- All 24 owned processes exited 0 and their PIDs are absent.
- The D2 worker was verified never-instantiated after every step (24 probes).
- All 6 owner producer calls exited 0 and passed their artifact checks.
- The never-publish scan found nothing (15 key labels including the H1/H2 root keys and the witness-1 vector key, and 6 release tokens). Raw producer logs are excluded.

**Status:**
- Catalog progress: **41/56 actual (15 remain).**
- A1-0072 points 1-4 are stated in S3-0016: wrong issuer is not a repair; STALE_ANCHOR is line 190; the paper rollback un-revokes Alice; CRL only, TempACL not run.
- MUT_NO_VERSION_MONOTONE remains P3 work.
- **Gate E: NOT_RUN.** F and G stay locked.

Evidence: `evaluation/evidence/e2/sl5-trust-live-20261010/README.md`.

## Solo-phase checkpoint: SL6 revocation barrier and expired duty actual, 9/9, 2026-10-11 IST

Recorded by agent 3 (proxy) under the human solo directive A1-0059. **Correlated self-review.**

**Run:** plan 78d6ebfb.. (FREEZE S3-0017; ACKs A1-0074 and S2-0017) gave exit 0, `E2_BARRIER_STRESS_SLICE_PASS`, 9/9 rows, 736.64 s. Host condition: low memory (about 3.2 GiB available, 4.4 GiB swap in use); the host was kept idle.

**Results:**

| Row | Class | Observed |
|---|---|---|
| pre- and post-barrier, paper ×4 | SPEC_GAP | `policyEnf` grants with the request-time records after the PBC revocation; one paper behaviour observed twice per profile (no barrier exists) |
| pre-barrier, repaired-e | REPAIR_SUPPORTED | grant on the unchanged checkpoint: an intentional window (2 s cross-clock, not the measured window) |
| post-barrier, repaired-e | REPAIR_SUPPORTED | `Rejected(6)` STALE_STATE, sequence cause of DV line 87 (decision seq 1, current seq 2) |
| expired duty, paper ×2 | SPEC_GAP | grant at DBC time = duty end (DBC-only clock move) |
| expired duty, repaired-e | REPAIR_SUPPORTED | `Rejected(7)` at step 13: duty end ≤ consume < min(decision, request, checkpoint expiry); 7 s margin |

**A31:** `decisionCollections` was 1 in each repaired row and 0 in each paper row.

**Controls:** wrong-admin (16), Alice allow with one outcome, and Bob deny (9) all passed.

**Integrity:**
- Sources were stable (bracket c86da89e.., HEAD 0d9409e).
- All 36 owned processes exited 0 and their PIDs are absent.
- The D2 worker was verified never-instantiated after every step (49 probes).
- All 9 owner producer calls exited 0.
- The never-publish scan found nothing (15 key labels and the frozen-vector keys, and 9 release tokens). Raw producer files are excluded.

**Status:**
- Catalog progress: **50/56 actual (6 remain: SL7).**
- A1-0074 points 1-6 are stated in S3-0018.
- The MUT_NO_STATE_BARRIER and MUT_NO_RECORD_FRESHNESS counterparts, and the measured revocation window, remain P3 work.
- **Gate E: NOT_RUN.** F and G stay locked.

Evidence: `evaluation/evidence/e2/sl6-barrier-live-20261011/README.md`.

## Solo-phase checkpoint: SL7 wrong destination and expiry boundary actual, 6/6; catalog comparisons complete (56/56), 2026-10-11 IST

Recorded by agent 3 (proxy) under the human solo directive A1-0059. **Correlated self-review.**

**Run:** plan d4fa294e.. (FREEZE S3-0019; ACKs A1-0076 and S2-0019) gave exit 0, `E2_DESTINATION_STRESS_SLICE_PASS`, 6/6 rows, 602.24 s. Host condition: low memory (about 2.8-2.9 GiB available, 3.8 GiB swap in use); the host was kept idle.

**Results:**

| Row | Class | Observed |
|---|---|---|
| wrong destination, paper ×2 | SPEC_GAP | A grants on B's forwarded tuple; A's PBC has no such request (chosen completion, compromised-relay stress) |
| wrong destination, repaired-e | REPAIR_SUPPORTED | `Rejected(3)` at DecisionVerifier step 1 (line 60); step 2 also mismatched; A and B unchanged; cannot kill MUT_NO_DESTINATION_BINDING |
| expiry boundary, paper ×2 | SPEC_GAP | grant at DBC time == `r.expiresAt` (DBC-only pin, verified), expiry `r.expiresAt` + 30 |
| expiry boundary, repaired-e | REPAIR_SUPPORTED | `Rejected(7)` at step 9 (line 74) on equality; `d.expiresAt` == `r.expiresAt` < `cp.expiresAt` |

**Deployment B:** a third deployment on the same chain pair, created by the pinned owner commands. The relay used about 400 ETH after a 1000 ETH reset. Its sha256 is bound into the evidence.

**A31:** `decisionCollections` was 1 in each repaired row and 0 in each paper row.

**Integrity:**
- Sources were stable (bracket 4e359a06.., HEAD f1c1e52).
- All 27 owned processes exited 0 and their PIDs are absent.
- The A and B workers were verified never-instantiated after every step (45 probes).
- The never-publish scan found nothing, including `source-instance/`.

**Status:**
- **Catalog progress: 56/56 actual. Catalog comparisons are complete.**
- A1-0076 points 1-5 are stated in S3-0020.
- **Gate E: NOT_RUN.** P3 remains: the mutant matrix (including MUT_NO_DESTINATION_BINDING detection), the integrated revocation window, the ProVerif publication, RQ1-E.md and the one-command gate.
- F and G stay locked.

Evidence: `evaluation/evidence/e2/sl7-destination-live-20261011/README.md`.

## Solo-phase record: gate E PASS (solo phase); board at F0, 2026-10-12 IST

Recorded by agent 3 (proxy) under the human solo directive A1-0059 and A1-0082 P4-4. **Correlated self-review.**

**Run:** plan c0086019.. (FREEZE S3-0021; plan ACKs A1-0083 and S2-0021), runId `E-gate-20261012`, launched by agent 1, gave exit 0, manifest PASS, 56/56 rows, 4749.50 s (S3-0022). Run HEAD 21b37fb, unchanged before and after; evidence `evaluation/evidence/e3/gate-run-20261012/` (2126 files, evidence commit c2c81d5; never-publish scan 0 hits).

**Reviews and RESULT:** A1-0084 (ledger) and S2-0022 (protocol) found no discrepancy. Gate RESULT S3-0023 names one manifest. RQ1-E.md is final at 69dabfba.. (1338 lines).

**Same-source ACKs (A1-0082 P4-3):**

| ACK | Scope | Message sha256 | Commit |
|---|---|---|---|
| A1-0085 | agent 1: ledger claims and every row | 56b7dc2b.. | 9d3e904 |
| S2-0023 | agent 2 (proxy): protocol and key claims; no blocker | 9b5869f8.. | ed3f99f |
| S3-0024 | agent 3 (proxy): evidence and model; self-sign-off | bc10947e.. | committed with this record |

All three name manifest.json 908fd615.., gate-evidence.json 47e38dd3.., RQ1-E.md 69dabfba.. and HEAD of record 871e218. `git diff --name-only 871e218 HEAD -- evaluation/ interfaces/` was empty when S3-0024 was written.

**Criteria (`evaluation/gate.py` `E_CRITERIA`):** 1-6 and 8 are VERIFIED in `gate-evidence.json`; criterion 4 is human-scoped (A1-0080). Criteria 7 (RQ1-report) and 9 (three-matching-acks) are PENDING in the run output by design and are adjudicated VERIFIED here on the three ACKs. `gate-evidence.json` is not edited; `evaluation/gate.py` stays fail-closed and never emits PASS.

**Decision:** "gate E PASS: solo phase, correlated review, criterion 4 human-scoped (A1-0080), window cited from owner evidence (A1-0081), integrated mutants and window not run"

**Limits carried with the PASS:**
- solo phase: agent 1 and the agent-2/agent-3 proxies are the same model, so no review is independent; S3-0024 is a self-sign-off of agent 3 (proxy)'s own runner, oracles, selection and report;
- single host, low memory; one trial per row; no statistics and no performance claim;
- Anvil without consensus or finality; symbolic adapter (no ABE, no secrecy, no `rotate_epoch`); trusted witness (q = 1) and trusted worker;
- paper crash rows D47: "frozen BLOCKED / decided SPEC_GAP, UNPROVED"; delivery unknown in every row;
- not run: the integrated live mutant matrix (A1-0080), the integrated revocation window (A1-0081; owner measurement A1-0046 cited), the hash-only log mode, TempACL rollback and acceptance at `expiresAt − 1`;
- relay-stress rows are outside A01 and are specification dependencies, not HMBC exploits; no vulnerability count is claimed;
- paper-derived reconstruction, not the authors' implementation; synthetic fixtures only.

**Disclosure:** this PASS is a solo-phase decision. The original agents 2 and 3 may overturn it on return, including D47, D48, D49, the criterion 4 scoping (A1-0080) and the window decision (A1-0081). Pushing `main` is a human decision; agent 1 pushes `agent-1` only.

**Status:**
- **Gate E: PASS (solo phase).** The board is at **F0**.
- **F is not started.** F needs its own plan (PLAN.md §6, the gate F checklist above) and the human's go-ahead for F work. Nothing in F is authorized by this record.
- G stays locked behind gate F.

Evidence: `evaluation/evidence/e3/gate-run-20261012/README.md`; `evaluation/reports/RQ1-E.md`; S3-0023, A1-0085, S2-0023, S3-0024.


## Agent 3 return review — 2026-10-12

Human request: pull all changes, gather context, verify and fix issues. Agent3
fast-forwarded8e5a6dd to consolidated6911478 on agent-3. A1-0086/S3-0023 and
A1-0080..0082 reviewed. Gate E remains the recorded **qualified solo-phase PASS**
for the original pinned report/source; board stays F0, F not started, G locked.
Integrated mutant matrix and integrated revocation-window measurement remain
NOT RUN under the recorded human scope. Four paper crash properties remain
frozen BLOCKED / decided SPEC_GAP, UNPROVED (D47); symbolic crypto/delivery unknown.

Fresh review verifies2112 selected gate artifacts +4 wrapper files,376 result
hashes (264 published/112 ABI blobs reconstructed),4047 historical source blobs,
all56 catalog entries/proofs and exact execution/same-source ACKs. All8 original
native review tools pass56/56 on the published data; original protocol reviewer
reports no problems. This is published-data verification, not a new live gate run
or access to omitted raw RPC/private worker databases. Frozen v1/archive and
pinned ledger/protocol production bytes remain unchanged.

Found and fixed owned evaluator issues: a gate test assumed only Agent1's rebuilt
ProVerif, version commands could fail while being marked verified, and ProVerif
binary/model pins were checked after execution (binary drift could also pass).
Baseline1643 PASS/1 FAIL, new probes RED11 and driftRED1; targetedGREEN15.
Historical gate version commands all exited0 with matching hashes; no recorded
row or report claim was changed. New evaluator source needs a revised exact plan
and affected ACKs before any future integrated service run.

Verification/publication details and final results:
evaluation/evidence/reviews/returning-agent3-20261012/README.md.
No automatic F work or main push. Original Agent2 review still remains distinct
from its correlated proxy reviews. Preexisting scheduled-runs remains untouched.


## Return review completed — 2026-10-12

State: WAITING at F0 for its separate plan/human go-ahead; return review/fixes
complete. Final evaluator1658 PASS/exit0/447.11s,6272 suite inputs unchanged;
protocol1375 PASS/201 deliberate evaluator-type SKIP/exit0, fixtures stopped;
ledger suite and existing owner mutant checker exit0; protocol exports9 match.
Published gate artifact/source/ACK audits and all56 native-row checks pass;
protocol public-evidence reviewer reports0 problems. Signed report/manifest/
criteria and frozen interface unchanged. No fresh full live gate rerun.

Agent3 accepts the recorded qualified solo E closure in its original pinned
scope, with correlated review, human-scoped criterion4/window and all stated
UNPROVED/NOT_RUN limits retained. This review is not a substitute Agent2 ACK.
New evaluator guards/test fixes have fresh unit/regression proof; future live
execution needs revised source/tool plan and both exact affected ACKs.
See evaluation/evidence/reviews/returning-agent3-20261012/README.md and A3-0050.
Only reviewed owned checkpoint on agent-3; no main push/F implementation.
