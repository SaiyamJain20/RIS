# Agent 1 status

- Role: Ledger and policy
- State: WAITING (revision 4 reviewed in A1-0013 with F-1..F-3 change requests; new ledger READY A1-0014; waiting on agent-3 revised manifest, the v1 freeze and E1 unlock)
- Active RQ/task: E / E0 (final review); A-E1 draft and A-E2 (incl. E03 receipt) published
- Interface version: candidate v1 revision 4 (manifest c8cf819f..), reviewed: scoped ACK for policy tuple/deployment label/common semantics/toolchain; changes requested F-1 (fixture role ids), F-2 (E01 subject-substitution error class), F-3 (OUTCOME_RECORDED join rule); NOT frozen
- Git: branch `agent-1` on origin; distributed workflow D19
- Current files: `ledger/**` (manifest `ledger/evidence/source-manifest.sha256`, 100 entries), `communication/agent-1/**`
- Completed tests/evidence: forge test 166/0; policy test-first run (2 expected failures); mutant suites 7/7; source mutation smoke 17/17 (baseline 166/0); cast crosscheck 196/0; live smoke 4/4 profiles; revision-4 LedgerDeployment validation 4/4
- Dependencies: agent-3 revision addressing F-1..F-3, then the exact final manifest ACK; v1 freeze; E1 unlock
- Blocker: none for owned work
- Last message sent: A1-0017 (review of agent-2 candidate witness: sign ALLOW only if ACSC.evaluate passes, so policy denials are DBC-logged). Current READY A1-0014. Read: A3-0001..A3-0011 (agent-3 c982d04), A2-0001..A2-0008 (agent-2 2f9f0bb)
- Next action: monitor origin; ACK the revised revision-4 manifest; on freeze, emit v1-labelled exports and start E1 integration support
- Integration freeze acknowledged: none

Writer: agent 1 only. Update this snapshot; preserve durable history in immutable outbox messages.
