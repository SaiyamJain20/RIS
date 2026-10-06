# research/ - evidence trail (history; do not edit)

Everything the plan rests on. Add new evidence as **new files**; do not rewrite these.

## reports/ (agent reports; each ends with a reference list and evidence tags)
| File | What it is |
|---|---|
| `A1_dissection.md` | Audit of both papers and the JANUS code: coverage matrix of gaps, gap cards GC1-GC5 |
| `C_citations_and_authors.md` | Forward citations of HMBC2020/JANUS, the authors' later work, pre-emption map |
| `G1_private_logging.md` | Grounding for case B (sealed need-to-know log) |
| `G2_mpc_dp.md` | Grounding for case A (privacy-loss accounting; MPC + differential privacy) |
| `G37_emergency_access.md` | Grounding for case D (emergency tickets) and misuse detection |
| `G6_hierarchy_trust.md`, `G6_calc.py` | Grounding for case C (governance capture); the back-of-envelope script |
| `R2_design_budget_accountant.md` | Full project design for case A |
| `R2_adversary.md` | Adversarial novelty search against case A |
| `R2_venues.md` | First venue survey |
| `E1_janus_attack_catalogue.md` | JANUS code audit: 20 findings (case E) |
| `E2_hmbc_design_attack_catalogue.md` | Design-level audit of the 2020 paper: 26 attacks + claims audit (case E) |
| `PLAN_AUDIT.md` | Consistency/grounding audit of an earlier plan version |

## round1/ - first verification round (web search, API-only grounding)
`RECHECK_HANDOFF.md` (task brief T1-T10), `RECHECK_COMMS.md` (the shared comms log with all results; **Section 7 = the resumed session's candidates E/F/G and the three-helper JANUS audit VD-1..VD-13**), `RECHECK_REFERENCES.md` (about 150 references with identifiers), `START_PROMPT.md`.

## round2/ - second web-search round
`RECHECK2_HANDOFF.md` (tasks T11-T16, T12), `RECHECK2_COMMS.md` (**MASTER VERDICT 2** at the top, per-class prior-art table, repository recon, venue calibration), `START_PROMPT2.md`.

Paths inside these historical files were rewritten on 2026-10-05 to the new layout. Superseded early planning documents
(the JANUS-hardening proposals "Cerberus" etc.) were removed and are recoverable from git history (commit `cd737e4`).
