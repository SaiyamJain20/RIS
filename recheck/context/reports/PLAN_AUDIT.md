# PLAN_WORKSHOP.md audit (local-only)

Auditor: PLAN-AUDITOR, 2026-10-04. No web access. Evidence = local files only: the plan, RECHECK_REFERENCES.md, both paper texts, the nine agent reports, janus-repo, plus (read-only) PROJECT_IDEAS.md, OPEN_QUESTIONS.md, RECHECK_COMMS.md and a local copy of the Big Bird text in this session's scratchpad (`bigbird.txt`). I recomputed the DP numbers myself (`scratchpad/chk.py`).

Severity: HIGH = changes a decision or a gate; MED = a reviewer or the lead will trip on it; LOW = polish.

Headline: 2 HIGH, 7 distinct MED (some listed in two sections), about 25 LOW. All 59 non-task IDs in the plan (plus G11 inside the range G10-G12) exist in RECHECK_REFERENCES.md. All [V] tags I could test hold, with 3 wording problems (G-3, G-4, G-7). The design numbers reproduce.

---

## 1. Reference IDs

Extracted: A01-A06, A08, A09, A11-A14, A16, A17, A23, A24, A32, A33; B01, B02, B04, B06, B07, B11, B14-B16, B26; C01-C03, C10-C12, C15; D01-D03, D09, D20; E01-E03; G01-G04, G06, G09, G10-G14, G16; R01-R04; task IDs T1, T6, T7, T9 (T2-T5, T8, T10 in text). No missing rows. Authors/title/venue/year/identifier of every row cited in Sections 6, 9 and 14 match the table, except:

| Check | Location | Finding | Sev | Fix |
|---|---|---|---|---|
| Author initial | S14 [A04]; refs row A04 | "F. Tholoniat" is wrong. The local Big Bird text (title page + ACM Reference Format) reads "Pierre Tholoniat, Alison Caulfield, ..., Martin Thomson". The refs row also has "K. Caulfield" (should be A.) and "J. Thomson" (should be M.). Venue SOSP '26 (Prague, 29 Sep-2 Oct 2026) and doi 10.1145/3830418.3843897 are correct. | LOW (but this is the paper to "cite prominently") | Write "P. Tholoniat et al."; fix the refs row too |
| Tag vs table | S9 B row, S14 [B15], [B16] tagged [O] | RECHECK_REFERENCES lists B15 ("SNIPPET (no abstract)") and B16 ("Unopened ... SNIPPET") as unopened. R2_adversary E8 says both were OPENED (B15 via OpenAlex inverted index, B16 via S2). C report Part 5 says B15's abstract was not retrievable. The plan follows the adversary; the table is stale or the sources conflict. | LOW | Update table rows B15/B16 to "OPENED by R2_adversary" and say how |
| Missing DOI | S14 [R03] "(DOI to find)" | The local PDF header gives it: Computers and Electrical Engineering 119 (2024) 109547, doi 10.1016/j.compeleceng.2024.109547. Authors Du, Dong, Ning, Xu, Yang. C report Part 3 already had this DOI. | LOW | Insert the DOI; remove it from "Known unknowns" |
| ID collision | S9 B row "[G-10]" | Same string pattern as reference ID [G10] (Chin-Ozsoyoglu). Section 5's row G-10 is meant. | LOW | Write "Sec. 5 row G-10" |
| Count | S1 "about 150 entries" | The table has 127 numbered rows (4 R + 33 A + 27 B + 15 C + 20 D + 11 E + 17 G). 150 holds only if the bundled rows (C14, D20, B26) are expanded. | LOW | Say "127 rows" |
| ID not in table | S14 arXiv ids for Bun-Steinke 1605.02065 and Canonne-Kamath-Steinke 2004.00010 | These come from the design report, not the refs table (A33 has no arXiv ids). Tagged [U]. Acceptable. | LOW | none |

---

## 2. [V]-tagged claims

