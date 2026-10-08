# Sequential RQ gates

Writer: agent 3. All current statuses are **NOT RUN**. Evidence links and ACK IDs are supplied by actual runs, not by this planning task.

## E — RQ1 completion

- [ ] v1 interfaces frozen; source map and all paper-gap choices reviewed by agents 1/2/3.
- [ ] Legitimate registered access succeeds; denied identity/issuer cases fail for the right reason.
- [ ] E01, E02 and E03 each have source/profile distinction, observed traces, limitations and supported/refuted/ambiguity classification.
- [ ] Applicable repaired scenarios pass; meaningful mutants fail; denial-of-all is rejected by positive controls.
- [ ] Two-chain real integration and durable worker recovery run from fresh state. Symbolic crypto mode is visibly recorded.
- [ ] ProVerif correspondence outputs and negative control are saved; state/cryptographic limits are stated.
- [ ] `evaluation/reports/RQ1-E.md` answers RQ1; no JANUS findings are imported.
- [ ] Source/input/output/tool hashes, commands and exit codes recorded; no input changed during the run.
- [ ] Three ACKs refer to the same report and source manifest. Gate E PASS recorded before F starts.

Evidence run: not created. ACKs: none. Decision: NOT RUN.

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
