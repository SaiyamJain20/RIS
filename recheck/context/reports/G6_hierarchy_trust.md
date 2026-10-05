# G6 - Trust assumptions of the HIERARCHY itself (governance capture, cross-layer attestation, stale credentials)

Status: COMPLETE (see end). Date 2026-10-04. Agent G6.
Search channel: WebFetch against arXiv / Semantic Scholar / OpenAlex / Crossref APIs (WebSearch exhausted). OPENED = abstract or text read; SNIPPET = title/metadata only.

## 0. Anchors in the ORIGINAL paper (HMBC2020, verified in plain text by G6)
| Anchor | Quote / paraphrase (hmbc2020.txt line) | Problem it creates |
|---|---|---|
| A1 honest majority conflation | V-A1 (l.1131-1134): "for each Domain BC the majority of its stakeholders are honest. Since Domain BC stakeholders also operate PBC nodes, the same assumption holds for the PBC." | Per-domain majority does not imply PBC majority unless all stakeholders weigh equally AND domain sizes are fixed; conversely PBC majority says nothing about a small DBC. |
| A2 domain-local admission | V-B1 (l.1281-1285): "Within each domain, stakeholders can be added or removed (e.g. adding a new hospital), provided there is consensus among existing members of the particular domain, without engaging members of other domains. The same holds for the underlying services (Smart Contracts) within each DBC." Also III-D1b (l.731-735): add/remove needs "consensus of stakeholders in the corresponding domain (e.g. a sufficient number of signatures by CA-Admin...)" | Every admitted stakeholder also runs a PBC node (l.1047) -> a domain majority can mint PBC voters (Sybil/dilution) and rewrite its own ACSC/KSSC without other domains. |
| A3 inconsistent rule | V-B1 (l.1279-1281): new DOMAINS need "a majority of existing stakeholders ... majorityConsent"; V-A2 (l.1171-1173): changes "within each domain only if a majority of the relevant domain's stakeholders agree"; threshold "sufficient number" never quantified. | Spec ambiguity is itself a finding: the security of the hierarchy depends on an unspecified, layer-inconsistent quorum. |
| A4 detect-only | V-A5 (l.1259-1264): "it is not possible for a single domain of stakeholders to modify an access policy, without such changes being globally detected." | Detection only if the change transits the PBC; nothing forces a DBC policy-contract upgrade to be PBC-committed before it takes effect. No prevention, no bound on damage window. |
| A5 notary middleware | Sec. II (l.347-354): "our approach is closer to the Notary scheme [46], except that our model is fully autonomous: in Notary, a trusted individual or group is assumed." IV-A (l.1013-1046): one Inter-blockchain API in Docker 1 = "global, unique entry point", routes, throttles, buffers via an off-chain cache DB. | The API IS a single notary; the DBC acts on "verified attributes" (Fig. 6 step 4) with no proof; PBC learns DBC result only via the API/cache (Fig. 8). Integrity rests on Docker isolation (V-A1 first bullet). |
| A6 TOCTOU | III-D1c (l.741-751): TMSC validates cert/CRL/TempACL at the PBC; enforcement happens later at the DBC via a buffer (IV-B l.1069-1071 "buffer-like mechanism stores temporal data off-chain"). V-B3: tx can be finalised before block verification. | Revocation/TempACL expiry between PBC check and DBC use is not bounded. |

## 1. Candidates (sharpened)
- **C1 (main): Quantitative + adversarial analysis of capture in two-layer, type-partitioned permissioned hierarchies** (honest-majority conflation, domain capture, Sybil admission/vote dilution), with analytic bounds, a Monte-Carlo study over realistic domain-size/stake distributions, comparison with random committee sharding, and a mitigation (cross-layer admission quorum + per-domain PBC vote cap + PBC-committed timelocked policy upgrades) evaluated in the same simulator.
- **C2: Verifiable cross-layer attestation** - DBC accepts a request only with a PBC-quorum certificate (multi-/aggregate/BLS signature) bound to (req, GID, attrs, epoch, validity); PBC logs a result only with a DBC-quorum receipt; middleware untrusted for integrity, trusted only for liveness. (Must not threshold the gatekeeper key -> excl. zone 2.)
- **C3: Bounded stale-credential acceptance** across the two chains (validity window in the attestation; analysis of revocation latency vs queue/finality delays).

