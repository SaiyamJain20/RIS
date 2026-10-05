# Literature Review & Extension Analysis — HMBAC / Janus

**Status:** Draft v1, pending answers to the open questions in §9.
**Date:** 2026-09-17
**Scope:** Base paper (IEEE Access 2020) + Janus (Appl. Sci. 2023) + surrounding literature, aimed at identifying an unexplored extension direction that fits the *Research in Information Security* syllabus.

> **Citation warning.** Every reference below was found either (a) inside the reference lists of the two assigned papers, or (b) through web search during this review. Titles/venues taken from search engines have **not** been opened and verified page-by-page. Before any of this goes into a report, each citation must be pulled and checked. Items marked **[V]** were verified directly (paper text or source code read).

---

## 1. What the two assigned papers actually do

### 1.1 Base paper — Malamas, Kotzanikolaou, Dasaklis, Burmester, *"A Hierarchical Multi Blockchain for Fine Grained Access to Medical Data"*, IEEE Access 8 (2020) 134393–134412 **[V]**

- **Architecture:** two-layer blockchain. A **Proxy Blockchain** at the top lets independently-managed trust authorities interoperate (single access point, single source of truth). One or more **Domain Blockchains** below let each domain (hospitals, device manufacturers, insurers) enforce its own policy.
- **Crypto:** CP-ABE, with the decryption process *split* between the end user and the system, plus a credential revocation mechanism.
- **Smart contracts:** TMSC (trust management), RSC (registration), PSC (proxy) on the proxy chain; ACSC (access control), KSSC (key store) on the domain chains.
- **Extras:** "tailored forensics" — granular, domain-scoped auditing by design.
- **Weakness the authors themselves concede:** proof-of-concept only, no end-to-end implementation, so practicality was unproven.
- **Uptake:** ~46 citing works (OpenAlex/Semantic Scholar), mostly surveys and adjacent healthcare-blockchain designs, not direct extensions.

### 1.2 Janus — Malamas, Palaiologos, Kotzanikolaou, Burmester, Glynos, *"Janus: Hierarchical Multi-Blockchain-Based Access Control (HMBAC) for Multi-Authority and Multi-Domain Environments"*, Applied Sciences 13(1):566, 2022/2023 **[V]**

This is the direct successor by (mostly) the same group. Four contributions:

1. **HMBAC, a formal access-control model** (§4.1 of the paper): sets `U, Au, S, K, D` (users, authorities, subjects, keys, domains), attribute functions, and three gate functions — **AVF** (attribute verification, on the proxy chain), **AF** (authorization against inter-/cross-domain policy, on the domain chain), **DF** (partial decryption, on the domain chain). Modelled after the Servos–Osborn style of formalising ABAC element relations.
2. **An architecture** — Frontend Layer / Hierarchical Blockchain Infrastructure / Data Layer, with data held **off-chain** in each stakeholder's own DB, ABE-encrypted.
3. **A real implementation ("Janus")** — Hyperledger Fabric, **Raft** consensus, five JavaScript chaincodes (PSC/TMSC/LSC on proxy; ACSC/KSSC per domain), Kubernetes pods, RabbitMQ queues, Electron+React client, Hyperledger Fabric CA per stakeholder, **HashiCorp Vault** with a custom **Go ABE plugin**.
4. **The core cryptographic trick — enforced single point of access.** Data `d_i` is AES-encrypted under `k_i`; `k_i` is MA-CP-ABE encrypted under a policy that has an *extra AND clause requiring the domain's own attribute key*. The **KSSC** is the only holder of the domain secret key `SK_D`; it generates `K_{U,domain} = KeyGen(GID_U, GP, domain, SK_D)` **on the fly, bound to the requesting user's GID**, and performs a *partial* decryption. The user finishes decryption with their own attribute keys. Consequence: stealing the ciphertext from the database is useless — you cannot decrypt outside the system, even with a full set of valid attribute keys.
5. **Governance:** an on-chain voting/election mechanism (`majorityConsentInit`, `majorityClientVote`, `updateElection`) for adding/removing domains and stakeholders, changing cross-domain policy, and granting auditors access to logs.