| Claim | Location | Status | Evidence / correction |
|---|---|---|---|
| G-1 statistical access is a use case | S5 | CONFIRMED | hmbc2020.txt l.145 (I-A2, quote exact), l.640-641 (III-C6, quote exact), l.925, l.952 (III-F). Sections right. |
| G-2 quote "Allow insurance companies ... privacy of personal health records is preserved." | S5, S0, L1 | CONFIRMED | l.952-961. The quote spans a page break (l.961 "personal health records is preserved"); "line 952" is the start line. Wording exact. III-F-2 is right. |
| G-3 no DP/MPC/anonymisation/aggregation in HMBC | S5 | CONFIRMED, wording WRONG | With the stated pattern (`differential\|multiparty\|anonymi\|aggregat\|privacy budget\|k-anonym`) a case-sensitive grep finds 0 hits; with -i exactly 1 hit (l.1592, a proceedings title "Privacy Anonymity" in the reference list). "noise" is NOT in the pattern; the two "noise" hits (l.536, 538, ABE collusion) come from a different search. Fix: print the exact command (use `grep -niE`) and say "one reference-list title". LOW |
| G-4 JANUS: single hit line 530 | S5 | CONFIRMED, incomplete | `grep -niE` on the same pattern: one hit, l.530 ("access to anonymized data to researchers"). But l.121 also says the multi-authority doctor-researcher "would also require access to (statistical) health data maintained in all hospitals". So "it only mentions 'anonymized data' as an example policy" omits a second mention (and l.121 is direct support for the cross-authority identity story, G-7). LOW |
| G-5 stats endpoint, raw counts, no noise/budget; grep absence | S5, L3 | CONFIRMED with location correction | `disease_stats.py` is 45 lines and is only the fan-out (loop l.28, POST l.31-35, append l.37-41). The raw count is in `database_api/api/db_api/src/crud/clinics.py:175-201` (`number_of_cases`, optional `clinic_uuid`, free `start_date/end_date`). Reachable as `data_03` in `dbc_api/src/server.py:38-40`. `grep -rniE 'laplace\|gaussian\|epsilon\|differential\|k_anon\|suppress\|min_count\|budget' database_api blockchain/chaincodes` = 0 hits (I ran it). RECHECK_COMMS T9 reaches the same result. Add the clinics.py reference. LOW |
| G-6 every stakeholder runs a PBC node; PBC single entry + global log | S5, L4, S3 | CONFIRMED text | III-C-1 l.481-483 (quote exact), V-A5 l.1251-1253 (quote exact). "Non-bypassable" is the paper's assumption (V-A1 bullet 1: isolation is secure), not a verified property. LOW: say "assumed non-bypassable (V-A1)". |
| G-7 nothing verifies the person behind a second authority's certificate is the person behind the GID | S5 | PARTLY WRONG as phrased | RSC (III-D2, l.768-785): the user "will prove possession of the global identifier GID_A, which will be included in the new certificate cert_AY". That is key-possession, not person-binding, and it does not stop one person registering twice (two RSC registrations, two GIDs). The attack A3 survives, but the plan sentence will be read as ignoring l.779-781. IV-D (l.1105) correct. MED. Fix: "binds GIDs to keys, not persons; nothing prevents multiple registrations or a corrupt authority issuing certificates; cf. JANUS faq.md:94-104 (A1 N7)" |
| G-8 membership decided inside domain; honest-majority conflation | S5 | CONFIRMED | V-B1 l.1281-1283 and V-A1 l.1131-1134, quotes exact. |
| G-9 only initiator's domain votes; quorum Math.round(n/2) | S5, L5 (tagged [O]) | CONFIRMED locally (can upgrade) | tmsc.js:352-355 (same-domain check), :377-383 (`Election.createInstance("add_ca", initiatorOrgDomain, ...)`, stakeholders = initiator's domain); election.js:76-77. RECHECK_COMMS T9 adds a correction: n = number of OTHER non-revoked members, so n<=1 gives threshold 0. |
| G-10 PSC writes invoker, base64 certs, data id in clear | S5, S9 | CONFIRMED | psc.js:458-498 `requestAccess` builds `{txID, invoker, invocationTime, requestDetails:{certificates(base64), dataID}}` and sends to `LSC.requestLog` (lsc.js:78-100, stored via recordManager). "In clear" = base64, no encryption. Whether `dataID` identifies a patient (fallback B motivation "who-accessed-which-patient") is not shown by this code; A1 asserts it. |
| S3 HMBC summary (contracts, no root CA, quote III-C-1, GID = Ethereum address IV-D, ganache/truffle, Python-simulated ABE) | S3 | CONFIRMED | l.482-483; 592-600; 1105; 1077; "simulate the multi-authority ABE with a two-step decryption" l.977 (Charm library l.1103). |
| S3 JANUS summary (Fabric 2.4 + Raft, Vault ABE plugin, RabbitMQ congestion levels, voting, attack trees, 2-300 concurrent) | S3 | CONFIRMED | janus2023.txt l.1589, 954-960, 1159-1370, 1383-1388, 1903-1911, 1598. |
| HMBC "PoS finality is itself unclear (Sec. V-B3)" | S6 objections table [V] | Text CONFIRMED, "unclear" is an interpretation | l.1327-1333: "a transaction can be finalized before a block is verified by the stakeholders". The paper never discusses PoS finality guarantees. S7.10 then says "which HMBC's PoS ... does not guarantee" - stronger. LOW: pick one wording, tag as [V]+reading. |
| L1-L4 | S13 | CONFIRMED | see G-2, G-3/4, G-5, G-6. |
| L7 Big Bird Limitations "could require API invokers to register with trusted authorities" ([O], "T1 must verify") | S6, L7 | CONFIRMED verbatim (local copy) | scratchpad `bigbird.txt` l.1266-1267: "browsers could require API invokers to register with trusted authorities to limit Sybil domains". Context: offered as an API-governance measure "beyond budget management". Note "trusted authorities" is already plural. The copy is not in `recheck/context/papers/`, so by S1's own definition it is not [V] yet. LOW: copy the text into context/papers and quote the full sentence. |

