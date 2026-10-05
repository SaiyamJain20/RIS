# Verification report: `problems.md` and `PROPOSAL_REVISED.md`

**Date:** 20 September 2026
**Method:** each factual and bibliographic claim checked against a primary source (publisher page, DBLP, author-hosted PDF, official platform documentation) or against a local PDF/source file. Mathematical identities re-derived by hand. Where a claim could not be checked, it is marked **unverified** rather than accepted.

---

## 1. Verdict on `problems.md`

**It is substantively correct on every point I could check, and it caught two real errors of mine.** Detail below.

| # | Critique | Verdict | Evidence |
|---|---|---|---|
| 1 | "First formal definition" overclaimed; mediated/server-aided ABE already formalizes mandatory online participation | **Correct — my error** | Ibraimi, Petkovic, Nikova, Hartel & Jonker, *Mediated Ciphertext-Policy Attribute-Based Encryption and Its Application*, WISA 2009, LNCS 5932, pp. 309–323, DOI `10.1007/978-3-642-10838-9_23`. Divides decryption between a mediator and the user. Reinforced by Yang, Cui & Jing, *Generic Constructions of Server-Aided Revocable ABE with Verifiable Transformation*, ACNS 2023 Workshops, LNCS 13907, DOI `10.1007/978-3-031-41181-6_25` |
| 2 | Threshold gatekeeper not broadly novel | **Correct — my error** | TMACS (Li, Xue, Xue & Hong, *IEEE TPDS* 27(5), 2016) shares the **master key** `(t,n)`; a user obtains their secret key by interacting with any `t` authorities. Threshold transformation on a ledger also exists: *A Threshold Proxy Re-Encryption Scheme for Secure IoT Data Sharing Based on Blockchain*, **Electronics** 10(19):2359, 2021 |
| 3 | Verifiable outsourced decryption not novel | **Correct** | Lai et al., *IEEE TIFS* 8(8), 2013; plus the 2023 server-aided verifiable transformation work above |
| 4 | Missing close recent literature | **Correct, and the most consequential point** | My original review surfaced outsourced ABE but never surfaced **mediated / server-aided ABE at all** — the exact prior-art family for "decryption requires an online party". That omission is what produced critiques 1–3 |
| 5 | BMHADS comparison inaccurate | **Correct — my error, and worse than stated** | See §3 below. Verified directly from the PDF |
| 6 | `Sign_proxy` reintroduces a central compromise point | **Correct** | Design critique; a single proxy signing key would be a new single point of forgery inside a system whose stated goal is removing such points |
| 7 | Capability replay | **Correct** | My original token had `nonce` and `expiry` but no single-use state and no ciphertext binding, so one capability could authorise repeated transforms |
| 8 | S3 verification underspecified | **Correct** | "Use Chaum–Pedersen" was hand-waving; two independent secrets `(α_i, y_i)` across two groups need an explicit multi-witness relation |
| 9 | 160→256 migration oversimplified | **Correct** | LW11 Appendix D is a **symmetric** pairing `e : G₀×G₀→G₁`; BLS12-381 is Type-3. Re-instantiation, not reconfiguration |
| 10 | ROR proof largely irrelevant | **Technically correct — but see caveat N3** | There is no new key-exchange protocol, so the ROR model has nothing to bind to |
| 11 | Scope too large | **Correct in diagnosis; see N2 — the revision does not actually fix it** | |
| 12 | Core story diluted | **Correct** | |

---

## 2. What I verified as correct in `PROPOSAL_REVISED.md`

### 2.1 Bibliography — all checked, all accurate

| Reference | Status |
|---|---|
| BMHADS: **Hao Yuan, Guofang Dong, Leilei Zhao**, *PLoS One* **21(5):e0349767**, published **27 May 2026** | ✅ exact match to the PDF front matter |
| TMACS: W. Li, K. Xue, Y. Xue, J. Hong, *IEEE TPDS* 27(5), 2016 | ✅ |
| Ibraimi et al., WISA 2009, LNCS 5932, pp. 309–323 | ✅ |
| Yang, Cui & Jing, ACNS 2023 Workshops, DOI `10.1007/978-3-031-41181-6_25` | ✅ |
| Threshold PRE, *Electronics* 10(19):2359, 2021 | ✅ |
| Du et al., *Comput. Electr. Eng.* 119:109547, 2024 | ✅ |