(sections 2+ appended below)

## 2a. Running log of queries and hits (appended during search)
| # | Channel / query | Useful hits |
|---|---|---|
| Q1 | arXiv: cross-chain AND (SoK OR survey) AND bridge | Zhang-Zhang-Barbee SoK bridges 2312.12573; Notland et al. SoK bridging design flaws 2403.00405; Lee et al. SoK bridge hacks 2210.16209; Belenkov et al. 2501.03423 (all permissionless asset bridges) |
| Q2 | arXiv: interoperability AND (SoK/permissioned/enterprise) | Abebe et al. 1911.01064 (Weaver precursor) - OPENED |
| Q3 | arXiv: consortium/permissioned AND governance/membership/reconfiguration | BMS 2109.03913 (OPENED); SocChain 2207.02711 (bribery, SNIPPET) |
| Q4-5 | arXiv + Crossref: hierarchical consensus subnets | De la Rocha et al. ICDCSW 2022 (OPENED via S2) |
| Q6 | arXiv: shard AND takeover/failure probability AND committee | Hafid et al. 2104.07215 (SNIPPET); Mozeika et al. 2303.14276 (SNIPPET) |
| Q7 | S2: hierarchical blockchain subchain compromise honest majority | nothing relevant (FEL multi-chain) |
| Q8 | arXiv: access control AND cross-chain/multi-chain/cross-domain | only engineering frameworks; none analyses malicious majority / capture (BlockA2A, relay-based 2510.14151, TrustCross TEE) |
| Q9 | Crossref title: cross-chain access control threshold signature notary (2020+) | notary-group + threshold-signature literature is LARGE: Bool Network (TIFS 2022), Fan & Yan JISA 2026, Xiong & Liu DCN 2022, Chen et al. Electronics 2023, Tian et al. 2025 "hierarchically managed notary group"; cross-chain AC: Si-Li-Su Comput. Commun. 2024 (OPENED), Ding-Zhang-Qin Sensors 2023 (OPENED), Belcaid & Zbakh Future Internet 2025 (SNIPPET), Zhang & Li 2026 threshold FHE cross-chain AC (SNIPPET) |
| Q10 | arXiv: blockchain AND (Sybil / governance attack / vote dilution) in titles | only permissionless: airdrop Sybils, DAO Sybils (DuPont 2311.17929), Rajab et al. 2002.06531 shard Sybil feasibility, Hafid et al. 2104.07215 (OPENED). NOTHING on permissioned/consortium member admission |
| Q11 | arXiv: Fabric AND (endorsement policy / channel config / MSP) AND (attack/collusion) | only PQFabric 2010.06571 - nothing on colluding-org governance |
| Q12 | Crossref: consortium blockchain member admission voting collusion governance security | DAO voting (Tamai & Kasahara Front. Blockchain 2024 whale/collusion; Bhaskar & Farshim CSF 2026 UC-secure L2 voting) - permissionless/token setting; nothing on consortium admission capture |
| Q13 | arXiv: Amiri hierarchical permissioned (Saguaro, Qanaat, SharPer) | org-/topology-partitioned permissioned systems, per-cluster fault assumptions; no capture analysis in abstracts (SNIPPET) |
| Q14 | arXiv: revocation latency / TOCTOU / stale credential + blockchain | only TxT 2301.08806 (Ethereum TOCTOU, unrelated); nothing cross-chain AC |
| Q15 | Crossref: hierarchical multi-blockchain access control cross-chain trust security analysis | ChainKeeper (IET Blockchain 2023, OPENED); Zhang & Gao 2023 relay-chain cross-chain authN for WSNs (SNIPPET); Georghiades & Kreder hierarchical longest-chain 2022 (SNIPPET) |
| Q16 | Fabric docs: policies (release-2.5) | OPENED: channel config updates governed by ImplicitMeta "MAJORITY Admins" (global-majority admission is the platform default) |
| Q17 | arXiv: GeoBFT / clustered / hierarchical BFT | ResilientDB 2002.00160, BunchBFT 2205.10658, Yahyaoui et al. 2504.21410 (SNIPPET): clusters by topology, no threshold-exceedance analysis in abstracts |
| Q18 | IACR ePrint 2019/1128 Zamyatin et al. SoK CCC | OPENED: "CCC is impossible without a trusted third party" |
| Q19-20 | arXiv multi-domain/sub-chain + collusion/capture/honest majority | nothing relevant |
| Q21 | arXiv ti:SoK AND ti:governance | Kiayias & Lazos SoK Blockchain Governance 2201.07188 (OPENED abstract: dimensions incl. "suffrage") |
| Q22-24 | Polkadot/ELVES (arXiv, ePrint x2) | not found - Polkadot random validator assignment NOT cited (unverified) |
| - | Semantic Scholar (4 attempts) and OpenAlex (1) | HTTP 429 every time - those channels not used; Crossref hit 429 once at the end |
Reused from agent C (OPENED by C): He et al. IPCCC 2022 nested blockchain with notary module; Jiang et al. Int. J. Netw. Manag. 2024 relay-chain MCF medical cross-chain; Silva et al. ERI-GO 2025 multi-blockchain survey; Wu et al. CMC 2026 multi-blockchain survey.

