# Project Idea Catalogue — extending HMBAC / Janus

**Date:** 2026-09-17
**Inputs:** the four papers in `Papers/`, both assigned papers, and the source audit of `janus-repo/` + `vault-secrets-abe-janus/`.
**Constraints assumed:** mid-eval in ~1.5–2 weeks, final in ~2 months, coding done by AI agents, laptops now / server maybe, "a little" novelty required, ROR + formal-verification + comparison-table methodology expected, blockchain must be central, not extending the instructors' own papers.

---

## 0. Two corrections to what I told you earlier

1. **The symmetric (Type A) pairing is *not* a flaw.** LW11's prime-order construction (Appendix D) explicitly uses a symmetric map `e : G₀ × G₀ → G₁`, so a Type A curve is the *correct* choice for the scheme as published. I was wrong to list it as a weakness. What *does* stand is the **size**: `r` is 160-bit, i.e. ~80-bit security, which is below the modern baseline.
2. **Du et al. 2024 is not the competitor I thought it was.** Despite the near-identical title, its "hierarchical" means *data sensitivity levels* (mild/moderate) in a **cloud** setting with two authorities (KGC + AAC). It is not multi-domain and not a multi-blockchain. **It does not overlap with HMBAC.** Good news.

---

## 1. What each paper actually gives us

### 1.1 Lewko–Waters, *Decentralizing Attribute-Based Encryption* (EUROCRYPT 2011)
The scheme Janus implements. Confirmed by matching `constructSystemAttribute` against the paper.

- **Two constructions.** Composite-order (proven under static assumptions, random oracle model, dual-system encryption) and **prime-order (Appendix D), proven only in the *generic bilinear group model* + ROM.** Janus uses the prime-order one, so the guarantee it inherits is the *weaker, heuristic* one. Worth one honest paragraph in our report.
- **Algorithms we need verbatim:**
  - `PK = {e(g,g)^{αᵢ}, g^{yᵢ}}`, `SK = {αᵢ, yᵢ}`
  - `C₀ = M·e(g,g)ˢ`, `C₁ₓ = e(g,g)^{λₓ}·e(g,g)^{α_{ρ(x)}rₓ}`, `C₂ₓ = g^{rₓ}`, `C₃ₓ = g^{y_{ρ(x)}rₓ}·g^{ωₓ}`
  - `K_{i,GID} = g^{αᵢ}·H(GID)^{yᵢ}`
  - Decrypt: `C₁ₓ·e(H(GID),C₃ₓ)/e(K_{ρ(x),GID},C₂ₓ) = e(g,g)^{λₓ}·e(H(GID),g)^{ωₓ}`, then **the product over x** of those raised to `cₓ`, where `Σ cₓAₓ = (1,0,…,0)`.
- **Two facts we exploit:**
  - `K = g^α·H(GID)^y` is **linear in the exponents α, y** ⇒ Shamir sharing of `(α, y)` and Lagrange interpolation *in the exponent* works cleanly. This is what makes Idea I3 sound rather than hand-wavy.
  - Decryption is a **product** over rows. Janus's `sys_decrypt_path.go` **assigns** instead of multiplying ⇒ confirmed deviation from spec (see §2).
- **Security model is IND-CPA, static** (adversary commits to queries up front). Not CCA. Relevant to any oracle-style attack argument.

### 1.2 Green–Hohenberger–Waters, *Outsourcing the Decryption of ABE Ciphertexts* (USENIX Security 2011)
**The most important paper for us.** It is the principled version of what Janus does ad hoc.

- **Key blinding technique:** pick random `z ∈ Z_p`, raise the key elements to `1/z` to get a **transformation key TK**; the user retains `z` as the retrieving key. A proxy holding TK converts a full ABE ciphertext into a short ElGamal-style ciphertext **and learns nothing about the message**.
- **It supplies the security definitions Janus is missing:** CPA-with-outsourcing and **RCCA-with-outsourcing**. We do not have to invent a security model — a huge derisking factor for a student project.
- **The structural insight:** GHW11's proxy is *untrusted by construction* and holds a key **derived from the user's own key**. Janus's KSSC is the mirror image — it holds a **system-owned authority key**, is **fully trusted**, and the user can verify nothing. Janus inherits none of GHW11's guarantees.
- Verifiability is *not* in GHW11 (it is CPA/RCCA only). That came later — Lai, Deng, Guan & Weng, IEEE TIFS 2013. **Worth downloading.**

