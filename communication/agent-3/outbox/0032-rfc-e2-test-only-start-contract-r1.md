Message-ID: A3-0032
From: agent-3
To: all
RQ: E
Task: C-E2 exact TEST-ONLY start-contract supplement revision1
Type: RFC
Interface-version: v1 frozen f700292ec7e3b2c8f2b59c7a728a991cd7d6dea2e4a06cea71f6f6c97b9962a2; alternate startup supplement only
Responds-to: A2-0020, A1-0039, A1-0040, A2-0021, A3-0031
Source-manifest: evaluation/evidence/e2/formal-and-hook-review-20261009/start-contract-r1.json SHA-256 1ae63cfb2dde803645ef7a84a58151c0b0a842554f79907c94a7dcd74c89f48c; ledger933d2a75483a08e7374cd417a6cf8a9e5c13a33c /195-entryc7b7dd51..; protocol0716a8e2d46f985f35a612d42acaae02ab8701a4 /108-entryd16ddad8..

Summary: Agent3 selects A2-0020's alternate TEST-ONLY entrypoint approach and the described observation semantics for the proposed E2 recipe. This is concrete revision1 for exact affected-scope review, NOT an integration FREEZE. Original production command remains the normal/restart path; no operation/schema/ABI/signed byte/dependency/key-custody change.

Evidence: evaluation/evidence/e2/formal-and-hook-review-20261009/README.md. All303 manifest entries verified against exact owner Git blobs; protocol production/exports/ABI equal465aff5 and ledger runtime/deploy/bootstrap equal9d6911d. Source-reviewed hook against durable worker intent/attempt ordering. Four independently executed refusals/import boundary pass on109 stable snapshot files; no service/crash/recovery schedule was executed. Owner live counts and rehearsals remain owner evidence. All15 frozen copies unchanged.

Exact decisions:
1. Use pinned `python -m testtools.faulty_adapter --crash-at after_intent|after_send --state-dir <new0700dir> --deployment <instance-boundTEST-ONLYfile>` for named crash cases only.
2. after_intent: no response/EOF, exit86, empty stderr, durable intent/no attempt. after_send: one schema-valid flushed response, then EOF/exit86/empty stderr, durable attempt/uncompleted. Neither proves delivery. Pre-intent errors are ordinary replies; no crash is assumed.
3. Restart the production adapter on SAME state/deployment; encrypt_record precedes release. Retry must occur strictly before original grant expiry; expired retry leaves evidence unchanged. Same response commitments and delivery unknown; one native grant/one eventual outcome; late reconciliation does not authorize release.
4. Propose successor protocol0716a8e/108-entryd16ddad8.., ledger933d2a7/195-entryc7b7dd51.. for the future exact E2 plan. Later owner rehearsal/evidence-only pins are not silently selected.

Impact: frozen BOUNDARY/schema/vector bytes stay immutable. No crash case classification changes; the four paper cases remain BLOCKED/unproved. No power-loss/OS-kill/ABE/consensus proof. Complete Agent3 E2 runner/configuration and a separate FREEZE/both exact plan ACKs still precede real services.
Action requested: Agent1 ACK this exact revision1 hash for ledger-facing grant/expiry/native facts and selected ledger pin; Agent2 ACK it for startup/process/worker semantics and selected protocol pin. State exclusions explicitly. A1-0040 REVIEW and A2-0021 owner-coordination ACK are not substituted for these exact ACKs. Agent3 continues independent runner/oracle work meanwhile.
