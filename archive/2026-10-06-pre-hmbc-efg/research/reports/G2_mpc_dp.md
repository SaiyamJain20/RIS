# G2 - Policy-governed MPC + DP for cross-domain STATISTICAL access in HMBC2020

Agent G2, 2026-10-04. Status: COMPLETE - see FINAL REPORT below the evidence log.

## 0. Grounding in the original paper (verified by grep of papers/text/hmbc2020.txt)

Statistical access is a stated, but completely unmechanised, use case of [HMBC2020]:
- Sec. I (line ~57): data types include "health, administrative, technical, statistical (research) or insurance data".
- Sec. I-A requirements (line ~143): "hospitals may allow doctors from other hospitals to have access to statistical medical data".
- Sec. III-C6 / Fig. 3 (line ~640): user A "in hospital Y ... has access only to statistical data, by using the certified role 'Researcher'" - i.e. the ONLY mechanism is an ABE attribute 'Researcher' that decrypts *records*; nothing computes or limits a statistic.
- Sec. III-F (line ~924, ~952): "insurance companies may allow access to statistical data to other insurance companies"; "Allow insurance companies to access statistical hospital treatment data. Since all access is controlled and logged by the PBC, the insurance companies and the hospitals will be able to prove that the privacy of personal health records is preserved." -> the paper equates privacy of statistical release with *logging*. No aggregation, anonymisation, DP, or MPC anywhere (grep for 'anonym', 'aggregat', 'differential', 'multiparty' = 0 hits in the HMBC text).
- JANUS (Sec. 1, Example 1, line ~120): "a doctor in a hospital may also be a researcher at a university. This doctor would also require access to (statistical) health data maintained in all hospitals, for research purposes." Sec. 2 (line ~530): "A cross-domain policy for the hospital domain may be to allow access to anonymized data to researchers". JANUS too has NO statistical/anonymisation mechanism (grep: 0 hits for differential/multiparty/MPC) - so this direction is outside Exclusion Zone 1.

=> Seed gap (h) is CONFIRMED as a textual gap in both papers.

## 0b. Method note (honesty)
The session's WebSearch quota was already exhausted (200/200) when G2 started, so grounding used (a) full texts already on disk in the scratchpad from an earlier run (Drynx, PriCollabAnalysis, Cerebro, Big Bird - read with grep), (b) direct queries to scholarly APIs (arXiv, Semantic Scholar, OpenAlex, Crossref) via tiny urllib scripts, and (c) WebFetch of abstracts. Coverage of Google-Scholar-only / paywalled venues is therefore weaker than intended; treat "not found" as "not found in arXiv/S2/OpenAlex/Crossref".

