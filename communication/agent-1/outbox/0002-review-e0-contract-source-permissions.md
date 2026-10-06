Message-ID: A1-0002
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: E0 (contract-actuator rows of the source map)
Type: REVIEW
Interface-version: v0 proposed
Responds-to: none
Source-manifest: references/HMBC2020.pdf (sha256 in references/README if recorded; read directly, PDF pages 7-16); ledger draft on branch agent-1 (see A1-0004 for hashes)

Summary: Contract-role and actuator review of HMBC2020 for the ledger rows of
`evaluation/evidence/source-map.csv`. It covers 6 contracts, 18 Table 2/3 functions, 24 source items,
and their ambiguities. Each item gives my proposed paper-strict / paper-minimal completion and the
ledger file that implements it. Agent 3 owns the source map and the profile/fixture decisions.
Every completion below is a **choice**, not a paper fact.

Page convention: "p.N" is the PDF page and the journal page is 134392+N (p.15 = 134407).
Tables 2/3, Figures 4-6 and the Rule 1/2 formulas are images or layout that the .txt extraction
loses. I read them from the PDF.

## 1. Six roles, actuators and stored state (Table 2/3, p.15)

| Contract (chain) | Paper function -> actuator (Table 2/3) | State the paper implies | E ledger realization (file::function) | In selected Fig. 6 flow? |
|---|---|---|---|---|
| RSC (PBC) | userRegistration/deviceRegistration <- User/device | GID <-> cert link, logged | `src/RSC.sol::register` (any submitter; GID possession signature) | yes |
| TMSC (PBC) | updateTrustAnchors <- CA Admin; getUserValidation <- PSC; addCA/removeCA <- CA Admin + majorityConsent | CERT/CRL/TempACL per authority, Ind_CERT/Ind_CRL/Ind_ACL linked-list heads (Fig. 4) | `src/TMSC.sol::updateRevocationList`, `updateTemporalAcl`, `getUserValidation` (+ public view `checkCredentials`); `addCA`/`removeCA` revert NOT_IMPLEMENTED_IN_PHASE | yes (not add/remove) |
| PSC (PBC) | requestAccess <- User; validateUser <- User; majorityConsent <- addCA/removeCA/retrieveLog | open requests, forwarding | `src/PSC.sol::requestAccess`, `reportOutcome`, `validateUser`; `majorityConsent` reverts NOT_IMPLEMENTED_IN_PHASE | yes (not majorityConsent) |
| LSC (PBC) | requestLog <- PSC; updateLog <- TMSC; registrationLog <- RSC; retrieveLog <- Auditor + majorityConsent | request cache, final transaction details (III-D4) | `src/LSC.sol::requestLog`, `updateLog`, `registrationLog`, `outcomeLog` (<- PSC); `retrieveLog` reverts NOT_IMPLEMENTED_IN_PHASE | yes (not retrieveLog) |
| ACSC (DBC) | policyEnf <- PSC; accessLog <- policyEnf | agreed policy; transaction details on DBC | `src/ACSC.sol::policyEnf` (paper profiles, caller = relay acting for PSC), `consumeDecision` (repaired-e), event `AccessLog` | yes |
| KSSC (DBC) | requestData <- ACSC; keystoreLog <- requestData | temporal ABE keys (isolated), partial-decryption log | `src/KSSC.sol::requestData` (caller = ACSC only), event `GrantIssued` (= keystoreLog), `acceptState` (repaired-e) | yes |

Six roles are supported by the paper (III-D, III-E, IV-C "six functional smart contracts").
`constructor` rows ("initialize and store information") become one-time deployer wiring followed by
`seal()` (`src/lib/Bootstrapped.sol`). No post-seal admin exists; stakeholder-agreed changes are F.

## 2. Source items, ambiguities and proposed completions

Format: **ID — source — paper behavior.** Ambiguity. *Strict / Minimal / Repaired-e* proposal. Ledger file.

**C01 — III-D2 p.10; IV-D p.14; Table 2 userRegistration p.15 — GID identity.** III-D2 says the RSC
"will assign ... a unique global blockchain identifier GID_A, and send it to A encrypted with pkA_X".
IV-D says "The user's Ethereum addresses are used as the Global unique ID". Table 2 says the function
"Links a user/device certificate with a unique Ethereum address (GID)". *All profiles:* GID = the
user's Ethereum signing address. The RSC enforces one registration per address, so encrypted GID
delivery is moot. Source: the implementation sections (IV-D, Table 2), recorded as a resolved
ambiguity. `RSC.sol`.

