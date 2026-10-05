# E1 - JANUS attack catalogue (paper claims vs code)

Status: COMPLETE. Static reading only; nothing was run, built or deployed. 20 findings (E1-01..E1-20).
Severity: HIGH 11 (E1-01,02,05,08,09,10,11,14,15,17,20); MED-HIGH 3 (E1-03,06,16); MED 4 (E1-04,12,18,19); LOW-MED 2 (E1-07,13).
Testability: T1 ~15; T2 (Vault) 4 (E1-14,15,16,17; E1-15/16 doable with a stock Vault dev container, no pbc build); T3 1 (E1-04 commit semantics).

## 0. Scope and conventions
Attacker models: EXT = external party; USR = valid low-privilege user; CAA = stakeholder CA-Admin; AUD = auditor; ORG = malicious organisation / peer admin; IBC = compromised Inter-BC API instance; NET = network attacker.
Evidence: CONFIRMED-BY-READING (exact lines + call path read) vs INFERRED (needs a run).
Testability: T1 = unit test vs Fabric mock stub / plain Node/Python, no network; T2 = needs Vault plugin container only; T3 = needs full multi-peer Fabric network.
Paths relative to `artifacts/janus-repo/` (J/) unless prefixed `vault/` (= `artifacts/vault-secrets-abe-janus/`).

## 1. Catalogue

### Batch 1 - PSC / LSC governance and logging

**E1-01 Zero-approval / <=50% elections (governance capture)**
- Where: `PSC/lib/types/elections/election/election.js:76-77` (`audienceMajorityNr = n>=2 ? Math.round(n/2) : 0`), `PSC/lib/helper.js:382` (`isApproved = audienceMajorityNr <= currentApprovals`), electorate built without initiator `PSC/lib/psc.js:157-169` + `helper.js:112-120`; window 30 min `election.js:84-85`; topology `configs/organizations_info/organizations.json` (MEDICAL=2, MANUFACTURER=2).
- Attacker: CAA (trust/addCA elections) or AUD (log-access elections) of any stakeholder.
- Precondition: audience = initiator's own domain; that domain has <=2 members (true as shipped).
- Flaw: initiator is excluded from the electorate, leaving n=1 OTHER member, so threshold=0 and `0<=0` is "approved" with zero ballots. Even n gives exactly half (n=4->2).
- Impact: integrity/governance - HIGH. Every intra-domain decision (admit a CA, open the domain's logs to one's own auditor) is unilateral in the reference deployment.
- Evidence: CONFIRMED-BY-READING (+ T9).
- Contradicts: JANUS "majority" voting (Sec 4.3.4, p.17); HMBC V-A2 "only if a majority of the relevant domain's stakeholders agree" (p.134406).
- Test: T1 - mock stub, 2-org domain, run `majorityConsentCheck` with zero ballots, expect NOT approved.
- Mitigation: strict `floor(n/2)+1` over ALL domain members, >=1 external approval, refuse empty electorate; cross-layer quorum for PBC-wide effects.
- A1: = f/f2/N6/J5. NEW consequence: applies to the shipped config.

**E1-02 `updateFromDBC` has no caller/MSP authorisation: forge the approved/fulfilled log flag + poison stored response**
- Where: PSC `psc.js:589-642` (`updateFromDBC`) -> LSC `updateRequestLog` (`lsc.js:210-244`).
- Attacker: USR (any identity that can invoke PSC) / IBC.
- Precondition: an enrolment cert of an org running a PBC peer; choose a `reqID`+`invoker` in your own org.
- Flaw: no `accessAudit`, no "caller is Inter-BC/ACSC", no revocation check. Caller-supplied `{invoker,reqID,approved,accessibleUntil}` flips the immutable record (key `[REQUEST_LOG,domain,callerMSP,invoker,reqID]`) to `fulfilled=true, approved=<caller value>` and writes caller transient bytes into `callerMSPPrivateCollection[reqID]`.
- Impact: integrity + accountability - HIGH. The "immutable global log" records an approval the DBC never issued; stored response can be substituted.
- Evidence: CONFIRMED-BY-READING (no auth gate; `updateRequestLog` keys only on callerMSP, trusts `approved`).
- Contradicts: JANUS Table 1 "global source of truth"; HMBC V-A5 "successful or not ... logged" (p.134408).
- Test: T1 - call `updateFromDBC` with crafted record+transient, assert `approved` changed with no ACSC round-trip. Regression: require caller == authorised Inter-BC service MSP/role and bind approval to a signed ACSC attestation.
- Mitigation: gate with `accessAudit` for a service role; bind the approval to a DBC signature, not a caller flag.
- A1: extends N4 (NEW: forgeable approval, not just missing logs).

