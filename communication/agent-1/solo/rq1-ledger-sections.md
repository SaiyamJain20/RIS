# RQ1-E.md ledger sections: agent 1 draft for agent 3 (proxy) to merge

Paper-derived HMBC2020 reconstruction: synthetic fixtures, solo phase, correlated review (A1-0059).
Follows the S3-0003 skeleton. Every ledger claim below cites its source at pin 933d2a7 (manifest
c7b7dd51..), which is unchanged for runtime contracts since 91add8c. Agent 1 checks the final report's
ledger claims against this file.

## L1. What the ledger is, and what it is not

- **Six contracts on two Anvil chains:**
  - PBC: RSC, TMSC, PSC, LSC;
  - DBC: ACSC, KSSC.

  Solidity 0.8.37, Foundry 1.8.5, no external Solidity dependencies (`ledger/README.md`).
- **Profiles are fixed at deployment** (`ledger/README.md` "Profiles"; `TMSC.sol:30-45`):

  | Profile | Meaning |
  |---|---|
  | `paper-strict` | issuer-scoped CA-Admin caller, list signed by the issuer root key; latest appended list is current, with no version ordering or list expiry (paper silent) |
  | `paper-minimal` | as strict, but the list signature is not verified on chain |
  | `repaired-e` | **a project extension, not HMBC**: strict plus monotone list versions, list validity at use, typed witness decisions verified by the 13-step `DecisionVerifier`, `(gid, nonce)` consumption, a state-checkpoint barrier, destination binding and request/grant-correlated receipts |
  | `mutant-*` | repaired-e minus one check (bit). These exist only to show that tests and oracles are sensitive. They are never HMBC evidence |
- **Must not claim:**
  - Anvil with automining/interval mining on one host is **not a consensus implementation**, not
    PoS, and not Byzantine-tolerant;
  - the "safe ledger" assumption (correct execution, no reorg) is assumed, not tested;
  - a symbolic model is not a measured cryptographic implementation;
  - the KSSC holds authorization state only, and key material lives in agent 2's off-chain worker;
  - **No ABE**, no real encryption, and no claim about the authors' implementation.

## L2. Where each E-family guarantee is enforced (repaired-e), and its absence in the paper profiles

The DecisionVerifier check order (`ledger/src/DecisionVerifier.sol` header) is fixed, so a
multi-defect certificate always yields the same code:

| Step | Check | Code |
|---|---|---|
| 1 | source | WRONG_DESTINATION (3) |
| 2 | destination | WRONG_DESTINATION (3) |
| 3 | action | MALFORMED |
| 4 | request binding | WRONG_SUBJECT (2) |
| 5 | witness-set version | STALE_STATE (6) |
| 6 | signatures | BAD_SIGNATURE (1) / quorum codes |
| 7 | result | — |
| 8 | credential binding | WRONG_SUBJECT |
| 9 | request/decision expiry, `now >= expiresAt` | EXPIRED (7) |
| 10 | checkpoint freshness | STALE_STATE |
| 11 | auth/policy epoch | STALE_STATE |
| 12 | key epoch | WRONG_EPOCH |
| 13 | record validity at now | EXPIRED |

| Family / property | Paper profiles (ledger behaviour) | Repaired-e guard (source) |
|---|---|---|
| E01 subject binding | `policyEnf` checks only gid != 0 and evaluates the **relay-supplied** records (`ACSC.sol:140-167`); grantId = H(pbcRequestId, KSSC, dbcChainId) (`ProtocolTypes.sol:447`), independent of gid | DV step 4: WRONG_SUBJECT |
| E01 forged tuple | `policyEnf` needs no PBC request; caller = configured relay | DV step 6: BAD_SIGNATURE |
| E01 identical replay | grant uniqueness `KSSC.sol:180`: REPLAY | same guard, checked before the nonce |
| E01 new reference | a fresh pbcRequestId means a new grantId and a **second grant** | same request/certificate means the same grantId: REPLAY (`KSSC.sol:180`) |
| E01 same nonce, distinct digests | not applicable | nonce guard `KSSC.sol:181-183`: REPLAY. The **only** row reaching it |
| E01 expiry | paper grant TTL = policyEnf block + 30 s (`ACSC.sol:154`); no request expiry check. SL7: a grant mined at DBC time == request expiry, expiring 30 s later | grant expiry = min(decision.expiresAt, request.expiresAt) (`ACSC.sol:190`); DV step 9 (line 74, `>=`) rejects at equality. SL7: consume == request expiry == decision expiry → EXPIRED |
| E01 wrong destination | the tuple has no destination (or source) field. SL7: A grants on B's tuple although A's PBC never saw the request | DV steps 1-2 (lines 60, 61-64). The catalog's second-deployment recipe fails at **step 1** (A1-0039). SL7 confirmed this on calldata, and the certificate was signed under B's domain |
| E02 rollback | latest appended list wins; an old signed list is re-accepted | strictly increasing version: STALE_ANCHOR (`TMSC.sol:190`) |
| E02 wrong issuer | `UNAUTHORIZED_CALLER` (16) (`TMSC.sol:181`): **baseline caller restriction in every profile, not a repair** (D-record N-1) | same |
| E02 revocation barrier | no barrier; a forwarded tuple stays grantable after revocation (pre- and post-barrier paper rows are the same execution) | a newer accepted checkpoint invalidates older decisions: DV line 87, **sequence** cause (`d.stateSequence != cp.sequence`). SL6 showed this, with the expiry clause on the same line not applying. Before that checkpoint, acceptance is the intended window |
| E02 expired duty | no record-validity check at use. SL6: grants at DBC time == record validUntil (expired under the half-open convention, zero-second margin) | DV step 13 (lines 92-94): EXPIRED. SL6 showed `duty end <= consume < min(decision, request, checkpoint expiry)`, so the rejection is not step 9 |
| E03 outcome | paper `reportOutcome` accepts a relay report for a forwarded request, even with no DBC grant (fabricated). The relay must supply the public derived grantId = H(digest, KSSC, dbcChainId); any other value gives WRONG_DESTINATION (`PSC.sol:227-229`). A dropped outcome leaves the request FORWARDED with outcomeLogId 0 permanently, because the PSC has no time-based transition (SL3) | `reportOutcome`: WRONG_PROFILE; `reportAttestedOutcome` needs a witness receipt bound to (requestDigest, gid, dataId) (`PSC.sol:266-269`). The binding test precedes quorum, so binding and signature rows give the same code (SL4) |
| E03 duplicate outcome | `PSC.sol:226` (paper) / `:250` (repaired) REPLAY. It is checked right after the unknown-request check (`:225`/`:249`, WRONG_SUBJECT) and before any binding or signature check | same |

