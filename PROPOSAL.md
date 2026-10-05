# Project Proposal

## Cerberus: Cryptographically Enforced, Threshold-Distributed Access Control for Hierarchical Multi-Blockchain Environments

**Course:** Research in Information Security, IIIT Hyderabad
**Instructors:** Prof. Ashok Kumar Das, Prof. Srinathan Kannan
**Assigned paper:** Malamas, Kotzanikolaou, Dasaklis & Burmester, *A Hierarchical Multi Blockchain for Fine Grained Access to Medical Data*, IEEE Access 8 (2020) 134393–134412
**System extended:** Malamas, Palaiologos, Kotzanikolaou, Burmester & Glynos, *Janus: Hierarchical Multi-Blockchain-Based Access Control (HMBAC)*, Applied Sciences 13(1):566, 2023
**Date:** 17 September 2026
*(“Cerberus” is a working name — the guardian of a gate, split across heads. Replace if you prefer.)*

---

## 1. Summary

Janus is, to our knowledge, the only artifact-backed implementation of hierarchical multi-blockchain access control. Its headline contribution is a **cryptographically enforced single point of access**: medical data is encrypted under a policy carrying an extra `AND` clause that only the system can satisfy, so stolen ciphertext is useless and every access must pass through the blockchain and be logged.

We have audited the Janus source and specification. We find that this property is **asserted but not defined, enforced by access-control configuration rather than by cryptography, concentrated in a single trusted key store, and in one code path computed incorrectly with respect to the scheme it claims to implement.**

We propose **Cerberus**: the first formal security definition of HMBAC-style enforced decryption, and a construction that meets it by (i) binding system-side decryption to an unforgeable on-chain capability, (ii) splitting the gatekeeper key `t`-of-`n` across a domain's stakeholders using distributed key generation and threshold partial decryption, and (iii) making the transform verifiable by the user. We will prove the construction secure, verify the protocol in ProVerif, implement it on the Janus artifact, and evaluate it against Janus and current multi-authority schemes.

---

## 2. Background: the current architecture, across the literature

### 2.1 The assigned paper (IEEE Access 2020)

A two-layer blockchain for medical data:

- **Proxy Blockchain** — single access point; lets independently managed trust authorities interoperate; immutable single source of truth.
- **Domain Blockchains** — one per domain (hospitals, device manufacturers, insurers); each enforces its own policy.
- **CP-ABE** with decryption split between user and system; certificate-based revocation; "tailored forensics" for granular auditing.
- Proof of concept only — no end-to-end implementation, so practicality was unproven. This is what motivated Janus.

### 2.2 Janus (Applied Sciences 2023) — the system we extend

| Layer | Component | Function |
|---|---|---|
| Frontend | Electron/React client | 2FA login, request submission |
| Proxy chain | **PSC** | user validation, stakeholder voting, request forwarding |
| Proxy chain | **TMSC** | certificate/attribute validation, trust anchors, revocation lists |
| Proxy chain | **LSC** | logging — the "global source of truth" |
| Domain chain | **ACSC** | intra- and cross-domain policy enforcement |
| Domain chain | **KSSC** | holds the domain attribute key; performs system-side partial decryption |
| Data | per-stakeholder DBs | AES-encrypted records, off-chain |

**The HMBAC model** defines sets `U, Au, S, K, D` and three gates: **AVF** (attribute verification, proxy chain), **AF** (authorisation against inter-/cross-domain policy, domain chain), **DF** (partial decryption, domain chain).

**The enforcement mechanism.** Each record `dᵢ` is AES-encrypted under `kᵢ`; `kᵢ` is MA-CP-ABE encrypted under a policy extended with an `AND` clause requiring the **domain attribute**. Only the KSSC holds `SK_D`; on an authorised request it computes `K_{D,GID} = KeyGen(GID, GP, D, SK_D)` on the fly, bound to the requester's GID, and partially decrypts. The user completes decryption with their own attribute keys.

**Implementation:** Hyperledger Fabric, Raft consensus, Kubernetes pods, Fabric CA per stakeholder, HashiCorp Vault with a custom Go ABE plugin (`CENSUS/vault-secrets-abe-janus`, BSD-2).

**Stated future work:** Byzantine-tolerant consensus; user credential management. *(The first is now largely obsolete — Fabric 3.0, September 2024, ships SmartBFT.)*

