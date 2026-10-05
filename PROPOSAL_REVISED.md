# Project Proposal

## Cerberus: Authorization-Bound Threshold Enforcement for Hierarchical Multi-Blockchain Access Control

**Course:** Research in Information Security, IIIT Hyderabad  
**Instructors:** Prof. Ashok Kumar Das, Prof. Srinathan Kannan  
**Assigned paper:** Malamas, Kotzanikolaou, Dasaklis & Burmester, *A Hierarchical Multi Blockchain for Fine Grained Access to Medical Data*, IEEE Access 8 (2020), 134393–134412  
**System extended:** Malamas, Palaiologos, Kotzanikolaou, Burmester & Glynos, *Janus: Hierarchical Multi-Blockchain-Based Access Control (HMBAC)*, Applied Sciences 13(1):566, 2023  
**Original proposal:** 17 September 2026  
**Revision:** 19 September 2026

**Evidence convention.** `[CONFIRMED]` below preserves a specification/source finding reported in the supplied audit; it does not imply a newly reproduced deployment experiment. `[HYPOTHESIS]` identifies an untested exploit or consequence. `[PROPOSED]` identifies a design or security goal requiring construction, proof, and evaluation. The findings report must attach the audited repository commits, source locations, configuration, and reproduction evidence. No new empirical result or completed security proof is claimed in this revision.

---

## 1. Summary

Janus provides a public artifact for hierarchical multi-blockchain access control. Its encryption policy requires both user attributes and an additional system-held domain attribute. This creates a cryptographic dependency on system-side assistance, but does not by itself establish that the assistance follows a valid blockchain authorization or leaves an audit record.

The supplied audit identifies a missing formal authorization-to-transform property, a transform endpoint whose relationship to blockchain authorization depends on its deployment controls, a concentrated domain enforcement secret, and a reported accumulation defect for multi-row system sub-policies. The practical administrator bypass remains a hypothesis pending reproduction.

We propose **Cerberus**, centered on one research question: **can every fresh, successful system-side transform for a registered ciphertext be cryptographically tied to a matching, valid, committed on-chain authorization, despite a malicious requester and fewer than `t` corrupt domain stakeholders?** We will specify this HMBAC-specific property, construct a candidate protocol using Fabric endorsement evidence and a single-use authorization record, distribute the mandatory domain enforcement secret, and verify transform shares against explicit public commitments.

Mediated/server-aided ABE, threshold cryptography, threshold proxy transformation, and verifiable outsourced decryption already exist. Our intended contribution is their carefully analyzed integration at Janus's authorization-to-transform boundary, with a reproducible artifact assessment. To our knowledge, the particular HMBAC definition and integration warrant investigation; priority and security claims remain conditional on the literature review and proof. The prototype will retain documented research parameters. Curve migration, proactive share refresh, aggregate-signature governance, and session-key/AKE proofs are outside the core project.

The guarantee concerns **new system-side releases**, not every later reading of plaintext. A user who already obtained a transform, data key, or plaintext can retain it. The ledger can record authorization and release attempts; it cannot establish that a human read the data or prevent offline reuse of previously released information.

---

## 2. Background: the current architecture, across the literature

### 2.1 The assigned paper (IEEE Access 2020)

The assigned paper describes a two-layer architecture for medical data:

- **Proxy blockchain:** a common request entry point and coordination/audit layer across independently managed authorities.
- **Domain blockchains:** domain-specific policy enforcement for stakeholders such as hospitals, device manufacturers, and insurers.
- **ABE-assisted access:** encryption and system/user decryption steps, certificate-based revocation, and granular auditing.

Janus supplies an implementation of this architectural direction. The project will distinguish what the 2020 model specifies from what the Janus artifact actually implements.

### 2.2 Janus (Applied Sciences 2023) — the system we extend

| Layer | Component | Function |
|---|---|---|
| Frontend | Electron/React client | Login and request submission |
| Proxy chain | PSC | User validation, stakeholder voting, request forwarding |
| Proxy chain | TMSC | Certificate/attribute validation, trust anchors, revocation lists |
| Proxy chain | LSC | Global logging and audit coordination |
| Domain chain | ACSC | Intra- and cross-domain policy enforcement |
| Domain chain | KSSC | Interface to the domain attribute secret and system-side partial decryption |
| Data | Per-stakeholder databases | Off-chain AES-encrypted records |

The HMBAC model uses sets `U, Au, S, K, D` and three gates: **AVF** for attribute verification at the proxy layer, **AF** for authorization at the domain layer, and **DF** for partial decryption.

For record `dᵢ`, Janus encrypts its data key `kᵢ` under an MA-CP-ABE policy extended by a mandatory domain attribute. The system uses `SK_D` to derive a GID-bound domain component `K_{D,GID}` and supplies the domain-side contribution. The requester completes decryption with user attribute keys. The distinction is between requiring a domain secret and requiring evidence of a particular committed authorization before that secret is used.

