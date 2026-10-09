# Team 17: HMBC presentation (Research in Information Security)

**Open [`hmbc-presentation.pdf`](hmbc-presentation.pdf) to view the deck.** It is LaTeX Beamer with the Metropolis theme, 16:9.

| Slides | Content |
|---|---|
| 1–8 | The paper: Malamas et al., *A Hierarchical Multi Blockchain for Fine Grained Access to Medical Data*, IEEE Access 8 (2020) |
| 9–10 | JANUS (Appl. Sci. 2023): what it adds on top of HMBC, and what it changes |
| 11–12 | Our project: RQ1/RQ2/RQ3 mapped to Phases E/F/G; why this direction; literature |
| 13–14 | Tech stack: the paper vs. JANUS vs. ours, and why |
| 15–18 | Phase E: what we add, results so far, the measured revocation window, the ProVerif check |
| 19–20 | Plan for F and G; questions |

## Live status

Slides 11 and 15–18 summarise the live project state from the `agent-1`, `agent-2` and `agent-3`
branches. The **"Status:" stamp** on slides 11 and 16 gives the time of the last refresh. The deck is
refreshed about **every hour** while Saiyam's Claude Code session is running. Each refresh is one
commit on this branch that says what changed.

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
