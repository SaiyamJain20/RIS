"""Deterministic schema fixtures, explicitly separate from executed service results."""
import argparse
import copy
import json
from pathlib import Path

from eth_utils import keccak

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'interfaces/vectors/boundary-candidate.json'


def build():
    peer = json.loads((ROOT / 'interfaces/vectors/adapter-agent2-candidate.json').read_text())
    vectors = json.loads((ROOT / 'interfaces/vectors/eip712-agent1-candidate.json').read_text())['vectors']
    example = peer['examples']['prepare_request']['cases'][0]
    prepared = example['response']['result']
    deployment = example['request']['deploymentManifest']
    signed = next(v for v in vectors if v['name'] == 'AccessDecision')
    records = next(v['records'] for v in vectors if 'records' in v)
    h = lambda label: '0x' + keccak(text=label).hex()
    data_id = prepared['request']['dataId']
    policy = {'clauses': [[{'role': h('Doctor'), 'kind': '1', 'issuerMode': '0'},
                           {'role': h('OnDuty'), 'kind': '2', 'issuerMode': '2'}]]}
    record = {'dataId': data_id, 'owner': deployment['fixture']['authorities'][0]['root'],
              'payloadDigest': h('TEST-ONLY synthetic record')}
    release = {'schemaVersion': 'v1', 'adapterMode': 'symbolic', 'requestDigest': prepared['requestDigest'],
               'grantId': h('constructed grant'), 'dataId': data_id, 'keyEpoch': '0',
               'ciphertextDigest': h('constructed symbolic ciphertext commitment'),
               'recipientKeyHash': prepared['request']['recipientKeyHash'],
               'responseEnvelope': {'kind': 'symbolic-partial/v1', 'token': h('constructed public token')}}
    inputs = {
        'PrepareRequest': example['request']['input'],
        'CollectDecision': {'requestDigest': prepared['requestDigest'], 'witnessSetVersion': '1'},
        'Release': {'grantId': release['grantId']},
        'EncryptRecord': {'record': record, 'policy': policy, 'keyEpoch': '0'},
        'FinishDecryption': {'response': release, 'userKeyRef': 'keyref:user:alice'},
        'RotateEpoch': {'targetEpoch': '1'},
    }
    results = {
        'PrepareRequest': prepared,
        'CollectDecision': {'schemaVersion': 'v1', 'adapterMode': 'symbolic',
                            'decision': signed['typedData']['message'], 'signatures': [signed['signature']],
                            'credentialRecords': records},
        'Release': release,
        'EncryptRecord': {'schemaVersion': 'v1', 'adapterMode': 'symbolic', 'dataId': data_id, 'keyEpoch': '0',
                          'ciphertextDigest': release['ciphertextDigest'], 'policyDigest': h('constructed policy')},
        'FinishDecryption': {'schemaVersion': 'v1', 'adapterMode': 'symbolic', 'decryptable': True,
                             'dataId': data_id, 'ciphertextDigest': release['ciphertextDigest']},
    }
    operations = ('prepare_request', 'collect_decision', 'release', 'encrypt_record', 'finish_decryption', 'rotate_epoch')
    cases = []
    def case(name, value, valid, label, provenance='constructed schema fixture; NOT EXECUTED'):
        cases.append({'schema': name, 'valid': valid, 'label': label, 'provenance': provenance, 'input': copy.deepcopy(value)})
    def closed(name, value, provenance='constructed schema fixture; NOT EXECUTED'):
        case(name, value, True, 'positive', provenance)
        case(name, {**value, 'privateKey': 'forbidden'}, False, 'unknown secret field')
        for field in value:
            bad = copy.deepcopy(value); del bad[field]
            if name == 'CollectDecisionInput' and field == 'witnessSetVersion':
                case(name, bad, True, 'optional E witness set omitted')
            else:
                case(name, bad, False, 'missing ' + field)
    for operation, (name, inp) in zip(operations, inputs.items()):
        closed(name + 'Input', inp)
        request = {'schemaVersion': 'v1', 'operation': operation, 'input': inp, 'deploymentManifest': deployment}
        closed(name + 'Request', request)
        case('AdapterRequest', request, True, operation)
        case('AdapterRequest', {**request, 'input': {}}, False, operation + ': empty input')
        error = {'schemaVersion': 'v1', 'ok': False, 'result': None,
                 'error': {'code': 'NOT_IMPLEMENTED_IN_PHASE' if name == 'RotateEpoch' else 'ADAPTER_UNAVAILABLE',
                           'message': 'schema fixture, no service execution'}}
        case(name + 'Response', error, True, 'unavailable/unsupported envelope')
        if name in results:
            provenance = 'A2-0003 generated prepare_request' if name == 'PrepareRequest' else 'constructed schema fixture; NOT EXECUTED'
            closed(name + 'Result', results[name], provenance)
            response = {'schemaVersion': 'v1', 'ok': True, 'result': results[name], 'error': None}
            closed(name + 'Response', response, provenance)
            case('AdapterResponse', response, True, operation + ' success SHAPE only', provenance)
        else:
            case(name + 'Response', example['response'], False, 'rotation cannot succeed in E')
    for name, value in [('SymbolicRecord', record), ('SymbolicPolicy', policy), ('SymbolicEnvelope', release['responseEnvelope'])]:
        closed(name, value)
    case('AdapterResponse', {'schemaVersion': 'v1', 'ok': True, 'result': {}, 'error': None}, False, 'opaque result')
    bad = copy.deepcopy(policy); bad['clauses'][0][0]['issuerMode'] = '2'
    case('SymbolicPolicy', bad, False, 'unanchored SAME_AS_FIRST')
    bad = copy.deepcopy(results['CollectDecision']); bad['credentialRecords'].reverse()
    case('CollectDecisionResult', bad, False, 'nested credential order')
    for handle in ('keyref:user:alice', 'keyref:user:0', 'keyref:user:' + 'a' * 64):
        case('UserKeyRef', handle, True, 'valid handle')
    for handle in ('keyref:user:', 'keyref:user:Alice', 'keyref:user:-alice', 'keyref:user:alice\n',
                   'keyref:worker:alice', 'keyref:user:' + 'a' * 65, '0x' + '11' * 32):
        case('UserKeyRef', handle, False, 'invalid handle or raw secret')
    scenarios = json.loads((ROOT / 'evaluation/scenarios/e_positive.json').read_text())
    for scenario in scenarios:
        events = []
        for i, event_name in enumerate(scenario['expectedEvents']):
            event = {'type': event_name, 'requestDigest': scenario['fixture']['requestDigest'], 'timestamp': str(100 + i)}
            fields = ['grantId', 'gid', 'dataId'] if event_name in ('DBC_AUTHORIZED', 'RELEASE_INTENT', 'RELEASE_SENT', 'OUTCOME_RECORDED') else []
            if event_name == 'DBC_AUTHORIZED': fields += ['kssc', 'destinationChainId', 'recipientKeyHash', 'keyEpoch']
            event.update({field: scenario['fixture'][field] for field in fields})
            events.append(event)
            closed('ObservedEvent', event)
        result = {'scenarioId': scenario['id'], 'classification': scenario['expectedClass'], 'observedEvents': events,
                  'assertions': [{'name': 'constructed example only', 'passed': True}], 'latencyMs': None,
                  'gasUsed': None, 'encodedBytes': None, 'limitations': ['Constructed schema fixture; NOT RUN.'],
                  'evidencePaths': ['fixture.json']}
        closed('ScenarioResult', result)
    blocked = {**result, 'classification': 'BLOCKED', 'observedEvents': [], 'assertions': [], 'evidencePaths': []}
    case('ScenarioResult', blocked, True, 'unexecuted blocked trial')
    return {'interfaceVersion': 'candidate v1 revision 4 NOT frozen',
            'scope': 'Schema positive/negative examples. Constructed results are not executable provider evidence or a gate.',
            'cases': cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--check', action='store_true')
    args = parser.parse_args(); document = build(); rendered = json.dumps(document, indent=2, allow_nan=False) + '\n'
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != rendered: raise SystemExit('Boundary fixtures differ from deterministic generator')
    else: OUTPUT.write_text(rendered)
    print(f"{len(document['cases'])} boundary cases {'match' if args.check else 'generated'}")


if __name__ == '__main__': main()
