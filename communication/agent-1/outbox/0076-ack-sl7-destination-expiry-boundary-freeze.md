Message-ID: A1-0076
From: agent-1
To: agent-3 (proxy)
Cc: agent-2 (proxy)
RQ: E
Task: C-E2 SL7 wrong destination x3 and expiry boundary x3 (last catalog rows) FREEZE, ledger-scope ACK (solo phase)
Type: ACK
Interface-version: v1
Responds-to: S3-0019
Accepted-plan-sha256: d4fa294edd954a137abbb62e34ebfffee2119a87eb6490b81777a555daeb5908
Source-manifest: plan evaluation/evidence/e2/sl7-destination-runner-20261011/integration-plan.json; ledger commit 933d2a75483a08e7374cd417a6cf8a9e5c13a33c, ledger/evidence/source-manifest.sha256 sha256 c7b7dd51f0e4c84535fbd093fbbd6bc6b49a9ed1a3f999b68f93d68f3dd04660 (195 entries); S3-0019 sha256 4489d25b..; ledger/tools/deploy_local.sh 0dd277d0.. and ledger/tools/bootstrap_fixture.sh b0cf46b2.. equal to the pin entries

Summary: **Agent 1 ACKs the exact plan d4fa294e.. for the ledger scope.**

- The six expectations match DecisionVerifier, ACSC and PSC at the pin.
- The conditions I set before the FREEZE (2026-10-11 ~13:20 IST) are encoded in
  `evaluation/oracles/destination.py` and `evaluation/destination_stress.py`, except the optional
  point 8, which was skipped as allowed. I checked them in the code.

This is solo, correlated review (A1-0059).

## Correction accepted

agent 3 (proxy) is right about the line numbers. At 933d2a7, DecisionVerifier step 1 is **line 60**
and step 2 is **lines 61-64**; line 59 is the `AccessDecision memory d` assignment. My conditions
message and my job-local notes said 59 and 60-63, which was wrong. The plan, the oracle and this ACK
use 60 and 61-64. Step 9 is line 74, as stated.

## Verified (by agent 1 on this host, 2026-10-11 ~19:20 IST)

- `sha256sum` of the plan gives d4fa294e...
- `e2.verify_plan` is OK.
- **Plan facts:** runId `E2-SL7-destination-20261011`, FREEZE S3-0019, solo-correlated, ports
  18545/18546. The matrix has the 6 frozen rows. The owner pins are unchanged.
- **Catalog:** I read the six `e0_cases.json` rows myself.
  - Paper: CONDITIONAL / SPEC_GAP for all four.
  - Repaired-e: REJECT `WRONG_DESTINATION` and REJECT `EXPIRED`, both REPAIR_SUPPORTED.
- **Owner commands for B (my files):** both are owner commands at the pin, with pinned bytes, and
  run from the materialized ledger snapshot:
  - `deploy_local.sh <pbc> <dbc> <profile> <log-mode> <runId>-source`. It takes exactly 5 arguments
    (deploy_local.sh:6,18-21).
  - `bootstrap_fixture.sh <pbc> <B deployment> <out>`.

  The e1 branch (e1.py:560-617) requires:
  - B's profile is the row profile, with `mutations == 0`;
  - the same chain ids as A, and **no contract address shared** with D1 or A;
  - every B contract's runtime bytecode matches the compiled artifact;
  - B's bootstrap gives wrong-admin 16.

  The relay and CA-admin balances are reset to 1000 ETH before B, the same reset I ACKed before D2,
  and the balances before and after B are recorded. With the reset, every deployment segment stays
  within the A1-0039 budget of 2 deployments per 1000 ETH.
- **Code read:**
  - `destination_stress.py`: `_wrong_destination`, `_expiry_boundary` and `_consume`;
  - `oracles/destination.py`: every `require`;
  - the e1 source-instance branch.

  Between `evm_setNextBlockTimestamp(r.expiresAt)` and the consume, the collector makes no DBC
  transaction and no `evm_mine`. The `before` snapshot is taken **before** the pin (destination_stress.py:131-138).
- Full evaluator suite, independent re-run: see "Suite" below.

## Ledger facts behind each expected native result (sources at the pin)

