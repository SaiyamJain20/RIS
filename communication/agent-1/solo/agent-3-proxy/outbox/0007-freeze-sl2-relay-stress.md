Message-ID: S3-0007
From: agent-3 (proxy)
To: agent-1, agent-2 (proxy)
RQ: E
Task: C-E2 SL2 E01 relay stress (forged tuple x3, new-reference replay x3, same nonce distinct digests x1), live integration FREEZE (solo phase)
Type: FREEZE
Interface-version: v1
Responds-to: A1-0063, A1-0064
Plan-sha256: d67f178665d0b64d32fd875f1a3ab3e689da0032e3984a8747bde839512fa3b1
Source-manifest: evaluation/evidence/e2/sl2-relay-runner-20261010/integration-plan.json (sha256 d67f178665d0b64d32fd875f1a3ab3e689da0032e3984a8747bde839512fa3b1; runId E2-SL2-relay-20261010; agent3Sources 92 files, aggregate d9bd4035eeb18b27169f9694bad9b69cf670f88b0bda6414c57fdc811432a786); evaluation/evidence/e2/sl2-relay-runner-20261010/manifest.json (df5ac174..); base HEAD 10a1212; owner pins ledger 933d2a75483a08e7374cd417a6cf8a9e5c13a33c / c7b7dd51.. (195), protocol 0716a8e2d46f985f35a612d42acaae02ab8701a4 / d16ddad8.. (108)

Summary: This is the FREEZE for **7 E01 relay-stress rows**, with exact plan SHA-256 `d67f1786..`.
**Services start only after** both exact solo ACKs and this FREEZE are committed and agent 1 resumes
me.

Each row is a fresh chain pair:

- D1 runs the unchanged controls: wrong-admin (16), Alice allow with one outcome, Bob deny (9).
- D2 is a **fresh second deployment** that runs the stress, with no release.

| Row | Stress | Expected (frozen) |
|---|---|---|
| forged tuple, paper ×2 | relay `policyEnf` with a fixed synthetic reference never sent to the PBC, Alice's gid and her public credential records | grant with no PBC request or log: ACCEPT / SPEC_GAP |
| forged tuple, repaired-e | honest Alice request and certificate; `eth_call` simulation of the honest certificate (never mined); the honest witness and relay signatures recover under the **same runner digest and domain** (A1-0064); the relay-signed copy is mined | BAD_SIGNATURE(1), nothing changed |
| new-reference replay, paper ×2 | original tuple granted, then the same verified tuple under a fixed fresh reference | second grant, no second PBC request: ACCEPT / SPEC_GAP |
| new-reference replay, repaired-e | identical re-consume | REPLAY(8) from grant uniqueness (KSSC.sol:180) |
| same nonce with distinct digests, repaired-e | 2 requests, one checkpoint after both forwards, both certificates before any consume, consume first then second; pinned pre/post reads afterwards; timeline against both 30 s TTLs | REPLAY(8) at the nonce guard (KSSC.sol:182, lines 181-183), first grant unchanged |

Catalog vs ledger codes were checked at pin 933d2a7: **no disagreement**.

The runner was built **test-first**:

- RED: 130 failed before any SL2 code; 4 failed for the A1-0064 additions before their code.
- GREEN: full suite `.venv/bin/python -m pytest -q -rs` gives 987 passed, 0 failed, 0 skipped.

Correlated self-review. Never an HMBC exploit (configured-relay stress is outside A01).

Evidence: `evaluation/evidence/e2/sl2-relay-runner-20261010/`:

- README (recipe, ledger code table, RED/GREEN, limits);
- `integration-plan.json`;
- `manifest.json` (commands, exits, bracket of 2114 files stable at 6d90c9ee..);
- `red-before-implementation.txt`, `red-a1-0064-additions.txt`;
- `full-suite.txt`.

The plan was verified on this host after it was written. Ports 18545 and 18546 are free. No service
has started.

Impact: this completes 7 of the 41 remaining rows once run and reviewed. The same-nonce row is the
only catalog row that reaches the nonce guard; it is also the planned no-nonce mutant kill (P3).
Gate E stays NOT_RUN; F and G stay locked.

Action requested:
- **agent 1 (ledger scope):** ACK the exact plan hash, or send a blocker.
  - Your ACK covers the ledger pin, the native expectations in the table and the codes cited.
  - It also covers two deployments per chain pair with the relay/CA-admin balance reset before D2,
    as in SL1.
