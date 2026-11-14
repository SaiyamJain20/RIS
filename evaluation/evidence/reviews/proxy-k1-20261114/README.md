# Exact S2-0025 review and role continuation — Agent 3, 2026-11-14

PAPER-DERIVED HMBC2020 reconstruction; synthetic fixtures and placeholder signer;
one host; same-model correlated review. Not a FREEZE ACK or F-case result.

## Disposition

**ACCEPT at tested isolated scope; source adopted in the DRAFT.** Direct human
instructions in this chat authorize Claude proxy-2 for Agent 2, including protocol
source approval and exact protocol FREEZE ACKs. The human clarified that agent
numbers are portable work roles, not people, models, sessions or computers.
D57 records both instructions. No original-session countersignature or duplicate
push to agent-2 is required. One writer per scope and exact artifact review remain.
S2-0024 is accepted as the protocol role's answer; S2-0026 remains REVIEW, not ACK.

## Source and commands

Exact source: 37ca31c80ab9a81956647428435addb1802cb370, protocol tree
7566f63d693afe8fa88ab7cc69872082d58d88db, published on agent-1. Base: 9d44754.
The delta is four source paths plus the evidence directory (45 paths total);
production difference is two calls through the existing crash_hook seam, no-ops
without a supplied test hook. No production caller supplies that hook. Test-only
faulty_witness still recognizes only before_commit/after_commit. No shared schema,
signed bytes, ABI, dependency or lock changed.

All 40 entries of the S2-0025 checksum manifest match. Full git-archive input is
hashed in provenance.json; source-bracket.json.gz records all 2,303 files before
and after, exactly equal. Original READY trial driver k1_trials.py.txt is copied
byte-for-byte, and reproduce.py.txt records the command sequence. Recreate the
scratch input with git archive of the exact commit, then run:

```
.venv/bin/python -I evaluation/evidence/reviews/proxy-k1-20261114/reproduce.py.txt
```

The driver expects the archive at evaluation/runs/rq2-k1-review-20261114/owner/
and its disposable tmp/home directories plus source-before.json (the before map
in source-bracket.json.gz). Commands use the pinned root interpreter, isolated
HOME/TMPDIR, PYTHONDONTWRITEBYTECODE=1, and pytest plugin autoload disabled. Exact
argv/cwd/UTC/duration/exits/env hash and raw output hashes are in commands.json.
Output logs are losslessly gzip compressed after the run; receipt hashes refer
to decompressed bytes. The caller setup script is described by provenance.json.

## Fresh results

| Check | Result | Exit |
|---|---|---|
| New between-statement test, unmutated, 40 separate runs | 40 PASS, no crash | driver 0 |
| Same test with runner's K1 edits, 40 runs | 40 expected FAIL = 40 detections, no crash | driver 0 |
| Five state files including kill tests | 81 PASS | 0 |
| Full kill mutation runner once | control passes; K1/K2 detected; E1 survives | 0 |
| State mutation runner | 42/42 detected, control passes | 0 |
| New preflight behavior tests before implementation | 5 expected FAIL | 1 |
| Complete preflight tests after implementation | 15 PASS | 0 |
| Combined preflight/run/manifest regressions | 22 PASS | 0 |

New controls exercise all three pauses (fresh pin, digest, superseding pin).
K1 repetitions short-circuit at the first failing case; we do not claim a fresh
five-run-per-case mutant reproduction. The owner-published per-case evidence was
hash-checked/read, not rerun. One kill-runner reproduction is not its author's
six-run sample. Old candidate 55f180e's 29/40 result remains valid for those bytes;
new candidate's 40/40 is kill coverage, not an estimate of production corruption.
Initialization control records four actual stage interruptions even though all
25 random initializations finished before the kill. Premature-reply positive
control passes as part of the kill file. E1 survival explicitly limits any
power-loss claim. No service, chain, native signature, integrated F case or full
protocol/evaluator suite ran. Earlier measurements retain their original pins.

Tools: CPython 3.13.13, SQLite 3.47.2, pytest 9.0.2, eth-account 0.14.0,
eth-abi 6.0.0, jsonschema 4.26.0. Structured results are in result.json.

## Preflight and remaining work

D57 removes identity-based branch inference. The plan declares actual sourceRefs,
pins protocol commit and exact subtree, and preflight still checks publication
ancestry. It rejects wrong/short/missing module pins and unpublished local refs.
Legacy ownerCandidates/isAncestorOfOwnerHead output names refer to role artifacts,
not operator identity. Generated launch prompts match the common/ROLE sources.

The revised plan remains DRAFT with authorizesExecution=false. The final CLI
preflight exits 2/BLOCKED with all 32 cases NOT_RUN and no services;
all 11 pins match exactly; its manifest/receipt record the actual outcome. Missing runner stages,
signing-time/native-generation joins, exact authorized execution FREEZE and
actual role-scope ACKs remain. Gate F NOT_RUN, G locked. These results improve
the reviewable partial report; they do not replace the 32-case integration.
