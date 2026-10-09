"""E0 contract tests. Constructed outputs are fixtures, never service evidence."""
import copy
import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from evaluation.schema import validate


HASH = '0x' + '11' * 32
ADDRESS = '0x' + '22' * 20
VECTORS = json.loads(Path('interfaces/vectors/eip712-agent1-candidate.json').read_text())
REQUEST = next(v['typedData']['message'] for v in VECTORS['vectors'] if v['name'] == 'AccessRequest')
SIGNED = next(v for v in VECTORS['vectors'] if v['name'] == 'AccessRequest')
PEER = json.loads(Path('interfaces/vectors/adapter-agent2-candidate.json').read_text())
DEPLOYMENT = PEER['examples']['prepare_request']['cases'][0]['request']['deploymentManifest']


def prepared():
    return {'schemaVersion': 'v1', 'adapterMode': 'symbolic', 'request': copy.deepcopy(REQUEST),
            'requestDigest': SIGNED['digest'], 'signature': SIGNED['signature'], 'signer': SIGNED['signer']}


def record():
    return {'dataId': HASH, 'owner': ADDRESS, 'payloadDigest': HASH}


def policy():
    return {'clauses': [[{'role': HASH, 'kind': '1', 'issuerMode': '0'},
                         {'role': HASH, 'kind': '2', 'issuerMode': '2'}]]}


def released():
    return {'schemaVersion': 'v1', 'adapterMode': 'symbolic', 'requestDigest': HASH,
            'grantId': HASH, 'dataId': HASH, 'keyEpoch': '0', 'ciphertextDigest': HASH,
            'recipientKeyHash': HASH, 'responseEnvelope': {'kind': 'symbolic-partial/v1', 'token': HASH}}


@pytest.mark.parametrize('name,value', [
    ('PrepareRequestInput', {'request': REQUEST, 'signingKeyRef': 'keyref:user:alice'}),
    ('PrepareRequestResult', prepared()),
    ('CollectDecisionInput', {'requestDigest': HASH}),
    ('ReleaseInput', {'grantId': HASH}),
    ('EncryptRecordInput', {'record': record(), 'policy': policy(), 'keyEpoch': '0'}),
    ('FinishDecryptionInput', {'response': released(), 'userKeyRef': 'keyref:user:alice'}),
    ('RotateEpochInput', {'targetEpoch': '1'}),
    ('ReleaseResult', released()),
])
def test_operation_positive_wire_shapes(name, value):
    validate(name, value)


@pytest.mark.parametrize('handle', ['keyref:worker:alice', 'keyref:user:-alice',
                                    'keyref:user:Alice', 'keyref:user:alice\n',
                                    'keyref:user:' + 'a' * 65, '0x' + '11' * 32])
def test_user_key_handles_reject_secret_or_wrong_role(handle):
    with pytest.raises((ValueError, ValidationError)):
        validate('PrepareRequestInput', {'request': REQUEST, 'signingKeyRef': handle})


def test_success_envelope_rejects_opaque_or_extra_result_fields():
    response = {'schemaVersion': 'v1', 'ok': True, 'result': prepared(), 'error': None}
    validate('AdapterResponse', response)
    for result in ({}, {**prepared(), 'privateKey': 'secret'}):
        with pytest.raises((ValueError, ValidationError)):
            validate('AdapterResponse', {**response, 'result': result})


def test_symbolic_layouts_are_closed_and_require_nonempty_policy():
    validate('SymbolicRecord', record())
    validate('SymbolicPolicy', policy())
    for name, bad in [('SymbolicRecord', {**record(), 'plaintext': 'patient data'}),
                      ('SymbolicPolicy', {'clauses': []}),
                      ('SymbolicPolicy', {'clauses': [[]]}),
                      ('SymbolicEnvelope', {'kind': 'abe-real', 'token': HASH}),
                      ('SymbolicEnvelope', {'kind': 'symbolic-partial/v1', 'token': HASH, 'temporalKey': HASH})]:
        with pytest.raises((ValueError, ValidationError)):
            validate(name, bad)


def test_policy_cannot_use_unanchored_same_as_first():
    bad = policy(); bad['clauses'][0][0]['issuerMode'] = '2'
    with pytest.raises(ValueError, match='first'):
        validate('SymbolicPolicy', bad)


def scenario_result():
    return {'scenarioId': 'E-control-alice', 'classification': 'REPAIR_SUPPORTED',
            'observedEvents': [{'type': 'REQUEST_LOGGED', 'requestDigest': HASH, 'timestamp': '100'}],
            'assertions': [{'name': 'fixture control', 'passed': True}], 'latencyMs': 1.5,
            'gasUsed': '12345', 'encodedBytes': 400,
            'limitations': ['Constructed schema fixture, not an integrated run.'],
            'evidencePaths': ['fixture.json']}