- **Underlying MA-ABE:** Lewko–Waters, *Decentralizing Attribute-Based Encryption*, EUROCRYPT 2011 (ref [7] in Janus). Rouselakis–Waters FC 2015 is cited as related but not used.
- **Explicit future work (paper §7):** (i) different consensus mechanisms for **Byzantine** tolerance; (ii) user credential management is outside the system and inefficient management degrades overall efficiency.
- **Uptake: only 8 citations** (OpenAlex W4313391751). **Nobody has published a direct extension of Janus.** That is the good news for this project — the space is genuinely open — and the bad news — there is no follow-on work to lean on.

---

## 2. Artifact reality check (what the code actually says)

Both repos were cloned and read. This section is the most useful part of the review, because several findings are *not* in the papers and give us defensible, concrete contributions.

Repos: `github.com/CENSUS/Janus` → `./janus-repo/`, and `github.com/CENSUS/vault-secrets-abe-janus` → `./vault-secrets-abe-janus/` (BSD-2-clause, so we are free to fork and modify).

| Finding | Evidence | Why it matters |
|---|---|---|
| **The ABE core uses a Type A pairing at ~80-bit classical security.** `q` is a 512-bit prime, `r` (group order) is **160-bit**: `730750818665451621361119245571504901405976559617`. | `vault-secrets-abe-janus/plugin/init_path.go:11-19` **[V]** | 80-bit security has been deprecated since ~2013 (NIST SP 800-57). This is a *classical* weakness, before we even mention quantum. Re-parameterising and re-benchmarking is a concrete, low-risk contribution. |
| **Symmetric (Type A, supersingular) pairing**, i.e. G1 = G2, via Ben Lynn's PBC library (`github.com/Nik-U/pbc`). | `go.mod`, `plugin/*.go` **[V]** | Type A is the slowest and largest option; asymmetric BN/BLS12-381 curves would be smaller and faster. But moving curve type changes the scheme's algebra — not a free swap. |
| **The policy engine is an access *tree* with Shamir shares (AND = 2-of-2, OR = 1-of-2), not an LSSS matrix.** | `plugin/policy_parser.go:225-295` (`compute_shares`, `genshares`, `Pfunc`) **[V]** | The paper states policies are "in the form of a matrix" (LSSS), as Lewko–Waters requires. The implementation is Bethencourt–Sahai–Waters-style. Trees are convertible to LSSS, so this is probably not a break — but **the implemented scheme is not literally the proven scheme**, and nobody has checked. A careful re-derivation is a legitimate paper section. |
| **No Byzantine tolerance.** Fabric with Raft = crash-fault-tolerant only. The paper admits this. | Janus §6.2 **[V]** | Hyperledger **Fabric 3.0 (Sept 2024) now ships SmartBFT**, a BFT ordering service. So Janus's "future work #1" has become an *upgrade*, not research. Useful as a supporting engineering step, **not** as the project's novelty. |
| **`SK_D` (domain secret key) lives in a single Vault instance per domain.** Vault, Kubernetes and the pods are *assumed trusted*. | Janus §6 assumptions + `configs/vault/` **[V]** | This is the single strongest trust assumption in the whole design, and the authors state it plainly. Compromise one Vault → forge the domain attribute key for *any* GID → the "single point of access" guarantee collapses for that domain. **This is the most attackable gap.** |
| Revocation is by **attribute-certificate revocation lists**, explicitly chosen "instead of applying costly attribute key revocation techniques". | Janus §4.3.4 (TMSC) **[V]** | So there is no attribute-level ABE revocation, no forward/backward secrecy on attribute keys. A revoked user who kept their attribute keys is stopped only by the system refusing them entry. |
| Client is an **Electron desktop app**. | `blockchain/client/` **[V]** | There is no story at all for the medical IoT devices that the base paper's motivation is built around. Devices cannot run PBC pairings. |
| Every request is logged by **LSC on the proxy chain**, replicated to all stakeholders. | Janus §4.3.4 **[V]** | Global verifiability is the selling point, but it means every stakeholder sees *which user asked for which `data_ID` and when*. In healthcare that metadata is itself sensitive (GDPR). No privacy-preserving auditing. |
| Access is by `data_ID`. | `database_api/api/dbc_api/src/*` **[V]** | You must already know the identifier. No search over encrypted data. |
| Security analysis is **informal**. | Janus §6 **[V]** | No game-based proof of the *modified* two-step decryption scheme, no ProVerif/AVISPA/Scyther model, no ROR proof for the authentication. For this course, that is both a gap and an opportunity. |
| **The shipped stakeholder-admin Vault policy grants `create`/`update` on `sysdecrypt/<org>/*`.** | `janus-repo/configs/vault/policies/attikon-hospital-admin.hcl` **[V]** | A stakeholder *administrator* token appears able to call the system-decryption endpoint directly, bypassing PSC/TMSC/ACSC **and the LSC log**. The paper's two headline claims are precisely "cannot be bypassed by users **or authorities**" and "global source of truth". **Needs empirical confirmation — this is hypothesis from config + code, not a demonstrated exploit.** |
| The plugin **trusts its caller entirely**: `cryptogram`, `sub_policy`, `subject` and `entity_id` are all caller-supplied, with no signature, freshness or well-formedness check. | `plugin/sys_decrypt_path.go:60-75` **[V]** | The single-point-of-access property is enforced by **Vault ACLs, not by cryptography**, although the paper frames it as a cryptographic guarantee. Also a partial-decryption oracle on chosen ciphertexts for anyone who reaches the endpoint. |
| **GID decoupling:** the collusion-binding hash uses the caller's `subject` parameter, while stored attribute keys are loaded from a *separate* `entity_id` parameter. | `sys_decrypt_path.go:60,90-93` **[V]** | LW11's collusion resistance rests on *one* `H(GID)` binding every key component. Two independent caller-controlled identifiers is exactly the mixing that binding exists to prevent. Worth a focused look. |
| **Probable implementation bug:** in the pruned-attribute loop, `EggS` is *assigned* (`Set(div).ThenPowBig(...)`), not multiplied into an accumulator, so only the last attribute contributes. | `sys_decrypt_path.go:~155` **[V]** | Fine for the intended single-system-attribute policy; silently wrong for any multi-attribute system sub-policy. |
| `constructSystemAttribute` computes `g^{α_i}·H(GID)^{y_i}`. | `sys_decrypt_path.go:~180` **[V]** | Confirms the scheme really is Lewko–Waters 2011, so LW11 is the right thing to study and to prove against. |