### 2.3 The cryptographic substrate — Lewko–Waters (EUROCRYPT 2011)

Janus implements LW11's **prime-order** construction (Appendix D), confirmed by matching `constructSystemAttribute` against the paper:

```
PK   = { e(g,g)^{αᵢ}, g^{yᵢ} }            SK = { αᵢ, yᵢ }
C₀   = M·e(g,g)ˢ
C₁ₓ  = e(g,g)^{λₓ}·e(g,g)^{α_{ρ(x)}·rₓ}    C₂ₓ = g^{rₓ}    C₃ₓ = g^{y_{ρ(x)}·rₓ}·g^{ωₓ}
K_{i,GID} = g^{αᵢ}·H(GID)^{yᵢ}
Decrypt: ∏ₓ [ C₁ₓ·e(H(GID),C₃ₓ) / e(K_{ρ(x),GID},C₂ₓ) ]^{cₓ} = e(g,g)ˢ,  where Σ cₓAₓ = (1,0,…,0)
```

Two properties matter for this proposal:

1. **`K = g^α·H(GID)^y` is linear in the exponents `α, y`.** Shamir sharing plus Lagrange interpolation *in the exponent* therefore reconstructs it exactly. This is what makes our threshold design sound rather than aspirational.
2. **Security of the prime-order variant is proven only in the generic bilinear group model, with `H` as a random oracle.** The composite-order variant has the stronger static-assumption proof. Janus cites LW11 without distinguishing the two.

### 2.4 The paradigm Janus should have used — Green–Hohenberger–Waters (USENIX Security 2011)

GHW11 outsources ABE decryption to an untrusted proxy: pick random `z`, raise key elements to `1/z` to form a **transformation key TK**; the proxy transforms a ciphertext into a short ElGamal-style ciphertext and **learns nothing about the message**; the user finishes with `z`. GHW11 supplies **CPA- and RCCA-with-outsourcing security definitions**.

**The structural comparison is the core of our argument:**

| | GHW11 | Janus KSSC |
|---|---|---|
| Who owns the key the proxy uses | the **user** (blinded) | the **system** |
| Trust in the proxy | none required | fully trusted |
| Security definition | CPA / RCCA with outsourcing | **none given** |
| User can verify the transform | (added by Lai et al. 2013) | no |
| Purpose | efficiency | **access enforcement** |

Janus repurposed the *mechanism* of outsourced decryption to achieve *enforcement*, a goal GHW11 never addressed, and in doing so inherited none of its guarantees. That gap is our opening.

### 2.5 Closest related systems

| Work | Architecture | Multi-authority | Key escrow fix | Enforced single point of access | Artifact |
|---|---|---|---|---|---|
| IEEE Access 2020 (assigned) | two-layer multi-blockchain | yes | no | claimed | no |
| **Janus 2023** | two-layer multi-blockchain | yes | no (single Vault) | **claimed, ACL-enforced** | **yes** |
| BMHADS, PLOS One 2026 | single consortium chain | yes | **yes** — DKG + BLS threshold + PSS on the **issuance** key | no | partial |
| Du et al., CEE 2024 | cloud + blockchain | two authorities (KGC, AAC) | yes | no | no |
| TMACS (Li et al.) | threshold multi-authority | yes | yes — threshold master key | no | no |
| Banerjee, Bera, Das et al., ComCom 2021 | private blockchain | yes | — | no | no |
| **Cerberus (this proposal)** | two-layer multi-blockchain | yes | **yes — on the *enforcement* key** | **yes, cryptographically** | **yes** |

**The distinction that carries our novelty claim:** BMHADS and TMACS threshold the key used to **issue** user attribute keys, to remove escrow at issuance. We threshold the key used to **enforce** the access gate, to remove a bypass and a single point of compromise. Different key, different adversary, different security goal — but we will state this explicitly, because it is the first thing a reviewer will probe.

---

## 3. Problem statement

Janus claims two properties (its Table 1 marks both as things competing systems lack):

> **P1 — Enforces a single point of access** that "cannot be bypassed by users or authorities."
> **P2 — Global source of truth**: all access transactions immutably logged and globally verifiable.

Our audit identifies four problems. Status is marked honestly: **[CONFIRMED]** means verified against the specification or the source; **[HYPOTHESIS]** means read from code and configuration but not yet demonstrated on a running system.