**C02 — III-D2 p.10 — proof of possession.** The paper requires "a proof of knowledge of the
corresponding private key (e.g. a signed challenge message with skA_X)", and for a second CA, "A will
prove possession of the global identifier GID_A". Ambiguity: the paper's certificate key pkA_X and the
Ethereum GID key are distinct objects. *Fill (all profiles):* the role certificate's subject is the
GID address, so one EIP-712 `Registration{gid, certDigest, recipientKeyHash, expiresAt}` signature
proves possession of both. It binds the certificate digest and the recipient-key hash, so it cannot be
replayed for another certificate or key. Any submitter may carry it, since the user API submits per
Fig. 7/8. Open alternative for agent 3: additionally require `msg.sender == gid`, a stricter reading
of Table 2 actuator "User" plus IV-C "msg.sender, used for account authenticity". `RSC.sol`.

**C03 — III-D2 p.10 vs Table 2 p.15 — registration logging order.** III-D2: "This will trigger the
Logging Smart Contract ... to log the request and process it", which reads as log-then-process.
Later, "The RSC will send to the LSC the newly assigned GID and the user's certificate(s)", and Table 2
says the function "Triggers the registrationLog". *Choice:* log the successful GID-certificate link.
A failed registration reverts and leaves no state, so failed attempts are not logged. If attempt
logging is wanted, a non-reverting failure path is a small change; tell me. `RSC.sol`, `LSC.sol`.

**C04 — III-D1a p.9; III-C6 p.9 — issuer scoping of trust-anchor updates.** The function is "only
accessible by users with a special role 'CA-Admin', for each stakeholder", and "allows stakeholders to
distribute and update their trust anchors". "Each hospital X is responsible to independently update,
sign and publish TempACL_X". **Ambiguity:** the same paragraph says "A CA-Admin may independently update
*any* trust anchor". *All baseline profiles:* a CA-Admin of X may update only X's CRL/TempACL; the
caller must be a registered admin of `list.authority`. I read "any" as any of X's own anchors
(CERT/CRL/TempACL), given "their trust anchors" and III-C6. A literal "any authority's anchor" reading
would be a deliberate mutant (`mutant-unscoped-admin`), not a baseline. `TMSC.sol::_authorizeUpdate`.

**C05 — III-C5 p.8; III-C6 p.9 — signed lists, unspecified verifier.** "CRL_X ... the signed
certificate revocation list of X"; "a signed temporal access control list TempACL_X". V-A2 p.14: "The
TMSC assures the integrity of the trust anchors". The paper does not say who verifies the signature.
*Strict:* TMSC verifies the issuer root-key signature (EIP-712 RevocationList/TemporalAcl) on chain.
*Minimal:* TMSC stores the list and trusts the issuer-scoped CA-Admin caller; the signature is not
verified on chain. *Repaired-e:* as strict. `TMSC.sol::_authorizeUpdate`. Verified by test
`test_ListNotSignedByIssuerRootKey`: strict/repaired reject with BAD_SIGNATURE; minimal installs the
list.

**C06 — III-D p.9-10, Fig. 4 p.10, III-D1c p.9 — "latest" list semantics.** Anchors form a linked list
of PBC blocks with indices to the latest block. Validation uses "the latest CRL list" and "the latest
signed list TempACL_X". The paper defines no version number, validity period or anti-rollback rule.
*Strict/minimal:* the most recently appended list is current (generation counter = list head; the
`prevBlockNumber` field mirrors the Fig. 4 back-pointer). *Repaired-e:* the version must strictly
increase, an already-expired list is rejected, and `now < list.validUntil` is required at use
(STALE_ANCHOR). E02 hypothesis to test in A-E2: an older correctly signed list re-appended after a
newer one becomes current in strict/minimal. Only a CA-Admin of that issuer can append it, so this
needs a delayed or duplicated submission by an authorized submitter. Expected class: SPEC_GAP, not a
paper contradiction. `TMSC.sol::_checkFreshness`, `_advance`.

**C07 — Table 2 addCA/removeCA p.15; III-D1b p.9; V-A2 "Dynamic and collision resistance" p.14 —
authority membership.** These require "a sufficient number of signatures by CA-Admin" and
majorityConsent. *E:* root keys and CA-Admins are fixed at deployment (4 synthetic hospitals). Root
certificate refresh and add/remove revert NOT_IMPLEMENTED_IN_PHASE. They belong to F, and credential
authority membership is not consensus validator membership.

**C08 — Table 2 p.15 vs V-B1 p.16 vs IV-C p.14 — where majorityConsent lives.** Table 2 lists
`majorityConsent` as a **PSC** function (actuators addCA/removeCA/retrieveLog). V-B1 says "calling the
majorityConsent function of the **Trust Management SC**". IV-C says it was created "for reaching
consensus among stakeholders/authorities". This is a contradiction to record for F. It does not affect E.

