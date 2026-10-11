# SL7: E01 wrong-destination and expiry-boundary runner and plan (no services yet)

Paper-derived HMBC2020 reconstruction. Synthetic only. E/RQ1 is active; gate E is NOT_RUN; F and G
are locked.

Author: agent 3 (proxy), solo phase (A1-0039, A1-0059, A1-0064). **Correlated self-review.**

**Status:** runner implemented **test-first** and unit-verified; plan frozen as S3-0019. No service
has run. **No catalog row is completed by this checkpoint.** These are the last 6 catalog rows.

## Rows, frozen expectations and pinned ledger facts (933d2a7)

| Row | Frozen expected | Ledger fact | Agreement |
|---|---|---|---|
| E01-wrong-destination-paper-strict / -minimal | CONDITIONAL / SPEC_GAP | paper `policyEnf` (ACSC.sol:140-167) has no destination binding: it grants on another deployment's forwarded tuple (recipient 0, +30) | yes (class) |
| E01-wrong-destination-repaired-e | REJECT / REPAIR_SUPPORTED / WRONG_DESTINATION | DecisionVerifier step 1, **line 60** (`r.sourceChainId/psc != ctx`), fires first; step 2, lines 61-64 (destination chain/KSSC), also mismatches | yes |
| E01-expiry-boundary-paper-strict / -minimal | CONDITIONAL / SPEC_GAP | the forwarded tuple has no request expiry; `policyEnf` grants at DBC time == request expiry, with expiry block + grantTtl (line 154) | yes (class) |
| E01-expiry-boundary-repaired-e | REJECT / REPAIR_SUPPORTED / EXPIRED | step 9, **line 74**, uses `>=`, so consumption exactly at the expiry is rejected | yes |

**Line correction:** your message cited step 1 as line 59 and step 2 as lines 60-63. At 933d2a7 they
are line 60 and lines 61-64; line 59 is `AccessDecision memory d = c.decision`. The plan cites the
pinned lines.

**No disagreement between the catalog and the ledger was found.**

## Recipe (`integration-plan.json` sha256 d4fa294e..)

Each of the 6 rows runs on a fresh chain pair: PBC port 18545, DBC port 18546, chain IDs
18545/28545.

- **D1** runs the controls: wrong-admin 16; Alice allow with release and one outcome; Bob deny 9.
- **A (D2)** is a fresh deployment with its own bootstrap, adapter and 0700 state (`kind=destination`).

**Source deployment B (wrong-destination rows only):**

- B is a **third deployment on the same chain pair**: the same chain ids, different contract
  addresses.
- It is created by the same **pinned owner commands** as D2, recorded with exact argv in
  `commands.json`:
  - `deploy_local.sh <pbc> <dbc> <profile> <log-mode> <runId>-source` (label `owner-deploy-source`);
  - `bootstrap_fixture.sh <pbc> <B deployment> <out>` (label `owner-bootstrap-source`).
- B has its own adapter and 0700 state.

**Funding:**

- Relay and CA-admin balances are reset to 1000 ETH before B, exactly as before D2.
- The relay balance on both chains is recorded after A's deploy and bootstrap, and before and after
  B's deploy (`destinationFunding` in the case manifest). This shows each deployment fits; A1-0039
  gives about 400 ETH per deployment.
- B's `deployment.json` (`source-instance/deployment.json`) and its sha256 (`sourceDeployment`) are
  bound into the evidence.

**Wrong destination** (REQUEST_ACCESS > SUBSTITUTE_DESTINATION > FORWARD_OR_CONSUME):

1. **REQUEST_ACCESS on B:** B's PSC, destination B's KSSC. Repaired-e also collects B's checkpoint
   and **one** decision through B's adapter.
2. **SUBSTITUTE_DESTINATION:** B's request, certificate and records are submitted at A **without
   rewriting any signed field**. `substitution.json` records `r.sourceChainId`, `r.psc`,
   `r.destinationChainId` and `r.kssc` against A's and B's bindings.
3. **Repaired-e:** A's `consumeDecision` gives `Rejected(3)`, with `firingStep: 1`, plus
   `step2Mismatch: true`. Nothing changes at A. B is untouched: its request is forwarded, with no
   grant and the nonce unused.
   - **This row cannot kill MUT_NO_DESTINATION_BINDING**, because step 1 still fires (A1-0039 G-3).
     A collector test shows the step-2-skipping double still rejects at step 1.
   - A kssc-only rewrite is not substituted for the catalog row.
4. **Paper:** A's `policyEnf` with B's forwarded tuple (`pbcRequestId` = B's digest, which A's PBC
   does not have: `getRequest` gives status 0) and B's records.
   - Authority roots are deterministic label keys, so the records evaluate equally at A, giving a
     grant (recipient 0, +30).
   - This is a chosen completion under compromised-relay stress, outside A01.

**Expiry boundary** (REQUEST_ACCESS > ADVANCE_CLOCK > FORWARD_OR_CONSUME):

1. **REQUEST_ACCESS:** the request, plus on repaired-e the checkpoint and **one** decision.
2. **ADVANCE_CLOCK:** `evm_setNextBlockTimestamp(r.expiresAt)` on the **DBC only**, with **no
   `evm_mine`**. The consumption is the next mined block.
3. Its timestamp is **verified** to equal `r.expiresAt` exactly, not +1.
4. **Repaired-e:** the oracle requires `d.expiresAt == r.expiresAt` and `cp.expiresAt > r.expiresAt`.
   Step 9 (line 74) then fires on equality, giving `Rejected(7)` with `firingStep: 9`. If the
   decision were capped lower, the oracle refuses the row; that would be reported as the decision
   clause.
5. **Paper:** `policyEnf` mined at DBC time == request `expiresAt` grants with the fill block +
   grantTtl. Both the request expiry and the grant expiry are recorded.
6. **Supplementary `eth_call` at expiresAt − 1:** skipped, as your condition 8 allowed.

**A31:** exactly one `collect_decision` per request in repaired-e (`decisionCollections`), zero in
paper.

**D49:** the workers of both deployments stay verified never-instantiated at baseline and after every
catalog step. The adapter operations are `prepare_request`, `collect_checkpoint` and
`collect_decision` only.

## Verification (`manifest.json`)

**RED first:** your conditions 1-12 were written into the tests before any SL7 code: **102 failed**
(`red-before-implementation.txt`): 71 oracle-module-missing, 18 collector-module-missing and 13
`create_plan(destination_stress)` errors. **No test was changed after RED.**

**GREEN:**

- oracle 71 passed and collector 18 passed;
- every oracle mutation fails at its intended check (`oracle-reasons.txt`);
- 7/7 collector controls and 4 unsupported selections fail for the intended reason
  (`control-reasons.txt`);
- plan tests: 13 passed;
- full suite: `.venv/bin/python -m pytest -q -rs` exit 0, **1596 passed, 0 failed, 0 skipped**, 453 s; the bracket of 3724 files is stable.

## Limits

- **Not yet run live:** the third deployment on one chain pair, the DBC timestamp pin without
  `evm_mine`, and the cross-deployment submission. All are unit-tested only, against TEST-ONLY doubles.
- **MUT_NO_DESTINATION_BINDING** is not killable by this catalog recipe.
- Symbolic adapter; safe-ledger, trusted-worker and one-trusted-witness assumptions.
- **Do not touch these files before the run.** All `agent3Sources` are frozen. Store helper scripts as
  `.py.txt`.
