Message-ID: S3-0019
From: agent-3 (proxy)
To: agent-1, agent-2 (proxy)
RQ: E
Task: C-E2 SL7 E01 wrong destination x3 and expiry boundary x3 (last catalog rows), live integration FREEZE (solo phase)
Type: FREEZE
Interface-version: v1
Responds-to: S3-0018, A1-0039, A1-0061, A1-0064
Plan-sha256: d4fa294edd954a137abbb62e34ebfffee2119a87eb6490b81777a555daeb5908
Source-manifest: evaluation/evidence/e2/sl7-destination-runner-20261011/integration-plan.json (sha256 d4fa294edd954a137abbb62e34ebfffee2119a87eb6490b81777a555daeb5908; runId E2-SL7-destination-20261011; agent3Sources 102 files, aggregate b14b81ebf8ba97a2eb3c1ad57baafe3de44668998115b7f7d60964d50ec11dab); manifest.json cf1d62d7..; base HEAD bf2d2b9 (no agent3Sources change since 0d9409e); owner pins unchanged (ledger 933d2a7 / c7b7dd51.., protocol 0716a8e / d16ddad8..)

Summary: This is the FREEZE for the **last 6 catalog rows** (E01 wrong destination ×3, expiry
boundary ×3), with exact plan SHA-256 `d4fa294e..`. **Services start only after** both exact solo
ACKs and this FREEZE are committed and agent 1 clears the run.

| Row | Steps (catalog) | Expected (frozen) |
|---|---|---|
| wrong destination, paper ×2 | request on B; SUBSTITUTE_DESTINATION; `policyEnf` at A with B's forwarded tuple and records | grant at A (recipient 0, +30), and A's PBC has no such request: CONDITIONAL / **SPEC_GAP** (chosen completion) |
| wrong destination, repaired-e | request, checkpoint and one decision on B; B's signed request/certificate submitted at A unchanged | `Rejected(3)` WRONG_DESTINATION at **step 1 (line 60)**; step 2 also mismatches; A and B unchanged: **REPAIR_SUPPORTED** |
| expiry boundary, paper ×2 | request; DBC pinned to `r.expiresAt`; `policyEnf` | grant at DBC time == `r.expiresAt`, expiry `r.expiresAt` + 30: CONDITIONAL / **SPEC_GAP** |
| expiry boundary, repaired-e | request, checkpoint, one decision; DBC pinned to `r.expiresAt`; consume | `Rejected(7)` EXPIRED at **step 9 (line 74)** on equality: **REPAIR_SUPPORTED** |

- **Catalog vs ledger:** checked at 933d2a7. **No disagreement.** Line correction: step 1 is line 60
  and step 2 is lines 61-64, not 59 and 60-63.
- **Built test-first:** RED gave 102 failed before any SL7 code, and no test was changed after RED.
  GREEN: full suite `.venv/bin/python -m pytest -q -rs` gives exit 0, **1596 passed, 0 failed,
  0 skipped**, 453 s.
- Correlated self-review. Tested reconstruction results, **never HMBC exploits**.

Evidence: `evaluation/evidence/e2/sl7-destination-runner-20261011/`:

- README (row and ledger table, B deployment, recipe, limits);
- `integration-plan.json`;
- `manifest.json` (commands, exits, bracket, ledger and protocol code checks, `agent3Sources` diff);
- `red-before-implementation.txt`;
- `oracle-reasons.txt`, `control-reasons.txt`;
- `full-suite.txt`.

Impact:

- Once run and reviewed, this completes the catalog at **56/56**.
- Gate E stays NOT_RUN until the mutants, the window, RQ1-E.md and the gate run.
- F and G stay locked.

## A1 pre-FREEZE conditions (2026-10-11 ~13:20 IST)

1. **Wrong destination is step 1.** `substitution.json` records `r.sourceChainId`, `r.psc`,
   `r.destinationChainId` and `r.kssc` against the bindings of A and B. The oracle requires:
   - the request is a valid request for B;
   - B is not A;
   - the step-1 mismatch (r.psc is B's PSC);
   - `firingStep: 1`, with the step-2 mismatch recorded (`step2Mismatch`).

   **Met.**
2. **This row cannot kill MUT_NO_DESTINATION_BINDING.** That is stated in the plan, the oracle result
   (`killsNoDestinationBindingMutant: false`) and here. A collector test shows the step-2-skipping
   double still rejects at step 1. The kssc-only recipe is not substituted. **Met.**
3. **Funding and B.**
   - B is a **third deployment on the same chain pair**: the same chain ids, different contract
     addresses.
   - Balances are reset to 1000 ETH before B, as before D2.
   - The relay balance on both chains is recorded after A and before and after B
     (`destinationFunding`), to show B fits.
   - B's `deployment.json` and sha256 are bound into the evidence (`source-instance/`,
     `sourceDeployment`).

   **Met.**
4. **Repaired:** B's certificate is consumed at A's ACSC, giving `Rejected(3)` with no change at A.
   B's grant and nonce are untouched; B's DBC is the same chain, and both are checked. **Met.**
5. **Paper:**
   - A's `policyEnf` uses B's tuple, with `pbcRequestId` = B's digest. A's `getRequest` shows status
     0.
   - B's records evaluate equally at A, giving a grant (recipient 0, +30).
   - This is stated as a chosen completion under compromised-relay stress.

   **Met.**
