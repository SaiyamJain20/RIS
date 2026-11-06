# Agent 2 source READY evidence (isolated successor source, NOT an execution ACK)

Source commit `dbae4e1e13fb26984a6d4b0aa042ae321c1c49f0` (branch `agent-2`); manifest `MANIFEST.sha256` (384 files under `protocol/`, sha256 `6ed9a53de1ec2ec32fedad01019ce18cd4196a304cc47202b4a0e3655218ca08`); the 52 F0 pins under `protocol/f0` verify against `protocol/f0/MANIFEST.sha256` at this commit (script check, 0 mismatches). Between source commit 076bde2 (when the full-suite run started) and this commit only evidence documents changed under `protocol/` (`git diff --stat 076bde2 dbae4e1 -- protocol`: the evidence README and the full-suite output). This directory is added by a LATER commit and is excluded from the manifest.

## Commands and results (all from `/home/karma/Documents/RIS-agent-2`, venv python 3.13.13 on Linux 6.19.14, UTC 2026-11-06)

| Command | Exit | Result |
|---|---|---|
| `python -B -m pytest -q -c protocol/pytest.ini --rootdir protocol -p no:cacheprovider protocol/tests -rs` | 0 | 2226 passed, 201 skipped, 363 s (`../af2-state/full-suite-0f7-after-7b.txt`); 2427 collected; the 201 skips are 200 `ScenarioResult` and 1 `FileHash` schema-review cases out of agent 2's scope |
| `PYTHONPATH=protocol python -B -m hmbc_protocol.export --check` | 0 | `exports match 9 files` |
| the 13 mutation runners `python -B -I protocol/tools/run_*_mutants.py` | all 0 | detected counts in `MAPPING.md` section 3; per-runner output, exit codes and start/end UTC times in `mutants/` (`_exits.txt`; commit hash in `_commit.txt`) |
| E source manifest check (script: sha256 of each of the 142 entries of `protocol/evidence/source-manifest.sha256`) | n/a | exactly 2 mismatches, both intended: `worker_log.py`, `deviating_witness.py` |

Tool versions: Python 3.13.13; eth-account 0.14.0, eth-utils 6.0.0, eth-keys 0.8.0, eth-hash 0.8.0, hexbytes 2.0.0, pycryptodome 3.24.0, jsonschema 4.26.0, pytest 9.0.2. The test venv is a scratchpad venv whose `.pth` points read-only at agent 3's site-packages (agent 3 owns the root dependency lock); `protocol/requirements.txt` is unchanged (no new package). No Foundry/Anvil binary is installed on this machine; I did not check which carried E tests would use one.

Fixtures and configuration: synthetic keys (`keys.synthetic_private_key`), byte-copied published schema and manifests listed in `MAPPING.md` section 1, TEST-ONLY allow-list for governance approval (a witness with none signs nothing). No external message or deployment.

## Failed trials and corrections (kept, not hidden)

First mutation runs below 100%: pool driver 13/18 (`pool-driver-mutants-run1-13-of-18.txt`), binding_open 46/52, worker_binding 30/32, adapter_v2 42/43, witness handlers 52/64 (`adapter-v2-witness-mutants-run1-52-of-64.txt`), startup 15/16, Byzantine 15/16; each survivor was either a gap in my tests (fixed, rerun) or an equivalent mutant (recorded). Process slips admitted: implementation written before the first red run in slices 4a and 3c (the red run on file was made by moving the module aside). A slice-1 defect found by slice 5b (a marker next to missing binding rows classified wrongly; fixed with 6 red tests and mutant S25). My first claim that the 201 skipped tests needed a live ledger was wrong and is corrected in `../af2-state/README.md`, STATUS and HANDOFF. Details per slice: `../af2-state/README.md`.

## Limitations (plain)

Isolated synthetic source only. NOT built: a command line and the real wiring (JSON-RPC chain views, real `Worker` factory, supervised witness processes, a real transport and clock); so the adapter cannot yet be launched end to end. The pool and witnesses are tested against ONE shared fake ledger view and the TEST-ONLY virtual transport; independent views, real timing, persistence across process kills (only `witness_state` crash hooks), disk rollback, and H2/H5/H6 are not exercised. A consistent rollback of a witness store is not detectable locally (INVENTORY FM-14); the symbolic model shows the equivocation. The carried `witness.py` is not changed (new modules instead; stated in `MAPPING.md` section 2). Same-model review of every test and mutant by the author: correlated, not independent. This READY claims no F gate, no E parity result and no integrated execution; separate reviewed exact owner READYs and a complete execution FREEZE with exact ACKs are still required.
