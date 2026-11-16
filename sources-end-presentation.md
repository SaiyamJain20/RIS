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
**mid** = `origin/slides:hmbc-presentation.tex` (the mid-eval deck).

Every result in the deck is a paper-derived reconstruction result on synthetic fixtures, not a result about
the HMBC authors' implementation.

---

## Slide 1 — Title

| Item | Source |
|---|---|
| Status line: gate E PASS; gate F NOT RUN (0/32); G LOCKED | `communication/GATES.md:621,648,661,675`; RQ2:3; BOARD A3-0163 (`communication/BOARD.md:13`) |
| Fig. 1 | `origin/slides:figures/fig1-architecture.png` (paper Fig. 1, CC BY 4.0) |

## Slide 2 — Recap: HMBC

| Item | Source |
|---|---|
| Architecture, PBC/DBC roles, six contracts, split decryption | paper §III, Fig. 1/5/6 (`references/HMBC2020.pdf`); mid lines 153–284 |
| 603 ms per access | paper Table 4 (527 ms contracts + 2 ms cache + 74 ms user); mid lines 303, 310 |
| The paper's assumptions (isolation, honest majority, secure crypto, uncompromised keys) | paper §V; mid lines 322–324 |

## Slide 3 — Recap: JANUS and our stack

| Item | Source |
|---|---|
| Paper and JANUS columns | mid lines 371–383 and 431–448 (JANUS: Appl. Sci. 13(1):566, 2023) |
| Anvil chain ids 18545 / 28545; Solidity 0.8.37; Foundry 1.8.5; ProVerif 2.05 | mid lines 438–445; RQ1:244–245 |
| Governance contract added in F | MEAS:38–39 ("new Governance 4,829") |
| Four witnesses with durable SQLite stores | MEAS:42–43; RQ2:132 |
| TEST-ONLY synthetic keys | RQ2:270 |
| TLA+/TLC 2.19 | RQ2:141 |
| ABE real only in RQ3 after G0 | `PLAN.md:224–234`; `SPEC.md:96–100` |

## Slide 4 — Three RQs and status

| Item | Source |
|---|---|
| RQ wording | `SPEC.md:22–24` |
| 8 Oct: interface v1 / 56-row catalog frozen | `communication/DECISIONS.md:107` (D38, `E0-v1-r6-20261008`, FREEZE f700292e..); RQ1:240–243 |
| 12 Oct: gate E PASS; F0 planning authorised | `communication/GATES.md:611–617, 648` |
| 4 Nov: F0 design accepted | `communication/DECISIONS.md:516–540` (D53) |
| 13–15 Nov: TLC, measurements, K1 fix | `EV/decision-quorum-tlc-20261113/`; MEAS (2026-11-14); `evaluation/evidence/reviews/proxy-k1-20261114/README.md` |
| 16 Nov: report reviewed at exact hash | `communication/BOARD.md:54–68` (A3-0160) |
| 17 Nov: plan DRAFT, 0 of 32 run | `communication/BOARD.md:13` (A3-0163); `EV/partial-report-packet-20261115/README.md:131–134` |

## Slide 5 — Method and evidence labels

| Item | Source |
|---|---|
| 41 recorded completions A01–A41 | RQ1:35, 106 |
| Profiles paper-strict / paper-minimal / repaired-e / mutants | RQ1:170–253; mid lines 577–583 |
| repaired-f and mutant-f-q2 | A1-0143 §1–2.1 (lines 16–41) |
| Freeze → ACK → run → review; failed trials kept | RQ1:250–253 |
| Portable roles; same model family | `communication/DECISIONS.md:598–615` (D57) |
| Labels [I]/[R]/[U]/[F] | `origin/slides:README.md` ("Results are labelled by evidence level") |
| Five finding classes | `AGENTS.md` ("Evidence" section) |
| "No [I] result for RQ2" | RQ2:3–10, 324 ("No row is an integrated F result") |

## Slide 6 — RQ1 gaps and repair

