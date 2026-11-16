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
**mid** = `origin/slides:hmbc-presentation.tex` at d292576 (the mid-eval deck; slides 6–14 of this deck are
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

## Slide 6 — RQ1: question and gaps

| Item | Source |
|---|---|
| RQ1 wording | RQ1:91–93; `SPEC.md:22` |
| Gaps RQ1-01 / 02 / 03 | RQ1:44–57; mid lines 564–566 |
| Relay stress outside the isolation assumption (A01) | RQ1:55–57 |

## Slide 7 — RQ1 method

| Item | Source |
|---|---|
| 37 paper passages | `interfaces/v1/source-map.csv` (37 rows, S01–S37) |
| 41 recorded completions | `interfaces/v1/assumptions.csv` (41 rows, A01–A41); RQ1:35 |
| 16 schedules × 3 profiles + 8 repaired-only rows = 56 | RQ1:240–242 |
| Frozen on 8 Oct, before any run | RQ1:242–243; `communication/DECISIONS.md:107` (D38, `E0-v1-r6-20261008`) |
| Fresh chain pair per row; controls first (wrong admin, Alice allow, Bob deny) | RQ1:244–249 |
| Six mutants | RQ1:1037–1044 |
| Four classes | RQ1:112–122 (§2.1) |

## Slide 8 — repaired-e

| Item | Source |
|---|---|
| Typed EIP-712 signatures, single-use (gid, nonce), request lifetime ≤ 30 s | RQ1:58–68; mid lines 630–641 |
| Versioned lists, checkpoints as barrier; receipt per outcome; durable intent | RQ1:58–67; mid lines 634–641 |
| 13 DecisionVerifier steps in fixed order; step 12 reserved | mid lines 645–652; RQ2:269 (key epoch must be 0 under REPAIRED_F) |

## Slide 9 — RQ1 results, gap 1 [I]

| Item | Source |
|---|---|
| Every row and code (REPLAY, WRONG_SUBJECT step 4, BAD_SIGNATURE step 6, WRONG_DESTINATION step 1, EXPIRED step 9 at equality) | RQ1:36–37, 45–47, 59–61; RQ1 §7 (lines 612–734); gate rows 10–22, 51–56 in RQ1 §6 |
| Identical replay rests on deterministic grant id (A25) | RQ1:36–37 |
| Evidence-label legend [I]/[R]/[U]/[F] (first slide that uses a label) | `origin/slides:README.md` (mid-eval "Results are labelled by evidence level") |

## Slide 10 — RQ1 results, gap 2, and the window

| Item | Source |
|---|---|
| UNAUTHORIZED_CALLER baseline (code 16) | RQ1:40–41 |
| Rollback un-revokes; STALE_ANCHOR (TMSC.sol:190) | RQ1:48, 62 |
| Pre/post-barrier rows; STALE_STATE | RQ1:48–50, 62–63, 72–73; RQ1 §8.3 (lines 771–789) |
| Expired duty; EXPIRED step 13 | RQ1:49–50, 63; RQ1 §8.4 (lines 790–809) |
| Window, machine A: 2 / 6 / 11 / 21 s (delays 0 / 5 / 10 / 20 s), 26 s no barrier | A1-0046 lines 22–28; RQ1:820–823 |
| Window, machine B: 2 / 6 / 11 / 21 s, 27 s no barrier | A2-0026 lines 16–23 |
| Paper-strict still grantable 65 s later | A1-0046 lines 17, 33; RQ1:825 |
| W = min(...) ≤ 30 s; 30 s cap | RQ1:832–833 |
| One trial per delay; not the gate run | RQ1:837–839 |

## Slide 11 — RQ1 results, gap 3 [I]

| Item | Source |
|---|---|
| Duplicate REPLAY; dropped outcome PENDING | RQ1:38–43; RQ1 §9.1–9.2 (lines 866–900) |
| Fabricated outcome; WRONG_PROFILE | RQ1:51, 63–64 |
| Receipt binding WRONG_SUBJECT; deviating test witness (A40) | RQ1:64–65; RQ1 §9.3 (lines 901–926) |
| Crash rows BLOCKED / decided SPEC_GAP, unproved (D47); cached response; EXPIRED after expiry | RQ1:51–53, 66–67; RQ1 §9.4 (lines 927–979) |
| Logical process deaths only; delivery unknown | RQ1:1161 |

## Slide 12 — Mutants and ProVerif

| Item | Source |
|---|---|
| Six mutants and the tests that detect them | RQ1:1031–1044 |
| 8 guard rows; destination mutant not killable by the catalog recipe | RQ1:1048–1059 |
| ProVerif queries and verdicts | RQ1:999–1013 |
| Model limits | RQ1:1016–1020 |

## Slide 13 — Gate E

| Item | Source |
|---|---|
| 32 paper rows: 8 SUPPORTED, 20 SPEC_GAP, 4 BLOCKED; 24 repaired-e rows: 19 REPAIR_SUPPORTED, 5 SUPPORTED | tally of the GATE column of RQ1 §6 (lines 410–555); same grid as mid lines 842–853 |
| 56 PASS, 0 FAILED, 0 NOT_RUN | RQ1:356 |
| 4,749 s (1.32 h), exit 0 | RQ1:327–328, 361 |
| Sources and HEAD unchanged; inputs/outputs hashed | RQ1:358–359; `communication/GATES.md:634` |
| 7 criteria verified in the run, report and ACKs adjudicated after | RQ1:13, 397–407 |
| Mutant criterion on scoped evidence | RQ1:1024–1027; GATES.md:630 |
| Three ACKs; decision text | `communication/GATES.md:637–648` |
| Integrated mutants and window not run; correlated review | RQ1:16–21, 76–81 |

## Slide 14 — What RQ1 shows

| Item | Source |
|---|---|
| Holds / depends / repairable | RQ1:34–67 |
| ≤ 30 s | RQ1:68, 832–833 |
| Limits: symbolic crypto, one trusted witness and worker, local chains, one trial per row | RQ1:1150, 1152, 1156, 1173 |
| "First executable instance-level analysis" (non-exhaustive search) | mid lines 427, 893, 908 |

## Slide 15 — RQ2 question

| Item | Source |
|---|---|
| RQ2 wording, n=4, q=3, f=1, safe ledgers, trusted key worker | RQ2:127–129 |
| Overlap ≥ 2 witnesses | RQ2:149 |
| Single signing per key, persisted | `SPEC.md:79`; RQ2:132 |
| One witness per hospital; relay has no key | `SPEC.md:73`; RQ2:272 |
| Not consensus; Anvil not BFT | `SPEC.md:75`; GATES.md:658 |
| Out-of-bound controls f=2, q=2, ≥3 | RQ2:146–147, 269 |

## Slide 16 — RQ2 design

| Item | Source |
|---|---|
| Three signed paths (checkpoint→KSSC, decision→ACSC, receipt→PSC) | RQ2:129–131 |
| ≥ q = 3 of 4 signatures, strictly increasing; 4 of 4 accepted | RQ2:130; A1-0137 §1 table (SigLib.sol:37) |
| Governance: add/remove authority, set CA admins; nonce + expiry | RQ2:131; A1-0137 §1 (Governance.sol:83–86) |
| Removed authority tombstoned | A1-0137 §1 (TMSC.sol:144–147, 159) |
| Witness set fixed at deployment | RQ2:269; A1-0137 §1 (A1-0126) |
| Checkpoint: strictly greater sequence; authEpoch / sourceBlockNumber non-decreasing | A1-0137 §2.1 (KSSC.sol:160–163) |
| Receipt names another request/GID/record | RQ1:64–65 |
| Honest witness REPLAY after grant | A2-0089 §2 (witness_service.py:146–147) |

## Slide 17 — How RQ2 will be judged

| Item | Source |
|---|---|
| 32 cases, six families 8+6+4+8+3+3 | `EV/execution-plan-draft-20261114/plan-draft.json` (`families`); its README line 25 |
| Stages 1–7 | `plan-draft.json` (`stages`) |
| Status DRAFT, authorizesExecution false | `plan-draft.json` (`status`, `authorizesExecution`) |
| 0 of 32 integrated | `EV/case-coverage-map-20261114/README.md:7`; RQ2:3 |
| Stages 1–2 fail closed (BLOCKED); 3–7 open | RQ2:3–4, 113–115, 355–357 |
| Evidence labels per item | as slides 18–25 |
| Measured before runner and FREEZE | MEAS:13–14; RQ2:365–366 |

## Slide 18 — TLC [F]

| Item | Source |
|---|---|
| f=1, q=3: holds, 433 / 108, complete | RQ2:144; `EV/tlc-audit-20261115/README.md:16` |
| f=0: holds, 217 / 81 | RQ2:145; tlc-audit README:17 |
| q=2, f=2, no-persistence: violated | RQ2:146–148; tlc-audit README:18–20 |
| Fresh rerun matched | RQ2:154–158; tlc-audit README:22–24 |
| Agent 1's enumeration matches | RQ2:150–151; A1-0137 §1 ("A1-0122: 108 and 81") |
| Limits | RQ2:149–154; tlc-audit README:29–33 |
| First f=0 run deadlocked | RQ2:216–217; `EV/decision-quorum-tlc-20261113/first-run-with-deadlock/` |

## Slide 19 — Oracle/store differential [U]

| Item | Source |
|---|---|
| 180/180 agree, 142 accepts, 38 CONFLICT_PINNED, 0 disagreements | `EV/oracle-store-diff-20261115/README.md:9–14`; RQ2:27–29 |
| Four signing kinds; subtree 7566f63d.. | oracle-store-diff-20261115 README:10–14 |
| Seven mutations 20, 18, 6, 4, 4, 4, 4 | `EV/oracle-mutant-discrimination-20261115/README.md:16–24`; RQ2:33–35 |
| Not completeness | oracle-mutant README:36–38 |
| Store capability vs service reachability; earlier DENY claim wrong | RQ2:293–301; A2-0089 §2 |

## Slide 20 — M5 pool sweep [U]

| Item | Source |
|---|---|
| f=1: 972 cases, 180 certificates, 792 none, 0 invalid, 0 hazards | `EV/pool-sweep-20261115/README.md:20–22`; MEAS:74–77 |
| f=2: 4,374 cases, 330 certificates, 4,044 none, 0 invalid, 2,916 hazards | pool-sweep README:23; MEAS:78–79 |
| 3 distinct sorted valid signers | pool-sweep README:29–30 |
| 9 behaviours; 4×9×27 and 6×81×9 | MEAS:72–79 |
| Hazard definition (potential); honest witnesses modelled; byte-identical rerun | pool-sweep README:15–17, 25–28, 34–38; MEAS:80–83 |

## Slide 21 — Availability

| Item | Source |
|---|---|
| 16 subsets × 5 runs = 80 trials | `EV/availability-receipt-review-20261115/README.md:13–16` |
| 0/1 muted: certificate; 2/3/4 muted (6/4/1 subsets): none by 10,000 virtual ms | MEAS:45–48 |
| Delays 400/300/200/100 ms → certificate at 300 ms | MEAS:49–50 |
| Real witnesses behind virtual transport; exact-source rerun matched | MEAS:42–44; RQ2:117–124, 167–173 |
| M6 table (0.69/0.69/0.78; 0.63/0.55/0.60; 10.54/10.54/10.55; 0.96/0.87/0.88 s); 4 passed × 3 runs | MEAS:122–129 |
| 10.5 s = 10 s deadline + overhead | MEAS:130 |
| M6 raw stdout and invocation not retained | availability-receipt-review README:1–6; RQ2:93–95 |

## Slide 22 — Gas [R]

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

## Slide 23 — K1 [R]

| Item | Source |
|---|---|
| K1 definition | `protocol/tools/run_state_kill_mutants.py:5–6, 25–27` |
| The synchronous=FULL → OFF mutant survives (power loss only) | run_state_kill_mutants.py:9, 34; `evaluation/evidence/reviews/proxy-k1-20261114/README.md:65–66` |
| Earlier 3/3 not reproduced | `evaluation/evidence/reviews/a2-0086-signing-kill-20261113/README.md:14–16`; RQ2:197–199 |
| 29/40 (72.5%), control 40/40 | a2-0086 review README:28–32; RQ2:197–198 |
| After the hook: 40/40, controls 40/40 | proxy-k1 README:48–49; RQ2:199–201 |
| Agent 2: 15/15, 10/10, 81 state tests, 3,226 passed / 201 skipped | A2-0089 lines 22–23; RQ2:201–203 |
| Three defects found and fixed | RQ2:195–197 |

## Slide 24 — Trust matrix

| Item | Source |
|---|---|
| Every row; the compromised-worker case NOT_RUN | RQ2:265–278 (274) |

## Slide 25 — Outside the bound

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

## Slide 26 — Assurance

| Item | Source |
|---|---|
| Report SHA-256 e59a51cd..; A1-0142 / A2-0091 no objection in scope; evaluation-tool correctness excluded; not an ACK | `communication/BOARD.md:54–68` (A3-0160); `EV/partial-report-packet-20261115/README.md:3–6, 37–43, 126–130` |
| Honest DENY after used ALLOW: wrong, corrected | RQ2:293–301 |
| Ledger/signing conflation corrected | A1-0141; RQ2:379–386 |
| M1 count 9/9 → 6/6 | A1-0136 §2 (lines 37–43) |
| Plan checker 27/27 vacuous dev-key scan → 28/28 + 9/9 | RQ2:49–55 |
| TMSC 52,339 B parser artifact | MEAS:64; RQ2:217 |
| K1 3/3 → 29/40 → 40/40 | as slide 23 |
| First-line hash missed an edit | A1-0141 §5 (lines 61–67) |
| Same model family; correlated | RQ2:12, 278; D57 |

## Slide 27 — Honest status of RQ2

| Item | Source |
|---|---|
| Plan DRAFT, authorises no execution | `plan-draft.json`; packet README:131 |
| Gate F NOT RUN; 0 of its 8 checklist boxes ticked | `communication/GATES.md:650–661` |
| 0/32 cases NOT_RUN | packet README:131–134 |
| REVIEWED: partial report, ledger + protocol scope, exact hash | `communication/BOARD.md:54–68` (A3-0160); packet README:3–6 |
| F0 accepted 4 Nov | `communication/DECISIONS.md:516–540` (D53) |
| Stages 1–2; stage-3 executor, snapshot materialiser, RPC capture (synthetic) | `communication/BOARD.md:1–52` (A3-0161..0163); RQ2:3–4 |
| Merged snapshot: ledger 316 passed; protocol 3,226 passed / 201 skipped; evaluation 3,097 passed / 4 failed (host-specific, same on agent-3 ca82b7f) | **`origin/agent-1`** `communication/agent-1/outbox/0145-note-code-merge-final-branch.md:39–46` (A1-0145) |
| Still-needed list | packet README:131–141; GATES.md:652–659; RQ2:350–356 |

## Slide 28 — Limitations and lessons

| Item | Source |
|---|---|
| Limitations | RQ2 §5 (lines 350–356), §3 (lines 265–278); RQ1 §15 (lines 1146–1183) |
| What F does not prove | RQ2:179, 277, 350–356; `SPEC.md:75, 83` |
| Lesson 1 (K1) | slide 23 sources |
| Lesson 2 (vacuous scan) | RQ2:49–55 |
| Lesson 3 (q2 manifest says repaired-f; threshold 2 vs 3 read back) | A1-0143 §2.1 (lines 27–41) |
| Lesson 4 (first-line hash) | A1-0141 §5 |
| Lesson 5 (signing vs ledger) | RQ2:288–291, 316–319 |

## Slide 29 — Conclusion

| Item | Source |
|---|---|
| 8 / 20 / 4 of 32; 19 repaired rows | slide 13 tally |
| ≤ 30 s | RQ1:832–833 |
| RQ2 partial answer | RQ2:19–24 |
| One unavailable certifies, two time out | RQ2:173–179 |
| +3.7% to +11.0% | RQ2:185–187 |
| Next steps before a gate F decision | packet README:131–141; `communication/GATES.md:650–661` |

---

## Facts left out because no file supports them, or by instruction

- **"112 services"** in the gate run (on the mid-eval's commented-out gate slide): not found in `RQ1-E.md`
  or the gate manifest, so not used.
- **A date for a gate F decision**: no file gives one; the deck gives none.
- **A mitigation for the forged-credential grant**: none is designed or tested in the sources; the Q&A says so.
- **The paper's prototype performance** (603 ms per access, Fig. 11): kept out of the two paper slides to fit;
  it is only in a speaker note (paper Table 4; mid lines 303, 310).
- By instruction, the deck presents the project as RQ1 and RQ2 only.
