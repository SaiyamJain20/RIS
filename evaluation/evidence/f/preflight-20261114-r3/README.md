# F runner preflight checkpoint — 2026-11-14 (A3-0128)

**Result: plan validation passes; execution remains BLOCKED.** The runner checks exact source and artifact pins and matches the 32 planned case IDs against the frozen revision-8 matrix. It implements preflight stages 1–2 only. It starts no services, executes no F case, and does not authorize a run. All 32 cases remain `NOT_RUN`; Gate F is `NOT_RUN`; G remains locked.

## Verification

- Full evaluator: `.venv/bin/python -m pytest evaluation/tests -q` — exit 0, **2,977 passed in 722.84 s**. Output SHA-256: `1dc1b64b05d38c390b3c2ddbfadc0c29d9f6712e53e71a849f315643d3aa91e6`.
- Focused runner checks: `.venv/bin/python -m pytest evaluation/tests/test_f_preflight.py evaluation/tests/test_run.py -q` — exit 0, **13 passed in 9.97 s**. Output SHA-256: `2fea0afe65f6db6b5b9af7aea1ed6c38e1d404febb5a9c8eccf4352c66486d56`.
- Final preflight: `.venv/bin/python -m evaluation.run --rq F --profile repaired-f --integration-plan evaluation/evidence/f/execution-plan-draft-20261114/plan-draft.json --output evaluation/evidence/f/preflight-20261114-r3/preflight-final` — exit 2, status `BLOCKED` as required. Manifest SHA-256: `38c04512716e40b3c275031e6146698d02913c1114de4b61aaa51bdcd7b37ae8`.
- Plan SHA-256: `7a212c55b2f4f9fa68f0e4bf6acbac6dc24e6df97ee5ed4f6215efb6b1764ac0`.
- Final source-bracket digest: `0239abec492a384b70738705e6c36a034adda43d46d2ba617365cab290583d5f`; bracket HEAD `702b3c82b154d250c86a3cbf390c15060413d602` on `agent-3`, with the listed worktree changes. This is a pre-publication bracket, not an execution FREEZE.

## What was checked

Coverage is `MATCH`: 32 planned / 32 expected / 32 frozen matrix rows, with no missing, extra, duplicate or out-of-matrix IDs. Exact hash checks all pass for ledger and protocol candidate commits, v2 and v2.1 freezes, v2.1 schema, frozen matrix, coverage CSV, root toolchain manifest, TLC jar and the ledger source-manifest blob. Coverage CSV SHA-256 is `fc090df2f565b2c3f1766f720255f77f4c3fdcc913a3d858f18bab924396985d`.

Owner candidates resolve as:

- Ledger `85c59f588de58a8ff5e87b9fe6f630c9d8c43642`, tree `36a868305d67c8f546e6bde558ceb8e356962819`, ancestor of `origin/agent-1`; source manifest SHA-256 `70f541cd63bb8e8c4c0c1202dda0e5611ab15fde6d1ab4b8a0451497b6fb08dd` (429 entries).
- Protocol `55f180e15d73825870d3326a3edb817824b3f265`, tree `0e59256bd859d347ad416a5ab77099a9a9f2809e`, ancestor of `origin/agent-2`.

These are exact candidate pins, **not execution ACKs**. The root toolchain manifest remains frozen to the E scope; the F-only TLC 2.19 jar is pinned separately at SHA-256 `936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88`.

## Remaining blockers

1. The machine-readable plan is `DRAFT` with `authorizesExecution=false`.
2. Protocol remains a candidate. K1 was detected in 29/40 controlled runs (control 40/40) and agent 2 has not confirmed the A3-0121 signing-rule reading.
3. Only stages 1–2 exist. Stages 3–7, including owner baselines, integrated family runs, signing-time capture joins, post-source bracket, E regression and gate evidence, remain unimplemented or unrun.
4. Agent 1's A1-0129 review was folded into the draft but is not an ACK. Agent 2 has issued no exact execution ACK.

No measured result should be inferred for any of the 32 F cases from these checks.

## A1-0129 plan changes

The revised draft records v2.1 freeze/schema and ledger-manifest pins, exact deployment argument order/template, `repaired-f` and `mutant-f-q2` profiles, `complete-details` logs, chain IDs 18545/28545 and a requirement that witnesses sign for those same IDs, scratch archive deployment, deployment-manifest readback, secret exclusion, and the ledger ACK's checks. It also records the exact `Q.badLists` fixture path and quorum rejection-code precedence, FL-6's `STALE_STATE` expectation, fresh chain pairs for F-24/F-31, F-24 poison isolation, and F-31 `evm_revert` as outside the monotone safe-ledger assumption. Stage 7 chooses the pinned F ledger with `repaired-e` and `SUCCESSOR_EXPORT=1` for the E regression.

## Preserved correction trail

- `../preflight-20261114/` is invalidated: the first checker used the wrong 29-row matrix path. No services or cases ran.
- `../preflight-20261114-r2/` records the first corrected-matrix check, before A1-0129 plan amendments; this r3 result supersedes it.
- `preflight-a1-0129/manifest.json` and `preflight-published/manifest.json` are intermediate post-amendment captures; `preflight-final/manifest.json` is the final source-bracket capture after board/report updates and the last plan refinements.
- `preflight-setup-error.txt` preserves one invocation that exited 2 before preflight because the output directory had already been created. No source/service/case execution occurred in that attempt.