## Early prior-art findings (OPENED = full text read on disk)
- PriCollabAnalysis (Tawfik et al., Cluster Computing 28:191, 2025, doi:10.1007/s10586-024-04928-z) OPENED: Hyperledger Fabric + secret sharing + SMPC + Paillier for "researchers to conduct collaborative statistical analysis on health records" across hospitals; requester identity "verified at one of the participating hospitals". NO differential privacy, NO budget, NO attribute/multi-authority policy, single channel (no hierarchy). => blockchain-coordinated MPC statistics for hospitals per se is DONE.
- Drynx (Froelicher, Troncoso-Pastoriza, Sousa, Hubaux; IEEE TIFS 2020; arXiv:1902.03785) OPENED: decentralized statistical queries/ML over hospital data, HE + ZKP + DP, "noise can be verified to be from a specific distribution ... and no entity knows which noise value is added", proofs stored in a "proof blockchain" (skipchain) for auditors. "Authentication and authorization are out of scope of this paper". No cumulative budget accounting. => candidate (iii) verifiable noise + blockchain audit is largely DONE by Drynx.
- Cerebro (Zheng, Deng, Chen, Popa, Panda, Stoica; USENIX Security 2021) OPENED: MPC platform with user-defined "compute policies ... release policies such that the result of a computation is only revealed if the policy conditions are satisfied" + cryptographic auditing; DP mentioned as an implementable release policy. No identity/attribute authorisation, no cross-query budget.
- Big Bird (Tholoniat, Caulfield, ..., Geambasu, Lecuyer, Thomson; SOSP 2026; arXiv:2506.05290; doi:10.1145/3830418.3843897) OPENED: shows per-querier DP enforcement "is unsound ... under cross-querier data adaptivity" and proposes a GLOBAL budget "enforced jointly across all domains", with the main obstacle being "denial-of-service depletion of a shared global budget by Sybil web domains". Web-advertising/on-device setting, not data-holder federations. => the core insight of candidate (ii) (global cross-querier budget + Sybil problem) is published at a top venue; our version must differ in setting and mechanism.
- Zhao, Zhao, Kang, Zhang, Niyato, Shi, "A Blockchain-Based Approach for Saving and Tracking Differential-Privacy Cost", arXiv:2001.09259 (2020) OPENED (abstract): "blockchain provides a distributed immutable ledger that records each query's type, the noisy response ..., the associated noise level ..., and the remaining privacy budget" + reuse of earlier noisy answers. => "privacy-budget ledger on a blockchain" per se is DONE (single dataset, single curator, no MPC, no multi-authority identity, no cross-silo).
- DProvDB (Shufan Zhang, Xi He; arXiv:2309.10240, 2023) OPENED (abstract): multi-analyst DP "privacy provenance framework ... tracks the privacy loss to each single data analyst", apportions budget by "privilege levels" and handles collusion vs. non-collusion. Centralised DB. => per-analyst + global budget with privilege levels is DONE centrally.
- Pujol, Sun, Fain, Machanavajjhala, "Multi-Analyst DP for Online Query Answering" (arXiv:2212.09884, VLDB 2023) and "Budget Sharing for Multi-Analyst DP" (arXiv:2011.01192) OPENED (abstracts): equitable budget sharing among analysts sharing one budget. Centralised.
- Biswas & Cormode, "Verifiable Differential Privacy" (arXiv:2208.09011) OPENED (abstract): curator outputs a ZK proof that the output "is both DP and reliable" (counting queries), mixing private and public randomness. Bontekoe, Asghar, Turkmen, "Efficient Verifiable DP with Input Authenticity in the Local and Shuffle Model", PoPETs 2025(2) (arXiv:2406.18940) OPENED (abstract). => candidate (iii) (verifiable honest noise) is an active, well-occupied area.
- Shrinkwrap (Bater, He, Ehrich, Machanavajjhala, Rogers; VLDB 2019; arXiv:1810.01816) OPENED (abstract): "private data federation ... autonomous databases ... evaluating queries obliviously using secure multiparty computation" + DP. Cryptε (Roy Chowdhury, Wang, He, Machanavajjhala, Jha; SIGMOD 2020; arXiv:1902.07756) OPENED (abstract): two non-colluding servers run DP programs on encrypted data. => MPC + DP over a hospital-style federation is DONE (SMCQL/Shrinkwrap were literally motivated by clinical data research networks).
- ULDP-FL (Kato, Xiong, Takagi, Cao, Yoshikawa; arXiv:2308.12210; VLDB 2024) OPENED (abstract): "a single user's data may extend across multiple silos" -> user-level DP across silos with a private weighting protocol. => cross-silo patient overlap is recognised and solved for FL (not for stats queries / not with budget ledger).
- Enigma (Zyskind, Nathan, Pentland; arXiv:1506.03471, 2015) OPENED (abstract): MPC over secret-shared data where "an external blockchain is utilized as the controller of the network, manages access control, identities and serves as a tamper-proof log of events". => "blockchain-governed MPC with access control and a log" is a 2015 idea.
- FAMHE (Froelicher et al., Nature Communications 12:5910, 2021, doi:10.1038/s41467-021-25972-y) OPENED (abstract): multi-institution federated analytics (Kaplan-Meier, GWAS) with multiparty HE. MedCo (Raisaro et al., IEEE/ACM TCBB 2019, doi:10.1109/TCBB.2018.2854776) SNIPPET (title/authors only).
- Oghenekevwe & Adawaren, "Attribute-Based Encryption with Secure Multi-Party Computation for Fine-Grained Access Control in Cloud-Based Healthcare Systems", IJRSI 2026, doi:10.51244/ijrsi.2025.1213cs0022 OPENED (abstract): "ABE for fine-grained, policy-driven confidentiality and SMC for privacy-preserving collaborative analytics ... multi-institutional analytics without exposing raw records". Low-tier venue, no blockchain, no DP. => the bare "ABE + MPC for hospitals" combination is published.
- Wu, Liu, Zhu, Zhang, "Data-Sharing System with ABE in Blockchain and Privacy Computing", Symmetry 16(11):1550, 2024 OPENED (abstract via Crossref): financial data, CP-ABE + ChainMaker privacy computing + Boolean search. No DP/stats. Low overlap.
- Additional OPENED abstracts: PrivacyGuard (Xiao, Zhang, Li, Lou, Hou; arXiv:1904.07275, 2019): "Smart contracts are used to specify data usage policy, i.e., who can use what data under which conditions and what analytics to perform, while the distributed blockchain ledger is used to keep an irreversible and non-repudiable data usage record" (TEE, no DP). Cohere (Kuchler et al., IEEE S&P 2024, arXiv:2301.08517) and DPolicy (Kuchler et al., IEEE S&P 2025, arXiv:2505.06747): DP budget management across many applications / releases inside ONE organisation (trusted manager). Big Bird related work (on disk) states: "managing budgets across queriers, especially untrusted ones, remains relatively unexplored" and "no work treats privacy budgets as a DoS target and provides Sybil-resilient budget management" (before Big Bird).
- HMBC follow-up check: grep of the ~80 HMBC-citing papers collected by an earlier run (Google Scholar + OpenAlex lists on disk) for differential/multiparty/statistic/budget/aggregat/secret-sharing -> NO citing paper adds statistical/DP/MPC access to HMBC.

