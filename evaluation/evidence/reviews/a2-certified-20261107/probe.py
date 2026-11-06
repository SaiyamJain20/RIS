"""Synthetic-view honest witness controls; no services or owner edits."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SNAP = ROOT / 'evaluation/runs/a2-certified-20261107/snapshot'
sys.path.insert(0, str(SNAP / 'protocol'))
from hmbc_protocol import witness_service as svc, witness_state as ws, messages, eip712

spec = importlib.util.spec_from_file_location('owner_checkpoint_tests', SNAP / 'protocol/tests/test_witness_service.py')
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)
rows = []
MAX = 2**64 - 1

with tempfile.TemporaryDirectory(prefix='a3-sequence-') as directory:
    view = owner.FakeView()
    store = ws.init_store(str(Path(directory) / 'store'), owner.BIND, owner.B, owner.OWNER)
    service = svc.WitnessService(store=store, key=owner.KEY, view=view,
                                 deployment=owner.DEPLOY, witness_set_version='2')
    initial = copy.deepcopy(store.evidence())
    proposal = svc.derive_checkpoint(view, owner.DEPLOY)
    for sequence in (5, 7, MAX):
        wrong = dict(proposal, sequence=str(sequence))
        try:
            service.sign_checkpoint(wrong)
        except svc.WitnessRefusal as exc:
            assert (exc.code, exc.reason) == ('STALE_STATE', 'PROPOSAL_MISMATCH')
            assert 'sequence' in exc.message
            assert store.evidence() == initial
            rows.append(dict(control='fresh-store skip refused without writes', sequence=str(sequence), code=exc.code, reason=exc.reason))
        else:
            raise AssertionError('honest service signed a skipped sequence')
    result = service.sign_checkpoint(proposal)
    # Verify against production message hashing and real secp256k1 recovery.
    digest = messages.digest_of('StateCheckpoint', proposal, messages.domain_for('StateCheckpoint', proposal, owner.DEPLOY))
    assert eip712.recover(digest, result) == owner.ADDR
    assert store.evidence() != initial
    rows.append(dict(control='legitimate sequence 1 signed and persisted', signer=owner.ADDR))
    for current in (5, 7, MAX - 1):
        view.current = dict(sequence=str(current), sourceBlockNumber='250')
        assert svc.derive_checkpoint(view, owner.DEPLOY)['sequence'] == str(current + 1)
        rows.append(dict(control='ordinary advancement', current=str(current), successor=str(current+1)))
    view.current = dict(sequence=str(MAX), sourceBlockNumber='250')
    try:
        svc.derive_checkpoint(view, owner.DEPLOY)
    except ValueError as exc:
        rows.append(dict(control='max+1 cannot encode uint64', exception=type(exc).__name__, message=str(exc)))
    else:
        raise AssertionError('encoded a successor beyond uint64')
    store.close()

(OUT / 'probe-results.json').write_text(json.dumps(rows, indent=2) + '\n')
print(json.dumps(rows, indent=2))