### 1.3 BMHADS — *Blockchain-based multi-authority hierarchical attribute encrypted data sharing in IoMT* (PLOS One, 2026)
The nearest thing to our threshold idea. Read carefully to stay distinct.

- **Contributions (verbatim summary):** (1) collaborative authentication combining blockchain **DKG + BLS threshold signatures + Proactive Secret Sharing** for periodic key updates without changing public keys; (2) hierarchical multi-authority CP-ABE on **Type-3 curves**, hierarchical access tree encrypting multiple related files at once, **multiple authorities issue key fragments that are aggregated into the user private key — fixing key escrow**; (3) **PRE-based periodic revocation** offloaded to cloud; (4) IND-CPA + DKG validity/robustness/confidentiality/Sybil resistance, implemented on **Hyperledger Fabric with 100 nodes**, ~280 ms consensus latency.
- **Where it does *not* reach:** it is a **single consortium chain**, not a two-layer proxy/domain architecture; it has **no enforced single-point-of-access property**; its threshold machinery secures **key issuance (KeyGen)**, not a **gatekeeper key used for system-side partial decryption**.
- **Verdict: our Idea I3 survives**, but the report must state the distinction explicitly and cite BMHADS as the closest prior art. We should reuse their DKG/PSS machinery rather than reinvent it.

### 1.4 Du et al. — *Blockchain-based and multi-authority hierarchical access control data sharing scheme* (Comput. Electr. Eng., 2024)
- Cloud-centric; hierarchical = **data sensitivity tiers**; two authorities (KGC + AAC) against single-point-of-failure and escrow; smart contracts supervise operations; formal proof + comparative evaluation.
- **Useful to us for two things:** (a) it is a clean **template** for the "formal proof + comparison table" format the course expects; (b) it states the log-privacy problem crisply — recording access transactions on-chain "leads to the disclosure of the visitor's identity and the content of the accessed data to the entire network". That is our Idea I7's motivation, quotable.
- It also points us at **TMACS** (Li et al., threshold multi-authority access control via threshold secret sharing so no single authority holds the master key) — **prior art we must cite for I3. Worth downloading.**

---

## 2. Confirmed findings from the source audit

Status key: **[CONFIRMED-vs-SPEC]** = checked against LW11's text. **[HYPOTHESIS]** = read from code/config, needs a running system to prove.

| # | Finding | Status |
|---|---|---|
| F1 | `sys_decrypt_path.go` **assigns** `EggS` inside the pruned-attribute loop instead of accumulating a product. LW11 requires `∏ₓ(...)^{cₓ}`. Correct only when the system sub-policy has exactly one attribute; silently wrong otherwise. | **[CONFIRMED-vs-SPEC]** |
| F2 | Group order `r` is 160-bit ⇒ ~80-bit security, below the 128-bit baseline. | **[CONFIRMED]** |
| F3 | Janus uses LW11's **prime-order** variant, whose only proof is in the **generic group model**. The paper cites LW11 without noting this. | **[CONFIRMED-vs-SPEC]** |
| F4 | The plugin authenticates **nothing** about its caller's input: `cryptogram`, `sub_policy`, `subject`, `entity_id` are all caller-supplied with no signature, nonce, expiry or well-formedness check. Enforcement rests on **Vault ACLs, not cryptography**, though the paper frames it as a cryptographic guarantee. | **[CONFIRMED in code]** |
| F5 | The stakeholder-**admin** Vault policy grants `create`/`update` on `sysdecrypt/<org>/*`, so an admin token may be able to call system decryption directly — bypassing PSC/TMSC/ACSC **and the LSC log**. Contradicts the paper's "cannot be bypassed by users or authorities" and "global source of truth" claims. | **[HYPOTHESIS]** ← mid-eval task |
| F6 | Collusion binding hashes the caller-supplied `subject`, while attribute keys load under a separate caller-supplied `entity_id`. LW11 collusion resistance depends on **one** `H(GID)` binding all components. | **[HYPOTHESIS]** |
| F7 | `coeff_list` is computed from the **ciphertext's** policy while pruning uses the **caller's** `sub_policy` — a mismatch surface. | **[HYPOTHESIS]** |
| F8 | Domain key `SK_D` lives in a single Vault per domain; Vault/K8s/pods are assumed trusted by the paper. | **[CONFIRMED]** |