---

## 3. Consistency with the agent reports

| Check | Location | Finding | Sev | Fix |
|---|---|---|---|---|
| 225 / 37 / 338 queries | S0, L15 | Reproduced (337.9 / 225.2 / 37.5; RECHECK_COMMS T10 got the same). They hold only for \|S\|=3, t=1, eps=2, delta=1e-6, a count of ~1000 with c=1, sigma=50 (z=2.0, not 1.96), the whole lifetime budget of a group spent on this one query type, shared by ALL analysts. S0 gives none of this. Cell-size dependence is severe (T10: 100 -> 2.3 queries, 200 -> 9, 1000 -> 225). | MED | State preconditions next to the numbers; add the cell-size row |
| 6x and 45x | S7.5, S11 R3, L15 | 6 = 3x2, 45 = 9x5: correct, and they are VARIANCE ratios. S12 Q1 uses 2.45x RMSE for the same 6x; R3 says "the 6x gap" without the word variance. | LOW | Write "6x variance (2.45x RMSE)" everywhere |
| G = 16, common ID | S7.5 | Matches design Sec. 4. | - | - |
| H1-H5 | S7.9 | Match design Sec. 7 except H1 drops "at 95%". | LOW | add |
| Gates G1-G3 | S8.2 | Match, except G1 FAIL says "< 15/30" where design says "< 15/30 at eps=4". | LOW | add "at eps=4" |
| Gate G2 / H5 threshold 0.9 | S7.9 H5, S8.2 G2 | NOT ATTAINABLE with the plan's own parameters. Using the design's MI formula adv = 2*Phi(mu/2)-1 and rho(eps) at delta=1e-6 (eps 1/2/4 -> rho 0.0175 / 0.0676 / 0.254): A1 on B1 with m<=3 sites: 0.25 at eps=2, 0.46 at eps=4, 0.13 at eps=1. A3 on B4 at eps=1/GID: k=200 gives 0.81 (0.9 needs k=309). A2 on B3' at eps=1, n=9: 0.87. Only A2 at n=9, eps=2 (0.997) clears 0.9. Gate G2 would fail by construction and send the team into "fix before W5" for nothing. (My calculation; ask T10 to confirm.) | HIGH | Redefine pass as "empirical advantage within +-0.03 of the analytic baseline curve mu=sqrt(2 m rho) / sqrt(2 k rho) / 2^(n-1) rho, and ours below the bound + 0.02", or raise k (>=310) / per-unit eps and say which attack reaches 0.9 |
| H1 (KILL, eps<=2) vs G1 (PASS eps<=4, pivot at eps=4) | S7.9 vs S8.2 | Two thresholds for the same event. At the default eps=2 (Q3) H1 is the stricter test, at which T10's cell table says a 30-query workload with cells of 100-5000 is unlikely to pass. Which one decides GO? | MED | Make H1 the same test as G1 or drop "KILL" |
| Laptop RAM | S7.10 | 2.6 / 1.8 / 1.8 (+2 TLC) and 512 MB heap match design Sec. 2. The design's 4th PBC validator (University U, V4) sits on L1; the plan's laptop list omits it (only V1-V3 appear). | LOW (see S5 row on placement) | add V4 to L1 |
| Adversary verdict | S0, S4, S6 | "SURVIVES ONLY IF REFRAMED", ~65%: matches R2_adversary (a). G2 had NOVEL-NICHE ~60%. | - | - |
| Three closest threats | S0, S6 | Adversary ranks: 1 Big Bird, 2 Hybrid-TPR-ABE, 3 Qiu et al. S0 risk list names only the first two; Qiu appears in S6/L10 but is never presented as threat #3. | LOW | list all three in S0 |
| Candidate scores | S4 | A 6/7/7/9/7 = G2 C2 row; B 6/7/7/8/7 = G1 C1 row; C 6/8/7/6/7 = G6 "C1 + M3/M4" row; D 6/7.5/7/8/6.5 = G37 recommended-PACKAGE row (C-I + C-II-lite + C-III), while the D pitch in S9 is C-I only (core row 6/8/7/7/6). Column order matches. | LOW | footnote that D is the package score |
| Venue dates (S10, S0) | vs R2_venues.md | All match: SPETViD 2026 = 18 May / 2027 inferred mid-May; IWPE 13 Feb ext. 26 Feb, 8 pp / 4 pp, archival or not; SECRYPT 16 Feb, 25 Mar, 13 May verified; DPM/CBT 1 Jul; AsiaJCIS 16 Apr tentative. Two softenings are missing: (a) report says SPETViD is "primary target IF IT REPEATS" (2027 edition not announced); (b) DPM "Springer LNCS" is "in prior editions, not confirmed for 2026". | LOW | add both caveats |
| Pre-emption statements (S9) | vs C report | Match: no extension of HMBC/JANUS found; group on device authN (ECICE 2020, thesis ch.7, HA-CAAP 2025) and supply chain; repo dormant (last commit 28 Jun 2022); thesis future work = ML predictive access control, trusted hardware, bridges. Coverage "46 of ~82": the 82 is ONE cached Google Scholar card; OpenAlex says 58, so the un-enumerated share may be 12, not 36. | LOW | give 58/82 range |
| Capture numbers (S7.8) | vs G6 + G6_calc.py | Script runs in 0.02 s and prints 1 org (JANUS quorum) / 2 (strict) for the smallest domain; ~24-26 shams. They assume an invented 28-org registry (20 hospitals, 3 manufacturers, 3 insurers, 2 labs), smallest domain n=2; T9 adds that n counts other members. | LOW | state the 28-org assumption |
| Effort | S8.4, S9 | "9-11 person-weeks [U, design agent]": the design report contains no effort estimate; the figure is G2's. The listed breakdown (2 + 2-3 + 1-2 + 2 + 2 + 1-2) sums to 10-13, not 9-11. B (11 = 2+2.5+2+1.5+1+2), D (~10), C (4-5.5) match their reports. "Paper floor 6-7 pw" has no source. | LOW | cite G2; fix the sum; tag paper floor [U] |
| "Twelve agents ... eight directions" | S4 | Matches HANDOFF (12 agents lost) and C report map (G1-G8). | - | - |