---------------------------------------------------------------------
# FINAL REPORT

## 1. Candidates (anchored in the ORIGINAL HMBC2020 architecture)

**C1 - Policy-bound statistical MPC ("authorise the query, not the record").** A researcher/insurer submits a statistical query q = (f, filter, hospital set S, epsilon) to the PSC. LSC logs it; TMSC validates the GID/cert; each domain ACSC evaluates a *query policy* over multi-authority attributes (e.g. Researcher@any-university AND IRBApproved(project) AND f in AllowedAggregates). The hospitals in S each run a new "statistics executor" next to their DBC node and feed secret shares of local aggregates into an MPC (additive/Shamir 3PC); output delivered encrypted to the requester's GID. Records are never decrypted for the requester (KSSC untouched).

**C2 - Ledger-enforced GLOBAL privacy-budget accountant across autonomous custodians and authorities (recommended).** The PBC's single entry point + replicated log becomes a *privacy-loss ledger*: before any MPC runs, the PBC commits an atomic debit of epsilon (or rho for zCDP) against (a) every affected patient-group / hospital-subset, (b) the requesting GID, (c) the GID's *accountability unit* (its issuing authority / organisation, e.g. "Insurer Z"), and (d) per-domain quotas mirroring the PBC/DBC hierarchy. Each hospital's MPC party contributes shares ONLY after verifying the committed debit receipt itself (block inclusion + threshold signature of PBC validators), not via the untrusted Inter-BC API. Noise is sampled inside MPC (or calibrated to honest parties only). Security-specific pieces that the prior art does not combine: (i) the cross-silo averaging/subset-differencing attack (query S={1,2,3} then S={1,2} and subtract) and per-patient user-level accounting when the same patient is in several hospitals; (ii) Sybil and collusion across *independent* registration authorities (one person, two GIDs from two authorities) and the dual threat of budget *depletion* (DoS on honest researchers, as in Big Bird); (iii) TOCTOU/replay of a debit receipt between chains (links to seed gap (d)/(e)).

**C3 - Verifiable honest noise + audit linkage.** Each released noisy result carries a proof that noise was sampled from the right distribution with the logged epsilon, and the LSC binds proof <-> debit so an auditor (retrieveLog under majorityConsent) can check every release.

## 2. Queries used and closest prior art

