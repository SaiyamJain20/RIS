# F measurements — agent 3, 2026-11-14 (presentation results)

Classification: tested reconstruction results on LOCAL synthetic runs (Forge EVM, in-process real
witnesses behind a virtual transport). NOT an F gate result, NOT consensus, NOT a live chain, NOT
network latency. Paper-derived reconstruction; same-model author. These are deviations from the plan's
sequence (no runner/FREEZE yet) made on the human's instruction to measure what exists; nothing here
claims Gate F. No owner file edited (scratch extracts of git commits).

## M1. Certificate overhead (gas, calldata) — controlled benchmark
Harness `evaluation/measurements/CertBench.t.sol` (run inside a scratch copy of ledger 85c59f5, not
added to the ledger module). Forge 1.8.5, solc 0.8.37 (the ledger's pinned config), exit 0.
Same code, profile REPAIRED_E (1 signature) vs REPAIRED_F (q-of-n), measured with gasleft around the
single external call; one deterministic run per row (log `certbench.log.gz`).

| call | sigs | gas | calldata bytes | vs 1 sig |
|---|---|---|---|---|
| KSSC.acceptState (checkpoint) | 1 (E) | 208,290 | 548 | - |
| | 3 (F, q=3) | 231,260 | 868 | +22,970 (+11.0%) |
| | 4 | 238,046 | 1,028 | +29,756 (+14.3%) |
| ACSC.consumeDecision | 1 (E) | 324,323 | 1,380 | - |
| | 3 (F, q=3) | 342,261 | 1,700 | +17,938 (+5.5%) |
| | 4 | 349,053 | 1,860 | +24,730 (+7.6%) |
Marginal cost of one more signature: about 6.8k gas and 160 calldata bytes. Going from E to F q=3 adds
more than 2x the marginal cost (22.9k vs 13.6k for two signatures), so a fixed F cost (witness-set/policy
checks) is included. Includes cold-storage access; not an EIP-1559 fee estimate. Not measured here:
receipt (PSC) path, governance execute (the whole-suite report shows Governance.execute median 58,724,
max 931,093 over mixed test calls), signing-time latency.
Whole-suite gas-report comparison E 91add8c (166 tests pass) vs F 85c59f5 (316 tests pass): `gas-compare.md`.
Caution: medians there mix test call patterns; indicative only. Runtime sizes from `forge build --sizes` (files runtime-sizes-*.txt), E 91add8c -> F 85c59f5, bytes:
ACSC 12,345 -> 12,370; KSSC 7,407 -> 7,767; PSC 12,503 -> 12,516; TMSC 12,635 -> 16,127; new
Governance 4,829; LSC/RSC unchanged. All under the 24,576 B limit (TMSC margin 8,449 B).

## M2. Availability sweep with real witnesses (all 16 muted subsets)
`evaluation/measurements/availability_sweep.py` over agent 2's snapshot 55f180e: four real witnesses
(real durable SQLite stores, real EIP-712 signatures, synthetic keys), real pool state machine, virtual
transport with muted endpoints; 5 runs per subset; raw `availability.json`.
- 0 muted: certificate with 3 signatures, finished at virtual 0 ms (wall ~36 ms median).
- exactly 1 muted (4 subsets): certificate with 3 signatures every run (wall ~30 ms).
- 2 muted (6 subsets), 3 muted (4), 4 muted (1): NO certificate in every run; collection ends at the
  10,000 virtual-ms deadline with 0 signatures submitted.
- Reply delays 400/300/200/100 ms: certificate from the three fastest, finished at virtual 300 ms (the
  slowest witness is not waited for).
This is the paper-style statement: valid access survives one withholding witness; two withholding
witnesses give unavailability (liveness is not claimed under arbitrary delay). Virtual time only.

## M3. Safety tests run (agent 2's suites, snapshot 55f180e)
test_pool_core, test_witness_pool, test_witness_pool_driver, test_byzantine_witness,
test_faulty_witness, test_delayed_witness: 276 passed, 5 skipped (Foundry-dependent), exit 0, 35 s.
Includes the explicit f=2 control (two Byzantine witnesses get a fake value adopted) and the f=1 test
(a certificate is only over a value an honest witness recorded).

## M4. Finite model (TLC)
See evaluation/evidence/f/decision-quorum-tlc-20261113/: f=1,f=0 hold; weak q=2, f=2, no persistence violate.

## Caveats stated plainly
- CORRECTION: an earlier version of this README (commit 0754d98) and gas-compare.md list TMSC deployment size 52,339 B and an open question about the EVM size limit. That was a parser artifact (the script took the last table row for a contract name), not a real size. The sizes above are from forge --sizes. The 'Deployment size' block of gas-compare.md is unreliable; ignore it.
- Gas numbers are single deterministic runs of one fixture; no confidence intervals apply.
- Wall times are in-process CPU timings, not network latency.
- E vs F comparison in M1 uses the F commit's own E profile, not the historical 91add8c bytecode.

## M5. Byzantine sweep (added 2026-11-14, later; `byzantine_sweep.py`, raw `byzantine.json`, exit 0, 7.6 s)
Over agent 2's pool state machine and scripted-witness harness at 55f180e (hash-matched snapshot).
Honest witnesses are agent 2's MODEL of the signing rule, not the durable store (correlated, same-model
author of both); signatures are real EIP-712. Byzantine behaviours (9): silent, valid signature over
A/B/C, recorded report over A/B/C, garbage, wrong-key signature.
- f=1: 972 cases (4 positions x 9 behaviours x 27 honest pin patterns). 180 certificates, 792 no
  certificate (honest pin splits make many cases unavailable regardless of the Byzantine witness; no
  certificate is not unsafe). 0 invalid certificates (every one has 3 distinct, sorted, valid signers).
  0 agreement-hazard cases.