### Problem 1 — The enforced property has no security definition **[CONFIRMED]**
Janus §6 argues security informally. There is no game, no adversary model, and no reduction for the two-step decryption. It is therefore not possible to say what P1 means formally, nor what breaks it. GHW11 shows that outsourced decryption *can* be defined rigorously; Janus simply does not do so.

### Problem 2 — Enforcement rests on access-control configuration, not cryptography **[CONFIRMED in code; bypass is HYPOTHESIS]**
`plugin/sys_decrypt_path.go` authenticates **nothing** about its caller's input. `cryptogram`, `sub_policy`, `subject` and `entity_id` are all caller-supplied, with no signature, nonce, expiry or well-formedness check. The only thing standing between a caller and a system-side partial decryption is a Vault ACL.

The shipped stakeholder-**admin** policy (`configs/vault/policies/attikon-hospital-admin.hcl`) grants `create`/`update` on `sysdecrypt/<org>/*`. If that is reachable in practice, a stakeholder administrator can obtain a partial decryption **without any blockchain transaction** — defeating P1 (an *authority* bypasses the gate) and P2 (nothing is logged). Confirming or refuting this is our first empirical task.

Two related issues: the collusion binding hashes the caller-supplied `subject` while attribute keys load under a separate caller-supplied `entity_id`, although LW11's collusion resistance depends on a single `H(GID)` binding all key components **[HYPOTHESIS]**; and the LSSS coefficients are derived from the *ciphertext's* policy while pruning uses the *caller's* sub-policy **[HYPOTHESIS]**.

### Problem 3 — The gatekeeper key is a single point of compromise **[CONFIRMED]**
`SK_D` resides in one Vault instance per domain, and Janus §6 explicitly assumes Vault, Kubernetes and the pods are trusted. Compromising one Vault yields the ability to forge the domain attribute key for **any** GID, collapsing P1 for that entire domain. This is the strongest trust assumption in a system whose stated goal is to avoid globally trusted authorities.

### Problem 4 — A confirmed correctness defect **[CONFIRMED against LW11]**
LW11 decryption requires the **product** over rows, `∏ₓ(·)^{cₓ}`. In `sys_decrypt_path.go` the accumulator is **assigned** inside the loop (`EggS = Set(div).ThenPowBig(cₓ)`) rather than multiplied, so only the final attribute contributes. This is correct for the intended single-attribute system policy and silently wrong for any multi-attribute system sub-policy — which also means a user today cannot distinguish a buggy KSSC from a malicious one.

Additionally, the deployed parameters give `r` at 160 bits (~80-bit security), below the 128-bit baseline, and the prime-order LW11 variant carries only a generic-group-model proof.

---

## 4. Proposed solution

### 4.1 Component S1 — A formal definition of HMBAC-enforced decryption
*Backed by: GHW11 (definitional template), LW11 (underlying scheme).*

We define an **enforced outsourced decryption** primitive with algorithms `Setup, AuthSetup, KeyGen, Enc, Capability, Transform, Decrypt`, and two games:

- **Enforcement soundness.** No PPT adversary — even holding a set of attribute keys satisfying the user-side policy, and corrupting up to `t−1` domain stakeholders — can produce a decryptable transform without a valid capability issued by the proxy chain.
- **Transform privacy.** The entities performing `Transform` learn nothing about the plaintext, formalised as in GHW11's CPA/RCCA-with-outsourcing games.

Collusion resistance is inherited from LW11 and must be shown to be preserved under our modifications.

### 4.2 Component S2 — Capability-bound partial decryption
*Backed by: the Problem 2 findings; GHW11's transform paradigm; standard EUF-CMA signatures.*

The KSSC transform executes **only** on presentation of a capability token

```
σ = Sign_proxy( GID ‖ data_ID ‖ policy_id ‖ nonce ‖ expiry )
```

signed by the proxy chain after AVF and endorsed by ACSC after AF. **The Vault plugin verifies `σ` itself**, so a direct call to the endpoint with no preceding blockchain transaction fails by construction rather than by policy file. We additionally bind `subject ≡ entity_id` and derive the system sub-policy from the ciphertext rather than from caller input.

This restores P1 against authorities, and restores P2 as a corollary: no transform can occur without a logged, signed transaction.