## 2b. Closest prior art per candidate
### C1 - capture analysis of type-partitioned two-layer permissioned AC hierarchies
| Work | Status | Overlap | What remains different |
|---|---|---|---|
| Hafid, Hafid, Samih, "A Tractable Probabilistic Approach to Analyze Sybil Attacks in Sharding-Based Blockchain Protocols", arXiv 2104.07215 (journal article), 2021 | OPENED | "compute the failure probability that at least one committee fails" - the analytic baseline we would compare to | Assumes RANDOM committee assignment and compute-based Sybils; no organisation-typed domains, no governance-driven admission, no access-control consequence |
| Rajab, Manshaei, Dakhilalian, "On the Feasibility of Sybil Attacks in Shard-Based Permissionless Blockchains", arXiv 2002.06531, 2020 | SNIPPET | Sybil committee members break a shard | Permissionless; Sybils from compute, not from a domain's own admission vote |
| De la Rocha, Kokoris-Kogias, Soares, Vukolic, "Hierarchical Consensus: A Horizontal Scaling Framework for Blockchains", ICDCSW 2022, doi:10.1109/ICDCSW56584.2022.00018 | OPENED | "Child subnets are firewalled from parent subnets ... benefit from the security of parent subnets by periodically checkpointing state" = the design pattern our mitigation would adapt (PBC-checkpointed DBC policy) | Asset/token setting; firewall bounds value, not policy/AC; no analysis of membership capture or vote dilution |
| Steinhoff, Stathakopoulou, Pavlovic, Vukolic, "BMS: Secure Decentralized Reconfiguration for Blockchain and BFT Systems", arXiv 2109.03913, 2021 | OPENED | Root membership service on a parent chain; "extensions of BMS to hierarchical deployments" | Threat = long-range / "I still work here" key reuse; not Sybil admission, not cross-layer vote dilution, no quantification |
| Kiayias, Lazos, "SoK: Blockchain Governance", arXiv 2201.07188, 2022/23 | OPENED (abstract) | Governance property "suffrage" (who may vote) - our attack is a suffrage-manipulation attack | Permissionless chains; no permissioned hierarchy or AC |
| Amiri et al.: Saguaro (2101.08819), Qanaat (2107.10836), SharPer (1910.00765); Gupta et al. ResilientDB/GeoBFT (2002.00160) | SNIPPET | Permissioned systems partitioned by enterprise / topology with per-cluster fault assumptions (closest structural analogue to DBCs) | No capture-probability or governance analysis visible in abstracts |
| Hyperledger Fabric docs, "Policies" (release-2.5) | OPENED | Channel config updates (incl. adding orgs) need ImplicitMeta "MAJORITY Admins" -> a global-majority admission quorum is a platform default | Shows the naive fix is standard practice -> our contribution must be the analysis + trade-off, not "use global quorum" |
| DAO voting: Tamai & Kasahara, Front. Blockchain 2024 (10.3389/fbloc.2024.1405516); Bhaskar & Farshim, CSF 2026 (10.1109/csf68417.2026.00029) | SNIPPET | Collusion / whale resistance; UC-secure governance voting | Token-weighted permissionless DAOs |
| Silva et al., ERI-GO 2025 (10.5753/erigo.2025.17034) (via agent C) | OPENED by C | Names "reliance on external trust rather than cryptographic consensus in multi-chain transactions" as an open gap; cites JANUS | Survey; motivates, does not solve |
Searches found NO work quantifying domain capture / Sybil admission / vote dilution in hierarchical or multi-chain PERMISSIONED access-control systems.