F1–F4 are already enough for a mid-eval on their own, because they are provable by reading, not by exploiting.

---

## 3. The idea catalogue

Effort assumes AI agents write the code. **The bottleneck is design and proofs, not typing.** Agents are unreliable at pairing math without test vectors — so every crypto idea below starts with "derive test vectors from LW11 Appendix D".

---

### **I1 — Give HMBAC's split decryption a real security definition**
- **Based on:** GHW11 (definitions), LW11 (scheme), Janus §4.3.5.
- **What:** Janus invented "system-side partial decryption to enforce a single point of access" and never defined what security it provides. Formalise it as an outsourced-decryption game in GHW11's style: define *enforcement soundness* (no PPT adversary without a valid system authorisation can produce a decryptable transform) and *transform privacy* (the KSSC learns nothing about the plaintext).
- **Major factors:** provable security, game-based reductions. No MPC, no PQC.
- **Novelty:** **High.** This is the intellectual spine. Nobody has defined the property Janus claims.
- **Effort:** Medium — mostly writing, little code.
- **Risk:** Requires the team to actually understand reduction proofs. This is the part an AI agent cannot do for you convincingly.

### **I2 — Capability-bound partial decryption (make the enforcement cryptographic)**
- **Based on:** F4/F5, GHW11 transform paradigm, standard signature schemes.
- **What:** KSSC performs a partial decryption **only** on presentation of a capability token — signed by the proxy chain, endorsed by ACSC — binding `(GID, data_ID, nonce, expiry)`. The Vault plugin verifies that signature itself. A direct Vault call with no blockchain transaction then fails *by construction*, not by ACL.
- **Major factors:** **digital signatures**, protocol design, **ROR proof** of the request/authorisation exchange, **ProVerif/Scyther** model. This is the component that satisfies the course's expected methodology.
- **Novelty:** **Medium-high** — it fixes a claim the original paper makes but does not deliver.
- **Effort:** Medium. Go signature verification in the plugin + chaincode changes + protocol write-up.
- **Bonus:** naturally restores "global source of truth", since no decryption can happen without a logged transaction.

### **I3 — Threshold gatekeeper key (the MPC contribution)**
- **Based on:** BMHADS (DKG + BLS threshold + PSS machinery), TMACS (threshold multi-authority prior art), LW11 (`K = g^α·H(GID)^y` is exponent-linear).
- **What:** Split `(α_D, y_D)` `t`-of-`n` across the domain's stakeholder organisations. Each peer computes a **decryption share** for the requester's GID; shares combine by Lagrange interpolation in the exponent. The gatekeeper key then never exists anywhere, so no single Vault compromise breaks the domain. Add PSS so shares refresh periodically without changing the public key. Optionally map the access structure onto **Fabric's endorsement policy**, which is already a t-of-n mechanism.
- **Major factors:** **MPC / threshold cryptography / DKG / proactive secret sharing.** Directly on-syllabus, and the natural fit for the instructor whose area this is.
- **Novelty:** **Medium.** The technique is standard; the *target* is new — BMHADS and TMACS threshold the **issuance** key to fix escrow, we threshold the **enforcement** key to fix bypass. The distinction must be stated explicitly or a reviewer will call it derivative.
- **Effort:** Medium-high. The math is clean (linear exponents), the engineering is the work.
- **Risk:** Do this properly or not at all — it will be read by someone who knows threshold crypto.

### **I4 — Verifiable partial decryption**
- **Based on:** GHW11 + **Lai et al., IEEE TIFS 2013** (needs downloading).
- **What:** Today the user cannot tell whether the KSSC transformed honestly. Add a checkability tag so a cheating or buggy KSSC is detected. Given F1, this is not hypothetical — a buggy KSSC *already exists*.
- **Major factors:** verifiable outsourced computation.
- **Novelty:** Low alone, good as a component. Pairs naturally with I1.
- **Effort:** Low.

### **I5 — Correctness and parameters: fix F1, re-parameterise for 128-bit**
- **Based on:** LW11 Appendix D as ground truth.
- **What:** Build LW11 test vectors, demonstrate F1 with a multi-attribute system policy, fix the accumulation, then move the curve from 160-bit `r` to ≥256-bit and re-benchmark the whole decryption path.
- **Major factors:** implementation correctness, benchmarking, parameter security.
- **Novelty:** **Low** (engineering) — but very high credibility, and it is the most demo-able thing you have.
- **Effort:** **Low.** Best effort-to-payoff ratio in the list. **Do this first.**