### 4.3 Component S3 — Threshold gatekeeper key (the MPC contribution)
*Backed by: BMHADS (DKG + BLS threshold + PSS machinery), TMACS (threshold multi-authority prior art), LW11 (exponent linearity), Chaum–Pedersen (share-correctness proofs).*

**Distributed setup.** The `n` stakeholders of a domain run a GJKR/Pedersen DKG over `Z_p` to jointly generate `(α_D, y_D)`. Each `Sᵢ` holds shares `α_D^{(i)}, y_D^{(i)}`; the public key `(e(g,g)^{α_D}, g^{y_D})` is published. **No party ever learns `α_D` or `y_D`.**

**Threshold transform.** On an authorised request for `GID`, each participating stakeholder computes its own share of the pairing rather than a share of the key:

```
Kᵢ = g^{α_D^{(i)}} · H(GID)^{y_D^{(i)}}          Tᵢ = e( Kᵢ , C₂ₓ )
∏ᵢ Tᵢ^{Lᵢ} = e( g^{α_D}·H(GID)^{y_D} , C₂ₓ ) = e( K_{D,GID} , C₂ₓ )
```

where `Lᵢ` are Lagrange coefficients. The gatekeeper key `K_{D,GID}` is therefore **never assembled anywhere**, in contrast to a naive design that reconstructs it and then decrypts. The transform completes as `C₁ₓ·e(H(GID),C₃ₓ)` divided by the combined value.

**Robustness.** Each `Sᵢ` publishes a Chaum–Pedersen NIZK proving its share is consistent with its DKG commitment, so a malicious stakeholder producing a bad share is both detected and attributed, rather than silently corrupting the result.

**Refresh.** Proactive secret sharing rotates shares between epochs without changing the public key, so an adversary must corrupt `t` stakeholders *within one epoch*.

**Mapping to the platform.** The `t`-of-`n` access structure maps naturally onto Hyperledger Fabric's endorsement policy, which is already a threshold mechanism over organisations — so the security requirement and the deployment configuration become the same object.

### 4.4 Component S4 — Verifiable transform
*Backed by: Lai, Deng, Guan & Weng, IEEE TIFS 2013; GHW11.*

A checkability tag lets the user verify the transform was computed correctly. Problem 4 shows this is not hypothetical — an incorrect KSSC already exists in the shipped code, and users have no way to notice.

### 4.5 Component S5 — Correctness and parameters
*Backed by: LW11 Appendix D as ground truth.*

Fix the product/assignment defect; construct LW11 test vectors as a regression suite; migrate from 160-bit to ≥256-bit group order and quantify the cost.

### 4.6 Component S6 — Aggregate signatures for governance *(secondary)*
*Backed by: BMHADS (BLS machinery we already need for S3); Janus PSC voting functions.*

Janus's stakeholder voting has each administrator sign a ballot individually. An aggregate/multi-signature compresses a majority decision to one compact signature. Low cost, reuses S3's primitives, and addresses an explicit syllabus topic.

---

## 5. Threat model

**Entities:** users, stakeholder organisations (authorities) grouped into domains, proxy chain, domain chains, per-stakeholder databases and Vaults.

**Adversary classes.** Janus considers compromised nodes and compromised users. We add the class its analysis omits and which Problem 2 suggests is decisive:

- **A1 — external attacker.** No valid credentials. *(As in Janus.)*
- **A2 — malicious user.** Valid credentials; tries to exceed their policy or collude with other users. *(As in Janus.)*
- **A3 — malicious-but-authorised stakeholder administrator.** Holds legitimate administrative credentials for their own organisation, controls their own database and Vault access, and attempts to obtain data outside policy or without leaving an audit record. **New in our model.**
- **A4 — up to `t−1` colluding domain stakeholders.** Attempt to reconstruct the gatekeeper key or forge transforms. **New; only meaningful once S3 exists.**

**Assumptions we retain:** AES and the MA-ABE scheme are secure; consensus is correct; a majority of stakeholders behave honestly for governance decisions; users protect their own credentials.

**Assumptions we remove:** that Vault and the key-holding pod are trusted (S3); that callers of the ABE plugin are authenticated by configuration alone (S2).

---

## 6. Methodology

