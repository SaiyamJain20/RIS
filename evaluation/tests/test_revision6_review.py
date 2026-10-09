"""E0 review definitions only; these checks execute no peer or service code."""
import copy
import json
from pathlib import Path

import pytest
from jsonschema import ValidationError
from evaluation.schema import validate


@pytest.mark.parametrize('action', ['REQUEST_SAME_NONCE_DISTINCT_DIGEST', 'FORWARD_BOTH_REQUESTS',
    'CERTIFY_BOTH_BEFORE_CONSUMPTION', 'CONSUME_FIRST', 'CONSUME_PRECOLLECTED_SECOND', 'ATTEST_GRANT'])
def test_supplement_steps_accept_only_closed_test_directives(action):
    step = {'action': action, 'offsetSeconds': '0'}
    validate('E0CaseStep', step)
    with pytest.raises(ValidationError):
        validate('E0CaseStep', {**step, 'witnessKey': 'forbidden'})


@pytest.mark.parametrize('action', ['RESIGN_RECEIPT_FIELD', 'ALTER_RECEIPT_KEEP_SIGNATURE'])
@pytest.mark.parametrize('field', ['requestDigest', 'gid', 'dataId'])
def test_receipt_control_requires_one_of_the_three_bound_fields(action, field):
    step = {'action': action, 'offsetSeconds': '0', 'receiptField': field}
    validate('E0CaseStep', step)
    for bad in ({'action': action, 'offsetSeconds': '0'}, {**step, 'receiptField': 'grantId'},
                {**step, 'action': 'REPORT_OUTCOME'}, {**step, 'signingKeyRef': 'witness-1'}):
        with pytest.raises(ValidationError):
            validate('E0CaseStep', bad)


def test_supplement_catalog_is_unexecuted_and_isolates_nonce_and_receipt_controls():
    path = Path('evaluation/scenarios/e0_supplement_cases.json')
    assert path.is_file(), 'the accepted supplement needs concrete review fixtures'
    cases = json.loads(path.read_text())['cases']
    assert len({c['id'] for c in cases}) == len(cases) == 8
    nonce = next(c for c in cases if c['caseFamily'] == 'E01')
    assert [s['action'] for s in nonce['steps']] == ['REQUEST_ACCESS', 'REQUEST_SAME_NONCE_DISTINCT_DIGEST',
        'FORWARD_BOTH_REQUESTS', 'ACCEPT_CHECKPOINT', 'CERTIFY_BOTH_BEFORE_CONSUMPTION',
        'CONSUME_FIRST', 'CONSUME_PRECOLLECTED_SECOND']
    assert nonce['expected']['error'] == 'REPLAY'
    for case in cases:
        validate('E0CaseFixture', case)
        assert case['executionStatus'] == 'NOT_RUN'
        bad = copy.deepcopy(case); bad['executionStatus'] = 'PASS'
        with pytest.raises(ValidationError): validate('E0CaseFixture', bad)
    for action, error in [('RESIGN_RECEIPT_FIELD', 'WRONG_SUBJECT'),
                          ('ALTER_RECEIPT_KEEP_SIGNATURE', 'WRONG_SUBJECT')]:
        trials = [c for c in cases if any(s['action'] == action for s in c['steps'])]
        assert {next(s['receiptField'] for s in c['steps'] if s['action'] == action) for c in trials} == {'requestDigest','gid','dataId'}
        assert all(c['expected']['error'] == error and c['expected']['outcome'] == 'NO_NEW_OUTCOME' for c in trials)
    positive = next(c for c in cases if c['variant'] == 'receipt-binding-positive')
    assert positive['expected']['outcome'] == 'ACCEPT' and positive['expected']['error'] is None