---

## 4. Overclaims and untagged assurances

| # | Location | Sentence | Problem | Sev | Fix |
|---|---|---|---|---|---|
| O1 | S0 "Why this is not JANUS's direction" | "JANUS ... has **no** statistics/DP/MPC mechanism (grep-verified)" | Contradicts S5 G-5 / L3: JANUS code ships a statistics endpoint; the paper also lists "(statistical) health data" as a use case. What is absent is any disclosure control (noise/DP/budget/MPC). | MED | "no disclosure-control mechanism for statistics (no DP/MPC/noise/budget)" |
| O2 | S0 risks | "~225 useful queries in linked mode vs ~37 unlinked" | Presented without eps, \|S\|, t, cell size, "useful" definition. Quoted out of context it reads as a general utility figure. | MED | see S3 row |
| O3 | S6 "What the adversary could not kill" / S0 "about 65%" | Absence claim and a probability with no tag in S0/S4/S6 (L13 does tag [U]). Search was API-only, Elsevier journals by title only (R2_adversary coverage caveat). | LOW | tag [U] at each use |
| O4 | S6 item 3 | Framing "MPC + DP joint statistics ... blockchain audit and a total budget" is labelled DEAD citing Qiu (abstract only), PriCollabAnalysis (no DP/budget in the text), Enigma (no DP), Shrinkwrap/Drynx (no ledger budget). The kill rests on one abstract of a low-tier proceeding. | LOW | say "closest: Qiu [abstract]; the others cover parts" |
| O5 | S9 B row; S0 "hinges on one unread paper" | G1 kill criteria name three unread items (EHRAuditChain B14, Jiang BSCI'25 B17, Zhang JSA'23 B18) plus memory leads (Waters 2004, Frankle 2018, SAMPL; B26). B17 is P0 in the refs table. | MED | "hinges on EHRAuditChain, B17, B18 and unverified leads" |
| O6 | S9 / S3 "generic ML insider detection (... the authors' stated future work)" | Thesis future work is "ML for predictive access control", not insider detection (C report Part 2a). | LOW | reword |
| O7 | S5 G-6 | "non-bypassable" is an assumption in the paper (see S2). | LOW | reword |
| O8 | S7.10 "HMBC's PoS ... does not guarantee" | See S2: interpretation. | LOW | reword |
| O9 | S3/S5 "[V]" definition | [V] requires a local file under `recheck/context/papers/` or `janus-repo/`; L7 relies on a scratchpad copy. | LOW | move file |

