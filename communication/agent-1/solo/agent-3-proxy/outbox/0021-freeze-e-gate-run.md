Message-ID: S3-0021
From: agent-3 (proxy)
To: agent-1, agent-2 (proxy)
RQ: E
Task: P4-1 one-command gate E run (evaluation/e_gate.py, all 56 catalog rows, ProVerif, brackets, manifest, gate evidence), live integration FREEZE (solo phase)
Type: FREEZE
Interface-version: v1
Responds-to: A1-0082, A1-0080, A1-0081, S3-0002
Plan-sha256: c00860192aaa69fd2e5f7baf132f5ebf10bf14ebba377edada31c1d9372b6bb9
Source-manifest: evaluation/evidence/e3/gate-plan-20261012/integration-plan.json (sha256 c00860192aaa69fd2e5f7baf132f5ebf10bf14ebba377edada31c1d9372b6bb9; runId E-gate-20261012; 10 embedded slice plans, 56 rows; agent3Sources 103 files, aggregate 6f23444c89f3adef125b3d67d6c0ec54c79bb00426be3f270e0eb2d081bcc60c; 24 gate inputs); manifest.json f81acbb35717fa9e9f00e0e9dab69e0c8fd141930f377b46b41aa7aa3581a7e1; base HEAD 5c4c487 (no agent3Sources change since SL7 d4fa294e.. other than the two files below); owner pins unchanged (ledger 933d2a7 / c7b7dd51.., protocol 0716a8e / d16ddad8..)

Summary: This is the FREEZE for the **one-command gate E run** (A1-0082 P4-1), with exact plan
SHA-256 `c0086019..`. **Services start only after** both exact solo ACKs and this FREEZE are committed
and agent 1 clears the run.

| Stage | Content |
|---|---|
| 1 verify-freeze and versions | `FREEZE.json` hash, the 15 frozen copies (the two moved owner inventories against their frozen Git blobs), tool versions and hashes |
| 2 source bracket (pre) | `agent3Sources`, the 24 gate inputs, and `evaluation/**` + `interfaces/v1/**` + 5 root files; must equal the plan |
| 3 catalog | **all 56 rows**, one fresh chain pair per row, each through `e2.run_row` (the P2 slice runner and its frozen row check): three controls first on D1, stress on fresh D2 (and B for wrong destination) |
| 4, 5 | **dropped**: mutants (A1-0080), window (A1-0081) |
| 6 ProVerif | both models with the declared 2.05 build bc2cd5ed..; verdicts and stdout bytes compared with A3-0033 and `p3-proverif-20261012` |
| 7 source bracket (post) | same bracket; HEAD and `git status` unchanged; gate plan re-verified |
| 8, 9 | `manifest.json`; `gate-evidence.json` with all 9 `E_CRITERIA`; `catalog-coverage-56.json` |

- **Aggregation only.** The plan embeds the ten slice plans produced by the existing `e2.create_plan`
  flags. No oracle is added. `e2.py` changed only by moving the `execute` loop body into `run_row` (plus
  `probe_name`, `case_name`, `slice_mode`, `slice_status`); `execute` behaves as before.
- **Layouts unchanged:** `<out>/catalog/<slice>/<case>/<profile>/...`, so your seven slice tools, the SL1
  subject tool and the early-rows tool find their rows as before.
- **Criterion 4:** VERIFIED only as human-scoped (A1-0080), with the note "met on owner, formal and
  baseline evidence (human decision A1-0080); integrated live mutant matrix not run ...". Evidence:
  `ledger/evidence/p3-mutant-suite-rerun/`, `evaluation/evidence/e2/p3-proverif-20261012/`, the 8 SL2-SL7
  guard rows of this run, and A1-0080. The window is not a criterion.
- **RQ1-report and three-matching-acks are PENDING by design.** A fully passing run gives 7 VERIFIED and
  2 PENDING. `gate.py` is unchanged and stays fail-closed (a test shows BLOCKED on a complete passing run).
- **Built test-first:** RED gave **48** (29 failed, 19 errors) before any implementation; no test changed
  after RED. GREEN: the 48 new tests pass. Full suite: `.venv/bin/python -m pytest -q -rs -p no:cacheprovider --color=no` exit 0, **1644 passed,
  0 failed, 0 skipped**, 574 s; the source bracket (4028 files) is stable.
- Correlated self-review. Tested reconstruction results, **never HMBC exploits**.

Evidence: `evaluation/evidence/e3/gate-plan-20261012/`:

- README (design, rows, criteria, failure/output/host policy, limits);
- `integration-plan.json`;
- `manifest.json` (commands, exits, RED/GREEN, suite and bracket, `agent3Sources` diff, hashes);
- `red-before-implementation.txt`, `green-new-tests.txt`, `full-suite.txt`;
- `e2-refactor-diff.txt` (`git diff -w` of `e2.py`: moves only).

I chose the S3-0002 naming (`evaluation/evidence/e3/gate-plan-<date>/`) as A1-0082 suggested.

Impact:

- Once run, reviewed and ACKed, this run is the gate E evidence for C2, C3, C5, C6 and C8, and the
  baseline part of C4.
- Gate E stays NOT_RUN until the run, RQ1-E.md and the three same-source ACKs (P4-2, P4-3).
- F and G stay locked.

## A1-0082 P4-1 points

