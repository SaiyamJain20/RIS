The additive [v2.1 schema revision](v2.1/README.md) closes the opt-in E carrier's
source inventory after exact A1-0114/A2-0060 proposal ACKs. Its separate
[freeze](v2.1/FREEZE.json) preserves the v2 wire family and original v2 bytes.
Both owner publication receipts are verified in
[the live migration record](../communication/E_SOURCE_CLOSURE_MAPPING.json).
Agent1's exact migrated exporter READY is reviewed; Agent2's consumer mapping
and full source READY remain pending. Frozen publication bytes stay unchanged.

Published successor contract: [v2/FREEZE.json](v2/FREEZE.json) pins the exact reviewed payloads; its acceptance sidecar governs live state. Frozen [v1](v1/FREEZE.json) remains reproducible.

**Live state (2026-11-04):** F0 design accepted after exact A1-0110/A2-0058
freeze ACKs; shared v2 published byte-for-byte from candidate2. Owned implementation
and isolated tests may start. Integrated execution still requires source READY
and separate exact run FREEZE ACKs. All32 F cases NOT_RUN; G locked; historical
qualified E unchanged. See [the live board](../communication/BOARD.md) and [acceptance](../communication/F0_ACCEPTANCE_CANDIDATE2.json).
Earlier status paragraphs below are historical.

**Latest F0 review (2026-11-04):** [Revision8 review](../evaluation/evidence/reviews/f0-a2-revision8-20261104/README.md) independently reproduces three bindings/14profile cases. A3-0068 ACKs D50/wire adapter-response scope; A3-0069 withholds layout ACK on legal effect recurrence and ALLOW-only death checks. Candidate2 awaits Agent2's exact correction/tests. F0 not frozen; all32Fcases NOT_RUN/G locked. Earlier entries below are historical.

**Live F0 status (2026-11-04):** Both exact candidate8 design ACKs are verified. Successor [v2 candidate1](proposals/v2/README.md) is a proposal for mapping review, with explicit profile/q2/export-layout dependencies. No mapping ACK, F0 freeze or implementation/execution authorization; F NOT_RUN/G locked. Frozen v1 and qualified E evidence remain unchanged.

**Live status (2026-10-12):** Qualified solo Gate E PASS recorded;56/56 catalog
rows. Agent3 has returned and pulled the consolidated work. Current review and
new evaluator fixes are in [return-review evidence](../evaluation/evidence/reviews/returning-agent3-20261012/README.md).
The human authorized the shared baseline for F0 planning (D51/A3-0052). Exact F0
matrix/source/interface reviews precede implementation; G locked. Frozen v1 bytes
are unchanged.
Integrated mutants/window remain NOT RUN; correlated review/symbolic crypto
limitations remain. All checkpoint counts and pending text below are historical;
use the live board and return review for current state.

**Current C-E1 checkpoint (2026-10-08 UTC /2026-10-09 IST):** actual fresh two-chain/service controls pass 9/9 in all three profiles after exact A1-0038/A2-0019 plan ACKs. C-E1 complete; A3-0029 released; no active services. E2/E3 now permitted within E; every RQ gate remains NOT_RUN; F/G locked. Frozen v1 bytes are unchanged. Evidence: [integrated-controls-20261008](../evaluation/evidence/e1/integrated-controls-20261008/README.md). Earlier runtime status below is historical.

# Cross-module contract v1

Owner: Agent3. **Frozen bytes; both exact peer mapping ACKs verified. E0 closed/E1 unlocked.** Freeze E0-v1-r6-20261008: [interfaces/v1/FREEZE.json](v1/FREEZE.json) SHA-256`f700292ec7e3b2c8f2b59c7a728a991cd7d6dea2e4a06cea71f6f6c97b9962a2`. F/G remain locked; every RQ gate is NOT_RUN. This is a paper-derived HMBC2020 reconstruction, synthetic fixtures and visibly symbolic E crypto.