**E1-03 `requestAccess` does not bind submitted `userCerts` to the signer (no proof-of-possession on the data path)**
- Where: PSC `psc.js:458-563`; roles from TMSC `getUserValidation(userCerts)`; `invoker` from `cid` but attributes from the payload certs; contrast `majorityClientVote` which DOES `validateSignChallenge` (`psc.js:248-266`).
- Attacker: USR.
- Precondition: possession of a victim's certificate (public; also leaked in logs, E1-05).
- Flaw: the certs whose roles drive the DBC decision are a free argument; no per-request sign-challenge. Forwarded event carries `invoker`=caller but `userRole`=roles of the submitted certs.
- Impact: integrity/accountability + possible authz uplift - MED-HIGH (ABE still gates plaintext, but decision+log are decoupled from a proven identity).
- Evidence: CONFIRMED-BY-READING (no PoP in `requestAccess`); INFERRED for end-to-end grant.
- Contradicts: JANUS p.12 "typical challenge-response signature verification"; HMBC "cannot be bypassed by users".
- Test: T1 - drive `requestAccess(ctx, victimCerts, data_id)` from identity A, assert `userRole` reflects victimCerts, no PoP required. Regression: require a signed nonce over data_id+txID tied to the master cert.
- Mitigation: add `validateSignChallenge` to `requestAccess`; TMSC must check master-cert subject == `cid` subject.
- A1: CONTRADICTS A1 N1 "ADDRESSED by platform choice" - the data-request path specifically skips PoP. Extends gap e.

**E1-04 Rejected data requests are not durably logged (log-before-grant atomicity)**
- Where: PSC `psc.js:459-461` (revocation gate before any log write), `psc.js:496-497` (`requestLog` nested same-tx), error returns `:519-523,:554-556`.
- Attacker: USR / insider probing.
- Flaw: a chaincode error invalidates the whole tx, so the nested `requestLog` write (shared RW-set) is discarded on rejection; requests rejected at the revocation gate never reach `requestLog`. Denied attempts leave no committed record.
- Impact: accountability - MED.
- Evidence: CONFIRMED-BY-READING (control flow + single-tx nesting); INFERRED (Fabric invalid-tx write-discard).
- Contradicts: JANUS Table 1 note 4 "all data access attempts are immutably recorded"; HMBC V-A5.
- Test: T3 (commit semantics) / T1 partial (error path precedes write). Regression: log attempts in a separate committed tx before evaluation.
- Mitigation: independent committed log tx, or event the Inter-BC persists.
- A1: verifies/extends N4 (adds the revocation-gate pre-log hole).

**E1-05 Request log stores invoker + base64 certs + dataID in clear, world-readable to every PBC peer**
- Where: PSC `psc.js:469-497` builds `{txID,invoker,invocationTime,certificates(base64),dataID}`; LSC `requestLog` (`lsc.js:78-101`) writes to PBC world state (CouchDB).
- Attacker: ORG (any stakeholder peer admin - insurer/manufacturer/other hospital) reading CouchDB.
- Flaw: no encryption/pseudonymisation; `retrieveLogs` election gate (`lsc.js:609-709`) controls only an API over state every peer replicates.
- Impact: confidentiality/privacy - HIGH (who-accessed-what-when; with TMSC `DOCTOR_OF`, doctor-patient graphs).
- Evidence: CONFIRMED-BY-READING.
- Contradicts: HMBC III-F-2 "privacy ... is preserved"; JANUS "global source of truth" as pure virtue.
- Test: T1 - assert `requestLog` world-state value contains cleartext CN/dataID. Regression: logged identity fields encrypted/pseudonymous.
- Mitigation: encrypt/commit log payloads; pseudonym resolvable only under threshold audit.
- A1: = gap a / GC1 (with file lines).

**E1-06 `LSC.updateLog` (trust-anchor audit record) trusts caller-supplied fields**
- Where: LSC `lsc.js:134-190`: destructures `{domain,subject,invoker,invokerMSP,dataHash,invocationTime}` from payload; no check `invokerMSP==cid.getMSPID()`, no caller==TMSC, time taken from payload not `getTxTimestamp`.
- Attacker: USR/IBC able to invoke LSC.
- Flaw: the "who changed the CRL/ACL and when" audit record is fully attacker-controllable (wrong org, wrong hash, backdated time), so trust-change audit can be forged/repudiated.
- Impact: accountability/integrity - MED-HIGH.
- Evidence: CONFIRMED-BY-READING (no auth gate; fields from payload). Caveat: whether only TMSC can reach LSC at endorsement level is INFERRED.
- Contradicts: "immutable trustworthy global log".
- Test: T1 - call `updateLog` with spoofed `invokerMSP`/time, assert stored. Regression: derive identity/time from ctx, restrict caller to TMSC.
- Mitigation: take `invoker/invokerMSP/time` from `cid`+`getTxTimestamp`; enforce caller MSP==TMSC.
- A1: NEW (sharpens gap a / N8 logging side).

