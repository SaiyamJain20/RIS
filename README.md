# Team 17: HMBC presentation (Research in Information Security)

## End presentation (17 Nov 2026)

**Open [`hmbc-end-presentation.pdf`](hmbc-end-presentation.pdf) for the end-evaluation deck** (29 slides, same style,
about 22½ minutes spoken). It explains the paper in two slides, then the project so far as two research questions,
each in full. RQ1 is complete (gate E PASS, 12 Oct). RQ2 has offline and peer-reviewed partial results, but its
execution plan is a DRAFT, gate F is **NOT RUN** and all 32 F cases are NOT_RUN. Slide map and status:
[`README-endeval.md`](README-endeval.md); speaker script: [`script-hmbc-end-presentation.md`](script-hmbc-end-presentation.md);
source for every number: [`sources-end-presentation.md`](sources-end-presentation.md). Content snapshot:
`Code_Merge_Final` fc80bf0 plus agent-1 messages to A1-0145.

## Mid presentation (12 Oct 2026)

**Open [`hmbc-presentation.pdf`](hmbc-presentation.pdf) to view the deck.** It is LaTeX Beamer with the Metropolis theme, 16:9.

| Slides | Content |
|---|---|
| 1–8 | The paper: Malamas et al., *A Hierarchical Multi Blockchain for Fine Grained Access to Medical Data*, IEEE Access 8 (2020) |
| 9–10 | JANUS (Appl. Sci. 2023): what it adds on top of HMBC, and what it changes |
| 11–12 | Our project: the three research questions RQ1/RQ2/RQ3; why this direction; literature |
| 13–14 | Tech stack: the paper vs. JANUS vs. ours, and why |
| 15–22 | RQ1, complete: the gaps in HMBC's flow (RQ1-01/02/03); method; the repaired-e design; results for RQ1-01, RQ1-02 (with the revocation window) and RQ1-03; mutants and ProVerif; what RQ1 shows, why it matters and its limits |
| 23–24 | Next: RQ2, then RQ3; questions |

Speaker script for the whole deck in about 20 minutes, with Q&A backups: [`script-hmbc-presentation.md`](script-hmbc-presentation.md). The longer [`script-hmbc-presentation-30min.md`](script-hmbc-presentation-30min.md) was written for the earlier 26-slide deck and is background only.

## Live status

Slides 15–22 summarise RQ1 (Phase E) as recorded on the `agent-1` branch: the gate E run
`E-gate-20261012`, `evaluation/reports/RQ1-E.md` and the gate E decision in `communication/GATES.md`.
Before 12 Oct, the RQ1 slides summarised the live project state from the
`agent-1`, `agent-2` and `agent-3` branches. The deck is refreshed about **every hour** while Saiyam's
Claude Code session is running. Each refresh is one commit on this branch, and the changelog below
records the time and the source commits.

Results are labelled by evidence level:
- **[I]:** integrated run by the independent evaluator;
- **[R]:** cross-run by the module owners;
- **[U]:** unit tests;
- **[F]:** a formal model run by the evaluator.

Nothing on these slides is a passed gate unless the board says so.

## Build

Use XeLaTeX or LuaLaTeX (needed for the Fira fonts):

```bash
tectonic -X compile hmbc-presentation.tex     # or: latexmk -xelatex hmbc-presentation.tex
```

On Overleaf: upload the `.tex` file and `figures/`, then set *Menu → Compiler → XeLaTeX*.

## Sources

- Paper figures 1, 9, 10 and 11 are taken from HMBC2020 (CC BY 4.0). The other diagrams are redrawn.
- JANUS facts come from the JANUS paper (CC BY 4.0).
- Project numbers come from the agents' messages and the board on their branches.

## Changelog

- 2026-10-09 04:42 IST: first push. Paper slides 1–8, slides 9–19 on JANUS, the stack and E/F/G, and
  the revocation-window chart (A1-0046 / A2-0026). Heads: agent-1 48d85e8, agent-2 2fd871d, agent-3 7fbd1ed.
- 2026-10-09 05:30 IST: new slide 18 with the evaluator's ProVerif check (A3-0033): 8-field agreement is true
  for repaired-e, and the no-destination mutant has an attack trace. Timeline: E2 shows ProVerif done. The
  slide 16 to-do note is updated. The E2 crash start contract is accepted (A3-0034, A1-0047, A2-0027);
  the 56-case runs and gate E are not run yet. Heads: agent-1 af7a60d, agent-2 4f39643, agent-3 feae05d.
- 2026-10-09 06:37 IST: slide 16 gets a new tile, 6/6 integrated crash/recovery runs [I] (A3-0036), and the
  crash row is marked integrated. The to-do note now lists the other 50 cases, the expired-retry probes
  (freeze A3-0037, ACKed in A1-0050 and A2-0030) and the mutants. The slide 11 timeline shows ProVerif +
  crash slice. Gate E is not run; F/G are locked. Heads: agent-1 38e0a95, agent-2 3d60b40, agent-3 c7eeb0a.