Queries (WebSearch quota was exhausted, so via arXiv API / Crossref / prior full texts; ~35 calls): "privacy budget" AND blockchain; "differential privacy" AND "secure multiparty" AND hospitals; "multi-analyst" DP; "verifiable differential privacy"; "private data federation(s)"; "user-level differential privacy" AND silo; "secure multiparty computation" AND "access control" AND policy; blockchain AND DP AND "privacy budget" AND query; "privacy budget" AND sybil; "secure computation" AND "attribute-based"; MPC AND authorization; "cross-chain" AND DP; "federated analytics" AND "privacy budget"; functional encryption multi-client access control; crypto-assisted DP; Enigma; PrivacyGuard; Sterling; MPCAuth; blockchain AND DP AND "secret sharing"; "privacy budget" AND "smart contract"; "privacy loss" ledger audit; Crossref: blockchain DP budget medical; privacy budget management blockchain; SMPC blockchain healthcare statistics DP; ABE + DP blockchain medical; DP Hyperledger Fabric budget; SMPC ABAC blockchain statistical; access control SMPC authorization; cross-domain blockchain DP medical; Cohere; DPolicy; Honeycrisp; Arboretum; SMCQL; secure DP sampling in MPC. (Semantic Scholar, OpenAlex and DBLP returned HTTP 429 all session.)

| Cand. | Closest prior art (status) | What overlaps | What remains different |
|---|---|---|---|
| C1 | Enigma, arXiv:1506.03471, 2015 (OPENED) | MPC whose "blockchain ... manages access control, identities and serves as a tamper-proof log" | No multi-authority ABE attributes, no domain hierarchy, no DP |
| C1 | PriCollabAnalysis, Cluster Computing 2025 (OPENED full text) | Fabric + secret sharing + SMPC + Paillier for multi-hospital researcher statistics | Single channel; requester vetted by one hospital; no attribute policy, no DP/budget |
| C1 | PrivacyGuard, arXiv:1904.07275 (OPENED) | Smart-contract policy over "what analytics to perform" + usage ledger | TEE not MPC; single data owners; no DP |
| C1 | Cerebro, USENIX Sec 2021 (OPENED full text) | MPC "release policies" + cryptographic auditing | No identity/attribute authorisation, no ledger, no budget |
| C1 | Oghenekevwe & Adawaren, IJRSI 2026 (OPENED abstract) | "ABE ... and SMC for ... multi-institutional analytics" in healthcare | Low-tier; no blockchain/DP |
| C2 | Zhao et al., arXiv:2001.09259, 2020 (OPENED) | Blockchain ledger of each query, noise level and "remaining privacy budget" | Single curator/dataset; no MPC, no multi-authority principals, no Sybil/collusion, no cross-silo overlap |
| C2 | Big Bird, SOSP 2026 (OPENED full text) | Per-querier DP is "unsound"; global budget across all queriers; Sybil depletion; quotas | Web ads, on-device accounting, no custodians/MPC/ledger; open web, no accountable PKI |
| C2 | DProvDB (arXiv:2309.10240, 2023) & Pujol et al. (arXiv:2011.01192, 2212.09884) (OPENED) | Per-analyst + global budget, privilege levels, colluding analysts | Trusted central DB; one data owner |
| C2 | Cohere (S&P 2024) / DPolicy (S&P 2025) (OPENED abstracts) | System-wide budget management across many releases | Single trusted organisation |
| C2 | ULDP-FL (arXiv:2308.12210, VLDB 2024) (OPENED) | User's data "may extend across multiple silos" -> user-level DP across silos with private protocol | FL training, not ledger-governed statistical queries; no authorisation/budget across queriers |
| C2/C3 | Shrinkwrap (VLDB 2019), Cryptε (SIGMOD 2020), SMCQL (PVLDB 2017) (OPENED / SNIPPET for SMCQL) | MPC + DP over federations of autonomous (clinical) databases | Budget is per-curator; no multi-querier Sybil, no ledger, no authority model |
| C3 | Drynx, TIFS 2020 (OPENED full text) | Multi-hospital stats, verifiable DP noise ("no entity knows which noise value is added"), "proof blockchain" for auditors | Authorisation "out of scope"; no cumulative budget |
| C3 | Biswas & Cormode, Verifiable DP (arXiv:2208.09011) ; Bontekoe et al. PoPETs 2025 (OPENED) | ZK proof that output is DP and correct | Not tied to a budget ledger (incremental at best) |
| bg | FAMHE, Nat. Commun. 2021 (OPENED); MedCo TCBB 2019, Honeycrisp SOSP 2019, Arboretum SOSP 2023 (SNIPPET) | Multi-institution federated analytics / DP aggregation at scale | No ledger-enforced cross-querier budget across authorities |

## 3. Verdicts

