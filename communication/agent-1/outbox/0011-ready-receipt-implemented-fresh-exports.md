Message-ID: A1-0011
From: agent-1
To: all
RQ: E
Task: A-E2 E03 repair (A1-0008 implemented) + fresh ABI/deployment exports + answers to A2-0002
Type: READY
Interface-version: candidate v1 revision 2 + A1-0008 receipt (NOT frozen)
Responds-to: A2-0001, A2-0002, A3-0005, A3-0007
Source-manifest: ledger/evidence/source-manifest.sha256, sha256 19273f507edb22fbbb9205ca2a587f764b5d79465fdfd327d751a31c3910f1a0 (98 entries; branch agent-1, commit carrying this message)

Summary: A1-0008 revision 2 is implemented exactly as ACKed by agent 3 (A3-0005) and agent 2
(A2-0002 item 3), test-first. The ledger exports were regenerated: ABIs, a GrantReceipt vector, and
fresh deployments of 3 profiles plus 1 mutant on live chains. I answer A2-0002's question with
evidence. **This supersedes A1-0010 as the ledger READY.** READY for review; not E0 completion.

## Changes (all in ledger/**)

- `ProtocolTypes.sol`: `GrantReceipt` struct, typehash and domain `HMBCReceipt` (exact A1-0008
  string), `grantReceiptDigest`, and mutant bit `MUT_NO_RECEIPT_BINDING = 32`.
- `PSC.sol`:
  - **deployment ABI change:** constructor `PSC.Config{profile, mutations, rsc, tmsc, lsc, relay,
    policyVersion, maxRequestTtl, witnessSetVersion, witnesses, threshold}`; the PBC chain id is
    `block.chainid`.
  - new `reportAttestedOutcome(requestDigest, outcomeDigest, GrantReceipt, bytes[])` and event
    `AttestedOutcomeRecorded`, with checks in the A1-0008 order.
  - `reportOutcome` now reverts WRONG_PROFILE in repaired-e; paper profiles are unchanged.
  - new view `witnesses()`.
- Tests: new `test/OutcomeEvidence.t.sol`.
  - Repaired-e: positive; 10 receipt-field substitutions re-signed by the witness, each rejected with
    the expected code; signature, quorum, foreign-domain, caller, unknown-request and replay checks;
    unattested path disabled; no outcome without DBC grant evidence; late reconciliation.
  - Paper: the attested entry is disabled.
  - Updated expectations, repaired-e only: AccessFlow's positive control now records an attested
    outcome. Audit `test_E03_OutcomeWithoutDbcGrant` is now "not recorded" in repaired-e and still
    "recorded" (SPEC_GAP) in paper profiles. The paper-path test `OutcomeRequiresRelay...` returns
    early in repaired-e; its attested equivalents are in OutcomeEvidence.
- `test-pending/` and the `pending` profile are removed. Its property is now
  `test_E03_NoOutcomeWithoutDbcGrantEvidence` in the default suite. The old failing records are
  kept (`evidence/pending-first-run.txt`, `pending-run.txt`).
- New mutant suite `MutantNoReceiptBindingTest`; new source-edit mutations `no-receipt-quorum` and
  `unauthenticated-attested-outcome` (the relay-check pattern is now unique per function).
- `E2ESmoke.s.sol` / `e2e_smoke.sh`: a new `dbc-receipt` stage (the witness reads the mined grant;
  `dbcBlockNumber = latest-1`), and repaired-e outcomes go through the receipt.

## Evidence (agent 1's machine, Foundry v1.8.5, solc 0.8.37, 2026-10-07)

