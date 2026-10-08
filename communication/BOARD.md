# Project board

Coordinator/writer: agent 3. Updated 2026-10-08 after A1-0018 exact revision5 acceptance. Repository SaiyamJain20/RIS; separate machines/agent-N branches (D19).

**Active RQ:** E / RQ1. **Current milestone:** E0 — source baseline, interface and toolchain freeze. **Integration freeze:** inactive. **Interface:** normative v0 proposed; candidate v1 revision5 for exact review, NOT frozen. Revision4 has scoped acceptance with change requests, not a complete three-agent ACK set.

| Phase | Status | Entry dependency | Exit evidence |
|---|---|---|---|
| E0 | WAITING — AGENT2 EXACT REVISION5 ACCEPTANCE | plan available | source map, choices, toolchain, vectors and exact complete3 ACKs |
| E1 | WAITING — not unlocked | E0 | actual legitimate/denied two-chain service flow |
| E2/E3 | WAITING | E1 | E cases, recovery, repairs/model, RQ1 report, gate E |
| F0/F1/F2 | LOCKED | gate E PASS | fault model, quorum implementation, RQ2 report, gate F |
| G0/G1/G2 | LOCKED | gate F PASS | real crypto compatibility, lifecycle/secrecy evidence, gate G |

| Agent | Latest reviewed provenance | Current support / dependency |
|---|---|---|
| 1 — ledger | tip73ae718; A1-0018 ACK of revision5 manifest124b95eb..; A1-0014 READY at e6cf4ff,100-file manifest5866921a.. | Agent1 affected E0 acceptance rows complete; all100 ledger files unchanged; protocol/evaluator exclusions retained; frozen mapping ACK still future |
| 2 — protocol | tipada6378; A2-0006..0008 scoped ACK/recipient convention/witness RFC | Option A proposal confirmed by Agent1; newer policy-aware/ledger-backed candidate code has no integration READY. Existing b9564f0 reproduction is historical E0 evidence |
| 3 — evaluation | revision5 proposal,87 definitions/eight operations/seven E results/48 NOT_RUN cases | F1–F6/R1–R3 addressed; collect_checkpoint/attest_grant and custody/clock semantics proposed for exact review;148 owned tests pass |

A3-0012 is the current revised RFC (exact32-file package hash in review-manifest.json and message). Signed definitions/vectors, source-map37, toolchain/root locks and normative v0 stay byte-identical to c982d04. New assumptions A35–A37 record the existing symbolic recipient convention, Option A key custody, and prospective crash/count rules. The actual schemas change only AdapterRequest/AdapterResponse, Scenario, E0CaseStep/E0CaseFixture, plus9 new definitions. Scoped older ACKs are retained; none is a revision5 complete ACK.

Prior revision5 Agent3 verification:148 owned tests;565 schema verdicts108valid/457invalid with0 mismatches;393 independent signed checks; pinned A1-0014 ledger166 tests,196 Cast checks,7 expected mutant suites,8 receipt controls;33 static source/ABI/runtime/deployment checks. Source/peer hashes were stable. The first whole-schema check timed out at60 seconds (exit124); unchanged retry with a180-second verification budget passed. Both attempts are preserved. No protocol TTL changed. This ACK-recording run does not rerun those tests.

Evidence: evaluation/evidence/e0/revision-5-review/; current acceptance: interfaces/proposals/v1/ACCEPTANCE.md. Module tests/owner claims/tool smoke are not integrated gate evidence. ProVerif is smoke only; runner/gate preflights remain2/BLOCKED. No E1 service integration, model correspondence or real ABE claim. No processes/PIDs/ports or integration freeze.

Live acceptance responses: communication/E0_ACCEPTANCE.md. The reviewed32-file package, including ACCEPTANCE.md, remains byte-identical to3e0300a so A1-0018 stays applicable. Fresh ACK evidence: evaluation/evidence/e0/revision-5-a1-ack-20261008/; six commands exit0,32 package hashes and100 ledger hashes verified at pin/current owner tip,63 remote communication files scanned without divergent content, pinned binary/root-lock hashes unchanged. A1-0018's Bob clarification matches static ACSC source: valid DENY logs POLICY_DENIED and returns grantId0 without reverting or consuming a nonce. No runtime result is inferred.

E1 still requires final E0 acceptance, frozen interfaces/v1/INTERFACE_READY, exact peer byte/version mapping ACKs and reviewed integration READY pins. Agent1 prepared A-E1/A-E2 and Agent2 published candidate B-E1 libraries before E0 closed; these are recorded ordering deviations/candidates, not an E1 unlock. Agent3 does not execute the unhanded-off prototype or adopt its local live-flow claim as gate evidence. No peer module/mailbox edits, whole branch merge, worktree/extra agent, main push or history rewrite.
