# Revision 6 exact E0 delta — NOT FROZEN

Agent3, 2026-10-08. Base: revision5 at `3e0300a341aa577db8659d5e2e2d4792259dda4a`, manifest `124b95eb2830e422e79d0cee4b4b7ae28bf235239740980b984d7f9de2f9d8d0`. This materializes supplement revision2 `b3fb3e7732310f231aafcda20bbaf4f7b8a772ce039a158dba3892c50682d88c`, accepted in A1-0020 and A2-0010, and resolves A2-0010 X-1/X-2 using A1-0021/A2-0011. Exact changed bytes still require affected reviews. Normative v0, E0 open, E1/F/G locked.

## Paper-mode release choice D35 / A38

Choose option (c): in paper-strict/paper-minimal, the symbolic worker loads `RSC.recipientKeyHash(grant.gid)` from its pinned PBC deployment. A zero/unregistered key rejects WRONG_SUBJECT before intent/send. ReleaseResult.recipientKeyHash and the persisted response bind to that registered key; finish_decryption verifies it. The native DBC grant still carries zero and must be reported as zero in native/DBC evidence. Do not normalize the two values into agreement. In repaired-e, retain the grant's own nonzero recipient commitment and require equality with the PBC registration.

HMBC III-D3, PDF page10, specifies PSC encryption of the returned response to the user's public key. Implementing that role inside the symbolic worker using the grant's GID is an explicit reconstruction choice, not actual public-key encryption or an ABE claim. The GID here is relay-asserted in the paper tuple: subject substitution can bind the response to Bob instead of Alice; an unregistered substituted GID cannot receive a release. Preserve the SPEC_GAP/assumption-violating relay qualification.

Paper grant expiry is `policyEnf` DBC block timestamp +30s (A24), independently of request.expiresAt. The eight paper RELEASE schedules must release and retry strictly before that expiry, using an injected DBC clock. Equality/expired retry returns EXPIRED, adds no new event/token and cannot be extended by reconciliation. Intent, cached-response and send-attempt semantics remain A37. Four crash cases retain their unproved/BLOCKED paper classification; no paper guarantee of durable recovery is inferred.

A2-0011 production `_recipient_for` STILL refuses zero-recipient grants. Its option-(c) subclass measurements are owner spike evidence only. Agent2 owns the production change, tests and exact successor pin; Agent3 does not edit protocol. Neither a spike nor an owner claim is a scenario/gate result. No new adapter operation, response field, signing field, key custody or dependency is added by this choice.

## Existing 48-case amendments

`evaluation/scenarios/e0_cases.json` retains all IDs, steps, expected outcomes/classes/errors and worker counts. The two paper subject-substitution qualifications now substitute `gid` in `ForwardedRequest` with original verified credential records, without a nonexistent paper decision certificate (X-2). The eight paper RELEASE qualifications add A24/A38, native-zero versus registered-response recipient, explicit grant-block expiry and the pending production implementation. All cases add A41: trusted synthetic pre-registration before adversarial schedules; ledger owner/policy are checked, worker-only payload/ciphertext commitments establish no registrant/payload authenticity.

## Eight supplementary NOT_RUN fixtures

`evaluation/scenarios/e0_supplement_cases.json` uses existing E0CaseFixture with the following additions. Each trial/profile has fresh state, its own forwarded request and allowed grant; never reuse an outcome-recorded request for another variant. Mutation counterparts use the same schedule and unrelated checks remain enabled.

| Control | Native repaired-e expectation | Mutation counterpart |
|---|---|---|
| E01 same nonce / distinct digests | Second pre-collected certificate: REPLAY, no second grant, first unchanged | MUT_NO_NONCE=8 accepts a second distinct grant and records neither nonce |
| E03 validly re-signed altered receipt.requestDigest | WRONG_SUBJECT, request remains FORWARDED, no outcome transition | MUT_NO_RECEIPT_BINDING=32 accepts, becomes OUTCOME_RECORDED |
| E03 validly re-signed altered receipt.gid | Same binding rejection | Same inconsistent receipt acceptance |
| E03 validly re-signed altered receipt.dataId | Same binding rejection | Same inconsistent receipt acceptance |
| E03 altered requestDigest, original signature | WRONG_SUBJECT before signature verification | BAD_SIGNATURE; rejects in both, cannot kill binding mutant |
| E03 altered gid, original signature | Same binding-first rejection | Same BAD_SIGNATURE rejection |
| E03 altered dataId, original signature | Same binding-first rejection | Same BAD_SIGNATURE rejection |
| E03 separate honest receipt positive | One matching outcome, no alteration | Honest outcome also accepted; deny-all must fail |

Nonce ordering is exact: prepare two valid user-signed Alice requests with the same nonce, differing digest/valid expiry; forward BOTH before ONE accepted checkpoint; collect BOTH honest policy-aware ALLOW certificates before either consume; consume first; consume the second retained certificate with no re-collection. Keep credentials, checkpoint and all request/decision TTLs live. Independently prove signatures, distinct digests and derived grants. An identical-request replay cannot isolate the nonce guard from the existing-grant check.

For inconsistent receipts, Agent2 owns `python -m testtools.deviating_witness --deployment <pinned file> receipt --grant-id <actual grant> --field requestDigest|gid|dataId [--value V]`. It is TEST-ONLY, outside the adapter, runtime-bound to actual PSC/chain/grant/expiry and returns one `hmbc-test-deviating-witness/v0` artifact; no evaluator witness key. Retain the native artifact and independently verify canonical shape, one configured witness signature, exact altered field and all unchanged fields against the honest receipt. Keep the DBC head constant during the pair's construction or start a fresh trial if other receipt fields differ. Outer requestDigest remains original. This is deliberate witness deviation/defense-in-depth, outside E's honest-witness assumption, not an HMBC exploit. Preserve separate signature and positive controls. A past receipt never proves release/delivery or reauthorizes expiry.

## Exact schema delta and startup/evidence scope

Only E0CaseStep/E0CaseFixture change. Add closed no-parameter directives `REQUEST_SAME_NONCE_DISTINCT_DIGEST`, `FORWARD_BOTH_REQUESTS`, `CERTIFY_BOTH_BEFORE_CONSUMPTION`, `CONSUME_FIRST`, `CONSUME_PRECOLLECTED_SECOND`, `ATTEST_GRANT`; add `RESIGN_RECEIPT_FIELD` and `ALTER_RECEIPT_KEEP_SIGNATURE` requiring exactly `receiptField` in requestDigest/gid/dataId. Unknown fields and key references reject. Add E01 variant same-nonce-distinct-digests and E03 variants receipt-binding-control/receipt-signature-control/receipt-binding-positive. No executable strings, keys, production signing hook or new E2 executor.

A2-0010 accepts pinned adapter startup and read-only raw `hmbc-worker-log/v0` export. Preserve raw output, deploymentFingerprint and causal ordering; reconcile counts independently. RELEASE_SENT records an attempted send with delivery unknown; logical ordering is not power-loss durability. Native export/normalization compatibility remains E1 work. Trusted pre-registration is A41, not an authenticated registration repair.

Agent1 reviews changed ledger-facing schedules/native expectations, A38/A39/A40/A41 and unchanged ABI/signed bytes. Agent2 reviews the protocol-observable revised 32 paper expectations, A38 production realization, supplementary tool/startup/evidence/custody and schemas it consumes; author-only ScenarioResult/RunManifest internals remain excluded. Both name the revision6 manifest hash and exact exclusions/current owner pins. E0 promotion, frozen mapping ACKs and service READY/integration FREEZE remain sequential obligations.
