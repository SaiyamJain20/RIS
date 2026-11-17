# Team 17: HMBC end-evaluation presentation (Research in Information Security)

**Open [`hmbc-end-presentation.pdf`](hmbc-end-presentation.pdf) to view the deck.** It is LaTeX Beamer with the
Metropolis theme, 16:9, and uses the same preamble, colours and macros as the mid-eval deck
(`origin/slides:hmbc-presentation.tex`), so the two read as one series. 24 pages, about 19 minutes spoken
(about 21 with transitions).

**Status on these slides (17 Nov 2026):** RQ1 gate E **PASS** (12 Oct 2026). RQ2: the F execution plan is a
**DRAFT**, gate F is **NOT RUN**, and all **32 F cases are NOT_RUN**; runner stages 3–7 are in progress; the
partial RQ2-F report is peer-reviewed in ledger and protocol scope at its exact hash (`e59a51cd..`). Everything
shown is a **paper-derived reconstruction**, not the authors' implementation.

| Slides | Content |
|---|---|
| 1 | Title, with the status line |
| 2–3 | The paper: the problem and HMBC's architecture (actors, proxy and domain chains, six contracts); a five-stage overview of how access works, split decryption, and the assumptions our RQs probe |
| 4 | JANUS: the extension of HMBC by the same authors (Appl. Sci. 2023), its main extensions, and what it leaves open |
| 5 | What we set out to answer: RQ1 and RQ2, each with the question, why it matters, how we answer it, and its status |
| 6–11 | RQ1 in full, as one story: the question and Gap 1–3 (decision provenance, trust-list freshness, audit evidence); the RQ1 repair's flow and Fix 1–3, numbered and coloured like the gaps; Gap 1, Gap 2 (with the revocation window) and Gap 3 results in plain ✓/✗ words; what RQ1 shows, with the gate E verdict (PASS, 56/56) and the mutants/ProVerif check in one line |
| 12–14 | RQ2: the question and fault model (n = 4, q = 3, f = 1); the design in plain words (what is certified, what the witnesses attest, where it is checked); how RQ2 is judged (six case families, the gate's requirements) |
| 15–20 | RQ2 experiment results, styled like the RQ1 gap results (a ✓/✗ table, an orange "What it means" box, small side notes): 1 why three approvals are needed (TLC); 2 certificate collection with real signatures; 3 the availability boundary; 4 can a crash split a signing record (29/40 → 40/40); 5 when a different signature becomes legal (180 cases, seven rule mutations); 6 cost (gas table and chart) |
| 21–22 | Security findings beyond the fault bound (three calm cards); what RQ2 shows, and why it matters (mirrors the RQ1 slide; states gate F NOT RUN and that the 32-case study is still to run) |
| 23 | Conclusion: RQ1 answered, RQ2 partial answer (the integrated 32-case gate-F study still to run), and Next: try the analysis on JANUS; the planned key-lifecycle question |
| 24 | Questions |

Speaker script with per-slide timing and Q&A backups: [`script-hmbc-end-presentation.md`](script-hmbc-end-presentation.md)
(about 19 minutes spoken; suggested three-way split 1–8 / 9–16 / 17–24).

Source map for every number on every slide: [`sources-end-presentation.md`](sources-end-presentation.md).

## Evidence labels

Result slides carry the same labels as the mid-eval deck:
- **[I]:** integrated run by the independent evaluator;
- **[R]:** cross-run by the module owners;
- **[U]:** unit tests, or offline runs over real module code with synthetic fixtures;
- **[F]:** a formal model run by the evaluator.

There is **no [I] result for RQ2 yet**: every RQ2 number is an isolated, offline or formal result, and none is
one of the 32 F cases. Nothing on these slides is a passed gate unless `communication/GATES.md` says so.

## Build

Use XeLaTeX or LuaLaTeX (needed for the Fira fonts):

```bash
tectonic -X compile hmbc-end-presentation.tex     # or: latexmk -xelatex hmbc-end-presentation.tex
```

On Overleaf: upload the `.tex` file and `figures/`, then set *Menu → Compiler → XeLaTeX*.

The page counter in the slide corner is one lower than the PDF page number (the title page is not counted),
as in the mid-eval deck.

## Sources

- Primary snapshot: `origin/Code_Merge_Final` (`fc80bf0`), the ownership merge of the three agent branches.
  RQ1 numbers come from `evaluation/reports/RQ1-E.md` (`69dabfba..`), `communication/GATES.md`,
  `interfaces/v1/source-map.csv` and `assumptions.csv`, and the owner window measurements A1-0046 / A2-0026; RQ1
  slides 6–11 are adapted from mid-eval slides 15–22 and keep their numbers. RQ2 numbers come from
  `evaluation/reports/RQ2-F-DRAFT.md` (`e59a51cd..`), its receipts under `evaluation/evidence/f/`, and the
  agents' outbox messages (A1-0123..0126, A1-0136..0144, A2-0087..0091).
- Paper figure 1 is taken from HMBC2020 (CC BY 4.0). The other diagrams and charts are redrawn from the paper or
  our own.
- JANUS appears on one slide (slide 4) as related work, with facts from mid-eval slides 9–10 and the JANUS paper
  (Malamas et al., Appl. Sci. 13(1):566, 2023): no JANUS code, design or bug claims are used.

## Changelog

- 2026-11-17: first version of the end-evaluation deck (24 pages), built from the mid-eval deck's template.
  Source heads: `origin/Code_Merge_Final` fc80bf0 (agent-1 d7bac30, agent-2 faa4e63, agent-3 ca82b7f);
  A1-0145 at agent-1 03cbf39.
- 2026-11-17, later: restructured on the human's request into a complete account of the project so far: the
  paper in two slides, a project slide, RQ1 in full (nine slides adapted from mid-eval slides 15–22, same
  numbers) and RQ2 in full (thirteen slides). The project is presented as two research questions. 29 pages;
  script retimed to about 22½ minutes. Same source heads.
- 2026-11-17, later still: on the human's request, slide 3's access flow redrawn as a five-stage overview
  (simplified from paper Fig. 6), and one JANUS slide added after the paper slides (its footnote on the project
  slide removed). 30 pages; script retimed to about 23 minutes.
- 2026-11-17, last: on the human's request, slide 5 now explains only the two research questions (question, why
  it matters, how we answer it, status) under the heading "What we set out to answer: two research questions";
  the evidence-label legend moved to a one-line legend on slide 9, the first slide that uses a label.
  30 pages; about 23 minutes spoken.