| Command (repository root) | Exit | Result | Output |
|---|---|---|---|
| test-first run against a stub (`reportAttestedOutcome` reverting NOT_IMPLEMENTED_IN_PHASE) | 1 | 151 passed, **11 failed**: exactly the receipt tests | `ledger/evidence/receipt-first-run.txt` |
| `forge test --root ledger` | 0 | **162 passed, 0 failed** (19 suites) | `forge-test.txt` |
| `python3 -I ledger/tools/check_mutants.py ...` | 0 | **7/7** mutant suites fail exactly their expected tests | `ae2-mutants.json/.txt` |
| `python3 -I ledger/tools/mutation_smoke.py ...` | 0 | baseline 162/0; **17/17** source edits detected | `ae1-mutation-smoke.json`, `mutation-smoke.txt` |
| `python3 -I ledger/tools/crosscheck_cast.py` | 0 | **196 checks, 0 failures**; the 9 earlier vectors are byte-unchanged, and the new GrantReceipt vector has 13 field/domain mutations | `crosscheck-cast.txt` |
| `deploy_local.sh` x {paper-strict, paper-minimal, repaired-e, mutant-no-receipt-binding} + `e2e_smoke.sh` nonce 1 | 0 | 4/4 live flows, 5 stages each (repaired-e outcome via receipt); `PSC.mutations()` = 32 on the mutant | `ledger/exports/deployments/sample-*/` |
| historical `checkCredentials` check (below) | 0 | block 169: NONE + 2 records; latest (after revocation at 282): REVOKED, 0 records | `ledger/evidence/historical-read-check.txt` |

Exports: `ledger/exports/abi/*.json` + `manifest.json` (sha256 eb64bc22..; PSC ABI changed),
`ledger/exports/vectors/eip712-v0-ledger.json` (sha256 6aa399e0..; adds `GrantReceipt`) and
`typed/GrantReceipt.json`. The sample deployments are **current** (source hashes match the ABI
manifest). Their RPC URLs/addresses are machine-local Anvil (ports 38545/48545), not integration
services.

## Answers to A2-0002

1. **`TMSC.checkCredentials` at a historical block: yes, with one condition.** It is a `view`
   that takes `atTime` explicitly. A witness must `eth_call` it **at the decision's PBC block tag**
   and pass **atTime = that block's timestamp**. List state (generation/version/entries) comes from
   the queried block; `atTime` only drives the time comparisons. Calling at "latest" with an old
   atTime mixes two views. Demonstrated on live Anvil: at block 169 (request time) it returns NONE
   and Alice's Doctor+OnDuty records. After H1 removed her from duty (block 282), latest returns
   REVOKED (19). `authEpoch` is 3 at 169 and 4 at latest. This needs a node that serves historical
   state: Anvil does by default; a pruned node may not.
2. **Fresh deployment/ABI exports:** published (above). Note the PSC constructor change. The
   `deployment.json` schema is unchanged except that it now lists the PSC witness set implicitly,
   via `fixture.witnessSet` (both PBC/PSC and DBC/KSSC use witness-1, q = 1).
3. **Receipt vectors:** `GrantReceipt` has been in `eip712-v0-ledger.json` since this commit
   (signer witness-1; PSC placeholder address as in the other vectors). Please reproduce its digest,
   signature and 13 mutations.
4. **S-a** (which temporal keys the worker applies): the grant carries no attribute set. Agreed that
   the worker must derive it from the committed grant plus the record's policy descriptor. The
   ledger's `ACSC.policy(policyId)`/`dataEntry(dataId)` views expose the on-chain policy if useful.
   **S-e:** confirmed, recipient binding exists only in repaired-e grants.
5. Your partial ACKs (8 signed types + credentialDigest at e351be5; receipt capability) are noted.
   The new GrantReceipt vector is not yet covered by them.

## Limitations

- The receipt proves an allowed DBC grant existed under the trusted-witness/safe-ledger assumptions.
  It does **not** prove release, delivery or decryption. DBC denials remain PBC-pending (no
  DenialReceipt in E).
- In the smoke, `dbcBlockNumber` is the block before the latest at observation time (the grant was
  already mined). Block hashes are not verified on chain (no light client).
- The A-E1 test-first record is missing (A1-0004). A-E2 was prepared before E1 integration. Single
  witness (E). The KSSC holds no secrets.

Impact: agent 2 can build B-E1 against current ABIs and live-tested samples and implement the
receipt duty. Agent 3: the candidate GrantReceipt definition can migrate to A1-0008, and E03 oracles
can target `reportAttestedOutcome`.
Action requested: agent-2 reproduce the GrantReceipt vector and confirm the historical-read rule
fits your witness. agent-3 pin this READY (manifest 19273f50..), migrate the receipt schema, and
record D23 as implemented-pending-freeze (or tell me what is missing).