## L3. Mutant sensitivity (owner evidence: `ledger/E2_HANDOFF.md` kill map, `ledger/evidence/ae2-mutants.*`)

| Mutant (bit) | Killing catalog row | Guard → mutant behaviour |
|---|---|---|
| no-nonce (8) | E01-same-nonce-distinct-digests | REPLAY → second grant |
| no-receipt-binding (32) | E03-receipt-binding-control-* | WRONG_SUBJECT → inconsistent receipt recorded |
| no-state-barrier (2) | E02-post-barrier-revocation | STALE_STATE → grant after revocation |
| no-record-freshness (4) | E02-expired-duty | EXPIRED → grant after the duty ended |
| no-version-monotone (16) | E02-signed-list-rollback | STALE_ANCHOR → old list accepted |
| no-destination-binding (1) | **not killable by the catalog recipe** | the second-deployment request fails at step 1, which the mutant keeps |

Sensitivity for no-destination-binding comes from:

- forge `MutantNoDestinationBindingDecisionBindingTest`;
- `test_E01_RequestForOtherDestinationCertifiedHere`;
- the ProVerif destination mutant (A3-0033).

**No integrated destination kill is claimed** (A1-0061 G-3). The integrated mutant matrix is P3;
until it runs, these rows are owner rehearsal evidence only.

## L4. Revocation window (repaired-e)

- **Owner measurement** (A1-0046, `ledger/evidence/revocation-window/`): W = min(barrier checkpoint
  acceptance, remaining request/decision TTL) ≤ 30 s.
  - Barrier at d = 0, 5, 10 or 20 s means refusal in the barrier block itself (STALE_STATE).
  - With no barrier, refusal comes at `request.expiresAt` exactly (EXPIRED).
  - New requests are refused at the PBC at once (REVOKED).
- **Paper-strict:** no ledger bound. A pre-revocation tuple was still grantable at T0 + 65 s.
- **What W is:** a runner/witness cadence parameter capped by the request TTL, not a ledger constant.
- **Limits:** one host, one trial per delay, 1 s granularity, owner runner.
- **The integrated measurement (P3) replaces or extends this.** Cite both.

## L5. Ledger-side limitations and must-not-claims

1. **TEST-ONLY keys:** all keys are derivable from labels, so custody is role separation, not
   secrecy (S2-0003).
2. **Single host, local Anvil:**
   - 1 s timestamp granularity;
   - automining for catalog runs, interval mining for the owner window measurement;
   - no network adversary on chain transport.
3. **Relay stress:** the "configured relay" is a compromised-relay stress **outside A01** (paper secure
   isolation). Relay-stress rows are specification dependencies, **not HMBC exploits**.
4. **The policy is a fixed synthetic one:** doctor/onDuty TempACL and DATA_P1/P2. It is not a
   general ABAC engine.
5. **Governance:** addCA/removeCA/root refresh (majorityConsent) is phase F and not implemented.
6. **Gas and cost:** not an RQ1 metric. The relay deployer needs about 400 ETH per deployment on Anvil
   (E2_HANDOFF).
7. **Evidence decoding:** reviews decode status-0 codes from
   `debug_traceTransaction.returnValue` (selector `0xf73a052c`). That is an Anvil debug API, not a
   consensus-level guarantee.

## L6. Ledger evidence index

| Evidence | Location |
|---|---|
| Forge suite | `forge test --root ledger` (166/0 at P1, `communication/agent-1/solo/evidence/p1-integrated-baseline/`) |
| Mutant suites, mutation smoke, cast crosscheck | `ledger/evidence/` |
| Owner rehearsal of 56 rows | `ledger/evidence/e2-full-rehearsal/` (dropped-outcome rows without RELEASE: A1-0060 R2 correction) |
| Revocation window | `ledger/evidence/revocation-window/` |
| SL1-SL7 independent reviews | `ledger/evidence/sl{1-subject,2-relay,3-audit,4-receipt,5-trust,6-barrier,7-destination}-review/`, A1-0063, A1-0067, A1-0069, A1-0071, A1-0073, A1-0075, A1-0077. The SL6/SL7 tools were committed before their runs |
| ProVerif re-run on the integrated tree | A1-0078 D-P3-4 (outputs published with P3) |
