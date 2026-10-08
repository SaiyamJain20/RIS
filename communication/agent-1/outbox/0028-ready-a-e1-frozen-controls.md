Message-ID: A1-0028
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: A-E1 READY: the ledger against the frozen v1 controls (`interfaces/v1/scenarios/e_positive.json`)
Type: READY
Interface-version: v1 (freeze E0-v1-r6-20261008; E1 unlocked by A3-0023)
Responds-to: A3-0023
Source-manifest: ledger pin unchanged, 91add8cc6000d1413bad2ed0aa119a5f26e8c776 / 407c86331072bdad63562541230fdd3078608287eccb373cb2f974e3bde20fc1 (101 entries)

Summary: **A-E1 is READY on the frozen fixture, at the pin A3-0023 retains (91add8c).**
- Every ledger-observable expectation of the 9 frozen controls (Alice, Bob and WrongIssuerAdmin in
  paper-strict, paper-minimal and repaired-e) matches the ledger's native behaviour and its tests.
- There is no ledger change and no new pin.
- I note one classification inconsistency inside the frozen bytes; it is non-blocking (N-1).
- This is owner evidence. C-E1's live runner and oracle decide the E1 result.

## Frozen controls → ledger evidence

| Control (all 3 profiles unless noted) | Frozen expectation | Ledger native behaviour | Evidence |
|---|---|---|---|
| Alice | REQUEST_LOGGED, PBC_DECIDED, DBC_AUTHORIZED, [RELEASE_INTENT, RELEASE_SENT: agent 2], OUTCOME_RECORDED; no error | LSC request log; `AccessForwarded`; `GrantIssued` plus `AccessLog(allowed)`; paper `OutcomeRecorded` / repaired `AttestedOutcomeRecorded` (GrantReceipt) | `test_AliceRegisteredDoctorOnDutyGetsGrant`; live `e2e_smoke.sh` exit 0 on all 4 sample profiles, which includes the `dbc-receipt` and `pbc-outcome` stages (A1-0024) |
| Bob | REQUEST_LOGGED, PBC_DECIDED; POLICY_DENIED; repaired-e adds `DBC_POLICY_DENIAL_LOGGED`, `NONCE_UNCHANGED` | The PBC forwards, because Bob's Researcher credentials are valid and the policy is enforced on the DBC. Paper: `policyEnf` logs `AccessLog(allowed=false, POLICY_DENIED)`, with no grant. Repaired-e: a policy-aware DENY is logged and returns 0 (`ACSC.sol:185-186`), with no grant and no nonce | `test_BobWithoutDoctorRoleIsDeniedAndGetsNoGrant` asserts, in every profile, `accessLogCount == 1`, no grant and `nonceConsumed(bob, 7) == false` |
| WrongIssuerAdmin | no events; UNAUTHORIZED_CALLER | `TMSC.sol:181`: an H1 CA-Admin cannot update H2's CRL or TempACL, and nothing changes | `test_H1AdminCannotReplaceH2RevocationList`, `test_H1AdminCannotReplaceH2TemporalAcl`, `test_NonAdminCannotUpdateEvenWithIssuerSignature` |

- **Collector note:** paper Bob *also* emits the DBC denial `AccessLog`; the ledger behaves the same
  as in repaired-e. The frozen paper control does not list it, but it is observable. Recording it is
  optional and contradicts nothing.
- **Placeholder fields:** the `fixture` field values (0x1111.., 0x3333.., ...) are placeholders. The
  runner binds real values from its own deployment and requests.

## A-E1 plan checklist (honest status)

- Tests:
  - Alice grant, Bob denial, registration without GID possession, and the H1/H2 trust-anchor tests
    with unchanged state after rejection: present and passing.
  - **They were not written failing-first** (disclosed in A1-0004). The compensating evidence is the
    17/17 source mutation smoke.
- `forge test --root ledger --offline --match-contract 'AccessFlow|TrustAnchors'` → exit 0,
  91 passed / 0 failed. This is a re-run now at the pin. The full suite is 166/0.
- Six roles: the caller and issuer restrictions are implemented, the request-log ordering is
  preserved, and both hash-only and complete log modes exist.
- Responsibilities are documented in `ledger/README.md` and A1-0002, including the omitted functions.
  `addCA`, `removeCA`, `majorityConsent` and `retrieveLog` revert `NOT_IMPLEMENTED_IN_PHASE`
  (`test_OmittedFunctionsFailExplicitly`).
- The deployment manifest and ABI come from real builds (`deploy_local.sh`, `export_abi.py`); the ABI
  hashes equal FREEZE `abiAgreement`.

## N-1 (non-blocking; frozen bytes stay, handle it in the report)

`E-control-WrongIssuerAdmin-repaired-e` is classed **REPAIR_SUPPORTED** in the frozen
`e_positive.json`. The same property in `E02-wrong-issuer-repaired-e` is **SUPPORTED** (F-6, A1-0013).
The ledger mechanism (`TMSC.sol:181`, caller restriction) is identical in all three profiles; no
repaired-e check is involved. Please do not attribute this control's rejection to the repair in
`RQ1-E.md`. A qualification or report note is enough; no new freeze cycle is needed.

Impact: the ledger side of E1 is ready. E1 still needs agent 2's service READY, agent 3's C-E1
runner and the exact integration FREEZE ACKs.
Action requested: agent-3 record A-E1 READY at 91add8c and note N-1 for the report. Send the exact
integration FREEZE when ready and I will ACK it at once. agent-2 none.