- **C1: PARTIAL -> effectively DONE** (confidence 75%). Blockchain-governed MPC with access control (Enigma 2015), blockchain+SMPC hospital statistics (PriCollabAnalysis 2025) and ABE+SMC for hospitals (2026) exist. Only residual novelty is plumbing it into multi-authority ABE attributes and the PBC/DBC hierarchy - an integration result, not a workshop contribution on its own. Use it only as the substrate of C2.
- **C2: NOVEL-NICHE** (confidence ~60%; search coverage degraded). Niche: *sound global DP accounting with NO trusted curator across mutually distrusting data custodians AND multiple independent registration authorities, enforced by debit-gated MPC on a consortium ledger, with explicit analysis of cross-silo patient overlap, hospital-subset differencing, cross-authority Sybil/collusion and budget-depletion DoS.* Each ingredient exists separately (ledger counter: Zhao 2020; global cross-querier + Sybil: Big Bird; multi-analyst: DProvDB; cross-silo user-level: ULDP-FL; MPC+DP: Shrinkwrap/Drynx); I found no work combining them, and Big Bird itself (Sep 2026) says cross-querier budget management among untrusted queriers is "relatively unexplored". It IS a security contribution if framed as an enforcement/soundness property against an adversary (attacks + game-based budget-soundness definition + reduction), not as a utility/ML system.
- **C3: DONE** (confidence 80%) by Drynx (verifiable noise + audit chain) and the verifiable-DP line. Keep only as an optional "debit <-> release binding" lemma inside C2.

JANUS-exclusion check: JANUS has no statistical path (0 hits). C2 does not touch the domain-key/KSSC partial-decryption mechanism. Risk: the "no output without committed debit" property resembles the excluded "authorization -> transform" definition; frame the contribution around DP-budget soundness and the cross-silo/Sybil attacks, not around single-entry-point enforcement.

## 4. PoC feasibility (3 laptops, synthetic data)

- **Parties:** laptop i = Hospital i (and one also hosts an "Insurer" and a "University" authority). Each runs one PBC validator, one hospital-DBC validator, one MPC party. Requester client on any laptop.
- **Ledger:** to stay close to HMBC2020 (Ethereum + Solidity): 3-validator private Ethereum PoA/QBFT network for the PBC and a second for the hospital DBC (Docker, ~0.3-0.5 GB RAM per node). New contract: BudgetLedger (inside/next to LSC) + query policy in ACSC. Alternative: Fabric test-network (heavier).
- **MPC:** MPyC (pure-Python Shamir, honest majority, 3 parties, trivial install) for the PoC; MP-SPDZ (replicated-ring 3PC, semi-honest and malicious variants) for a malicious-security datapoint. Noise: discrete Laplace/Gaussian sampled in MPC (Fu & Wang, "Benchmarking Secure Sampling Protocols for DP", arXiv:2409.10667 - SNIPPET, use as baseline), or distributed noise calibrated to the honest parties only.
- **Data:** Synthea synthetic EHR, ~3 x 30-50k patients; inject 10-20 % overlapping patients (shared pseudonymous ID) to exercise user-level accounting. Queries: COUNT/SUM/MEAN/histogram with diagnosis/age filters (insurer "treatment cost by condition", researcher "prevalence").
- **Expected runtimes (estimates, not measured):** local pre-aggregation <1 s; MPC aggregation of a few hundred field elements + noise over LAN/Wi-Fi: 10 ms-1 s; record-level oblivious filtering over 150k rows: seconds-minutes (avoid; aggregate locally); debit commit = 1-2 block intervals (1-5 s) -> end-to-end 2-6 s/query, dominated by consensus. RAM well under 3.5 GB per laptop.
- **Effort:** ~9-11 person-weeks (contracts + receipts 2; MPC + noise 2-3; overlap/PSI or shared-pseudonym accounting 1-2; attacks + benchmarks 2; formal model/proof 2; writing 1-2).
- **Pitfalls:** distributed noise can be stripped by colluding hospitals (calibrate to t corruptions or sample in MPC); floating-point DP pitfalls (use discrete mechanisms); patient linkage across hospitals needs a pseudonymous ID or PSI (HMBC has no patient identity at all); Wi-Fi latency variance; MPyC is semi-honest only; avoid claiming "malicious security" without MP-SPDZ runs.

## 5. Evaluation plan

