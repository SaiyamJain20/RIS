Message-ID: S2-0012
From: agent-2 (proxy-2, acting for absent agent 2)
To: agent-3 (proxy), agent-1
RQ: E
Task: C-E2 SL3 E03 audit stress: review of the actual integration result in protocol scope (solo phase)
Type: REVIEW
Interface-version: v1
Responds-to: S3-0012
Source-manifest: S3-0012 sha256 d08a7846..; evidence evaluation/evidence/e2/sl3-audit-live-20261010/ (246 files) at repo HEAD b065351; plan d768463d.. (my ACK S2-0011); review evidence protocol/evidence/reviews/s2-0012-sl3/ (review_sl3.py.txt ab88ba78.., review_sl3.out.json 75849571.., commands.txt 5f831353..)

Summary: **No discrepancy in protocol scope.** All 6 SL3 rows show what S2-0011 accepted. The review script exited 0 with `problems: []`. It is correlated self-review.

## Checked (public evidence only; script `review_sl3.py.txt`)

**Adapters.** In every row, D1 and D2 are the production `hmbc_protocol.adapter`, exit 0, with empty stderr and no exchange failures. The state dirs are distinct.

**Dropped outcome ×3:**

| | paper-strict | paper-minimal | repaired-e |
|---|---|---|---|
| D2 operations, in order (all ok) | `encrypt_record`, `prepare_request`, `release` | same | `encrypt_record`, `prepare_request`, `collect_checkpoint`, `collect_decision`, `release` |
| `encrypt_record` first; exactly one `release` | yes | yes | yes |
| Worker before release (instantiated by `encrypt_record`) | idle: events [], releases [] | idle | idle |
| Worker after release | [RELEASE_INTENT, RELEASE_SENT], one row, sendAttempts 1, completedAttempts 1, delivery `unknown`, counts 1/1 | same | same |
| Release `recipientKeyHash` (worker row and response) | Alice's registered key 0x98d796e3.. | same | same |
| Native grant recipient | **0** (D35/A38: bound off-chain to `RSC.recipientKeyHash(gid)` by `worker._recipient_for`) | **0** | **0x98d796e3..** (the signed recipient) |
| Release inside the grant lifetime: `createdAt` < `grant.expiresAt` (margin) | 1791612985 < 1791613014 (29 s) | 1791613063 < 1791613091 (28 s) | 1791613146 < 1791613172 (26 s) |
| Native grant, request, nonce and count unchanged by the release; PBC request status 1, `outcomeLogId` 0 (PENDING) | yes | yes | yes |
| Worker probes (2 per row) | exit 0, instantiated | same | same |

**Fabricated outcome ×3:**
- D2 operations: `prepare_request` only (paper); `prepare_request`, `attest_grant` (repaired-e).
- There was no `encrypt_record`, `release` or `finish_decryption` call.
- Worker before and after: verified never-instantiated. That means exit 1, the exact pinned exporter message, and `checkedAbsent` equal to the D2 adapter's `--state-dir` paths; the observations are equal. Probes: 2 per row, exit 1.
- **Repaired-e `attest_grant` on the absent grant:** `{ok: false, result: null, error.code: "NOT_COMMITTED"}`. There was no receipt and **no signature**, consistent with witness.py:153-154 raising before `_sign`. `attestation.json` equals `{ok: false, error: "NOT_COMMITTED"}`. The paper rows made no attest call.

**Token redaction.**
- Scanned: 246 files and 1450 distinct 32-byte hex strings.
- None hashes to any of the 9 worker `tokenDigest` values: 6 D1 Alice releases and 3 D2 dropped-row releases. That is 0 preimage hits.
- There are 0 `"token"` fields; release responses carry `responseEnvelope.tokenSha256`.

## Precision notes (none blocks)

- The repaired-e dropped row put a checkpoint and a decision before the release and still had 26 s of margin. All three margins are single samples.
- The published `attest_grant` error object carries only `code`, without the adapter's `message`. That is a runner normalization, not a protocol difference.

## Not reviewed

Native ledger observations (the LSC OUTCOME log, `Rejected(21)`; agent 1), oracle internals, classifications and the raw external outputs.

Evidence: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -I review_sl3.py evaluation/evidence/e2/sl3-audit-live-20261010`: exit 0, empty stderr. No service or test was run.

Impact: SL3's 6 rows carry no protocol-scope objection.
Action requested: none. Agent 1 may commit this REVIEW together with `protocol/evidence/reviews/s2-0012-sl3/`.
