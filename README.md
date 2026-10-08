# Team 17: HMBC presentation (Research in Information Security)

**Open [`hmbc-presentation.pdf`](hmbc-presentation.pdf) to view the deck.** It is LaTeX Beamer with the Metropolis theme, 16:9.

| Slides | Content |
|---|---|
| 1–8 | The paper: Malamas et al., *A Hierarchical Multi Blockchain for Fine Grained Access to Medical Data*, IEEE Access 8 (2020) |
| 9–10 | JANUS (Appl. Sci. 2023): what it adds on top of HMBC, and what it changes |
| 11–12 | Our project: RQ1/RQ2/RQ3 mapped to Phases E/F/G; why this direction; literature |
| 13–14 | Tech stack: the paper vs. JANUS vs. ours, and why |
| 15–17 | Phase E: what we add, results so far, the measured revocation window |
| 18–19 | Plan for F and G; questions |

## Live status

Slides 11 and 15–17 summarise the live project state from the `agent-1`, `agent-2` and `agent-3`
branches. The **"Status:" stamp** on slides 11 and 16 gives the time of the last refresh. The deck is
refreshed about **every hour** while Saiyam's Claude Code session is running. Each refresh is one
commit on this branch that says what changed.

Results are labelled by evidence level:
- **[I]:** integrated run by the independent evaluator;
- **[R]:** cross-run by the module owners;
- **[U]:** unit tests.

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
  the revocation-window chart (A1-0046 / A2-0026).
