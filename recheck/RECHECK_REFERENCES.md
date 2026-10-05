# RECHECK_REFERENCES - everything to verify (tasks T2 and T8)

Compiled by the LEAD from the sub-agent reports in `context/reports/`. **Every row was produced by an AI agent working mostly through arXiv/Crossref/Semantic Scholar APIs; metadata and claims may be wrong.**

How to use: for each row, check title / authors / venue / year / identifier against a primary source (Crossref, arXiv, the publisher page, or Google Scholar) and verify the **Claim relied on** by reading the abstract (or text). Record the outcome in `RECHECK_COMMS.md` (section "T8 results") as: `ID | OK / MISMATCH(correct value) / NOT FOUND | opened? | note`.
"Prior" = status in the LEAD's runs: **OPENED** (abstract or full text read) or **SNIPPET** (metadata/title only). Priority: **P0** = the plan's headline claim depends on it; **P1** = cited as related work; **P2** = background.

## Section 0 - the two assigned papers and the local artifacts (verify identifiers only)

| ID | Citation | Identifier | Prior | Claim relied on |
|---|---|---|---|---|
| R01 | V. Malamas, P. Kotzanikolaou, T. K. Dasaklis, M. Burmester, "A Hierarchical Multi Blockchain for Fine Grained Access to Medical Data", IEEE Access 8:134393-134412, 2020 | doi 10.1109/ACCESS.2020.3011201 | OPENED (local) | Architecture in RECHECK_HANDOFF Sec. 1. Statistical access is only gated by an ABE 'Researcher' attribute and 'logging' (Sec. III-C6, III-F); every request is logged on the PBC (Sec. III-D4, V-A5); membership rules (III-D1, V-A2, V-B1) |
| R02 | V. Malamas, G. Palaiologos, P. Kotzanikolaou, M. Burmester, D. Glynos, "Janus: Hierarchical Multi-Blockchain-Based Access Control (HMBAC) for Multi-Authority and Multi-Domain Environments", Appl. Sci. 13(1):566, 2023 | doi 10.3390/app13010566 | OPENED (local) | Fabric+Raft implementation, Vault ABE plugin, voting governance, attack trees; no DP/MPC/statistics mechanism; auditor log access via election |
| R03 | Du et al., "Blockchain-based and multi-authority hierarchical access control data sharing scheme", Computers & Electrical Engineering, 2024 | **DOI unknown - find it** (local PDF in `../Papers/`) | OPENED (local) | States that on-chain access logs disclose visitor identity and accessed content to the whole network; lists zero-knowledge proofs as future work |
| R04 | A. Lewko, B. Waters, "Decentralizing Attribute-Based Encryption", EUROCRYPT 2011 | doi 10.1007/978-3-642-20465-4_31 (check) | OPENED (local) | Source of the global-identifier (GID) requirement for collusion resistance |

## Section A - Candidate A (ledger-enforced global DP-budget accounting): threats and substrate. Tasks T1/T2/T8

