# Sources for every number in `hmbc-end-presentation.pdf`

All repository paths are read with `git show <ref>:<path>`. Unless stated otherwise the ref is
**`origin/Code_Merge_Final`** (commit `fc80bf00e32c9f57f9bd01f0785c063969633c71`, the ownership merge of
agent-1 `d7bac30`, agent-2 `faa4e63` and agent-3 `ca82b7f`). Line numbers refer to that ref.

Pinned report hashes (recomputed from that ref on 2026-11-17):

| File | SHA-256 |
|---|---|
| `evaluation/reports/RQ2-F-DRAFT.md` | `e59a51cd8c92a38780aa820191286887d9dc92deb1a0cdefe8c699f34a6e3b40` (the hash reviewed in A1-0142 and A2-0091) |
| `evaluation/reports/RQ1-E.md` | `69dabfbab9d9deeb0d94b448da6bf9b9674ce25c7c94e1b101f67c4804c89b8f` (the hash named in the gate E ACKs) |

Short names used below: **RQ2** = `evaluation/reports/RQ2-F-DRAFT.md`; **RQ1** = `evaluation/reports/RQ1-E.md`;
**EV** = `evaluation/evidence/f/`; **MEAS** = `EV/measurements-20261114/README.md`;
**A1-nnnn** = `communication/agent-1/outbox/nnnn-*.md`; **A2-nnnn** = `communication/agent-2/outbox/nnnn-*.md`;
**mid** = `origin/slides:hmbc-presentation.tex` at d292576 (the mid-eval deck; slides 6–12 of this deck are
adapted from its slides 15–22 and keep its numbers; slide 4 takes its JANUS facts from mid slides 9–10).

Every result in the deck is a paper-derived reconstruction result on synthetic fixtures, not a result about
the HMBC authors' implementation.

---

## Slide 1 — Title

| Item | Source |
|---|---|
| Status line: RQ1 gate E PASS; RQ2 gate F NOT RUN, 0 of 32 F cases run | `communication/GATES.md:621, 648, 661`; RQ2:3 |
| Fig. 1 | `figures/fig1-architecture.png` (paper Fig. 1, CC BY 4.0; copied from `origin/slides:figures/`) |

## Slide 2 — The paper (1/2): problem and architecture

| Item | Source |
|---|---|
| Problem, running example, cloud vs blockchain | paper §I, §I-B (`references/HMBC2020.pdf`); mid lines 82–112 |
| Actors: users with one GID; per-stakeholder CA and ABE authority; CA admins publish trust lists; one node per chain | paper §III-C5/C6, §III-D (Fig. 3/4); mid lines 187–217 |
| PBC contracts RSC, TMSC, PSC, LSC; DBC contracts ACSC, KSSC | paper Fig. 1, §III; mid lines 153–184 |
| Records off chain, ABE-encrypted | paper §III; mid line 166 |

## Slide 3 — The paper (2/2): access overview and assumptions

| Item | Source |
|---|---|
| Five-stage overview: request → proxy chain verifies credentials → domain chain checks the policy → key release (two-step decryption) → audit log on both chains | paper Fig. 6 (simplified; the ten steps are in the slide note); mid lines 220–248 |
| Split decryption; revocation as a TempACL update | paper Fig. 5, §III-E2, §V-A4; mid lines 251–284 |
| Assumptions: isolation, honest majority, secure crypto, uncompromised keys | paper §V; mid lines 322–324 |

## Slide 4 — JANUS