### 2.2 Hyperledger Fabric claims — both load-bearing assertions are correct

- **"`txID` … is known when its proposal is constructed."** ✅ The transaction ID is the hash over the concatenation of nonce and creator; `CreateChaincodeProposal` returns the proposal *and* its transaction ID. Known before submission.
- **"Endorsement alone is insufficient: simulation can succeed while the transaction is never submitted or later becomes invalid."** ✅ Fabric's official transaction-flow documentation states that at commit, transactions are validated "to ensure endorsement policy is fulfilled and to ensure that there have been no changes to ledger state for read set variables since the read set was generated," and are then "tagged as being valid or invalid." The revision's insistence on an independent valid-commit check is therefore justified, not paranoia.

### 2.3 The S3 mathematics — I re-derived every identity; all correct

- `T_{i,x} = B_x^{a_i}·D_x^{b_i} = e(g,C₂ₓ)^{a_i}·e(H_G(GID),C₂ₓ)^{b_i} = e(g^{a_i}·H_G(GID)^{b_i}, C₂ₓ)` ✅ by bilinearity
- `∏_{i∈I} T_{i,x}^{L_i} = e(g^{α_D}·H_G(GID)^{y_D}, C₂ₓ) = e(K_{D,GID}, C₂ₓ)` ✅
- `L_i = ∏_{j≠i}(−j)/(i−j)` is Lagrange interpolation at 0 ✅
- Feldman commitments: `A_i = ∏_k V_{α,k}^{i^k} = E^{f_α(i)} = E^{a_i}`, `Y_i = g^{b_i}` ✅, and `V_{α,0}=E^{α_D}`, `V_{y,0}=g^{y_D}` coincide with LW11's public key ✅
- Sigma protocol: `E^{z_a}=R_A·A_i^c` ✅, `g^{z_b}=R_Y·Y_i^c` ✅, `B_x^{z_a}·D_x^{z_b}=R_T·T_{i,x}^c` ✅. Reusing `u` across `R_A` and `R_T` is what proves the *same* `a_i` in both statements — correct.
- **Committing `f_α` in the target group (`E^{coeff}`) rather than the source group is a deliberate and correct choice**: LW11 publishes `e(g,g)^{α_D}` but never `g^{α_D}`, and the revision's instruction not to publish `g^{α_D}` preserves that. This is the most careful thing in the document.
- Threshold relations: `q > f` for authorization soundness, `n − f ≥ t` for liveness ✅
- Splitting the row product between system and user rows is sound: `Σ_x c_x A_x = (1,0,…,0)` holds over the full selected set, so neither half need reconstruct it alone ✅ — the revision states this explicitly and is right to

### 2.4 BMHADS characterisation — now accurate

The revision's description ("DKG and threshold BLS for collaborative data-source authentication; separate multi-authority ABE/key-fragment mechanisms") matches the paper. See §3 for the sharper statement it should make.

---

## 3. Correcting the BMHADS comparison properly (verified from the PDF)

`problems.md` #5 is right, and the true picture is more useful than either document states:

- **Contribution (1)** is "a collaborative authentication mechanism that integrates blockchain-based DKG with BLS threshold signatures… uses auxiliary nodes for collaborative verification… ensures data authenticity," with PSS for periodic key updates. The DKG/BLS/PSS machinery serves **authentication of data sources among auxiliary nodes**.
- **Contribution (2)**, separately, fixes escrow "by having multiple authorities independently issue key fragments and aggregate them to generate the user's private key."
- The security section is explicit about the shape of (2): "complete decryption capability can be achieved only through the product of components from **all N** independent authorities," and the scheme "is designed to withstand attacks by up to **N−1** corrupted authorities."

**So BMHADS's escrow resistance is all-N cumulative, not a `(t,n)` threshold.** My original proposal called it a "threshold issuance key" — wrong on both words. The final report should draw the three-way contrast cleanly, because a reviewer will otherwise assume all three are the same mechanism:

| Scheme | Secret distributed | Structure | Purpose |
|---|---|---|---|
| TMACS | attribute-authority **master key** | `(t,n)` threshold | escrow / single-point bottleneck at **issuance** |
| BMHADS | user private key **components** | **all-N** cumulative product | escrow at **issuance**; separately, DKG+BLS+PSS for **data-source authentication** |
| Cerberus | Janus's mandatory **domain enforcement secret** | `(t,n)` threshold | bypass + single-point compromise at **each transform** |

One more thing worth knowing: **Du et al. 2024 and BMHADS 2026 share a co-author** (Guofang Dong, Yunnan Minzu University). They are one research line, not two independent data points about the state of the art.

---

## 4. Problems neither document catches

### N1 — Still-missing prior art that Janus itself cites
**Guo, Meamari & Shen, *Multi-Authority Attribute-Based Access Control with Smart Contract*, ICBCT 2019** (arXiv `1903.07009`; ACM DOI `10.1145/3320154.3320164`). Data users present attributes to attribute authorities and, after validation, **obtain attribute tokens via Ethereum smart contracts**.

This is the closest "smart contract gates an ABE capability" prior art, and **Janus cites it as its own reference [20]**. Omitting it from a related-work section whose entire job is to defend the novelty claim is exactly the failure mode `problems.md` #4 identified — the revision fixed the mediated-ABE gap but left this one. Add it, and distinguish clearly: Guo et al. gate the **issuance** of attribute tokens once; Cerberus gates **each individual transform** against a committed, single-use authorization record.

### N2 — Scope was rebalanced, not reduced
`problems.md` #11 said cut scope. The revision cuts PSS, aggregate signatures, ROR and curve migration — but **adds**: concrete DKG selection with complaint/disqualification handling and analysis; a two-witness Fiat–Shamir protocol with concurrent-use and malformed-input analysis; a cross-chain consumption state machine with durable atomic release records, idempotent retry and crash recovery; a related-ciphertext derivation analysis; and ProVerif modelling of persistent state.

§4.2 step 5 alone — atomically persisting a release record per `(capID, stakeholderID)` with exactly-once logical consumption and idempotent delivery across crashes — is a serious distributed-systems task independent of the cryptography. **Net effort is plausibly higher than the original, in the same eight weeks.**

*Recommendation:* declare a **minimum viable core** that must land — S5 correctness fix, S2 single-use authorization with real Fabric evidence, and S3 threshold transform **with a trusted-dealer setup as the declared fallback** if DKG integration does not converge. A trusted-dealer threshold still demonstrates the enforcement property; it just weakens the setup assumption, and saying so honestly costs nothing.

### N3 — Dropping ROR may collide with what the instructors expect
`problems.md` #10 is technically right: no new AKE means the ROR model has nothing to bind to. But you confirmed the course expects the ROR + formal-verification + comparison-table methodology, and Prof. Das's line of work uses it consistently. Being technically right and meeting the assessment criteria are different things.

*Recommendation:* keep ProVerif for the authorization-correspondence property, and **state in the proposal why ROR does not apply** — that reasoning demonstrates more understanding than a bolted-on proof would. Then raise it with the instructors **before** the mid-eval rather than discovering the mismatch at the final. If an ROR-style result is genuinely required, N4 below creates a legitimate place for one.

### N4 — A cheap fix for the "critical limitation" the revision honestly flags
§4.3 concedes that `T_{i,x}` is a deterministic function of `(K_{D,GID}, C₂ₓ)`, so once released it can be copied; the capability binds the proof transcript, not the algebraic value. That is unavoidable in the current shape — but the **passive-harvesting path is closable almost for free**:

> Have the requester include an ephemeral public key `g^u` in the authorized request, covered by `capID`. Each share holder returns its `T_{i,x}` encrypted under that ephemeral key, and **the requester acts as combiner**. Raw pairing values then never transit a combiner or the network in the clear, and only the authorized requester can assemble them.

This does not stop an authorized requester from retaining what it learned — the revision already scopes retention out, correctly — but it removes third-party harvesting and combiner compromise from the attack surface. It also gives you a genuine session-key element, should you want an ROR-style argument for N3.