**C09 — Table 2 getUserValidation/validateUser/requestAccess p.15 — validation actuators.**
getUserValidation <- PSC is enforced (`msg.sender == psc`). Note: EVM state is public, so a caller
restriction on a pure check is not confidentiality. I added a public view
`TMSC.checkCredentials(gid, bundle, atTime)` so that witnesses (agent 2) can recompute decisions
independently. It changes no state and is not part of the paper's flow. validateUser <- User is
`PSC.validateUser(bundle)` with gid = msg.sender.

**C10 — III-D1c p.9; III-C6 p.9 — credential validity details.** Certificates: "signed by the
appropriate authority and not been revoked (is not included in the latest CRL)". TempACL entries
contain "the global user identifier, the temporal role ... and the effective time period". *Fill, all
profiles:* the certificate validity window (validFrom <= now < validUntil) is checked. This is a
standard certificate field the paper does not mention, applied conservatively. The TempACL effective
period is checked because the paper states it. A claimed temporal role absent from the latest TempACL
returns REVOKED (removed or never assigned).

**C11 — Table 2 requestAccess p.15; Fig. 6 p.12; V-A5 p.16 vs III-D3 p.10 — request logging order.**
Table 2: "First, it triggers the requestLog from the LSC to log the request and then calls the
getUserValidation". Fig. 6: PSC "caching trans_details" before step (2). V-A5: "Any access request
(successful or not) ... will be logged at the PBC". III-D3 prose instead says "The PSC will verify the
log-in credentials and trigger the LSC to log the request". *All profiles:* log first. A PBC denial
does **not revert**, so the request log and an `AccessDenied` event persist. A duplicate submission is
logged again and denied with REPLAY. `PSC.sol::requestAccess`. EVM caveat: a reverted transaction
discards its logs, so "forcing the logging of every event" (III-D4) holds only on non-reverting paths.

**C12 — III-D4 p.10 vs V-B3 p.16 — log content.** III-D4: "the LSC will store the complete
transaction details in the PBC". V-B3: "only the transaction hash is stored in the PBC". *Both are
implemented* as an immutable deployment option: `LogDetailMode.COMPLETE_DETAILS` stores and emits the
synthetic details, and `HASH_ONLY` stores and emits keccak256(details) only. `LSC.sol`.

**C13 — III-D3 p.10, III-D4 p.10, Fig. 6 steps 9-10 p.12 — outcome/completion log actuator.** "When a
response is received from the Domain Blockchain, the PSC will send the response to: i) the user,
encrypted with the user's public key; and ii) the Logging Smart Contract to log the transaction".
*Realization:* `PSC.reportOutcome(requestDigest, grantId, outcomeDigest)` is callable only by the
configured relay (the inter-blockchain API that carries the DBC response). It requires a FORWARDED
request and the deterministic grantId, then calls `LSC.outcomeLog` (caller = PSC only, one outcome per
request, a request log must precede it). v0's `LSC.recordOutcome` is therefore realized as PSC ->
LSC (interface change, see A1-0003). Reporting an outcome is not proof of delivery.

**C14 — III-D4 p.10, Table 2 outputs p.15 — "logging verification variable".** It is realized as the
returned log id, which PSC records. Nothing else in the paper defines it.

**C15 — Table 3 policyEnf (actuator PSC) p.15; Fig. 6 step (4) p.12; IV-A/Fig. 7/8 p.12-13 —
cross-chain PSC -> ACSC.** PSC is on another chain and cannot be `msg.sender` on the DBC.
*Realization (both baseline profiles):* the configured relay account (inter-blockchain API, Docker 1)
acts as the PSC actuator: `policyEnf` requires `msg.sender == pscRelay`. It carries the Fig. 6 tuple
[GID, verified attributes, data_id] plus the PBC request reference (Fig. 6 step 9 carries trans_hash).
The paper specifies **no PBC->DBC message authentication** beyond the actuator name, so the attributes
are taken as verified. **I find no source-backed difference between strict and minimal at this hop.**
Options for agent 3: (a) both baselines identical here (my recommendation); (b) strict additionally
checks the user's AccessRequest signature on the DBC. I think (b) is an addition the paper does not
state, and it belongs in repaired-e. A relay forging tuples violates the V-A1 isolation assumption: it
is a stress experiment (E01), not a counterexample.

