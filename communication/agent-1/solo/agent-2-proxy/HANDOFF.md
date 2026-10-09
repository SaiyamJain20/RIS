# agent-2 (proxy-2) handoff: P0, 2026-10-09

## Scope and provenance
- Read-only P0 preparation. Local checkout HEAD 78cdd11 (agent-1, after merging origin/agent-3 and origin/agent-2).
- `git diff origin/agent-2 HEAD -- protocol` is empty, so protocol/** equals agent-2 96ebe16.

Pins I rely on (sha256sum on this host):

| File | SHA-256 | Note |
|---|---|---|
| interfaces/v1/scenarios/e0_cases.json | 438fa38ddcbd7edd0e49fb93cc580e5219ed05349fd677b2e386bc4669f5d50e | |
| interfaces/v1/scenarios/e0_supplement_cases.json | 9ccade362c5a8853d63f06a08be3134ae32cd99527ceb36fcd78c311a9246858 | |
| protocol/hmbc_protocol/worker.py | 204af36906a89521517c88b1314e596e087a303e576cff38836071532bdb8908 | |
| protocol/hmbc_protocol/witness.py | 43c86b1f85bc3220d8bff3ba27728a4fbdde4b502d548762fb8725f50a45ee70 | |
| protocol/hmbc_protocol/adapter.py | 7fa01a39909ee9b94555d5f3c616bc89488d649b4731993ef80e7f4235267ce0 | |
| protocol/testtools/faulty_adapter.py | f0ab2400db5b3667f92ad2e9061b931c8acc94696f42bcd7080e7cdd4e39bde4 | equals the accepted start-contract-r1 hook |
| protocol/testtools/deviating_witness.py | 0511ba571b71d960d8ffbe4b8c811da99ed7de53a4b7515ac425c5291cc3c2d7 | |
| ledger/tools/e2_rehearsal.py | 8c8ecb09cc17171213909fd3c0dd443a67bf003d523b3020f440ffdd91aa5cfd | |
| ledger/E2_HANDOFF.md | b770c8257d2ea5a283ec8e9cfdb619fc6701f07e72e99116884eae9d2d902dd8 | |

## Commands run (all read-only)
- `git log`, `git ls-tree`, `git show origin/agent-{2,3}:<path>` (before the merge) into the scratch dir `/home/saiyamjain/.claude/jobs/aed51961/tmp/p2/`, then local reads after the merge.
- `git diff --stat origin/agent-2 HEAD -- protocol communication/agent-2`: protocol empty. Only the agent-2 ROLE/START_PROMPT differ, and those are agent-3-owned templates.
- `python3 -I` JSON inspection of the two frozen catalog files, plus the revision-5 vs v1 comparison: 48/48 rows have identical steps, outcome, error, classification and worker record.
- `grep -n -i` over references/HMBC2020.txt for crash, retry, atomic, durab, persist, recover, failure and fault.
- `sha256sum` of the files above.

No pytest, forge, Anvil, adapter or service was started. Agent 1 is running the P1 baseline.

## Results (details in outbox)
- **S2-0001:** 44/44 remaining comparisons are runnable on existing protocol code: the production adapter, plus the TEST-ONLY `deviating_witness` for 3 receipt-binding rows.
  - Recipe ambiguity R1: forged-tuple repaired-e. Optional H1 TEST-ONLY decision signer.
  - Owner test gaps T1-T3, all test-only: paper subject routing on both profiles without the silent skip; crash before intent; first restart after expiry.
  - Discrepancies R2-R11.
- **S2-0002:** recommend Option A, reporting the paper crash property as SPEC_GAP (ambiguity) with outcome UNPROVED, through a D-record. Frozen bytes untouched; the mechanics count as a tested reconstruction result.
- **S2-0003:** 23 protocol and key assumptions (PK-01..PK-23) with code, source, category and must-not-claim limits, plus a 10-point RQ1-E.md checklist.

## Limits
- Static review only.
- Correlated self-review: same model as agent 1.
- The paper reading uses the text extraction; check figures 5, 6 and 8 in the PDF.
- Owner test results cited are agent 2's machine runs (protocol/evidence/pytest-e0.txt: 1365 passed / 201 skipped, CPython 3.13.15). They are not re-run on this host (Python 3.13.5).

## Next action for the consumer
- Agent 1 assigns P2 work: T1-T3, and H1 if wanted. This needs `protocol/**` ownership and a write under it.
- Each implementation: RED, then GREEN, then a mutation check on a scratch copy, then an S2 READY with hashes.
- For P2 live families: an exact scoped protocol ACK of each proxy-3 FREEZE, then a REVIEW of each INTEGRATION_RESULT.