1. **Empirical audit.** Reproduce Problems 2–4 on a running instance; record which hypotheses hold.
2. **Formalisation.** Define the primitive and the two games (S1).
3. **Construction.** Specify Cerberus as algorithms with explicit inputs/outputs.
4. **Security proof.** Reduce enforcement soundness to EUF-CMA of the capability signature plus the secrecy of `α_D, y_D` under the DKG; reduce transform privacy to LW11's security in GHW11's style. State plainly that the inherited LW11 guarantee for the prime-order variant is generic-group-model.
5. **Protocol proof.** ROR-model proof of the request/authorisation exchange (session-key security), following the Abdalla–Fouque–Pointcheval formulation.
6. **Formal verification.** Model the protocol in **ProVerif** (Scyther as fallback); check secrecy and authentication properties.
7. **Implementation.** Modify the Go ABE plugin and the KSSC/ACSC/PSC chaincodes on the Janus artifact.
8. **Evaluation.** Benchmarks and comparison tables (§7).

---

## 7. Evaluation plan

**Correctness.** LW11 test-vector regression suite; demonstration that the current code fails multi-attribute system policies and that ours does not.

**Micro-benchmarks.** `KeyGen`, `Encrypt`, system transform, user decryption — at 160-bit (baseline) and ≥256-bit, and for threshold configurations `n ∈ {3,5,7}`, `t ∈ {2,3,4}`.

**End-to-end.** Request latency and throughput versus stock Janus, reusing the repository's existing benchmark harness so numbers are comparable to the published ones.

**On-chain cost.** Capability token size, endorsement latency, log growth; governance transaction size with and without aggregate signatures.

**Comparison tables.** Against Janus, BMHADS, Du et al. 2024, TMACS and Banerjee–Bera–Das, on: multi-owner setting, dynamic trust management, inter/cross-domain policy, enforced single point of access, global source of truth, escrow freedom, threshold tolerance, verifiable transform, formal proof, artifact.

---

## 8. Timeline

Mid-evaluation ~1 October 2026; final presentation ~mid-November 2026.

| Phase | Window | Work | Output |
|---|---|---|---|
| **P0** | Weeks 1–2 (→ mid-eval) | Standalone ABE plugin environment; LW11 test vectors; confirm/refute Problems 2–4; threat model A1–A4; design sketch | **Mid-eval: findings report + slides** |
| **P1** | Weeks 3–4 | Formal definition and games (S1); full construction spec (S2, S3) | Definition + construction document |
| **P2** | Weeks 5–6 | Implement S2 and S5; implement S3 (DKG, threshold transform, Chaum–Pedersen proofs) | Working code + regression suite |
| **P3** | Week 7 | Security proofs; ROR proof; ProVerif model; S4 and S6 if on schedule | Proofs + verification output |
| **P4** | Week 8 | Benchmarks, comparison tables, write-up, presentation | **Final report + artifact + slides** |

**Mid-evaluation scope, explicitly.** Evidence and design, not a working fix. The presentation is built so that it stands **even if every hypothesis in Problem 2 is refuted** — Problems 1, 3 and 4 are established by reading the specification and the source, and do not depend on the bypass being reachable. A refuted hypothesis is reported as a characterisation of the real trust boundary, which is itself a result.

---

## 9. Deliverables

1. This proposal.
2. Mid-evaluation findings report and slides.
3. Formal definition, construction specification, and security proofs.
4. ProVerif/Scyther models and output.
5. Implementation as a fork of `CENSUS/Janus` and `CENSUS/vault-secrets-abe-janus` (both BSD-2, so redistribution is permitted).
6. LW11 test-vector suite — reusable independently of this project.
7. Benchmark data and comparison tables.
8. Final report in the format the course requires.
9. Disclosure correspondence with the Janus authors, if findings warrant it.

---

## 10. Novelty claims

Stated conservatively, in the order we would defend them:

1. **First formal security definition** of the enforced-single-point-of-access property that HMBAC asserts. *(Strongest claim; independent of any empirical finding.)*
2. **First escrow-free realisation** of that property — thresholding the **enforcement** key, as distinct from BMHADS/TMACS which threshold the **issuance** key.
3. **Security analysis of a deployed artifact** under an adversary class its own threat model omits, including a correctness defect confirmed against the scheme's specification.
4. **First verifiable** system-side transform in a hierarchical multi-blockchain access control system.
5. Secondary: aggregate-signature governance, and a quantified 128-bit parameter migration.

We do not claim: a new ABE scheme, post-quantum security, or a new consensus mechanism.