---

## 3. Gap analysis — and whether the literature already closed each gap

| # | Gap in Janus | Already solved elsewhere? | Still open *for HMBAC*? |
|---|---|---|---|
| G1 | Pairing-based → quantum-broken; and only 80-bit classically | Lattice MA-ABE exists in theory; PQ healthcare ABAC schemes exist (2025) | **Partly open** — nobody has done it for a hierarchical multi-blockchain with enforced single point of access |
| G2 | Domain key `SK_D` in one trusted Vault | Threshold/DKG MA-ABE exists in isolated schemes | **Open** — strongest gap; directly contradicts Janus's own "no globally trusted authority" claim |
| G3 | Raft, no BFT | Fabric 3.0 SmartBFT (2024) | **Closed** — engineering only |
| G4 | No attribute-level revocation / no forward-backward secrecy | Large revocation literature (2016–2025) | Partly open; low novelty alone |
| G5 | No traceability of leaked attribute keys | MA-CP-ABE with accountability (Li et al. 2018; Liu et al. 2024) | Open for HMBAC, moderate novelty |
| G6 | Policies are public | Hidden-policy ABE exists | Open; a 2023 ABE survey explicitly states **no hidden-policy scheme also provides accountability + hierarchical/multi-authority features** |
| G7 | Access logs leak who-accessed-what | ZKP auditing (zkCross 2024, etc.) | **Open and attractive** |
| G8 | Partial decryption by KSSC is unverified by the user | Verifiable outsourced decryption (Green et al. 2011; Lai et al. 2013) | **Open for HMBAC** — cheap to add, easy to prove, nice small contribution |
| G9 | No IoT/IoMT device support | Fog/edge-outsourced ABE (MACFI 2022 etc.) | Open |
| G10 | No search over encrypted data | ABSE / multi-keyword ABE search (2022–2026) | Open, but large |
| G11 | No formal proof / formal verification | Standard methodology in this course's field | **Open** — and expected by this kind of course |
| G12 | Perfect audit trail, no misuse detection | IDS/ML-on-logs literature (2024–2025) | **Open for HMBAC** |
| G13 | Governance voting = one ECDSA signature per stakeholder | Multi-sig / aggregate signature / BLS | Open, small, but maps *exactly* onto the syllabus |

---

## 4. Literature clusters — what exists, and what we can reuse

