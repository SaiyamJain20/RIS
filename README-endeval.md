# Team 17: HMBC end-evaluation presentation (Research in Information Security)

**Open [`hmbc-end-presentation.pdf`](hmbc-end-presentation.pdf) to view the deck.** It is LaTeX Beamer with the
Metropolis theme, 16:9, and uses the same preamble, colours and macros as the mid-eval deck
(`origin/slides:hmbc-presentation.tex`), so the two read as one series. 28 pages, about 21½ minutes spoken
(about 23 with transitions).

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
| 6–12 | RQ1 in full, as one story: the question and Gap 1–3 (decision provenance, trust-list freshness, audit evidence); the repaired-e flow and Fix 1–3, numbered and coloured like the gaps; Gap 1, Gap 2 (with the revocation window) and Gap 3 results in plain ✓/✗ words; gate E (56-row grid, mutants and ProVerif in one line, verdict); what RQ1 shows |
| 13–15 | RQ2: the question and fault model (n = 4, q = 3, f = 1); the design (three signed paths, governance, single-signing witnesses); how RQ2 will be judged (32 cases, six families, seven stages) vs the offline evidence that exists |
| 16–18 | RQ2 safety: TLC finite model (five configurations); oracle/store differential and seven mutation controls; M5 pool sweep (f = 1 vs the f = 2 control) |
| 19–21 | RQ2 availability (M2 virtual, M6 real-process); cost (M1/M1b/M1c gas chart); durability (the K1 kill-test story, 29/40 then 40/40) |
| 22–25 | RQ2 trust matrix; out-of-bound results (permanent DBC halt, forged-credential grant, DENY/ALLOW double certificates); assurance process and the errors we kept; honest status (plan DRAFT, gate F NOT RUN, 0/32 cases) |
| 26–27 | Limitations and lessons; conclusion |
| 28 | Questions |

Speaker script with per-slide timing and Q&A backups: [`script-hmbc-end-presentation.md`](script-hmbc-end-presentation.md)
(about 21½ minutes spoken; suggested three-way split 1–8 / 9–17 / 18–28).

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
  slides 6–12 are adapted from mid-eval slides 15–22 and keep their numbers. RQ2 numbers come from
  `evaluation/reports/RQ2-F-DRAFT.md` (`e59a51cd..`), its receipts under `evaluation/evidence/f/`, and the
  agents' outbox messages (A1-0123..0126, A1-0136..0144, A2-0087..0091). The merged-snapshot test counts on
  slide 25 come from A1-0145 on `origin/agent-1`.
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
