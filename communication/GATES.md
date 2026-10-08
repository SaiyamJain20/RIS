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