| ID | Citation | Identifier | Prior | Claim relied on / why it matters | Pri |
|---|---|---|---|---|---|
| A01 | N. Rahimian, L. Panny, S. Joshi, "Privacy at Scale in Networked Healthcare" (IEEE TPS-ISA 2025/2026; 1st IEEE HMD-SPiRiT workshop) | arXiv:2601.04298 | OPENED (full text, 6 pp) | Position paper that names "privacy-budget ledgers" across healthcare sites as an agenda item and says end-to-end privacy accounting across institutions is open; **no mechanism, no blockchain, no threat model**. Both a threat (idea named) and motivation (problem open). Verify exact wording and venue | P0 |
| A02 | Y. Zhao, J. Zhao, J. Kang, Z. Zhang, D. Niyato, S. Shi, "A Blockchain-Based Approach for Saving and Tracking Differential-Privacy Cost" | arXiv:2001.09259 (2020; check IEEE IoT-J venue) | OPENED (abstract) | Blockchain ledger records each query, noisy response, noise level and remaining budget; single curator/dataset, no MPC, no multi-authority | P0 |
| A03 | Han, Zhao, Zhao, "POSTER: Blockchain-Based DP Cost Management System", ACM AsiaCCS 2020 | doi 10.1145/3320269.3405446 | OPENED (abstract) | Demo of A02 | P1 |
| A04 | F. Tholoniat, K. Caulfield, ..., R. Geambasu, M. Lecuyer, J. Thomson, "Big Bird" (ACM SOSP 2026) | arXiv:2506.05290; doi 10.1145/3830418.3843897 | OPENED (full text) | Shows per-querier DP enforcement is "unsound ... under cross-querier data adaptivity"; proposes a global budget enforced across all domains; main obstacle is "denial-of-service depletion of a shared global budget by Sybil web domains". Web-advertising, on-device setting. Verify these quotes, and that SOSP 2026 is the right venue/year | P0 |
| A05 | T. Islam, M. H. Rehmani, J. Chen, "Differentially Private Enhanced Permissioned Blockchain for Private Data Sharing in Industrial IoT" (EDH-IIoT) | arXiv:2212.00068 (journal per Semantic Scholar: Information Sciences - check) | OPENED (abstract) | Fabric chaincode answers statistical queries with DP, tracks epsilon against a threshold, evaluates linking/composition attacks; single data owner, no MPC | P0 |
| A06 | Islam, Rehmani, Gao, Chen, "An Optimized Privacy-Utility Tradeoff Framework for DP Data Sharing in Blockchain-Based IoT" (OPU-TF-IoT) | arXiv:2212.00128; doi 10.1109/JIOT.2025.3530247 | OPENED (abstract) | Blockchain-based verification so data owners can see DP-budget use; budget accumulates under composition | P0 |
| A07 | Agarwal, Pal, "HierChain: A Hierarchical-Blockchain-Based Data Management System for Smart Healthcare", IEEE IoT-J 2024 | doi 10.1109/JIOT.2023.3295847 | OPENED (abstract) | Hierarchical multi-blockchain healthcare system that applies DP at the fog layer; local sanitisation only, no cumulative budget | P1 |
| A08 | S. Zhang, X. He, "DProvDB: Differentially Private Query Processing with Multi-Analyst Provenance" | arXiv:2309.10240 | OPENED (abstract) | Per-analyst + global budget with privilege levels, collusion vs non-collusion; centralised trusted DB | P1 |
| A09 | Pujol, Wu, Fain, Machanavajjhala, "Budget Sharing for Multi-Analyst Differential Privacy" arXiv:2011.01192; Pujol, Sun, Fain, Machanavajjhala, "Multi-Analyst Differential Privacy for Online Query Answering" arXiv:2212.09884 (VLDB 2023) | as given | OPENED (abstracts) | Budget shared among analysts; centralised | P2 |
| A10 | Kuchler et al., "Cohere" (IEEE S&P 2024) arXiv:2301.08517 doi 10.1109/SP54263.2024.00122; "DPolicy" (IEEE S&P 2025) arXiv:2505.06747 | as given | OPENED (abstracts) | System-wide DP budget management inside one trusted organisation | P2 |
| A11 | Kato, Xiong, Takagi, Cao, Yoshikawa, "ULDP-FL: Federated Learning with Across-silo User-Level Differential Privacy" (VLDB 2024) | arXiv:2308.12210 | OPENED (abstract) | A user's data can span silos; user-level DP across silos with a private weighting protocol (FL, not queries) | P1 |
| A12 | Bater, He, Ehrich, Machanavajjhala, Rogers, "Shrinkwrap: Efficient SQL Query Processing in Differentially Private Data Federations" (VLDB 2019) arXiv:1810.01816; Bater et al., "SMCQL" (PVLDB 2017) doi 10.14778/3055330.3055334 | as given | Shrinkwrap OPENED (abstract); SMCQL SNIPPET | MPC + DP over federations of autonomous (clinical) databases; budget per curator | P0 |
| A13 | Roy Chowdhury, Wang, He, Machanavajjhala, Jha, "Crypt-epsilon: Cryptography Meets Differential Privacy" (SIGMOD 2020) | arXiv:1902.07756 | OPENED (abstract) | Two non-colluding servers run DP programs on encrypted data | P1 |
| A14 | Froelicher, Troncoso-Pastoriza, Sousa, Hubaux, "Drynx: Decentralized, Secure, Verifiable System for Statistical Queries and ML on Distributed Datasets", IEEE TIFS 2020 | arXiv:1902.03785 | OPENED (full text) | Multi-hospital stats; verifiable DP noise; "proof blockchain" for auditors; "authentication and authorization are out of scope"; no cumulative budget | P0 |
| A15 | Zheng, Deng, Chen, Popa, Panda, Stoica, "Cerebro: A Platform for Multi-Party Cryptographic Collaborative Learning", USENIX Security 2021 | (find DOI/URL) | OPENED (full text) | MPC release policies + cryptographic auditing; no ledger, no budget across queriers | P2 |
| A16 | Tawfik, Al-Ahwal, Tag Eldien, Zayed, "PriCollabAnalysis" (title: check), Cluster Computing 28:191, 2025 | doi 10.1007/s10586-024-04928-z | OPENED (full text) | Fabric + secret sharing + SMPC + Paillier statistics across hospitals for researchers; no DP/budget/attribute policy/hierarchy | P0 |
| A17 | G. Zyskind, O. Nathan, A. Pentland, "Enigma: Decentralized Computation Platform with Guaranteed Privacy" | arXiv:1506.03471 | OPENED (abstract) | Blockchain as controller for MPC: access control, identities, tamper-proof log | P1 |
| A18 | Xiao, Zhang, Li, Lou, Hou, "PrivacyGuard: Enforcing Private Data Usage Control with Blockchain and Attested Off-chain Contract Execution" (title: check) | arXiv:1904.07275 | OPENED (abstract) | Smart-contract data-usage policy + immutable usage record (TEE, no DP) | P2 |
| A19 | Biswas, Cormode, "Verifiable Differential Privacy" arXiv:2208.09011; Bontekoe, Asghar, Turkmen, "Efficient Verifiable Differential Privacy with Input Authenticity in the Local and Shuffle Model", PoPETs 2025(2) arXiv:2406.18940 | as given | OPENED (abstracts) | Verifiable DP noise proofs (a different, occupied sub-area) | P2 |
| A20 | Froelicher et al., FAMHE, Nature Communications 12:5910 (2021) doi 10.1038/s41467-021-25972-y; Raisaro et al., MedCo, IEEE/ACM TCBB 2019 doi 10.1109/TCBB.2018.2854776; Roth et al., Honeycrisp, SOSP 2019 doi 10.1145/3341301.3359660; Margolin et al., Arboretum, SOSP 2023 doi 10.1145/3600006.3624566 | as given | FAMHE OPENED; others SNIPPET | Background: federated analytics with MPC/HE; DP aggregation at scale | P2 |
| A21 | Oghenekevwe, Adawaren, "Attribute-Based Encryption with Secure Multi-Party Computation for Fine-Grained Access Control in Cloud-Based Healthcare Systems", IJRSI 2026 | doi 10.51244/ijrsi.2025.1213cs0022 | OPENED (abstract) | ABE + SMC for multi-institution analytics (low-tier; no blockchain/DP) | P1 |
| A22 | Yang, Li, Cheng, Kuo, Lu, Xiong, "A Security Model of Multihospital FHIR Database Authorization Based on Secret Sharing and Blockchain", IEEE IoT-J 11(6), 2024 | doi 10.1109/JIOT.2023.3328989 | OPENED (abstract, by R2 adversary) | Threshold key authorisation across hospitals; no statistics/DP/budget (closer to an excluded direction) | P1 |
| A23 | Gu, Wang, Wu, "A Dual-Chain and Differential Privacy-Based Solution for Medical Data Privacy Protection and Access Control", IJACSA 17(2), 2026 | doi 10.14569/ijacsa.2026.0170288 | OPENED (abstract) | Private+consortium chains + IPFS; external parties get de-identified, noised data; no cumulative budget | P1 |
| A24 | Venkatesan et al., "Blockchain Enabled EHR Sharing with Zero-Trust Access Controls and Differential Privacy Protection", ICIETSD 2026 | doi 10.1109/ICIETSD68684.2026.11584847 | OPENED (abstract) | Multi-hospital Fabric + access control + DP analytics + audit trail (buzzword level) | P1 |
| A25 | Wang, Guo, "Research on a Blockchain Adaptive DP Mechanism for Medical Data Protection", Future Internet 17(12):539, 2025 | doi 10.3390/fi17120539 | OPENED (abstract) | Budget allocation by contributor reputation + zk-SNARK verification of DP computation | P1 |
| A26 | Balakrishnan et al., "Blockchain-Orchestrated Privacy Preservation for Cloud-Based Data Mining" (BOPPF), IEEE RCSM 2025 | doi 10.1109/RCSM67767.2025.11506883 | OPENED (abstract) | Blockchain + DP + secure aggregation + access control on MIMIC-III (low-tier, vague) | P2 |
| A27 | Veeraragavan, Nygard, "DeCanSec: A Decentralized Architecture for Secure Statistical Computations on Distributed Health Registry Data", ARES 2021 | doi 10.1145/3465481.3470071 | OPENED (abstract) | Blockchain-coordinated secure statistics over health registries (no DP in abstract) | P1 |
| A28 | Heo, Doh, "Blockchain and DP-based data processing system for data security and privacy in urban computing", Computer Communications 2024 | doi 10.1016/j.comcom.2024.04.027 | SNIPPET | Title-level overlap only; open it | P2 |
| A29 | Gu, Zhang, Zhang, "Multiparty Data Publishing via Blockchain and Differential Privacy", Security and Communication Networks 2022 | doi 10.1155/2022/5612794 | OPENED (abstract) | Multi-owner DP publishing, no budget ledger | P2 |
| A30 | Rogers et al., "VaultDB: A Real-World Pilot of Secure Multi-Party Computation within a Clinical Research Network" | arXiv:2203.00146 | OPENED (abstract) | Substrate: MPC SQL across health systems | P2 |
| A31 | Xia et al., "Data Station: Delegated, Trustworthy, and Auditable Computation to Enable Data-Sharing Consortia with a Data Escrow", PVLDB 2022 | arXiv:2305.03842 | OPENED (abstract) | Consortium escrow + audit log; no DP budget | P2 |
| A32 | **Design-agent references (math, not novelty):** Kairouz, Liu, Steinke, "The Distributed Discrete Gaussian Mechanism for Federated Learning with Secure Aggregation" arXiv:2102.06387; Agarwal, Kairouz, Liu, "The Skellam Mechanism for Differentially Private Federated Learning" arXiv:2110.04995; Feldman, Zrnic, "Individual Privacy Accounting via a Renyi Filter" arXiv:2008.11193; Dong, Roth, Su, "Gaussian Differential Privacy" arXiv:1905.02383 | as given | OPENED (abstracts, by design agent) | Noise mechanism and accounting tools the design relies on | P2 |
| A33 | Not re-checked by anyone (verify standard refs): Bun, Steinke, "Concentrated Differential Privacy: Simplifications, Extensions, and Lower Bounds" (TCC 2016); Canonne, Kamath, Steinke, "The Discrete Gaussian for Differential Privacy" (NeurIPS 2020); Bonawitz et al., "Practical Secure Aggregation for Privacy-Preserving ML" (ACM CCS 2017); Hyperledger Besu QBFT documentation | -- | not checked | Used in the proposed noise/aggregation design and the PoC stack | P2 |

