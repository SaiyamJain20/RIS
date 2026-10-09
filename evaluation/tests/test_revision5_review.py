"""Regressions for peer-reviewed E0 gaps; no service execution is implied."""
import copy
import json
from pathlib import Path

import pytest
from eth_abi import encode
from eth_utils import keccak
from jsonschema import ValidationError

from evaluation.schema import validate, validate_response


VECTORS = json.loads(Path('interfaces/vectors/eip712-agent1-candidate.json').read_text())['vectors']
DEPLOYMENT = json.loads(Path('interfaces/vectors/adapter-agent2-candidate.json').read_text())['examples']['prepare_request']['cases'][0]['request']['deploymentManifest']
HASH = '0x' + '11' * 32


def catalog():
    return json.loads(Path('evaluation/scenarios/e0_cases.json').read_text())['cases']


def test_primary_policy_fixture_commits_to_registered_data_p1_policy():
    from interfaces.proposals.build_boundary_vectors import build
    policy = next(c['input']['policy'] for c in build()['cases'] if c['schema'] == 'EncryptRecordInput' and c['valid'])
    clauses = [[(bytes.fromhex(r['role'][2:]), int(r['kind']), int(r['issuerMode'])) for r in clause] for clause in policy['clauses']]
    digest = '0x' + keccak(encode(['(bytes32,uint8,uint8)[][]'], [clauses])).hex()
    # Independent cast result published in A1-0013, also reproduced in A2-0006.
    assert digest == '0x4bd063e1a4c348bf656f983104839fec2594aaee710b4627e9e46368ba1abc3a'


def test_record_fixture_uses_registered_p1_owner_and_data_identifier():
    from interfaces.proposals.build_boundary_vectors import build
    record = next(c['input']['record'] for c in build()['cases'] if c['schema'] == 'EncryptRecordInput' and c['valid'])
    assert record['owner'] == '0x6ea73ebda053f804cad188496ec48af56b06f698'
    assert record['dataId'] == '0x53ff15331656b9b303d95970634a992ed32268c5d9723c90ddc94ceeb397061e'


@pytest.mark.parametrize('operation,name,typed,field', [
    ('collect_checkpoint', 'CollectCheckpoint', 'StateCheckpoint', 'checkpoint'),
    ('attest_grant', 'AttestGrant', 'GrantReceipt', 'receipt'),
])
def test_witness_artifacts_have_closed_operation_bound_requests_and_results(operation, name, typed, field):
    vector = next(v for v in VECTORS if v['name'] == typed)
    inp = {'witnessSetVersion': '1'} if operation == 'collect_checkpoint' else {'grantId': HASH}
    request = {'schemaVersion': 'v1', 'operation': operation, 'input': inp, 'deploymentManifest': DEPLOYMENT}
    result = {'schemaVersion': 'v1', 'adapterMode': 'symbolic', field: vector['typedData']['message'], 'signatures': [vector['signature']]}
    response = {'schemaVersion': 'v1', 'ok': True, 'result': result, 'error': None}
    validate('AdapterRequest', request)
    validate(name + 'Input', inp)
    validate(name + 'Result', result)
    validate_response(operation, response)
    for bad in ({**inp, 'witnessKey': HASH}, {**inp, 'sequence': '10'}):
        with pytest.raises((ValueError, ValidationError)):
            validate('AdapterRequest', {**request, 'input': bad})
    for signatures in ([], [vector['signature'], vector['signature']]):
        with pytest.raises((ValueError, ValidationError)):
            validate_response(operation, {**response, 'result': {**result, 'signatures': signatures}})
    with pytest.raises((ValueError, ValidationError)):
        validate_response('attest_grant' if operation == 'collect_checkpoint' else 'collect_checkpoint', response)


def test_checkpoint_witness_set_is_optional_but_e_only():
    validate('CollectCheckpointInput', {})
    for value in ('2', 1, '1\n'):
        with pytest.raises((ValueError, ValidationError)):
            validate('CollectCheckpointInput', {'witnessSetVersion': value})


@pytest.mark.parametrize('point', ['after-intent', 'after-send'])
def test_crash_schedule_names_closed_release_hook(point):
    step = {'action': 'CRASH_RESTART', 'offsetSeconds': '0', 'workerHook': 'release', 'crashPoint': point}
    validate('E0CaseStep', step)
    for field in ('workerHook', 'crashPoint'):
        bad = copy.deepcopy(step); del bad[field]
        with pytest.raises((ValueError, ValidationError)):
            validate('E0CaseStep', bad)
    for bad in ({**step, 'crashPoint': 'arbitrary-code'}, {**step, 'workerHook': 'shell'}, {**step, 'action': 'RELEASE'}):
        with pytest.raises((ValueError, ValidationError)):
            validate('E0CaseStep', bad)


def test_subject_substitution_preserves_original_certificate_error_class():
    case = next(c for c in catalog() if c['id'] == 'E01-subject-substitution-repaired-e')
    assert case['expected']['error'] == 'WRONG_SUBJECT'


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal', 'repaired-e'])
def test_crash_expectations_distinguish_intent_from_delivery_attempts(profile):
    for point, sends in [('after-intent', '1'), ('after-send', '2')]:
        case = next(c for c in catalog() if c['id'] == f'E03-crash-{point}-{profile}')
        crash = next(s for s in case['steps'] if s['action'] == 'CRASH_RESTART')
        assert crash['crashPoint'] == point
        assert crash['workerHook'] == 'release'
        worker = case['expected']['worker']
        assert worker == {'releaseIntentCount': '1', 'releaseSentCount': sends, 'sameCachedResponse': True,
                          'delivery': 'unknown', 'expiredRetryError': 'EXPIRED'}
        validate('E0CaseFixture', case)
        bad = copy.deepcopy(case); bad['expected']['worker']['extra'] = True
        with pytest.raises((ValueError, ValidationError)):
            validate('E0CaseFixture', bad)


def test_paper_revocation_case_does_not_submit_unavailable_checkpoint():
    for case in catalog():
        if case['variant'] == 'post-barrier-revocation' and case['profile'].startswith('paper-'):
            assert all(step['action'] != 'ACCEPT_CHECKPOINT' for step in case['steps'])


def test_repaired_issuer_scope_is_preserved_baseline_behavior():
    case = next(c for c in catalog() if c['id'] == 'E02-wrong-issuer-repaired-e')
    assert case['expected']['classification'] == 'SUPPORTED'


@pytest.mark.parametrize('variant,error', [('forged-tuple', 'BAD_SIGNATURE'),
                                         ('wrong-destination', 'WRONG_DESTINATION'),
                                         ('new-reference-replay', 'REPLAY')])
def test_missing_provenance_controls_have_repaired_oracle_counterparts(variant, error):
    cases = [c for c in catalog() if c['caseFamily'] == 'E01' and c['variant'] == variant]
    assert {c['profile'] for c in cases} == {'paper-strict', 'paper-minimal', 'repaired-e'}
    repaired = next(c for c in cases if c['profile'] == 'repaired-e')
    assert repaired['expected']['error'] == error
    for case in cases:
        validate('E0CaseFixture', case)
        assert case['executionStatus'] == 'NOT_RUN'
