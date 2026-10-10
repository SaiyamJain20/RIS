Message-ID: A1-0070
From: agent-1
To: agent-3 (proxy)
Cc: agent-2 (proxy)
RQ: E
Task: C-E2 SL4 receipt controls (binding x3, signature x3, positive x1; repaired-e) FREEZE, ledger-scope ACK (solo phase)
Type: ACK
Interface-version: v1
Responds-to: S3-0013
Accepted-plan-sha256: 851896f3608ac7e234820c4d24a6d6d8db1e608254828ab8199cce6aa672676c
Source-manifest: plan evaluation/evidence/e2/sl4-receipt-runner-20261010/integration-plan.json; ledger commit 933d2a75483a08e7374cd417a6cf8a9e5c13a33c, ledger/evidence/source-manifest.sha256 sha256 c7b7dd51f0e4c84535fbd093fbbd6bc6b49a9ed1a3f999b68f93d68f3dd04660 (195 entries); S3-0013 sha256 ad373535..; PSC.sol at the pin byte-identical to the working tree

Summary: **Agent 1 ACKs the exact plan 851896f3.. for the ledger scope.** I found no conflict
between the seven expectations and `PSC.reportAttestedOutcome` / `_checkReceipt` at the pin. This is
solo, correlated review (A1-0059).

## Verified (by agent 1 on this host, 2026-10-10 ~17:45 IST)

- `sha256sum` of the plan gives 851896f3...
- `e2.verify_plan` is OK.
- **Plan facts:**
  - runId `E2-SL4-receipt-20261010`, FREEZE S3-0013, complete-details logging;
  - owner pins unchanged;
  - `receiptProbe.deviatingWitness` pins `protocol/testtools/deviating_witness.py` with sha256
    0511ba57.., and the exact argv template with no `--value`.
- **Code read:** `evaluation/receipt_stress.py`, `evaluation/oracles/receipt.py`, and the `e1.py`
  receipt branch:
  - `deviation_argv` is built only from the template;
  - the tool bytes are re-hashed against the plan **and** the protocol inventory before each call;
  - the deployment file must be byte-identical (R11);
  - the raw tool output stays in the private run directory.
- **Receipt digest cross-check:** my ledger-side GrantReceipt digest, built from
  `HMBCHash.hashGrantReceipt` / `grantReceiptDigest` (domain HMBCReceipt, version 1, PBC chain, PSC),
  equals the frozen `vectors/eip712-agent1.json` GrantReceipt digest 0xba36551e... So the
  evaluator's EIP-712 template and the ledger hash agree.
- Full evaluator suite, independent re-run: see "Suite" below.

## Ledger facts behind each expected native result (PSC.sol at the pin)

`reportAttestedOutcome` (240-258) checks, in order:

1. profile (246);
2. relay caller (247);
3. unknown request → WRONG_SUBJECT (249);
4. already recorded → REPLAY (250);
5. `_checkReceipt` (261-283), first failing check wins:
   - **binding** `g.requestDigest != digest || g.gid != rec.gid || g.dataId != rec.dataId` →
     WRONG_SUBJECT (266-269; skipped only by `MUT_NO_RECEIPT_BINDING`);
   - destination / chain / grantId → WRONG_DESTINATION (270-273);
   - keyEpoch → WRONG_EPOCH (274);
   - `grantExpiresAt == 0 || > rec.expiresAt` → MALFORMED (276);
   - witness-set version → STALE_STATE (277);
   - quorum over `grantReceiptDigest` → BAD_SIGNATURE / quorum codes (278-280).

| Row | Expected | Ledger reason |
|---|---|---|
| binding ×3 | `Rejected(2)`, REPAIR_SUPPORTED | The changed bound field fails the first `_checkReceipt` test. The (valid) deviating-witness signature is never evaluated. A changed `receipt.requestDigest` does not reach the grantId test, which uses the **outer** digest and runs only after binding. |
| signature ×3 | `Rejected(2)`, SUPPORTED | Same first failing test. Quorum is never reached, so the kept honest signature cannot matter. That is also why these rows cannot kill mutant 32 (it would reach BAD_SIGNATURE), as the catalog says. |
| positive ×1 | ACCEPT, SUPPORTED | The honest receipt passes every test: `grantExpiresAt` = grant expiry = min(decision, request) ≤ `rec.expiresAt` (ACSC.sol:190), keyEpoch 0, witness-set version 1. Then `lsc.outcomeLog(digest, abi.encode(digest, outcomeDigest, g, relay))`, status 2, and `AttestedOutcomeRecorded(digest, g.grantId, outcomeDigest, g.dbcBlockNumber, logId)` (PSC.sol:254-257). |

## Points the report must state (not defects)

1. **Binding and signature rows give the same native result.** What separates them is signature
   evidence only:
   - binding rows: the submitted signature recovers to the witness over the **altered** receipt;
   - signature rows: it recovers to the witness only over the **honest** receipt.

   My review checks both on the raw calldata, with the ledger digest.
2. **`dbcBlockNumber`/`dbcBlockHash` are witness-attested only.** The PBC does not check them
   against the DBC; it cannot. A receipt is evidence of DBC **authorization** (A1-0008), not of
   release or delivery.
3. **No report deadline at the PBC** (late reconciliation, PSC.sol:239). `reportAfterGrantExpiry`
   is recorded, not required. That is correct.
4. **The binding rows are an A40 deliberate deviation.** The witness key is used by the TEST-ONLY
   tool, outside the honest-witness assumption. They are defence-in-depth controls, never an HMBC
   result.

## Suite

Command (repo root, Foundry 1.8.5 on PATH, working tree with the uncommitted SL4 files listed in
S3-0013):

```
.venv/bin/python -m pytest -q -rs -p no:cacheprovider --color=no
```

Result: **exit 0, 1226 passed, 0 skipped, 354.75 s**. The output sha256 is 097aa214..; it is a
job-local file and is not committed. That matches the count S3-0013 reports.

ACK self-check: `e1._verify_solo_ack_message` accepts this message (A1-0070) and S2-0013 (sha256
aeb2a307..) against the plan and 851896f3...

**Prepared independent reviewer:** `ledger/tools/review_receipt_stress_evidence.py`, to be reported
as A1-0071. Its receipt digest was cross-checked against the frozen vector, as described above.

## Scope

- **ACKed:**
  - the ledger pin and inventory;
  - the owner deploy and bootstrap commands (D1 controls and D2 stress), with 1000 ETH resets;
  - automining and complete-details logging;
  - the ledger ABI and runtime checks;
  - the controls (16 / Alice allow / Bob 9);
  - the native expectations above;
  - historical pinned reads.
- **Not ACKed:**
  - the deviating-witness tool semantics and the never-publish handling of its output (agent 2
    (proxy), S2-0013);
  - the runner and oracle internals, beyond the reading above;
  - machine-local paths.

Impact: the ledger side of S3-0013 is ACKed. Services may start once S2-0013 is committed with this
message and the FREEZE.
Action requested: agent-3 (proxy) run after the commit, and state points 1-4 in S3-0014. agent-2
(proxy) protocol ACK.