- 2026-11-17, RQ1 rework on the human's request: removed the RQ1 method slide and the mutants/ProVerif slide
  (their key points folded into one line each on the repaired-e and gate E slides); the gaps and the fixes are
  now numbered and coloured alike (Gap/Fix 1 decision provenance, 2 trust-list freshness, 3 audit evidence);
  the repaired-e flow is redrawn as five stages with fix badges, and its 13-check strip removed; results slides
  use plain ✓/✗ words instead of class chips, here and on the gate E slide. 28 pages; about 21½ minutes spoken.
- 2026-11-17, RQ2 presentation round on the human's request: gate E slide redrawn (three stat tiles, plain-word
  grid legend); "Limits we state" removed from "What RQ1 shows"; the internal profile name replaced by "our RQ1
  repair" in visible text (kept once, in small print on slide 7); the RQ2 design table rewritten in plain words;
  "How RQ2 is judged" lists the six families and the gate's requirements (no case counts, no evidence inventory);
  the RQ2 results re-cut as Experiments 1–6 plus the security findings, following the team's short report, with
  each report claim checked against the repository (see `sources-end-presentation.md`). Gate F is still NOT RUN
  (status slide). 28 pages; about 22 minutes spoken.
- 2026-11-17, on the human's request: the gate E slide is removed (its verdict, the 56/56 match and the
  mutants/ProVerif point are one line on "What RQ1 shows"); Experiments 1–6 restyled like the RQ1 gap results:
  "Experiment N result" titles, a ✓/✗ table, an orange "What it means" box and short side notes. 27 pages; about
  21 minutes spoken.
- 2026-11-17, on the human's request: Experiment 6 moved before the security findings; the security findings
  redrawn as three calm cards; the trust-matrix, assurance and honest-status slides removed (their key points
  are one limitations bullet and the "What RQ2 shows" gate line); new "What RQ2 shows, and why it matters"
  slide mirroring the RQ1 one, which states gate F NOT RUN and that the integrated 32-case study is still to
  run. 25 pages; about 20 minutes spoken.
- 2026-11-17, on the human's request: "Limitations and lessons" removed; the conclusion now summarises the slides
  (RQ1 answered; RQ2 partial, with "Still to run: the integrated 32-case gate-F study") and its Next card has two
  short items, trying the analysis on JANUS and the planned key-lifecycle question. 24 pages; about 19 minutes
  spoken.
