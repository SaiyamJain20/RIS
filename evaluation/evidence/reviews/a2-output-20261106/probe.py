"""Independent public-boundary controls. Shape acceptance is not ledger truth."""
import copy
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT = Path(__file__).resolve().parents[4]
SNAPSHOT = ROOT / 'evaluation/runs/a2-output-20261106/snapshot'
sys.path[:0] = [str(SNAPSHOT / 'protocol'), str(ROOT)]
from hmbc_protocol import adapter_v2 as adapter
from evaluation import schema_v2 as evaluator

SCHEMA = json.loads((ROOT / 'interfaces/v2.1/hmbc.schema.json').read_text())
MANIFEST = json.loads((SNAPSHOT / 'protocol/tests/fixtures/agent1-85c59f5-f-base-deployment.json').read_text())
VECTOR = next(v for v in json.loads((ROOT / 'interfaces/v2/vectors/signing.json').read_text())['vectors']
              if v['name'] == 'StateCheckpoint')
VALID = dict(schemaVersion='v2', adapterMode='symbolic', checkpoint=VECTOR['typedData']['message'],
             signatures=[VECTOR['signatures'][0]['signature']])
N = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141
rows = []


def note(label, result):
    rows.append(dict(control=label, result=result))


def run(result, *, schema=SCHEMA, enabled=True, operation='collect_checkpoint'):
    ctx = adapter.Context(manifest=MANIFEST, schema_revision='v2.1', schema=schema,
                          check_responses=enabled, handlers={operation: lambda i, c: copy.deepcopy(result)})
    inp = {} if operation == 'collect_checkpoint' else {'grantId': '0x' + 'ab' * 32}
    line = json.dumps(dict(schemaVersion='v2', operation=operation, input=inp, deploymentManifest=MANIFEST))
    return adapter.handle_line(line, ctx)


def generic(response):
    assert response == dict(schemaVersion='v2', ok=False, result=None,
                            error=dict(code='ADAPTER_UNAVAILABLE', message='internal adapter failure')), response


assert run(VALID)['result'] == VALID
evaluator.validate('CollectCheckpointResponse', run(VALID))
note('published-vector shape preserved and independently validated', 'PASS')

bad_cases = []
for label, change in (
    ('extra result field', lambda r: r.update(secret='must not escape')),
    ('missing signature', lambda r: r.pop('signatures')),
    ('uint64 overflow', lambda r: r['checkpoint'].update(sequence=str(2**64))),
    ('noncanonical uint64', lambda r: r['checkpoint'].update(sequence='05')),
    ('wrong result version', lambda r: r.update(schemaVersion='v1')),
):
    bad = copy.deepcopy(VALID)
    change(bad)
    bad_cases.append((label, bad))
sig = VALID['signatures'][0]
high = '0x%064x%064x%02x' % (int(sig[2:66], 16), N-int(sig[66:130], 16),
                            27 + (1-(int(sig[130:], 16)-27)))
bad = copy.deepcopy(VALID)
bad['signatures'] = [high]
bad_cases.append(('high-s signature', bad))

for label, bad in bad_cases:
    generic(run(bad))
    assert run(bad, schema=None)['result'] == bad
    assert run(bad, enabled=False)['result'] == bad
    note(label, 'GENERIC_REFUSAL; BOTH_OPT_OUT_LIMITS_CONFIRMED')
generic(run(VALID, operation='release'))
note('checkpoint result cannot serve release', 'GENERIC_REFUSAL')

# The two producer/evaluator implementations register formats independently.
for bits in (8, 32, 64, 256):
    name = f'Uint{bits}'
    doc = {'$ref': '#/$defs/' + name, '$defs': SCHEMA['$defs']}
    bare = Draft202012Validator(doc, format_checker=FormatChecker())
    checked = Draft202012Validator(doc, format_checker=adapter.published_format_checker())
    maximum, overflow = str(2**bits-1), str(2**bits)
    assert checked.is_valid(maximum) and not checked.is_valid(overflow)
    evaluator.validate(name, maximum)
    try:
        evaluator.validate(name, overflow)
    except (ValueError, ValidationError):
        pass
    else:
        raise AssertionError('evaluator admitted overflow: ' + name)
    note(name, dict(maximumAccepted=True, overflowRefusedByBoth=True,
                    bareLibraryAdmitsOverflow=bare.is_valid(overflow)))

for label, signature in [('valid', sig), ('high-s', high), ('zero-r', '0x'+'00'*32+sig[66:])]:
    expected = label == 'valid'
    assert adapter.published_format_checker().conforms(signature, 'canonical-signature') == expected
    assert evaluator.FORMATS.conforms(signature, 'canonical-signature') == expected
    note('signature format: ' + label, 'PASS')

for name in ('AdapterResponse', 'ReleaseResponse', 'CollectCheckpointResponse', 'RotateEpochResponse'):
    broken = copy.deepcopy(SCHEMA)
    del broken['$defs'][name]
    try:
        run(VALID, schema=broken)
    except ValueError:
        note('missing response definition: ' + name, 'CONSTRUCTION_REFUSED')
    else:
        raise AssertionError('missing response definition accepted: ' + name)

for fmt, value in [('user-key-ref', '../not-a-key'), ('evidence-path', '/outside/evidence')]:
    assert adapter.published_format_checker().conforms(value, fmt)
    assert not evaluator.FORMATS.conforms(value, fmt)
    note(fmt, 'PRODUCER_ANNOTATION_LIMIT; EVALUATOR_REFUSES')

print(json.dumps(dict(classification='synthetic reconstruction/extension review', controls=rows,
                     count=len(rows), limits='Injected shape controls; no native truth, signature recovery, source-state, process or integrated result.'), indent=2))