**Classical background to attribute correctly (T1):** Denning (inference control / tracker attacks, 1979-1982 era), Dobkin-Jones-Lipton (secure databases, 1979), Kenthapadi-Mishra-Nissim (simulatable auditing, PODS 2005), Chin-Ozsoyoglu (auditing and inference control). Not yet looked up by anyone - find the correct bibliographic entries.

## Section B - Candidate B (sealed global log) - tasks T3/T8

| ID | Citation | Identifier | Prior | Claim relied on / why it matters | Pri |
|---|---|---|---|---|---|
| B01 | Thazhath et al., "Harpocrates: Privacy-Preserving and Immutable Audit Log for Sensitive Data Operations", IEEE TPS-ISA 2022 | arXiv:2211.04741 | OPENED | Private, verifiable audit logs (closest primitive) | P0 |
| B02 | Narula, Vasquez, Virza, "zkLedger: Privacy-Preserving Auditing for Distributed Ledgers", NSDI 2018 | usenix.org/conference/nsdi18/presentation/narula | OPENED | Auditing a ledger without revealing transactions | P1 |
| B03 | Wang et al., "PCTRS" (full title: check), IEEE IoT-J 2026 | doi 10.1109/JIOT.2025.3646619 | OPENED | Threshold tracing / anonymous credentials with on-chain opening | P1 |
| B04 | Guo et al., "zkCross: A Novel Architecture for Cross-Chain Privacy-Preserving Auditing" | IACR ePrint 2024/888 | OPENED | Privacy-preserving auditing across chains | P0 |
| B05 | Garman, Green, Miers, "Accountable Privacy for Decentralized Anonymous Payments", FC 2016 | ePrint 2016/061 | OPENED | Accountable privacy with an opening mechanism | P2 |
| B06 | Naaz et al., "DTRAC" (full title: check), IEEE Access 2022 | doi 10.1109/ACCESS.2022.3225439 | OPENED | Multi-authority anonymous credentials with threshold opening | P1 |
| B07 | Sun, Lai et al. (title: check), IEEE Trans. Cloud Computing 2025 | doi 10.1109/TCC.2025.3555519 | OPENED | Multi-authority anonymous credentials with threshold opening | P1 |
| B08 | M. Chase, S. Chow, "Improving Privacy and Security in Multi-Authority Attribute-Based Encryption", ACM CCS 2009 | doi 10.1145/1653662.1653678 | OPENED | Hides the global ID from key authorities | P1 |
| B09 | Zhang, Li, Wu, Rezaeibagha (title: check; blockchain-aided anonymous traceable and revocable ABE), IEEE IoT-J 2024 | doi 10.1109/JIOT.2023.3287190 | OPENED | Cites BOTH HMBC2020 and JANUS; anonymous participation + white-box tracing | P0 |
| B10 | Wu, Meng, Zhang, Rezaeibagha, JKSU-CIS 2023 (collusion-resistant MA access control, PHR) | doi 10.1016/j.jksuci.2023.101677 | OPENED | Accountable CP-ABE, blockchain accounting node | P2 |
| B11 | Albalwy, "ZK-EHR" (full title: check), Systems 2026 | doi 10.3390/systems14040385 | OPENED | Groth16 proof of EHR policy compliance on-chain without revealing roles | P0 |
| B12 | Naeem, Toorani, Cryptography 2026 | doi 10.3390/cryptography10040059 | OPENED | (title/claim: check) | P2 |
| B13 | Zhang, Datta, TrustCom 2024 | doi 10.1109/TrustCom63139.2024.00088 | OPENED | (title/claim: check) | P2 |
| B14 | **Unopened - HIGH PRIORITY:** "EHRAuditChain: Scalable Privacy-Preserving EHR Audit with RSA Accumulators on Blockchain", SSRN 2025 | SSRN 5495652 | SNIPPET | Closest title to Candidate B | P0 |
| B15 | **Unopened - HIGH PRIORITY:** Zhang et al., "Auditable and dynamic access control scheme with behavior and identity tracing", Computer Networks 2024 | doi 10.1016/j.comnet.2024.110623 | SNIPPET (no abstract) | Cites HMBC2020; touches log accountability + identity tracing | P0 |
| B16 | **Unopened:** Odelu et al., ACM BSCI 2026 | doi 10.1145/3807407.3807473 | SNIPPET | Unlinkable identities, linkable only with user consent | P0 |
| B17 | **Unopened:** Jiang et al., "Cross-Chain Privacy-Preserving Auditable Protocol", ACM BSCI 2025 | doi 10.1145/3709016.3737804 | SNIPPET | Cross-chain privacy-preserving audit | P0 |
| B18 | **Unopened:** Zhang, Xiong, Li, Niu, Wu, J. Syst. Archit. 142 (2023) | doi 10.1016/j.sysarc.2023.102949 | SNIPPET | (check what it does) | P1 |
| B19 | Camenisch, Lehmann, EuroS&P 2017 | doi 10.1109/EuroSP.2017.36 | SNIPPET | Accountable anonymity | P2 |
| B20 | Yin, Zhang, Mu, 2018 | doi 10.1007/978-3-030-00012-7_40 | SNIPPET | GID-free decentralized ABE | P2 |
| B21 | Rahulamathavan et al., IEEE Trans. Computers 2016 | doi 10.1109/TC.2015.2510646 | SNIPPET | Anonymous ABE | P2 |
| B22 | Roio et al., SD-BLS, IEEE Blockchain 2024 | doi 10.1109/Blockchain62396.2024.00074 | SNIPPET | Threshold/BLS | P2 |
| B23 | Tran et al., Maze-Guard, SSRN 2025 | doi 10.2139/ssrn.5387641 | SNIPPET | (check) | P2 |
| B24 | Liu et al., anonymous EHR decentralized hierarchical ABE, IEEE Access 2020 | doi 10.1109/ACCESS.2020.3035468 | SNIPPET | Hierarchical anonymous ABE for EHR | P2 |
| B25 | Prabha, "RSHealth", IEEE Access 2024 | doi 10.1109/ACCESS.2024.3439611 | SNIPPET | Ring-signature anonymisation of the sending stakeholder | P1 |
| B26 | **Leads from memory (not found by any API; verify they exist and say what the LEAD believes):** Waters, Balfanz, Durfee, Smetters, "Building an Encrypted and Searchable Audit Log", NDSS 2004; Frankle, Park, Shaar, Goldwasser, Weitzner, "Practical Accountability of Secret Processes", USENIX Security 2018; Panwar et al., SAMPL (2019); Coconut (NDSS 2019); SEPIA (Burkhart et al., USENIX Security 2010) | -- | NOT VERIFIED | Prior art on private/searchable audit logs and multi-domain event aggregation | P1 |
| B27 | Hyperledger Fabric docs: Idemix (`hyperledger-fabric.readthedocs.io/en/latest/idemix.html`) and Private data (`.../private-data/private-data.html`) | URLs | OPENED | Industry mechanisms that already give anonymous identities and private collections; a reviewer will ask why they do not solve the log-privacy problem | P1 |

