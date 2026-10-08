# Ledger E2 handoff (agent 1; A1-0039)

Owner handoff for the E2 runner (agent 3). It describes how each frozen `E0CaseStep` directive maps to
public ledger calls, which TEST-ONLY tools produce the inputs, which native result to expect, and which
`mutant-*` deployment each case can kill. The facts are measured on agent 1's machine with agent 2's
unmodified adapter (evidence under `evidence/e2-rehearsal/`). This is owner evidence, not a C-E2
result, and classification is agent 3's.

Conventions:
- The runner signs only as the TEST-ONLY relay and H1..H4-ca-admin.
- Honest user and witness signatures come from the adapter.
- "Native" means a mined receipt or event, or `Rejected(code)`.
- Read the code of a status-0 receipt from `debug_traceTransaction(tx).returnValue`. The selector is
  `0xf73a052c` (A1-0036).

## Tools (ledger-owned, TEST-ONLY, read-only producers)

| Tool | Purpose | Notes |
|---|---|---|
| `tools/deploy_local.sh <pbc> <dbc> <profile> <log-mode> <run-id>` | one deployment | profiles `paper-strict`, `paper-minimal`, `repaired-e`, `mutant-{no-destination-binding,no-state-barrier,no-record-freshness,no-nonce,no-version-monotone,no-receipt-binding}`; default slow, `LEDGER_DEPLOY_FAST=1` optional. With the relay as deployer and 1000 ETH, at most **2 deployments per PBC instance** (about 400 ETH per deployment) |
| `tools/bootstrap_fixture.sh <pbc> <deployment.json> <out>` | E1 bootstrap: H1 CRL, H1 TemporalAcl, H2 CRL, Alice/Bob certificates, registrations, bundles | accepted for E1 (A3-0025); unchanged |
| `tools/sign_list.sh <pbc> <deployment.json> <out> crl\|tempacl H1..H4 [--version N] [--valid-for S] [--revoke s1,s2] [--duty label:fromAgo:untilIn]` | one signed RevocationList or TemporalAcl (E02) | version defaults to the on-chain version + 1; serials and duty gids must be ascending; output `item` has the bootstrap `trustLists[i]` shape |

## Directive → ledger realization → native result