- 2026-10-09 07:37 IST: slide 16 tile and crash row now include the integrated expiry check, 6/6 [I]
  (A3-0038): a retry after grant expiry returns EXPIRED and nothing changes. The to-do note names the
  duplicate-outcome probe as next (freeze A3-0039, ACKed in A1-0052 and A2-0032). Gate E is not run; F/G
  are locked. Heads: agent-1 b3cfb15, agent-2 fbab2f2, agent-3 abc2db3.
- 2026-10-09 08:33 IST: slide 16 gets a new row, duplicate outcome rejected with REPLAY, 3/3 [I] (A3-0040);
  classed SUPPORTED in the paper version and REPAIR_SUPPORTED in the repaired version. The second tile now
  reads 9/56 evaluator-run cases (6 crash + 3 duplicate), all as expected. To-do: the other 47 cases and
  the mutants. The slide 11 timeline shows E2 at 9/56 run plus ProVerif. Gate E is not run; F/G are
  locked. Heads: agent-1 8c991de, agent-2 e6a8927, agent-3 46af1e2.
- 2026-10-09 10:30 IST: slide 16 gets a new row for the E01 identical-replay slice (A3-0042), which FAILED
  overall. The two paper versions complete: REPLAY, nothing changes, 2/2 [I]. In repaired-e the replay was
  rejected but the run then hit grant expiry (runner timing), so it is incomplete and a re-run is due. The
  tile now reads 11/56 evaluator-run cases as expected, 1 re-run due. To-do: the other 44 cases, the
  repaired-e re-run and the mutants. The slide 11 timeline shows 11/56 run. The table is tightened to fit.
  Gate E is not run; F/G are locked. Heads: agent-1 194379c, agent-2 ca1b8ce, agent-3 b209386.
- 2026-10-09 11:30 IST: no new results. Agent 3 diagnosed the repaired-e replay timing and requested a
  grouped re-run freeze (A3-0043, A3-0044), and the owners reviewed it (A1-0055, A2-0035, A2-0036). Only
  the status stamp changed. Heads: agent-1 2d2d386, agent-2 d408669, agent-3 8f1d2e1.
- 2026-10-09 13:09 IST: committed Saiyam's own edits: the 'Mid presentation' title; Phases E/F/G renamed to
  RQ1/RQ2/RQ3; the timeline, stat tiles, footnotes and status stamps removed. Three compile slips fixed: an
  extra '}' in the slide 8 alert-block title, a stray '}' on slide 11, and the RQ2 card title field.
  Slide 16 replay row: the repaired-e re-run passed, REPLAY, nothing changes (grouped replay 3/3 [I],
  A3-0045). The evaluator has now run 12/56 cases (44 remain). A1-0058 caught a subject-oracle code error
  (WRONG_SUBJECT = 2), fixed in A3-0047; no live subject result yet. Gate E is not run; RQ2/RQ3 are locked.
  Heads: agent-1 e66eeb9, agent-2 96ebe16, agent-3 fbebab7.
- 2026-10-09 16:30 IST: no new results. Agent 3 prepared the subject-substitution collector and checker
  (A3-0048, A3-0049), with no live run yet; 44 cases remain. The deck is unchanged. Heads: agent-1 e66eeb9,
  agent-2 96ebe16, agent-3 8e5a6dd.
- 2026-10-12: Phase E rewritten as slides 15–24 after gate E PASS (solo phase; GATES.md decision of
  2026-10-12). New slides: where we are (timeline and headline numbers), the three gaps in the paper's
  flow, the method (profiles, frozen 56-row catalog, result classes), the repaired-e design (with the
  13-step DecisionVerifier), one results slide each for E01/E02/E03, mutants and ProVerif, the gate run
  (all 56 rows coloured by class) and a summary of findings, impact and limits. The old slides 15–18 are
  folded into these. Slide 25 is the next step: F (RQ2), then G (RQ3). Slides 1–14 are unchanged.
  Every number comes from `evaluation/reports/RQ1-E.md` (69dabfba..) and the gate evidence
  (manifest 908fd615..); the window chart is still the owner measurement (A1-0046 / A2-0026). Stated
  limits: integrated mutant matrix and integrated window not run; final reviews correlated (same model).
  Heads: agent-1 6911478, agent-2 96ebe16, agent-3 8e5a6dd.
- 2026-10-12 evening: Saiyam's edits. The "where we are" and "gate E" slides are commented out. Phases
  E/F/G are renamed to RQ1/RQ2/RQ3, and the case families to RQ1-01/02/03. Some caveat lines are
  removed (the mutant-run note, the correlated-review note, two limits). The deck is recompiled: 24 pages.
  The 20-minute script is updated to match; its Q&A backups keep the removed caveats as answers.
