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
Caution: medians there mix test call patterns; indicative only. Deployment size: TMSC 14,861 -> 52,339 B,
KSSC 9,490 -> 10,077 B, new Governance 6,511 B (all below the 24,576 B limit except TMSC at 52,339 B,
which exceeds it as reported by the gas report's size column — see caveat below).

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
- The Deployment size note: the gas report lists TMSC at 52,339 B for F. That exceeds the EVM's
  24,576 B contract-size limit; Forge test runs do not enforce it. I have NOT verified whether the
  deployed F TMSC would be refused on a real chain (it must be checked against agent 1's deploy
  scripts/ via_ir settings). Treat as an open question for agent 1, not a finding.
- Gas numbers are single deterministic runs of one fixture; no confidence intervals apply.
- Wall times are in-process CPU timings, not network latency.
- E vs F comparison in M1 uses the F commit's own E profile, not the historical 91add8c bytecode.
