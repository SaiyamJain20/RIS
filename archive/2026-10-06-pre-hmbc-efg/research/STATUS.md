# STATUS - where we are and how to resume (updated 2026-10-05)

## State
- **Planning and evidence gathering are complete.** Two web-search verification rounds, three local audits (paper+code, JANUS code, 2020 design) and a plan audit are done. Results: `research/reports/`, `research/round1/`, `research/round2/`.
- **Plan:** `docs/PLAN_WORKSHOP.md` (v6, working) and `docs/TEAM_PLAN_ALL_CASES.md` (shareable: Part I guide + Part II = a copy of the plan). **If you edit one, update the other.**
- **Recommendation (both web sessions):** E+F+G first, D second, A third. A is falling (~45-50%): watch arXiv for the Liu-Li companion paper (arXiv 2606.16763) and read the Hybrid-TPR-ABE full text.
- **Nothing has been implemented or run.** All JANUS findings are static readings.
- Repo layout was reorganised on 2026-10-05 (see `README.md`); superseded early plans were removed (recoverable from git history, commit `cd737e4`). Nothing has been committed since the reorganisation.

## Pending - humans (see `docs/OPEN_QUESTIONS.md`)
1. Ask the instructors: is "security analysis + hardening of two published systems" acceptable as the extension? ROR/ProVerif expected? OK to send a private advisory to the authors?
2. Library reading (IIIT-H access): `docs/LIBRARY_TASKS.md` (Google Scholar "Cited by" and the Fabric-vulnerabilities paper first).
3. Week-0 decision A / D / E+F+G; assign owners; two people re-open the key [V] code lines (list in `docs/TEAM_PLAN_ALL_CASES.md`, checklist item 3).
4. Re-check every inferred 2027 venue date in January 2027 (CODASPY paper deadline 23 Nov 2026 and ASIACCS cycle 2 on 11 Dec 2026 are only realistic for the lean version).

## Next steps once E+F+G is confirmed (plan Section 9.2)
W1: consolidated catalogue + `work/harness/` set-up (mocha + sinon, pure-JS deps) + Hardhat project. **W2 gate: at least 3 HIGH findings (about 6 of the 10 chosen) reproduce at mock-stub level**, else shrink to design-level and formal parts or switch to D. Then Vault tests, Solidity re-implementation, formal models, repairs, measurements, disclosure, paper.

## If you are an AI session resuming this work
Read `README.md`, this file, then `docs/TEAM_PLAN_ALL_CASES.md` Part I. Constraints: the user's laptop has ~14 GB RAM and has OOM-crashed before (keep local work light, no heavy builds); WebSearch is capped per session (set `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`); account usage limits have stopped parallel agents before (use at most 3-4 sub-agents). Do not commit unless asked. Prior sessions' coordination protocol is in the two `RECHECK*_COMMS.md` files.
