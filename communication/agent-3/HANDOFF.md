# Agent 3 handoff — 2026-10-07 corrected ledger READY

**E0 candidates READY FOR REVIEW; Phase 1 incomplete. E1 locked, gate E NOT RUN.**
Current checkpoint: A1-0009 scoped candidate ACK and A1-0010 corrected READY accepted; ledger589a053 reproduced (154 tests). Agent2 still absent. Use the current checkpoint section below; earlier boundary notes are historical. Do not treat module/candidate tests as integrated proof.

## Exact published artifacts and verification

- Candidate: interfaces/proposals/v1/review-manifest.json SHA-256 `e2dde1994fb1146e0df979a955cc2c2ada7ce05e88eb55bf26c26fdf91a815c7`, 16 exact files. Supersedes candidate abbeca1d.. at 14d54aa; normative interfaces/README.md remains v0. A3-0006 requests exact peer ACKs.
- Current evidence: evaluation/evidence/e0/review-a1-0007/checks.json SHA-256 `08a26fa290feed61f024dac17f18a751841f126ca60502d9eb49c9ef6ce0a10e`; source manifest SHA-256 d744c94e12e6254951493e55125d91858e1a32af1a091f1b31287bf79baf61b7. Source hashes stable during commands. Manifest and status/report publication metadata is packaged afterward; runtime/test/fixture inputs are reverified unchanged.
- Commands: `.venv/bin/python -m pytest -q` exit0 / 67 passed; `.venv/bin/python -m evaluation.vectors interfaces/vectors/eip712-agent1-candidate.json --output <evidence>/vectors.json` exit0 / 333 checks, 8 signed vectors, 70 mutations. Recorded fixture validator Python command exit0 / 53 cases (10 valid,43 invalid), zero mismatches. `communication/build_prompts.py --check` and `git diff --check` exit0. Runner `--rq E --profile repaired-e --output <fresh>` and gate `--rq E --run <fresh>` exit2/BLOCKED. Every argv/log/exit/time/hash is in checks.json. Ten new regression cases first failed (10 failed/21 passed), then schema suite31 passed.
- S-1 exact EIP-712 annotations/RoleCertificate signing order; S-2 empty bundle; S-3 zero-GID temporal entries fixed. M-1..M-4 source corrections verified against owner source/paper; map37/assumptions27. No paper vulnerability claim.
- Local versions/paths/executable hashes unchanged in evaluation/toolchain.json: Python3.13.13, uv0.11.11, Foundry1.8.5/solc0.8.37, eth-account0.14.0/jsonschema4.26.0/pytest9.0.2, PV2.05. Shared tool freeze still incomplete. No ABE/TLC work or services.

## Historical review revision 2 boundary (superseded by current checkpoint below)

Agent-1 latest 589a05331a1a9a9cfe99eee2da70b980a44e5317. A1-0007 SHA-256 7489f8ec3b5b196573bb1748ed43faa208802eb9048c384bd878e992d8f61e49 ACKs A3-0002 ledger items1/2/5 only and requests schema/source changes. A1-0008 SHA-256 c42d064ce31a6c482f26640e67d1c541e3681db7239b89147b10e6b2e35aefea supersedes old receipt RFC. Across-branch latest-file commit/hash/ancestry recorded in peer-communication.json; agent-2 still absent.

Current 589a053 manifest: SHA-256 1c4f4fc8679ba8a71179bec7ee09a6b7d597985e915bc8abacd604c6096b327b, 87 Git blobs verified, zero mismatches. HANDOFF still claims the old86/hash4d7802..; no refreshed immutable READY is present. A3-0006 asks for one. Do not execute/adopt newer module until exact READY reviewed. Owner reports154 tests; not reproduced for this revision. Sample deployment TMSC hashes predate the change and need owner redeployment.

Historical executed READY remains f643805/A1-0006, 86 entries/hash4d7802b70d731cf5ba3ac3b38fac32ffddaf0400d5b0e7fccfb9117815bfd577; evaluation/evidence/e0/final-checks/checks.json hashcf1df9402ea4f0b46afa22a986a6b172652b8a277c7e5b32a31a64212f977710. Ledger151/Cast166, six mutants detected, pending E03 failure and trivial PV smoke remain evidence for that snapshot only. evaluation.e0_verify deliberately still rejects newer manifests; it must not be silently repinned.

## Exact receipt ACK and remaining work

A3-0005 ACKs A1-0008 revision2: success-only matching past allowed grant; request/gid/data/destination/grantId/epoch/expiry/set binding; HMBCReceipt/1/PBC/PSC; q=1; late reconciliation; opaque outcome commitment; separate durable intent/send and denial logging. Keep witnessSetVersion1 in E; no F rotation. Existing GrantReceipt schema fields are marked superseded but retained until agent-2 exact ACK; no implementation or freeze. This follows the affected-party contract rule, at the cost of later regeneration.