### N5 — Readability has swung too far
The original overclaimed; the revision overhedges. Nearly every sentence in §4 carries a caveat, which makes the actual plan hard to extract on a first read. Hedging belongs in §10 (claims) and §11 (risks) — both of which are excellent. Add a half-page plain-language box at the top: *what we will build, what we will prove, what we will measure.* An instructor reading cold should be able to answer those three questions in ninety seconds.

---

## 5. Bottom line

`problems.md` is a good critique and it was right to demote the novelty claims; two of its twelve points identify outright errors in my original proposal, and the rest are sound. `PROPOSAL_REVISED.md` fixes them, and everything I could check in it — bibliography, Fabric semantics, and the full S3 derivation — is correct. The scheme mathematics in particular is careful, notably the choice to commit `f_α` in the target group so that `g^{α_D}` is never exposed.

Four things remain: add Guo/Meamari/Shen; declare a minimum viable core because scope was rebalanced rather than cut; settle the ROR question with the instructors before mid-eval; and consider the ephemeral-key share delivery in N4. None of these is structural — the proposal is sound.
</content>

---

## 6. Soundness review — a concrete attack on the central claim

**Added 20 September 2026, after the verification pass above.** Derived by hand; **must be confirmed numerically against the PBC implementation before being reported as a finding.** The algebra is elementary, so my confidence is high, but it has not been executed.

### 6.1 The attack

The transform output is homomorphic in the ciphertext component:

```text
T_x = e(K_{D,GID}, C₂ₓ) = e(K_{D,GID}, g^{r_x}) = e(K_{D,GID}, g)^{r_x}
```

An adversary who knows `r_x` recovers a per-GID master value with one exponentiation:

```text
e(K_{D,GID}, g) = T_x^{(r_x)^{-1} mod p}
```

From then on, for **any** ciphertext whose randomness `r'` the adversary knows:

```text
T' = e(K_{D,GID}, g)^{r'} = e(K_{D,GID}, g^{r'})
```

— computed offline, with **no further authorization, no transform request, and no ledger record**.

### 6.2 Why this is reachable in HMBAC

In Janus, **stakeholders encrypt and store their own data**. A stakeholder administrator is therefore routinely an encryptor who *chooses* `r_x`. The attack needs only:

1. Encrypt a record with known randomness and store it in one's own database.
2. Request it through the system **once, legitimately and with a full audit record**.
3. Invert the exponent to obtain `e(K_{D,GID}, g)`.

Every input is available: `C₁ₓ, C₂ₓ, C₃ₓ` come from the adversary's own database, `H_G(GID)` is a public hash, and the LSSS coefficients `cₓ` are derived from the public policy.

### 6.3 CORRECTION (same day): the practical impact is much smaller than first stated

My first write-up of this said the attack "defeats Janus's P1 and P2" and was a practical break. **That overstates it.** On re-examination:

The only ciphertexts the recovered master value unlocks are those whose randomness `r'` the adversary knows — in practice, **ciphertexts the adversary encrypted themselves**. But an encryptor already knows their own plaintext, so unlocking the domain gate for it gains them nothing they did not already have.