**E1-07 Inverted ownership check in `getDataFromBC`**
- Where: PSC `psc.js:830-833`: `if (matchStrings(cn, invoker, true)) return error`.
- Flaw: `matchStrings` is true when equal, so the guard rejects the legitimate owner and passes only when caller CN != record invoker (latent authz inversion; today a functional break because `getUserRequestLog` pre-scopes to caller).
- Impact: availability/correctness - LOW-MED; latent authz.
- Evidence: CONFIRMED-BY-READING.
- Test: T1 - unit the boolean. Regression: require owner CN == invoker.
- Mitigation: invert the condition.
- A1: NEW.

### Batch 2 - TMSC / ACSC / KSSC

**E1-08 `majorityUpdate` (TMSC and LSC) has no caller check: finalize an election without a vote**
- Where: TMSC `tmsc.js:516-545` (`majorityUpdate`) -> `electionManager.updateFromElection` (`types/elections/electionManager.js:47-58`) -> `addCAMajorityReached`/`removeCAMajorityReached`; LSC `lsc.js:462-506` (same pattern, sets audit `approved=true`, `validUntil=+24h`).
- Attacker: USR/CAA with any identity on the PBC channel / IBC.
- Precondition: know a live `electionID` (deterministic sha1; also broadcast in `ElectionInitiated`/events).
- Flaw: both `majorityUpdate` functions read no `ClientIdentity`, do no `accessAudit`, and trust the caller-supplied `{electionApproved, canStillReachConsensus}`. Calling `TMSC.majorityUpdate({electionID, electionApproved:true})` directly applies the add/remove-CA regardless of ballots; `LSC.majorityUpdate` grants an auditor log access.
- Impact: integrity/governance + confidentiality (HIGH). Full bypass of the voting mechanism; admit a rogue stakeholder or open the logs with no approvals.
- Evidence: CONFIRMED-BY-READING (no caller gate; updateFromElection applies the change). INFERRED that a direct external invoke is accepted by the endorsement policy (needs a run).
- Contradicts: JANUS "majority voting" governance (Sec 4.3.4); HMBC "cannot be bypassed by ... authorities" (V-A).
- Test: T1 - mock stub: seed a pending add_ca election, call `majorityUpdate` with `electionApproved:true` from an arbitrary identity, assert stakeholder added. Regression: require caller MSP == PSC and verify the tallied result on-chain, not a caller flag.
- Mitigation: restrict `majorityUpdate` to the PSC MSP/role; recompute approval from ballots inside the function.
- A1: NEW (major; A1 noted governance capture via quorum, not this direct bypass).

**E1-09 `ACSC.policyEnf` trusts caller-supplied `verified_attributes` (GID + ROLES) with no authentication**
- Where: ACSC `acsc.js:75-155`: `policyEnf(ctx, verified_attributes, data_id)` - no `ClientIdentity`, no MSP/role check, no attestation that attributes came from the PBC/TMSC; GID taken from the payload (`:99`) and forwarded to KSSC (`:136`).
- Attacker: IBC (compromised Inter-BC) / ORG (peer on the DBC channel) / insider who can reach the DBC chaincode.
- Precondition: ability to invoke ACSC on a domain channel (Inter-BC service identity, or any DBC-channel identity if the endorsement policy allows).
- Flaw: the entire access decision rests on an unauthenticated argument; an attacker supplies arbitrary ROLES/temporal-roles and any GID, so ACSC approves and calls KSSC to system-decrypt for that GID. The PBC validation is "taken on trust" with no cross-chain proof.
- Impact: confidentiality + integrity + accountability (HIGH). Defeats the temporal/revocation/on-duty controls for anyone who can reach ACSC; bounded only by whether the attacker also holds matching ABE keys (an off-duty or revoked insider who still holds role keys gets full plaintext; see E1-10).
- Evidence: CONFIRMED-BY-READING (no auth in policyEnf); INFERRED end-to-end plaintext (needs run).
- Contradicts: JANUS p.12 "(already validated in the PBC)"; HMBC "cannot be bypassed".
- Test: T1 - mock stub: call `policyEnf(ctx, forgedAttrs, data_00)` with a chosen GID and DOCTOR role, assert KSSC `requestData` is invoked. Regression: ACSC must verify a signed PBC attestation binding GID+attributes to the request tx.
- Mitigation: sign the PBC verdict (TMSC-signed token over GID+attributes+data_id+nonce) and verify it in ACSC; restrict caller to the Inter-BC MSP.
- A1: = gap e / N-series; promoted to a concrete CONFIRMED attack with file lines.