### C2 - verifiable cross-layer attestation (PBC-QC -> DBC, DBC-QC receipt -> PBC)
| Work | Status | Overlap | Different |
|---|---|---|---|
| Abebe et al. (IBM), "Enabling Enterprise Blockchain Interoperability with Trusted Data Transfer", Middleware'19 industry / arXiv 1911.01064 | OPENED | "a communication protocol that derives trust from the underlying network consensus protocol" - Fabric-to-Fabric data with source-endorser proofs = exactly the DBC-QC/PBC-QC idea (this became Hyperledger Weaver) | No AC semantics (GID/attributes/epoch), no log-before-grant |
| Xu, He, Dai, Zhang, "ChainKeeper: A cross-chain scheme for governing the chain by chain", IET Blockchain 3(4) 2023, doi:10.1049/blc2.12047 | OPENED | Supervisory chain over consortium chains; "verifiable identity threshold signature method ... to prevent the cheating behavior of malicious nodes" | Supervision data transfer, not access decisions; no freshness/revocation |
| Zamyatin et al., "SoK: Communication Across Distributed Ledgers", FC 2021 / ePrint 2019/1128 | OPENED | "CCC is impossible without a trusted third party" - formalises that the Inter-BC API is a TTP | General theory; framing only |
| Notary-group threshold-signature cross-chain: Bool Network (TIFS 2022, 10.1109/tifs.2022.3209546); Xiong & Liu (DCN 2022, 10.1016/j.dcan.2022.04.012); Fan & Yan (JISA 2026, 10.1016/j.jisa.2026.104419); Tian et al. "hierarchically managed notary group" (IJACSA 2025) | SNIPPET | Threshold-signed notary committees replacing a single notary - the mechanism of C2 | Asset transfer focus |
| Si, Li, Su, cross-chain AC with threshold Paillier, Comput. Commun. 2024, doi:10.1016/j.comcom.2024.05.012 | OPENED | "decryption shares from multiple relay nodes jointly decrypt results" for cross-chain ABAC | Attribute PRIVACY, not decision integrity/accountability |
| Ding, Zhang, Qin, "A Scalable Cross-Chain Access Control and Identity Authentication Scheme", Sensors 23(4) 2023, doi:10.3390/s23042000 | OPENED (abstract) | "ensure that all cross-chain operations are carried out by verified users ... record all operations with the help of Superchain" | No quorum-certified attestation, no freshness bound |
| Jiang et al., Int. J. Netw. Manag. 2024 (10.1002/nem.2279); He et al., IPCCC 2022 (10.1109/IPCCC55026.2022.9894312) (via C) | OPENED by C | Relay-chain / notary module for medical / IoT nested chains (both cite HMBC) | No trust-minimised notary analysis |

### C3 - bounded stale-credential acceptance
| Work | Status | Overlap | Different |
|---|---|---|---|
| Ivanov et al., TxT, arXiv 2301.08806, 2023 | SNIPPET | TOCTOU in Ethereum transactions | Single chain, not credentials |
| (none found) cross-chain revocation latency for AC | - | - | Classic PKI freshness literature (OCSP, short-lived certs) NOT searched (budget) - a reviewer will cite it |