No "verified" without a tag found in Sections 6-14. The SECRYPT "verified" dates are the report's VERIFIED tag (page read), consistent.

---

## 5. Internal consistency

| # | Location | Contradiction | Sev | Fix |
|---|---|---|---|---|
| I1 | S8.1 vs S8.3, S7.9 H4, G3 | Tiers vs deliverables. Paper floor (weeks 1-6, "needed for submission: yes") has BudgetLedger on Anvil, gas only. The promised cost-breakdown table (latency per step, bytes, PSI time), hypothesis H4 (median <= 10 s on Wi-Fi), gate G3 (4-validator Besu at W4) and the W6 row "Latency, gas, bytes; 9-site scaling" all need the Target-tier Besu network and PSI. W4 row says "3-laptop network" while the gate text says "(simulator + 1-laptop chain)". The design report's MVP (Besu + executor + PSI + quotas) is the Target tier, and the plan uses "MVP" three times (S7.5 Aggregation/Answers/Time) without defining it. | MED | Move latency/cost table to Target or put Besu in the floor; define MVP = floor or target; make W4 consistent |
| I2 | S7.10 vs S7.4 / S12 Q4 | PBC has 4 validators (f=1) but the laptop list places V1-V3 only; the design puts V4 on L1. So L1 hosts 2 of 4 PBC validators. Default Q4 says t=1 of 3 and "employer may be corrupt": a corrupt H1 then controls 2 of 4 validators, which exceeds f=1 and breaks assumption L for the PoC measurements; one dead laptop (L1) also halts QBFT (3 of 4 needed). | MED | Place one validator per laptop (3) + one on the least-trusted/spare node, or state the PoC does not exercise L; add V4 |
| I3 | S7.9 H1 vs S8.2 G1 | See S3 (eps<=2 KILL vs eps<=4 PASS). | MED | unify |
| I4 | S0 "need the re-check before week 2" vs S8.2 W0/W1, S11 "do not write code until the re-check verdict is in", R1 "re-check in week 0" | Week 1 plan is all coding. | LOW | "before W1 coding starts" |
| I5 | S7.2 C1 "five unsound designs" vs S6 delta (2) "three existing designs" | Mapping unstated. A1/A2 -> per-dataset/hospital-set ledgers, A3 -> per-GID, A4 -> "HMBC as-is" log-only, A5 -> B6. B3', B5, B6 are the plan's own constructions, not published designs. | LOW | add a mapping table |
| I6 | S8.4 vs R9 | Needs 10-13 pw (target) against 24+ pw capacity, yet R9 scope risk is H/H. Not contradictory if learning curve is the issue, but say so. | LOW | add a sentence |
| I7 | S4 row D vs S9 D | Scores are the package row; pitch is C-I (see S3). | LOW | footnote |
| I8 | S11 R3 vs S12 Q1 | "6x gap" (variance) vs "2.45x RMSE" (see S3). | LOW | unify |
| I9 | S2 "about 14 GB RAM" vs S7.10 / W1 | W1 runs 4+3 Besu (7 JVMs at 512 MB heap) on one laptop and L3 peaks at 3.8 GB with TLC; the user's laptop-limits note caps our RSS at 3.5 GB after an OOM crash. | LOW | stagger runs, check `free -h` before each step |