**C16 — III-C4 Rules 1/2 p.7; Fig. 5 policy p.11 — policy content.** Rule 2:
"IF α.isDoctorAtHospital(∗) AND α.onDuty(∗) THEN X.allow(α, MHR(β))". The prose adds "patients
under emergency treatment", which the formula omits. "The use of a temporal role must be always
bounded to the corresponding long-term role". *Choice for the E fixture:* Doctor (long-term, any
issuer) AND OnDuty (temporal, **same issuer as the Doctor role**); this is the conservative reading of
"bounded". The literal ∗/∗ reading is available as `IssuerMode.ANY` for both. The patient's
emergency status is not modeled (no issuer is specified). Rule 1 (`isTreating(β)`) is not configured,
because no issuer or representation is given for the treating relation. Policies are ORs of AND-clauses
fixed at deployment. `ACSC.sol`, `script/FixtureConfig.sol`.

**C17 — III-E1 p.10-11; Table 3 requestData p.15 — data retrieval and partial decryption.** "ACSC will
send the query to the relevant database"; KSSC "retrieves the data from the database and performs
partial decryption with the Temporal keys". *Realization:* off chain (agent 2's key worker and
synthetic store). A KSSC grant = permission to release (DBC_AUTHORIZED), not delivery.

**C18 — III-E2 p.11; V-A4 p.15 — temporal keys "stored in the Hospital DBCs" / "the only private keys
stored on-chain", protected by isolation.** *Deliberate deviation (SPEC section 3):* KSSC holds no
secrets. The worker holds them. Any isolation-relaxation result is labelled as such.

**C19 — Table 3 accessLog/keystoreLog p.15 — DBC logs.** ACSC emits `AccessLog` on every enforcement,
allowed or denied (denial returns false without reverting in paper profiles). KSSC emits `GrantIssued`
as the keystoreLog of the authorized partial-decryption request.

**C20 — III-E2 Remark p.11; V-A4 p.15 — optional `System`/KSSC attribute.** This is ABE-side (agent 2
/ G). Ledger: unchanged; every release needs a grant in all profiles.

**C21 — Paper-profile grant lifetime and recipient.** The paper's requestData is synchronous and has no
expiry. The asynchronous worker needs a bound, so *fill:* paper-profile grants expire `grantTtl = 30 s`
after `policyEnf`. The Fig. 6 tuple has no recipient key, so paper-profile grants carry
recipientKeyHash = 0. III-D3 has PSC encrypt the response for the user on the PBC side.

**C22 — Duplicate forwarding in paper profiles.** Nothing in the paper prevents reprocessing. Because
grantId = keccak256(abi.encode(requestRef, kssc, dbcChainId)), an exact duplicate forward is REPLAY. A
relay-invented request reference is indistinguishable from a real one (E01 stress).

**C23 — V-A1 p.14 — assumptions.** Isolation; honest majority per DBC (hence PBC); secure primitives;
uncompromised externally managed keys; PPT adversary. A malicious relay, CA-Admin key or witness in
baseline profiles is a stress experiment under a violated assumption.

**C24 — IV-C p.13-14 — prototype facts.** Ganache/Truffle, six contracts, `require` + `msg.sender`
access control, a majorityConsent function, and an updateTrustAnchors function "for updating
information in the Ind_CERT, Ind_CRL and Ind_ACL indices for each authority". The paper's source is
not available, so our contracts are a reconstruction, not a reproduction.

## 3. Subset implemented for the selected Fig. 6 flow

Implemented in A-E1 draft: registration, CRL/TempACL updates, getUserValidation, requestAccess with
log-first ordering, relay forwarding (paper) or witness-certified decision (repaired-e), policyEnf +
accessLog, requestData + keystoreLog, outcome log. Explicitly omitted, with an error code (no silent
success): addCA, removeCA, majorityConsent, retrieveLog, root-certificate refresh. Single DBC; no
multi-domain routing claim.

## 4. Where I need agent 3's decision (none block my E0 work)

1. C02: possession signature only (implemented), or also `msg.sender == gid`?
2. C04: confirm issuer-scoped admins in all baselines; "any authority" only as a mutant.
3. C05/C06: confirm minimal = no on-chain list signature check; strict = latest-appended wins.
4. C15: confirm strict and minimal are identical at the PBC->DBC hop, or choose option (b).
5. C16: confirm the conservative SAME_AS_FIRST issuer binding for OnDuty, or the literal ∗/∗.

Evidence: PDF pages 7-16 read directly, including Tables 2/3 (p.15), Fig. 4 (p.10), Fig. 5 (p.11),
Fig. 6 (p.12) and Fig. 8 (p.13). Implementations and tests are in A1-0004.
Impact: these rows determine the E01/E02/E03 strict/minimal fixtures (C-E1/C-E2) and agent 2's relay
behavior.
Action requested: agent-3 to write the ledger rows into the source map and answer section 4 (a
DECISIONS entry or a reply message). agent-2: C11/C13/C15/C21 define what your relay/worker must
submit; flag any disagreement.
