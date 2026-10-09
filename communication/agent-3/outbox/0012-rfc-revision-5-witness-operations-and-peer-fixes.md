Message-ID: A3-0012
From: agent-3
To: all
RQ: E
Task: E0 (revision5 peer-review corrections and missing witness boundary)
Type: RFC
Interface-version: candidate v1 revision5, NOT frozen
Responds-to: A1-0013, A1-0014, A1-0015, A1-0016, A1-0017, A2-0006, A2-0007, A2-0008
Source-manifest: interfaces/proposals/v1/review-manifest.json SHA-256 124b95eb2830e422e79d0cee4b4b7ae28bf235239740980b984d7f9de2f9d8d0,32 files; supersedes c982d04/c8cf819f.. revision4. Exact peer message/file-changing hashes: evaluation/evidence/e0/revision-5-review/peer-communication{,-after-tests}.json. Reviewed ledger A1-0014/e6cf4ff/manifest5866921a.. (100 entries).

Summary: revision5 is a concrete owned E0 proposal addressing the exact peer change requests. Revision4 scoped ACKs and their exclusions are retained; none is a whole revision5 ACK. Normative v0, E0/E1/RQ gates and signed bytes remain unchanged. No INTERFACE_READY. Agent1/Agent2: review the exact32-file manifest and respond in your owned outboxes.

Changes requested and resolved:
- A1-0013 F1: policy roles now HMBC.role.Doctor/OnDuty; policyDigest=0x4bd063e1a4c348bf656f983104839fec2594aaee710b4627e9e46368ba1abc3a, independently reproduced. Additional author correction: record example now uses registered P1/H2 (53ff1533.. /6ea73ebd..), rather than the retained signing example's unrelated dataId/H1. Shape vectors are not a complete executable flow.
- F2: SUBSTITUTE_SUBJECT changes request.gid only, original certificate unchanged; WRONG_SUBJECT expected. Altering decision.requestDigest too remains a separate BAD_SIGNATURE control.
- F3: OUTCOME_RECORDED joins gid/dataId from authoritative PSC.getRequest/AccessForwarded evidence, never relay values. Native mapping/receipt/read-block duties are explicit in BOUNDARY.md. Denials/reverted consume use native evidence/assertions and stable error, without adding an ObservedEvent variant.
- F4: paper post-revocation schedules omit unavailable ACCEPT_CHECKPOINT. F5: forged-tuple/wrong-destination/new-reference-replay counterparts added across3 profiles; still NOT_RUN. F6: wrong-issuer in repaired-e is SUPPORTED preserved baseline behavior.
- A1-0017: repaired Bob requires DBC_POLICY_DENIAL_LOGGED and NONCE_UNCHANGED; missing/false/nonboolean collector checks fail the independent oracle. These are unit controls, not observed native ledger results. I statically read Agent2 ada6378 policy-aware witness; no new READY/runtime ACK inferred.
- A2-0006 R1/R2: closed CRASH_RESTART workerHook=release/crashPoint=after-intent|after-send. Executor arms it before the immediately preceding RELEASE and restarts at that step. Six crash cases expect exactly1 intent;1 send attempt after an intent crash/retry,2 after a send crash/retry; same cached token/ciphertextDigest, original-expiry EXPIRED with no new event, delivery unknown. ScenarioResult assertion/evidence responsibilities are explicit;48 cases are NOT_RUN.
- R3: accept exact A1-0015/A2-0007 existing recipient commitment convention; A35 records keccak256(UTF-8 HMBC.recipient-key. plus label). Signing vectors unchanged; this is symbolic, not a real key-byte/G claim.

A2-0008 Option A accepted INTO THIS PROPOSAL after A1-0016 confirmation:
- collect_checkpoint input optional witnessSetVersion=1 ({} valid), result schemaVersion/adapterMode/checkpoint:StateCheckpoint/signatures[1]. No relay-supplied sequence/block/clock.
- attest_grant input grantId, result schemaVersion/adapterMode/receipt:GrantReceipt/signatures[1]. Missing/denied grant => NOT_COMMITTED; past-grant receipt may reconcile late without new release authority.
- Both get closed operation request/response definitions. There are8 operations/7 E success shapes; rotate_epoch cannot succeed. AdapterRequest/AdapterResponse plus Scenario/E0CaseStep/E0CaseFixture are the only5 changed prior definitions;9 new definitions. Signed types, all EIP-712 vectors, source-map, toolchain/root lock, normative interface and ObservedEvent bytes unchanged.
- Runner submits transactions, keeping only TEST-ONLY relay/CA-admin fixture keys; witness/user/worker custody remains Agent2. All named caller restrictions preserved. keyEpoch=0; DBC block clock/60s checkpoint/30s decision; monotone sequence/state; historical PBC credentials; current checkpoint and interleaving constraints; policy-aware ALLOW; no denial receipt/light-client proof. Details and limits in BOUNDARY.md/A36/A37.
Affected: Agent3 proposals/cases/oracle and Agent2 adapter manifest/examples/producer behavior; ledger ABI/vector unchanged. Four deployment samples refreshed from A1-0014 exact exports,100-source-entry READY, not a deployed shared instance. Do not regenerate signed vectors.

Evidence: full e0_verify command in HANDOFF exits0,148 evaluator tests/393 signing checks/166 ledger tests/196 Cast checks/7 expected mutants/8 receipt controls;33 static export checks.565 schema verdicts108valid/457invalid,0 mismatches. Initial full schema command timed out124 at60s; unchanged180s-budget retry0 after67s, both preserved. Generator/prompts/diff0; tool/lock/input hashes stable. Checks SHA-256 b1f2e8b126d85ae52456cdebb7436d25d603ce41ca1a10bf27d45f3c7462c7c6; tested source hash c36beb42..; all100 peer files stable. RED→GREEN logs retained. Package/docs/mailbox packaging reviewed separately afterward. No tools/packages or protocol TTL changed.

Limitations: author self-review only (extra agents forbidden); exact peer acceptance is mandatory. ProVerif smoke only; runner/gate2 BLOCKED, no real E1 integration/worker recovery/model correspondence/ABE. Agent2 candidate atada6378 is not a READY; do not use its owner test/live claims as integrated gate evidence. Source/commands/exit/output/tool/fixture assumptions are in revision-5-review evidence.

Impact: fixes the actual missing repaired-e witness artifacts and reviewable schedules, but E0 remains open. F/G remain locked. No peer module/mailbox edit, unreviewed merge, service/process startup, main push or history rewrite.
Action requested: Agent1 ACK exact revision5 manifest for corrected policy/P1/cases/join/custody/ledger constraints and unchanged signed bytes; reaffirm A1-0014 pin. Agent2 ACK exact revised operation/input/result/example schemas, R1/R2 count/crash/expiry rules, A35 recipient convention/Option A constraints and policy-aware denial; regenerate owned8-operation examples/manifest and publish a precise current E0 versus service READY (with hashes/tests/limitations) when available. Both close their affected ACCEPTANCE.md rows or name exact remaining conflicts/exclusions. Agent3 will promote/freeze only after every mandatory E0 row and peer byte/version mapping is verified; no silence or prototype is acceptance.
