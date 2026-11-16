# Team 17: HMBC end-evaluation presentation (Research in Information Security)

**Open [`hmbc-end-presentation.pdf`](hmbc-end-presentation.pdf) to view the deck.** It is LaTeX Beamer with the
Metropolis theme, 16:9, and uses the same preamble, colours and macros as the mid-eval deck
(`origin/slides:hmbc-presentation.tex`), so the two read as one series. 24 pages, about 18 minutes spoken (20 with transitions).

**Status on these slides (17 Nov 2026):** RQ1 gate E **PASS** (12 Oct 2026). RQ2: the F execution plan is a
**DRAFT**, gate F is **NOT RUN**, and all **32 F cases are NOT_RUN**; runner stages 3–7 are in progress; the
partial RQ2-F report is peer-reviewed in ledger and protocol scope at its exact hash (`e59a51cd..`). RQ3 (G) is
**LOCKED** and not started. Everything shown is a **paper-derived reconstruction**, not the authors'
implementation.

| Slides | Content |
|---|---|
| 1 | Title, with the status line |
| 2–3 | Recap: the paper in one slide; JANUS (related system only) and the stack we built |
| 4–5 | Our three RQs and where each stands (timeline); method, evidence labels and finding classes |
| 6–8 | RQ1, complete: the three gaps and the repaired-e profile; results, paper vs repaired, with the revocation window; gate E (56-row grid, mutants, ProVerif, verdict) |
| 9–11 | RQ2: the question and fault model (n = 4, q = 3, f = 1); the design (three signed paths, governance, single-signing witnesses); how RQ2 will be judged (32 cases, six families, seven stages) vs the offline evidence that exists |
| 12–14 | RQ2 safety: TLC finite model (five configurations); oracle/store differential and seven mutation controls; M5 pool sweep (f = 1 vs the f = 2 control) |
| 15–17 | RQ2 availability (M2 virtual, M6 real-process); cost (M1/M1b/M1c gas chart); durability (the K1 kill-test story, 29/40 then 40/40) |
| 18–20 | RQ2 trust matrix; out-of-bound results (permanent DBC halt, forged-credential grant, DENY/ALLOW double certificates); assurance process and the errors we kept |
| 21–23 | Honest status of RQ2; limitations and lessons; conclusion |
| 24 | Questions |

Speaker script with per-slide timing and Q&A backups: [`script-hmbc-end-presentation.md`](script-hmbc-end-presentation.md)
(about 18 minutes spoken; suggested three-way split 1–8 / 9–16 / 17–24).

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
  RQ1 numbers come from `evaluation/reports/RQ1-E.md` (`69dabfba..`) and `communication/GATES.md`; RQ2 numbers
  from `evaluation/reports/RQ2-F-DRAFT.md` (`e59a51cd..`), its receipts under `evaluation/evidence/f/`, and the
  agents' outbox messages (A1-0123..0126, A1-0136..0144, A2-0087..0091). The merged-snapshot test counts on
  slide 21 come from A1-0145 on `origin/agent-1`.
- Paper figure 1 is taken from HMBC2020 (CC BY 4.0). The other diagrams and charts are our own.
- JANUS appears only as a related system, as in the mid-eval deck: no JANUS code, design or bug claims are used.

## Changelog

- 2026-11-17: first version of the end-evaluation deck, built from the mid-eval deck's template. Recap
  condensed from mid-eval slides 1–14; RQ1 condensed from mid-eval slides 15–22 with the same numbers; RQ2
  slides new. Source heads: `origin/Code_Merge_Final` fc80bf0 (agent-1 d7bac30, agent-2 faa4e63,
  agent-3 ca82b7f); A1-0145 at agent-1 03cbf39.
