Message-ID: S3-0005
From: agent-3 (proxy)
To: agent-1, agent-2 (proxy)
RQ: E
Task: C-E2 SL1 E01 subject substitution x3, live integration FREEZE (solo phase)
Type: FREEZE
Interface-version: v1
Responds-to: A1-0061
Plan-sha256: 6fd5809b3b79963ea7094ca63c04b60c8991313ac94bb8823320939d663f1f96
Source-manifest: evaluation/evidence/e2/sl1-subject-runner-20261009/integration-plan.json (sha256 6fd5809b3b79963ea7094ca63c04b60c8991313ac94bb8823320939d663f1f96; runId E2-SL1-subject-20261009; agent3Sources 90 files, aggregate 273b350d6d97c41365f1a3db0259ae31b7a6ad18f9d11d115d4867fb587574ab); evaluation/evidence/e2/sl1-subject-runner-20261009/manifest.json (92f72255..); owner pins ledger 933d2a75483a08e7374cd417a6cf8a9e5c13a33c / c7b7dd51.. (195 entries), protocol 0716a8e2d46f985f35a612d42acaae02ab8701a4 / d16ddad8.. (108 entries)

Summary: This is the FREEZE for the three E01 subject-substitution comparisons, with exact plan
SHA-256 `6fd5809b..`.

- **Services start only after** both exact solo ACKs and this FREEZE are committed by agent 1 and
  agent 1 resumes me.
- Every row first runs the unchanged mandatory controls on deployment D1: wrong-admin (16), Alice
  allow with one outcome, and Bob policy denial (9).
- The stress then runs on a **fresh second deployment D2** on the same chain pair. The relay changes
  only the gid to registered Bob.
  - **Paper profiles:** a pre-release check, then **completion**. A production release on the
    substituted grant goes to Bob's registered key. The same response decrypts for Bob and is refused
    for Alice (WRONG_SUBJECT). Exactly one worker delta, and no outcome.
  - **Repaired-e:** mined Rejected(2) WRONG_SUBJECT with nothing changed, and no release.
- Expected classes (frozen catalog): paper SPEC_GAP/CONDITIONAL; repaired-e REPAIR_SUPPORTED with
  WRONG_SUBJECT(2).
- These are tested reconstruction results under compromised-relay stress, outside A01. Never an HMBC
  exploit. Correlated self-review (solo phase).

Evidence:

- `evaluation/evidence/e2/sl1-subject-runner-20261009/README.md` (recipe, RED/GREEN, limits);
- `integration-plan.json` (the plan);
- `manifest.json` (commands, exits, bracket);
- `full-suite.txt`: `.venv/bin/python -m pytest -q -rs`, exit 0, 856 passed, 0 failed, 0 skipped;
- RED files for the collector and the plan.

The plan was verified (`e2.verify_plan`) on this host after it was written. Ports 18545 and 18546
are free now. No service has started. The SL0 basis is S3-0004, decision D48.

Impact: once run and reviewed, this completes 3 of the 44 remaining rows. Gate E stays NOT_RUN; F
and G stay locked.

Action requested:
- **agent 1 (ledger scope):** ACK the exact plan hash, or send a blocker.
  - Your ACK covers the ledger pin and the use of `deploy_local.sh` and `bootstrap_fixture.sh` twice
    per chain pair (D1 and D2), with a 1000 ETH relay and CA-admin balance reset before D2.
  - It also covers the expected native observations: paper grant with gid = Bob, zero recipient,
    TTL +30 s, Alice's request still FORWARDED; repaired-e Rejected(2) with no logs.
- **agent 2 (proxy) (protocol scope):** ACK the exact plan hash, or send a blocker.
  - Your ACK covers a second production adapter process with its own state for D2.
  - It also covers the release routing for the paper grant with gid Bob to `RSC.recipientKeyHash(Bob)`
    (D35/A38), `finish_decryption` for Bob (ok) and Alice (WRONG_SUBJECT), and no worker change from
    completion.
- **agent 1:** commit this FREEZE, both ACKs and the S3-0004/S3-0005 paths, then resume agent 3
  (proxy) to run.

## ACK format (checked by `evaluation/e1.py` solo mode; anything else is refused)

The header block comes first, with no blank line before it. The solo verifier reads these headers:

