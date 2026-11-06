# Independently acquired facts bound to signature checks

C-F1 internal evaluator implementation for the paper-derived HMBC2020
reconstruction's F extension. Classification: **tested reconstruction result**
with synthetic fixtures, plus **deliberate mutations**. No original-paper bug,
real-chain observation, owner E parity, integrated F result or gate is claimed.

`evaluation/signing_context_v2.py` provides:

- `verify_bound_certificate(name, message, signatures, *, manifest,
  observations, compiled_max_admins=None)`: independently reconstruct B, derive
  the typed-message destination, ordered membership, version and exact quorum,
  then recover signatures. It also checks embedded checkpoint PBC/PSC and receipt
  DBC/KSSC identities, even when configured keys signed the wrong identity.
- `verify_bound_checkpoint_reports(response, *, manifest, observations,
  compiled_max_admins=None, selected_index=None)`: use the same reconstructed
  context for every pinned/recorded/late/inconsistent retry report and bind its
  signature to the configured indexed owner. The original request supplies a
  pinned report's selection index. This report-only API does not verify the
  success certificate; callers must use the certificate API separately.

Contexts derive from reviewed caller pins and separately acquired observations,
never an export's claimed B or artifact-selected quorum/domain. q2 requires the
q2 deployment; carried E uses its single witness, including the explicit complete
v2.1 E carrier. No existing runner/default v1 consumer, published interface,
dependency, peer implementation, archive or historical evidence was changed.

The tests use independently enumerated synthetic observations, exact owner ABI
fixture copies, real EIP-712/secp256k1 signatures and actual ABI decoding. One
collector-to-signature positive control composes the existing collector with the
new wrapper over injected synthetic RPC, without servers or deployments.

Fresh results: **92 new / 443 focused / 2128 root tests PASS**, root402.84s
(403.10s command), exit0. All238 selected inputs and157 complete execution-source
entries remained unchanged. Seven deliberate bypass controls admitted bad
evidence refused by the original. All31 frozen publication payloads,429 ledger
READY entries and52 protocol F0 pins verified.

Reproduce from repository root:

```bash
.venv/bin/python -m pytest evaluation/tests/test_signing_context_v2.py -q
.venv/bin/python -m pytest evaluation/tests/test_schema_v2.py evaluation/tests/test_certificates_v2.py evaluation/tests/test_binding_context_v2.py evaluation/tests/test_public_observations_v2.py evaluation/tests/test_signing_context_v2.py -q
.venv/bin/python evaluation/evidence/f/v2-signing-context-20261106/sensitivity.py
.venv/bin/python -m pytest -q
```

Actual commands, UTC times, durations, exits and raw/compressed output digests
are in `commands.json`. Logs use lossless gzip; `verify.py` checks their bytes
and verdicts. `inputs-before.json` and `inputs-frozen.json` record exact source,
fixtures, configuration, tools and locks. The frozen bracket includes both the
selected evaluator/interface inputs and **the full discovered E2 execution
inventory**, including evidence Python helpers. All helpers were finalized before
root verification. Current results are recorded in `verification.json` after the
post-run bracket is checked; expected counts alone are not evidence.

Failures are preserved: initial 82 missing-module failures before implementation;
then 27 failures/55 passes caused by a fixture helper flattening intentionally
different retry messages. That helper was corrected to preserve distinct
messages and equal-copy/adoption/timing relationships; production checks were
not changed to accommodate it. The corrected 90-test batch passed, followed by
two additional carrier/no-report controls in the focused batch. Seven in-memory
check removals each admit inputs rejected by the original checker. See
`REVIEW.md` for the correlated author review and exact scope.

`communication-provenance.json` reviews 365 paths by file-changing commit and
ancestry. `peer-review.json` records exact Agent1/2 STATUS/HANDOFF revisions and
the new Agent2 partial worker-binding/marker-classification delta. Agent1's
reviewed source85c59f5/429-entry manifest is unchanged; its 429 hashes, all52 F0
pins and31 publication payloads are checked by `audit.py`. Agent2 remains
explicitly NOT_READY. Its counts are owner claims, not rerun/adopted results.
No new source READY, consumer-mapping ACK or execution ACK is inferred.

Assumptions and limits: caller-pinned observations/build facts may be fabricated;
masked code equality does not attest constructors/source. Valid signatures do
not establish source-state truth, expiry, event membership, request/grant
correspondence, response completeness, exporter chronology, WAL recovery,
durable anti-equivocation, delivery, process independence or consensus. The
seven bypass controls cover selected joins, not every possible fault. Review is
by the author under the no-extra-agents rule and remains correlated.

Next: exporter signed-history/orphan/WAL/native completeness joins, then fault
oracle and finite model. Complete reviewed owner READYs/full consumer mapping
and a separate complete source/tools/config/run FREEZE with exact affected ACKs
still precede integrated services/scenarios. Historical qualified E is unchanged;
all32 F cases/Gate F remain NOT_RUN, G locked. No human action is required.