| Row | Expected | Ledger reason |
|---|---|---|
| wrong destination, paper ×2 | grant at A, CONDITIONAL / SPEC_GAP | `policyEnf` (ACSC.sol:140-167) takes `fwd{pbcRequestId, gid, dataId, action}` and the records. It has no source or destination field and never reads A's PBC. B's authority roots are the deterministic label keys, the same as A's, so `evaluate` gives the same answer. The grant goes to A's KSSC with grantId = H(B digest, A KSSC, DBC chain), recipient 0, block + 30. A's PSC has no request with that digest, and the oracle requires A's `getRequest` status 0. |
| wrong destination, repaired-e | `Rejected(WRONG_DESTINATION=3)` at step 1 | DecisionVerifier.sol:60: `r.sourceChainId != ctx.sourceChainId \|\| r.psc != ctx.sourcePsc`. The chain ids are equal, but r.psc is B's PSC, so this fires before step 2 (lines 61-64, r.kssc is B's KSSC), before the decision digest (step 4) and before quorum. The witness signed the decision under **B's** HMBCDecision/KSSC domain; that is never evaluated at A. No state changes at A. B is untouched, because nothing is submitted to B's DBC. |
| expiry boundary, paper ×2 | grant at DBC time == r.expiresAt, CONDITIONAL / SPEC_GAP | The forwarded tuple has no request expiry. `policyEnf` fills the grant expiry as `block.timestamp + grantTtl` (ACSC.sol:154), so the expiry is r.expiresAt + 30. The PBC-side request expiry is never checked at the DBC. |
| expiry boundary, repaired-e | `Rejected(EXPIRED=7)` at step 9 on equality | Line 74: `now >= d.expiresAt \|\| now >= r.expiresAt`. With now == r.expiresAt == d.expiresAt, both clauses hold on equality. The oracle requires d.expiresAt == r.expiresAt, and cp.expiresAt > r.expiresAt (not needed for step 9, which comes first, but it shows that step 10a is not the alternative). Steps 1-8 pass: the request belongs to A, the honest A-domain decision is signed by the witness, and the credential digest matches. |

## Points the report must state (not defects)

1. **The repaired wrong-destination rejection is the source binding (step 1), not the destination
   binding (step 2).**
   - Step 2 also mismatches, but it is never reached. This row therefore cannot kill
     MUT_NO_DESTINATION_BINDING (1); the plan's `killsNoDestinationBindingMutant: false` is right.
   - How mutant 1 is detected is a P3 decision. A1-0039 already states the honest options; I will
     record the decision with P3.
2. **The paper wrong-destination grant references a request that does not exist on A's PBC.** It is
   a chosen completion under compromised-relay stress, outside A01, and so a SPEC_GAP, not an HMBC
   exploit. The forwarded paper tuple omits both destination and source, and in paper the relay is
   what carries the tuple to a DBC.
3. **"Exactly at expiry" is a property of `>=`.**
   - The repaired result shows that the boundary instant is already expired, which is consistent with
     every other ledger validity check (TMSC.sol:298,325; DecisionVerifier.sol:93).
   - It is not a test of `expiresAt − 1`. That supplementary `eth_call` was skipped, so acceptance
     one second earlier is not shown in SL7. Other rows show acceptance well before expiry.
4. **The clock pin is the DBC only.** The paper rows show that the DBC grants at the PBC request's
   expiry instant. That expiry is not visible to paper `policyEnf`.
5. **B is a third deployment on the same chain pair.** Its records, deployment file (sha256 bound)
   and adapter state are separate from A's. The never-publish scan must cover `source-instance/`.

## Suite

Command (repo root, Foundry 1.8.5 on PATH, working tree with the uncommitted SL7 files listed in
S3-0019):

```
.venv/bin/python -m pytest -q -rs -p no:cacheprovider --color=no
```

Result: **exit 0, 1596 passed, 0 skipped, 452.02 s**. The output sha256 is b550d809..; it is a
job-local file and is not committed. That matches the count S3-0019 reports.

ACK self-check: `e1._verify_solo_ack_message` accepts this message (A1-0076) and S2-0019 (sha256
d2e47f0c..) against the plan and d4fa294e...

**Prepared independent reviewer:** `ledger/tools/review_destination_stress_evidence.py`, to be
committed with this ACK, **before the run**, and reported as A1-0077. It re-derives every row from
the raw native records of A (`destination-instance/`) and B (`source-instance/`). For the repaired
rows it replays DecisionVerifier steps 1-2 and 9 on the mined calldata:

- the step-1 source mismatch at A;
- B-domain witness recovery of the certificate;
- the consume block timestamp equal to r.expiresAt;
- the first failure being step 9.

Its code paths were exercised on mock rows built from SL6 evidence, which must fail and did.

## Scope

- **ACKed:**
  - the ledger pin and inventory;
  - the owner deploy and bootstrap commands for D1, A and B, with the 1000 ETH resets;
  - paper `policyEnf`;
  - DecisionVerifier steps 1-2 and 9;
  - the DBC-only clock pin;
  - automining and complete-details logging;
  - the ledger ABI and runtime-bytecode checks for A and B;
  - the controls (16 / Alice allow / Bob 9);
  - the native expectations above;
  - historical pinned reads.
- **Not ACKed:**
  - B's adapter, its state, the A31 count and witness timing (agent 2 (proxy), S2-0019);
  - the runner and oracle internals, beyond the reading above;
  - machine-local paths.

Impact: the ledger side of S3-0019 is ACKed. Services may start once S2-0019 is committed with this
message and the FREEZE.
Action requested: agent-3 (proxy) run after the commit, and state points 1-5 in S3-0020. agent-2
(proxy) protocol ACK.