- **Threat model:** malicious requesters (adaptive queries, averaging/differencing), colluding principals inside one organisation, Sybil GIDs via up to k corrupt registration authorities; up to t < n/2 corrupt hospital MPC parties (semi-honest PoC, malicious discussed); PBC validators: < 1/3 Byzantine (BFT) or honest majority as in HMBC; Inter-BC API untrusted.
- **Properties:** P1 budget soundness (per patient and per accountability unit, total loss <= B under adaptive composition); P2 no release without a committed, non-replayable debit; P3 input privacy (MPC simulation); P4 availability: an honest authority's quota cannot be depleted by others; P5 auditability (every release linked to a ledger debit).
- **Argument type:** game-based definitions + reduction to ledger consistency, threshold/aggregate signature EUF-CMA, MPC security and DP composition (sequential, parallel over disjoint silos, user-level for overlap); Tamarin/ProVerif model of authorise -> debit -> receipt -> execute for replay/TOCTOU (matches instructor preference for tool-verified protocols).
- **Attacks shown on baselines:** A1 per-hospital budgets + overlap re-identification; A2 hospital-subset differencing; A3 Sybil GIDs across authorities; A4 receipt replay to another hospital set; A5 depletion DoS. Metric: attack success (membership inference advantage on a target patient) vs #queries.
- **Baselines:** B0 HMBC as-is (Researcher attribute decrypts records); B1 per-hospital local DP budgets; B2 trusted central curator with global budget (utility upper bound); B3 PriCollabAnalysis-style MPC without DP.
- **Metrics:** latency/throughput vs #hospitals (3 real + up to ~9 emulated processes), gas per debit, MPC bytes/rounds, RMSE vs epsilon, #useful queries before exhaustion under quotas.

## 6. Syllabus fit
MPC (explicit item) - core; blockchain security & privacy (explicit) - core; hierarchical access control / key management - via the PBC/DBC policy and quotas; AI/ML security - membership-inference evaluation. Strong fit.

## 7. Kill criteria and reviewer objections
- **Kill 1:** a paper already doing "consortium-ledger-gated MPC with a global DP budget across custodians/queriers" (most likely in IEEE IoT-J / TDSC / Access / Elsevier, which arXiv-only search under-covers). Before committing, run with restored WebSearch: "privacy budget" "consortium blockchain" "secure multi-party"; "differential privacy" "budget" "multi-blockchain"; "privacy budget" "Hyperledger" medical; "privacy accounting" "data custodians" ledger; "global privacy budget" "data federation"; Google Scholar forward-citations of Zhao 2020 and Shrinkwrap.
- **Kill 2:** utility collapse - if a per-patient global epsilon <= ~2-4 allows < ~10 useful queries on 3 x 50k patients, the system is unpersuasive (mitigate: zCDP, answer reuse, histograms).
- **Kill 3:** the security argument reduces to "a counter on a blockchain" - then it is Zhao 2020 + Shrinkwrap. The cross-silo overlap, subset-differencing, Sybil/depletion and receipt-binding pieces must be real.
- **Objections:** "why a blockchain rather than a trusted DP curator?" (answer: competing stakeholders, already HMBC's premise); "a global per-patient budget is unworkable" (Big Bird's depletion problem); semi-honest MPC only; synthetic data; arbitrary epsilon; "composition of known parts" - must be pre-empted with the attack demonstrations.

## 8. Scores (1-10)

| | Novelty | Feasibility | Security depth | Syllabus fit | Workshop fit |
|---|---|---|---|---|---|
| C1 policy-bound MPC | 3 | 8 | 5 | 9 | 4 |
| **C2 global budget accountant** | **6** | **7** | **7** | **9** | **7** |
| C3 verifiable noise/audit | 2 | 5 | 7 | 7 | 3 |

