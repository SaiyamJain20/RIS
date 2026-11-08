"""Deliberate in-memory join removals, never written to production source.

Each bad fixture must be refused by the real implementation and admitted when
only its named join is bypassed. Synthetic extension controls, not findings.
"""
import copy
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from evaluation import binding_context_v2 as subject

spec = importlib.util.spec_from_file_location('synthetic_binding_fixtures', ROOT / 'evaluation/tests/test_binding_context_v2.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
controls = []
original = subject._same
for name, labels in (
    ('configured', {'LSC.configured'}),
    ('immutable-wiring', {'PSC.rsc'}),
    ('governance-ttl', {'Governance.maxGovernanceTtl'}),
    ('masked-runtime', {'masked build'}),
    ('read-anchor', {'LSC code block'}),
    ('self-selected-export', {'export document', 'export digest'}),
):
    m, o, d = fixtures.fixture()
    if name == 'configured': o['pbc']['views']['LSC']['configured']['value'] = False
    elif name == 'immutable-wiring': o['pbc']['views']['PSC']['rsc']['value'] = fixtures.address(999)
    elif name == 'governance-ttl': o['pbc']['views']['Governance']['maxGovernanceTtl']['value'] = '121'
    elif name == 'masked-runtime': o['pbc']['code']['LSC']['value'] = '0xff' + o['pbc']['code']['LSC']['value'][4:]
    elif name == 'read-anchor': o['pbc']['code']['LSC']['anchor']['hash'] = '0x' + 'ff' * 32
    export = {'owner': 'worker', 'document': copy.deepcopy(d),
        'binding_v2': fixtures.digest(b'hmbc-deployment-binding/v2\n' + fixtures.canonical(d).encode()),
        'anchor': {k: v['anchor'] for k, v in o.items()}}
    if name == 'self-selected-export':
        export['document']['chains']['pbc']['genesisHash'] = '0x' + 'ff' * 32
        export['binding_v2'] = fixtures.digest(b'hmbc-deployment-binding/v2\n' + fixtures.canonical(export['document']).encode())

    def run():
        if name == 'self-selected-export':
            return subject.verify_export(export, m, o, expected_owner='worker', compiled_max_admins='8')
        return subject.reconstruct(m, o, compiled_max_admins='8')

    try:
        run()
    except ValueError:
        pass
    else:
        raise AssertionError(name + ': real checker admitted bad observation')
    try:
        subject._same = lambda actual, expected, label: None if label in labels else original(actual, expected, label)
        run()
    finally:
        subject._same = original
    controls.append({'name': name, 'realChecker': 'REFUSED', 'joinRemoval': 'ADMITTED', 'removedJoins': sorted(labels)})
print(json.dumps({'classification': 'deliberate in-memory mutations; synthetic extension tests', 'controls': controls}, indent=2))
