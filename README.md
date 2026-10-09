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