For someone else's ciphertext, `r'` is unknown and recovering it from `C₂ₓ = g^{r'}` is a discrete log. Computing `e(K,g)^{r'}` from `e(K,g)` and `g^{r'}` requires mapping back from the target group, which no pairing provides. So the interesting case — a user at hospital A bypassing the gate on hospital B's records — remains blocked.

**So this is a flaw in the security *claim*, not a practical exploit.** Its real significance:

- **The claim as literally stated is false.** An adversary wins the §4.1 enforcement-soundness game as written. The definition must therefore carry an explicit precondition. This is a genuine and useful finding — it shapes S1 — but it is definitional, not operational.
- **It caps the strength of the achievable theorem**, and forces the new hardness assumption in §6.4 to be stated rather than inherited.
- **It becomes a real attack if `r_x` is predictable.** That makes "audit the RNG used for encryption randomness in the Janus encrypt path" a concrete audit task with actual teeth, and a much better use of week 1 than I previously suggested.

It should be reported as a definitional gap plus an RNG-dependent conditional attack — not as a break of the deployed system.

### 6.3b Why the obvious fixes do not work

- **Blinded delivery (N4), or any user-removable blinding.** Useless here: the adversary *is* the authorized party, so whatever blinding the legitimate user strips, the attacker strips.
- **Returning `Q_x` instead of `T_x`.** `T_x` is recoverable from `Q_x` using only public values.
- **Making the domain key ciphertext-specific**, e.g. hashing `H_G(GID‖τ)` for the system row. **I checked this and it breaks the scheme.** LW11's final combination cancels the `e(H,g)^{ωₓ}` terms only because `Σₓ cₓ ωₓ = 0` *with the same* `H` *across every row*. Using a different hash input for the system row leaves `e(H₁,g)^{Σ_sys cω}·e(H₂,g)^{Σ_user cω}`, and those exponents are not individually zero. Using `H_G(GID‖τ)` for *all* rows would require reissuing every user attribute key per ciphertext.
- **An outer ElGamal/KEM layer under a domain key.** Worse: the encryptor can compute `h^{k'}` directly from the public key, so it offers no protection against a data owner at all.

The underlying reason all of these fail is simple and worth stating in the report: **you cannot stop a data owner from reading data they encrypted.** That is inherent, not a defect.

### 6.3c Residual effect on deployed Janus

`sys_decrypt_path.go` returns `SysDecrypted = EggS`, from which `e(K_{D,GID}, C₂ₓ)` is recoverable using only public values. So:

> **A single legitimate, authorized, logged access lets a user who knows the ciphertext randomness bypass the domain gate for all subsequent self-encrypted records under that GID, permanently and silently.**

This defeats Janus's P1 and P2 **without any Vault compromise and without any ACL misconfiguration** — it is independent of hypothesis F5. It is a mathematical property of the construction, not of the deployment.

Two consequences:

- **The "break" half of the project gets substantially stronger**, and this finding is *far more tractable to demonstrate in week 1* than the F5 ACL hypothesis: it is arithmetic over data the tester already controls, needing no privilege escalation.
- **The "fix" half must handle it**, and the N4 ephemeral-key delivery does **not**: the authorized requester still legitimately obtains `T_x` and can still invert it. N4 closes third-party harvesting only.

### 6.4 What the defensible claim looks like

Fixes that do not work:
- Returning `Q_x` instead of `T_x` — `T_x` is recoverable from `Q_x` via public values.
- Binding the domain key to the ciphertext — the LW11 decryption identity requires the `H_G(GID)` inside `K` to match the `e(H_G(GID), C₃ₓ)` term, so the hash input cannot be changed unilaterally.
- Blinded delivery (N4) — the authorized requester ends up with the true value regardless.

The realistic path is to **narrow the property**: enforcement is claimed only for ciphertexts whose encryption randomness is **not known to the adversary** — i.e. records encrypted by an honest data owner. This still covers the scenario that motivates HMBAC (a user at hospital A seeking hospital B's records, where B chose the randomness), but it must be stated as an explicit precondition, and it rests on a new hardness assumption roughly of the form:

> given `g`, `g^{r'}` and `h = e(K,g)`, computing `h^{r'}` is hard without knowledge of `K` or `r'`.

That assumption is **not** among LW11's. It must be named, related to standard co-CDH/BDH-style assumptions, and justified — it cannot be inherited.

### 6.5 Two further soundness obligations

- **DKG choice is not cosmetic.** Pedersen's DKG does not produce a uniformly distributed key — Gennaro, Jarecki, Krawczyk and Rabin demonstrated the biasing attack, which is why GJKR exists. Picking "Pedersen/GJKR" informally, as the earlier draft did, is a real soundness risk rather than a citation detail.
- **Publishing new elements invalidates the inherited proof.** LW11's prime-order variant is proven in the generic group model. Adding `A_i = E^{a_i}`, `Y_i = g^{b_i}`, sigma-protocol transcripts and released transform values introduces group elements the original argument never considered. The GGM argument must be **redone over the extended element set**, not cited. This is probably the single largest piece of unscoped theoretical work in the proposal.
