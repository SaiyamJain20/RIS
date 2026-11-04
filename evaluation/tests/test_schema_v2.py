"""Synthetic successor boundary checks, independent of either producer module.

Controls catch omitted nested validation, admin sorting, range/hash checks,
profile/set joins, retry partition/selection, and deadline/expiry confusion.
They do not claim chain, storage, timing or signature-recovery observations.
"""
import copy
import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from evaluation import schema_v2 as subject
from evaluation.schema import validate as validate_e

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / 'interfaces/v2'
BAD = (ValueError, ValidationError)


def load(path):
    return json.loads((V2 / path).read_text())


@pytest.mark.parametrize('name,row', list(load('d50-owner-vectors.json')['documents'].items()))
def test_frozen_binding_vectors(name, row):
    assert subject.binding_hash(row['document']) == row['bindingV2']


@pytest.mark.parametrize('name,value', [
    ('Uint32', '4294967295'), ('Uint64', '18446744073709551615'),
    ('Uint256', str(2**256-1)),
])
def test_width_maxima_are_accepted(name, value):
    subject.validate(name, value)


@pytest.mark.parametrize('name,value', [
    ('Uint32', '4294967296'), ('Uint64', '18446744073709551616'),
    ('Uint256', str(2**256)), ('Uint32', '01'), ('Uint64', True),
    ('Uint256', 1), ('Uint32', '-1'),
])
def test_noncanonical_or_overflow_uints_refuse(name, value):
    with pytest.raises(BAD):
        subject.validate(name, value)


def governance():
    return copy.deepcopy(next(v['typedData']['message'] for v in
        load('vectors/signing.json')['vectors'] if v['name'] == 'GovernanceAction'))


@pytest.mark.parametrize('name', ['GovernanceAction', 'CollectGovernanceInput'])
def test_governance_admin_order_not_just_unique(name):
    value = governance()
    value['admins'] = ['0x'+'11'*20, '0x'+'22'*20]
    subject.validate(name, value)
    value['admins'].reverse()
    with pytest.raises(BAD):
        subject.validate(name, value)


@pytest.mark.parametrize('change', ['overlap', 'unsorted', 'outside', 'hash', 'overflow'])
def test_immutable_ranges_and_digest(change):
    value = load('vectors/ledger-export-shape.json')['entry']
    subject.validate('LedgerAbiEntryV2', value)
    if change == 'overlap': value['immutableReferences'][1]['start'] = '24'
    elif change == 'unsorted': value['immutableReferences'].reverse()
    elif change == 'outside': value['immutableReferences'][1]['start'] = '100'
    elif change == 'overflow': value['runtimeBytes'] = str(2**32)
    else: value['immutableRefsSha256'] = '00'*32
    with pytest.raises(BAD):
        subject.validate('LedgerAbiEntryV2', value)


@pytest.mark.parametrize('profile', ['repaired-e', 'repaired-f'])
def test_binding_rejects_profile_and_set_disagreement(profile):
    document = load('d50-owner-vectors.json')['documents'][profile]['document']
    subject.validate('DeploymentBindingDocument', document)
    document['profile']['name'] = 'paper-strict'
    with pytest.raises(BAD):
        subject.binding_hash(document)


@pytest.mark.parametrize('change', ['duplicate', 'threshold', 'set-order', 'mask', 'mixed-mask', 'profile', 'partial-immutables'])
def test_binding_cross_field_checks(change):
    value = load('d50-owner-vectors.json')['documents']['repaired-f']['document']
    if change == 'duplicate':
        for group in value['witnessSets'].values(): group['witnesses'][1] = group['witnesses'][0]
    elif change == 'threshold':
        for group in value['witnessSets'].values(): group['threshold'] = '5'
    elif change == 'set-order': value['witnessSets']['psc']['witnesses'].reverse()
    elif change == 'mask':
        for carrier in value['immutables'].values(): carrier['mutations'] = '512'
    elif change == 'mixed-mask': value['immutables']['Governance']['mutations'] = '1'
    elif change == 'profile': value['immutables']['PSC']['profile'] = '2'
    else: del value['chains']['dbc']['contracts']['KSSC']['immutableRefsSha256']
    with pytest.raises(BAD):
        subject.validate('DeploymentBindingDocument', value)


def test_q2_control_requires_mask_zero():
    value = load('d50-owner-vectors.json')['documents']['repaired-f']['document']
    for group in value['witnessSets'].values(): group['threshold'] = '2'
    subject.validate('DeploymentBindingDocument', value)
    for carrier in value['immutables'].values(): carrier['mutations'] = '1'
    with pytest.raises(BAD):
        subject.validate('DeploymentBindingDocument', value)