---

## 11. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Problem 2 bypass turns out to be unreachable | Medium | Mid-eval framed around Problems 1, 3, 4, which are already confirmed; a refutation is reported as a result |
| Authors argue the Vault ACLs are illustrative, not normative | Medium | Frame as "the deployed configuration does not enforce the paper's claim", and separately show the plugin performs no cryptographic caller check regardless of configuration |
| Reviewer reads S3 as a straightforward application of known threshold techniques | Medium-high | State the issuance-key vs enforcement-key distinction explicitly and early; emphasise that the key is never reconstructed |
| Proofs exceed the team's depth | Medium | Reuse GHW11's definitional template rather than inventing one; start P1 immediately after mid-eval; proofs are the one component that cannot be delegated to tooling |
| AI-generated pairing code is plausibly wrong | **High** | Test vectors are built in P0, before any crypto is modified; every change gated on the regression suite |
| Full Kubernetes deployment infeasible on laptops | Medium | P0–P2 use the standalone plugin `docker-compose`; request a college server for P4 end-to-end runs |
| Scope creep | High | Post-quantum migration, ZKP log privacy, revocation and IoMT extensions are explicitly out of scope |

---

## 12. Ethics and responsible disclosure

The findings concern a publicly released artifact from an academic group and a commercial security firm (CENSUS). If the hypotheses in Problem 2 are confirmed, we will notify the authors (V. Malamas, University of Piraeus) and CENSUS **before** any public presentation, and allow a reasonable response window. No system outside our own deployment will be tested. Published data in the artifact is synthetic demo data; no real patient data is involved.

---

## 13. References

**Assigned and extended**
1. V. Malamas, P. Kotzanikolaou, T. K. Dasaklis, M. Burmester. A Hierarchical Multi Blockchain for Fine Grained Access to Medical Data. *IEEE Access*, 8:134393–134412, 2020.
2. V. Malamas, G. Palaiologos, P. Kotzanikolaou, M. Burmester, D. Glynos. Janus: Hierarchical Multi-Blockchain-Based Access Control (HMBAC) for Multi-Authority and Multi-Domain Environments. *Applied Sciences*, 13(1):566, 2023.

**Cryptographic foundations** *(in `Papers/`)*
3. A. Lewko, B. Waters. Decentralizing Attribute-Based Encryption. *EUROCRYPT 2011*.
4. M. Green, S. Hohenberger, B. Waters. Outsourcing the Decryption of ABE Ciphertexts. *USENIX Security 2011*.

**Closest related systems** *(in `Papers/`)*
5. BMHADS. A blockchain-based multi-authority hierarchical attribute encrypted data sharing scheme in the Internet of Medical Things. *PLOS One*, 2026.
6. J. Du, G. Dong, J. Ning, Z. Xu, R. Yang. Blockchain-based and multi-authority hierarchical access control data sharing scheme. *Computers and Electrical Engineering*, 119:109547, 2024.

**To obtain**
7. J. Lai, R. H. Deng, C. Guan, J. Weng. Attribute-Based Encryption With Verifiable Outsourced Decryption. *IEEE TIFS*, 8(8), 2013.
8. Li et al. TMACS: threshold multi-authority CP-ABE access control. *(cited by [6])*
9. R. Gennaro, S. Jarecki, H. Krawczyk, T. Rabin. Secure Distributed Key Generation for Discrete-Log Based Cryptosystems. *J. Cryptology*, 2007.
10. A. Herzberg, S. Jarecki, H. Krawczyk, M. Yung. Proactive Secret Sharing. *CRYPTO 1995*.
11. M. Abdalla, P.-A. Fouque, D. Pointcheval. Password-Based Authenticated Key Exchange in the Three-Party Setting. *PKC 2005*. — ROR model.
12. D. Chaum, T. P. Pedersen. Wallet Databases with Observers. *CRYPTO 1992*. — discrete-log equality proofs.
13. S. Banerjee, B. Bera, A. K. Das, S. Chattopadhyay, M. K. Khan, J. J. P. C. Rodrigues. Private blockchain-envisioned multi-authority CP-ABE-based user access control scheme in IIoT. *Computer Communications*, 169:99–113, 2021. — comparison baseline.

*All references in the “to obtain” group must be retrieved and checked before the final report; citation details there are from secondary sources.*
</content>