| Item | Source |
|---|---|
| Gaps RQ1-01/02/03 | RQ1:44–57; mid lines 564–566 |
| Repaired-e checks, request lifetime ≤ 30 s | RQ1:58–75; mid lines 630–641 |
| 13-step DecisionVerifier, step 12 reserved | mid lines 645–652 |

## Slide 7 — RQ1 results [I]

| Item | Source |
|---|---|
| Per-case outcomes and error codes, paper vs repaired | RQ1:34–75 (§0); RQ1 §6 rows (lines 410–555); mid lines 662–669, 697–701, 744–748 |
| Identical replay rests on deterministic grant id (A25) | RQ1:36–37 |
| Window W = min(...) ≤ 30 s | RQ1:832–833 |
| W = 2 / 6 / 11 / 21 s for delays 0 / 5 / 10 / 20 s; 26 s no barrier | RQ1:820–823 (owner measurement A1-0046) |
| Paper-strict still grantable at +65 s | RQ1:825 |
| One trial per delay; not the gate run | RQ1:837–839 |

## Slide 8 — Gate E

| Item | Source |
|---|---|
| 32 paper rows: 8 SUPPORTED, 20 SPEC_GAP, 4 BLOCKED; 24 repaired-e rows: 19 REPAIR_SUPPORTED, 5 SUPPORTED | tally of the GATE column of RQ1 §6 (lines 410–555); same grid as the commented-out mid slide (mid lines 842–853) |
| 56 PASS, 0 FAILED, 0 NOT_RUN | RQ1:356 |
| 4,749 s | RQ1:361 |
| ProVerif matched | RQ1:357, 1008 |
| Source/HEAD unchanged | RQ1:358–359 |
| 6 ledger mutants detected; 8 guard rows | RQ1:1031–1059 |
| ProVerif 8-field agreement; destination mutant attack | RQ1:999–1003 |
| Three ACKs A1-0085, S2-0023, S3-0024; decision text | `communication/GATES.md:637–648` |
| Expectations frozen 8 Oct | RQ1:240–243; D38 |

## Slide 9 — RQ2 question

| Item | Source |
|---|---|
| RQ2 wording, n=4, q=3, f=1, safe ledgers, trusted key worker | RQ2:127–129 |
| Overlap ≥ 2 witnesses | RQ2:149 |
| Single signing per key, persisted | `SPEC.md:79`; RQ2:132 |
| One witness per hospital; relay has no key | `SPEC.md:73`; RQ2:272 |
| Not consensus; Anvil not BFT | `SPEC.md:75`; GATES.md:658 |
| Out-of-bound controls f=2, q=2, ≥3 | RQ2:146–147, 269 |

## Slide 10 — RQ2 design

| Item | Source |
|---|---|
| Three signed paths (checkpoint→KSSC, decision→ACSC, receipt→PSC) | RQ2:129–131 |
| ≥ q = 3 of 4 signatures, strictly increasing; 4 of 4 accepted | RQ2:130; A1-0137 §1 table (SigLib.sol:37) |
| Governance: add/remove authority, set CA admins; nonce + expiry | RQ2:131; A1-0137 §1 (Governance.sol:83–86) |
| Removed authority tombstoned | A1-0137 §1 (TMSC.sol:144–147,159) |
| Witness set fixed at deployment | RQ2:269; A1-0137 §1 (A1-0126) |
| Checkpoint: strictly greater sequence; authEpoch / sourceBlockNumber non-decreasing | A1-0137 §2.1 (KSSC.sol:160–163) |
| Receipt names another request/GID/record | RQ1:64–65 (receipt binding) |
| Honest witness REPLAY after grant | A2-0089 §2 (witness_service.py:146–147) |

## Slide 11 — How RQ2 will be judged

