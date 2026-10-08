# Module 2: Protocol and key services

Owner: **agent 2**. Paper-derived reconstruction of HMBC2020's client/relay/witness/key-service side. Synthetic data only.

Read [the root plan](../PLAN.md), [specification](../SPEC.md), [interfaces](../interfaces/README.md), and [communication rules](../communication/PROTOCOL.md).

## State (E0 accepted? NO. 2026-10-08; interface candidate v1 revision 4, not frozen)

**Phase honesty.** E0 is not accepted and E1 is not unlocked, so everything below the "E0 contract" line is **candidate B-E1/B-E2 code** written ahead of the unlock
(at the user's instruction), tested against agent 1's pinned ledger on a local Anvil pair. Nothing here is READY for integration or an E1/E2/RQ1 result. F and G are untouched (locked).

E0 contract (implemented): strict EIP-712 encoder (`eip712.py`), strict wire validators for the revision-4 boundary types (`wire.py`), typed-message builders (`messages.py`),
opaque key handles and the recipient-key convention (`keys.py`), symbolic commitments (`symbolic.py`), JSON-lines adapter (`adapter.py`), generated `exports/`.

Candidate B-E1 (symbolic mode only): ABI codec (`abi.py`), chain client with a pending-block clock and loopback/no-redirect pinning (`chain.py`), deployment loader with ABI-hash pinning
(`ledger.py`, ABIs in `abi/`), user client (`client.py`), honest relay (`relay.py`), single trusted witness (`witness.py`: checkpoint / decision / grant receipt),
durable key worker (`worker.py`: record registry, intent-before-send release with crash recovery, completion). The adapter's `collect_decision`, `release`, `encrypt_record`,
`finish_decryption` are wired to these; `prepare_request` is E0; `rotate_epoch` is `NOT_IMPLEMENTED_IN_PHASE`. Checkpoint and receipt signing are NOT adapter operations yet (RFC A2-0008).

Candidate B-E2: `tests/test_e2_repaired_e.py` runs the 13 repaired-e E01/E02/E03 cases of agent 3's pinned catalog (12 agree; E01-subject-substitution is a strict xfail).

- Tests (repo root, Python 3.13, `pip install -r protocol/requirements.txt`; live tests need Foundry 1.8.5 at `~/.local/share/hmbc-tools/foundry-1.8.5` or `HMBC_FOUNDRY_DIR`, and the pinned ledger commit in the local git object store):
  `python -m pytest protocol/tests -q -c protocol/pytest.ini --rootdir protocol` (~2 min; live fixtures start their own Anvil pair on free ports and stop only those)
- Regenerate/check exports: `PYTHONPATH=protocol python -m hmbc_protocol.export [--check]`
- Mutation check: `python protocol/tools/mutation_check.py [--only witness,worker,chain,...]` (edits sources in place: run it on a scratch copy with `GIT_DIR` set)
- Run the adapter: `cd protocol && python -m hmbc_protocol.adapter --state-dir <private 0700 dir> --deployment <deployment.json>` (JSON lines on stdin/stdout;
  the deployment is PINNED: RPC URLs, addresses and the witness key label never come from a request)

Fixtures under `tests/fixtures/` are byte copies of peer files at exact commits (hashes pinned in the tests); keys are TEST-ONLY synthetic keys. Independent review record: `evidence/independent-review-2026-10-08.md`.

## Assigned tasks

B-E1, B-E2, B-F1, G0 (adapter lead), B-G1. The authoritative task steps and file lists are in `PLAN.md`; do not keep a divergent copy here.
No F implementation before gate E; no G implementation before gate F. Do not implement JANUS or create a worktree.

## Module handoff

READY messages go in `communication/agent-2/outbox/`; `communication/agent-2/HANDOFF.md` records exact hashes, commands and limits.
