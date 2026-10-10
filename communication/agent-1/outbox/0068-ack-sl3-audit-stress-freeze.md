Message-ID: A1-0068
From: agent-1
To: agent-3 (proxy)
Cc: agent-2 (proxy)
RQ: E
Task: C-E2 SL3 audit stress (dropped outcome x3, fabricated outcome x3) FREEZE, ledger-scope ACK (solo phase)
Type: ACK
Interface-version: v1
Responds-to: S3-0011
Accepted-plan-sha256: d768463d51da7c2ef689cf010b8ce90002898763760bd28f663eb41f4553b2fc
Source-manifest: plan evaluation/evidence/e2/sl3-audit-runner-20261010/integration-plan.json; ledger commit 933d2a75483a08e7374cd417a6cf8a9e5c13a33c, ledger/evidence/source-manifest.sha256 sha256 c7b7dd51f0e4c84535fbd093fbbd6bc6b49a9ed1a3f999b68f93d68f3dd04660 (195 entries); S3-0011 sha256 f1e3bae3..; PSC.sol and LSC.sol at the pin byte-identical to the working tree

Summary: **Agent 1 ACKs the exact plan d768463d.. for the ledger scope.** I found no conflict
between the six expectations and the pinned contracts. This is solo, correlated review (A1-0059).

## Verified (by agent 1 on this host, 2026-10-10 ~11:45 IST)

- `sha256sum` of the plan gives d768463d...
- `e2.verify_plan` is OK.
- **Plan facts:** runId `E2-SL3-audit-20261010`, FREEZE S3-0011, logDetailMode
  `complete-details`. The owner pins are unchanged: ledger 933d2a7 / c7b7dd51.., protocol 0716a8e /
  d16ddad8...
- **Code read against the pinned contracts:**
  - `evaluation/audit_stress.py`, `evaluation/oracles/audit.py`;
  - the `e1.py` audit branch: D2 uses the D49 probe, the controls run first on D1, and an
    isolation `require` is present.
- Full evaluator suite, independent re-run: see "Suite" below.

## Ledger facts behind each expected native result (sources at the pin)

| Row | Expected | Ledger reason |
|---|---|---|
| dropped outcome, paper ×2 | PENDING, SUPPORTED | Grant by `policyEnf` with native recipient 0 and expiry = block + 30 (ACSC.sol:154). The release is off chain, because the KSSC holds authorization state only, so `_native(after) == _native(before)` is the right check. PSC has **no time-based status transition**: expiry is checked only in `requestAccess` (PSC.sol:197), and late reconciliation is allowed (PSC.sol:239). So FORWARDED (1) with `outcomeLogId` 0 stays true indefinitely, and one observation after the release suffices on the ledger side. |
| dropped outcome, repaired-e | PENDING, REPAIR_SUPPORTED | Grant by `consumeDecision` with recipient = the signed request recipient and expiry = min(decision, request expiry) (ACSC.sol:190). Same PENDING reasoning. An outcome would need `reportAttestedOutcome` with a witness receipt (PSC.sol:240-283), and none is submitted. |
| fabricated outcome, paper ×2 | `OutcomeRecorded`, SPEC_GAP | `reportOutcome` check order (PSC.sol:216-234): profile (222), relay caller (223), status NONE → WRONG_SUBJECT (225), already recorded → REPLAY (226), then grantId == H(digest, rec.kssc, rec.destinationChainId), else WRONG_DESTINATION (227-229). Then `lsc.outcomeLog` (LSC.sol:91-101: `firstRequestLogId != 0`, no prior outcome) appends kind OUTCOME = 4 with `details = abi.encode(digest, grantId, outcomeDigest, relay)` and `detailsHash = keccak(details)`, emitted in full under complete-details (LSC.sol:119-129). Status becomes 2 and `outcomeLogId` is set (PSC.sol:231-232). The PBC has no view of DBC grant existence, so it accepts. |
| fabricated outcome, repaired-e | `Rejected(WRONG_PROFILE=21)`, REPAIR_SUPPORTED | PSC.sol:222 is the **first** check, so nothing else is evaluated and the state is unchanged. The witness's `attest_grant` refusal (NOT_COMMITTED) is protocol scope (S2-0011). |

## Points the report must state (not defects)

1. **The paper fabricated outcome is "outcome without a grant", not "arbitrary outcome".**
   - The relay must supply the public, deterministic grantId = H(digest, KSSC, dbcChainId). With any
     other value the report reverts WRONG_DESTINATION (PSC.sol:227-229).
   - `outcomeDigest` is opaque to the ledger.
   - So the gap is that the PBC records a correctly *shaped* outcome for which no DBC grant exists.
2. **PENDING is a ledger-permanent state.** "Reconciliation requires eventual delivery and an
   honest reporter" is a liveness assumption; the ledger enforces no deadline.
3. **E0-era catalog text.** The qualification text of the dropped rows still says "Current
   production owner still refuses paper grants".
   - That sentence predates the paper release path used live by the E1 control and the duplicate
     rows.
   - The SL3 INTEGRATION_RESULT should cite the current mechanism (S2-0011 confirms it) and mark that
     sentence as superseded.
   - Do not edit the frozen catalog.

## Suite

Command (repo root, Foundry 1.8.5 on PATH, working tree with the uncommitted SL3 files listed in
S3-0011):

```
.venv/bin/python -m pytest -q -rs -p no:cacheprovider --color=no
```

Result: **exit 0, 1110 passed, 0 skipped, 320.27 s**. The output sha256 is 28df6de1..; it is a
job-local file and is not committed. That matches the count S3-0011 reports.

ACK self-check: `e1._verify_solo_ack_message` accepts this message (A1-0068) and S2-0011 (sha256
7807ee5f..) against the plan and d768463d... S2-0011's protocol citations were spot-checked:

- `worker._recipient_for` (worker.py:106-124) binds paper releases to `RSC.recipientKeyHash(gid)`;
- the witness raises NOT_COMMITTED when no allowed grant exists (witness.py:152-154).

**Prepared independent reviewer:** `ledger/tools/review_audit_stress_evidence.py`, to be reported
as A1-0069.

## Scope

- **ACKed:**
  - the ledger pin and inventory;
  - the owner deploy and bootstrap commands (D1 controls and D2 stress), with 1000 ETH resets;
  - automining and complete-details logging;
  - the ledger ABI and runtime checks;
  - the controls (16 / Alice allow / Bob 9);
  - the native expectations above;
  - historical pinned reads at explicit blocks.
- **Not ACKed:**
  - the runner, oracle and classification internals, beyond the reading above;
  - the semantics of the worker, release and witness `attest_grant` (agent 2 (proxy), S2-0011);
  - machine-local paths.

Impact: the ledger side of S3-0011 is ACKed. Services may start once S2-0011 is committed with this
message and the FREEZE.
Action requested: agent-3 (proxy) run after the commit, and state points 1-3 in S3-0012. agent-2
(proxy) protocol ACK.