## Section C - Candidate C (governance capture) - task T5/T8

| ID | Citation | Identifier | Prior | Claim relied on | Pri |
|---|---|---|---|---|---|
| C01 | Hafid, Hafid, Samih, "A Tractable Probabilistic Approach to Analyze Sybil Attacks in Sharding-Based Blockchain Protocols" (title: check) | arXiv:2104.07215 | OPENED | Sharding analyses assume random assignment | P0 |
| C02 | Zamyatin et al., "SoK: Communication Across Distributed Ledgers", FC 2021 | ePrint 2019/1128 | OPENED | Cross-chain communication unavoidably needs a trusted third party in the general case | P1 |
| C03 | Abebe et al., "Enabling Enterprise Blockchain Interoperability with Trusted Data Transfer" (Weaver) | arXiv:1911.01064 | OPENED | Trust "from the underlying network consensus protocol" | P1 |
| C04 | Steinhoff et al., "BMS" (title: check) | arXiv:2109.03913 | OPENED | Mitigation patterns | P2 |
| C05 | De la Rocha et al., "Hierarchical Consensus" (title: check), ICDCSW 2022 | doi 10.1109/ICDCSW56584.2022.00018 | OPENED (abstract) | Hierarchical consensus mitigation patterns | P2 |
| C06 | Kiayias, Lazos, "SoK: Blockchain Governance" | arXiv:2201.07188 | OPENED | Governance background | P1 |
| C07 | Xu et al., "ChainKeeper" (title: check), IET Blockchain 2023 | doi 10.1049/blc2.12047 | OPENED (abstract) | Cross-chain verification mechanism | P1 |
| C08 | Si, Li, Su, Computer Communications 2024 | doi 10.1016/j.comcom.2024.05.012 | OPENED | (check) | P2 |
| C09 | Ding, Zhang, Qin, Sensors 2023 | doi 10.3390/s23042000 | OPENED | (check) | P2 |
| C10 | He, Zhang, Wang, "Scalable Nested Blockchain Framework with Dynamic Node Selection for IoT", IEEE IPCCC 2022 | doi 10.1109/IPCCC55026.2022.9894312 | OPENED | Main chain + sub chains + a notary for cross-chain transactions; cites HMBC | P1 |
| C11 | Jiang, Li, Tang, Xin, "Secure cross-chain transactions for medical data sharing in BIoMT", Int. J. Netw. Manag. 2024 | doi 10.1002/nem.2279 | OPENED | Relay-chain cross-chain gateway for medical chains; cites HMBC | P1 |
| C12 | Silva et al., "Challenges and trends of Blockchain Interoperability and multi-blockchain architectures", ERI-GO 2025 | doi 10.5753/erigo.2025.17034 | OPENED (abstract) | Survey that cites JANUS and names "reliance on external trust rather than cryptographic consensus" as an open gap | P1 |
| C13 | Wu et al., survey of multi-blockchain, CMC 2026 | doi 10.32604/cmc.2026.077332 | OPENED (abstract) | Taxonomy incl. hierarchical architectures | P2 |
| C14 | Snippet-only list (open if cheap): Zhang, Zhang, Barbee SoK bridges arXiv:2312.12573; Notland et al. arXiv:2403.00405; Lee et al. arXiv:2210.16209; Belenkov et al. arXiv:2501.03423; Rajab et al. arXiv:2002.06531; Mozeika et al. arXiv:2303.14276; Amiri et al. Saguaro 2101.08819 / Qanaat 2107.10836 / SharPer 1910.00765; Gupta et al. ResilientDB 2002.00160; Alqahtani, Demirbas BunchBFT 2205.10658; Yahyaoui et al. arXiv:2504.21410; Bool Network IEEE TIFS 2022 doi 10.1109/tifs.2022.3209546; Xiong, Liu DCN 2022 doi 10.1016/j.dcan.2022.04.012; Fan, Yan JISA 2026 doi 10.1016/j.jisa.2026.104419; Tian et al. IJACSA 2025 doi 10.14569/ijacsa.2025.0160450; Belcaid, Zbakh Future Internet 2025 doi 10.3390/fi17040149; Zhang, Li 2026 doi 10.1007/978-981-95-7027-0_9; Tamai, Kasahara 2024 doi 10.3389/fbloc.2024.1405516; Bhaskar, Farshim CSF 2026 doi 10.1109/csf68417.2026.00029; Ivanov et al. arXiv:2301.08806; Moradi et al. arXiv:2510.14151 | as given | SNIPPET | Neighbours of cross-chain trust and capture | P2 |
| C15 | Known by name only, never opened: OmniLedger, RapidChain, Elastico, Polkadot, IBC specification, Hyperledger Cactus. Hyperledger Fabric docs "Policies" (release-2.5) was OPENED: its default 'MAJORITY Admins' policy is the global-majority admission baseline | -- | NOT VERIFIED | Standard sharding / cross-chain baselines | P1 |

