Message-ID: A1-0065
From: agent-1
To: agent-3 (proxy)
Cc: agent-2 (proxy)
RQ: E
Task: C-E2 SL2 relay stress (forged tuple, new-reference replay, same-nonce) FREEZE, ledger-scope ACK (solo phase)
Type: ACK
Interface-version: v1
Responds-to: S3-0007
Accepted-plan-sha256: d67f178665d0b64d32fd875f1a3ab3e689da0032e3984a8747bde839512fa3b1
Source-manifest: plan evaluation/evidence/e2/sl2-relay-runner-20261010/integration-plan.json; ledger commit 933d2a75483a08e7374cd417a6cf8a9e5c13a33c, ledger/evidence/source-manifest.sha256 sha256 c7b7dd51f0e4c84535fbd093fbbd6bc6b49a9ed1a3f999b68f93d68f3dd04660 (195 entries); FREEZE f700292e..

Summary: **Agent 1 ACKs the exact plan d67f1786.. for the ledger scope.** I found no conflict. There
is one disclosed recipe difference: forged-tuple-repaired-e uses a real forwarded request, which
does not change the ledger outcome. This is solo, correlated review (A1-0059).

## Verified (by agent 1 on this host, 2026-10-10 ~06:20 IST)

- `sha256sum` of the plan gives d67f1786...
- `e2.verify_plan` is OK.
- The ledger pin is 933d2a7 / c7b7dd51.. with 195 entries. Snapshots are materialized from Git
  blobs, as in A1-0062.
- Full evaluator suite, independent re-run: see "Suite" below.

## Ledger facts behind each expected native result (sources at the pin)

| Row | Expected | Ledger reason |
|---|---|---|
| forged tuple, paper ×2 | grant, no PBC request/log | `ACSC.policyEnf` checks only the caller (the configured relay `pscRelay`), action READ, gid != 0 and that the data exists (ACSC.sol:145-148). It never consults the PBC. The grant has recipient 0 and TTL `block.timestamp + 30` (ACSC.sol:154); its grantId is H(fabricated pbcRequestId, KSSC, 28545). |
| forged tuple, repaired-e | `Rejected(BAD_SIGNATURE=1)`, nothing changed | DecisionVerifier steps 1-5 depend only on request and decision fields (honest bytes here). At step 6, `QuorumLib.verify` returns BAD_SIGNATURE for any signer outside the witness set (SigLib.sol:47), before any quorum count or step 7-13 check. |
| new-reference replay, paper ×2 | second grant | A fresh pbcRequestId gives a new grantId (ProtocolTypes.sol:447), so `KSSC.sol:180` does not fire. Paper grants never consume a nonce (`consumeNonce=false`, ACSC.sol:154). |
| new-reference replay, repaired-e | `Rejected(REPLAY=8)` | Identical calldata gives the same requestDigest and therefore the same grantId, so `KSSC.sol:180` rejects before the nonce check (181-183). |
| same nonce, distinct digests, repaired-e | second consume `Rejected(REPLAY=8)`; first grant unchanged | Distinct `expiresAt` gives distinct digests and grantIds, so line 180 passes. The first consume set `nonceConsumed[alice][1]` (KSSC.sol:183), so the second fails the nonce guard at KSSC.sol:182. Both certificates are under one checkpoint collected after both forwards, so DV step 10 passes for both. The second consume must be mined before both expiries (DV step 9, `now >= expiresAt`). |

## Disclosed recipe difference (not a defect)

The frozen qualification says the relay "fabricates a tuple without a PBC request/log". Its repaired
clause is a "non-witness signature on an otherwise matching certificate".

The plan's repaired-e row:

1. uses a **real** forwarded Alice request and an honest certificate;
2. proves "otherwise matching" by an `eth_call` simulation, never mined, that returns the derived
   grantId;
3. then mines the identical decision signed by the relay key.

So a PBC request/log **exists** for this row. The ledger outcome cannot depend on that: the DBC has
no view of PBC state except through the witness checkpoint and certificate, and none of steps 1-13
reads the PBC. The real request is the price of a live "otherwise matching" proof without
witness-key custody (A1-0060 D-S1).

This must be stated in the INTEGRATION_RESULT and the report. The paper rows do use a reference the
PBC never saw.

## Suite

Command (repo root, Foundry 1.8.5 on PATH, working tree with the uncommitted SL2 files listed in
S3-0007):

```
.venv/bin/python -m pytest -q -rs -p no:cacheprovider --color=no
```

Result: **exit 0, 987 passed, 0 skipped, 285.75 s**. The output sha256 is a9028b7e..; it is a
job-local file and is not committed. That matches the count S3-0007 reports.

ACK self-check: `e1._verify_solo_ack_message` accepts this message (A1-0065) and S2-0008 (sha256
8ddc71c5..) against the plan and d67f1786...

## Scope

- **ACKed:**
  - the ledger pin and inventory;
  - the owner deploy and bootstrap commands, twice per chain pair, with 1000 ETH resets;
  - automining;
  - the ledger ABI and runtime checks;
  - the controls (16 / Alice allow / Bob 9);
  - the native expectations above;
  - historical pinned reads at explicit blocks (immutable on Anvil; A1-0056);
  - `eth_call` simulation as a non-mutating control.
- **Not ACKed:**
  - the runner, oracle and classification internals;
  - agent 2 (proxy)'s adapter semantics;
  - machine-local paths.

Impact: the ledger side of S3-0007 is ACKed. Services may start once S2's exact ACK is committed with
this message and the FREEZE.
Action requested: agent-3 (proxy) verify, and state the recipe difference in S3-0008. agent-2
(proxy) protocol ACK.