## 3. Verdicts
| Cand. | Verdict | Confidence | Niche / reason |
|---|---|---|---|
| C1 | **NOVEL-NICHE** | Medium (S2/OpenAlex unavailable; Chinese-language and IEEE-only venues under-searched) | Niche = quantitative capture analysis of *type-partitioned, self-governing* sub-chains in a two-layer permissioned ACCESS-CONTROL hierarchy, where the attack amplifies from a small domain to global governance via domain-local admission (Sybil-by-governance, not Sybil-by-compute). Sharding analyses assume random assignment; hierarchical-consensus/BMS give the mitigation patterns but not the analysis. |
| C2 | **PARTIAL (mechanism DONE)** | Medium-High | Quorum-certified cross-network proofs (Weaver lineage), threshold-signed notary groups and supervisory threshold signatures (ChainKeeper) exist. Residual niche: two-way binding "DBC grant only with PBC-QC that already commits the log entry; PBC log finalised only with DBC-QC receipt". Also edges into exclusion zone 2 (a PBC-signed attestation consumed by KSSC is a capability token). Not a main contribution. |
| C3 | **NOVEL-NICHE but thin** | Low | Just a validity window/epoch in the attestation plus a latency analysis; fold in as one property of the C1 mitigation or a C2 model. |

Illustrative numbers (G6 back-of-envelope, Python stdlib, 28 orgs = 20 hospitals + 3 manufacturers + 3 insurers + 2 labs):
- Targeted adversary: capturing the smallest domain needs **1 org** under the JANUS quorum `Math.round(n/2)` (n=2 -> 1) and 2 under a strict majority. After that, the domain admits sham members (each a PBC voter): about N-2a = 24-26 shams reach the PBC quorum. **The minimum coalition depends on the smallest domain, not on N, so adding stakeholders never raises it.**
- Under random assignment into committees of the same sizes, a 2-org adversary captures some committee with probability <= 0.019 (union bound), and a 6-org adversary with probability <= 0.25.
- Random corruption (each org corrupt with probability p, independently), probability that some domain is captured: p=0.1 -> 0.23 (JANUS quorum) vs 0.065 (strict majority); p=0.2 -> 0.49 vs 0.23. At p=0.2, random assignment into equally tiny committees gives about 0.25.
- Lesson: tiny committees are weak with or without random assignment. **The hierarchy-specific risk is that a targeted adversary chooses its domain, combined with governance-driven amplification.** The mitigation should therefore be "cross-domain witnesses plus PBC-committed timelocked changes", not "random sharding", because data and policy are domain-owned by design.

## 1b. Recommended framing (C1 as core, C2/C3 shrunk into its mitigation)
"How many stakeholders does it take? Capture analysis of hierarchical multi-blockchain access control."
1. **System and adversary model**, drawn from HMBC2020 V-A1 / III-D1b / V-B1 / V-A5 (JANUS code is a second instance; optionally He et al. 2022 and Jiang et al. 2024 as third and fourth).
   - Separate *consensus* majority (PoS stake, 2020 IV-A) from *governance* majority (majorityConsent, one org one vote). The paper conflates both, and in two directions.
   - Adversary goals: G1 rewrite a DBC's ACSC/KSSC policy; G2 capture PBC governance (add or remove domains, change cross-domain policy, open the global log to a crony "Auditor"); G3 mint emergency access by TempACL; G4 suppress detection.
   - Adversary moves: corrupt orgs, admit shams (domain-local), remove honest members, and time actions inside JANUS's 30-min election windows.
2. **Analytic results**: the minimum coalition t*(rule, goal) for each rule set (2020-text-A domain majority, 2020-text-B global majority, JANUS code), the weakest-domain theorem, and the Sybil amplification bound s >= N - 2a. Also the damage window of "detect-only" (V-A5): records exposed before detection = access rate x (detection + response delay).
3. **Monte-Carlo study**:
   - Domain-size and stake distributions: JANUS demo 2+2, a regional e-health mix, Zipf.
   - Corruption models: random p, budgeted targeted adversary, correlated corporate groups.
   - Baselines: random committee sampling (Hafid-style), the 2020 text rules, JANUS rules.
4. **Mitigations, evaluated for capture probability AND autonomy/liveness cost**:
   - M1: dual-quorum admission (domain majority AND a PBC supermajority).
   - M2: per-domain vote cap or weighting in the PBC.
   - M3: a DBC policy upgrade (ACSC/KSSC) takes effect only with a PBC-quorum certificate plus a timelock delta and an objection window. This turns "detectable" into "preventable within delta". Multi-signature here; ECDSA k-of-n or BLS.
   - M4: k cross-domain witnesses, sampled at random from other domains, co-sign governance-critical DBC actions (this is the hypergeometric benefit of sharding, without moving data).
   - The central result is the trade-off frontier between autonomy and capture resistance. V-B1 sells "without engaging members of other domains" as a feature.