## Section D - Candidate D (case-scoped emergency tickets) - task T4/T8

| ID | Citation | Identifier | Prior | Claim relied on | Pri |
|---|---|---|---|---|---|
| D01 | Al Amin, Shah, Tummala, Ray (title: check), SECRYPT 2025 | doi 10.5220/0013527000003979 | OPENED | **Closest threat.** Emergency duty-doctor access; approval by the "senior in charge" via multi-signature; patient/emergency contact notified; immutable audit on a private blockchain; "Proof of Compliance" consensus; single institution; detection left as future work | P0 |
| D02 | Rajput, Li, Ahvanooey, Masood, "EACMS: Emergency Access Control Management System for Personal Health Record Based on Blockchain", IEEE Access 7 (2019) | doi 10.1109/ACCESS.2019.2917976 | OPENED | Patient-defined emergency conditions and duration on Fabric (also cited by JANUS as [13]) | P0 |
| D03 | de Oliveira et al., Annals of Telecommunications 2020 | doi 10.1007/s12243-020-00759-2 | OPENED | CP-ABE break-glass scoped to the care period with a formal analysis; single cloud | P0 |
| D04 | Saberi et al., "ABAC break-glass on blockchain", IEEE ICDH 2021 | doi 10.1109/ICDH52753.2021.00041 | OPENED (G37) / SNIPPET (G1) - conflicting; check | Break-glass on blockchain with patient preferences | P1 |
| D05 | Muslim, Gregoire | arXiv:2603.07004 | OPENED | (check what it covers) | P2 |
| D06 | Guo et al., IEEE ICBC 2020 | doi 10.1109/icbc48266.2020.9169395 | OPENED | (check) | P2 |
| D07 | Wu et al., ICCCS 2024 | doi 10.1109/icccs61882.2024.10602797 | OPENED | (check) | P2 |
| D08 | Noble, Longstaff, JEIS 2026 | doi 10.30564/jeis.v8i2.13211 | OPENED | (check) | P2 |
| D09 | Syta et al., "Keeping Authorities 'Honest or Bust' with Decentralized Witness Cosigning" (CoSi) | arXiv:1503.08768 | OPENED | Witness cosigning as the k-of-n attestation primitive | P1 |
| D10 | Chen, Malin, "Detection of Anomalous Insiders in Collaborative Environments via Relational Analysis of Access Logs" (CADS), IEEE TDSC 2012 | doi 10.1109/tdsc.2012.11 | OPENED | EHR access-log anomaly detection | P2 |
| D11 | Boxwala et al., JAMIA 2011 | doi 10.1136/amiajnl-2011-000217 | OPENED | Insider detection via access-log modelling | P2 |
| D12 | Fabbri, LeFevre, "Explanation-Based Auditing", PVLDB 2011 | doi 10.14778/2047485.2047486; arXiv:1109.6880 | OPENED | Explanation-based auditing of EHR accesses | P2 |
| D13 | Llamas et al., ICDCSW 2025 | doi 10.1109/icdcsw63273.2025.00015 | OPENED | Federated EHR access anomaly detection on real hospital logs | P1 |
| D14 | Senturk et al., IEEE BigData 2025 | doi 10.1109/bigdata66926.2025.11400768 | OPENED | (check) | P2 |
| D15 | arXiv:2604.09630 (title: check) | arXiv | OPENED | (check) | P2 |
| D16 | Hurst, TechRxiv 2022 | doi 10.36227/techrxiv.19575229 | OPENED (Crossref abstract) | Supervised ML insider threats on EHR | P2 |
| D17 | Herrera Montano et al., SSRN 2026 | doi 10.2139/ssrn.6875799 | OPENED (Crossref abstract; page 403) | Real EMR audit log of 1.0M events; are labels / is it public? | P2 |
| D18 | Niu et al., IEEE JBHI 2025 | doi 10.1109/JBHI.2025.3527752 | OPENED | (check) | P2 |
| D19 | Saint-Hilaire et al., SECRYPT 2026 | doi 10.5220/0015169500004103 | OPENED | Process-mining insider playbooks (not EHR) | P2 |
| D20 | Snippet-only (open if cheap): Brucker, Petritsch SACMAT 2009; Petritsch 2014; Ferreira ACSAC 2009 and ICISSP 2016; Povey 1999; Rissanen 2006; Georgakakis 2011; Padhya 2019; Saberi Procedia CS 2021; Rodrigues arXiv:2307.01175; Chen, Malin CODASPY 2011; Malin JBI 2011; Kamra VLDBJ 2007; FedAT arXiv:2409.13083; ICBAC arXiv:2602.08014; Wagner, Soto CCS 2002; Goyal NDSS 2023; Bagdasaryan arXiv:1807.00459; Blanchard arXiv:1703.02757; Walonoski et al., Synthea, JAMIA 2018; Attipoe JMIR 2022; Yang et al. LiBAC 2017; Stark, "Misuse of break-the-glass policies in hospitals" (IGI 2021, doi 10.4018/978-1-7998-8954-0.ch058) | as given | SNIPPET | Break-the-glass and insider-detection background | P2 |

