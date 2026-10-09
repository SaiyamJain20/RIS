# C-E1 public access runner checkpoint — 2026-10-08 UTC / 2026-10-09 IST

**Unit/static verification only. Real E1 integration is unproved.** E0 closed;
E1 WORKING; every RQ gate and all56 catalog schedules remain NOT_RUN.

`integration-plan.json` SHA-256 `1899126e37c683fd9b4334787f71131250d7950506d845286220249b526a4b31` is the concrete A3-0027 FREEZE
review artifact. It pins47 runtime/config/fixture inputs, ledger9d6911d/106 entries,
protocol465aff5/105 entries, the immutable v1 freeze, tools/root dependencies,
ports/chain IDs, service environment, key custody and finite budgets. Both exact
owner ACKs of these bytes are required before any snapshots or services start.
No ACK index or fabricated peer ACK is packaged here.

Final command `.venv/bin/python -m pytest evaluation/tests -q -p no:cacheprovider`
exited0:411 passed,74 explicit inputs unchanged.76 new checks include public
signature/native/worker joins, exact FREEZE refusals, environment controls,
process-group timeout cleanup and cancellation recording. Synthetic positive and
denied controls cover all3 profiles; they are not9 real two-chain controls.
`commands.json` records argv/cwd/exit/times/output digests; `source-brackets.json`
contains the final exact pre/post maps. Raw command/test logs live at `/home/karma/.codex/automations/ris-agent-branch-monitor-and-continuation/runs/20261008T185322Z`.
`source-audit.json` records211 exact Git blob checks,15 frozen copies,35 original
review files, sample provenance, tool hashes and actual package versions.

RED failures are retained in command metadata and external raw logs. Author
review found invalid/schema-valid error logging leaks, shell-child cleanup and
cancellation status defects; regressions pass. `helper-recovery.json` separates
helper/test mistakes from product/research results. Review was author-only,
weaker than independent review; no extra agents are authorized.

`peer-communication.json` preserves109 exact file-changing revisions. A1-0036
at13f21fca/c5731493.. is owner Anvil revert-trace evidence, not Agent3 live
compatibility. Selected pins and all frozen interface bytes are unchanged.
`no-ack-probe.json` records actual CLI exit2/BLOCKED before startup, with no services.

Next: both owners ACK A3-0027 with the exact plan hash; record their immutable Git
commit/path/SHA in an ACK index; re-fetch and verify ancestry/content; run fresh
wrong-admin, Alice allow and registered Bob policy-deny on all3 profiles. Record
native receipts/views, signed artifacts, redacted worker commitments, raw CLI
hashes, source brackets and owned process cleanup. Publish actual results and
release the logical freeze. Wrong-admin is baseline issuer restriction, not a
repair. E2/crash hooks/formal models and F/G remain gated. RPC consistency and
symbolic decryptability do not prove provider integrity, delivery, ABE or consensus.
