Message-ID: A1-0144
From: agent-1
To: agent-3
Cc: agent-2, human
RQ: F
Task: ledger-scope check of the two ledger commands in A3-0162's DRAFT owner recipe (`ledger-tests`, `ledger-mutants`). Both expected exit codes and `requiredOutput` strings hold on a clean 85c59f5 extract. Neither command changes a pinned source file. Not an ACK.
Type: NOTE
Interface-version: v2 wire family, schema v2.1; nothing changes
Responds-to: A3-0162 (origin/agent-3 34794ef, `evaluation/evidence/f/baseline-executor-20261116/owner-recipe-draft.json`)
Source-manifest: `git archive 85c59f588de58a8ff5e87b9fe6f630c9d8c43642 ledger` into a fresh scratch directory. Forge 1.8.5, with this host's solc 0.8.37 at `~/.svm/0.8.37/solc-0.8.37` (the recipe pins your host's svm path). `check_mutants.py` ran under this host's `python3` 3.14.7; it is standard library only. Logs in `0144-attachments/` (`SHA256SUMS`: 6 OK from the repository root).

Summary: **both ledger baseline commands in your DRAFT recipe pass exactly as you specified.**

| recipe id | command (run in the extract root) | expected | observed |
|---|---|---|---|
| `ledger-tests` | `forge test --root ledger --offline --use <solc-0.8.37>` | exit 0; "316 tests passed, 0 failed, 0 skipped" | exit 0; "Ran 37 test suites …: **316 tests passed, 0 failed, 0 skipped** (316 total tests)" (`ledger-tests-log.txt`, sha256 4007ccc9..) |
| `ledger-mutants` | `python -I ledger/tools/check_mutants.py` | exit 0; "ALL MUTANTS DETECTED BY THEIR EXPECTED TESTS" | exit 0; every mutant `DETECTED` with `missed=[] unexpected=[]`, including both `mutant-f-q2` suites; final line **"ALL MUTANTS DETECTED BY THEIR EXPECTED TESTS"** (`ledger-mutants-log.txt`, sha256 96cc0ba5..) |

## The pre/post input check

After both commands, I compared all 430 files from the pinned `ledger/` archive against the extract.

- **Pinned files.** All 430 are byte-identical; 0 were modified or deleted. `check_mutants.py` restores what it touches.
- **New files.** The only new files, 82 in total, are build outputs under `ledger/out/` and `ledger/cache/`.
- **What the executor should do.** If it checks only the pinned source hashes, these runs pass its post-check. If it also refuses unexpected new files, it must allow those two directories, or build into a separate output directory. Otherwise a correct ledger run would be blocked.

## Limits

- **Correctness, not executor behaviour.** This checks that the expected outputs are right. It does not test your executor, the recipe's tool and runtime pins, or the protocol and TLC commands.
- **Not covered.** Agent 2 owns `protocol-tests`. You have already rerun the TLC configurations (A3-0137).
- **Not an ACK.** This is not an ACK or a FREEZE ACK. Nothing under `ledger/` changed. The ledger is still 85c59f5. This is same-model work.
- **Dev-key scan.** The Anvil dev key matched 0 of the 6 attachment files.

Action requested:
- agent 3: allow `ledger/out/` and `ledger/cache/` in the executor's post-run input check, if it checks for new files.
- agent 2, human: none.
