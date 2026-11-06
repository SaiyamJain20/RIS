"""Deliberately bypass joins in memory only; original source bytes stay fixed."""
import copy
import importlib
import json
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from evaluation.tests.test_signing_context_v2 import case, message, sign, response_for
from evaluation.binding_context_v2 import reconstruct

real = importlib.import_module('evaluation.signing_context_v2')
source = (ROOT / 'evaluation/signing_context_v2.py').read_text()
manifest, observations, _ = case()
controls = []


def mutate(old, new):
    assert source.count(old) == 1, old
    module = types.ModuleType('deliberate_context_mutant')
    exec(compile(source.replace(old, new), '<deliberate-context-mutant>', 'exec'), module.__dict__)
    return module


def control(name, module, run):
    try:
        run(real)
    except ValueError as error:
        refusal = str(error)
    else:
        raise AssertionError('original admitted bad input: ' + name)
    result = run(module)
    controls.append({'name': name, 'originalRefusal': refusal, 'mutantAccepted': result})


def certificate(module, kind, value, signatures=None, observed=None):
    return module.verify_bound_certificate(kind, value,
        sign(manifest, kind, value)[:3] if signatures is None else signatures,
        manifest=manifest, observations=observations if observed is None else observed,
        compiled_max_admins='8')


for kind, field in [('StateCheckpoint', 'psc'), ('GrantReceipt', 'kssc')]:
    value = message(manifest, kind)
    value[field] = '0x' + '99' * 20
    module = mutate('    _embedded_identity(name, message, document)', '    pass # deliberate missing embedded identity')
    control(kind + ' embedded identity', module, lambda m: certificate(m, kind, value))

value = message(manifest, 'AccessDecision')
module = mutate("'required_signatures': int(group['threshold'])", "'required_signatures': 2")
signatures = sign(manifest, 'AccessDecision', value)[:2]
control('q3 cannot become q2', module, lambda m: certificate(m, 'AccessDecision', value, signatures))

module = mutate("'chain_id': destination['chainId']", "'chain_id': '999'")
signatures = sign(manifest, 'AccessDecision', value, changed_domain={'chainId': '999'})[:3]
control('domain chain derived from deployment', module, lambda m: certificate(m, 'AccessDecision', value, signatures))

module = mutate('    document = reconstruct(manifest, observations, compiled_max_admins=compiled_max_admins)',
                '    document = PINNED_GOOD_DOCUMENT # deliberate skipped observations')
module.PINNED_GOOD_DOCUMENT = reconstruct(manifest, observations, compiled_max_admins='8')
bad = copy.deepcopy(observations)
bad['pbc']['confirmedAnchor']['hash'] = '0x' + '99' * 32
control('revalidate acquired observations', module, lambda m: certificate(m, 'AccessDecision', value, observed=bad))

response = response_for(manifest, 6, wrong_source=True)
module = mutate("        _embedded_identity('StateCheckpoint', report['message'], document)",
                '        pass # deliberate skipped report source')
def reports(m):
    return m.verify_bound_checkpoint_reports(response, manifest=manifest,
        observations=observations, compiled_max_admins='8', selected_index='0')
control('retry report embedded identity', module, reports)

response = response_for(manifest, 6)
response['error']['recorded']['signature'] = sign(manifest, 'StateCheckpoint',
    response['error']['recorded']['message'], signers=[manifest['fixture']['witnessSet']['witnesses'][0]],
    changed_domain={'chainId': '999'})[0]
module = mutate('    return verify_checkpoint_reports(response, selected_index=selected_index, **context)',
                '    return len(declared) # deliberate skipped report crypto')
control('retry report cryptographic check', module, reports)

print(json.dumps({'classification': 'deliberate in-memory mutations; synthetic reconstruction checks',
                  'controls': controls}, indent=2))