5. (Optional, from C2/C3) A Tamarin/ProVerif model of the PBC->DBC request: the DBC accepts only if the PBC logged the request and the credential was valid at some time >= accept - delta. Keep it to correspondence and freshness lemmas. No gatekeeper-key thresholding and no capability-token redesign (exclusion zone 2).

## 4. PoC feasibility (3 laptops)
| Item | Stack | Effort | Pitfalls |
|---|---|---|---|
| Analytic and Monte-Carlo simulator | Python 3 + numpy/scipy (or stdlib), 10^5-10^6 trials (seconds, single core) | 1-1.5 pw | Realistic domain sizes need a cited source (e.g. a national hospital or manufacturer register); keep stake and vote models separate |
| Governance model check | TLA+/TLC (Java, < 1 GB) or Alloy, or a Python BFS over governance states for N <= 10 | 1 pw | Bound the state space (N <= 8, <= 3 shams) to stay laptop-safe |
| Contract PoC (attack + mitigation) | 2 x Anvil (Foundry) or Hardhat nodes = PBC and DBC; Solidity governance (JANUS rules ported) + M1-M3; Python web3.py relayer as the untrusted Inter-BC API; ECDSA k-of-n `ecrecover` (BLS via EIP-2537 only if the Anvil hardfork supports it) | 1.5-2 pw | Anvil has no real PoS, so measure gas and latency only and claim no consensus security; do not reimplement Fabric |
| (Opt.) Tamarin/ProVerif freshness model | ProVerif 2.x | 0.5-1 pw | Stay away from token-bound decryption |
| **Total** | about 4-5.5 person-weeks, i.e. about 2 calendar weeks for 3 students | | No Docker or K8s needed |

## 5. Evaluation plan
- **Security argument**:
  - A game-based "governance-capture game" (the adversary wins if a goal-changing transaction executes).
  - Theorems: weakest-domain bound; amplification bound; the mitigated rule's minimum coalition under M1+M2; under M3, a detection-to-prevention guarantee if at least one honest org objects within delta.
  - Bounded model checking for exhaustive small-N confirmation and to find non-obvious traces (remove-then-admit, domain-add cascade).
- **Simulation metrics**:
  - P[capture domain]; P[capture PBC governance]; t* as a fraction of N; expected exposed records before detection.
  - Governance latency and liveness-failure probability (an honest domain blocked by caps or vetoes) under M1-M4.
  - Gas per admission or upgrade; added end-to-end latency of the attested path.
- **Baselines**: HMBC2020 text rules (two readings), JANUS code rules, random committee sampling, Fabric MAJORITY Admins.

## 6. Syllabus fit
Blockchain security and privacy (core). Digital-signature variants: multi-, threshold and aggregate signatures for the M3/M4 certificates (a component, NOT the contribution, because aggregate-signature voting is excluded). Key management or access control in hierarchical settings (adjacent). Moderate overall; weaker than crypto-protocol directions for an instructor who wants ROR proofs.

## 7. Kill criteria and reviewer objections
- **Kill criteria**:
  - K1: a 2020-26 paper quantifying sub-chain capture or Sybil admission in a hierarchical permissioned AC system. Not found here, but re-run when S2/OpenAlex quotas reset, with these queries: "hierarchical blockchain" + "malicious stakeholders" + "domain"; "multi-chain consortium governance Sybil"; "cross-domain access control blockchain collusion of domains"; and the forward-citation list of HMBC and JANUS.
  - K2: the Monte-Carlo study adds nothing beyond t* = q(n_min). Then drop the simulation and go formal-only.
  - K3: the Malamas/Kotzanikolaou group has published a governance or BFT follow-up. Agent C found none.
- **Reviewer objections, with planned responses**:
  - "Obvious; just require a global vote." Respond with the autonomy/liveness cost frontier and the M3/M4 designs; Fabric's default shows the naive fix is known.
  - "Sham stakeholders are legal entities, so expensive." Respond with HMBC's own no-global-root-CA design: a stakeholder is its own CA, admitted by its own domain. Treat sham cost as a parameter c_sham.
  - "Analysis of a toy design." Generalise to a class (HMBC, JANUS, nested and relay-chain medical designs), and show that the 2020 spec is internally inconsistent.
  - "No real PoS." Separate governance votes from consensus; the PoC measures cost only.
  - C2 alone would be rejected as "Weaver / threshold notary applied to your system".