def test_export_digest_is_checked():
    for value in load('export-layout-owner-vectors.json')['bindingExports'].values():
        subject.validate('BindingExport', value)
        value['binding_v2'] = '00'*32
        with pytest.raises(BAD):
            subject.validate('BindingExport', value)


@pytest.mark.parametrize('row', load('vectors/success.json'))
def test_pool_success_operation_specific(row):
    subject.validate_response(row['operation'], row['response'])


@pytest.mark.parametrize('value', load('vectors/wire.json')['responses'])
def test_all_frozen_retry_examples(value):
    subject.validate_response('collect_checkpoint', value)


def collection():
    return copy.deepcopy(load('vectors/wire.json')['responses'][4]['result']['collection'])


@pytest.mark.parametrize('change', ['signer-order', 'not-signed', 'silent-replies', 'signed-zero',
    'report-order', 'report-overlap', 'missing-adoption', 'wrong-reporters', 'wrong-action',
    'wrong-deadline', 'wrong-close', 'late-hard-stop'])
def test_collection_declared_semantics(change):
    value = collection()
    subject.validate('Collection', value)
    if change == 'signer-order': value['submittedSigners'].reverse()
    elif change == 'not-signed': value['outcomes'][0]['status'] = 'duplicate-only'
    elif change == 'silent-replies': value['outcomes'][0].update(status='silent', replies='1')
    elif change == 'signed-zero': value['outcomes'][0]['replies'] = '0'
    elif change == 'report-order': value['recordedReports'].reverse()
    elif change == 'report-overlap':
        r = copy.deepcopy(value['recordedReports'][0])
        other = copy.deepcopy(r); other['message']['expiresAt'] = '1791521599'
        value['inconsistentReports'] = [{'witnessIndex': r['witnessIndex'],
            'reports': [{k:v for k,v in x.items() if k != 'witnessIndex'} for x in [r, other]]}]
    elif change == 'missing-adoption': del value['adopted']
    elif change == 'wrong-reporters': value['adopted']['reporters'] = ['0', '3']
    elif change == 'wrong-action': value['adopted']['reproposal'] = 'skipped_validity'
    elif change == 'wrong-deadline': value['timing']['collectionDeadlineMs'] = '9999'
    elif change == 'wrong-close': value['timing']['snapshotClosedAtMs'] = '4999'
    else:
        value['timing'].update(proposalExpiresAt='1791521474', collectionDeadlineMs='2000',
            snapshotClosedAtMs='2000', snapshotClosedBy='deadline')
        value['adopted']['reproposal'] = 'skipped_deadline'
        value['lateReports'] = [copy.deepcopy(value['recordedReports'][0])]
    with pytest.raises(BAD):
        subject.validate('Collection', value)


@pytest.mark.parametrize('remaining_ms,action', [(2000, 'skipped_validity'), (2001, 'sent')])
def test_retry_uses_adopted_expiry_at_reserve_boundary(remaining_ms, action):
    value = collection()
    # Selected message expires at 1791521500; proposal expires later.
    value['timing'].update(ledgerNowAtStart='1791521497', proposalExpiresAt='1791521520',
        snapshotClosedAtMs=str(3000-remaining_ms), snapshotClosedBy='all-replied')
    value['adopted']['reproposal'] = action
    subject.validate('Collection', value)
    value['adopted']['reproposal'] = 'sent' if action != 'sent' else 'skipped_validity'
    with pytest.raises(BAD):
        subject.validate('Collection', value)


@pytest.mark.parametrize('line', ['{"admins":[],"admins":[]}', '{"x":NaN}', '{"x":Infinity}', ' '*1048577],
    ids=['duplicate-key', 'nan', 'infinity', 'oversize'])
def test_strict_json_rejects_duplicates_nonfinite_oversize(line):
    with pytest.raises(ValueError, match='MALFORMED'):
        subject.validate_json_line('CollectGovernanceInput', line)


def test_strict_json_valid_governance():
    value = governance()
    assert subject.validate_json_line('CollectGovernanceInput', json.dumps(value)) == value


def test_inherited_nested_semantics_not_bypassed():
    value = load('vectors/success.json')[1]['response']
    subject.validate_response('collect_decision', value)
    value['result']['credentialRecords'].reverse()
    with pytest.raises(BAD):
        subject.validate_response('collect_decision', value)


def test_v1_still_refuses_f_governance_and_v2_envelopes():
    with pytest.raises(ValueError): validate_e('GovernanceAction', governance())
    with pytest.raises(ValidationError): validate_e('AdapterResponse', load('vectors/wire.json')['responses'][0])