| Item | Source |
|---|---|
| 32 cases, six families 8+6+4+8+3+3 | `EV/execution-plan-draft-20261114/plan-draft.json` (`families`); `EV/execution-plan-draft-20261114/README.md:25` |
| Stages 1–7 | `plan-draft.json` (`stages`) |
| status DRAFT, authorizesExecution false | `plan-draft.json` (`status`, `authorizesExecution`) |
| 0 of 32 integrated | `EV/case-coverage-map-20261114/README.md:7`; RQ2:3 |
| Stages 1–2 fail closed (BLOCKED); 3–7 open | RQ2:3–4, 113–115, 355–357 |
| Measurements taken before runner/FREEZE on the human's instruction | MEAS:13–14; RQ2:365–366 |

## Slide 12 — TLC [F]

| Item | Source |
|---|---|
| f=1, q=3: holds, 433 / 108, complete | RQ2:144; `EV/tlc-audit-20261115/README.md:16` |
| f=0: holds, 217 / 81 | RQ2:145; tlc-audit README:17 |
| q=2, f=2, no-persistence: violated | RQ2:146–148; tlc-audit README:18–20 |
| Fresh rerun 15 Nov matched | RQ2:154–158; tlc-audit README:22–24 |
| Agent 1's enumeration matches | RQ2:150–151; A1-0137 §1 ("A1-0122: 108 and 81") |
| Limits (one slot, no expiry …) | RQ2:149–154; tlc-audit README:29–33 |
| First f=0 run deadlocked | RQ2:216–217; `EV/decision-quorum-tlc-20261113/first-run-with-deadlock/` |

## Slide 13 — Oracle/store differential [U]

| Item | Source |
|---|---|
| 180/180 agree, 142 accepts, 38 CONFLICT_PINNED, 0 disagreements | `EV/oracle-store-diff-20261115/README.md:9–14`; RQ2:27–29 |
| Four signing kinds | oracle-store-diff-20261115 README:14 |
| Subtree 7566f63d.. | oracle-store-diff-20261115 README:10–11 |
| Seven mutations 20, 18, 6, 4, 4, 4, 4 | `EV/oracle-mutant-discrimination-20261115/README.md:16–24`; RQ2:33–35 |
| Not completeness | oracle-mutant README:36–38 |
| Store capability vs service reachability; earlier DENY claim wrong | RQ2:293–301; A2-0089 §2 |

## Slide 14 — M5 pool sweep [U]

| Item | Source |
|---|---|
| f=1: 972 cases, 180 certificates, 792 none, 0 invalid, 0 hazards | `EV/pool-sweep-20261115/README.md:20–22`; MEAS:74–77 |
| f=2: 4,374 cases, 330 certificates, 4,044 none, 0 invalid, 2,916 hazards | pool-sweep README:23; MEAS:78–79 |
| 3 distinct sorted valid signers | pool-sweep README:29–30 |
| 9 behaviours; 4×9×27 and 6×81×9 | MEAS:72–79 |
| Hazard definition (potential) | pool-sweep README:25–28; MEAS:80–83 |
| Honest witnesses modelled; byte-identical rerun | pool-sweep README:15–17, 34–38 |

## Slide 15 — Availability

| Item | Source |
|---|---|
| 16 subsets × 5 runs = 80 trials | `EV/availability-receipt-review-20261115/README.md:13–16` |
| 0/1 muted: certificate; 2/3/4 muted (6/4/1 subsets): none by 10,000 virtual ms | MEAS:45–48 |
| Delays 400/300/200/100 ms → certificate at 300 ms | MEAS:49–50 |
| Real witnesses (SQLite, EIP-712) behind virtual transport | MEAS:42–44 |
| Rerun on exact source; 80 trials match | RQ2:117–124, 167–173 |
| M6 table (0.69/0.69/0.78; 0.63/0.55/0.60; 10.54/10.54/10.55; 0.96/0.87/0.88 s) | MEAS:124–129 |
| 4 passed in each of three runs | MEAS:122 |
| 10.5 s = 10 s deadline + overhead | MEAS:130 |
| M6 raw stdout and invocation not retained | availability-receipt-review README:1–6; RQ2:93–95 |

## Slide 16 — Gas [R]