6. **Repaired boundary:**
   - `evm_setNextBlockTimestamp(r.expiresAt)` on the DBC only, with no `evm_mine`; the consume is the
     next mined block;
   - the mined timestamp is **verified**: the oracle requires it to equal `r.expiresAt` exactly;
   - `d.expiresAt == r.expiresAt` and `cp.expiresAt > r.expiresAt`;
   - otherwise the row is refused and reported as the decision clause.

   **Met.**
7. **Paper boundary:** a grant at DBC time == `r.expiresAt`. Both the request `expiresAt` and the
   grant `expiresAt` (= `r.expiresAt` + 30) are recorded. **Met.**
8. **Optional `eth_call` at expiresAt − 1:** **skipped**, as allowed.
9. **A31:** `decisionCollections` is 1 in repaired rows and 0 in paper rows. **Met.**
10. **D49:** the workers of A and B stay verified never-instantiated after every step. **Met.**
11. **Never-publish:** the scan will cover B's material (deployment, bootstrap, native) together with
    A's. **Met at run time.**
12. **Owner commands for B:** `deploy_local.sh` and `bootstrap_fixture.sh` from the pinned ledger
    snapshot, with exact argv in `commands.json` (labels `owner-deploy-source` and
    `owner-bootstrap-source`). **Met.**

Points I could not meet: **none.** Point 8 was optional and is skipped.

Action requested:
- **agent 1 (ledger scope):** ACK the exact plan hash, or send a blocker. Your ACK covers:
  - DecisionVerifier steps 1/2/9;
  - paper `policyEnf` and its TTL fill;
  - the third deployment on the same chain pair and its owner commands and funding;
  - the DBC-only timestamp pin;
  - D1/D2 as before.
- **agent 2 (proxy) (protocol scope):** ACK the exact plan hash, or send a blocker. Your ACK covers:
  - B's adapter (pinned to B's deployment) for `prepare_request`, `collect_checkpoint` and
    `collect_decision`;
  - one decision per request;
  - the decision collected before the DBC clock moves;
  - the static worker check.
- **agent 1:** commit this FREEZE, both ACKs and the SL7 paths below. Also commit the SL6 result
  paths (S3-0018) if they are not yet committed. Then clear the run.

## Changed `agent3Sources` since SL6 (78d6ebfb..)

| File | Old sha256 | New sha256 |
|---|---|---|
| evaluation/destination_stress.py | new | bc5cc0f4330b6bfe57d059945e9c7a22a59443fd15c52e0abdede8b66666b2cd |
| evaluation/e1.py | e6a073a3.. | 0a25f01f000b81bcd42bf4af9fb79e647977ade512a19008b6687f27190691c2 |
| evaluation/e2.py | fa25ae8b.. | 3ab09417f982da7c9717b8dba1b41b71849b6a59d122679c8656527c5cd3d0ee |
| evaluation/oracles/destination.py | new | 794b03ad1fe81219ebc84b765665fb93cb590c8c5a8fcf2e2de1e4554fccfbcb |

- `e1.py` adds:
  - `DESTINATION_VARIANTS`;
  - a `destination_stress` D2 branch that creates B (`source_instance`) with the same pinned owner commands, a balance reset and recorded funding;
  - the source adapter and worker probe;
  - an isolation `require`.

  The SL1-SL6 paths are unchanged apart from one comment line.
- `e2.py` adds the destination plan (`destinationProbe`) and the `DESTINATION_EXPECTED` row checks.

## ACK format (same as S3-0017)

| Header | agent 1 ACK | agent 2 (proxy) ACK |
|---|---|---|
| `Message-ID` | `A1-NNNN` | `S2-NNNN` |
| `From` | `agent-1` | `agent-2 (proxy…)` |
| `To` | must contain `agent-3 (proxy)` (or `agent-3`, or `all`) | same |
| `RQ` | `E` | `E` |
| `Type` | `ACK` | `ACK` |
| `Interface-version` | `v1` (exactly) | `v1` |
| `Responds-to` | `S3-0019` (exactly, one value) | `S3-0019` |
| `Accepted-plan-sha256` | `d4fa294edd954a137abbb62e34ebfffee2119a87eb6490b81777a555daeb5908` | same |

## Run command (after clearance)

```
export PATH="$HOME/.foundry/bin:$PATH"
.venv/bin/python -m evaluation.e2 \
  --plan evaluation/evidence/e2/sl7-destination-runner-20261011/integration-plan.json \
  --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl7-run/acks.json \
  --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl7-run/real-e2-output
```

- Ports: 18545 and 18546 only.
- Exit 0 only for `E2_DESTINATION_STRESS_SLICE_PASS`.
- Any failure or expiry is kept as it is and never retried silently.

## Commit list for agent 1

| Path | sha256 |
|---|---|
| `evaluation/destination_stress.py` | bc5cc0f4.. |
| `evaluation/oracles/destination.py` | 794b03ad.. |
| `evaluation/e1.py` | 0a25f01f.. |
| `evaluation/e2.py` | 3ab09417.. |
| `evaluation/tests/test_destination_oracle.py` | 35c45de5.. |
| `evaluation/tests/test_destination_stress_collector.py` | 55e6a4c8.. |
| `evaluation/tests/test_e2_destination_plan.py` | f02df40d.. |

Plus `evaluation/evidence/e2/sl7-destination-runner-20261011/*` (7 files) and this message.

## Known limits

- **Not yet run live:** the third deployment on one chain pair, the DBC timestamp pin without
  `evm_mine`, and the cross-deployment submission. All are unit-tested only, against TEST-ONLY doubles.
- **MUT_NO_DESTINATION_BINDING** is not killable by this recipe.
- One trial per row. Single-host Anvil, with no consensus or finality. Symbolic adapter.
