Message-ID: A1-0083
From: agent-1
To: agent-3 (proxy)
Cc: agent-2 (proxy), human
RQ: E
Task: one-command gate E run (evaluation/e_gate.py, 56 catalog rows, ProVerif, brackets, gate evidence) FREEZE, ledger-scope ACK (solo phase)
Type: ACK
Interface-version: v1
Responds-to: S3-0021
Accepted-plan-sha256: c00860192aaa69fd2e5f7baf132f5ebf10bf14ebba377edada31c1d9372b6bb9
Source-manifest: plan evaluation/evidence/e3/gate-plan-20261012/integration-plan.json (runId E-gate-20261012); S3-0021 sha256 dcb8c72a70462aa51f7cd46d9e19518388c89b3af71eeae03561002828ecf682; evaluation/e_gate.py bc231dd5..; evaluation/e2.py ab37fb13..; evaluation/gate.py 23fbfae5.. (unchanged since 7af866d); ledger commit 933d2a75483a08e7374cd417a6cf8a9e5c13a33c, ledger/evidence/source-manifest.sha256 c7b7dd51f0e4c84535fbd093fbbd6bc6b49a9ed1a3f999b68f93d68f3dd04660 (195 entries); agent 1 review tools committed in 9682e54 and earlier (hashes below)

Summary: **Agent 1 ACKs the exact gate plan c0086019.. for the ledger scope.**

- The ten embedded slice plans carry the same ledger recipes, owner commands, pins and TEST-ONLY
  producer invocations as the frozen slices.
- The criterion 4 wording and evidence follow A1-0080.
- I accept the per-row continuation choice.

This is solo, correlated review (A1-0059). Exit 0 of the gate command is not gate E PASS.

## Verified (by agent 1 on this host, 2026-10-12 ~06:35-06:50 IST)

- **Hashes:** `sha256sum` of the plan gives c0086019... `e_gate.verify_plan(plan)` returns None,
  which also runs `e2.verify_plan` on all ten slices. There are 56 case IDs, all distinct, equal to
  the frozen catalog.
- **Embedded plans against their FREEZEs:** I diffed each embedded plan field by field against the
  committed historical plan.

  | Slices | Differ only in |
  |---|---|
  | SL1-SL7 (subject, relay r2, audit, receipt, trust, barrier, destination) | `runId`, `freezeMessage`, `agent3Sources` |
  | recovery-expiry, duplicate outcome, nonce replay (the A3-0038/0040/0045 runner plans) | the same three fields, plus the SL0 host-portability fields: `ports`, `tools`, `pythonVersion`, `serviceEnvironment`, `castHashPolicy`, `hostDifferences`, `hostToolOverride` and the solo review fields |

  `owners`, `matrix`, fixtures and every other ledger-relevant field are identical. Every slice uses
  ledger 933d2a7, ports 18545/18546 and chain IDs 18545/28545.
- **Full suite, run independently:**
  - Command: `export PATH="$HOME/.foundry/bin:$PATH"; .venv/bin/python -m pytest -q -rs -p no:cacheprovider --color=no`.
  - Result: exit 0, **1644 passed** in 574.24 s (575 s wall). This matches S3-0021.
  - Output (job tmp): `eval-gate-verify.out`, sha256 5ee35b20...
- **Code review of `e_gate.py` (594 lines):**
  - Every row runs through `e2.run_row` with its embedded slice plan. There is no new oracle;
    `_coverage` and `_criteria` only aggregate the row status and the proof fields the row checks
    already accepted.
  - `git diff -w` of `e2.py` shows only the move of the `execute` loop body into `run_row`, plus
    `probe_name`, `case_name`, `slice_mode` and `slice_status`. Each `continue` became `return case`,
    which is equivalent per row. The stored `e2-refactor-diff.txt` equals my diff apart from its
    header comment.
  - `--output` inside the repository is refused. HEAD and `git status` are compared before and
    after the run. The source bracket covers `agent3Sources`, the 24 gate inputs and
    `evaluation/**` + `interfaces/v1/**` + 5 root files. The plan is re-verified at the end.
  - ProVerif must exit 0 with empty stderr, give the expected verdicts, and produce stdout
    byte-identical to the A3-0033 and p3-proverif-20261012 references.
  - Criterion 4: `CRITERION4_NOTE` is the A1-0080 wording, including "integrated live mutant matrix
    not run". The evidence is the owner forge rerun, the P3 ProVerif files, the 8 guard rows of this
    run and A1-0080. It is VERIFIED only together with all 56 rows, the guard errors, the ProVerif
    match and unchanged inputs.
  - `RQ1-report` and `three-matching-acks` are PENDING by construction. `gate.py` is unchanged and
    fail-closed.

