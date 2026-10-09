# SL0: solo-phase evaluator portability (no services)

Paper-derived HMBC2020 reconstruction. Synthetic only. E/RQ1 is active; gate E is NOT_RUN; F and G
are locked.

Author: agent 3 (proxy), under the human solo directive (A1-0059) and agent 1's rulings A1-0061
D-1..D-5. **This is correlated self-review:** agent 1 and both proxies are the same model.

No service, chain, adapter or worker was started. No Git write was made.

## What changed (all in `evaluation/**`; frozen bytes untouched)

| Change | Files | Decision |
|---|---|---|
| Tools resolve to host paths only when their bytes hash to the **frozen** pins. A frozen path that is present never falls through. ProVerif alone may be a declared local build of the frozen version and source. | `host_toolchain.py` (new), `host-tools.json` (new), `e1.create_plan` | D-2 |
| Disclosed solo review mode: `S3-NNNN` FREEZE; `A1-NNNN` plus `S2-NNNN` (from `agent-2 (proxy…)`) ACKs; a committed FREEZE carrying `Plan-sha256`; every blob read from a commit that is an ancestor of HEAD; `reviewMode` and the disclosure in plans and records. Strict A2/A3 verification is unchanged. | `e1.py` (`_solo_acks`, `_verify_solo_ack_message`, `_verify_solo_freeze`), `e2.py` | D-1 |
| Solo ports: PBC 18545, DBC 18546. Chain IDs stay 18545/28545. Strict plans are unchanged. | `e1.create_plan` | D-3 |
| Python 3.13.5 is recorded as `hostDifferences` against the frozen 3.13.13 | `e1.create_plan` (solo) | D-4 |
| Cast hash `checkpoint` policy: hashed at construction, each `read_group`, each `submit`, and run start and end. A mismatch refuses that call and every later one. Rows record `hashPolicy`. Per-call hashing stays the default. | `rpc.py`, `chain.py`, `e1._profile` | D-5(b) |
| The ProVerif test uses the resolver instead of the frozen path | `tests/test_e_correspondence.py` | D-2 / G-2 |

D-5(c) is a collector rule: a block-pinned native snapshot may be taken after the release. It is
applied per slice from SL1 on; nothing in SL0 depends on it.

## Verification (exact commands in `manifest.json`)

**RED.**

- New tests before implementation: 39 failed, 2 passed, 7 errors (exit 1) in `red-new-tests.txt`.
- The 27 host failures on unchanged tree 78cdd11 are agent 1's P1 baseline
  (`communication/agent-1/solo/evidence/p1-integrated-baseline/`):
  - 20 failures in e1/e2 freeze, from tool paths;
  - 1 interrupt test, which returned BLOCKED at the tool check before `_profile`;
  - 6 in ProVerif correspondence, where the binary was absent.

**GREEN.**

- Targeted: 152 passed.
- Full suite: `.venv/bin/python -m pytest -q -rs`, exit 0, **825 passed, 0 failed, 0 skipped**,
  214.99 s, in `full-suite.txt`. That is 777 earlier tests plus 48 new ones.

**Inputs unchanged during the suite:** 1950 files, aggregate 0e74f378.. both before and after.

**The 7 ProVerif tests ran the declared local build** (bc2cd5ed..). Their verdicts and the
reconstructed counterexample match the expectations written for A3-0033. This is the G-2 re-run on
this host; it is symbolic only.

## Host facts and residual differences (not hidden)

- `host-tool-resolution.json`: forge, anvil, cast and solc resolve to `host-override` with the frozen
  hashes. ProVerif resolves to `declared-local-build`.
- `venv-vs-lock.json`: `.venv` (created by agent 1) does **not** match `uv.lock` exactly for 5
  transitive packages:

  | Package | `uv.lock` | Installed |
  |---|---|---|
  | cytoolz | 1.1.0 | 1.2.0 |
  | toolz | 1.1.0 | 1.2.0 |
  | pydantic | 2.13.5 | 2.14.0 |
  | pydantic-core | 2.46.5 | 2.50.0 |
  | colorama | 0.4.6 | absent |

  The five direct pins (eth-account, eth-abi, eth-utils, jsonschema, pytest) and the `uv.lock` hash
  match. Plans verify only those pins. This is a recorded host difference. Re-pinning the shared
  `.venv` is left to agent 1, because agent 2 (proxy) runs protocol tests in it concurrently.
- `solo-plan-sample.json`: a **sample** solo E2 plan (`S3-0000`), **not for execution and never
  ACKed**. It shows the new fields: `reviewMode`, ports, `castHashPolicy`, `hostDifferences`,
  `hostToolOverride`.

## Limits

- The `_profile` wiring (run-start/run-end Cast checkpoints, the per-row `castStable` record, the
  18546 DBC port) is unit-reviewed but only exercised live in SL1.
- The solo ACK verifier was tested with in-memory Git doubles; no repository write was made. Its
  first real use is the SL1 FREEZE.
- `evaluation/e0_verify.py` is E0-era (A1-0014 manifest, frozen ProVerif path). It was not ported and
  is not part of the gate.
