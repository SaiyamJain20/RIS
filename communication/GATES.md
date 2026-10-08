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