1. **Stages** 1-3 and 6-9 as listed; 4 and 5 dropped with their decision IDs in the plan
   (`droppedStages`), the manifest and the gate evidence. **Met.**
2. **Aggregation only:** the same slice runners and checks via the existing slice flags; no new oracle
   logic. **Met.**
3. **Failures kept:** each row runs once; a failed or timed-out row is recorded FAILED with its type and
   message and is never retried; rows not reached stay NOT_RUN. **Met.** One explicit choice: after a
   failed row the run **continues** with the next row on a fresh chain pair (`e2.execute` stops a slice
   at its first failure). Any FAILED or NOT_RUN row makes the run FAILED.
4. **Criterion 4** evidence paths and note exactly as asked. **Met.**
5. **`gate.py` stays fail-closed;** unchanged (sha256 23fbfae5..). **Met.**
6. **Host:** free memory from `/proc/meminfo` before and after, and at each row start. The output must
   lie outside the repository (refused otherwise), so nothing writes in the repo during the run. **Met.**
7. **Test-first,** full suite, FREEZE S3-0021. **Met.**
8. **Slice layouts unchanged** for your review tools. **Met.**

Points I could not meet: **none.**

Action requested:
- **agent 1 (ledger scope):** ACK the exact plan hash, or send a blocker. Your ACK covers:
  - the gate plan and its ten embedded slice plans (the same ledger recipes, owner commands, pins and
    TEST-ONLY producer invocations as SL1-SL7 and the pre-solo slices);
  - the criterion 4 wording and evidence (A1-0080);
  - the per-row continuation choice.
- **agent 2 (proxy) (protocol scope):** ACK the exact plan hash, or send a blocker. Your ACK covers:
  - the production and faulty adapter use exactly as in the slices (crash hook in the 6 recovery rows,
    deviating witness in SL4, one decision per request, D49 probes);
  - the solo-mode re-run of the pre-solo slices (recovery-expiry, duplicate, nonce replay) on this host.
- **agent 1:** commit this FREEZE, both ACKs and the paths below, build the ACK index, then clear the run.

## Changed `agent3Sources` since SL7 (d4fa294e..)

| File | Old sha256 | New sha256 |
|---|---|---|
| evaluation/e2.py | 3ab09417.. | ab37fb135a290361a4ba25cfa32b9ea39b4062cad6ef50cb4a0ddd7b49f6fae7 |
| evaluation/e_gate.py | new | bc231dd54bc1f249896c939c6dbbdfb46c4b66dd334459dd9d20b72fbdc30a92 |

## ACK format (same as S3-0019)

| Header | agent 1 ACK | agent 2 (proxy) ACK |
|---|---|---|
| `Message-ID` | `A1-NNNN` | `S2-NNNN` |
| `From` | `agent-1` | `agent-2 (proxy…)` |
| `To` | must contain `agent-3 (proxy)` (or `agent-3`, or `all`) | same |
| `RQ` | `E` | `E` |
| `Type` | `ACK` | `ACK` |
| `Interface-version` | `v1` (exactly) | `v1` |
| `Responds-to` | `S3-0021` (exactly, one value) | `S3-0021` |
| `Accepted-plan-sha256` | `c00860192aaa69fd2e5f7baf132f5ebf10bf14ebba377edada31c1d9372b6bb9` | same |

The ACK index is `{agent-1, agent-2, freeze}`, each `{commit, path, sha256}` from
`git log -1 --format=%H HEAD -- <path>` and the blob sha256.

## Run command (after clearance)

```
export PATH="$HOME/.foundry/bin:$PATH"
.venv/bin/python -m evaluation.e_gate \
  --plan evaluation/evidence/e3/gate-plan-20261012/integration-plan.json \
  --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/gate-run/acks.json \
  --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/gate-run/out
```

- Ports 18545 and 18546 only; one live run at a time; no full suite in parallel.
- Exit 0 only when every run stage passed (manifest status PASS). That is **not** gate E PASS.
- Expected wall time: **about 1.5 h; allow up to 2.5 h** (estimate from the slice wall times, 5252 s;
  S3-0002 estimated 2-2.5 h). Run it in the background. To stop cleanly, send SIGINT (`kill -INT <pid>`).

## Commit list for agent 1

| Path | sha256 |
|---|---|
| `evaluation/e_gate.py` | bc231dd5.. |
| `evaluation/e2.py` | ab37fb13.. |
| `evaluation/tests/test_e_gate.py` | 3b54fd2c.. |
| `evaluation/tests/test_e2_row_runner.py` | 9761500d.. |

Plus `evaluation/evidence/e3/gate-plan-20261012/*` (7 files), this message, and my STATUS.md and
HANDOFF.md.

## Known limits

- **Not yet run live:** the gate command itself. Its row path is the live-proven slice path; the
  aggregation, continuation, brackets and evidence writer are unit-tested only, against TEST-ONLY doubles.
- The pre-solo slices were strict-mode runs on agent 3's host; here they run as solo-mode slice plans on
  this host for the first time (same recipe).
- Repaired TTL margins about 2 s (SL7 expiry boundary) and about 7 s (SL6 expired duty) under low host
  memory; a failed row would be kept and needs a new FREEZE.
- The integrated live mutant matrix and the integrated window are not run (A1-0080, A1-0081).
- One trial per row, one host, Anvil without consensus or finality, symbolic adapter.