| Item | Source |
|---|---|
| Extension of HMBC by HMBC's authors (Malamas, Kotzanikolaou, Burmester) with CENSUS S.A., *Applied Sciences* 13(1):566, 2023 | mid line 351 ("Same authors with CENSUS S.A., *Applied Sciences* 13(1):566, 2023"); mid line 360 note: Malamas, Palaiologos, Kotzanikolaou, Burmester, Glynos, Appl. Sci. 13(1):566, 2023, doi 10.3390/app13010566 |
| Formal access model (HMBAC): attribute verification (PBC), authorisation and decryption (DBC) | mid line 353 |
| Open-source system: Fabric 2.4 + Raft, JavaScript contracts, Kubernetes pods | mid line 354 |
| Domain key only the KSSC can derive (in Vault), ANDed into every policy; realises the "System" role | mid line 355 |
| AES for records, MA-ABE only for the AES keys | mid line 355 |
| RabbitMQ queues with throttling; voting for domains, stakeholders and policies | mid line 356 |
| Attack trees; 2–300 concurrent requests, no failed requests | mid line 357 |
| Stack diagram (simplified from JANUS Fig. 5) | mid lines 335–347 |
| Left open: Raft tolerates crashes only; Byzantine tolerance named as future work | mid line 383 |

## Slide 5 — What we set out to answer: two research questions

| Item | Source |
|---|---|
| RQ1 question (follow / depend on missing details / repairs) | `SPEC.md:22`; RQ1:91–93 |
| RQ1 why: nothing binds the DBC grant to the PBC decision; lists have no freshness; outcomes logged without DBC evidence | RQ1:44–54; mid line 420 |
| RQ1 how: paper flow vs repaired-e on a frozen 56-row catalog, two local chains | RQ1:240–245 |
| RQ1 DONE, gate E PASS 12 Oct 2026 | `communication/GATES.md:621, 648` |
| RQ2 question | `SPEC.md:23`; RQ2:127–129 |
| RQ2 why: honest majority assumed in every chain; RQ1's repair trusts one witness | paper §V (mid lines 322–324); RQ1:1156 |
| RQ2 how: n = 4, q = 3, f = 1; safe ledgers and a trusted key worker; 32 integrated F cases | RQ2:127–129; `EV/execution-plan-draft-20261114/plan-draft.json` (`families`) |
| RQ2 in progress, gate F NOT RUN, 0 of 32 cases | `communication/GATES.md:661`; RQ2:3 |

## Slide 6 — RQ1: question and gaps (Gap 1, 2, 3)