### **I6 — Post-quantum, tiered**
- **Based on:** would need PQFabric (arXiv 2010.06571) and Datta–Komargodski–Waters EUROCRYPT 2021 — **not yet downloaded**.
- **Tier 1:** hybrid ECDSA+Dilithium identities for Fabric CA/TLS across both chain layers; measure the cost. *Feasible.*
- **Tier 2:** Kyber KEM for the AES key-wrapping layer, ABE left classical. *Feasible-ish.*
- **Tier 3:** replace LW11 with lattice MA-ABE. **Not feasible** — no usable library, DNF-only policies.
- **Major factors:** **PQC**, hybrid certificates, KEM.
- **Novelty:** Medium for Tier 1 *in this architecture*; low as a standalone.
- **Verdict:** **Optional stretch goal, not the spine.** Take it only if I1–I3 land early.

### **I7 — Access-pattern privacy for the global log**
- **Based on:** Du et al. 2024 (states the problem), ZKP literature (zkCross 2024 etc.).
- **What:** the LSC log makes every request visible to every stakeholder — who asked for which record, when. Replace with a ZK commitment proving "an authorised user of authority X made an authorised request" and open it only via Janus's existing auditor-election mechanism.
- **Major factors:** **zero-knowledge proofs**, privacy, GDPR framing.
- **Novelty:** Medium.
- **Effort:** **High.** ZKP tooling plus Fabric chaincode integration is the biggest engineering item here.
- **Verdict:** attractive but I would not commit to it alongside I1–I3 in two months.

### **I8 — Malicious-stakeholder threat model + empirical audit**
- **Based on:** Janus §6 (their model), Du24 and BMHADS threat models for contrast.
- **What:** Janus's threat model covers compromised nodes and compromised users but **not an authorised-but-malicious stakeholder administrator** — which F5 suggests is the adversary that actually matters. Formalise it, then confirm/refute F5, F6, F7 on a running instance.
- **Major factors:** threat modelling, security analysis, responsible disclosure.
- **Novelty:** Medium — and it is the **enabler** that justifies every fix below it.
- **Effort:** Low-medium.
- **Verdict:** **This is the mid-eval.**

### **I9 — Attribute revocation**
- **Based on:** BMHADS (PRE-based periodic revocation).
- **Verdict:** **Skip.** BMHADS did it, and Janus deliberately chose certificate-based revocation. Cite, don't build.

### **I10 — IoMT device-side lightweight AKE**
- **Based on:** BMHADS's resource-constrained-sensor motivation; would need Das-style AKE papers (which you'd rather not extend).
- **Verdict:** **Don't take as a standalone direction** — crowded field, and it extends the base paper's *motivation* rather than Janus's *mechanism*. **But** harvest the AKE-wrapper idea into I2, because that is where your ROR proof comes from.

### **I11 — Aggregate/multi-signature for the stakeholder voting mechanism**
- **Based on:** BMHADS (BLS threshold signatures — same primitive family, so you get reuse), Janus PSC voting functions.
- **What:** Janus's governance has each stakeholder admin sign a ballot individually. Replace with an aggregate/multi-signature so one compact signature proves the majority. Measure the on-chain size and verification savings.
- **Major factors:** **aggregate & multi-signatures** — an explicit syllabus item.
- **Novelty:** Low, but cheap, self-contained, and it pairs with I3 (same BLS machinery).
- **Effort:** Low.
- **Verdict:** good secondary contribution; strong slide material.

### **I12 — Type-3 curve migration**
- **Based on:** LW11 Appendix D (which assumes a **symmetric** `e : G₀×G₀→G₁`), BMHADS (which argues for Type-3/BLS12-381 on size and speed grounds).
- **What:** moving Janus to an asymmetric Type-3 curve is **not** a parameter swap — the scheme must be re-derived for `e : G₁×G₂→G_T`, deciding which elements live in which group. That re-derivation is a small but genuine cryptographic contribution, with a large measurable efficiency win.
- **Major factors:** pairing-friendly curve selection, scheme adaptation, efficiency benchmarking.
- **Novelty:** Low-medium; excellent *evaluation* material.
- **Effort:** Medium-high.
- **Verdict:** a natural extension of I5 if time allows; also the cleanest answer to F2.