def test_scenario_result_has_strict_observations_measurements_and_evidence():
    validate('ScenarioResult', scenario_result())
    for field, value in [('encodedBytes', -1), ('latencyMs', float('nan')),
                         ('gasUsed', 12345), ('evidencePaths', ['../secret']),
                         ('observedEvents', [{'type': 'GRANT', 'requestDigest': HASH, 'timestamp': '100'}])]:
        bad = scenario_result(); bad[field] = value
        with pytest.raises((ValueError, ValidationError)):
            validate('ScenarioResult', bad)


def test_scenario_success_cannot_contain_failed_assertions_or_no_evidence():
    for field, value in [('assertions', [{'name': 'broken binding', 'passed': False}]),
                         ('assertions', []), ('evidencePaths', [])]:
        bad = scenario_result(); bad[field] = value
        with pytest.raises((ValueError, ValidationError)):
            validate('ScenarioResult', bad)


def test_request_line_parser_rejects_duplicate_keys_and_nonfinite_json():
    from evaluation.schema import validate_json_line
    for line in ['{"schemaVersion":"v1","schemaVersion":"v1"}',
                 '{"latencyMs":NaN}', '{"latencyMs":Infinity}', 'x' * (1048576 + 1)]:
        with pytest.raises(ValueError):
            validate_json_line('AdapterRequest', line)


def test_operation_response_cannot_substitute_another_result_or_rotate_success():
    from evaluation.schema import validate_response
    response = {'schemaVersion': 'v1', 'ok': True, 'result': prepared(), 'error': None}
    validate_response('prepare_request', response)
    for op in ['release', 'rotate_epoch']:
        with pytest.raises((ValueError, ValidationError)):
            validate_response(op, response)
    with pytest.raises(ValueError):
        validate_response('arbitrary-command', response)


@pytest.mark.parametrize('operation,input', [
    ('prepare_request', {'request': REQUEST, 'signingKeyRef': 'keyref:user:alice'}),
    ('collect_decision', {'requestDigest': HASH, 'witnessSetVersion': '1'}),
    ('release', {'grantId': HASH}),
    ('encrypt_record', {'record': record(), 'policy': policy(), 'keyEpoch': '0'}),
    ('finish_decryption', {'response': released(), 'userKeyRef': 'keyref:user:alice'}),
    ('rotate_epoch', {'targetEpoch': '1'}),
])
def test_envelope_associates_operation_with_closed_input(operation, input):
    from evaluation.schema import validate_json_line
    envelope = {'schemaVersion': 'v1', 'operation': operation, 'input': input, 'deploymentManifest': DEPLOYMENT}
    validate('AdapterRequest', envelope)
    assert validate_json_line('AdapterRequest', json.dumps(envelope)) == envelope
    for bad in [{**envelope, 'command': ['sh']}, {**envelope, 'operation': 'execute'},
                {**envelope, 'input': {**input, 'privateKey': 'secret'}},
                {**envelope, 'deploymentManifest': {**DEPLOYMENT, 'privateKey': 'secret'}}]:
        with pytest.raises((ValueError, ValidationError)):
            validate('AdapterRequest', bad)


def test_nested_collected_records_validate_order_through_result_and_envelope():
    from evaluation.schema import validate_response
    signed = next(v for v in VECTORS['vectors'] if v['name'] == 'AccessDecision')
    records = next(v['records'] for v in VECTORS['vectors'] if 'records' in v)
    result = {'schemaVersion': 'v1', 'adapterMode': 'symbolic', 'decision': signed['typedData']['message'],
              'signatures': [signed['signature']], 'credentialRecords': records}
    validate('CollectDecisionResult', result)
    response = {'schemaVersion': 'v1', 'ok': True, 'result': result, 'error': None}
    validate_response('collect_decision', response)
    bad = copy.deepcopy(response); bad['result']['credentialRecords'].reverse()
    for name, value in [('CollectDecisionResult', bad['result']), ('AdapterResponse', bad),
                        ('CollectDecisionResponse', bad)]:
        with pytest.raises(ValueError, match='order'):
            validate(name, value)