- f=2 control (outside the fault bound): 4,374 cases (6 position pairs x 81 behaviour pairs x 9 pin
  patterns). 330 certificates, 0 invalid, **2,916 agreement-hazard cases**.
Hazard definition (mine): after the run, two different values could each gather >= 3 signers, counting
honest witnesses whose store holds the value plus all Byzantine witnesses. It is a POTENTIAL, not a
realized double certificate; it restates the quorum-overlap bound on post-run states of the real pool
and matches the TLC result (f=1 safe, f=2 not). Same-model, virtual time, one fixture family.

## M1b. Receipt path added (2026-11-14, later; CertBench.t.sol updated, log `certbench-with-receipt.log.gz`, exit 0, 9 tests pass)
PSC.reportAttestedOutcome: 1 sig (E profile) 533,754 gas / 644 B calldata; 3 sigs (F) 553,488 / 964
(+19,734, +3.7%); 4 sigs 560,290 / 1,124 (+26,536, +5.0%). Per extra signature ~6.8k gas, 160 B, as
for the other two paths. The three witness-signed paths (checkpoint, decision, receipt) therefore cost
+3.7% to +11.0% gas at q=3 over the single-signature profile. Same caveats (single deterministic run,
same-commit E profile, not a fee estimate). Governance execute is NOT measured by this harness.

## Agent 1's review of M1 (A1-0123)
Agent 1 reproduced all six original gas/calldata values and the seven runtime sizes exactly (its host,
harness unmodified, 9/9 pass; correlated review). It refuted its own cold-storage hypothesis for the fixed
F overhead (scratch variant warming the witness set: 231,261 vs 231,260), and attributes the ~9.4k
(checkpoint) / ~4.4k (decision) fixed part to the policy-version external call and the 4-entry
witness-set scan; that split is unmeasured. `forge build --sizes` exits 1 only because of Forge scripts
(Deploy 83,849 B, ExportGovernanceVectors 45,094 B, ExportVectors 39,827 B), never deployed as product;
quote product rows only. Receipt-path numbers above are mine alone, not yet reproduced by a peer.

## M1c. Governance execute (2026-11-14, later; `CertBenchGov.t.sol`, log `certbench-governance.log.gz`, exit 0, 6 pass)
Governance exists only in F, so there is no 1-signature baseline. Gas for Governance.execute by quorum
(caller holds no role; fresh fixture, nonce 1, single deterministic run):
| action | 3 sigs gas / calldata | 4 sigs gas / calldata |
|---|---|---|
| AddAuthority | 524,214 / 836 B | 530,980 / 996 B |
| RemoveAuthority | 424,421 / 804 B | 431,185 / 964 B |
| SetCaAdmins | 446,934 / 836 B | 453,688 / 996 B |
The signature part is again ~6.8k gas and 160 B per extra signature; the rest is the state change in TMSC,
the LSC log entry and the authEpoch bump (cost not split here). Not yet peer-reproduced. The whole-suite
report's Governance.execute max of 931,093 comes from other test shapes, not from these three actions.

## Peer reproduction of M1c (A1-0125)
Agent 1 reproduced all six Governance.execute gas/calldata values exactly (harness unmodified, 6/6, exit 0;
correlated review) and found my cost attribution consistent with the source (nonce check, quorum verify,
dispatch to TMSC, authEpoch bump, LSC log entry). So M1, M1b and M1c are all peer-reproduced.

## M6. Real-process runs (added 2026-11-14, later)
Agent 2's `tests/test_witness_process_transport_live.py` at 55f180e, run UNMODIFIED by me on this host:
four real `witness_main` OS processes (durable stores, synthetic keys), a local Anvil pair, the real F
ledger 85c59f5 (read via GIT_DIR from this repo, read-only), real KSSC acceptance. HMBC_FOUNDRY_DIR set,
python -I, exit 0 in three consecutive runs (4 passed in 58.8 s, 78.2 s, 59.1 s; setup ~46 s is chain
deploy). Test-body ("call") times, three runs:
| scenario | run 1 | run 2 | run 3 |
|---|---|---|---|
| 4 live witnesses, q=3 certificate, real KSSC accepts | 0.69 s | 0.69 s | 0.78 s |
| 1 witness SIGKILLed: 3 signers, certificate still accepted | 0.63 s | 0.55 s | 0.60 s |
| 2 witnesses stopped (SIGSTOP): classified timeout, takes the pool's time | 10.54 s | 10.54 s | 10.55 s |
| SIGKILLed witness restarted by a fresh supervisor keeps its durable pin | 0.96 s | 0.87 s | 0.88 s |
The 10.5 s is the pool's configured 10 s deadline plus overhead, i.e. unavailability costs the full
timeout; the successful paths include the on-chain acceptance on a local Anvil (no network, no block
time). These are agent 2's assertions re-executed on my host, not new scenarios of my own; they show the
M2 virtual-time result (<=1 faulty tolerated, 2 not) also holds with real processes and a real contract.
No leftover anvil/witness processes afterwards. One host, local only, same-model; not Gate F.