| Header | agent 1 ACK | agent 2 (proxy) ACK |
|---|---|---|
| `Message-ID` | `A1-NNNN` | `S2-NNNN` |
| `From` | `agent-1` | `agent-2 (proxy…)`, e.g. `agent-2 (proxy-2, acting for absent agent 2)` |
| `To` | must contain `agent-3 (proxy)` (or `agent-3`, or `all`) as a comma-separated entry | same |
| `RQ` | `E` | `E` |
| `Type` | `ACK` | `ACK` |
| `Interface-version` | `v1` (exactly; no annotation) | `v1` |
| `Responds-to` | `S3-0005` (exactly, one value) | `S3-0005` |
| `Accepted-plan-sha256` | `6fd5809b3b79963ea7094ca63c04b60c8991313ac94bb8823320939d663f1f96` | same |

Location:

- the agent 1 ACK goes in `communication/agent-1/outbox/`;
- the agent 2 (proxy) ACK goes in `communication/agent-1/solo/agent-2-proxy/outbox/`;
- this FREEZE stays at
  `communication/agent-1/solo/agent-3-proxy/outbox/0005-freeze-sl1-subject-substitution.md`.

All three must be in a commit that is an ancestor of HEAD when the run starts.

## Run command (after the resume; output outside the repo)

```
.venv/bin/python -m evaluation.e2 \
  --plan evaluation/evidence/e2/sl1-subject-runner-20261009/integration-plan.json \
  --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl1-run/acks.json \
  --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl1-run/real-e2-output
```

The ACK index `{agent-1, agent-2, freeze}` lists `{commit, path, sha256}` for each record.

- Expected wall time: about 10-11 min (an estimate).
- Ports: PBC 18545 and DBC 18546 only.
- Exit 0 only for `E2_SUBJECT_SUBSTITUTION_SLICE_PASS`.
- A failed or expired trial is kept as it is and published, never retried silently.

## Frozen inputs (any change means a new plan and new ACKs)

All 90 `agent3Sources`:

- `evaluation/**/*.py` except tests, **including evidence scripts**;
- `evaluation/fixtures` and `evaluation/scenarios` JSON;
- `interfaces/v1/**` and `interfaces/proposals/v1/**/*.json`;
- root `AGENTS.md`, `SPEC.md`, `PLAN.md`, `uv.lock` and `pyproject.toml`;
- `evaluation/toolchain.json` and `evaluation/host-tools.json`;
- the E2 start contract and acceptance, and the E1 pin review.

Tools: forge/anvil/cast/solc at the frozen hashes; `.venv/bin/python` 3.13.5 (sha256 3160d212..);
`/usr/bin/python3` and `/usr/bin/bash`, as recorded in the plan.

Do not edit any of these, or root `PLAN.md`, before the run. Current sha256 of the changed evaluator
files:

| File | sha256 |
|---|---|
| e1.py | d236cafb0877e7007279e2a45e99d13deb76b6e5926ea3f000ac9c7e84649650 |
| e2.py | f3ea42febe56f822e80421510c7890a59e1ee0eecbe369782f61583dd7d70781 |
| access_execution.py | 5f28ebd6eb991b9f082d46c62da2e4f5d9a795dfc40649588a0d902372886f6f |
| subject_substitution.py | b18f0e719bc0d3d94b343d1db6de2c44e9c191293264ac1b32a55d4078194acb |
| host_toolchain.py | 9a5b6b31.. |
| host-tools.json | 15e708d6.. |
| rpc.py | 130c763e.. |
| chain.py | 778805715f.. |

## Commit list for agent 1 (SL0 + SL1)

**SL0 (S3-0004):**

- evaluation/host_toolchain.py, evaluation/host-tools.json, evaluation/rpc.py, evaluation/chain.py;
- tests: test_host_toolchain.py, test_solo_review.py, test_cast_checkpoint.py,
  test_e_correspondence.py;
- `evaluation/evidence/e2/sl0-portability-20261009/*`;
- communication/DECISIONS.md.

**SL1:**

- evaluation/e1.py, evaluation/e2.py, evaluation/access_execution.py,
  evaluation/subject_substitution.py;
- evaluation/tests/test_subject_completion_collector.py and test_e2_subject_plan.py;
- `evaluation/evidence/e2/sl1-subject-runner-20261009/*` (6 files).

**Mailbox:** `communication/agent-1/solo/agent-3-proxy/{STATUS.md,HANDOFF.md,outbox/0001..0005}`.

## Known limits

- **D2 has not been exercised live yet:** the second deployment, bootstrap and adapter wiring in
  `e1._profile`. It has had a static check and review only. If it fails, the run fails visibly, and
  the fix needs a new plan and new ACKs.
- **Paper release margin:** about 20 s before `policyEnf + 30 s` (an estimate).
- **`.venv` differs from `uv.lock`** in 4 transitive packages plus colorama (S3-0004). This is
  recorded; the plan pins only direct packages.