The artifact uses Hyperledger Fabric, Raft ordering, Kubernetes, stakeholder certificate authorities, and HashiCorp Vault with the Go ABE plugin `CENSUS/vault-secrets-abe-janus`. The exact topology and key-storage arrangement will be pinned during reproduction. Consensus upgrades do not automatically repair the transform interface or establish the required authorization correspondence. The project will document the deployed ordering assumptions rather than assume a later Fabric feature is active. See the [Janus paper](https://doi.org/10.3390/app13010566) and [public repository](https://github.com/CENSUS/Janus).

### 2.3 The cryptographic substrate — Lewko–Waters (EUROCRYPT 2011)

The supplied audit identifies Janus's equations with the prime-order construction in LW11 Appendix D. Using symmetric bilinear groups of prime order `p`, a generator `g`, `E = e(g,g)`, and a hash `H_G` into the source group, its relevant equations are:

```text
PK_i = (E^α_i, g^y_i)                 SK_i = (α_i, y_i)
C₀   = M · E^s
C₁ₓ  = E^λₓ · E^(α_{ρ(x)} rₓ)
C₂ₓ  = g^rₓ
C₃ₓ  = g^(y_{ρ(x)} rₓ) · g^ωₓ
K_{i,GID} = g^α_i · H_G(GID)^y_i

∏ₓ [C₁ₓ · e(H_G(GID), C₃ₓ) / e(K_{ρ(x),GID}, C₂ₓ)]^cₓ = E^s
where Σₓ cₓ Aₓ = (1, 0, …, 0).
```

Here `A` is the LSSS matrix and `ρ` its row-to-attribute mapping. Every component used for a requester must use the same canonical `GID`.

Two observations guide the design:

1. Exponent linearity permits Shamir sharing of `α_D` and `y_D` and interpolation of pairing contributions. This establishes an algebraic correctness identity; it does **not** establish authorization enforcement, resistance to malicious transform queries, or a complete threshold-security theorem.
2. The prime-order variant's security analysis uses the generic bilinear group model and a random oracle. The composite-order construction has a different proof basis. The final report must identify the exact variant, assumptions, and changes rather than transfer a stronger guarantee from another construction.

### 2.4 Outsourced, mediated, and server-aided decryption

GHW11 supplies definitions and constructions for outsourced ABE decryption, including CPA/RCCA notions in its setting. Its usual transformation key is derived from a user's key with a blinding secret retained by that user. Janus instead uses a system-held attribute to make online assistance necessary. GHW11 is useful prior art for syntax and confidentiality analysis, but its theorems do not automatically apply to this different key ownership and authorization model.

Mandatory online participation is also prior art. Ibraimi et al.'s mediated CP-ABE divides decryption capability between a mediator and a user and uses mediator-issued tokens for revocation and contextual access. Server-aided revocable ABE and verifiable transformation further connect online assistance, revocation, and correctness checking. These works preclude a broad claim to invent enforced or mediated decryption. See [mediated CP-ABE](https://research.utwente.nl/files/5098398/Mediated_Ciphertext-Policy_Attribute-Based_Encryption_and_its_Application_%28extended_version%29.pdf) and [Yang, Cui & Jing, 2023](https://doi.org/10.1007/978-3-031-41181-6_25).

| Dimension | Outsourced ABE (GHW11) | Mediated/server-aided ABE | Janus / proposed Cerberus focus |
|---|---|---|---|
| Main purpose | Reduce user decryption work | Online assistance, revocation, or contextual control, depending on scheme | HMBAC authorization-to-transform correspondence |
| Server's key role | Typically user-derived transformation key | Scheme-dependent mediator/server material | Mandatory domain attribute secret |
| Relevant existing guarantees | Outsourcing confidentiality | Scheme-specific mediation/revocation guarantees | Must specify committed authorization and release conditions |
| Verifiability | Established extensions include Lai et al. | Existing verifiable server-aided constructions | Supporting mechanism, not a new primitive |
| Ledger correspondence | Not the central GHW11 property | Must be checked for each system | Exact ciphertext/request binding across HMBAC layers |

### 2.5 Closest related systems

The table distinguishes reported mechanisms from properties this proposal has not established. “Not established” is not a claim that a paper lacks a capability; it identifies a comparison requiring evidence.

| Work | Relevant mechanism | Relationship to Cerberus | Evidence / comparison status |
|---|---|---|---|
| IEEE Access 2020; Janus 2023 | HMBAC and system/user decryption split | Architectural and implementation baseline | Public Janus artifact; audit findings require pinned revisions |
| Mediated CP-ABE, Ibraimi et al. | Mandatory mediator token, revocation/context checking | Prior art for online enforcement | No novelty claimed for mediation itself |
| GHW11; Lai et al. 2013; Yang et al. 2023 | Outsourcing and verifiable transformation | Definitions and correctness-verification prior art | Compatibility must be shown for the selected LW11 variant |
| Threshold proxy re-encryption, including blockchain-based IoT work (2021) | Multiple proxies jointly transform ciphertexts | Prior art for distributed transformation | Does not by itself settle HMBAC authorization-to-transform correspondence |
| BMHADS, PLOS One 2026 | DKG and threshold BLS for collaborative data-source authentication; separate multi-authority ABE/key-fragment mechanisms | Close blockchain/IoMT comparison; different use of threshold machinery | Do not characterize its DKG/BLS component simply as a threshold issuance key |
| Du et al., CEE 2024 | Blockchain-based multi-authority hierarchical data sharing | Recent architectural and access-control comparison | Exact enforcement and compromise guarantees require full-text mapping |
| TMACS, Li et al. | Robust/verifiable threshold multi-authority access control | Prior art for distributed authority/key management | Compare the protected secret and security game precisely |
| Banerjee, Bera, Das et al., ComCom 2021 | Private-blockchain multi-authority CP-ABE access control | Application and trust-model comparison | Performance comparison only if reproducible and comparable |
| Cerberus `[PROPOSED]` | Threshold domain enforcement plus committed, request-bound authorization | Targeted HMBAC integration and formal property | Construction and guarantees remain to be established |

BMHADS explicitly places its DKG/threshold-BLS mechanism in collaborative authentication of data sources, alongside a separate multi-authority ABE design. It cannot be dismissed as merely distributing an issuance key. Our proposed distinction is the distribution of **Janus's mandatory system-attribute secret** and its relationship to committed authorization evidence. This distinction alone does not prove novelty. See the [BMHADS primary paper](https://doi.org/10.1371/journal.pone.0349767).

The review will include Du et al. (2024), BMHADS (2026), and relevant 2024–2026 decentralized, server-aided, and blockchain ABE publications identified through primary-source citation searches. We will record the search date, security model, protected secret, authorization mechanism, and artifact evidence. A missing statement or an unavailable artifact will be marked **unknown**, not converted into a negative result. [Du et al.](https://doi.org/10.1016/j.compeleceng.2024.109547) and [blockchain-based threshold PRE (2021)](https://doi.org/10.3390/electronics10192359) are explicit comparison entries.

---

## 3. Problem statement

Janus motivates a mandatory access path and a global audit record. We examine the narrower, testable implication: does successful system-side assistance require a matching valid on-chain authorization?

### Problem 1 — The HMBAC authorization-to-transform property is not formally specified `[CONFIRMED: supplied specification audit]`

The audit reports informal security analysis without a game connecting AVF/AF authorization, ledger commitment, and DF output under stakeholder compromise. Existing mediated and outsourced ABE definitions are relevant foundations. The gap is an HMBAC-specific correspondence property and adversary model, rather than the absence of formal online-decryption notions in the literature.

### Problem 2 — The transform interface lacks independently checked authorization evidence `[CONFIRMED: supplied code audit; bypass is HYPOTHESIS]`

The supplied audit reports that `plugin/sys_decrypt_path.go` accepts caller-provided `cryptogram`, `sub_policy`, `subject`, and `entity_id` without validating a cryptographic capability tied to a committed authorization. Vault authentication and ACLs may control endpoint access; the observation is specifically that endpoint admission is not the same as proof of an authorized blockchain request.

The reported `configs/vault/policies/attikon-hospital-admin.hcl` policy grants administrator `create`/`update` access to `sysdecrypt/<org>/*`. Whether an administrator can reach this route, access the required inputs, obtain a usable transform, and avoid the expected ledger records is `[HYPOTHESIS]`. It must be tested on the pinned deployment before being reported as an exploit.

Two further hypotheses require tests: inconsistent identity binding when `subject` supplies the hash input but `entity_id` selects keys, and inconsistent reconstruction when ciphertext policy supplies LSSS coefficients while a caller-supplied sub-policy controls pruning. Canonical identity and policy checks belong at every honest transform service.

### Problem 3 — The domain enforcement secret is concentrated `[CONFIRMED: supplied architecture/source audit]`

The audit reports that the domain enforcement secret is available at a single logical Vault trust boundary. Extracting `SK_D` permits derivation of domain components for arbitrary GIDs. An attacker still needs the relevant user-side components to complete decryption, but the mandatory domain gate can then be bypassed for otherwise qualified users. Replicating a Vault containing the complete secret does not remove this compromise path.

Threshold distribution reduces this specific trust concentration. It does not eliminate all authority escrow, all infrastructure trust, or the consequences of `t` cooperating malicious holders.

### Problem 4 — Reported multi-row correctness defect and parameter limitations `[CONFIRMED: supplied code/specification comparison]`

LW11 requires a product of row contributions. The audit reports that the loop instead assigns `EggS = Set(div).ThenPowBig(cₓ)`, retaining only the final contribution. A single contributing system row does not expose this error; general multi-row system sub-policies require multiplication. Runtime reproduction and exact supported-policy behavior remain empirical tasks.

The reported 160-bit subgroup order is inadequate for a 128-bit security target: generic discrete-log attacks alone give an approximately 80-bit upper bound, and pairing target-field attacks may lower the effective security further. Subgroup-order size is not a complete security estimate. Replacing “160” with “256” does not safely instantiate the symmetric equations on a modern Type-3 pairing curve.

---

## 4. Proposed solution

### 4.1 Component S1 — An HMBAC authorization-to-transform definition

*Foundations: mediated/server-aided ABE, GHW11's outsourcing definitions, LW11, and ledger authorization semantics.*

We will specify algorithms `Setup`, `DomainDKG`, `UserKeyGen`, `Enc/Register`, `AuthorizeConsume`, `VerifyAuthorization`, `TransformShare`, `VerifyShare`, `Combine`, and `Decrypt`. The syntax includes the ciphertext registry, public DKG transcript, ledger state, corruption interface, and persistent per-service release state.

**Primary security objective `[PROPOSED]`.** A PPT adversary controlling a requester, the network/combiner, and at most `f < t` domain share holders must not obtain a fresh usable domain transform for a protected registered ciphertext/GID pair unless there is a prior matching **valid, committed authorization-and-consumption record**. The requester may already hold user attributes satisfying the user-side policy. Both proxy AVF evidence and domain AF evidence must be linked to that record. The game must recognize usable algebraic outputs even if the adversary strips their certificates; checking only the honest client's acceptance algorithm would be too weak.

The game will expose legitimate authorization/transform queries for other requests, corrupted shares, public commitments, and adversarial submissions. It must explicitly handle related ciphertexts and attempted registration of malformed or substituted headers. Freshness excludes a target whose usable assistance or plaintext has already been legitimately released to the adversary. This exclusion must not discard distinct unauthorized targets merely because their encodings are related.

Three subsidiary obligations accompany the primary game:

- **Release correspondence and replay resistance:** an honest service's release event refers to one consumed authorization record and one fixed request. Concurrent calls and retries cannot create a second logical use of the same capability.
- **Transform correctness:** accepted shares combine to the prescribed domain contribution, and the user verifies the complete row product. Invalid shares are rejected.
- **Confidentiality and GID collusion resistance:** public commitments, proofs, and authorized transform transcripts must not reveal protected plaintext or enable cross-GID decryption beyond the explicitly permitted release history. A service coalition that independently possesses sufficient user keys and an authorized transform is not required to forget what those inputs reveal.

We target a CPA-style confidentiality analysis appropriate to the actual construction. RCCA/CCA security will not be asserted merely by citing GHW11. The exact corruption model, query restrictions, and generic-group/random-oracle assumptions must accompany any theorem.

**Claim boundary.** This is a proposed definition and candidate realization. Signature unforgeability plus Shamir secrecy is not, by itself, a proof that all useful transforms require authorization. The analysis must also rule out deriving an unauthorized target transform from previously released pairing values. If that fails, the construction must change or the achieved property must be stated more narrowly.

### 4.2 Component S2 — Committed, capability-bound partial decryption

*Foundations: Fabric endorsement signatures, ledger validation, collision-resistant hashing, authenticated identities, and durable state.*

#### Request and authorization evidence

Use an unambiguous, versioned canonical encoding. Let `H_b` be a domain-separated hash of bytes, distinct from `H_G` in the ABE scheme. Define:

```text
request = Encode(
  "Cerberus/Auth/v1", networkID, proxyChannelID, domainChannelID,
  domainID, keyID, dataID, dataVersion,
  H_b(ciphertext), GID, txID, policyDigest, nonce, epoch, expiry,
  proxyAVFReference, domainAFReference
)
capID = H_b("Cerberus/CapID/v1" || request)

authorizationEvidence = (
  request,
  Fabric endorsed transaction envelope(s),
  validated ledger references and consumption state
)
```

`ciphertext` denotes the registered encryption envelope: ABE header, LSSS matrix and mapping, encrypted payload or its authenticated content digest, algorithms, and immutable object/version metadata. `policyDigest` covers the canonical policy bundle and versions used by AVF/AF, including the required domain gate. A mutable data identifier is not a substitute for a content hash. The requester must prove possession of the authenticated identity mapped to `GID`; all lookups and ABE hash inputs use that same identity.

`txID` identifies the proxy authorization-and-consumption transaction, is known when its proposal is constructed, and must match the envelope. `nonce` is a fresh unpredictable application nonce; it is distinct from any Fabric-internal nonce. `epoch` identifies the authorization/configuration generation; `keyID` separately identifies the DKG key. An epoch change does not refresh key shares.

**Fabric signatures replace a single proxy signing key.** Verify the signed proposal-response material and its binding to the request, chaincode identity, read/write set, channel, and applicable MSP/endorsement policy. Distinct signatures from distinct authorized organizations are required; several certificates belonging to one organization do not count as several stakeholders. The verifier must check the actual Fabric envelope semantics, not assume endorsers signed a free-standing `request` string.

Endorsement alone is insufficient: simulation can succeed while the transaction is never submitted or later becomes invalid. Each honest transform service checks valid commitment using its own authenticated, validating ledger view, including relevant configuration history. An untrusted caller's event or claimed block inclusion is insufficient. [Fabric transaction flow](https://hyperledger-fabric.readthedocs.io/en/latest/txflow.html) and [endorsement policies](https://hyperledger-fabric.readthedocs.io/en/latest/endorsement-policies.html) define the platform semantics to implement against.

#### Single-use state and cross-chain ordering

1. Register and authenticate the immutable ciphertext/version and its policy. A caller cannot replace the system sub-policy, omit the domain gate, or substitute arbitrary pairing inputs.
2. Obtain committed AVF/AF decisions for the same object, GID, policy versions, nonce, epoch, and expiry. The domain decision references the proxy request. Cross-chain evidence is validated by the receiving layer; channel-local identifiers are always qualified by their channel.
3. Execute `AuthorizeConsume` on the designated proxy authorization ledger. It verifies those references and atomically records `capID → CONSUMED(request, txID)`, with a uniqueness check for the request nonce/identity namespace. Fabric state-version validation resolves conflicting attempts. This is the sole authoritative spend point; no two-chain atomic transaction is assumed.
4. Wait for that transaction to commit **validly**. Each honest share service independently verifies all bound fields, the referenced decisions, the consumed state, and its current epoch/configuration before producing a share. If it cannot establish the required ledger state, it does not release.
5. Before sending its output, each service atomically persists its release record for `(capID, stakeholderID)` together with the exact response. An identical retry can return that response under the same logical operation; a changed request is rejected. This provides at-most-once logical consumption with idempotent delivery, not exactly-once network delivery.

The baseline uses short-lived authorization leases with explicit policy snapshots. The final consumption transaction is the authorization decision point; later policy changes do not retroactively undo an already consumed permission. Honest services also check expiry immediately before first release using a specified authenticated time source and bounded clock-skew rule. Cross-chain synchronization and lease validation must be specified and tested; the design does not promise simultaneous observation of every policy update across independent chains. A missing or stale proof causes failure, not optimistic acceptance.

Consumption precedes release, so a crash can leave a consumed request without a completed transform. Retry recovery may finish the same recorded operation while its release conditions still hold. After expiry, a fresh authorization is required. Completion receipts may aid diagnostics, but the security claim does not depend on a client honestly reporting receipt.

**What this establishes, subject to S1/S3 analysis.** Every newly enabled transform has preceding matching authorization evidence, and every honest release has a durable request identity. The audit record establishes authorization/consumption, not proof of successful delivery or plaintext reading. Neither `expiry` nor single-use state can invalidate an already released pairing value or plaintext. Corrupt holders can emit their own shares repeatedly; the claimed protection is that fewer than `t` cannot thereby enable an unauthorized target transform.

### 4.3 Component S3 — Threshold domain enforcement and explicit share verification

*Foundations: Shamir sharing, established malicious-secure DKG/VSS techniques, LW11 exponent linearity, and proofs of knowledge of a shared representation.*

#### Distributed setup

For fixed nonzero, distinct participant indices `i ∈ Z_p`, use two independently randomized degree-`t−1` polynomials:

```text
f_α(0) = α_D                     f_y(0) = y_D
a_i = f_α(i)                    b_i = f_y(i)
PK_D = (E^α_D, g^y_D)           E = e(g,g)
```

The selected DKG must prevent any single dealer from learning the completed domain secret and provide consistent, authenticated public verification material. Its specification must cover private share delivery, complaint/disqualification handling, qualified-set agreement, and the admissible corruption/availability thresholds. Two informal references to “Pedersen/GJKR” are not a substitute for selecting and analyzing an actual protocol.

A candidate public commitment layout, aligned with the existing LW11 public-key groups, is:

```text
V_{α,k} = E^(coefficient_k(f_α))  V_{y,k} = g^(coefficient_k(f_y))
A_i = ∏_{k=0}^{t−1} V_{α,k}^(i^k) = E^a_i
Y_i = ∏_{k=0}^{t−1} V_{y,k}^(i^k) = g^b_i
V_{α,0} = E^α_D                  V_{y,0} = g^y_D
```

Here `V_{α,k},V_{y,k}` are coefficient commitments and `A_i,Y_i` are evaluated commitments for participant `i`. These are discrete-log commitments, not information-theoretically hiding commitments. Their compatibility with the DKG and the modified LW11 proof is an explicit obligation. Do not publish `g^α_D`, a reusable `K_{D,GID}`, or additional source-group secret commitments without analyzing their consequences.

No full domain secret is reconstructed during honest setup or transformation. A coalition of `t` holders can reconstruct it; that compromise is outside the claimed protection. The baseline uses a fixed key and a **static corruption bound over its lifetime**. It does not claim a per-epoch/mobile-adversary bound.

#### Partial transform and combination

After S2 succeeds, for each required system row `x`, stakeholder `i` computes directly in the target group:

```text
B_x = e(g, C₂ₓ)                 D_x = e(H_G(GID), C₂ₓ)
T_{i,x} = B_x^a_i · D_x^b_i
        = e(g^a_i · H_G(GID)^b_i, C₂ₓ)

For a set I of t distinct valid share holders:
L_i = ∏_{j∈I, j≠i} (-j)/(i-j) mod p
T_x = ∏_{i∈I} T_{i,x}^L_i = e(K_{D,GID}, C₂ₓ)
Q_x = C₁ₓ · e(H_G(GID), C₃ₓ) / T_x
Q_D = ∏_{x in selected system rows} Q_x^cₓ
```

Each row uses its owning attribute's appropriate distributed key if multiple system attributes are supported. Reconstruction coefficients come from the same validated ciphertext policy and satisfying row set as the user-side calculation. The system's partial row sum need not itself reconstruct `(1,0,…,0)`; the complete selected rows must do so. No service returns `g^a_i H_G(GID)^b_i`, and no combiner assembles `K_{D,GID}`.

#### Exact candidate verification relation

For a single row, the public statement is `(E,g,A_i,Y_i,B_x,D_x,T_{i,x},ctx)` and the witness is `(a_i,b_i)`. Prove simultaneous satisfaction of:

```text
A_i = E^a_i
Y_i = g^b_i
T_{i,x} = B_x^a_i · D_x^b_i
```

This is a two-witness proof of representation across the source and target groups. A candidate generalized Schnorr/Fiat–Shamir transcript is:

```text
Choose independent u,v uniformly in Z_p.
R_A = E^u                  R_Y = g^v                  R_T = B_x^u · D_x^v
c = H_FS(Encode("Cerberus/ShareProof/v1", ctx,
                 E,g,A_i,Y_i,B_x,D_x,T_{i,x},R_A,R_Y,R_T)) ∈ Z_p
z_a = u + c a_i mod p       z_b = v + c b_i mod p

Verify:
E^z_a = R_A · A_i^c
g^z_b = R_Y · Y_i^c
B_x^z_a · D_x^z_b = R_T · T_{i,x}^c
```

`ctx` includes protocol/network/domain identifiers, key and DKG-transcript digests, `capID`, the complete request digest, ciphertext hash, GID, policy digest, row identifier, stakeholder index, epoch, and the valid consumption reference. All statement elements use validated canonical encodings and appropriate subgroup checks. Reject invalid parameters and forbidden degenerate ciphertext inputs; public commitments are validated under the chosen DKG rules rather than indiscriminately rejecting a legitimate zero share. Proof randomness must never be reused.

The response is authenticated under the stakeholder's organizational identity. Proof failure detects an inconsistent share; attribution additionally requires that authenticated response. The Fiat–Shamir security argument, concurrent use, public DKG commitment exposure, and malformed-input handling must be analyzed in the chosen model. The relation is explicit; it is not a completed proof of the whole protocol.

**Critical limitation.** Including the capability in the proof challenge binds the proof transcript to the request. It does not make the raw `T_{i,x}` algebraically dependent on every capability field. Once revealed, that value can be copied. S1 therefore needs an analysis of related ciphertexts, repeated/reused `C₂ₓ` values, policy/header substitution, and combining previous responses. Authentication of registered objects and honest request checks are necessary, but must not be mistaken for a proved cryptographic non-transferability result. A failed binding argument is a construction failure, not something to conceal with client-side certificate checks.

#### Platform mapping and availability

Shares remain in independently administered per-stakeholder services, outside deterministic chaincode simulation. Chaincode handles authorization state and public commitments. No share is released during endorsement simulation.

The **transform threshold `t`**, **authorization endorsement threshold `q`**, and **ordering/consensus fault threshold** are separate parameters. A threshold over distinct organizations can align their administration, but does not make these mechanisms equivalent. For every relevant authorization policy, the permitted corrupt organizations must be unable to satisfy it alone; with the same population and corruption bound `f`, this requires `q > f`. Proxy and domain populations require their own mappings and bounds. Availability also requires at least `t` responsive, valid share holders (`n−f ≥ t` when all corrupt holders withhold), plus the selected DKG and ledger protocols' own conditions.

### 4.4 Component S4 — Verifiable transform as a supporting mechanism

*Foundations: existing verifiable outsourced ABE, including Lai et al. (2013), and the explicit S3 relation.*

The baseline verification method is concrete: the user checks authorization evidence and the authenticated DKG commitments, validates `t` distinct share proofs per required row, recomputes interpolation, and checks the complete system row product against the committed ciphertext policy. This also checks the combiner's work. The user then combines system and user contributions according to LW11.

The multi-row regression must fail if a combiner replaces the product with the final row contribution. A proof of each share alone does not establish that the combiner selected the right rows or multiplied them correctly. No unspecified “checkability tag” is assumed. This baseline may cost the user substantial verification work; it will be measured. Compact verification is a possible later optimization, not a headline novelty claim or a promised constant-cost result.

### 4.5 Component S5 — Correctness and parameter discipline

Fix the reported product/assignment defect after reproducing it. Build deterministic correctness vectors and adversarial input tests for single- and multi-row policies, GID consistency, policy selection, serialization, share interpolation, and rejection paths. These are implementation tests, not substitutes for security proofs.

The main prototype retains the baseline pairing setting to isolate enforcement overhead and reports the actual curve, subgroup order, base/extension fields, pairing type, library versions, and estimated security limitations. It is a research prototype, not a claim of deployable 128-bit security.

A modern-curve migration is **future work**. A Type-3 instantiation requires explicit assignment of every element and hash to `G₁`/`G₂`, well-typed pairings, revised key/ciphertext and proof equations, compatible DKG commitments, and a security analysis for that variant. It is not a “160→256-bit” configuration change and is excluded from the core timeline and performance claims.

### 4.6 Scope boundary

The core comprises S1–S5 with a fixed stakeholder set and static corruption bound. Proactive secret sharing and aggregate-signature governance are removed from the implementation plan. Ordinary Fabric endorsements supply authorization evidence; no BLS subsystem is required for that choice. Epochs invalidate stale authorizations and identify configuration changes, but do not repair accumulated secret-share compromise.

Future work may consider securely specified rekeying/refresh, Type-3 re-instantiation, compact verification, and stronger revocation. There is no new session-key protocol in this proposal, so an ROR/AKE proof is not part of its security argument.

---

## 5. Threat model

**Entities:** requesters, data owners, attribute authorities, domain share holders, proxy/domain peers and orderers, untrusted combiners, off-chain databases, and per-stakeholder secret stores.

| Adversary class | Capability | Protection to investigate |
|---|---|---|
| A1 — External attacker | Network interference and unauthenticated calls | Reject malformed requests and unauthorized releases |
| A2 — Malicious user | Valid credentials, satisfying user-side keys, colluding identities, replay/substitution attempts | Domain assistance still requires matching committed authorization |
| A3 — Malicious stakeholder administrator | Controls its own organization and services, bypasses its local ACLs | One organization cannot independently satisfy the distributed gate |
| A4 — Coalition of `f < t` domain holders | Holds their shares; submits invalid shares, withholds, and colludes with requesters | Cannot derive a fresh unauthorized target transform under the completed construction's assumptions |

These classes extend the audit's focus; we do not claim earlier literature never considered malicious authorities. Corruption of an organization includes its relevant services and endorsement credentials, so correlated compromise must be counted consistently across the authorization and transform thresholds.

**Retained assumptions.** The selected ABE and symmetric encryption provide the exact security properties used in the proof; randomness, hashing, and signatures meet their stated assumptions; honest services validate inputs, protect their shares, and maintain durable release state; the relevant endorsement policies include sufficient honest organizations; and ordering/ledger validation meets the declared consensus assumptions. Cross-chain evidence verification and the policy-snapshot/expiry semantics in S2 are part of the trusted protocol, not a free consequence of blockchain deployment.

**Reduced trust.** No single Vault or stakeholder is entrusted with the full domain enforcement secret. Honest share services independently validate authorization, so an administrator's local ACL bypass cannot by itself obtain the threshold contribution. We still require the uncorrupted services and their infrastructure to behave correctly.

**Exclusions and boundaries.** We do not protect against `t` corrupt share holders, a corrupt authorization quorum, failed consensus assumptions, or a data owner deliberately disclosing its own plaintext/key. We do not revoke previously learned plaintext, promise access during quorum failure, or count offline copies as new logged accesses. A mobile attacker accumulating `t` shares over time violates the static lifetime bound, even if it never controls `t` simultaneously. General attribute-authority escrow and new user-revocation mechanisms are not claimed to be solved.

---

## 6. Methodology

1. **Evidence and literature review.** Pin Janus/plugin commits, policies, parameters, and deployment settings; retrieve close prior work and map mechanisms and games. Preserve confirmed source observations separately from reproduced behavior.
2. **Empirical audit.** Test the administrator bypass hypothesis, identity/policy inconsistencies, and multi-row correctness defect on an isolated deployment. Record successful, failed, and inconclusive tests with prerequisites and ledger traces.
3. **Formalization.** Define protected objects, permitted registration, authorization leases, corruption/query interfaces, release events, and fresh-transform security. State the difference between service correspondence and adversarial algebraic derivation.
4. **Construction.** Fully specify S2's transaction evidence/state machine, the selected DKG, S3's public commitment layout and proof relation, and the user's verification algorithm. Freeze encoding and policy/version rules before integration.
5. **Computational analysis.** Prove correctness; analyze DKG secrecy/consistency, signature and hash binding, share-proof soundness/zero knowledge, and preservation of LW11 confidentiality/GID binding. The central enforcement proof must include the authorized-transform oracle and related-ciphertext attacks. State all assumptions and unresolved lemmas; do not assert a reduction solely to signatures and DKG secrecy.
6. **Symbolic protocol analysis.** Model authorization/release correspondence, identity/context substitution, and message replay in ProVerif if suitable. Model persistent consumption explicitly or report the abstraction and verify the concrete state machine with concurrent integration tests. Symbolic success does not prove pairing security, Fabric consensus, or crash-safe storage. If another tool is needed, choose it for the missing property rather than label an unsupported property verified.
7. **Implementation.** Modify the Go plugin and relevant Janus chaincodes/services. Keep secret operations outside endorsement simulation and reuse existing identity, endorsement, storage, and benchmark facilities where they satisfy the specification.
8. **Evaluation and reporting.** Run the experiments in §7, classify every result by evidence level, and revise the final claims to match what was actually demonstrated or proved.

There is no ROR/AKE proof: the project does not design an authenticated key-exchange protocol. Existing secure transport is an explicit deployment assumption.

---

## 7. Evaluation plan

**Correctness and compatibility.** Reproduce the reported accumulation error, then test single-row, multi-row, mixed user/system, and unsatisfied policies; consistent GID use; correct threshold subsets; and combiner verification. Publish test vectors with exact parameters and expected intermediate values.

**Authorization and replay tests.** Exercise direct endpoint calls without evidence, forged/insufficient endorsements, wrong channel/domain/GID, changed ciphertext hash or policy digest, invalid/uncommitted transactions, nonce reuse, stale epochs, expiry, and revoked/stale policy versions under the declared snapshot semantics. Race concurrent consumption attempts, duplicate requests across share services, and restart services between durable recording and delivery. Verify that retries remain the same logical operation and that no honest first release precedes valid consumption.

**Threshold/adversarial tests.** For each selected `(t,n)`, corrupt up to `t−1` holders, withhold responses, send malformed shares and proof transcripts, repeat participant indices, and mix keys, epochs, rows, or request contexts. Test reused/related ciphertext components and attempts to repurpose previously authorized raw pairing values. A test failure here may invalidate the proposed security claim. Passing finite tests is evidence of implementation behavior, not a proof of impossibility.

**Micro-benchmarks.** Measure DKG setup separately from per-request `KeyGen`, `Encrypt`, authorization verification, share generation/proof generation, share verification, combination, and final decryption. Use `(t,n) ∈ {(2,3),(3,5),(4,7)}` subject to the selected protocols' fault constraints. Vary policy size, number of system rows, responding holders, and network delay. Use identical documented baseline parameters across variants; no modern-curve speed/security comparison is promised.

**End-to-end and ablations.** Compare stock Janus, correctness-fixed Janus, a single-service authorization-checking variant, and full Cerberus. Report request latency distributions, throughput, failure/recovery rates, CPU/memory, and bytes exchanged, with hardware/software versions, workload, warm-up, repetitions, and uncertainty. A single-service variant is an ablation, not evidence of tolerance to holder compromise. Reuse the repository's harness where possible and explain any changes.

**Ledger and audit cost.** Measure endorsement and valid-commit latency, cross-chain evidence handling, request/evidence size, consumption-state growth, local replay-state storage, and optional completion receipts. Separate authorization-consumed, share-released, combined, and delivered outcomes. Explain orphaned consumption records and ledger-outage behavior; do not equate logged authorization with observed plaintext use.

**Related-work comparison.** Compare Janus, mediated/server-aided ABE, threshold PRE, BMHADS, Du et al., TMACS, and the Banerjee–Bera–Das baseline by protected secret, mandatory online assistance, commitment checks, ciphertext/GID binding, replay model, stakeholder corruption threshold, verification cost, assumptions, and artifact evidence. Use “specified,” “proved under stated model,” “implemented/tested,” and “unknown” rather than unsupported yes/no labels. Published timings from different workloads or security settings are not direct performance wins.

**Acceptance criteria.** A completed core result requires a pinned audit; an explicit S1 definition; a complete authorization/consumption protocol; a specified threshold construction with the stated verification relation; passing correctness, replay, and failure tests; and a proof or clearly delimited partial analysis of the central claim. An incomplete enforcement proof must be reported as incomplete, not presented as a secure realization.

---

## 8. Timeline

Mid-evaluation is expected around 1 October 2026; final presentation around mid-November 2026. Dates remain subject to the course schedule.

| Phase | Window | Work | Output / decision gate |
|---|---|---|---|
| P0 | Weeks 1–2, through mid-evaluation | Pin artifacts; literature mapping; standalone plugin reproduction; correctness vectors; classify Problems 1–4; initial threat model | Findings report + slides; confirmed/hypothesis evidence ledger |
| P1 | Weeks 3–4 | S1 games; S2 evidence/consumption semantics; choose DKG; specify S3 relation; analyze related-ciphertext queries | Construction and proof-obligation document; reject or revise an unsound candidate before integration |
| P2 | Weeks 5–6 | Implement S2/S3/S5; integrate S4 verification; concurrency/restart and malicious-share tests; continue proofs | Working prototype + regression and attack tests |
| P3 | Week 7 | Complete or delimit computational analysis; symbolic correspondence model; failure and cross-chain tests | Proofs/limitations + verification output + documented failure semantics |
| P4 | Week 8 | Fixed-parameter benchmarks, ablations, evidence-backed comparisons, report and presentation | Final report + artifact + benchmark data + slides |

**Mid-evaluation scope.** Evidence and a defensible design. If the endpoint-bypass hypothesis is refuted, report the deployment conditions that prevent it and retain only supported claims. The formalization, secret-concentration analysis, and reported correctness issue remain relevant subject to their own verification.

**Schedule control.** S1/S2 and threshold-transform soundness take priority. No proactive refresh, governance aggregation, new key exchange, or curve migration is scheduled. If DKG integration or the enforcement proof remains incomplete, deliver and label the verified subset and unresolved obligations; a centralized setup experiment is not a completed distributed enforcement result.

---

## 9. Deliverables

1. Revised proposal and a primary-source related-work matrix.
2. Mid-evaluation findings report and slides, with pinned source evidence and hypothesis outcomes.
3. Formal HMBAC authorization-to-transform definition, construction specification, proofs, and explicitly unresolved obligations.
4. Symbolic models and outputs, with abstraction limits and concrete state-machine tests.
5. Research implementation based on the Janus and ABE-plugin artifacts, with exact revisions, deployment instructions, and retained license notices after license verification.
6. Reusable correctness vectors and authorization/replay/malicious-share regression tests.
7. Benchmark configurations, raw results, ablations, and evidence-qualified comparison tables.
8. Final course report and presentation, distinguishing proposed, proved, and implemented properties.
9. Responsible disclosure correspondence if reproduced findings warrant it.

---

## 10. Novelty claims

The intended claims, stated conservatively and subject to the completed review, are:

1. **HMBAC-specific formalization.** To our knowledge, an explicit formulation of the correspondence between AVF/AF decisions, valid ledger commitment, one logical authorization consumption, and fresh system-side transforms under a stated stakeholder-corruption bound is a potentially useful contribution to the Janus/HMBAC setting. We do not claim the first formal definition of mediated or enforced decryption generally.
2. **Authorization-bound threshold domain gate.** To our knowledge, adapting Janus's mandatory system-attribute secret into a distributed transform service with independently verified committed authorization is a potentially distinctive HMBAC integration. A claim of realization depends on completing the construction and central proof. Threshold key management or threshold proxy transformation alone is not novel.
3. **Reproducible artifact analysis.** A source- and experiment-grounded assessment of Janus's authorization boundary and supported policy behavior, with fixes and measured enforcement costs. Exploit claims depend on reproduction, not only on permissive-looking configuration.

Share verification and existing verifiable outsourced-decryption ideas support these goals; we do not claim their invention or an unverified “first” HMBAC deployment. Nor do we claim general escrow freedom: the design distributes the domain enforcement secret under a threshold assumption and retains separate trust assumptions for attribute issuance, authorization, and consensus.

No novelty claim is made for a new ABE scheme, DKG, signature/proof primitive, consensus mechanism, parameter-size upgrade, aggregate-signature governance, proactive refresh, post-quantum security, or logging every subsequent plaintext access.

---

## 11. Risks and mitigations

| Risk | Assessment | Mitigation / consequence for claims |
|---|---|---|
| Administrator bypass is unreachable in the actual deployment | Open empirical question | Pin credentials, topology, policies, inputs, and logs; report a refuted or conditional hypothesis honestly |
| Audit source/version assumptions are wrong or incomplete | Material | Recheck exact code and configurations before claiming confirmed runtime behavior |
| Prior mediated/server-aided or threshold work already covers the claimed property | Material novelty risk | Compare games and constructions, including recent work; narrow the claim to supported HMBAC integration/artifact results |
| Endorsements are mistaken for valid commitment | High-impact design risk | Require independent valid-commit/state checks; test unsubmitted, invalidated, and conflicting transactions |
| Cross-chain snapshots, expiry, retries, or crashes permit inconsistent release | High implementation risk | One authoritative consume point; explicit lease semantics; durable idempotent responses; fail closed when evidence is unavailable |
| Raw pairing outputs can be repurposed for unauthorized related ciphertexts | Central cryptographic risk | Include such queries in S1 and attack tests; analyze object registration and ciphertext integrity; change the construction or narrow the result if proof fails |
| DKG commitments/proofs leak useful material or lack malicious-party robustness | Central cryptographic risk | Select a concrete DKG, specify public leakage, prove the two-witness relation, and analyze composition; algebraic interpolation alone is insufficient |
| Share proofs validate individual rows but the combiner returns an incorrect product | Concrete correctness risk | User recomputes combination and row selection/product; reproduce the accumulator regression |
| Correlated infrastructure or endorsement compromise defeats independence | Deployment risk | Map shares and signing identities to organizations and failure domains; distinguish transform, authorization, and consensus thresholds |
| Long-lived compromise accumulates `t` shares | Known baseline limitation | State a static lifetime corruption bound; do not imply that epoch counters provide proactive protection |
| Proof or implementation exceeds the course schedule | High scope risk | Start soundness analysis before integration; prioritize core correspondence; label partial results and omit unsupported theorems |
| Legacy parameters limit practical security | Known limitation | Use synthetic data and disclose parameters; defer a fully specified modern pairing instantiation |
| Full Kubernetes deployment is impractical on available hardware | Operational risk | Use standalone services for correctness first; secure suitable hardware for end-to-end measurements and document what was actually run |

---

## 12. Ethics and responsible disclosure

Test only deployments controlled by the project, with synthetic data and credentials. No real patient data or third-party systems are required. If a bypass or other security-relevant behavior is reproduced, privately notify the Janus authors and CENSUS before public exploit details and allow a reasonable response period consistent with course requirements.

Reports will state the tested commit, prerequisites, affected configuration, and limits. A permissive example policy, a source observation, and a demonstrated deployment exploit are different findings. Benchmarks and diagrams must not imply production readiness or security beyond the stated proof and parameter setting.

---

## 13. References

**Assigned and extended systems**

1. V. Malamas, P. Kotzanikolaou, T. K. Dasaklis, M. Burmester. *A Hierarchical Multi Blockchain for Fine Grained Access to Medical Data.* IEEE Access, 8:134393–134412, 2020. Assigned paper; publication details retained from the source proposal.
2. V. Malamas, G. Palaiologos, P. Kotzanikolaou, M. Burmester, D. Glynos. [*Janus: Hierarchical Multi-Blockchain-Based Access Control (HMBAC) for Multi-Authority and Multi-Domain Environments.*](https://doi.org/10.3390/app13010566) Applied Sciences, 13(1):566, 2023. Artifacts: [Janus](https://github.com/CENSUS/Janus) and [Vault ABE plugin](https://github.com/CENSUS/vault-secrets-abe-janus). Audit revisions to be pinned.

**Cryptographic foundations and close prior art**

3. A. Lewko, B. Waters. *Decentralizing Attribute-Based Encryption.* EUROCRYPT 2011. Use Appendix D for the prime-order variant and identify its proof model explicitly.
4. M. Green, S. Hohenberger, B. Waters. *Outsourcing the Decryption of ABE Ciphertexts.* USENIX Security 2011. Outsourcing syntax/security prior art; no automatic theorem transfer to Cerberus.
5. L. Ibraimi, M. Petkovic, S. Nikova, P. Hartel, W. Jonker. [*Mediated Ciphertext-Policy Attribute-Based Encryption and Its Application.*](https://doi.org/10.1007/978-3-642-10838-9_23) WISA 2009, LNCS 5932, pp. 309–323. [Author-hosted extended version](https://research.utwente.nl/files/5098398/Mediated_Ciphertext-Policy_Attribute-Based_Encryption_and_its_Application_%28extended_version%29.pdf).
6. J. Lai, R. H. Deng, C. Guan, J. Weng. *Attribute-Based Encryption With Verifiable Outsourced Decryption.* IEEE TIFS, 8(8), 2013. Full construction must be checked before adopting any mechanism.
7. F. Yang, H. Cui, J. Jing. [*Generic Constructions of Server-Aided Revocable ABE with Verifiable Transformation.*](https://doi.org/10.1007/978-3-031-41181-6_25) ACNS Workshops 2023, pp. 459–479. [Author-institution publication record](https://research.monash.edu/en/publications/generic-constructions-ofserver-aided-revocable-abe-withverifiable).
8. [*A Threshold Proxy Re-Encryption Scheme for Secure IoT Data Sharing Based on Blockchain.*](https://doi.org/10.3390/electronics10192359) Electronics, 10(19):2359, 2021. Concrete prior art for blockchain-assisted threshold transformation; full security-model comparison remains required.
9. R. Gennaro, S. Jarecki, H. Krawczyk, T. Rabin. *Secure Distributed Key Generation for Discrete-Log Based Cryptosystems.* Journal of Cryptology, 2007. A foundation to evaluate when selecting the concrete DKG, not shorthand for a fully specified implementation.
10. D. Chaum, T. P. Pedersen. *Wallet Databases with Observers.* CRYPTO 1992. Related discrete-log proof background; S3 specifies a generalized two-witness representation relation rather than citing a single equality-of-logs proof as sufficient.

**Application and authority-management comparisons**

11. H. Yuan, G. Dong, L. Zhao. [*A blockchain-based multi-authority hierarchical attribute encrypted data sharing scheme in the Internet of Medical Things.*](https://doi.org/10.1371/journal.pone.0349767) PLOS One, 21(5):e0349767, 27 May 2026. BMHADS; distinguish collaborative authentication from its separate ABE key-generation mechanism.
12. J. Du, G. Dong, J. Ning, Z. Xu, R. Yang. [*Blockchain-based and multi-authority hierarchical access control data sharing scheme.*](https://doi.org/10.1016/j.compeleceng.2024.109547) Computers and Electrical Engineering, 119:109547, 2024. Detailed property/artifact mapping remains to be completed.
13. W. Li, K. Xue, Y. Xue, J. Hong. *TMACS: A Robust and Verifiable Threshold Multi-Authority Access Control System in Public Cloud Storage.* IEEE Transactions on Parallel and Distributed Systems, 27(5), 2016. Retrieve and check the primary publication and exact key-management/security model before final comparison claims.
14. S. Banerjee, B. Bera, A. K. Das, S. Chattopadhyay, M. K. Khan, J. J. P. C. Rodrigues. *Private blockchain-envisioned multi-authority CP-ABE-based user access control scheme in IIoT.* Computer Communications, 169:99–113, 2021. Bibliographic details retained from the source proposal; full-text comparison pending.

**Platform semantics**

15. Hyperledger Fabric documentation. [*Transaction Flow.*](https://hyperledger-fabric.readthedocs.io/en/latest/txflow.html) Read with the exact release documentation used by the implementation.
16. Hyperledger Fabric documentation. [*Endorsement policies.*](https://hyperledger-fabric.readthedocs.io/en/latest/endorsement-policies.html) Endorsement thresholds are distinct from threshold secret sharing and consensus fault bounds.

**Reference status.** Linked primary/publication sources support the corrected related-work and Fabric descriptions. Bibliographic verification is not a completed security review of a construction. The final report will attach checked primary texts, literature-search coverage, exact artifact revisions, and a claim-to-evidence mapping. The ROR/AKE and proactive-refresh references from the original core plan are removed because those components are out of scope.