def test_peer_generated_prepare_result_matches_independent_eip712_recovery():
    from eth_account import Account
    from eth_account.messages import encode_typed_data
    from eth_utils import keccak
    cases = PEER['examples']['prepare_request']['cases']
    for i, case in enumerate(cases):
        validate('AdapterResponse', case['response'])
        if i == 3:  # JSON-number nonce is an owner-executed negative wire example.
            with pytest.raises((ValueError, ValidationError)):
                validate('AdapterRequest', case['request'])
        else:
            validate('AdapterRequest', case['request'])
    result = cases[0]['response']['result']; req = result['request']
    typed = {'types': SIGNED['typedData']['types'], 'primaryType': 'AccessRequest', 'message': req,
             'domain': {'name': 'HMBCRequest', 'version': '1', 'chainId': req['sourceChainId'],
                        'verifyingContract': req['psc']}}
    message = encode_typed_data(full_message=typed)
    assert '0x' + keccak(b'\x19' + message.version + message.header + message.body).hex() == result['requestDigest']
    assert Account.recover_message(message, signature=result['signature']).lower() == result['signer'] == req['gid']


@pytest.mark.parametrize('name', ['ReleaseResult', 'EncryptRecordResult', 'FinishDecryptionResult'])
def test_symbolic_result_cannot_claim_real_abe_mode(name):
    results = {'ReleaseResult': released(),
               'EncryptRecordResult': {'schemaVersion': 'v1', 'adapterMode': 'symbolic', 'dataId': HASH,
                                       'keyEpoch': '0', 'ciphertextDigest': HASH, 'policyDigest': HASH},
               'FinishDecryptionResult': {'schemaVersion': 'v1', 'adapterMode': 'symbolic', 'decryptable': False,
                                          'dataId': HASH, 'ciphertextDigest': HASH}}
    validate(name, results[name])
    results[name]['adapterMode'] = 'abe-real'
    with pytest.raises(ValidationError):
        validate(name, results[name])


def test_e0_case_catalog_distinguishes_expectation_from_execution():
    fixture = {'id': 'E02-rollback-repaired-e', 'caseFamily': 'E02', 'profile': 'repaired-e',
               'sourceRefs': ['HMBC III-C6/V-A4'], 'assumptions': ['A01', 'A02'],
               'baseScenarioId': 'E-control-alice', 'variant': 'signed-list-rollback',
               'steps': [{'action': 'INSTALL_NEW_LIST', 'offsetSeconds': '0'},
                         {'action': 'REPLAY_OLD_LIST', 'offsetSeconds': '1'}],
               'expected': {'property': 'trust-freshness', 'outcome': 'REJECT',
                            'classification': 'REPAIR_SUPPORTED', 'error': 'STALE_ANCHOR',
                            'qualification': 'Prospective expectation; real service execution remains required.'},
               'adapterMode': 'symbolic', 'executionStatus': 'NOT_RUN'}
    validate('E0CaseFixture', fixture)
    for field, value in [('executionStatus', 'PASS'), ('caseFamily', 'F01'), ('unexpected', True)]:
        bad = copy.deepcopy(fixture); bad[field] = value
        with pytest.raises(ValidationError): validate('E0CaseFixture', bad)


def test_all_prospective_cases_bind_existing_controls_and_source_assumptions():
    import csv
    catalog = json.loads(Path('evaluation/scenarios/e0_cases.json').read_text())
    controls = {s['id']: s for s in json.loads(Path('evaluation/scenarios/e_positive.json').read_text())}
    source_ids = {r['id'] for r in csv.DictReader(Path('evaluation/evidence/source-map.csv').open())}
    assumption_ids = {r['id'] for r in csv.DictReader(Path('evaluation/evidence/assumptions.csv').open())}
    assert len({c['id'] for c in catalog['cases']}) == len(catalog['cases']) == 48
    for case in catalog['cases']:
        validate('E0CaseFixture', case)
        assert controls[case['baseScenarioId']]['profile'] == case['profile']
        assert set(case['assumptions']) <= assumption_ids
        assert all(ref in source_ids or ref.startswith('SPEC4/') for ref in case['sourceRefs'])
    for family in ['E01', 'E02', 'E03']:
        assert {c['profile'] for c in catalog['cases'] if c['caseFamily'] == family} == {'paper-strict', 'paper-minimal', 'repaired-e'}


def test_deployment_version_label_allows_explicit_e0_to_v1_migration():
    validate('LedgerDeployment', DEPLOYMENT)
    frozen = copy.deepcopy(DEPLOYMENT); frozen['interfaceVersion'] = 'v1'
    validate('LedgerDeployment', frozen)
    frozen['interfaceVersion'] = 'v2'
    with pytest.raises(ValidationError): validate('LedgerDeployment', frozen)
