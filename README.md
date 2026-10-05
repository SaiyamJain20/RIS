# RIS project - extending HMBC (IEEE Access 2020) beyond JANUS

Course: *Research in Information Security* (IIIT Hyderabad). Goal: a **workshop-paper-grade** extension of
**HMBC2020** - Malamas, Kotzanikolaou, Dasaklis, Burmester, *A Hierarchical Multi Blockchain for Fine Grained Access to Medical Data*,
IEEE Access 8 (2020), doi 10.1109/ACCESS.2020.3011201 - **in a direction JANUS did not take** (JANUS = Malamas et al.,
*Janus: Hierarchical Multi-Blockchain-Based Access Control (HMBAC)...*, Appl. Sci. 13(1):566, 2023, doi 10.3390/app13010566).
Proof-of-concept scale: 2-4 laptops (about 14 GB RAM, no GPU, no cloud), about 8 weeks, synthetic data only.
(Instructors named in the earlier proposal: Prof. Ashok Kumar Das and Prof. Srinathan Kannan - please confirm.)

## Status (2026-10-05)
Planning and evidence gathering are **complete**; the team's **week-0 decision** is pending.
**Recommended direction (default): E+F+G - "Breaking the assumptions of HMBC and JANUS": an executed security analysis with formal models and repairs.**
Alternatives, in order: **D** (case-scoped emergency tickets), **A** (ledger-enforced privacy-loss accounting). B and C are sections inside the recommended project.
Nothing has been run or measured yet; every claim of the form "nobody has published X" is unverified (see the plan, Section 13).

## Start here
1. **`docs/TEAM_PLAN_ALL_CASES.md`** - the shareable plan: Part I (15-minute guide to every case) + Part II (full technical annex with evidence and references).
2. **`docs/OPEN_QUESTIONS.md`** - decisions the team must make (instructor questions, A/D/E choice, disclosure).
3. **`docs/LIBRARY_TASKS.md`** - six paywalled papers and Google Scholar checks that no tool could do (needs IIIT-H library access).
4. `research/STATUS.md` - exact state of the work and next steps (also the resume point for AI sessions).

## Layout
```
.
├── README.md                    this file
├── course/                      course syllabus (Course_Content.md)
├── docs/                        what the team reads and edits
│   ├── TEAM_PLAN_ALL_CASES.md   shareable plan, all cases (Part I guide + Part II annex)
│   ├── PLAN_WORKSHOP.md         working plan v6 (source of Part II; keep both in sync)
│   ├── OPEN_QUESTIONS.md        open decisions and defaults
│   └── LIBRARY_TASKS.md         reading tasks needing library / Google Scholar access
├── papers/
│   ├── base/                    HMBC2020.pdf, JANUS2023.pdf
│   ├── related/                 Lewko-Waters 2011, Green-Hohenberger-Waters 2011, BMHADS 2026, Du 2024
│   └── text/                    plain-text copies (hmbc2020, janus2023, bigbird) - grep-able evidence
├── artifacts/                   third-party code under analysis - READ-ONLY, git-ignored clones
│   ├── janus-repo/              CENSUS/Janus (Fabric chaincodes, APIs, configs)
│   └── vault-secrets-abe-janus/ CENSUS/vault-secrets-abe-janus (Go Vault ABE plugin)
├── research/                    evidence trail - history, do not edit (add new evidence as new files)
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
git clone https://github.com/CENSUS/vault-secrets-abe-janus artifacts/vault-secrets-abe-janus
```
Both have been dormant since June 2022. The line references in the plan (e.g. `ACSC/lib/acsc.js:75-100`) are relative to
`artifacts/janus-repo/blockchain/chaincodes/` unless a full path is given; they refer to the clone's HEAD as of 2026-10-04
(re-cloning gives the same state because upstream has not changed).

## Ground rules
- **Laptop limits:** keep resident memory under about 3.5 GB; run one heavy job at a time. Do **not** build the Go/libpbc plugin or the full Fabric/Kubernetes stack on a laptop (the plan shows how to test without them).
- **Ethics:** synthetic data only; analysis of the JANUS code is unit-test level on mock stubs; nothing touches a live system; send the private advisory to the authors before publishing (plan Section 9.2).
- **Evidence tags** in all documents: **[V]** verified by reading the file directly (an AI session so far - the team should re-check), **[O]** abstract/full text opened by a tool, **[S]** snippet only, **[U]** unverified or an estimate.
- Keep `docs/PLAN_WORKSHOP.md` and `docs/TEAM_PLAN_ALL_CASES.md` consistent when you change either; record decisions in `docs/OPEN_QUESTIONS.md`.
