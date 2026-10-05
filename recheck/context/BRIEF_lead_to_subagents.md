# BRIEF — extend the HMBC (IEEE Access 2020) paper in a direction JANUS did NOT take

Written 2026-10-04 by the lead agent after reading BOTH papers in full. Everything marked (seed) is a hypothesis to be verified, not a fact.

## 0. Mission and hard constraints

Course: "Research in Information Security" (IIIT Hyderabad, grad level). A student team must deliver a project that can end up as a **workshop-paper-grade** contribution extending **[HMBC2020]**:
Malamas, Kotzanikolaou, Dasaklis, Burmester, "A Hierarchical Multi Blockchain for Fine Grained Access to Medical Data", IEEE Access 8 (2020) 134393-134412.

The extension must be:
1. **Novel** - verifiably not already done in the literature (this is the thing we are most worried about).
2. **In a different direction from JANUS** (the same group's 2023 follow-up, Applied Sciences 13(1):566) AND from the directions we already tried and judged non-novel (section 4). Extending JANUS's mechanism = FAIL.
3. Squarely **information security** (course syllabus in section 5; neighbours are OK if clearly security).
4. **Proof-of-concept scale**: runs on 2-4 ordinary student laptops (about 14 GB RAM, 16 threads, NO GPU, no cloud/servers, Docker allowed but heavy Kubernetes stacks are not). No real hospital, no real patient data (synthetic only).
5. Evaluable: some mix of security argument/formal analysis (ROR-model proof, ProVerif/Scyther/Tamarin, game-based proof, or attack/adversary analysis) AND measurements (cost tables, latency, scalability).

## 1. Files on disk (use the Read tool with `pages` for PDFs, max 20 pages per call)

- PLAIN-TEXT COPIES (use these instead of the PDFs; cheaper and greppable): /tmp/claude-1000/-home-saiyamjain-Desktop-RIS-Project/7f3768f5-bcf0-4be7-b767-eed844b23403/scratchpad/papers/hmbc2020.txt and .../papers/janus2023.txt (read with Read + offset/limit, or grep -n). Only open the PDF pages if a figure is needed.
- Original paper: /home/saiyamjain/Desktop/RIS/Project/A_Hierarchical_Multi_Blockchain_for_Fine_Grained_Access_to_Medical_Data.pdf (20 pp)
- JANUS paper:    /home/saiyamjain/Desktop/RIS/Project/JANUS.pdf (27 pp)
- Syllabus:       /home/saiyamjain/Desktop/RIS/Project/Course_Content.md
- JANUS code:     /home/saiyamjain/Desktop/RIS/Project/janus-repo/ (Hyperledger Fabric chaincodes in blockchain/chaincodes, APIs in blockchain/blockchain_apis, database_api/, configs/) and /home/saiyamjain/Desktop/RIS/Project/vault-secrets-abe-janus/ (Go HashiCorp-Vault ABE plugin)
- Earlier planning docs (all about hardening JANUS crypto; read only if you need them): LITERATURE_REVIEW.md, PROJECT_IDEAS.md, PROPOSAL_REVISED.md, VERIFICATION.md, problems.md in /home/saiyamjain/Desktop/RIS/Project/. Papers/ holds 4 PDFs (Lewko-Waters 2011, Green-Hohenberger-Waters 2011, BMHADS 2026 PLOS One, Du et al. 2024).
- Report directory for subagent outputs: /tmp/claude-1000/-home-saiyamjain-Desktop-RIS-Project/7f3768f5-bcf0-4be7-b767-eed844b23403/scratchpad/reports/

## 2. [HMBC2020] in one page (verified by lead from the PDF)

Architecture (Fig. 1, Sec. III-B). User layer API -> **Proxy Blockchain (PBC)**, run by ALL stakeholders (hospitals, device manufacturers, insurers...), single entry point + global ledger -> **Domain Blockchains (DBC)**, one per domain, run by that domain's stakeholders -> **Data layer**: each stakeholder keeps its own off-chain DB of data encrypted by itself with MA-CP-ABE (Lewko-Waters 2011, Python Charm). Every stakeholder runs 2 nodes (one PBC, one DBC). Consensus: Proof of Stake, two independent Ethereum-based private chains. Docker+Kubernetes isolation; an **Inter-blockchain API** (middleware in "Docker 1") routes and throttles PBC->DBC requests with a cache DB (Figs. 7-8, Sec. IV-A/B). Six Solidity smart contracts, tested only on ganache-cli/truffle on one Ryzen box.

PBC contracts: **TMSC** (trust management: updateTrustAnchors, addCA/removeCA, getUserValidation), **RSC** (user/device registration -> unique global ID GID = Ethereum address, links GID<->certificate, logged), **PSC** (proxy: validate user, forward request), **LSC** (logging: every request, update, registration, retrieval is logged globally; retrieveLog needs majorityConsent of authorities). DBC contracts: **ACSC** (enforces inter-/intra-domain policy on verified attributes), **KSSC** (key store: holds the *temporal-role* ABE keys; partially decrypts, user finishes with long-term keys).

Trust model (Sec. III-C5, III-D1). NO global root CA. Each stakeholder X is its own CA + ABE key authority. Root certs CERT_X, revocation lists CRL_X and **TempACL_X** (signed temporal-access list: entries = (GID, temporal role e.g. onDuty, from, to)) are stored as linked, indexed blocks on the PBC. Adding/removing a stakeholder needs a threshold of CA-Admin signatures (majorityConsent). Long-term roles live in certificates; temporal roles live in TempACL and unlock ABE keys that are NEVER given to users (held in KSSC) -> two-step distributed decryption -> claimed "efficient revocation".

Access flow (Fig. 6). user -> PSC (LSC logs the request; TMSC validates cert + TempACL) -> Inter-BC API -> Domain ACSC (policy check on verified attributes) -> KSSC (fetch ciphertext, partial decrypt with temporal key) -> back through PBC -> user finishes decryption. Every step logged ("forensics-by-design").

Example policies (Sec. III-C4). Rule 1: doctor at hospital X who is treating patient beta may read beta's record. Rule 2 ("emergency"): a doctor with isDoctorAtHospital(*) AND onDuty(*) may read patient records under emergency treatment - formalised as `X.allow(alpha, MHR(beta)), forall MHR(beta) in DB_X`. Intro (Sec. I-B) explicitly rejects patient manual approval in emergencies as impractical.

Claims (Sec. I-A, V): decentralized interoperable adaptable trust mgmt, fine-grained + temporal + revocable access, privacy-preserving encryption, tailored forensics (global transaction verifiability, detectable policy modification, collusion resistance with honest majority), scalability, 603 ms per access at 100 concurrent requests. Table 1 claims "all types of queries" as data search scheme.

Assumptions (Sec. V-A1). Isolation holds; honest MAJORITY inside each DBC and (by the authors' argument) the PBC; primitives secure; ABE keys uncompromised; PPT adversary. Security discussion is informal.

Authors' own stated future work (Sec. VI): other consensus mechanisms per layer, larger-scale PoC, large objects via hybrid encryption, intra-blockchain communication / consensus consolidation / Docker orchestration.

## 3. JANUS - what it already did (EXCLUSION ZONE 1; verified by lead from the PDF)

Malamas, Palaiologos, Kotzanikolaou, Burmester, Glynos, "Janus: Hierarchical Multi-Blockchain-Based Access Control (HMBAC) for Multi-Authority and Multi-Domain Environments", Appl. Sci. 2023, 13(1), 566.
- Full implementation on **Hyperledger Fabric 2.4 + Raft**, chaincodes in JavaScript, Kubernetes pods, Electron/React client, Fabric CA per stakeholder, RabbitMQ.
- A **formal HMBAC access model** (sets U, Au, S, K, D; AVF / AF / DF functions, IDP/CDP policies).
- Moves the single-point-of-access enforcement into cryptography: extra AND clause on a **domain attribute key** held only by the KSSC in a **HashiCorp Vault** (custom Go ABE plugin); KSSC generates K_{U,domain} on the fly for the requester's GID and partially decrypts. Replaces the 2020 paper's "temporal keys stored in a contract".
- **Inter-BC API** with request queues + congestion-level throttling (5 congestion types) to avoid PBC overload/DoS.
- **Voting/election governance** on the PSC: add/remove domains/stakeholders, change cross-domain policy, grant auditors access to logs (majorityConsentInit/Vote/updateElection; retrieveLogInit/retrieveLogs).
- Two-factor frontend auth with attribute certificates; hybrid encryption (AES data key wrapped by MA-ABE).
- **Attack-tree security analysis** of unauthorized data access (5 cases, 3 propositions) + secure blockchain mgmt / key storage discussion.
- Benchmarks on Linode K8s (32c/64GB and 64c/512GB), 2-300 concurrent requests, linear scaling.
- JANUS's own future work: BFT consensus; inefficient external credential management.

## 4. Directions we already tried for JANUS and judged NON-NOVEL / out-of-bounds (EXCLUSION ZONE 2)

Do NOT propose these as the main contribution: threshold / DKG / proactive-secret-shared gatekeeper (domain/system) key; capability-token-bound partial decryption; verifiable outsourced/partial decryption; a formal security definition of "authorization -> transform" (HMBAC enforced decryption); Type-3 curve / parameter migration of Lewko-Waters; aggregate-signature voting; Raft->SmartBFT; Vault-ACL / sysdecrypt-bypass findings; generic "break-and-fix JANUS". Prior-art already identified there: BMHADS (PLOS One 2026), BDAE 2024, TMACS, Green-Hohenberger-Waters 2011, Lai et al. 2013, mediated/server-aided ABE.
Prior ideas that were only LIGHTLY explored (may be reconsidered but need fresh, rigorous novelty grounding, and must be anchored to the ORIGINAL paper's mechanisms, not JANUS's): privacy-preserving global audit (ZK) + ML misuse detection; post-quantum hardening; IoMT device-side authentication.

## 5. Course syllabus (Course_Content.md)

Digital signatures and variants (proxy, multi-, aggregate) and their IoT applications; key management in hierarchical access control; key mgmt / user authentication / access control in WSN & IoT; security in IoV; intrusion detection; blockchain security & privacy; AI/ML security; post-quantum cryptographic protocols; multiparty computation (MPC); quantum cryptography / QKD / teleportation. Things outside this list are allowed if clearly information security. The instructors appear to like: authentication/key-agreement protocols with Real-or-Random (ROR) proofs + ProVerif/AVISPA/Scyther verification + computation/communication cost comparison tables.

## 6. Seed gaps in HMBC2020 that JANUS (apparently) did not close - TO BE VERIFIED, with citations

(a) **Log/metadata privacy and identity linkability.** LSC logs every request (GID, data_id/target, DBC, time) on the PBC replicated at ALL stakeholders incl. insurers and manufacturers (Sec. III-D4, Fig. 6, Sec. V-A5). RSC logs the GID<->certificate link (Sec. III-D2), and the multi-authority GID links all of a user's identities. Only record CONTENT is protected, not who-accessed-what-when. (Du et al. 2024 states the log-privacy problem generically.)
(b) **Emergency (onDuty) access is coarse and only post-hoc audited.** Rule 2 grants attribute-level not patient-level scope; no preventive scoping to a declared emergency case, no patient notification/consent, no abuse detection - only forensic logs after the fact.
(c) **Insider misuse detection on the global log** - the log exists, but nobody analyses it (IDS/ML syllabus items).
(d) **Temporal-role/revocation freshness.** TempACL/CRL are signed lists published to the PBC and checked at the PBC, enforced later at a different chain (time-of-check vs time-of-use) with a cache DB between; no analysis of revocation propagation delay or of list growth.
(e) **Cross-chain trust.** PBC->DBC messages travel through the Inter-blockchain API, a single non-blockchain middleware; the DBC accepts "verified attributes" from it without any proof; PBC learns the DBC response only through it. The paper contrasts itself with Notary schemes but the API is effectively a notary.
(f) **Honest-majority assumption conflates PBC and DBC.** Domain chains are formed by organisation TYPE (not random assignment as in sharding), so a small domain (e.g., manufacturers) can be captured cheaply and its ACSC/KSSC policy changed; the paper claims only that this is *detectable*. No quantitative analysis of capture probability / stake distribution.
(g) **Data layer**: no binding of off-chain ciphertext to the chain (integrity, rollback, substitution), no erasure (GDPR is cited as motivation), no search despite the "all types of queries" claim, no patient role at all.
(h) **Statistical access across domains.** Researchers/insurers are meant to get *statistical* data across several hospitals; the architecture has nothing for computing or limiting statistical outputs (re-identification, cumulative disclosure across independent authorities). The PBC single-entry-point + immutable global log is a natural place to enforce a cumulative budget - hypothesis only. (MPC and differential privacy.)
(i) **Devices as principals**: devices register (RSC) and manufacturers push firmware (Sec. III-F-1) with PBC logging, but there is no constrained-device protocol, no update authenticity/rollback story, no vigilance evidence format.
(j) **Crypto agility / post-quantum**: ECC certificates + pairing-based ABE; nothing PQ.
(k) **No formal protocol analysis** of registration / request flows (no ROR / ProVerif / Scyther).

## 7. Grounding rules (apply to every agent)

- Today is 2026-10-04. Your training data is older; SEARCH for 2023-2026 work (arXiv, IACR ePrint, IEEE Xplore, ACM DL, Springer, Elsevier, MDPI, DBLP, Semantic Scholar, OpenAlex, Google Scholar, GitHub, vendor docs/blogs, Hyperledger/Ethereum docs, standards bodies). Use WebSearch (mode "standard" first; "extended" when a result is thin or the topic is niche/recent) and WebFetch to OPEN abstracts/PDFs.
- Run MANY distinct queries (>= 20 per assigned topic), with synonym variants, both "blockchain" and non-blockchain framings (e.g., EHR access control literature in general), and "hierarchical / multi-chain / cross-chain / sidechain / consortium / proxy chain" variants.
- Every cited work gets: authors, title, venue, year, DOI/URL, and a status: **OPENED** (you read the abstract or text via WebFetch/Read) or **SNIPPET** (only seen in search results). NEVER invent or "recall" a citation; if you cannot verify it, say so. Do not paper over uncertainty - "I could not find it" and "found a close one" are both valuable outputs.
- For overlap claims, quote or closely paraphrase the sentence in the source that establishes the overlap.
- Be adversarial toward our own ideas: your job is to find the paper that makes our idea unpublishable, not to be encouraging.
- LOCAL MACHINE RULES: this is a student laptop that has OOM-crashed before. Do ONLY light work: reading, web search/fetch, grep, small text extraction. NO installing packages, NO docker, NO builds, NO benchmarks, NO long-running or parallel local processes. Write files ONLY inside the reports directory above. Do not modify anything else.
- Final answer: write the full report to the reports directory (name given in your task) and return a SHORT summary (<= 400 words) with the path, the verdict(s), and the 3-5 most important citations.
- EFFORT AND ROBUSTNESS (important - a previous run died on a usage limit): budget roughly 25-40 searches/fetches in total, then stop and conclude; do not exhaustively chase every lead. CREATE your report file EARLY (after your first findings) and APPEND to it as you go, so partial work survives an API/rate-limit error. If you get a rate-limit/API error, immediately save what you have to the report file and stop. Keep the report tight (tables over prose; <= ~2,500 words).

## 8. UPDATE (2026-10-04, after batch 1) - READ THIS

- **WebSearch IS EXHAUSTED for this session (200/200). Do NOT call WebSearch.** Search through WebFetch against open APIs instead (this worked for earlier agents):
  - arXiv: `http://export.arxiv.org/api/query?search_query=all:%22access+control%22+AND+all:blockchain&max_results=20` (Atom XML)
  - Semantic Scholar: `https://api.semanticscholar.org/graph/v1/paper/search?query=<terms>&fields=title,year,venue,abstract,externalIds,url,citationCount&limit=20` (unauthenticated, rate-limited: space requests out, retry on 429)
  - OpenAlex: `https://api.openalex.org/works?search=<terms>&per-page=25&select=id,title,publication_year,doi,primary_location`
  - Crossref: `https://api.crossref.org/works?query=<terms>&rows=20&select=title,author,issued,container-title,DOI,URL`
  - IACR ePrint: `https://eprint.iacr.org/search?q=<terms>` ; DBLP is blocked. Google Scholar / IEEE Xplore search pages generally do not work via WebFetch; DOI landing pages (https://doi.org/<doi>) and arXiv / MDPI / PLOS / Springer open-access pages usually do.
  - Verify a paper by fetching its abstract page or the arXiv/open-access PDF. Mark OPENED only if you read the abstract or text.
- Existing findings you can reuse (read the relevant section, do not redo the work):
  - /tmp/claude-1000/-home-saiyamjain-Desktop-RIS-Project/7f3768f5-bcf0-4be7-b767-eed844b23403/scratchpad/reports/A1_dissection.md  (paper+code audit; gap cards GC1-GC5; coverage matrix. Code-verified examples: JANUS stats endpoint returns raw per-hospital counts with no noise/threshold/budget; JANUS PSC logs invoker + certificates + data id in clear; governance: only the initiator's domain votes on adding a stakeholder, quorum is Math.round(n/2); "onDuty" in JANUS is a shift calendar, no incident scope.)
  - .../reports/G1_private_logging.md  (privacy-preserving logging: verdict NOVEL-NICHE for a threshold-opened "need-to-know" PBC log; closest prior art Harpocrates 2211.04741, PCTRS 2026, DTRAC 2022, ZK-EHR 2026, zkLedger, zkCross)
- Keep reports tight (<= ~2,500 words). Create the report file early and append as you go.
