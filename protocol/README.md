# Module 2: Protocol and key services

Owner: **agent 2**. Paper-derived reconstruction of HMBC2020's client/relay/witness/key-service side. Synthetic data only. This is **not** the authors' implementation.

Read [the root plan](../PLAN.md), [specification](../SPEC.md), [interfaces](../interfaces/README.md), and [communication rules](../communication/PROTOCOL.md).

## State (2026-10-12): E implemented and exercised; F not started; G locked

- **Interface:** v1, frozen (freeze `E0-v1-r6-20261008`, `FREEZE.json` f700292e..). This module maps it; it does not own it.
- **Phase:** gate E was recorded PASS by agent 3 on `origin/agent-1` (4a68082) **under the solo phase, with correlated same-model review** (A1-0059, A1-0086). The original agent 2 re-verified the
  protocol-scope part on return (A2-0039); a gate decision is agent 3's. `communication/BOARD.md` on this branch may predate that record. F needs its own plan and a human go-ahead.
- **Pin of the integrated E runs:** protocol `0716a8e`, manifest `d16ddad8..` (108 entries). `hmbc_protocol/**`, `testtools/**`, `exports/**` and `abi/**` are byte-identical to it except
  **`hmbc_protocol/worker_log.py`** (A2-0039: the evidence exporter now percent-encodes the state path; see below). Every gate E run used the old `worker_log.py` bytes, so a later integrated run
  needs a new exact plan and ACKs for the changed file. The other differences from the pin are tests, `tools/mutation_check.py` and evidence.
- **Working manifest:** `evidence/source-manifest.sha256` (`sha256sum -c` from the repository root). It does not list itself.

## What exists (symbolic mode only)

| Layer | Modules |
|---|---|
| Wire and signing | strict EIP-712 encoder `eip712.py`; strict wire validators `wire.py`; typed-message builders `messages.py`; opaque key handles and recipient-key convention `keys.py`; symbolic commitments `symbolic.py` |
| Chain access | ABI codec `abi.py`; chain client with a pending-block clock and loopback/no-redirect pinning `chain.py`; deployment loader with ABI-hash pinning `ledger.py` (ABIs in `abi/`) |
| Actors | user client `client.py`; honest relay `relay.py`; one trusted witness `witness.py` (checkpoint / decision / grant receipt, repaired-e only); durable key worker `worker.py` (record registry, intent-before-send release, crash recovery, completion) |
| Boundary | JSON-lines adapter `adapter.py` (eight closed operations; `rotate_epoch` answers `NOT_IMPLEMENTED_IN_PHASE`); generated `exports/`; read-only evidence exporter `worker_log.py` |
| TEST-ONLY (outside the adapter boundary, not in `exports/adapter.json`) | crash hook `testtools/faulty_adapter.py`; deliberate receipt deviation `testtools/deviating_witness.py` (A40); bootstrap producer `testtools/bootstrap_fixture.py` |

**Limits to read before citing anything from this module:** symbolic decryptability only (no ABE, no ciphertext secrecy, no performance claim); one trusted witness (q = 1) and a trusted
worker; TEST-ONLY keys derivable from labels, so custody is procedural; logical crash points only (not power loss or OS kill); delivery stays `unknown`; Anvil without consensus; two chains with
uncorrected clock skew; `encrypt_record` is unauthenticated (first writer wins). A31 ("`collect_decision` retries at most once per accepted checkpoint") is caller-side discipline: the witness is
stateless and does not enforce it.

## Commands (repository root unless stated)

- **Tests** (Python 3.13 with the packages of the frozen root `uv.lock`, sha256 1fb4777a.., present in the integrated tree; live tests need Foundry 1.8.5 and solc 0.8.37 at the hashes in
  `interfaces/v1/toolchain.json` (integrated tree), plus the pinned ledger commit `91add8c` in the local git object store):
  `python -m pytest protocol/tests -q -rs -c protocol/pytest.ini --rootdir protocol -p no:cacheprovider` (about 5-6 minutes). Last verified run: 1383 passed, 201 skipped, exit 0, 324 s (2026-10-12, Python 3.13.12, Foundry 1.8.5).
  **Read the skip count, not only "passed".** The live fixtures `pytest.skip` when Foundry or the pinned commit is missing, so a machine without them still reports green. The expected 201
  skips are all "ScenarioResult/FileHash is not agent-2's scope" (`test_boundary_review*.py`, `test_candidate_schema_review.py`); any other skip means live tests did not run.
  `HMBC_FOUNDRY_DIR` names the Foundry directory; optional `HMBC_TEST_PORT_RANGE=LOW-HIGH` confines the Anvil pairs to that range (S2-0006).