**E1-10 `KSSC.requestData` trusts caller-supplied GID and un-bound ciphertext (system decryption for a chosen GID; ciphertext rollback/substitution)**
- Where: KSSC `kssc.js:43-70`; `helper.js:94-147` (`decryptWithVault` hits `.../sys_decrypt/${GID}` with SA policy); ciphertext from `forwardToDBCApi(data_id)` (`helper.js:32-52`) with no hash/signature/commitment.
- Attacker: IBC / ORG / insider reaching KSSC; also a malicious/breached DBC-DB host (rollback/substitution).
- Flaw: no caller auth; GID is a free argument; the off-chain ciphertext is never bound to the ledger, so a DB host can return stale/substituted ciphertext and KSSC will system-decrypt it. KSSC holds a long-lived Vault SA token (`vaultManager.js`), so it is a single de-anonymised decryption oracle.
- Impact: confidentiality + integrity (HIGH).
- Evidence: CONFIRMED-BY-READING.
- Contradicts: HMBC "data integrity"/forensics claims; JANUS partial-decryption trust model.
- Test: T1 - mock stub: call `requestData(ctx, data_id, attackerGID)`, assert Vault sys_decrypt is called for attackerGID with no ciphertext integrity check. Regression: verify a ledger-anchored hash of the ciphertext before decryption; bind GID to an attested request.
- Mitigation: commit ciphertext hashes on-chain and check before decrypt; bind GID to the signed PBC verdict.
- A1: = gap e + g1 (confirmed with lines).

**E1-11 Single CA-Admin rewrites own org CRL/TempACL; CRL signature never verified**
- Where: TMSC `updateTrustAnchors` (`tmsc.js:216-284`) gated only by `accessAudit([["CA-ADMIN"]])` + `invokerOwnsMSP`; `checkCertRevokedByCRL` (`utils/helper.js:326-347`) matches serial numbers only and never checks the CRL's signature; `constructCRL` (`:28-53`) just parses.
- Attacker: CAA (single CA-Admin of any stakeholder).
- Flaw: one admin can publish a TempACL granting a GID an all-week `DOCTOR_WORK_SHIFT` / add a patient to `DOCTOR_OF`, or publish a CRL that omits a serial (un-revoke), with no co-signer and no CRL-signature validation. Because data_00 is cross-hospital, any hospital's CA-Admin can mint all-patient emergency access for any GID.
- Impact: confidentiality + integrity + accountability (HIGH); detectable post-hoc only (hash logged, but see E1-06 forgeable log).
- Evidence: CONFIRMED-BY-READING.
- Contradicts: HMBC "cannot be bypassed by ... authorities"; III-D1(a).
- Test: T1 - unit `checkCertRevokedByCRL` with an unsigned/forged CRL, assert accepted; unit `updateTrustAnchors` single-admin TempACL write. Regression: require k-of-n co-signing for TempACL/CRL and verify CRL issuer signature.
- Mitigation: multi-party TempACL/CRL updates; validate CRL signature against the root CA cert.
- A1: = N8 (confirmed + NEW CRL-signature-not-verified sub-finding).

**E1-12 `data_04` grants Manufacturing_Staff static access to hospital data with no on-duty/patient/org scope**
- Where: ACSC `policies.js:141-150`: if any ORG role has `MANUFACTURING_STAFF`, `defineAccess(true,"static",null)` - no shift check, no patient scope, no organization match.
- Attacker: USR holding a MANUFACTURING_STAFF role.
- Flaw: blanket, non-expiring grant to a hospital-targeted data type for a manufacturer-side role.
- Impact: confidentiality (MED) - over-broad authorization; combined with E1-09, trivially forgeable.
- Evidence: CONFIRMED-BY-READING.
- Contradicts: "fine-grained access control" (HMBC Table 1).
- Test: T1 - `policyEnforcer` with only MANUFACTURING_STAFF, assert granted static. Regression: require shift + organization scope.
- Mitigation: add temporal + org + record scoping to data_04.
- A1: NEW (sharpens gap i / fine-grained claim).

