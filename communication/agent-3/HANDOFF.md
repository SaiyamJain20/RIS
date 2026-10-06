# Agent 3 handoff — 2026-10-07

**E0 candidates ready for review; E0/C-E1 acceptance incomplete. Gate E NOT RUN.** Human changed execution to independent machines and branch communication, confirmed RIS checkout/origin, and authorized owned work/pushes on agent-3. D19 supersedes old main/shared-index restrictions.

## Exact evidence and exports

- Candidate revision: interfaces/proposals/v1/review-manifest.json SHA-256 `abbeca1df4284fa31b3396020d7340f6bcd9461c5996e21419e95da80a7f0cb4`. It hashes the schema generator/document, wire/semantic validator, vectors, source/assumption map, controls and root dependency lock.
- Consolidated evidence: evaluation/evidence/e0/final-checks/checks.json SHA-256 `cf1df9402ea4f0b46afa22a986a6b172652b8a277c7e5b32a31a64212f977710`; tested source-manifest hash `43c7fab7075d0ee5ec33514d3a75561d1b34da7b6c48d4e500711ad45c860707`. Every recorded command, output and exit code is retained, including expected nonzero outcomes. Tested input files still match their hashes at packaging. Communication/status/manifest packaging records are added after the stable test run; they do not alter the tested inputs.
- Peer READY: agent-1 `f643805e21c996bbf4bd73212c85c8a5a85b655d`, A1-0006, 86-entry manifest `4d7802b70d731cf5ba3ac3b38fac32ffddaf0400d5b0e7fccfb9117815bfd577`; all entries match before/after tests.
- Commands and actual outcomes: 57 owned tests; 333 independent crypto/vector checks; 47 candidate wire fixture checks; Forge151/Cast166; 6 mutant suites caught; pending outcome-evidence test exits1 as expected. ProVerif smoke proves only the trivial public/private token checks; real E correspondence queries NOT RUN. Runner/gate preflight exit2/BLOCKED. No E1 service integration.
- Exact local tool versions/executable/source hashes: evaluation/toolchain.json; Python3.13.13, uv0.11.11, Foundry1.8.5/solc0.8.37, eth-account0.14.0/jsonschema4.26.0/pytest9.0.2, ProVerif2.05 compiled with local OCaml4.14.2. No shared version freeze, TLC or ABE backend.
- Red/green and failed-build records: evaluation/evidence/e0. First ProVerif GUI build lacked ocamlfind; core-only rebuild succeeded. Initial request-mutation verifier omitted derived domain changes; corrected and rechecked. Foundry initial signature-cache warning did not prevent module tests.

## Reproduction

`uv sync --frozen`; `.venv/bin/python -m pytest evaluation/tests -q`; `.venv/bin/python -m evaluation.vectors interfaces/vectors/eip712-agent1-candidate.json`.
For peer E0 reproduction, fetch and extract the exact owner commit into disposable scratch with `git archive <reviewed-commit> ledger | tar -x -C <new-scratch>`, then `.venv/bin/python -m evaluation.e0_verify --peer-root <new-scratch> --output evaluation/runs/<new-run>`. Review the module tools before execution; verify the READY manifest first. The helper uses pinned local toolchain paths/hashes; another host must explicitly install/review equivalent versions. Scratch is not a worktree/branch and is never pushed.

`python communication/build_prompts.py --check` must pass. `python -m evaluation.peers --output <snapshot>` reads latest committed communication file revisions across fetched branches, records ancestry/provenance and flags divergent edits without mutating peer files. Branch snapshots were rechecked repeatedly; agent-2 remained absent.

## Pending peers and next allowed work

Read/respond to A3-0002/A3-0003. Agent1 must ACK exact schema/source/semantic hashes and revise/ACK receipt semantics. Agent2 must publish its branch, source/key/credential flow, dependencies, independent matching vectors, capability ACK and adapter/result/deployment samples. Complete operation-specific payload and ScenarioResult/deployment schemas through exact RFC reviews. Schema candidates are proposals; live interfaces/README remains v0. No invented ACKs, premature interfaces/v1 freeze or E1 integration.

After complete E0 review/smoke/three ACKs, publish INTERFACE_READY and unlock A/B/C-E1 together. Implement the real public-adapter collector and owned service lifecycle, then integrate two real chains plus worker for positive/denied controls. Only then begin E2 systematic cases/receipt repair/recovery/correspondence model and E3 report/gate. F/G remain locked.

## Git, services and limits

No peer module/runtime mailbox was edited or merged. No service PID/port is owned; integration freeze inactive. Only owned/shared reviewed files are staged and normally pushed on agent-3. Main is not pushed. Lock acquired/released by this coordinator for the checkpoint. Inspect latest branch/status before restart; do not reset/stash/clean/rebase or change branches to read peers.

Author self-review found and fixed nested certificate ordering, E signature count, duplicate outcomes and malformed gate input, with RED→GREEN proof. No independent reviewer was spawned because the project explicitly prohibits extra agents. The candidate manifest covers exact review revision; research claims remain bounded to module/unit/toolchain checks. Complete Phase1/RQ1 is blocked on the listed support, not called done.

## Verified publication checkpoint

E0 payload commit `7af866da025bbc963677d67ec4c8d9f8f13575a0` was normally pushed to origin/agent-3; `git ls-remote` returned that exact SHA and the working tree was clean. A3-0001/0002/0003 are delivered. Post-push fetch still showed agent-1 at f643805, main at 5f71184 and no agent-2 branch. No new peer ACKs. This metadata checkpoint records publication without changing tested source/candidate hashes. Hourly monitor is ACTIVE and uses the confirmed checkout and live board; no main push/services are authorized.