---

## 6. Missing items a reviewer would ask for (prioritised)

1. **Strawman and stale novelty.** (a) The only blockchain-specific negative result (A4 vs B5 "unbound PBC-signed approval receipt") targets a baseline the plan invented: HMBC as-is has no statistics path and no receipt, and R2_adversary says "only the third is specific to blockchains". Say what published design B5 is, or label it a constructed counter-example. (b) RECHECK_COMMS T1 (provisional REFRAME) already lists closer ledger-gating priors that S6 / L8 / L13 do not: Mangala et al. FGCS 2026 (healthcare consortium, "Privacy Budget Ledger" contract checked before every DP query), SAP patent US 10,380,366 (2017), Yang et al. IEEE Cloud Comput. 2018 (Hyperledger), Trask and Prakash 2021 (patient-level budget across two hospitals). The "~65%" and the "No work found ..." claim (L13) need re-basing. [HIGH for item (b), as a refresh, not an error in v1]
2. **Mid-evaluation.** PROJECT_IDEAS.md assumed a mid-eval ~1.5-2 weeks after 17 Sep; the plan has no interim deliverable and W0/W1 says "do not write code until the re-check verdict". State what is shown at mid-eval (e.g. the A1-A3 simulator curves, which need no chain).
3. **Methodology match.** Earlier notes (PROJECT_IDEAS, OPEN_QUESTIONS Q3, BRIEF) say the instructors expect ROR + ProVerif/Scyther + comparison tables. The plan picks TLA+/TLC and puts ProVerif in stretch, and R2_adversary's minimum delta asked for a ProVerif/Tamarin model of authorise -> debit -> receipt -> share -> release. Either ask (Q6 exists but its default silently chooses TLA+) or put a small ProVerif model of the receipt/mask channel in the floor.
4. **Preconditions of the headline numbers** and the lifetime-budget semantics: after ~225 counts of size ~1000 the system is exhausted for every analyst combined (T10); cells of 100-200 patients are unanswerable. Give the workload's cell-size distribution and the per-cell cost, and say what a researcher gets after exhaustion. T10 also notes the zCDP -> eps conversion is conservative (exact GDP eps is 1.61 at rho 0.0676, ~1.5x more queries).
5. **Validator placement vs threat model** (I2) and the DBC f=0 remark (DBC has 3 validators = f 0; "not on the safety path" but ACSC-Q policy is evaluated there).
6. **Undefined terms.** MVP, "useful query", "stats executor", TempACL, TOCTOU, zCDP, PSI, QBFT, "linked/unlinked mode" (used in S0 before S7.5). Add a 10-line glossary.
7. **Plan refresh list.** RECHECK_COMMS already contains T9 and T10 results: upgrade L5/G-9 to confirmed (add T9 correction on n), L15 numbers to "reproduced" (tag change [U] -> recomputed), and fold in the T9 Fabric finding that `GetTxTimestamp` is the client's clock (relevant to any time-based budget or ticket window).
8. **Real-ID realism.** Linked mode needs a common patient ID (AMKA/SSN) and G2 notes HMBC has no patient identity at all. Q1 covers acceptability but not that Synthea's SSN field makes linked mode look easier than any real deployment; add that to Limitations.