**E1-13 KSSC infinite retry loop on Vault decryption error (resource exhaustion)**
- Where: KSSC `helper.js:123-132`: `do { ...doDecryption... } while (vaultResponseErr || !vaultResponse)` with only a 3-6 s random delay, no max attempts.
- Attacker: anyone who can make Vault/ciphertext return an un-decryptable value (e.g. via E1-10 substitution) / NET.
- Flaw: a persistently failing decryption spins forever inside the chaincode invocation.
- Impact: availability (LOW-MED).
- Evidence: CONFIRMED-BY-READING.
- Test: T1 - stub Vault to always error, assert loop never terminates. Regression: bounded retries with failure return.
- Mitigation: cap attempts, return an error.
- A1: NEW.

### Batch 3 - Vault ABE plugin, policies, deployment

**E1-14 KSSC service account is bound to the *admin* Vault policy (full `decrypt/+` + `keygen`), contradicting "KSSC only partially decrypts"**
- Where: `configs/vault/vault_values.json` (`kssc-role-*` -> `*-admin` policy); admin policy `configs/vault/policies/attikon-hospital-admin.hcl` grants `decrypt/+` (create/update), `keygen/<org>/*`, `syskeygen/+/<org>`, `SUBJECTS/GIDS/+` list, `sysdecrypt/<org>/*`. Plugin `decrypt` = full decryption (`plugin/full_decrypt_path.go`), `sysdecrypt` = partial.
- Attacker: ORG/IBC that compromises or reaches the KSSC chaincode process; a CA-Admin holding the org admin token.
- Flaw: JANUS's core claim is that the key store performs only a *partial* decryption and never holds full-decrypt capability for a user's data. But the token KSSC uses can (a) fully decrypt any GID's ciphertext (`decrypt/+`, single-segment wildcard = any subject) and (b) mint attribute keys for any GID. Least privilege (KSSC should hold only `sysdecrypt`) is violated.
- Impact: confidentiality - HIGH. KSSC (or its token) is a full decryption + key-minting oracle, not a partial one.
- Evidence: CONFIRMED-BY-READING (policy + role mapping).
- Contradicts: JANUS Sec 4.3.5 "partial decryption" by the key store; "cannot be bypassed".
- Test: T2 - with the Vault container, present the kssc token to `decrypt/<any-gid>`, assert success. Regression: give KSSC a policy with only `sysdecrypt/<org>/*`.
- Mitigation: separate admin vs KSSC policies; KSSC gets sysdecrypt-only.
- A1: NEW (strong paper-claim contradiction).

**E1-15 Admin policy `decrypt/+` lets an org admin fully decrypt ANY subject's data**
- Where: admin HCLs `path "stakeholders_abe_engine/decrypt/+"` create/update (vs subject HCL `decrypt/{{identity.entity.name}}` own-GID-only).
- Attacker: CAA (holds org admin Vault token).
- Flaw: `+` matches any single GID segment, so an admin can full-decrypt every user's ciphertext, not just data for its own entity; also `SUBJECTS/GIDS/+` lists all system subjects (user enumeration) which the subject policy denies.
- Impact: confidentiality + privacy - HIGH.
- Evidence: CONFIRMED-BY-READING.
- Contradicts: fine-grained, per-user confidentiality; "cannot be bypassed by ... authorities".
- Test: T2 - admin token vs `decrypt/<other-gid>`, assert allowed. Regression: scope admin decrypt or remove it.
- Mitigation: remove `decrypt/+` from admin; restrict to templated entity.
- A1: NEW.

