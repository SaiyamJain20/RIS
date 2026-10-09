# Solo Phase E: local three-agent protocol

Human directive, 2026-10-09: the three agents fan out and communicate **as before**, using the same
message types and rules as `communication/PROTOCOL.md`. The only change is that messages are **local
files in this directory**, not GitHub branches.

| Role | Played by | Writes (code) | Mailbox (local files) | Message IDs |
|---|---|---|---|---|
| agent 1: ledger, orchestrator, sole Git writer | main session | `ledger/**`, `communication/agent-1/**` | `communication/agent-1/outbox/` plus this directory | A1-NNNN (continues from A1-0059) |
| agent 2: protocol | proxy subagent "agent-2 (proxy)" | `protocol/**` | `communication/agent-1/solo/agent-2-proxy/` (`STATUS.md`, `HANDOFF.md`, `outbox/`) | S2-NNNN |
| agent 3: evaluation and coordination | proxy subagent "agent-3 (proxy)" | `evaluation/**`, `interfaces/**` (v1 frozen bytes untouched), `communication/{BOARD,GATES,DECISIONS,INTEGRATION}.md`, root active docs | `communication/agent-1/solo/agent-3-proxy/` (`STATUS.md`, `HANDOFF.md`, `outbox/`) | S3-NNNN |

Prefixes are S2 and S3, not A2 and A3, so the absent agents' own message history stays unambiguous.

## Rules (same as before, adapted)

1. **Headers.** Every message carries the `communication/PROTOCOL.md` headers:
   - `Message-ID`, `From`, `To`, `Cc`, `RQ`, `Task`, `Type`;
   - `Interface-version`, `Responds-to`, `Source-manifest`;
   - plus `Summary`, `Impact` and `Action requested`.

   `Type` is one of RFC, ACK, READY, BLOCKED, REVIEW, FREEZE, INTEGRATION_RESULT or DECISION.
2. **Sending.** A message counts as sent when its file exists in the sender's outbox **and** agent 1
   has been notified (the subagent returns to agent 1, or agent 1 relays it). Agent 1 wakes the
   addressee with a pointer to the file path.
3. **Same gates as before:**
   - **Live integration plans:** agent 3 publishes a FREEZE with the exact
     `integration-plan.json` SHA-256. Agents 1 and 2 each reply with an exact scoped ACK
     (`Accepted-plan-sha256:`).
   - **Services:** they start only after both ACKs, and only agent 3 starts or stops them.
   - **Results:** an INTEGRATION_RESULT is followed by REVIEWs from agents 1 and 2, each in its own
     scope.
4. **Ownership.** Each agent edits only its own paths. Anything another owner needs goes as an RFC
   or BLOCKED message. No agent edits another's module to unblock itself.
5. **Git.** Only agent 1 runs Git write commands. It commits exact reviewed paths and pushes to
   `agent-1`. Proxies may run read-only Git commands.
6. **Isolation:**

   | Agent | Ports | Scratch |
   |---|---|---|
   | agent 1 | 17545-17599 | `/home/saiyamjain/.claude/jobs/aed51961/tmp/a1/` |
   | agent 2 | 19545-19599 | `…/tmp/p2/` |
   | agent 3 | 18545-18599 | `…/tmp/p3/` |

   Durable evidence goes in the owner's evidence directory in the repo.
7. **Toolchain:**
   - Python: repo-root `.venv` (Python 3.13.5 with eth-account 0.14.0, jsonschema 4.26.0,
     pytest 9.0.2; created by agent 1 on 2026-10-09). Agent 3's frozen toolchain records 3.13.13; the
     patch-level difference is recorded, not hidden.
   - Foundry: v1.8.5 at `~/.foundry/bin`, which is not on PATH; prefix with
     `export PATH="$HOME/.foundry/bin:$PATH"`.
   - ProVerif 2.05 is **not installed** on this host. A3-0033's saved outputs stand as the formal
     evidence unless it is rebuilt.
8. **Honesty.** Proxy reviews and ACKs are the same model as agent 1. They are correlated self-review,
   and every gate record says so. Findings are classified as before: paper-supported, ambiguity,
   tested reconstruction result, deliberate mutation, or extension.
9. **Scope.** HMBC only, no JANUS, synthetic fixtures only. No external messages or deployments, no
   `archive/**` edits, no history rewrite or force push. F and G stay locked until gate E really
   passes.