### Cluster A — MA-ABE foundations (the crypto we would be modifying)
- Chase, *Multi-authority ABE*, TCC 2007 — needs a trusted central authority.
- Chase & Chow, *Improving privacy and security in multi-authority ABE*, CCS 2009 — removes the central authority, hides GID (relevant to G6/G7).
- **Lewko & Waters, *Decentralizing ABE*, EUROCRYPT 2011** — the scheme Janus actually builds on. Any crypto change starts here.
- Rouselakis & Waters, *Efficient statically-secure large-universe MA-ABE*, FC 2015 — prime-order, more efficient; a plausible drop-in upgrade.
- Bethencourt, Sahai & Waters, CP-ABE, S&P 2007 — the access-tree structure the Janus code actually implements.
- **Verdict: usable, and necessary background.** Read Lewko–Waters properly before touching anything.

### Cluster B — Post-quantum ABE
- **Datta, Komargodski & Waters, *Decentralized Multi-Authority ABE for DNFs from LWE*, EUROCRYPT 2021** — first MA-ABE from LWE alone; policies limited to **DNF formulas**.
- Waters, Wee & Wu, *Multi-authority ABE from lattices without random oracles*, TCC 2022.
- Datta–Komargodski–Waters, MA-ABE for NC¹ from BDH, J. Cryptology 2023.
- Lattice-ABE reviews and 2025–2026 lattice ABE+revocation papers (Springer *Discover Computing*; *Electronics* 15(11):2471).
- PQ blockchain plumbing: **PQFabric** (arXiv 2010.06571) — Fabric with hybrid classical/PQ X.509 certificates; CRYSTALS-Dilithium/Kyber are NIST standards.
- **Verdict: theory usable, implementation *not*.** There is no production-grade lattice MA-ABE library. Charm and PBC do not have it; OpenFHE does not ship MA-ABE. Building one in a semester is unrealistic. A **scoped** version is realistic — see Direction A in §5.

### Cluster C — Threshold / MPC / distributed key generation
- Gennaro, Jarecki, Krawczyk & Rabin, *Secure DKG for discrete-log based cryptosystems* — the classic.
- NIST **Multi-Party Threshold Cryptography** project (CSRC) — good framing citation.
- BLS threshold signatures + proactive secret sharing for periodic key refresh.
- 2026 IoMT scheme (PLOS One / PMC13215620) using blockchain-based DKG + BLS threshold signatures, with authorities issuing key *fragments* that are aggregated — "fundamentally alleviating the key escrow problem", resisting collusion of up to *t−1* authorities.
- **Verdict: highly usable, and the single best-aligned cluster.** Maps to the syllabus MPC item, and attacks Janus's own admitted weakest assumption.

### Cluster D — Outsourced / verifiable decryption
- Green, Hohenberger & Waters, *Outsourcing the decryption of ABE ciphertexts*, USENIX Security 2011.
- Lai, Deng, Guan & Weng, *ABE with verifiable outsourced decryption*, IEEE TIFS 2013.
- Fog-outsourced MA-ABE: MACFI (*J. Syst. Archit.* 2022), Zhang & Zhou (*Comput. Netw.* 2021) — both already cited by Janus.
- **Verdict: directly usable.** Janus's KSSC *is* an outsourced-decryption server that the user must blindly trust. Adding verifiability is a clean, provable, small delta.

### Cluster E — Privacy-preserving auditing / ZKP
- zkCross (IACR ePrint 2024/888) — cross-chain privacy-preserving auditing.
- ZKP for anonymous patient authentication on public/private blockchains (ScienceDirect 2025).
- Self-sovereign identity + blockchain for non-repudiation with patient anonymity.
- **Verdict: usable but heavier.** ZKP tooling (Circom/snarkjs, gnark for Go) is workable, but integrating with Fabric chaincode is real effort.

### Cluster F — Accountability, traceability, hidden policy, revocation
- Li, Chen, Chow, Huang, Wong & Liu, *Multi-authority fine-grained access control with accountability*, JNCA 2018 (already cited by Janus).
- *Traceable and revocable MA-ABE supporting decryption outsourcing and policy update*, Front. Comput. Sci. 2025.
- *Blockchain-aided anonymous traceable and revocable access control with dynamic policy updating for cloud IoT*, IEEE IoT-J 2024.
- BA-RMKABSE (*FGCS* 2022) — ranked multi-keyword ABSE **with hiding policy** for smart health.
- 2023 ABE survey (*J. Surveill. Secur. Saf.*): explicitly states there is **no scheme combining hidden-policy/policy-update with accountability *and* hierarchical/multi-authority features**. That sentence is a ready-made motivation paragraph.
- **Verdict: usable; G6+G5 combined is a defensible novelty claim backed by a survey's own statement.**