At review revision 2, pending items were agent-1 exact schema/source ACK and corrected READY (now resolved by A1-0009/A1-0010); current pending items remain agent-2 branch/source/key/credential/dependency/vector/adapter/capability support; operation/result/ScenarioResult/deployment schemas. Agree deployment unsigned values remain decimal strings; measurements may be numbers. Only after complete E0 smoke/reviews/three exact ACKs publish INTERFACE_READY and unlock E1 together. Then implement real runner lifecycle/collector, two-chain+worker controls, E2 correspondence/recovery/repair cases, E3 RQ1 report/gate. F/G remain locked.

## Git/services and review limits

Publish only explicit owned/shared paths on agent-3 with coordinator lock; normal pushes only. No peer module/mailbox edit or merge, no main push. No service/port/PID owned; no integration freeze. Author self-review only (project forbids extra agents). Tested runtime/fixture hashes and output hashes rechecked before publication; current manifest/communications are deliberate metadata revisions. A message is delivered only after verified push. Earlier payload7af866d and publication14d54aa are preserved in history.

Verified publication: payload `d9fb969089ad7a5fa828dc6cb746bf388835497a` normally pushed to origin/agent-3; remote SHA matched and checkout was clean. A3-0005/A3-0006 delivered. Post-push fetch: agent-1 unchanged589a053; agent-2 absent. This two-file metadata update records publication without changing runtime/evidence/candidate hashes. Coordinator lock will be released after its verified push.

## Current checkpoint — A1-0009/A1-0010

Owner file-changing commit e351be5c98c35b0692afeb139623717121a5c14c publishes scoped exact candidate ACK A1-0009 (SHA-256 6f6bf6282e3b23a95e26a2ffee76695a5c488eddd8089994872fe05cffb24521) and corrected READY A1-0010 (SHA-256 7b1152c73be93463c398afa0d952540f03b0c216e86c0cb84bf33e79f5e9d63b). A1-0010 supersedes A1-0006; ledger tree is unchanged from589a053. Previous stale-metadata blocker is resolved. A1-0009 covers non-receipt ledger semantics only, excluding adapter/operation/Scenario/RunManifest/ProVerif and Python test reproduction. Do not count it as a full-interface freeze.

Reviewed87-entry manifest SHA-256 1c4f4fc8679ba8a71179bec7ee09a6b7d597985e915bc8abacd604c6096b327b; pinned snapshot /tmp/hmbc-agent3-peer-a1-0010-589a053 extracted via git archive589a053 ledger. No peer edits/merge. evaluation.e0_verify now deliberately pins A1-0010 and rejects any other manifest. Command `.venv/bin/python -m evaluation.e0_verify --peer-root /tmp/hmbc-agent3-peer-a1-0010-589a053 --output evaluation/evidence/e0/ready-a1-0010` exit0. Exact10 command records/results/hashes in checks.json SHA-256 1b9283db8d6b08d80234e60eacad3067aaa0a981cce7f7e8e93af3a1c795cf8c; tested source hash711da464c61a10caa6f42118c1b19e75f34c87e9ca6e856fbee117ee452cc592; source and peer unchanged during tests. Publication provenance carries exact READY/ACK hashes and command.

Fresh results: owned67/0, independent vectors333/0, ledger154/0, Cast166/0, six mutant suites detected; pending E03 exit1 expected; PV trivial tool smoke0; prompts0; runner/gate2 BLOCKED. Owner15-edit mutation smoke and63-case first-run record not newly rerun. Historical f643805 evidence remains scoped to that snapshot. Stale sample deployments not integrated. Tools/fixtures/assumptions unchanged. No services/formal E proof/integration.

The candidate16-file manifest e2dde199.. and all16 bytes are unchanged, preserving A1-0009's exact ACK. Receipt fields remain superseded pending agent-2 ACK. Agent-2 branch still absent at post-test fetch. Next permitted work: obtain protocol exports/source/dependency/vector/adapter/receipt reviews, complete schemas and exact E0 ACKs; then unlock E1. Phase1 incomplete; F/G locked. A3-0007 publishes this module review; no gate conclusion.

Current verified publication: payload `2cf345c39e831ed5ca33c7fd5d58c98152222452` normally pushed to origin/agent-3; exact remote SHA matched and checkout was clean. A3-0007 delivered. Post-push fetch showed agent-1 e351be5 unchanged and no agent-2 branch. Publication metadata changes only STATUS/HANDOFF; candidate/runtime/evidence bytes remain unchanged. Coordinator lock released after metadata push verification.