| Item | Source |
|---|---|
| 208,290 / 231,260 / 238,046 (checkpoint) | MEAS:25–27; RQ2:185 |
| 324,323 / 342,261 / 349,053 (decision) | MEAS:28–30; RQ2:186 |
| 533,754 / 553,488 / 560,290 (receipt) | MEAS:86–87; RQ2:187 |
| +11.0% / +5.5% / +3.7% | RQ2:185–187; A1-0137 §1 table |
| ≈ 6.8k gas and 160 B per extra signature | RQ2:188; MEAS:31; A1-0137 §1 table |
| Governance.execute 524,214 / 424,421 / 446,934 | RQ2:189; MEAS:104–108 |
| All under 24,576 B; TMSC 12,635 → 16,127 B | RQ2:190–191; MEAS:37–39; A1-0137 §3 item 2 |
| 21 rows (15 distinct) reproduced exactly, raw logs | A1-0136 lines 14, 27–28; `EV/gas-attachment-audit-20261115/README.md`; RQ2:75–85 |
| Cold-storage hypothesis refuted (231,261 vs 231,260) | MEAS:94–96 (A1-0123) |
| Forge 1.8.5; single deterministic runs; not a fee estimate | MEAS:18–21, 65; RQ2:191–192 |

## Slide 17 — K1 [R]

| Item | Source |
|---|---|
| K1 definition (transaction removed, statements autocommit) | `protocol/tools/run_state_kill_mutants.py:5–6, 25–27` |
| E1 (synchronous=FULL → OFF) survives; needs power loss | run_state_kill_mutants.py:9, 34; proxy-k1 README:65–66 |
| Earlier 3/3 claim not reproduced | `evaluation/evidence/reviews/a2-0086-signing-kill-20261113/README.md:14–16`; RQ2:197–199 |
| 29/40 detected (72.5%), control 40/40 | a2-0086 review README:28–32; RQ2:197–198 |
| After the hook: 40/40 detected, 40/40 controls | `evaluation/evidence/reviews/proxy-k1-20261114/README.md:48–49`; RQ2:199–201 |
| Agent 2: 15/15, 10/10, 81 state tests, 3,226 passed / 201 skipped | A2-0089 lines 22–23; RQ2:201–203 |
| Three defects found and fixed | RQ2:195–197 |
| Dates 13–14 Nov / 14 Nov | review dirs `a2-0086-signing-kill-20261113` (follow-up 2026-11-14), `proxy-k1-20261114` |

## Slide 18 — Trust matrix

| Item | Source |
|---|---|
| Every row | RQ2:265–278 |
| F-19 (compromised worker) NOT_RUN | RQ2:274 |

## Slide 19 — Outside the bound

| Item | Source |
|---|---|
| Saturated sequence / authEpoch / sourceBlockNumber halt; no reset; redeploy | RQ2:269; A1-0137 §2.1 (lines 45–58); A1-0138 §1 (lines 31–49) |
| Decisions stop at once (authEpoch) or after expiry | A1-0138 lines 40–49 |
| < 3 signers cannot poison; 3/3 and 3/3 | A1-0137 lines 54–57; A1-0138 lines 53–61 |
| Forged-credential grant, controls INSUFFICIENT_QUORUM / POLICY_DENIED, 3/3 | A1-0137 §2.2 (lines 60–72); RQ2:269 |
| Records bound only by quorum-signed digest; key release not shown | A1-0137 lines 68–72 |
| f=2: second checkpoint STALE_STATE; second ALLOW REPLAY; DENY/ALLOW both accepted either order, incl. same sequence and after grant | RQ2:279–291; A1-0141 §2–3 (lines 28–43) |
| DENY consumes no nonce (E0 choice, ACSC.sol:186–188) | RQ2:285–286 |
| Honest witness REPLAY at signing | A2-0089 §2; RQ2:288–290 |
| Scratch 4/4, rerun by the evaluator | MEAS:141–144 (hash 5c0f3fb6..); RQ2:281–282 |

