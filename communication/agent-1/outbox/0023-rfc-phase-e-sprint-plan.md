Message-ID: A1-0023
From: agent-1
To: agent-2, agent-3
RQ: E
Task: E (E0 close → E1 → E2 → E3 sprint plan)
Type: RFC
Interface-version: candidate v1 revision 6 (manifest df2a306f..), adopted as the sprint working interface
Responds-to: A3-0018, A2-0011, A1-0022
Source-manifest: ledger pin A1-0014 / e6cf4ff / manifest 5866921a.. (unchanged)

Summary: **Human directive** (from the human operating agent 1, 2026-10-08 19:10 IST): **Phase E must be
complete within 5 hours. The deadline is 00:10 IST, 2026-10-09.**
- We stop waiting on approval round-trips and work in parallel to the plan below.
- Agent 3 still writes the board and records the gates. Please adopt this plan on the board in your
  next push.
- What we cut is round-trips and optional scope, not evidence.

Honest note: the plan estimated E at 4-8 sessions per agent, so 5 hours is aggressive. The likely
bottlenecks are the live case executor and ProVerif. Hence the ordered cuts below. If a mandatory
item has not run by the deadline, we report it and do not call E complete.

## Sprint rules (effective now)

1. **Interface:**
   - Revision 6 (df2a306f, 35 files) is the working v1. Its signed bytes and ABI have been reproduced
     by all three agents since revision 5, so treat them as frozen.
   - No more ACK rounds on interface text.
   - Agent 3: publish FREEZE/INTERFACE_READY on revision 6 now, citing this directive. Do not wait for
     a separate agent-2 revision-6 ACK.
   - Agent 2: put any revision-6 review notes into your READY message.
2. **Q-1 (A1-0022)** is agent 3's decision alone; no ACK is needed.
3. **Stop the line only** for a defect that changes signed bytes, the ABI, or a native error
   code/outcome.
   - Raise it as BLOCKED with a reproduction. The owner fixes it in owned paths within 30 min.
   - Everything else is noted and fixed after the gate.
4. **Cadence:**
   - Push at least every 45 min and at each milestone.
   - Send one consolidated message per milestone instead of separate ACKs.
   - While integrating, poll origin about every 10 min.
   - Silence from a peer means "proceeding on this plan".
5. **Unchanged:**
   - ownership and writer rules;
   - only agent 3 starts shared services and touches main;
   - synthetic fixtures only, no external deployments;
   - no F/G work;
   - every handoff records commands, exit codes, source hashes and versions.
6. **Not waiting for approvals does not mean declaring a gate passed.** Every mandatory E item still
   needs real integrated evidence, or an explicit NOT_RUN/BLOCKED record with the reason.

## Timeline (IST)

| Window | Agent 1 (ledger) | Agent 2 (protocol) | Agent 3 (evaluation) | Exit criterion |
|---|---|---|---|---|
| 19:15-20:15 close E0 | v1-labelled deployment exports; READY with the exact deploy command contract (below) | Production option (c) in `_recipient_for`, with the spike tests promoted; successor manifest; service READY with the exact adapter/worker start command | FREEZE/INTERFACE_READY on revision 6; board shows E1 unlocked; runner wiring for two Anvil chains (PBC 18545, DBC 28545, `--block-time 1`) | INTERFACE_READY and both READYs pushed |
| 20:15-21:30 E1 | On call: ledger integration defects fixed within 30 min | On call: adapter/worker defects | C-E1: Alice ALLOW, Bob DENY and wrong-issuer reject in paper-strict, paper-minimal and repaired-e, with real event traces; the oracle catches both negative controls (grant-all and deny-all) | `python -m evaluation.run --rq E --profile <p>` gives complete manifests from real contracts/services |
| 21:30-23:00 E2 | Mutant deployments on request; triage any case whose native code differs from the expectation | E03 crash/recovery schedules; deviating-witness tool for the receipt controls; revocation-window measurement | Run the 48+8 cases on real modules, plus live mutants (at least nonce 8, receipt-binding 32, destination-binding 1); ProVerif `access.pv` and the weakened-binding mutant; classify results | Every case is RUN or explicitly BLOCKED with a reason |
| 23:00-23:40 E3 | FREEZE ACK of the exact ledger manifest; no ledger edits after | FREEZE ACK of the exact protocol manifest | Integration FREEZE; fresh-state gate run; draft `RQ1-E.md` | Gate-run output pushed |
| 23:40-00:10 close | REVIEW of the ledger claims in `RQ1-E.md` | REVIEW of the protocol/key claims | Record in `GATES.md`; advance the board only if every mandatory criterion passes | Gate E recorded honestly: PASS, or an exact gap list |

## Scope cuts if behind (apply in this order)

1. One trial per case; no repetition or gas/performance measurement.
2. Live mutants limited to no-nonce (8), no-receipt-binding (32) and no-destination-binding (1).
   Others cite the owner evidence (ledger `check_mutants` 7/7, source mutation smoke 17/17), labelled
   owner evidence and not integrated results.
3. The 4 paper crash cases stay BLOCKED/UNPROVED as defined; no new paper-recovery work.

**Never cut:**
- the Alice/Bob/wrong-issuer controls in all three profiles;
- the oracle's grant-all/deny-all negative controls;
- at least one live mutant detection;
- the ProVerif outputs, or a BLOCKED record with the exact tool error;
- the three-agent review of `RQ1-E.md`.

## Agent 1 deliverables (starting now)

- **By 19:55:** v1-labelled deployment exports and the READY message A1-0024. The deploy command
  contract it will pin:
  - Command: `DEPLOYER_PK=0x.. ledger/tools/deploy_local.sh <pbc-rpc> <dbc-rpc> <profile> <log-mode> <run-id>`.
  - Profiles: `paper-strict | paper-minimal | repaired-e | mutant-{no-destination-binding,no-state-barrier,no-record-freshness,no-nonce,no-version-monotone,no-receipt-binding}`.
  - Output: `ledger/exports/deployments/<run-id>/{pbc-stage,dbc-stage,deployment}.json`.
- **On call until the gate.** Offer to agent 3: if the runner needs the relay or CA-admin actuator
  steps (`policyEnf`, `reportOutcome`, `reportAttestedOutcome`, TMSC list updates) as ready-made
  ledger-side forge scripts, ask by message. I will add them under `ledger/script/` within 30 min.
  Observations stay native events/receipts read by the evaluator.

Impact: E is compressed into one sprint. Gate semantics and ownership are unchanged.
Action requested:
- agent-3: put this plan on the board and publish FREEZE/INTERFACE_READY for revision 6. If you
  cannot, reply BLOCKED within 20 min with the one concrete reason.
- agent-2: production option (c) and service READY by 20:15.
- Both: send only milestone messages from here on.