| Directive | Realization (signer) | paper-strict / paper-minimal | repaired-e |
|---|---|---|---|
| REQUEST_ACCESS | adapter `prepare_request`, then `PSC.requestAccess(request, signature, bootstrap bundle)` (relay) | `AccessForwarded` (requestLogId != 0) | same |
| SUBSTITUTE_SUBJECT | paper: `ACSC.policyEnf({pbcRequestId: digest, gid: Bob, dataId, 1}, Alice's AccessForwarded.verifiedAttributes)`; repaired: `consumeDecision(request with gid := Bob, Alice's certificate, records)` | grant with `GrantIssued.gid` = Bob | `WRONG_SUBJECT` (DV step 4) |
| REPLAY_REQUEST | the identical tuple again (`policyEnf`) / the identical request and certificate again (`consumeDecision`) | `REPLAY` (`KSSC.sol:180`) | `REPLAY` |
| ADVANCE_CLOCK | wait in real time, then `evm_setNextBlockTimestamp(target)` on the DBC immediately before the step. **Never jump a shared chain's clock:** the cross-chain skew makes the honest witness answer EXPIRED later | expiry-boundary: granted at equality | expiry-boundary and expired-duty: `EXPIRED` (DV step 9 and step 13) |
| FABRICATE_TUPLE | paper: `policyEnf({fresh pbcRequestId, unregistered gid, DATA_P1, 1}, valid records from TMSC.checkCredentials(alice))`; repaired: an honest certificate whose signature is replaced by a **non-witness** signature over the same decision | grant, no PBC log | `BAD_SIGNATURE` (DV step 6) |
| SUBSTITUTE_DESTINATION | a **second independent deployment** (another run-id on the same chain pair, with its own bootstrap, lists, registrations and adapter). Its forwarded tuple (paper) or its request and certificate (repaired) are submitted unchanged to deployment 1 | grant (the tuple has no destination) | `WRONG_DESTINATION` at **DV step 1** (source PSC binding) |
| REPLAY_NEW_REFERENCE | paper: `policyEnf` with a fresh pbcRequestId and the same gid/data/records; repaired: re-consume the original request and certificate | second grant | `REPLAY` |
| INSTALL_NEW_LIST / REVOKE_ON_PBC | `sign_list.sh crl H1 --revoke 101`, then `TMSC.updateRevocationList` (H1-ca-admin), **after** collecting the certificate | pre-barrier: grant; post-barrier: grant (no barrier) | pre-barrier: grant (designed window); post-barrier with a new `acceptState`: `STALE_STATE`, nonce unchanged |
| REPLAY_OLD_LIST | resubmit an older signed artifact unchanged (e.g. bootstrap `trustLists[0]`) | accepted (rollback; Alice NONE again) | `STALE_ANCHOR` (`TMSC.sol:190`) |
| WRONG_ISSUER_UPDATE | an H2-signed list submitted from H1-ca-admin (before the legitimate H2 update) | `UNAUTHORIZED_CALLER` (`TMSC.sol:181`) | same (baseline, not a repair) |
| ACCEPT_CHECKPOINT | adapter `collect_checkpoint`, then `KSSC.acceptState` (relay) | not applicable (WRONG_PROFILE) | `StateAccepted` |
| FORWARD_OR_CONSUME | paper: `policyEnf(tuple, AccessForwarded.verifiedAttributes)`; repaired: `collect_decision`, then `consumeDecision(request, {decision, signatures}, credentialRecords)` | `AccessLog` (+ `GrantIssued`) | same |
| RELEASE | adapter `release(grantId)` (+ `finish_decryption`) | worker log | worker log |
| DROP_OUTCOME | no report | `getRequest.status` = 1 | 1 |
| FABRICATE_OUTCOME | `PSC.reportOutcome(digest, grantId(digest, kssc, dbcChainId), outcome)` for a forwarded request with **no** DBC grant (relay) | accepted, status 2 | `WRONG_PROFILE` |
| REPORT_OUTCOME | paper: `reportOutcome`; repaired: adapter `attest_grant`, then `reportAttestedOutcome(digest, outcome, receipt, signatures)` | status 2 | status 2 |
| DUPLICATE_OUTCOME | resubmit **the same** report or receipt. The honest witness refuses a fresh `attest_grant` after the outcome is recorded (WRONG_SUBJECT) | `REPLAY` | `REPLAY` |
| REQUEST_SAME_NONCE_DISTINCT_DIGEST … CONSUME_PRECOLLECTED_SECOND | two `prepare_request` calls with the same nonce and different expiresAt; forward both; one checkpoint; both decisions; consume the first, then the second | – | second consume: `REPLAY` (`KSSC.sol:181-183`) |
| ATTEST_GRANT / RESIGN_RECEIPT_FIELD | agent 2 `testtools.deviating_witness … --at-block <honest dbcBlockNumber>` | – | `WRONG_SUBJECT`, status stays 1 |
| ALTER_RECEIPT_KEEP_SIGNATURE | edit one bound field and keep the honest signatures | – | `WRONG_SUBJECT` (binding precedes quorum) |
| CRASH_RESTART | agent 2's hook (not ledger) | – | – |

## Mutant kill map (live probes, `e2_rehearsal.py --mutants`; one fresh `mutant-*` deployment each)

See `evidence/e2-rehearsal/summary.json` (`mutants`). The killing case is the frozen repaired-e case.
The mutant shows the vulnerable behaviour where the guard rejects.

| Mutant (bit) | Killing case | Guard | Mutant (measured) |
|---|---|---|---|
| no-nonce (8) | E01-same-nonce-distinct-digests | REPLAY | second grant, nonce not recorded |
| no-receipt-binding (32) | E03-receipt-binding-control-* | WRONG_SUBJECT | inconsistent receipt recorded |
| no-state-barrier (2) | E02-post-barrier-revocation | STALE_STATE | grant after the revoking checkpoint |
| no-record-freshness (4) | E02-expired-duty | EXPIRED | grant after the duty ended |
| no-version-monotone (16) | E02-signed-list-rollback | STALE_ANCHOR | old list accepted |
| no-destination-binding (1) | **not killable by the catalog recipe** | WRONG_DESTINATION | still `WRONG_DESTINATION`: the second-deployment request fails DV **step 1** (source PSC), which this mutant keeps. A relay rewrite of only `request.kssc` separates them by code: guard `WRONG_DESTINATION` (step 2), mutant `WRONG_SUBJECT` (step 4). Both reject. Accept-vs-reject evidence remains the ledger unit tests (`test_E01_RequestForOtherDestinationCertifiedHere`, `MutantNoDestinationBindingDecisionBindingTest`) |

**Correction to A1-0025:** its live-mutant priority 3 ("no-destination-binding on
E01-wrong-destination-repaired-e") does not hold for the integrated recipe. See the row above.

## Not covered here

The crash schedules (agent 2's TEST-ONLY hook RFC), agent 3's oracle and classification, ProVerif,
and any gate.
