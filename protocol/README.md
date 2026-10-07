# Module 2: Protocol and key services

Owner: **agent 2**. Paper-derived reconstruction of HMBC2020's client/relay/witness/key-service side. Synthetic data only.

Read [the root plan](../PLAN.md), [specification](../SPEC.md), [interfaces](../interfaces/README.md), and [communication rules](../communication/PROTOCOL.md).

## State (E0, 2026-10-07; interface candidate v1 revision 3, NOT frozen)

Implemented and tested: strict EIP-712 encoder (`hmbc_protocol/eip712.py`), strict wire validators (`wire.py`), typed-message builders (`messages.py`),
opaque key handles (`keys.py`), and the JSON-lines adapter (`adapter.py`) with only `prepare_request` behaving. Every other E operation answers
`ADAPTER_UNAVAILABLE` and `rotate_epoch` answers `NOT_IMPLEMENTED_IN_PHASE`: B-E1 (client/relay/witness/key worker) is locked until E0 unlocks E1.
No service, relay, witness, durable worker or live-chain code exists yet.

- Run tests (repo root, Python 3.13, `pip install -r protocol/requirements.txt`): `python -m pytest protocol/tests -q -c protocol/pytest.ini --rootdir protocol`
- Regenerate/check exports: `PYTHONPATH=protocol python -m hmbc_protocol.export [--check]` (adapter.json and examples are produced by running the adapter)
- Mutation check of the boundary code: `python protocol/tools/mutation_check.py`
- Run the adapter: `cd protocol && python -m hmbc_protocol.adapter --state-dir <private dir>` (JSON lines on stdin/stdout)

Fixtures under `tests/fixtures/` are byte copies of peer files at exact commits (hashes pinned in the tests); they are TEST-ONLY synthetic keys.

## Assigned tasks

B-E1, B-E2, B-F1, G0 (adapter lead), B-G1. The authoritative task steps and file lists are in `PLAN.md`; do not keep a divergent copy here.
No F implementation before gate E; no G implementation before gate F. Do not implement JANUS or create a worktree.

## Module handoff

READY messages go in `communication/agent-2/outbox/`; `communication/agent-2/HANDOFF.md` records exact hashes, commands and limits.