## Section E - The authors' group and citers of HMBC2020/JANUS (task T6/T8)

| ID | Citation | Identifier | Prior | Claim relied on | Pri |
|---|---|---|---|---|---|
| E01 | Malamas, PhD thesis, University of Piraeus (June 2024) | repository handle unipi/16570 | OPENED (full text, by agent C) | Chapters: HMBAC/Janus, SSI-based IoMT device authentication, ERP integration; **no** PQ/MPC/DP/consent/break-glass/unlinkable logs/BFT; future work: ML for predictive access control, trusted hardware, cross-chain bridges | P0 |
| E02 | Fotopoulos, Malamas, Dasaklis, Kotzanikolaou, "Blockchain-enabled Architecture for IoMT Device Authentication", ECICE 2020 | doi 10.1109/ECICE50847.2020.9301913 | OPENED | The group already did device authentication (SSI+ZKP+blockchain) | P1 |
| E03 | Malamas, Kotzanikolaou et al., "HA-CAAP", IEEE IoT-J 2025 | doi 10.1109/JIOT.2025.3530775 | OPENED | PUF-based continuous authentication + attestation on a blockchain | P1 |
| E04 | Malamas, Koutras, Kotzanikolaou, "Uninterrupted Trust", SEEDA-CECNSM 2023 | doi 10.1109/SEEDA-CECNSM61561.2023.10470549 | OPENED | PUF continuous authentication, supply chain | P2 |
| E05 | Malamas et al., "Blockchain Service Layer ... ERP", CoDIT 2023 | doi 10.1109/CoDIT58514.2023.10284288 | OPENED | Supply-chain port of the HMBAC idea | P2 |
| E06 | Malamas et al., "Granular traceability in multi-firm supply chains via tokenization", Logistics 2026 | doi 10.3390/logistics10070152 | OPENED | Group moving to supply chain / tokenisation | P2 |
| E07 | Yuan et al., B-SSMD, Security and Communication Networks 2022 | doi 10.1155/2022/2719951 | OPENED | Three-chain medical model | P2 |
| E08 | Emon et al., Annals of Emerging Technologies in Computing 2022 | doi 10.33166/aetic.2022.04.005 | OPENED | Hierarchical blockchain in edge computing | P2 |
| E09 | Li et al., BA-MA-ABE dual-blockchain + IPFS, CSCWD 2023 | doi 10.1109/CSCWD57460.2023.10152751 | OPENED | Dual-chain MA-ABE; cites HMBC | P1 |
| E10 | Citers with no abstract (open them): "A novel two-level secure access control approach for blockchain platform in healthcare", IJIS 2023 doi 10.1007/s10207-023-00664-4; "Privacy-First Healthcare", Procedia CS 2026 doi 10.1016/j.procs.2026.06.102 | as given | SNIPPET | May touch Candidates B/D | P1 |
| E11 | Counts to confirm: Google Scholar citers of R01 (82 seen via one cached card), OpenAlex (58), Semantic Scholar (46 enumerated); R02 citers: 7-8 | -- | -- | Completeness of the pre-emption sweep | P1 |

