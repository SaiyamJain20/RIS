"""Opt-in source-closure migration; synthetic structural evidence only."""
import copy
import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from evaluation import schema_v2 as subject

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / 'interfaces/proposals/v2-e-source-closure'
BAD = (ValueError, ValidationError)


def example():
    return json.loads((PROPOSAL / 'e-complete-example.json').read_text())


def test_complete_carrier_requires_explicit_successor_selection():
    value = example()
    with pytest.raises(BAD):
        subject.validate('LedgerDeployment', value)
    subject.validate('LedgerDeployment', value, schema_revision='v2.1')
    # No implicit global switch after using the successor.
    with pytest.raises(BAD):
        subject.validate('LedgerDeployment', value)


@pytest.mark.parametrize('source', sorted(example()['sources']))
def test_complete_carrier_refuses_each_missing_source(source):
    value = example()
    del value['sources'][source]
    with pytest.raises(BAD):
        subject.validate('LedgerDeployment', value, schema_revision='v2.1')


@pytest.mark.parametrize('change', ['old-marker', 'extra-source', 'bad-hash', 'wire-family', 'profile'])
def test_complete_carrier_refuses_confused_or_malformed_metadata(change):
    value = example()
    if change == 'old-marker':
        value['schemaVersion'] = 'hmbc-ledger-deployment/v2'
    elif change == 'extra-source':
        value['sources']['src/Unreviewed.sol'] = '0' * 64
    elif change == 'bad-hash':
        value['sources']['src/interfaces/IPolicyVersion.sol'] = 'not-a-hash'
    elif change == 'wire-family':
        value['interfaceVersion'] = 'v2.1'
    else:
        value['profileEnum'] = '3'
    with pytest.raises(BAD):
        subject.validate('LedgerDeployment', value, schema_revision='v2.1')


def test_historical_ten_source_carrier_remains_supported():
    value = example()
    value['schemaVersion'] = 'hmbc-ledger-deployment/v2'
    del value['sources']['src/Governance.sol']
    del value['sources']['src/interfaces/IPolicyVersion.sol']
    for revision in ('v2', 'v2.1'):
        subject.validate('LedgerDeployment', value, schema_revision=revision)


@pytest.mark.parametrize('revision', ['../v1', 'v3', '', None, ['v2.1']])
def test_unknown_schema_revision_refuses_without_path_fallback(revision):
    with pytest.raises(ValueError, match='Unknown v2 schema revision'):
        subject.validate('Uint32', '0', schema_revision=revision)


def test_successor_keeps_nested_semantic_checks_and_strict_json():
    value = example()
    entry = value['abi']['TMSC']
    entry['immutableRefsSha256'] = '0' * 64
    with pytest.raises(ValueError, match='immutable object-list hash'):
        subject.validate_json_line('LedgerDeployment', json.dumps(value), schema_revision='v2.1')
    with pytest.raises(ValueError, match='duplicate JSON key'):
        subject.validate_json_line('Uint32', '{"a":1,"a":2}', schema_revision='v2.1')


def test_binding_preimage_and_response_checks_unchanged_with_successor():
    vectors = json.loads((ROOT / 'interfaces/v2/d50-owner-vectors.json').read_text())
    for row in vectors['documents'].values():
        assert subject.binding_hash(row['document'], schema_revision='v2.1') == row['bindingV2']
    response = {'schemaVersion': 'v2', 'ok': False, 'result': None,
                'error': {'code': 'MALFORMED', 'message': 'synthetic'}}
    subject.validate_response('collect_checkpoint', response, schema_revision='v2.1')
    response['error']['code'] = 'NEW_UNAPPROVED_ERROR'
    with pytest.raises(BAD):
        subject.validate_response('collect_checkpoint', response, schema_revision='v2.1')


def test_published_schema_is_exact_acknowledged_patch():
    base = json.loads((ROOT / 'interfaces/v2/hmbc.schema.json').read_text())
    amendment = json.loads((PROPOSAL / 'AMENDMENT.json').read_text())
    expected = copy.deepcopy(base)
    expected['$defs']['LedgerDeploymentEComplete'] = amendment['operations'][0]['value']
    expected['$defs']['LedgerDeployment']['oneOf'].append(amendment['operations'][1]['value'])
    assert json.loads((ROOT / 'interfaces/v2.1/hmbc.schema.json').read_text()) == expected