| Item | Source |
|---|---|
| RQ1 wording | RQ1:91–93; `SPEC.md:22` |
| Gap 1 decision provenance, Gap 2 trust-list freshness, Gap 3 audit evidence (the mid-eval's RQ1-01 / 02 / 03) | RQ1:44–57; mid lines 564–566 |
| Relay stress outside the isolation assumption (A01); gaps are specification gaps, not attacks | RQ1:55–57 |

## Slide 7 — repaired-e: Fix 1, 2, 3

| Item | Source |
|---|---|
| Five-stage repaired flow (user signs; PBC logs and checks; witness signs checkpoint and decision; DBC verifies, nonce once, grants; worker releases, signed receipt closes the log) | mid lines 622–625 (repaired-e flow strip); RQ1:58–67 |
| Fix 1: typed EIP-712 signatures bound to the KSSC and the DBC chain; single-use (gid, nonce); request lifetime ≤ 30 s | RQ1:58–68; mid lines 630–633 |
| Fix 2: versioned, expiring lists; signed checkpoints as revocation barrier; duty validity at use | RQ1:58–67; mid lines 634–637 |
| Fix 3: witness-signed receipt per outcome; durable intent; cached response on retry | RQ1:58–67; mid lines 638–641 |
| Paper's flow (two readings) and repaired-e on one frozen 56-row catalog | RQ1:240–243; `communication/DECISIONS.md:107` (D38) |
| One trusted witness in RQ1 | RQ1:1156 |

## Slide 8 — Gap 1 result [I]

| Item | Source |
|---|---|
| Every row and code (REPLAY, WRONG_SUBJECT, BAD_SIGNATURE, WRONG_DESTINATION, EXPIRED at equality); same in both paper readings | RQ1:36–37, 45–47, 59–61; RQ1 §7 (lines 612–734); gate rows 10–22, 51–56 in RQ1 §6 |
| Identical replay rests on deterministic grant id (A25) | RQ1:36–37 |
| Nonce reuse row (speaker note only) | RQ1:59–60; RQ1 §7.4 (lines 688–701) |
| Evidence-label legend [I]/[R]/[U]/[F] (first slide that uses a label) | `origin/slides:README.md` (mid-eval "Results are labelled by evidence level") |

## Slide 9 — Gap 2 result and the window

| Item | Source |
|---|---|
| UNAUTHORIZED_CALLER baseline (code 16), specified by the paper | RQ1:40–41 |
| Rollback un-revokes; STALE_ANCHOR (TMSC.sol:190) | RQ1:48, 62 |
| Pre/post-barrier rows; STALE_STATE | RQ1:48–50, 62–63, 72–73; RQ1 §8.3 (lines 771–789) |
| Expired duty; EXPIRED | RQ1:49–50, 63; RQ1 §8.4 (lines 790–809) |
| Window, machine A: 2 / 6 / 11 / 21 s (delays 0 / 5 / 10 / 20 s), 26 s no barrier | A1-0046 lines 22–28; RQ1:820–823 |
| Window, machine B: 2 / 6 / 11 / 21 s, 27 s no barrier | A2-0026 lines 16–23 |
| Paper's flow still grantable 65 s later | A1-0046 lines 17, 33; RQ1:825 |
| W = min(...) ≤ 30 s; 30 s cap | RQ1:832–833 |
| One trial per delay; not the gate run | RQ1:837–839 |

## Slide 10 — Gap 3 result [I]

| Item | Source |
|---|---|
| Duplicate REPLAY; dropped outcome stays PENDING | RQ1:38–43; RQ1 §9.1–9.2 (lines 866–900) |
| Fabricated outcome; WRONG_PROFILE | RQ1:51, 63–64 |
| Receipt binding WRONG_SUBJECT; deviating test witness (A40) | RQ1:64–65; RQ1 §9.3 (lines 901–926) |
| Paper crash rows blocked and unproved, never a pass or a finding (D47); cached response; EXPIRED after expiry | RQ1:51–53, 66–67; RQ1 §9.4 (lines 927–979) |
| Logical process deaths only; delivery unknown | RQ1:1161 |

## Slide 11 — What RQ1 shows

| Item | Source |
|---|---|
| Holds / depends / repairable | RQ1:34–67 |
| ≤ 30 s bound in the RQ1 repair | RQ1:68, 832–833 |
| "First executable instance-level analysis" (non-exhaustive search) | mid lines 427, 893, 908 |
| One trusted witness | RQ1:1156 |
| Gate E: PASS on 12 Oct 2026 | `communication/GATES.md:637–648` (ACKs A1-0085, S2-0023, S3-0024) |
| All 56 catalog rows matched their frozen expectation | RQ1:356; RQ1:240–243 |
| 6 ledger mutants, each caught by its expected tests | RQ1:1031–1044 |
| ProVerif finds an attack once the destination check is dropped | RQ1:999–1013 |

## Slide 12 — RQ2 question

| Item | Source |
|---|---|
| RQ2 wording, n=4, q=3, f=1, safe ledgers, trusted key worker | RQ2:127–129 |
| Overlap ≥ 2 witnesses | RQ2:149 |
| Single signing per key, persisted | `SPEC.md:79`; RQ2:132 |
| One witness per hospital; relay has no key | `SPEC.md:73`; RQ2:272 |
| Not consensus; Anvil not BFT | `SPEC.md:75`; GATES.md:658 |
| Out-of-bound controls f=2, q=2, ≥3 | RQ2:146–147, 269 |

## Slide 13 — RQ2 design (plain explanation)

| Item | Source |
|---|---|
| Three certified paths: checkpoint checked at the key-service contract (KSSC), decision at the policy contract (ACSC), receipt on the shared request and audit path (PSC) | RQ2:129–131 |
| Checkpoint = snapshot of proxy-chain trust and authorisation state (sequence, auth epoch, source block) | A1-0137 §2.1 (KSSC.sol:160–163); A1-0138 §1 |
| Decision = outcome and credential binding for one request (quorum-signed credential digest) | A1-0137 §2.2 (DecisionVerifier.sol:73) |
| Receipt binds an outcome to a committed grant | RQ1:64–65 (receipt binding) |
| Governance: add/remove a credential authority, change its admins; nonce and expiry; applied to the shared trust lists | RQ2:131; A1-0137 §1 (Governance.sol:83–86, TMSC.sol:144–159) |
| At least 3 of 4 distinct member signatures | RQ2:130; A1-0137 §1 (SigLib.sol:37) |
| Witness membership fixed at deployment | RQ2:269; A1-0137 §1 (A1-0126) |
| Honest witness persists its signature (durable SQLite store, survives restart) and replaces an approval only once it is observed dead | `SPEC.md:79`; RQ2:132, 293–301; `protocol/hmbc_protocol/witness_state.py:408–427` |
| Collector / relay holds no key | `SPEC.md:73`; RQ2:272 |

## Slide 14 — How RQ2 is judged

| Item | Source |
|---|---|
| Six families A–F (names) | `EV/execution-plan-draft-20261114/plan-draft.json` (`families`) |
| Family purposes (case titles: e.g. FL-2 one witness withholds, F-12 equivocating witness, F-13 signer restarts, F-27 database rollback, F-31 clock/height regression, F-32 store reuse, FL-6 stale witness set, FL-10 governance replay, FL-11 relay suppresses outcomes, F-21 relay forges request contents, F-19 compromised worker host, F-25 common host compromise, F-26 storage faults) | `EV/case-coverage-map-20261114/coverage.csv` |
| What the gate requires (six bullets) | `communication/GATES.md:652–659` |
| Fresh chain pair per case, positive controls first | `plan-draft.json` (`stages`, stage 4) |
| No integrated run claimed on this slide; status on slide 22 | `communication/GATES.md:661`; RQ2:3 |

## Slide 15 — Experiment 1 result: why three approvals are needed [F]

| Item | Source |
|---|---|
| f=1, q=3: holds, 433 / 108, complete | RQ2:144; `EV/tlc-audit-20261115/README.md:16` |
| f=0: holds, 217 / 81 | RQ2:145; tlc-audit README:17 |
| q=2, f=2, no-persistence: violated | RQ2:146–148; tlc-audit README:18–20 |
| Fresh rerun matched | RQ2:154–158; tlc-audit README:22–24 |
| Agent 1's enumeration matches | RQ2:150–151; A1-0137 §1 ("A1-0122: 108 and 81") |
| Limits | RQ2:149–154; tlc-audit README:29–33 |
| Negative configurations stop at a counterexample trace | tlc-audit README:18–20, 22–24 |
| First f=0 run deadlocked (speaker note / history) | RQ2:216–217; `EV/decision-quorum-tlc-20261113/first-run-with-deadlock/` |

## Slide 16 — Experiment 2 result: certificate collection with real signatures [U]

| Item | Source |
|---|---|
| f=1: 972 cases, 180 certificates, 792 none, 0 invalid, 0 hazards | `EV/pool-sweep-20261115/README.md:20–22`; MEAS:74–77 |
| f=2: 4,374 cases, 330 certificates, 4,044 none, 0 invalid, 2,916 hazards | pool-sweep README:23; MEAS:78–79 |
| 3 distinct sorted valid signers | pool-sweep README:29–30 |
| 9 behaviours; 4×9×27 and 6×81×9 | MEAS:72–79 |
| Hazard definition (potential); honest witnesses modelled; byte-identical rerun | pool-sweep README:15–17, 25–28, 34–38; MEAS:80–83 |
| Honest witness starts uncommitted or committed to one of two values (3 states) | `evaluation/measurements/byzantine_sweep.py:46, 55` |
| Nine malicious behaviours (silent; sign A/B/C; report A/B/C; garbage; wrong key) | MEAS:72–73 |

## Slide 17 — Experiment 3 result: the availability boundary [U]/[R]

| Item | Source |
|---|---|
| 16 subsets × 5 runs = 80 trials | `EV/availability-receipt-review-20261115/README.md:13–16` |
| 0/1 muted: certificate; 2/3/4 muted (6/4/1 subsets): none by 10,000 virtual ms | MEAS:45–48 |
| Delays 400/300/200/100 ms → certificate at 300 ms | MEAS:49–50 |
| Real witnesses behind virtual transport; exact-source rerun matched | MEAS:42–44; RQ2:117–124, 167–173 |
| M6 table (0.69/0.69/0.78; 0.63/0.55/0.60; 10.54/10.54/10.55; 0.96/0.87/0.88 s); 4 passed × 3 runs | MEAS:122–129 |
| 10.5 s = 10 s deadline + overhead | MEAS:130 |
| M6 raw stdout and invocation not retained | availability-receipt-review README:1–6; RQ2:93–95 |
| Ranges 0.69–0.78 s, 0.55–0.63 s, 10.54–10.55 s (min–max of the three runs) | MEAS:126–128 |
| Every trial record retained (80 rows) | RQ2:117–124; `EV/availability-trial-records-20261115/README.md` |
| Two, three or four silent: 11 subsets (6 + 4 + 1) | MEAS:47 |

## Slide 18 — Experiment 4 result: can a crash split a signing record? [R]

| Item | Source |
|---|---|
| K1 definition | `protocol/tools/run_state_kill_mutants.py:5–6, 25–27` |
| The synchronous=FULL → OFF mutant survives (power loss only) | run_state_kill_mutants.py:9, 34; `evaluation/evidence/reviews/proxy-k1-20261114/README.md:65–66` |
| Earlier 3/3 not reproduced | `evaluation/evidence/reviews/a2-0086-signing-kill-20261113/README.md:14–16`; RQ2:197–199 |
| 29/40 (72.5%), control 40/40 | a2-0086 review README:28–32; RQ2:197–198 |
| After the hook: 40/40, controls 40/40 | proxy-k1 README:48–49; RQ2:199–201 |
| Agent 2: 15/15, 10/10, 81 state tests, 3,226 passed / 201 skipped | A2-0089 lines 22–23; RQ2:201–203 |
| Three defects found and fixed | RQ2:195–197 |
| Three pause points: after a fresh pin, after a digest, after replacing an obsolete pin | `evaluation/evidence/reviews/proxy-k1-20261114/README.md:57` ("all three pauses (fresh pin, digest, superseding pin)"); `protocol/hmbc_protocol/witness_state.py:416–435` (`after_pin` follows the supersede path; `after_digest`) |
| Placeholder signer; process death only | proxy-k1 README:3–4, 65–66 |
| Correct store passes 40/40 with either test | a2-0086 review README:32 (control 40/40); proxy-k1 README:48 (40 PASS) |
| Agent 2's rerun: 15/15 caught, 10/10 controls | A2-0089 lines 22–23 |

## Slide 19 — Experiment 5 result: when does a different signature become legal? [U]

| Item | Source |
|---|---|
| 180/180 agree, 142 accepts, 38 CONFLICT_PINNED, 0 disagreements | `EV/oracle-store-diff-20261115/README.md:9–14`; RQ2:27–29 |
| Four signing kinds; subtree 7566f63d.. | oracle-store-diff-20261115 README:10–14 |
| Seven mutations 20, 18, 6, 4, 4, 4, 4 | `EV/oracle-mutant-discrimination-20261115/README.md:16–24`; RQ2:33–35 |
| Not completeness | oracle-mutant README:36–38 |
| Store capability vs service reachability; earlier DENY claim wrong | RQ2:293–301; A2-0089 §2 |
| Grid: 3 expiry × 3 sequence/nonce × grant × outcome (= 36 per type) for checkpoints, governance, receipts; × earlier ALLOW/DENY for decisions (72): 180 | `EV/oracle-store-diff-20261114/README.md:9–14` |
| Plain rule names: expiry `>=`→`>` = treat exact expiry as still valid; receipt never dead; decision sequence `>`→`>=` = retire at an equal sequence; drop grant death; grant kills DENY; checkpoint `>=`→`>` = require a greater sequence; governance `>=`→`>` = require a greater nonce | `evaluation/measurements/oracle_mutant_discrimination.py:27–51` |
| Baseline row: correct rules, 0 disagreements (180/180; 142 replace, 38 refuse) | oracle-mutant-discrimination-20261115 README:9–14 |

## Slide 20 — Experiment 6 result: cost [R]

| Item | Source |
|---|---|
| 208,290 / 231,260 / 238,046 (checkpoint) | MEAS:25–27; RQ2:185 |
| 324,323 / 342,261 / 349,053 (decision) | MEAS:28–30; RQ2:186 |
| 533,754 / 553,488 / 560,290 (receipt) | MEAS:86–87; RQ2:187 |
| +11.0% / +5.5% / +3.7% | RQ2:185–187; A1-0137 §1 table |
| ≈ 6.8k gas and 160 B per extra signature | RQ2:188; MEAS:31 |
| Governance.execute 524,214 / 424,421 / 446,934 | RQ2:189; MEAS:104–108 |
| All under 24,576 B; TMSC 12,635 → 16,127 B | RQ2:190–191; MEAS:37–39; A1-0137 §3 item 2 |
| 21 rows (15 distinct) reproduced exactly, raw logs | A1-0136 lines 14, 27–28; `EV/gas-attachment-audit-20261115/README.md`; RQ2:75–85 |
| Cold-storage hypothesis refuted (231,261 vs 231,260) | MEAS:94–96 (A1-0123) |
| Single deterministic runs; not a fee estimate | MEAS:18–21, 65; RQ2:191–192 |

## Slide 21 — Security findings beyond the fault bound

| Item | Source |
|---|---|
| Saturated sequence / authEpoch / sourceBlockNumber halt; no reset; redeploy | RQ2:269; A1-0137 §2.1 (lines 45–58); A1-0138 §1 (lines 31–49) |
| Decisions stop at once (authEpoch) or after expiry | A1-0138 lines 40–49 |
| < 3 signers cannot poison; 3/3 and 3/3 | A1-0137 lines 54–57; A1-0138 lines 53–61 |
| Forged-credential grant; controls INSUFFICIENT_QUORUM / POLICY_DENIED; 3/3; key release not shown | A1-0137 §2.2 (lines 60–72); RQ2:269 |
| f=2: second checkpoint STALE_STATE; second ALLOW REPLAY; DENY/ALLOW both accepted either order, incl. same sequence and after grant | RQ2:279–291; A1-0141 §2–3 (lines 28–43) |
| DENY consumes no nonce (E0 choice, ACSC.sol:186–188) | RQ2:285–286 |
| Honest witness REPLAY at signing | A2-0089 §2; RQ2:288–290 |
| Scratch 4/4 rerun by the evaluator | MEAS:141–144; RQ2:281–282 |
| Headline wording ("partly stopped by the contracts", "certify fake credentials", "permanent halt"); all three outside the f = 1 bound | RQ2:269, 279–291 |

## Slide 22 — What RQ2 shows

| Item | Source |
|---|---|
| Agreement within the bound; both quorum and persistent single-signing needed | slides 15–16 sources (RQ2 §2.1; tlc-audit; pool-sweep) |
| One witness down works, two stop it | slide 17 sources (MEAS:45–48, 118–134) |
| Controlled kills catch a split signing record | slide 18 sources |
| Replacement rules match the store and catch rule errors | slide 19 sources |
| +3.7 to +11.0% gas | slide 20 sources (RQ2:185–187) |
| Compromised quorum can fake credentials or halt the deployment | slide 21 sources |
| What stays trusted: credential issuers, key worker, ledgers | RQ2:265–278 (trust matrix in the report) |
| Gate F: NOT RUN; the integrated 32-case study still to run | `communication/GATES.md:661`; RQ2:3; packet README:131–134 |

## Slide 23 — Conclusion

| Item | Source |
|---|---|
| Gaps 1–3 closed by Fix 1–3 | slides 6–7 sources (RQ1:44–67) |
| Paper's flow accepts what the RQ1 repair rejects (Gap 1–3 result tables) | slides 8–10 sources (RQ1 §7–§9) |
| Revocation bounded at ≤ 30 s | RQ1:832–833 |
| Gate E PASS, 12 Oct 2026 | `communication/GATES.md:637–648` |
| RQ2 items (Exp. 1–6, beyond the bound) | slides 15–21 sources; RQ2:19–24 |
| Crash test caught 40/40 | proxy-k1-20261114 README:48–49 |
| Still to run: the integrated 32-case gate-F study | `communication/GATES.md:661`; RQ2:3; packet README:131–134 |
| Next, try on JANUS: the authors' Fabric/Raft extension; JANUS integration needs a separate project decision | mid lines 351–354, 383; `AGENTS.md:8` ("A later JANUS integration requires a separate decision") |
| Next, planned RQ3: key lifecycle with real ABE; what stays secret after revocation, joining or later key compromise | mid lines 397, 941–955; `SPEC.md:24`, §6 (lines 85–102); `PLAN.md:224` |
| Only after gate F passes | `communication/GATES.md:659, 665` |

---

## Facts left out because no file supports them, or by instruction

- **"112 services"** in the gate run (on the mid-eval's commented-out gate slide): not found in `RQ1-E.md`
  or the gate manifest, so not used.
- **A date for a gate F decision**: no file gives one; the deck gives none.
- **A mitigation for the forged-credential grant**: none is designed or tested in the sources; the Q&A says so.
- **The paper's prototype performance** (603 ms per access, Fig. 11): kept out of the two paper slides to fit;
  it is only in a speaker note (paper Table 4; mid lines 303, 310).
- By instruction, the deck presents the project as RQ1 and RQ2 only.

## Short report (`presentation-hmbc/short-report.docx`, 15 Nov 2026): how its claims were used

The RQ2 experiment slides follow the report's structure and plain wording. The report is not a repository file,
so every claim used on a slide is backed above by repository evidence.

- **Used as is (verified):** Experiment 1 configurations and the 108/81 state counts; Experiment 2 scenario
  arithmetic (4 × 9 × 3³ = 972, 6 × 9² × 3² = 4,374), 180/792/0 and 330/2,916; Experiment 3's 80 trials,
  the 400/300/200/100 ms delay control finishing at 300 virtual ms, and the real-process ranges
  0.69–0.78 s, 0.55–0.63 s, 10.54–10.55 s; Experiment 4's 29/40 → 40/40 and the 81 state tests; Experiment 5's
  180-case grid, 142/38, and the seven rule mutations with their counts; the three security findings;
  Experiment 6's gas, calldata and size figures.
- **Reworded:** the third K1 hook is "after replacing an obsolete pin" (the store has two hook calls,
  `after_pin` and `after_digest`; `after_pin` runs after the supersede path, and the review receipt names
  three pauses), not "during replacement"; mutation names are plain-language renderings of the operator
  changes in `oracle_mutant_discrimination.py`.
- **Not used:** the "≤ 30 seconds residual acceptance" sentence (RQ1 material, already covered by RQ1's own
  sourced window slide); the regression-count table (3,004 evaluation tests, 37 focused controls), which
  is regression evidence, not an experiment, and is not on the slides.