- **Exports:** `PYTHONPATH=protocol python -m hmbc_protocol.export [--check]`
- **Mutation check:** `python protocol/tools/mutation_check.py [--only suite,...] [--grep substring|...]` (edits sources in place: run it on a scratch copy; `detected` means a non-zero pytest exit,
  so read the recorded tail, which must be a failed assertion and not a collection error).
- **Adapter:** `cd protocol && python -m hmbc_protocol.adapter --state-dir <new private 0700 dir> --deployment <deployment.json>` (JSON lines on stdin/stdout; the deployment is PINNED: RPC URLs,
  addresses and the witness key label never come from a request). One adapter and one NEW state directory per deployment.
- **Worker evidence:** `cd protocol && python -m hmbc_protocol.worker_log --state-dir <the adapter's state dir>` (read-only; tokens are exported only as keccak digests).
- **Crash hook (TEST-ONLY):** `cd protocol && python -m testtools.faulty_adapter --crash-at after_intent|after_send --state-dir D --deployment F`; restart with the PRODUCTION adapter command.

## Known limits and stale labels (honest accounting, not fixed in the pinned bytes)

1. **Stale E0/E1 wording in pinned files.** `exports/adapter.json` (`serviceStatus`, per-operation `status: "candidate-b-e1-not-unlocked"`, `draftNote`) still says E1 is not unlocked and no service is READY, and the module
   docstring of `hmbc_protocol/adapter.py` still describes only `prepare_request` as implemented (it says the other four answer `ADAPTER_UNAVAILABLE`). That was true on 2026-10-08. E1 completed (A3-0030), the owner service was published READY
   (A2-0014/A2-0016) and the integrated E runs used this code. The strings are labels; behaviour is unaffected. They were left unchanged because `exports/**` and `adapter.py` are pinned bytes
   consumed by agent 3's frozen plans; correct them in the next reviewed production revision.
2. **The worker's deployment fingerprint binds chain ids and the PSC/RSC/KSSC/ACSC addresses only** (`worker.py`), not the profile, mutation bits, deploy block or build. Measured on fresh
   Anvil pairs (`evidence/return-review-2026-10-12/fingerprint-measurement.txt`): clean repaired-e, `mutant-no-nonce`, `mutant-no-receipt-binding`, paper-strict and paper-minimal all give
   fingerprint `9886222d..`, so a state directory reused across a clean run and a mutant run would be accepted. The runner's rule (one NEW state directory per deployment) kept every run
   correct. The same formula is recomputed by `evaluation/worker_evidence.py`, so changing it is an interface change (RFC and agent 3's ACK), not a unilateral edit.
3. **`testtools/deviating_witness.py` reads the deployment with plain `json.loads`** (duplicate keys last-wins, NaN accepted) while the adapter uses `strict_loads`. TEST-ONLY; safe when given the
   byte-identical file the adapter was pinned with (R11, S2-0007).
4. A retry returns the *same response* because the token and release row are durable and every other field is an immutable ledger fact (`RSC.register` is write-once), not because the response
   bytes are stored.

Fixtures under `tests/fixtures/` are byte copies of peer files at exact commits (hashes pinned in the tests); keys are TEST-ONLY synthetic keys.
Review records: `evidence/independent-review-2026-10-08.md` (author-adjacent), `evidence/p2-t1-t3/` and `evidence/reviews/` (solo-phase proxy, correlated), `evidence/return-review-2026-10-12/` (A2-0039).

## Assigned tasks

B-E1, B-E2, B-F1, G0 (adapter lead), B-G1. The authoritative task steps and file lists are in `PLAN.md`; do not keep a divergent copy here.
No F implementation before gate F planning is approved; no G implementation before gate F. Do not implement JANUS or create a worktree.

## Module handoff

READY messages go in `communication/agent-2/outbox/`; `communication/agent-2/HANDOFF.md` records exact hashes, commands and limits.