## Ledger scope

1. **Guard rows.** The guard locations named in the plan are right at 933d2a7:

   | Guard row | Location |
   |---|---|
   | nonce guard | KSSC.sol:182 (181-183) |
   | receipt field binding | in `_checkReceipt`, before the quorum (PSC.sol:266-269 within the cited 240-283) |
   | rollback | TMSC.sol:190 |
   | post-barrier | DecisionVerifier line 87, sequence cause |
   | expired duty | DecisionVerifier step 13 |
   | wrong destination | DecisionVerifier step 1, line 60 |

   - The plan states that the wrong-destination row cannot kill no-destination-binding (1), as it
     should.
   - I checked that each historical guard row's `result.json` carries the `error` field that
     `_criteria` compares: REPLAY, WRONG_SUBJECT x3, STALE_ANCHOR, STALE_STATE, EXPIRED and
     WRONG_DESTINATION. So criterion 4 cannot fail on a missing field when the rows behave as
     before.
2. **Per-row continuation: accepted.** A failed row is kept with its type and message, is never
   retried, and makes the run FAILED. Re-running it needs a new FREEZE. Continuing on a fresh chain
   pair only adds evidence for the other rows, and no failure is hidden. This is consistent with
   A1-0082.
3. **D47:** the four paper crash rows carry "frozen BLOCKED / decided SPEC_GAP, UNPROVED (D47)" and
   are never findings. Correct.
4. **Known risks, accepted and to be reported as they fall:**
   - the repaired TTL margins (about 2 s SL7, about 7 s SL6);
   - the first solo-mode run of the pre-solo slices on this host. The first nonce-replay trial on
     agent 3's host failed on a repaired release EXPIRED, which is a timing risk of the same kind;
   - the first live use of the gate command itself.

   A FAILED row is a result to report, not something to work around.

## Agent 1's independent review of the run (pre-registered, unchanged before the run)

After the run I will run these tools, first on the job-tmp output and then on the published copy.
The slice tools take `<out>/catalog/<slice>`; the early-rows tool takes `<out>/catalog` (rglob).

| Tool | sha256 | Rows |
|---|---|---|
| review_early_rows_evidence.py | 199dd936.. (committed 9682e54, before this FREEZE) | recovery-expiry 6, duplicate 3, nonce replay 3 |
| review_subject_evidence.py | 3e180ac4.. | SL1 3 |
| review_relay_stress_evidence.py | 98a97c63.. | SL2 7 |
| review_audit_stress_evidence.py | f02cbec4.. | SL3 6 |
| review_receipt_stress_evidence.py | 5fa5a7c9.. | SL4 7 |
| review_trust_stress_evidence.py | 13c10d1d.. | SL5 6 |
| review_barrier_stress_evidence.py | 9edc3eb2.. | SL6 9 |
| review_destination_stress_evidence.py | 9e788ce9.. | SL7 6 |

Total: 56 rows. Any tool failure is reported as a discrepancy, not fixed silently.

## Run conditions (agent 1)

- The run starts only after this ACK, S2-0021 and S3-0021 are committed and the ACK index is built.
- The tree is clean at start.
- Nobody writes in the repository until the gate process exits. That includes agent 1: no commits,
  no edits, no review tools run inside the tree.
- No full suite or second live run in parallel.
- Free memory is recorded by the gate.
- If a usage limit interrupts the session, the gate process keeps running. Its output stays in job
  tmp and is reviewed on resume.

Impact: S3-0021 is ACKed in the ledger scope. The run waits for S2-0021. Gate E stays NOT_RUN until the
run, RQ1-E.md and the three same-source ACKs. F and G stay locked.
Action requested: agent-2 (proxy) ACK S3-0021 in protocol scope. agent-3 (proxy): none until the run
ends.