## 8. Scores (1-10)
| | Novelty | Feasibility | Security depth | Syllabus fit | Workshop fit |
|---|---|---|---|---|---|
| C1 alone | 6 | 9 | 5 | 5 | 5 |
| C1 + M3/M4 mitigation (+ small freshness lemma) | 6 | 8 | 7 | 6 | 7 |
| C2 alone | 3 | 7 | 6 | 7 | 3 |
| C3 alone | 4 | 8 | 4 | 5 | 3 |
**Is C1 alone enough for a workshop?** Borderline. The analysis alone reads as "critique of someone else's rules". It becomes a credible workshop paper with: (a) a general model covering at least 2 instantiations, (b) the weakest-domain and amplification theorems plus model-checked traces, and (c) at least one non-trivial mitigation (M3 timelocked PBC-certified upgrades and/or M4 cross-domain witnesses) evaluated on both capture and autonomy cost. It is also a good secondary section for a GC1/GC3-based paper.

## 9. References (status)
OPENED: Abebe et al. 2019 arXiv 1911.01064; Steinhoff et al. 2021 arXiv 2109.03913; De la Rocha et al. ICDCSW 2022 doi:10.1109/ICDCSW56584.2022.00018 (abstract via S2 API); Hafid et al. arXiv 2104.07215; Zamyatin et al. FC 2021 / ePrint 2019/1128; Kiayias & Lazos arXiv 2201.07188; Xu et al. ChainKeeper IET Blockchain 2023 doi:10.1049/blc2.12047 (abstract via Crossref); Si, Li, Su Comput. Commun. 2024 doi:10.1016/j.comcom.2024.05.012 (abstract via OpenAlex); Ding, Zhang, Qin Sensors 2023 doi:10.3390/s23042000 (abstract via OpenAlex); Hyperledger Fabric docs "Policies" release-2.5; HMBC2020 and A1 report (local).
OPENED by agent C (reused): He et al. IPCCC 2022 10.1109/IPCCC55026.2022.9894312; Jiang et al. IJNM 2024 10.1002/nem.2279; Silva et al. ERI-GO 2025 10.5753/erigo.2025.17034; Wu et al. CMC 2026 10.32604/cmc.2026.077332.
SNIPPET (search-result level only): Zhang, Zhang, Barbee SoK bridges arXiv 2312.12573; Notland et al. arXiv 2403.00405; Lee et al. arXiv 2210.16209; Belenkov et al. arXiv 2501.03423; Rajab et al. arXiv 2002.06531; Mozeika et al. arXiv 2303.14276; Amiri et al. Saguaro 2101.08819 / Qanaat 2107.10836 / SharPer 1910.00765; Gupta et al. ResilientDB 2002.00160; Alqahtani & Demirbas BunchBFT 2205.10658; Yahyaoui et al. 2504.21410; Bool Network TIFS 2022 10.1109/tifs.2022.3209546; Xiong & Liu DCN 2022 10.1016/j.dcan.2022.04.012; Fan & Yan JISA 2026 10.1016/j.jisa.2026.104419; Tian et al. IJACSA 2025 10.14569/ijacsa.2025.0160450; Belcaid & Zbakh Future Internet 2025 10.3390/fi17040149; Zhang & Li 2026 10.1007/978-981-95-7027-0_9; Tamai & Kasahara 2024 10.3389/fbloc.2024.1405516; Bhaskar & Farshim CSF 2026 10.1109/csf68417.2026.00029; Ivanov et al. TxT 2301.08806; Moradi et al. 2510.14151.
NOT VERIFIED (not cited as evidence): OmniLedger, RapidChain, Elastico, Polkadot/ELVES, IBC spec, Hyperledger Cactus - known by name only; the sharding baseline should cite Hafid et al. or be re-grounded.

Status: COMPLETE (about 34 fetches; Semantic Scholar and OpenAlex rate-limited throughout).
Back-of-envelope script: reports/G6_calc.py (Python stdlib, <1 s).
