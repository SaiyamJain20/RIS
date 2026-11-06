"""Coordinator probes of supplied-schema selection and exact manifest binding.

Synthetic calls to the public Context/handle_line API; no chain or owner store.
Also retain controls demonstrating what optional schema/output validation omits.
"""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
SNAPSHOT = ROOT / 'evaluation/runs/a2-ready-20261106/snapshot'
sys.path.insert(0, str(SNAPSHOT / 'protocol'))
from hmbc_protocol import adapter_v2 as adapter

SCHEMA = json.loads((ROOT / 'interfaces/v2.1/hmbc.schema.json').read_text())
FIXTURES = SNAPSHOT / 'protocol/tests/fixtures'
F = json.loads((FIXTURES / 'agent1-85c59f5-f-base-deployment.json').read_text())
E = json.loads((FIXTURES / 'agent1-85c59f5-e-successor-v2.1-deployment.json').read_text())
results = []


def context(manifest, revision='v2.1', schema=SCHEMA):
    return adapter.Context(manifest=manifest, schema_revision=revision,
                           handlers={'collect_checkpoint': lambda value, ctx: {'probe': True}}, schema=schema)


def refuses(label, fn):
    try:
        fn()
    except (ValueError, TypeError):
        results.append(dict(control=label, result='REFUSED'))
    else:
        raise AssertionError(label + ': expected refusal')


for manifest, revision in ((F, 'v2'), (F, 'v2.1'), (E, 'v2.1')):
    assert context(manifest, revision).manifest == manifest
    results.append(dict(control=manifest['profile'] + '/' + revision, result='VALID_CARRIER_ACCEPTED'))
refuses('successor E cannot select v2', lambda: context(E, 'v2'))
refuses('revision must be explicit', lambda: adapter.Context(manifest=E, handlers={}))
refuses('unsupported revision', lambda: context(F, 'v2.2'))

incomplete = copy.deepcopy(E)
del incomplete['sources']['src/interfaces/IPolicyVersion.sol']
refuses('successor source inventory omission', lambda: context(incomplete))
extra = copy.deepcopy(E)
extra['extra'] = 'not in the carrier'
refuses('closed carrier', lambda: context(extra))
missing = copy.deepcopy(SCHEMA)
del missing['$defs']['LedgerDeploymentEComplete']
refuses('selected revision must have all carrier branches', lambda: context(F, schema=missing))

ctx = context(E)
for label, alter in (
    ('rpc origin', lambda m: m['chains']['pbc'].__setitem__('rpcUrl', 'http://127.0.0.1:1')),
    ('source pin', lambda m: m['sources'].__setitem__('src/interfaces/IPolicyVersion.sol', '0' * 64)),
    ('creation time', lambda m: m.__setitem__('createdAt', '2026-11-07T00:00:00Z')),
):
    changed = copy.deepcopy(E)
    alter(changed)
    line = dict(schemaVersion='v2', operation='collect_checkpoint', input={}, deploymentManifest=changed)
    response = adapter.handle_line(json.dumps(line), ctx)
    assert response['ok'] is False and response['error']['code'] == 'WRONG_DESTINATION', (label, response)
    results.append(dict(control='whole manifest: ' + label, result='WRONG_DESTINATION'))

line = dict(schemaVersion='v2', operation='collect_checkpoint', input={}, deploymentManifest=E)
assert adapter.handle_line(json.dumps(line), ctx)['result'] == {'probe': True}
results.append(dict(control='matching manifest reaches injected handler', result='ACCEPTED'))
line['operation'] = 'rotate_epoch'
line['input'] = {'targetEpoch': '1'}
assert adapter.handle_line(json.dumps(line), ctx)['error']['code'] == 'NOT_IMPLEMENTED_IN_PHASE'
results.append(dict(control='G remains refused', result='NOT_IMPLEMENTED_IN_PHASE'))

# Positive omission controls: these are LIMITS, not proof of strict validation.
assert context(incomplete, schema=None).manifest == incomplete
results.append(dict(control='schema=None accepts incomplete successor inventory', result='LIMIT_CONFIRMED'))
results.append(dict(control='handler dict output not schema-validated by frontend', result='LIMIT_CONFIRMED'))
print(json.dumps(dict(classification='synthetic reconstruction/extension review', controls=results,
    limits='No chain/state/sign-time, runtime wiring, persistence or end-to-end result. Supplied schema and output-validating handlers remain recipe obligations.'), indent=2))