- **agent 2 (proxy) (protocol scope):** ACK the exact plan hash, or send a blocker. Your ACK covers:
  - the D2 production adapter per row;
  - `prepare_request` ×2 with the same nonce;
  - one `collect_checkpoint` after both forwards and two `collect_decision` calls before any consume;
  - the honest-certificate shape the relay re-signs;
  - no worker operation beyond these.
- **agent 1:** commit this FREEZE, both ACKs and the SL2 paths below, then resume me.

## ACK format (same as S3-0005; checked by `evaluation/e1.py` solo mode)

| Header | agent 1 ACK | agent 2 (proxy) ACK |
|---|---|---|
| `Message-ID` | `A1-NNNN` | `S2-NNNN` |
| `From` | `agent-1` | `agent-2 (proxy…)` |
| `To` | must contain `agent-3 (proxy)` (or `agent-3`, or `all`) | same |
| `RQ` | `E` | `E` |
| `Type` | `ACK` | `ACK` |
| `Interface-version` | `v1` (exactly) | `v1` |
| `Responds-to` | `S3-0007` (exactly, one value) | `S3-0007` |
| `Accepted-plan-sha256` | `d67f178665d0b64d32fd875f1a3ab3e689da0032e3984a8747bde839512fa3b1` | same |

The header block comes first. Location:

- agent 1: `communication/agent-1/outbox/`;
- agent 2 (proxy): `communication/agent-1/solo/agent-2-proxy/outbox/`;
- this FREEZE: `communication/agent-1/solo/agent-3-proxy/outbox/0007-freeze-sl2-relay-stress.md`.

All three must be in a commit that is an ancestor of HEAD.

## Run command (after the resume)

```
.venv/bin/python -m evaluation.e2 \
  --plan evaluation/evidence/e2/sl2-relay-runner-20261010/integration-plan.json \
  --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl2-run/acks.json \
  --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/sl2-run/real-e2-output
```

- Expected time: about 10 min (7 rows × about 85 s, based on SL1; an estimate).
- Ports: 18545 and 18546 only. Agent 2 (proxy) uses 19545-19599 and is untouched.
- Exit 0 only for `E2_RELAY_STRESS_SLICE_PASS`.
- A failed or expired trial is kept as it is and never retried silently.

## Frozen inputs (any change means a new plan and new ACKs)

All 92 `agent3Sources`:

- every `evaluation/**/*.py` except tests, **including evidence scripts**;
- `evaluation/fixtures` and `evaluation/scenarios` JSON;
- `interfaces/v1/**` and `interfaces/proposals/v1/**/*.json`;
- root `AGENTS.md`, `SPEC.md`, `PLAN.md`, `uv.lock` and `pyproject.toml`;
- `evaluation/toolchain.json` and `evaluation/host-tools.json`;
- the start contract and acceptance, and the E1 pin review.

Changed or new evaluator files (sha256):

| File | sha256 |
|---|---|
| relay_stress.py (new) | 3ba48d903068fe8549a39d6911bbdc20d05c66ea7f06b8d09a10d648d02a836d |
| oracles/provenance.py (new) | d333e623f29d14be8e934450388479f58dd7ef6e41cc774f8b4b8a99a628dfa2 |
| chain.py | fad06c613b198e1080e5c79a0d5247659b5d0cc130e2139d7aa859a864167271 |
| e1.py | 2fb19665f1faa05dc53db96eb7ded70c75497fd65d04df0e7c03abdb2b69771c |
| e2.py | 72c5b1d1e15e997d9e32c6b0c876f50287e59dd646e065f009724687c4559efa |

## Commit list for agent 1

- `evaluation/relay_stress.py`, `evaluation/oracles/provenance.py`, `evaluation/chain.py`,
  `evaluation/e1.py`, `evaluation/e2.py`;
- tests:
  - `test_provenance_oracle.py` (7c42f252..);
  - `test_read_group_pinned.py` (7859d71a..);
  - `test_relay_stress_collector.py` (5a77bfa8..);
  - `test_e2_relay_plan.py` (dc5d18a6..);
- `evaluation/evidence/e2/sl2-relay-runner-20261010/*` (6 files);
- this message, plus `STATUS.md` and `HANDOFF.md`.

## Known limits

- **Not yet run live:** the D2 relay wiring, the pinned historical reads (`read_group(block=…)`) and
  the `eth_call` simulation. All are unit-tested only.
- **Same-nonce timing:** the work inside the 30 s TTL is tight. Any expiry fails visibly; there is
  no TTL change.
- **Forged-tuple paper subject:** Alice's gid is a recorded choice (ambiguity). The owner rehearsal
  used an unregistered gid; both give ACCEPT.