## Section F - Venues (task T7)

See `context/reports/R2_venues.md` for the full table; verify at least: ARES 2027 workshop **SPETViD** (topics claimed to include DP, blockchain data integrity, secure MPC, PPML for healthcare); **IWPE** at IEEE EuroS&P 2027 (Madrid, 5-9 Jul 2027); **SECRYPT 2027** (Rome, 20-22 Jul 2027; deadlines 16 Feb, 25 Mar, 13 May 2027 reported as VERIFIED); **DPM** and **CBT** at ESORICS 2027; IEEE CSR 2027; AsiaJCIS 2027 (deadline 16 Apr 2027, tentative); WPES at CCS 2027 (Atlanta, 11-15 Oct 2027). Unreadable to the LEAD: IEEE ICBC (HTTP 418), ACM CODASPY, ACM SACMAT, TrustCom/DAPPS/BCCA, HealthCom/ICHI, ICDCN.

## Section G - ADDENDUM from the LEAD's adversarial agent (final report: `context/reports/R2_adversary.md`; added 2026-10-04)
New threats and background found after the lists above were written. Statuses are the adversary's. Verify per T1/T2/T8.

| ID | Citation | Identifier | Prior | Claim relied on / why it matters | Pri |
|---|---|---|---|---|---|
| G01 | H. K., Madhumala R. B., "Hybrid-TPR-ABE: a Blockchain-Enabled Verifiable Framework with Differential Privacy for Secure Healthcare IoT Analytics", IEEE ICIICS 2026 | doi 10.1109/ICIICS67880.2026.11483552 | OPENED (abstract only; paywalled) | **Threat #2.** "decentralized ABE and threshold proxy re-encryption ... DP layer at the edge/fog with on-chain privacy-budget accounting ... private Ethereum PoA". Open the FULL TEXT: what is the accounting granularity (per dataset / user / patient)? Is anything multi-custodian? | P0 |
| G02 | Qiu, Li, Kong, "A dual-guarantee approach for cross-departmental government data sharing with usable-but-invisible privacy based on privacy computing and blockchain", Proc. SPIE (OECE 2026) | doi 10.1117/12.3123765 | OPENED (abstract) | **Threat #3.** MPC + DP joint statistics across three departments; blockchain attribute authentication + audit; "total privacy budget less than 0.8" (estimated, not ledger-enforced). Open full text if available | P0 |
| G03 | Wu, Wang, Ning, Zhu, "Privacy-Preserved Electronic Medical Record Exchanging and Sharing: A Blockchain-Based Smart Healthcare System", IEEE JBHI 26(5), 2022 | doi 10.1109/JBHI.2021.3123643 | OPENED (abstract) | Blockchain dynamic access control + local DP budgets + statistics for EMR | P1 |
| G04 | Cui, Chen, "Research on Fine-grained Security Sharing Model of Medical Information Based on Blockchain", IEEE ICPADS 2023 | doi 10.1109/ICPADS60453.2023.00400 | OPENED (abstract) | Multi-authority ABAC + LDP budgets + consortium chain | P1 |
| G05 | Haque et al., "A novel secure and distributed architecture for privacy-preserving healthcare system", J. Netw. Comput. Appl. 2023 | doi 10.1016/j.jnca.2023.103696 | SNIPPET | Unknown - open it | P1 |
| G06 | Zhang, Tsai, Tian, Zhao, Yu, Xiao, "DPNM: A Differential Private Notary Mechanism for Privacy Preservation in Cross-Chain Transactions", IEEE TIFS 2025 | doi 10.1109/TIFS.2025.3527357 | OPENED (abstract) | DP + privacy-budget allocation at a cross-chain notary (HMBC's Inter-BC API is a notary) | P1 |
| G07 | Passerat-Palmbach, Wadhwa, "Differentially Private aggregate hints in mev-share" | arXiv:2508.14284 | OPENED (abstract) | DP hints, trusted curator, Sybil sampling; low relevance | P2 |
| G08 | Ouyang, Lyu, Long, "A Blockchain-Based Continuous Query Differential Privacy Algorithm", LNCS 2022 | doi 10.1007/978-3-030-96772-7_57 | SNIPPET | Probably Zhao-style budget tracking for continuous queries | P2 |
| G09 | Denning, Denning, Schwartz, "The Tracker: A Threat to Statistical Database Security", ACM TODS 4(1), 1979 | doi 10.1145/320064.320069 | SNIPPET | Differencing / tracker attack is classical: our "hospital-subset differencing" must be attributed to this line, not claimed as new | P0 |
| G10 | Chin, Ozsoyoglu, "Auditing and Inference Control in Statistical Databases", IEEE TSE 1982 | doi 10.1109/tse.1982.236161 | SNIPPET | Query auditing over a user's history | P1 |
| G11 | Dinur, Nissim, "Revealing information while preserving privacy", PODS 2003 | doi 10.1145/773153.773173 | SNIPPET | Reconstruction from many noisy aggregates | P1 |
| G12 | Kenthapadi, Mishra, Nissim, "Simulatable auditing", PODS 2005 | doi 10.1145/1065167.1065183 | SNIPPET | Auditing denials leak | P1 |
| G13 | Vinterbo, Sarwate, Boxwala, "Protecting count queries in study design", JAMIA 19(5), 2012 | doi 10.1136/amiajnl-2011-000459 | OPENED (abstract) | Per-user, role-based DP budget for clinical count queries (single institution, trusted admin) - a 2012 idea | P0 |
| G14 | Raisaro, Tramer, Ji, et al., "Addressing Beacon re-identification attacks: quantification and mitigation of privacy risks", JAMIA 24(4), 2017 | doi 10.1093/jamia/ocw167 | OPENED (abstract) | Multi-site health network; per-user per-genome access budgets (non-DP) | P0 |
| G15 | Murphy et al., "Strategies for maintaining patient privacy in i2b2", JAMIA 2011 | doi 10.1136/amiajnl-2011-000316 | OPENED (abstract) | Obfuscated counts / privacy categories (background) | P2 |
| G16 | Big Bird, Limitations section (full text) | arXiv:2506.05290 | OPENED | Says Sybil control "could require API invokers to register with trusted authorities" - **verify this exact sentence**: it is the hook that distinguishes our multi-authority, possibly-corrupt-CA setting | P0 |
| G17 | Zhu, Zuo, Sun, "EHRAuditChain: Scalable Privacy-Preserving EHR Audit with RSA Accumulators on Blockchain", SSRN 2025 | doi 10.2139/ssrn.5495652 | SNIPPET (abstract unavailable anywhere) | Same as B14 - the item that could kill Candidate B | P0 |
