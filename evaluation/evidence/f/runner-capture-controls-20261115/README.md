# Offline runner and signing-capture controls — 2026-11-15

**Classification:** tested reconstruction result using synthetic plan/capture fixtures. The F runner remains preflight-only; this is not an integrated case or service result.

## Controls reviewed and run

Added `test_f_preflight_blocks_duplicate_planned_case_ids` to directly exercise the coverage checker’s duplicate-plan-ID branch. The test duplicates `FL-1` and requires `caseCoverage.status=MISMATCH`, the duplicate ID in the manifest, `servicesStarted=[]`, and all case results `NOT_RUN`. This extends the existing missing-ID and matrix-drift checks.

The same focused run exercised the sealed signing-capture checks: a capture count that disagrees with the separately supplied source count is refused; edits after receipt creation fail the digest check; sequential RPC ID reuse is accepted when sequence numbers correlate; duplicate JSON object keys are rejected by the event join. F preflight also continues to report DRAFT as blocked and does not start services or execute cases.

Command:

```sh
.venv/bin/python -m pytest -q \
  evaluation/tests/test_f_preflight.py \
  evaluation/tests/test_sealed_signing_capture_v1.py \
  evaluation/tests/test_signing_event_join_v2.py
```

Result: 37 passed, exit 0, 14.34s. Runtime: CPython 3.13.13, pytest 9.0.2. Exact output, command, context and source hashes are retained alongside this README; `receipt-sha256.txt` hashes those files.

## Limits

The count and receipt are caller-supplied; they are not authenticated and do not prove that the source counter is complete. A digest detects changes only relative to that receipt. Sequential request-ID reuse is a join-correlation behavior, not service behavior. Runner stages 3–7 remain absent. Plan remains DRAFT; no exact execution FREEZE/role ACKs; all 32 F cases and Gate F remain NOT_RUN; no services or integrated cases were run. This evidence does not prove transcript completeness, runtime signing time, consensus, or production behavior.
