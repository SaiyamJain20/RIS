# F runner preflight checkpoint — 2026-11-14 (A3-0128, final)

**Pin and coverage checks pass; execution remains BLOCKED.** The implemented runner covers stages 1–2 only. It starts no services, executes no F case and does not authorize a run. All 32 cases are `NOT_RUN`; Gate F is `NOT_RUN`; G is locked.

## Verification

- Full evaluator: `.venv/bin/python -m pytest evaluation/tests -q` — exit 0, **2,978 passed in 1,183.99 s**. Output SHA-256: `e7fdaa934acc50a2938e88cc32d995a847e55daecf7c165d0892fae09bb2198a`.
- Focused runner tests: `.venv/bin/python -m pytest evaluation/tests/test_f_preflight.py evaluation/tests/test_run.py -q` — exit 0, **14 passed in 16.25 s**. Output SHA-256: `b1ad2f2d018dc1dc6f898628cb5c48d8c1f4f5d3a47648f0c5bb999d7486faed`.
- Final preflight: `.venv/bin/python -m evaluation.run --rq F --profile repaired-f --integration-plan evaluation/evidence/f/execution-plan-draft-20261114/plan-draft.json --output evaluation/evidence/f/preflight-20261114-r4/preflight-final` — exit 2, `BLOCKED` (expected). Manifest SHA-256: `5bc818d3bdb2cdf32af14a48d6235a8b2a2f2db6f62b4ef59681262a2d1e3ef8`.
- Plan SHA-256: `7a212c55b2f4f9fa68f0e4bf6acbac6dc24e6df97ee5ed4f6215efb6b1764ac0`.
- Source-bracket digest: `679b4341168c1886b9e30b8d46e49fa5f5d5ccb1b13e2c08455080e17acb5518`, parent HEAD `702b3c82b154d250c86a3cbf390c15060413d602` on `agent-3`. It records the source files and dirty paths for this pre-publication checkpoint; it is not a final FREEZE or execution authorization.

## Results

- Case coverage is `MATCH`: 32 planned, 32 expected, 32 matrix rows, no missing/extra/duplicate IDs. A test that changes one matrix ID without changing the row count is rejected; before the fix, the regression showed `MATCH`, and after the fix the focused and full suites pass.
- All ten pin checks are `EXACT_MATCH`: ledger commit, protocol candidate commit, v2 freeze, v2.1 freeze, v2.1 schema, frozen matrix, coverage CSV, frozen root toolchain manifest, F-only TLC jar, and ledger source-manifest blob.
- Ledger candidate: commit `85c59f588de58a8ff5e87b9fe6f630c9d8c43642`, tree `36a868305d67c8f546e6bde558ceb8e356962819`, ancestor of `origin/agent-1`; its source-manifest digest is `70f541cd63bb8e8c4c0c1202dda0e5611ab15fde6d1ab4b8a0451497b6fb08dd` (429 entries).
- Protocol candidate: commit `55f180e15d73825870d3326a3edb817824b3f265`, tree `0e59256bd859d347ad416a5ab77099a9a9f2809e`, ancestor of `origin/agent-2`.
- The frozen root toolchain remains unchanged for E. The F-only TLC 2.19 jar is separately pinned at SHA-256 `936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88`.

Exact candidate pins do not count as owner ACKs. Agent 1's A1-0129 review was incorporated into the draft but is not a FREEZE ACK. Agent 2 remains at `9d44754`; K1 detection remains 29/40 controlled runs with a 40/40 control, and agent 2 has not confirmed the A3-0121 signing-rule reading.

## Remaining blockers

1. The plan is `DRAFT` with `authorizesExecution=false`.
2. The protocol source is only a candidate while K1 and A3-0121 remain open.
3. Stages 3–7 remain unavailable or unrun: isolated baselines, integrated cases, signing-time observation joins, post-source bracket, E regression and gate evidence.

No F case result follows from this preflight. The fault oracle has synthetic tests but is not connected to captured signing-time observations.

## A1-0129 plan integration

The draft pins v2 and v2.1 interfaces/schema, ledger manifest, exact owner candidate commits/trees, coverage, root toolchain and TLC. It specifies scratch-extract deploy invocation, profiles, `complete-details` logs, PBC/DBC chain IDs 18545/28545 and matching witness signing IDs, key exclusion from records, deployment-manifest readback, `Q.badLists` rejection-code precedence, FL-6's `STALE_STATE`, fresh chain pairs for F-24/F-31, F-24 poison isolation, F-31 `evm_revert` outside the monotone safe-ledger assumption, owner ACK checks and the F-ledger `repaired-e` regression.

## Preserved correction trail

- `../preflight-20261114/` is invalidated because the first checker used the wrong 29-row matrix path; no services or cases ran.
- `../preflight-20261114-r2/` and `../preflight-20261114-r3/` preserve corrected intermediate checks before the final matrix-ID guard.
- `preflight-final/manifest.json` is the final capture for this checkpoint. Earlier attempts and their exit records remain preserved.