### Cluster G — AI/ML on access logs, intrusion detection
- *Anomaly-based threat detection in smart health using ML*, BMC Med. Inform. Decis. Mak. 2024.
- *AI-Driven Zero-Trust Models for Blockchain-Supported Healthcare Ecosystems*, ACM 2025.
- *Smart Contract-Based Validation of Intrusion Detection Systems in Blockchain Networks*, Springer 2025.
- *An optimized blockchain framework with ML-based anomaly detection for distributed access control in IoT networks*, Discover Computing 2026.
- **Verdict: usable, and cheap.** Janus produces a perfect, immutable, structured access log and then does nothing with it. Isolation Forest / LOF / sequence models over the LSC log is low-risk work. Maps to two syllabus items (intrusion detection; AI/ML security). **Caveat: on its own this is applied-ML, not security research — it needs a cryptographic co-contribution to be a strong project.**

### Cluster H — Directly adjacent systems (the "2-3 coinciding papers" you asked for)
These are the closest neighbours to Janus and the best candidates to build on:
1. **Banerjee, Bera, Das, Chattopadhyay, Khan & Rodrigues, *Private blockchain-envisioned multi-authority CP-ABE-based user access control scheme in IIoT*, Computer Communications 169 (2021) 99–113.** Janus cites this as ref [37] and compares against it in Table 1. Indian authorship, same problem class, and it uses the formal-proof + comparative-table methodology this course expects. **Strongest single candidate to pair with Janus.**
2. **Du et al., *Blockchain-based and multi-authority hierarchical access control data sharing scheme*, Computers & Electrical Engineering 2024 (DOI 10.1016/j.compeleceng.2024.109547).** Same title space as HMBAC, published after Janus, 12 citations. Must read — it is the nearest competitor and will tell us what is already taken.
3. **BMHADS — *A blockchain-based multi-authority hierarchical attribute encrypted data sharing scheme in the IoMT*, PLOS One 2026.** Explicitly targets hierarchical MA-CP-ABE, single-point-of-failure risk and key escrow — i.e. our G2. Read carefully to check it does not pre-empt Direction B.
4. *Hierarchical Blockchain-Based Multi-Chaincode Access Control for Securing IoT Systems*, Electronics 11(5):711, 2022 (52 citations) — the most-cited hierarchical-chaincode alternative.
5. *Collusion resistant multi-authority access control scheme with privacy protection for personal health records*, JKSU-CIS 2023.

---

## 5. Candidate extension directions

Ranked by my assessment of (novelty × feasibility × syllabus fit).

> **v2 update (after the code audit and the BMHADS check).** Direction A below is now demoted, because BMHADS (PLOS One 2026) and BDAE (*Wuhan Univ. J. Nat. Sci.* 2024) already apply DKG / (n,t) Pedersen VSS to multi-authority ABE key *issuance* on Fabric. The recommended project is now **Direction F — break-and-fix**, which subsumes the useful half of A while giving us a contribution that is unambiguously ours.

### **Direction F — Security analysis of HMBAC, and a cryptographically-enforced fix ("HMBAC⁺")** ⭐⭐ *recommended*
**Part 1 — the break.** Janus's threat model (§6) covers compromised nodes and compromised users, but **not a malicious-but-authorised stakeholder administrator**. The audit findings in §2 suggest that gap is real: `sysdecrypt` is reachable by an admin token, the plugin authenticates nothing about its caller's input, and the identity binding is split across two caller-controlled parameters. Formalise the missing adversary, then confirm each finding empirically.
**Part 2 — the fix.** Move enforcement from ACLs into the cryptography:
- **Capability-bound partial decryption.** KSSC decrypts only when presented with a proxy-chain-signed, ACSC-endorsed capability naming `(GID, data_ID, nonce, expiry)`, verified *inside* the Vault plugin. A direct Vault call with no blockchain transaction then fails by construction, restoring "cannot be bypassed by authorities" and closing the unlogged path.
- **Threshold domain key.** Split `SK_D` `t`-of-`n` across the domain's stakeholders, with decryption *shares* combined so the enforcement key never exists anywhere. Distinguished from BMHADS/BDAE: they threshold the **issuance** key to fix escrow; we threshold the **gatekeeper** key to fix bypass. Map the access structure onto Fabric's endorsement policy.
- **Close the oracle:** bind `subject ≡ entity_id`, verify ciphertext well-formedness, have the data owner sign ciphertexts at insertion.
- **Prove it:** ROR proof of the authorisation/request protocol, ProVerif or Scyther model, comparative computation/communication/security-feature tables against Janus, BMHADS, BDAE and Banerjee–Bera–Das.
**Syllabus fit:** MPC ✓, blockchain security & privacy ✓, key management in hierarchical access control ✓, digital signatures ✓.
**Why the novelty holds:** break-and-fix on a named, deployed, artifact-backed system is novel by construction, and the fix is a design contribution rather than a patch.
**Risk:** Part 1 must be empirically confirmed before anything is claimed in writing.

