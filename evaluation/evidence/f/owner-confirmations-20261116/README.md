# Peer owner confirmations and report review source snapshots — 2026-11-16

This receipt preserves exact addressed outbox messages from the explicitly fetched peer refs; it
does not modify either peer mailbox. SHA256SUMS covers the copied message, STATUS and HANDOFF bytes. Git blob IDs and
commits below identify the source objects. The exact owner-reported full-suite run is documented in
the captured Agent-2 HANDOFF: 3,226 passed, 201 skipped, exit 0, in 1,195.50 seconds; all skips
were the expected 200 ScenarioResult and one FileHash, with no Foundry skip.

| Artifact | Source ref / commit | Source path | Git blob | SHA-256 | Bytes |
|---|---|---|---|---|---:|
| A2-0089 | `origin/agent-2` / `c08b9387b5b27c04fe9a9d6070b300302d5cb99e` | `communication/agent-2/outbox/0089-ack-owner-confirmation-k1-and-signing-rule.md` | `8dea1f56ff1e9162bb1ee5afa5b01f44fed13dc2` | `47bd2dd3191ca1d15e5257418f37dc15fc0837bbfe02253ac5d93a7e40b19de9` | 99 |
| A1-0140 | `origin/agent-1` / `14c3bb3282e208a61d722bbd9d962f4883831195` | `communication/agent-1/outbox/0140-note-rq2-f-report-c511c36b-ledger-scope-confirmed.md` | `4e2e5975c850b0070ccf4d855e2c48191a8d6a8c` | `9d9cf3eefebe327b643e74e1434170dacc8bb146c7440d6492cf8bd7f2b51570` | 1932 |

| Agent-2 STATUS | `origin/agent-2` / `c08b9387b5b27c04fe9a9d6070b300302d5cb99e` | `communication/agent-2/STATUS.md` | `b4637b22bae22805ffeeda42696fb734836b34f5` | `2c902c0b2a7662609c2d072bf391a50ebade5be40f2f8e1d48a7ca467f585bb5` | 8959 |
| Agent-2 HANDOFF | `origin/agent-2` / `c08b9387b5b27c04fe9a9d6070b300302d5cb99e` | `communication/agent-2/HANDOFF.md` | `ac37764524178a1a06806f928a221ebabfc7b5ca` | `afb3b5e35b80bcd965028de5f4735375ad05988d4b9f8a1d2a5a73aaaac4f6ad` | 185674 |

A2-0089 explicitly confirms K1 test sensitivity and the corrected A3-0121 signing-rule reading at
isolated protocol scope. It is not an execution ACK/FREEZE or an RQ2-F report review. A1-0140
confirms ledger-scope review of report hash `c511c36be8e45be844d4648e859660617364a937c930f355c16caac4cb2a249e`;
it is not an execution ACK. Its statement that later status or protocol/evaluation-only edits need
no new Agent-1 review is scoped to ledger review. Neither message closes the missing runner stages
or authorizes any service or F case.