The authoritative definitions and byte mapping are [v1/README.md](v1/README.md), [hmbc.schema.json](v1/hmbc.schema.json), [BOUNDARY.md](v1/BOUNDARY.md) and [v1 vectors](v1/vectors/). Exact E0 affected-scope ACKs are A1-0022 and A2-0012 with earlier unchanged-scope reviews. [The live acceptance record](../communication/E0_ACCEPTANCE.md) checks all seven pre-publication rows and preserves evaluator-only exclusions. Candidate copies retain their old titles/pending prose to keep reviewed bytes identical; the frozen sidecar supersedes publication status only.

Use decimal-string unsigned integers, lowercase canonical addresses/hashes,65-byte canonical secp256k1 signatures and the exact `x-eip712Type` annotations/order in the schema/vectors. Apply the pinned `evaluation/schema.py` custom width/signature/order/interval checks as well as JSON Schema. Signature recovery, membership, ABI/source matching, checkpoints/expiry and deployment equality require independent runtime checks. E keyEpoch0 and witnessSetVersion1 are fixed; reserved F/G fields authorize no early work.

The JSON-lines envelope has exactly schemaVersion/operation/input/deploymentManifest; response has schemaVersion/ok/result/error with result/error exclusive. The schema associates each operation with its input and result. Eight operations are prepare_request, collect_decision, collect_checkpoint, attest_grant, release, encrypt_record, finish_decryption and rotate_epoch. E rotation refuses NOT_IMPLEMENTED_IN_PHASE. Unknown/noncanonical/extra fields use MALFORMED; deployment binding mismatch uses WRONG_DESTINATION. The frozen Error schema defines the complete vocabulary.

Contract ABIs are owner exports, never hand-written approximations. [FREEZE.json](v1/FREEZE.json) pins six identical ledger/protocol ABI payloads and source inventories. Future local deployments carry their own required RPC URLs, addresses, timestamps and deployBlock; these facts are instance-local and bind that run. Consume public ABI/adapters only. The trusted witness's signed block hash is an observation under safe-ledger assumptions, not a light-client proof.

Request/decision upper bounds30s; checkpoint60s; `now >= expiresAt` rejects. The DBC checkpoint is the revocation barrier for new grants. Checkpoints/certificates use the DBC clock, historical PBC credentials use the checkpoint block/time, and retries never extend the original grant expiry. Past-grant receipts may reconcile after expiry without authorizing release or proving delivery.

In paper profiles, native grant recipient remains zero; D35/A38 symbolic responses use the PBC registered key of grant.gid and refuse unregistered recipients. Relay subject substitution remains a documented specification gap. Paper expiry is policyEnf DBC timestamp+30s. No encryption, ABE secrecy, payload authenticity or power-loss durability guarantee follows. RELEASE_INTENT, attempted RELEASE_SENT and OUTCOME_RECORDED are different facts; uncertain delivery stays unknown.

All56 prospective schedules remain NOT_RUN. Scenario/ScenarioResult/WorkerExpectation/RunManifest internals are author-tested and excluded from peer ACKs. Real C-E1 process lifecycle, native evidence normalization, two-chain service controls and later recovery/formal/RQ gates still require execution.

A3-0021 FREEZE/A3-0022 INTERFACE_READY request exact manifest/commit/byte/version mapping ACKs from both peers. Both exact responses are now verified as A1-0027/70f704d and A2-0013/e30d00d; A-E1/B-E1/C-E1 are unlocked together. [Live ACK/status/successor record](../communication/E0_MAPPING_ACKS.json) supersedes frozen publication-time pending status/nulls; FREEZE.json/copies stay immutable. Future protocol pin e30d00d/98-entry140bb762.. has reviewed v1 export7146495b... Reviewed owner service READY and exact integration FREEZE ACKs are additionally required before actual services. Agent3 owns integrated processes and records their ports/PIDs/source stability in [INTEGRATION.md](../communication/INTEGRATION.md); no services or integration freeze are active now. Main publication is separately unauthorized.