---

## 4. Recommended plan

### Spine for the 2 months
**I8 → I5 → I1 → I2 + I3 → I4 → I11**, written up as one coherent story:

> *Janus claims a cryptographically enforced single point of access. We show the claim is enforced by access-control configuration rather than cryptography, that the underlying transform is undefined and in one case incorrect, and that the gatekeeper key is a single point of compromise. We give the first formal definition of HMBAC-style enforced decryption, and a construction — capability-bound, threshold-distributed, and verifiable — that meets it, with comparable performance.*

That yields: a security-analysis contribution (I8, I5), a definitional contribution (I1), a construction contribution (I2, I3, I4), a syllabus-aligned secondary result (I11), the expected ROR + ProVerif + comparison tables, and MPC content for the instructor whose field that is.

**Stretch, in priority order if things go fast:** I12, then I6 Tier 1. **Deliberately dropped:** I7, I9, I10, I6 Tier 3.

### What is realistically achievable in 1.5 weeks (mid-eval)

Aim for **evidence + a design sketch**, not a working fix.

**Days 1–3 — get something running.**
- Stand up the ABE plugin standalone with `vault-secrets-abe-janus/other/docker/docker-compose.yml`. Do **not** attempt the full Kubernetes stack yet, and do **not** run `janus-repo/initialize.sh` on your own machine — it reboots the box partway through.
- Build LW11 test vectors from Appendix D. This is the single highest-value setup task: without them, an AI agent cannot tell a correct pairing computation from a wrong one.

**Days 4–7 — evidence.**
- Demonstrate **F1** with a two-attribute system sub-policy, against your test vectors. This is a confirmed spec deviation, so it should reproduce.
- Attempt **F5**: obtain a stakeholder-admin token and call `sysdecrypt/<org>/*` directly. Record whether it succeeds and whether anything is logged. **Either outcome is a result** — if it fails, you have characterised the real trust boundary, which is still a contribution.
- Probe **F6** by passing mismatched `subject` and `entity_id`.
- Benchmark the existing decryption path at the shipped 160-bit parameters to establish a baseline.

**Days 8–11 — write and present.**
- The malicious-stakeholder threat model (I8), contrasted with Janus §6, Du24 and BMHADS.
- Findings table: F1–F8 with status and evidence.
- Design sketch for I1/I2/I3 with the GHW11 framing and the Lagrange-in-the-exponent argument for I3.
- Slides: claim → evidence → proposed fix → 2-month plan.

**Honest expectation:** F1, F2, F3, F4 will hold up because they are verifiable by reading the spec and the code. F5, F6, F7 may not survive contact with a running system. Plan the presentation so it stands even if all three are refuted — the definitional gap (I1) and the escrow problem (F8) do not depend on them.

---

## 5. Still to download

1. **Lai, Deng, Guan & Weng**, "Attribute-Based Encryption With Verifiable Outsourced Decryption", IEEE TIFS 8(8), 2013 — needed for I4.
2. **TMACS** (Li et al., threshold multi-authority access control) — prior art for I3; cited by Du et al.
3. **Gennaro, Jarecki, Krawczyk & Rabin**, DKG, J. Cryptology 2007 — needed for I3.
4. **Herzberg et al.**, Proactive Secret Sharing, CRYPTO 1995 — needed for I3's refresh.
5. **Abdalla, Fouque & Pointcheval**, PKC 2005 — the ROR model you will cite in I2's proof.
6. Optional, only if you take I6: **PQFabric**, arXiv 2010.06571.

---

## 6. Risks to keep an eye on

- **The proofs are the real work.** I1 and I2 need reductions that you must be able to defend verbally. Budget time for that, not for code.
- **AI agents and pairing math.** Agents will produce plausible, wrong group-element code. Test vectors first, every time.
- **F5 may be a demo-config artifact.** The authors could reasonably say the shipped Vault policies are illustrative. Frame it as "the deployed configuration does not enforce the paper's claim", not "the design is broken", unless the design turns out to require it.
- **Responsible disclosure.** If F5 or F6 hold, notify the authors (Malamas, University of Piraeus) and CENSUS before presenting publicly. Doing this properly is itself worth showing in a security research course.
- **Don't let the scope grow.** I6, I7 and I12 are each individually tempting and each capable of consuming the whole two months.
</content>