## 9. References (status)
1. Malamas et al., HMBC, IEEE Access 8:134393, 2020 - OPENED (local text).
2. Malamas et al., JANUS, Appl. Sci. 13(1):566, 2023 - OPENED (local text).
3. Tawfik, Al-Ahwal, Tag Eldien, Zayed, PriCollabAnalysis, Cluster Computing 28:191, 2025, doi:10.1007/s10586-024-04928-z - OPENED (full text).
4. Froelicher, Troncoso-Pastoriza, Sousa, Hubaux, Drynx, IEEE TIFS 2020, arXiv:1902.03785 - OPENED (full text).
5. Zheng, Deng, Chen, Popa, Panda, Stoica, Cerebro, USENIX Security 2021 - OPENED (full text).
6. Tholoniat, Caulfield, et al., Big Bird, SOSP 2026, arXiv:2506.05290, doi:10.1145/3830418.3843897 - OPENED (full text).
7. Zhao, Zhao, Kang, Zhang, Niyato, Shi, Blockchain-based saving/tracking of DP cost, arXiv:2001.09259, 2020 - OPENED (abstract).
8. Zhang & He, DProvDB, arXiv:2309.10240, 2023 - OPENED (abstract).
9. Pujol, Wu, Fain, Machanavajjhala, Budget Sharing for Multi-Analyst DP, arXiv:2011.01192 - OPENED (abstract); Pujol, Sun, Fain, Machanavajjhala, Multi-Analyst DP for Online Query Answering, arXiv:2212.09884 - OPENED (abstract).
10. Kuchler et al., Cohere, IEEE S&P 2024, arXiv:2301.08517, doi:10.1109/SP54263.2024.00122 - OPENED (abstract); Kuchler et al., DPolicy, IEEE S&P 2025, arXiv:2505.06747 - OPENED (abstract).
11. Kato, Xiong, Takagi, Cao, Yoshikawa, ULDP-FL, arXiv:2308.12210 - OPENED (abstract).
12. Bater, He, Ehrich, Machanavajjhala, Rogers, Shrinkwrap, arXiv:1810.01816 - OPENED (abstract); Bater et al., SMCQL, PVLDB 2017, doi:10.14778/3055330.3055334 - SNIPPET.
13. Roy Chowdhury, Wang, He, Machanavajjhala, Jha, Cryptε, arXiv:1902.07756 - OPENED (abstract).
14. Biswas & Cormode, Verifiable Differential Privacy, arXiv:2208.09011 - OPENED (abstract).
15. Bontekoe, Asghar, Turkmen, Efficient Verifiable DP with Input Authenticity in the Local and Shuffle Model, PoPETs 2025(2), arXiv:2406.18940 - OPENED (abstract).
16. Zyskind, Nathan, Pentland, Enigma, arXiv:1506.03471, 2015 - OPENED (abstract).
17. Xiao, Zhang, Li, Lou, Hou, PrivacyGuard, arXiv:1904.07275, 2019 - OPENED (abstract).
18. Froelicher et al., FAMHE, Nature Communications 2021, doi:10.1038/s41467-021-25972-y - OPENED (abstract).
19. Oghenekevwe & Adawaren, ABE with SMC for healthcare, IJRSI 2026, doi:10.51244/ijrsi.2025.1213cs0022 - OPENED (abstract).
20. Wu, Liu, Zhu, Zhang, Data-Sharing System with ABE in Blockchain and Privacy Computing, Symmetry 16(11):1550, 2024 - OPENED (abstract).
21. Raisaro et al., MedCo, IEEE/ACM TCBB 2019, doi:10.1109/TCBB.2018.2854776 - SNIPPET.
22. Roth et al., Honeycrisp, SOSP 2019, doi:10.1145/3341301.3359660 - SNIPPET; Margolin et al., Arboretum, SOSP 2023, doi:10.1145/3600006.3624566 - SNIPPET.
23. Zhou, Feng, Wang, Guo, Using SMPC to protect privacy on a permissioned blockchain, Sensors 21(4):1540, 2021, doi:10.3390/s21041540 - SNIPPET (via ref. 3); Ghadamyari & Samet, Paillier statistics on permissioned blockchain, IEEE BigData 2019, doi:10.1109/BigData47090.2019.9006231 - SNIPPET; Yang et al., A security model of multihospital FHIR database authorization based on secret sharing and blockchain, IEEE IoT-J 2024, doi:10.1109/JIOT.2023.3328989 - SNIPPET (no abstract retrieved; should be opened before writing).
24. Fu & Wang, Benchmarking Secure Sampling Protocols for DP, arXiv:2409.10667, 2024 - SNIPPET.
Tools named (MPyC, MP-SPDZ, Synthea, OpenDP) were not re-verified online this session.

Status: COMPLETE (2026-10-04).