**E1-16 Vault K8s listener disables client-cert verification and is exposed via NodePort**
- Where: `kubernetes/templates/hashicorp_vault/configmap.yaml` `tls_require_and_verify_client_cert = 0`; `services.yaml` `type: NodePort nodePort: 32000`; `VAULT_LOG_LEVEL=debug`; `replicas: 1`, `storage "file"` (single node, no HA).
- Attacker: NET (any host that can reach a node's :32000).
- Flaw: the plugin's docker config sets `tls_client_ca_file` but the k8s deployment turns off mTLS client verification, so the Vault API (login, encrypt, sysdecrypt, decrypt) is reachable by any TLS client that presents a valid K8s SA JWT / Vault token; debug logging may leak request context; single replica/file storage is a DoS/availability single point.
- Impact: confidentiality/availability - MED-HIGH (defence-in-depth removed; auth then rests solely on token/JWT secrecy).
- Evidence: CONFIRMED-BY-READING.
- Test: T2 - connect to the listener with no client cert, assert TLS handshake succeeds. Regression: `tls_require_and_verify_client_cert = 1` and ClusterIP + NetworkPolicy.
- Mitigation: require client certs, avoid NodePort, raise HA, lower log level in prod.
- A1: NEW.

**E1-17 Dev Vault: single unseal share + root token persisted in plaintext on the shared volume**
- Where: `artifacts/vault-secrets-abe-janus/other/docker/vault/config/vault_init.sh` (`-key-shares=1 -key-threshold=1`, writes `vault_operator_secrets.json` with root_token + unseal key) + `config.hcl` (`disable_mlock=true`, file backend, `max_lease_ttl=8760h`); compose mounts `./vault/config:rw`.
- Attacker: ORG/NET with volume or container read access.
- Flaw: one unseal key + root token in a world-mounted file; `disable_mlock` allows secrets to swap to disk; 1-year leases.
- Impact: confidentiality - HIGH (in the dev artifact); it is the reproducible default a student harness will run.
- Evidence: CONFIRMED-BY-READING.
- Test: T2 - bring up the compose file, read the secrets JSON. Regression: Shamir >1 shares, auto-unseal, no plaintext root persisted.
- Mitigation: multi-share unseal, store nothing in plaintext, enable mlock.
- A1: NEW.
- Note: committed config files use placeholders ("PASSWORD_NOT_DEFINED"/"NOT_DEFINED") - no real secrets are in the repo (see Section 3).

### Batch 4 - API layers (backend / inter-BC / database)

**E1-18 Backend `jwtAuthenticator` calls `next()` outside the async verify callback; long-lived HS256 tokens, algorithm not pinned**
- Where: `backend/utils/crypto/jwt.js:14-41`: `jwt.verify(token, secret, cb)` (async form) with `next()` at `:34` outside the callback; `jwtSign` default `expiresIn="10000m"` (~7 days); `jwt.verify` passes no `algorithms` option; secret `main_config.js:30` = `randomBytes(256)` (per-process).
- Attacker: EXT/USR.
- Flaw: with a callback, `jwt.verify` is asynchronous, so `next()` runs before verification resolves and a verification error thrown inside the callback is not caught by the outer try (uncaught, wrong tick); downstream handlers may run with `res.locals.authenticated_identity` unset. Tokens are valid ~7 days; algorithm not pinned; per-process secret breaks multi-replica verification.
- Impact: integrity/availability of auth handling - MED (potential auth-check ordering bypass / crash).
- Evidence: CONFIRMED-BY-READING (control flow); INFERRED (exact jsonwebtoken async timing - needs a run).
- Contradicts: "single secure entry point".
- Test: T1 - Express unit test: send a bad token, assert the protected handler does not execute. Regression: use sync verify / await, pin `algorithms:["HS256"]`, shorten TTL.
- Mitigation: move `next()`/error handling inside the callback or use the sync API; pin algorithm; shorten expiry.
- A1: NEW.

**E1-19 No per-user/GID quota: queue flooding + broken congestion-band logic**
- Where: inter-BC `utilities/modules/queue_supervisor.js` (global RabbitMQ prefetch throttle only; congestion = `MAX_CONCURRENT_CLIENTS/currentQueuedMsgs`); band test `:169,:177,:185` uses `0.3 <= congestionRatio < 0.5` which JS evaluates as `(0.3<=x) < 0.5` (always compares a boolean), so the MEDIUM/HIGH bands are mis-classified; no per-client rate limit (grep `rateLimit|per-client|quota`: none).
- Attacker: USR (authenticated insider) / IBC.
- Flaw: one principal can flood the request queue and the global log; the only mitigation is a system-wide prefetch throttle that penalises everyone, and its tiering is logically broken.
- Impact: availability - MED (also log-bloat on the "immutable" ledger).
- Evidence: CONFIRMED-BY-READING.
- Contradicts: JANUS "zero errors"/congestion handling (Sec 5, p.21).
- Test: T1 - unit the band function with sample ratios, assert mis-tiering; design-level for flooding. Regression: per-GID token-bucket; fix the comparison to explicit bounds.
- Mitigation: per-principal quotas; correct band comparisons.
- A1: = N5 (confirmed + NEW band-logic bug).

**E1-20 Statistical differencing on the disease/stats endpoints (no budget/noise/suppression)**
- Where: `database_api/api/db_api/src/crud/clinics.py:175-201` (`number_of_cases = treatments.filter_by(clinic_uuid=...).count()` / `treatments.count()`, free `start_date/end_date`, optional `clinic_uuid`); `dbc_api/src/disease_stats.py:20-45` fans out per hospital and tags `organization_uuid`; ACSC gate only `isResearcher+active` (`policies.js:115-139`).
- Attacker: USR with a Researcher role.
- Flaw: raw counts over caller-chosen date ranges and single-clinic filter, broken down per organisation; successive differenced queries isolate a single day/clinic (often a count of 0/1), and the per-org split plus a rare diagnosis reveals membership. No k-anon/suppression/DP/budget.
- Impact: privacy/confidentiality - HIGH.
- Evidence: CONFIRMED-BY-READING (+ T9). Note: queries use SQLAlchemy ORM (parameterised) - no SQL injection here.
- Contradicts: HMBC III-F-2 "privacy of personal health records is preserved"; JANUS "anonymized data" to researchers (p.6).
- Test: T1 - drive `get_disease_stats` against a SQLite fixture, run a two-range difference, recover a per-day count. Regression: enforce min-cell suppression + a per-GID budget ledger.
- Mitigation: small-cell suppression, noise, per-GID cumulative budget at the single entry point.
- A1: = gap h / GC3 (confirmed with lines).

## 2. Ranked top-10
Rank = Impact x Feasibility(T1 cheap) x Novelty-for-a-paper.
1. **E1-09** ACSC trusts unauthenticated attributes/GID (confidentiality core bypass; T1; directly contradicts "already validated in the PBC").
2. **E1-08** `majorityUpdate` governance bypass with no caller check (integrity; T1; novel direct-finalize attack).
3. **E1-14** KSSC bound to admin Vault policy = full decrypt + keygen oracle (contradicts the paper's "partial decryption only" thesis; T2-light).
4. **E1-02** `updateFromDBC` forges the approved/fulfilled log + poisons stored response (accountability; T1).
5. **E1-05** Request/trust logs world-readable in clear to every peer (privacy; T1; attacks the paper's flagship "forensics/global source of truth").
6. **E1-11** Single CA-Admin rewrites CRL/TempACL; CRL signature never verified (confidentiality+accountability; T1).
7. **E1-20** Statistical differencing on stats endpoints (privacy; T1; strong standalone paper section).
8. **E1-15** Admin `decrypt/+` wildcard = any-GID full decryption (confidentiality; T2-light).
9. **E1-01** Zero-approval/<=50% elections in the shipped topology (governance; T1).
10. **E1-03** `requestAccess` no proof-of-possession on submitted certs (authz/accountability; T1).

## 3. Not attackable / done right (for a fair paper)
- **SQL injection**: the DB API uses SQLAlchemy ORM with parameterised queries (`crud/clinics.py`, `manufacturers.py`); no string-built SQL seen.
- **No real secrets committed**: all passwords/tokens in `configs/**` and `vault/**` are placeholders (`PASSWORD_NOT_DEFINED`, `NOT_DEFINED`); the backend JWT secret is generated at runtime (`main_config.js:30`), not hardcoded.
- **DBC/API JWT (RS256)**: `database_api/api/utilities/my_jwt.py` signs with RS256 and the decoder verifies signature + `audience` + exp - sounder than the chaincode path (the weakness is that the on-chain ACSC does not re-verify it, E1-09).
- **Signed-challenge voting**: `majorityClientVote` does enforce `validateSignChallenge` and blocks the initiator from voting and double-voting (`psc.js:223-245`) - the gap is the quorum size (E1-01) and the unauthenticated finalizer (E1-08), not the ballot itself.
- **Lewko-Waters GID binding in the plugin**: `keygen`/`sysDecrypt` hash the GID into the curve so attribute keys cannot be recombined across GIDs (`keygen_path.go:129-130`, `sys_decrypt_path.go:94-95`) - the crypto binding is intact; the weakness is who may call it (policy/caller), not the math.
- **TLS between services**: KSSC<->DBC-API and KSSC<->Vault use client+CA certs (`KSSC/lib/helper.js:32-52,54-77`); mTLS material is wired (the k8s `tls_require_and_verify_client_cert=0` in E1-16 is the regression).
- **Revocation checks are present** on many PBC entry points (`isInvokerStakeholderRevoked` on requestAccess/getData/sync) - they exist (the gap is ordering vs logging, E1-04, and the forgeable finalizer).

## 4. Responsible disclosure note
CENSUS/JANUS is an academic artifact, dormant since ~2022 (no commits/releases since). Recommended courtesy path before any publication: (1) email the paper's corresponding author(s) and the CENSUS-labs GitHub org with a private advisory (90-day embargo offer) listing E1-08/09/14 first; (2) open a private security advisory / low-severity issue on the GitHub repos (`janus`, `artifacts/vault-secrets-abe-janus`) if the org allows; (3) since the project is unmaintained, if no response in 90 days, publish with the artifact treated as a research subject, keeping PoCs non-weaponised (unit tests against mock stubs only, no live endpoints), and crediting the authors. Do not touch any deployed instance; all testing stays on a local, synthetic deployment.

## 5. Minimal laptop-scale harness
Judged from `package.json`/tests already in the repo (nothing installed):
- **Chaincode (T1, cheapest)**: each chaincode ships a `test` script (`nyc mocha --recursive`) with `chai`+`sinon`+`mocha` devDeps but NO test files and empty `node_modules`. A harness needs `npm i` of `fabric-contract-api`, `fabric-shim` (both pure JS), `chai`, `sinon`, `mocha` - all lightweight, no native builds. Pattern: `sinon.createStubInstance(ChaincodeStub)` + a stubbed `ClientIdentity` (fake `getMSPID`, `getID`, `assertAttributeValue`), and stub `ctx.stub.invokeChaincode`/`getState`/`putState`/`getTxTimestamp`. Drive: `PSC.updateFromDBC`, `PSC.requestAccess`, `TMSC.majorityUpdate`, `ACSC.policyEnf`, `KSSC.requestData`, `election.js` quorum, `checkCertRevokedByCRL`. Fixtures: a fake GID/cert object, a pending-election record, a CRL string, a `verified_attributes` JSON. Memory footprint tiny (fits the <3.5 GB RSS limit).
- **DB/stats (T1)**: `pytest 6.0.1` + FastAPI + SQLAlchemy 1.3.19 already declared; `dbc_api/tests/*` ship fixtures (`history_distinct.json`, `history_common.json`). Point `get_disease_stats` at an in-memory SQLite with a few Diagnosis/Treatment rows and run the differencing test. Light.
- **Vault policy (T2-light)**: E1-15/E1-14/E1-16 need only a stock `vault` dev container + `vault policy write` + `vault token capabilities` to show `decrypt/+` is over-broad - no pbc/plugin build. 
- **Vault plugin crypto (T2, heavier)**: building the Go plugin needs cgo + `libpbc`/GMP (native; `vault/libraries/pbc.tar.gz`, Dockerfile builds it). Avoid on the laptop - use a prebuilt image or skip; not required for the policy-level findings.
- **Full network (T3)**: multi-peer Fabric + K8s is NOT laptop-safe (OOM risk). Reserve E1-04 (commit semantics) and E1-08's direct-invoke endorsement check for Ada/cloud; everything in the top-10 except E1-04 is demonstrable at T1/T2-light.

## 6. Deltas vs A1 / T9
- **Corrects A1 N1** ("request authentication/replay ADDRESSED by platform choice"): the data-request path `requestAccess` has NO proof-of-possession on the submitted `userCerts` (E1-03), and ACSC/KSSC do no caller auth at all (E1-09/E1-10) - so request authentication is only partly addressed.
- **Extends A1 N4** (log-before-grant): adds E1-02 (forgeable approval via unauthenticated `updateFromDBC`) and the pre-log revocation-gate hole (E1-04).
- **New, beyond A1**: E1-08 (direct `majorityUpdate` governance bypass - more severe than the quorum capture A1 described), E1-14/E1-15 (KSSC/admin Vault policy = full-decrypt oracle, contradicting the paper's partial-decryption thesis), E1-06 (forgeable trust-update log), E1-11 CRL-signature-never-verified sub-finding, E1-12 (data_04 blanket grant), E1-16/E1-17 (Vault deployment), E1-18 (async JWT bug), E1-13/E1-19 (DoS).
- **Confirms A1 + T9**: E1-01/E1-05/E1-20 reproduce gaps f/a/h with exact lines; T9's quorum, GetTxTimestamp (client clock, no skew bound <2.4.1), and raw-count location (`clinics.py:175-201`) are all consistent with what I read. No contradictions of T9 found.
- **Clock caveat (from T9)**: timestamp-dependent checks (election expiry `election.js:84-85`, ACSC shift windows `acsc.js:76`, access expiry `psc.js:846`) all use the client-supplied `GetTxTimestamp`, so a client can backdate/extend windows on Fabric 2.4.1 - folds into E1-01/E1-09 rather than a separate card.
## 3. Not attackable / done right
(pending)
## 4. Responsible disclosure note
(pending)
## 5. Minimal laptop harness
(pending)
## 6. Deltas vs A1 / T9
(pending)