## Slide 20 — Assurance

| Item | Source |
|---|---|
| Report SHA-256 e59a51cd..; A1-0142 / A2-0091 no objection in scope; evaluation-tool correctness excluded; not an ACK | `communication/BOARD.md:54–68` (A3-0160); `EV/partial-report-packet-20261115/README.md:3–6, 37–43, 126–130` |
| Honest DENY after used ALLOW: wrong, corrected | RQ2:293–301 |
| Ledger/signing conflation corrected | A1-0141; RQ2:379–386 |
| M1 count 9/9 → 6/6 | A1-0136 §2 (lines 37–43) |
| Plan checker 27/27 vacuous dev-key scan → 28/28 + 9/9 | RQ2:49–55 |
| TMSC 52,339 B parser artifact | MEAS:64; RQ2:217 |
| K1 3/3 → 29/40 → 40/40 | as slide 17 |
| First-line hash missed an edit | A1-0141 §5 (lines 61–67) |
| Same model family; correlated | RQ2:12, 278; D57 |

## Slide 21 — Honest status

| Item | Source |
|---|---|
| Plan DRAFT, authorizesExecution false | `plan-draft.json`; packet README:131 |
| Gate F NOT RUN; 8 checklist items unchecked | `communication/GATES.md:650–661` |
| 0/32 cases; G LOCKED | packet README:131–134; BOARD.md:13 |
| F0 accepted 4 Nov | D53 |
| Report reviewed 16 Nov | BOARD.md:54–68 |
| Stage 1–2; stage-3 executor, snapshot materialiser, RPC capture (synthetic) | BOARD.md:1–52 (A3-0161..0163); RQ2:3–4 |
| Merged snapshot: ledger 316 passed; protocol 3,226 passed / 201 skipped; evaluation 3,097 passed / 4 failed (host-specific, same on agent-3 ca82b7f) | **`origin/agent-1`** `communication/agent-1/outbox/0145-note-code-merge-final-branch.md:39–46` (A1-0145) |
| Still-needed list | packet README:131–141; GATES.md:652–659; RQ2:350–356 |

## Slide 22 — Limitations and lessons

| Item | Source |
|---|---|
| Limitations | RQ2 §5 (lines 350–356), §3 (lines 265–278); RQ1 §15 (lines 1146–1183) |
| What F does not prove | RQ2:179, 277, 350–356; `SPEC.md:75, 83` |
| Lesson 1 (K1) | slide 17 sources |
| Lesson 2 (vacuous scan) | RQ2:49–55 |
| Lesson 3 (q2 manifest says repaired-f; threshold 2 vs 3 read back) | A1-0143 §2.1 (lines 27–41) |
| Lesson 4 (first-line hash) | A1-0141 §5 |
| Lesson 5 (signing vs ledger) | RQ2:288–291, 316–319 |

## Slide 23 — Conclusion

| Item | Source |
|---|---|
| 8 / 20 / 4 of 32; 19 repaired rows | slide 8 tally |
| ≤ 30 s | RQ1:832–833 |
| Partial answer wording | RQ2:19–24 |
| One unavailable certifies, two time out | RQ2:173–179 |
| +3.7% to +11.0% | RQ2:185–187 |
| Next steps | packet README:131–141; `PLAN.md:216–234` (F2, G0) |

---

## Facts left out because no file supports them

- **"112 services"** in the gate run (on a commented-out mid-eval slide): not found in `RQ1-E.md`, so not used.
- **"37 paper passages (S01–S37)"** (mid-eval note): not re-verified in `RQ1-E.md`, so the deck cites only the
  41 completions A01–A41.
- **Machine-B revocation-window values** (mid-eval chart, A2-0026): `RQ1-E.md` §8.5 gives only the A1-0046 values,
  so the deck quotes those only.
- **A date for gate F or for starting RQ3**: no file gives one; the deck gives none.
- **A mitigation for the forged-credential grant**: none is designed or tested in the sources; the Q&A says so.