### **Direction A — Threshold/MPC-based domain authority: removing Janus's last trusted party** *(now folded into F)*
**Idea.** Replace the single Vault-held `SK_D` with a `(t,n)` secret-shared domain key distributed across the domain's stakeholder organisations. The KSSC's partial decryption becomes a **threshold protocol**: `t` of `n` domain peers each compute a decryption share bound to the requester's GID, and the shares combine on-chain. Add proactive refresh so shares rotate without changing the public key.
**Why it is novel here.** Janus §6 *states* that Vault and the pods are trusted. This removes exactly that assumption while preserving the enforced-single-point-of-access property — which is Janus's headline contribution. No published work does this for a hierarchical multi-blockchain.
**Reuses:** Cluster C (DKG, BLS threshold, PSS), Cluster A (Lewko–Waters key structure).
**Syllabus fit:** MPC ✓, key management in hierarchical access control ✓, blockchain security ✓.
**Effort:** modify `sys_keygen_path.go` / `sys_decrypt_path.go` in the Go plugin + KSSC chaincode. Medium-high, but well-bounded.
**Risk:** need to check BMHADS (PLOS One 2026) has not already done the equivalent.

### **Direction B — Verifiable + accountable partial decryption** ⭐ *recommended as a companion to A*
**Idea.** Today the user cannot tell whether the KSSC decrypted honestly, and a user who leaks attribute keys cannot be traced. Add (i) **verifiable outsourced decryption** (Green/Lai-style checksum) so the client detects a malicious or buggy KSSC, and (ii) **white-box traceability** so a leaked key can be attributed to a GID.
**Reuses:** Cluster D + Cluster F.
**Syllabus fit:** blockchain security & privacy ✓, digital signatures ✓.
**Effort:** low-medium. This is the highest contribution-per-hour option and pairs naturally with A into one coherent paper.

### **Direction C — Privacy-preserving global auditing + ML misuse detection**
**Idea.** Split the LSC log: keep a ZKP-backed commitment on the proxy chain that proves "some authorised user of authority X made an authorised request" without revealing *who* or *which record*, while each domain retains the cleartext log locally and runs anomaly detection (Isolation Forest / sequence models) to flag insider misuse; flagged events get opened on-chain via the existing voting mechanism (auditor election already exists in Janus!).
**Why it is nice.** It uses Janus's *existing* auditor-election machinery as the "open the envelope" step, which is elegant.
**Reuses:** Cluster E + Cluster G.
**Syllabus fit:** blockchain privacy ✓, intrusion detection ✓, AI/ML security ✓.
**Risk:** ZKP + Fabric integration is the highest-effort engineering in this list; the ML half needs a dataset we would have to synthesise from Janus's benchmark harness.

### **Direction D — Post-quantum hardening (scoped)**
**Idea.** Three tiers, pick by ambition:
- *Tier 1 (safe):* migrate Fabric CA/TLS identities to hybrid ECDSA+Dilithium à la PQFabric, keep ABE classical, and **measure the cost** across the multi-blockchain. Honest framing: "harvest-now-decrypt-later resistance for the control plane."
- *Tier 2:* replace the AES key-wrapping layer with a Kyber KEM, keep MA-ABE for policy.
- *Tier 3 (research-grade, probably too big):* replace MA-ABE with lattice MA-ABE (Datta–Komargodski–Waters, DNF-only).
**Syllabus fit:** PQC ✓✓ (explicit syllabus item).
**Risk:** Tier 3 is not feasible in a course timeline. Tier 1 alone may read as "we swapped certificates" unless combined with A or B. Also, hybrid quantum-safe ABAC for smart healthcare **already exists** (ACM *DLT: Research and Practice*, DOI 10.1145/3827623, 2025) — we would need to differentiate on the hierarchical/multi-domain angle.

