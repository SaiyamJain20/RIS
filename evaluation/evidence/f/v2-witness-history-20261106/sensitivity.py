"""Deliberate in-memory bypasses; no mutation of product source or evidence."""
import copy
import importlib
import json
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from evaluation.tests.test_witness_history_v2 import fixture, fingerprint, supersede, resign
from evaluation.schema_v2 import _binding_digest

real = importlib.import_module('evaluation.witness_history_v2')
source = (ROOT / 'evaluation/witness_history_v2.py').read_text()
controls = []


def mutant(skip=None, orphan=False):
    changed = source
    if orphan:
        old = "        _require(key in generations, 'superseded key missing live successor')"
        assert changed.count(old) == 1
        changed = changed.replace(old, '        generations.setdefault(key, []) # deliberate orphan admission')
    module = types.ModuleType('deliberate_history_mutant')
    exec(compile(changed, '<deliberate-history-mutant>', 'exec'), module.__dict__)
    if skip:
        original = module._require
        module._require = lambda condition, message: None if message == skip else original(condition, message)
    return module


def control(label, module, m, o, e):
    kwargs = dict(manifest=m, observations=o, expected_owner=e['owner'], compiled_max_admins='8')
    fingerprint(e)
    try:
        real.verify_signed_history(e, **kwargs)
    except ValueError as error:
        refusal = str(error)
    else:
        raise AssertionError('real verifier admitted bad input: ' + label)
    result = module.verify_signed_history(e, **kwargs)
    controls.append(dict(name=label, originalRefusal=refusal, mutantAccepted=result))


m, o, e = fixture(); supersede(m, e, 'AccessDecision'); e['conflicts'].pop(0)
control('orphaned history', mutant(orphan=True), m, o, e)

m, o, e = fixture(); supersede(m, e, 'AccessDecision')
e['conflicts'][0]['digests'][0]['observation']['timestamp'] = '1049'
control('generation signed before previous death', mutant('generation before prior death'), m, o, e)

m, o, e = fixture(); row = e['conflicts'][0]
row['digests'][0]['digest'] = '0x' + '99' * 32
control('claimed digest differs from signed bytes', mutant('signed digest mismatch'), m, o, e)

m, o, e = fixture(); row = e['conflicts'][0]
row['domainSeparator'] = '0x' + '99' * 32
control('claimed domain differs from fixed HMBC domain', mutant('domain separator mismatch'), m, o, e)

m, o, e = fixture()
e['binding']['document']['chains']['pbc']['genesisHash'] = '0x' + '99' * 32
e['binding']['binding_v2'] = _binding_digest(e['binding']['document'])
e['marker']['binding_v2'] = e['binding']['binding_v2']
control('export-selected binding', mutant('binding differs from reconstructed context'), m, o, e)

m, o, e = fixture(); row = e['conflicts'][0]
good = dict(digest=row['digests'][0]['digest'], domainSeparator=row['domainSeparator'])
row['digests'][0]['signature'] = resign(m, row,
    signer=sorted(m['fixture']['witnessSet']['witnesses'])[-1])['signature']
module = mutant(); original_signature = module.verify_bound_signature
bad_signature = row['digests'][0]['signature']
def bypass_one_signature(name, message, signature, **kwargs):
    return good if signature == bad_signature else original_signature(name, message, signature, **kwargs)
module.verify_bound_signature = bypass_one_signature
control('missing owner signature recovery', module, m, o, e)

m, o, e = fixture(); supersede(m, e, 'GovernanceAction')
old, live = e['superseded'][0], e['conflicts'][-1]
live['effect'] = copy.deepcopy(old['effect']); live['digests'] = [resign(m, live)]
control('adjacent repeated effect is not supersession', mutant('adjacent equal generation effects'), m, o, e)

print(json.dumps(dict(classification='deliberate in-memory bypasses; synthetic extension checks', controls=controls), indent=2))
