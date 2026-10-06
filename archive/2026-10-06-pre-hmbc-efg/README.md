# RIS project - extending HMBC (IEEE Access 2020) beyond JANUS

Course: *Research in Information Security* (IIIT Hyderabad). Goal: a **workshop-paper-grade** extension of
**HMBC2020** - Malamas, Kotzanikolaou, Dasaklis, Burmester, *A Hierarchical Multi Blockchain for Fine Grained Access to Medical Data*,
IEEE Access 8 (2020), doi 10.1109/ACCESS.2020.3011201 - **in a direction JANUS did not take** (JANUS = Malamas et al.,
*Janus: Hierarchical Multi-Blockchain-Based Access Control (HMBAC)...*, Appl. Sci. 13(1):566, 2023, doi 10.3390/app13010566).
Proposed proof-of-concept scale: 2-4 laptops (about 14 GB RAM, no GPU, no cloud), about 8 weeks, synthetic data only.
Hardware/team details are inherited planning inputs, not confirmed requirements; see the decision register.
(Instructors named in the earlier proposal: Prof. Ashok Kumar Das and Prof. Srinathan Kannan - please confirm.)

## Status (audited 2026-10-06)
Evidence gathering and the implementation specification are **incomplete**; the team's direction is pending.
The [current audit](research/audit-2026-10-06/AUDIT.md) identifies substantive source-reading errors,
unproved secrecy/privacy claims and missing specifications. It supersedes conflicting historical evidence tags.
All 345 DOI/arXiv identifiers in the original Markdown resolve to metadata, but their full contents and every
attributed claim have not been verified. The citation register records that distinction.
**Recommended direction (decision pending): E+F+G - "Breaking the assumptions of HMBC and JANUS": an executed security analysis with formal models and repairs.**
Alternatives, in order: **D** (case-scoped emergency tickets), **A** (ledger-enforced privacy-loss accounting). B and C are sections inside the recommended project.
No implementation, attack harness or formal model has been run. Conditional arithmetic was independently
recomputed in this audit; every claim of the form "nobody has published X" remains unverified.

## Start here
1. **`research/audit-2026-10-06/AUDIT.md`** - current source/claim corrections, limits and specification gates; `CITATION_REGISTER.csv` resolves cited identifiers and `SOURCE_MANIFEST.json` pins source hashes.
2. **`docs/TEAM_PLAN_ALL_CASES.md`** - the shareable plan: Part I (15-minute guide to every case) + Part II (full technical annex with evidence and references).
3. **`docs/OPEN_QUESTIONS.md`** - decisions the team must make (instructor questions, A/D/E choice, disclosure).
4. **`docs/LIBRARY_TASKS.md`** - six paywalled papers and Google Scholar checks that no tool could do (needs IIIT-H library access).
5. `research/STATUS.md` (historical; the current audit supersedes its completion claims) - exact state of the work and next steps (also the resume point for AI sessions).

## Layout
```
.
├── README.md                    this file
├── course/                      course syllabus (Course_Content.md)
├── docs/                        what the team reads and edits
│   ├── TEAM_PLAN_ALL_CASES.md   shareable plan, all cases (Part I guide + Part II annex)
│   ├── PLAN_WORKSHOP.md         audited working plan v7 (source of Part II; keep both in sync)
│   ├── OPEN_QUESTIONS.md        open decisions and proposed values
│   └── LIBRARY_TASKS.md         reading tasks needing library / Google Scholar access
├── papers/
│   ├── base/                    HMBC2020.pdf, JANUS2023.pdf
│   ├── related/                 Lewko-Waters 2011, Green-Hohenberger-Waters 2011, BMHADS 2026, Du 2024
│   └── text/                    plain-text copies (hmbc2020, janus2023, bigbird) - grep-able evidence
├── artifacts/                   proposed third-party clones (absent here; git-ignored)
│   ├── janus-repo/              CENSUS/Janus (Fabric chaincodes, APIs, configs)
│   └── vault-secrets-abe-janus/ CENSUS/vault-secrets-abe-janus (Go Vault ABE plugin)
├── research/                    evidence trail - history, do not edit (add new evidence as new files)
│   ├── audit-2026-10-06/         current audit, citation metadata and source hashes
│   ├── STATUS.md                where we are / next steps
│   ├── reports/                 agent reports (see research/README.md)
│   ├── round1/                  first verification round: handoff, comms log, references, start prompt
│   └── round2/                  second web-search round: handoff, comms log, start prompt
└── work/                        OUR implementation workspace (empty scaffold; see work/README.md)
    ├── harness/  reimpl/  models/  experiments/  repairs/  paper/  notes/
```

## Setup
The two JANUS repositories are third-party clones and are **not** committed. To recreate them:
```bash
git clone https://github.com/CENSUS/Janus artifacts/janus-repo
git -C artifacts/janus-repo checkout --detach 0fd5bb051463003d93777f6c49c6be077577ecdf
git clone https://github.com/CENSUS/vault-secrets-abe-janus artifacts/vault-secrets-abe-janus
git -C artifacts/vault-secrets-abe-janus checkout --detach efcf03fe682911b1bc6d3d328c5d5af37fcf889c
```
These exact commits were read on 2026-10-06; their last commit dates are in June 2022. The line references in the plan (e.g. `ACSC/lib/acsc.js:75-100`) are relative to
`artifacts/janus-repo/blockchain/chaincodes/` unless a full path is given. Use the pinned commits above;
future upstream HEAD is not a reproducibility guarantee. This checkout does not include the clones.

## Ground rules
- **Laptop limits:** keep resident memory under about 3.5 GB; run one heavy job at a time. Do **not** build the Go/libpbc plugin or the full Fabric/Kubernetes stack on a laptop (the plan shows how to test without them).
- **Ethics:** synthetic data only; local analysis and proposed mock tests. Advisory recipients, authorization and publication/embargo timing remain pending decisions; a plan default does not authorize outreach.
- **Evidence tags:** **[V]** means a cited passage/pinned file was read, not that exploitability or a security proof is established; **[O]** must distinguish metadata, abstract and full text; **[S]** snippet only; **[U]** unresolved/estimate. Historical tags are not a certification. Unaccepted design parameters are proposals.
- Keep `docs/PLAN_WORKSHOP.md` and `docs/TEAM_PLAN_ALL_CASES.md` consistent when you change either; record decisions in `docs/OPEN_QUESTIONS.md`.
