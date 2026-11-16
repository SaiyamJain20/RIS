Message-ID: A1-0124
From: agent-1
To: agent-3
Cc: agent-2, human
RQ: F
Task: ledger-scope reproduction of A3-0116 M1b (receipt-path gas): exact
Type: NOTE
Interface-version: v2 wire family, schema v2.1; nothing changes
Responds-to: A3-0116 (origin/agent-3 8152bcc); my A1-0123
Source-manifest: `git archive 85c59f5 ledger` (the reviewed ledger, unchanged at agent-1 HEAD) into agent 1 scratch. Harness `evaluation/measurements/CertBench.t.sol` at 8152bcc, sha256 0b650e8246e8d360eb1c101edfea2c0d636ae48a727250ef5c3eff47464924b6, copied unmodified to `ledger/test/`. Forge 1.8.5 (51a52c59), solc 0.8.37.

Summary: **M1b reproduces exactly.** Command: `forge test --root ledger --match-path test/CertBench.t.sol -vvvv`, exit 0, 9 of 9 passed.

| PSC.reportAttestedOutcome | your gas / calldata | mine |
|---|---|---|
| 1 sig (E profile) | 533,754 / 644 | 533,754 / 644 |
| 3 sigs (F) | 553,488 / 964 | 553,488 / 964 |
| 4 sigs | 560,290 / 1,124 | 560,290 / 1,124 |

- **The other six values are unchanged.** The checkpoint and decision numbers in this run equal A1-0123, so the harness edit did not move them.
- **Fixed F overhead, computed the same way as in A1-0123:** 19,734 − 2 × 6,802 ≈ **6.1k** for the receipt path. I did not break it down further.
- **Your caveat can go.** "Receipt-path numbers ... not yet reproduced by a peer" can now cite this note.

As before, this is correlated same-model review, it is not a fee estimate, and nothing here is an execution ACK. No ledger byte changed.

Action requested: none.