### **Direction E — IoMT edge extension**
**Idea.** Extend HMBAC downward to constrained medical devices: a lightweight device↔gateway authentication and key-agreement protocol (ECC/hash based), ABE decryption outsourced to the gateway, device attestation attributes issued by the manufacturer domain. Prove the AKE in the Real-Or-Random model, verify in ProVerif/Scyther, and give computation/communication cost tables.
**Syllabus fit:** key management/authentication/access control in WSN-IoT ✓✓, digital signatures ✓.
**Why consider it:** this is the *exact* template of the Banerjee–Bera–Das line of work, so if the course expects that methodology, this is the safest possible choice.
**Risk:** lowest novelty relative to the crowded IoMT-auth literature; it extends the *motivation* of the base paper more than the *mechanism* of Janus.

### Cross-cutting "free" contributions worth bundling into whichever direction we pick
- Re-parameterise the ABE plugin from 80-bit Type A to ≥128-bit, re-benchmark, report the real cost. **[V — this is a genuine finding from the code, not speculation]**
- Reconcile the implemented access-*tree* with the paper's claimed LSSS matrix. **[V]**
- Upgrade Raft → SmartBFT (Fabric 3.0) and measure — closes the authors' own stated future work #1.
- Replace per-stakeholder voting signatures with an aggregate/multi-signature (syllabus item; compresses the governance transactions).
- Formal verification of the access-control logic (ProVerif/Scyther/Tamarin) — no one has done it for HMBAC.

---

## 6. What we should *not* try

| Not this | Why |
|---|---|
| Implementing lattice MA-ABE from scratch | No usable library; DKW21 supports DNF only; a semester is not enough |
| Rewriting the whole Janus stack in another framework | ~350 JS files + Go plugin + K8s; reimplementation burns the entire timeline |
| "Add BFT consensus" as the main contribution | Fabric 3.0 already ships SmartBFT — this is now configuration |
| A pure survey | The course expects an extension; surveys of blockchain healthcare access control are already saturated (several 2024–2026 ones found) |
| ML anomaly detection alone | Applied ML, not security research, unless paired with a crypto contribution |
| Full-scale benchmark reproduction without hardware | Janus runs ~15–20 Kubernetes pods; needs serious RAM |

---

## 7. Practical notes on the artifacts

- `janus-repo/` — 346 JS files (chaincodes + React client), 83 Python (database API), Kubernetes templates, Dockerfiles. BSD-2-clause.
- `vault-secrets-abe-janus/` — the crypto. 13 Go files under `plugin/`. This is where a cryptographic contribution lands: `init_path.go` (global setup), `authority_setup_path.go`, `keygen_path.go`, `sys_keygen_path.go`, `sys_decrypt_path.go`, `full_decrypt_path.go`, `encrypt_path.go`, `policy_parser.go`.
- Setup requires **both** repos side by side, plus Kubernetes, Docker, Go, and a build of the PBC C library (`libraries/pbc.tar.gz`). `initialize.sh` reboots the machine during install — **do not run it on your main working machine without reading it first**.
- Both clones currently sit inside `/home/saiyamjain/Desktop/RIS/Project/`, which is inside your home-level git repo. You may want to gitignore them or move them.

---

## 8. Suggested reading order (before we commit to a direction)

1. Janus paper §4 and §6 again, closely — the model and the security assumptions.
2. Lewko & Waters, EUROCRYPT 2011 — the scheme everything rests on.
3. Du et al., *Comput. Electr. Eng.* 2024 — the nearest competitor published after Janus.
4. Banerjee, Bera, Das et al., *Comput. Commun.* 2021 — methodology template + Janus's own comparison baseline.
5. BMHADS, PLOS One 2026 — checks whether Direction A is already taken.
6. Green–Hohenberger–Waters 2011 + Lai et al. 2013 — if we take Direction B.
7. Datta–Komargodski–Waters, EUROCRYPT 2021 — only if we take Direction D Tier 3.

---

## 9. Open questions (see chat)

Answers to these change which direction is right, so they are blocking on the *choice*, not on the review itself.
</content>
</invoke>
