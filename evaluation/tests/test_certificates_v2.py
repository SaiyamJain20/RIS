"""Synthetic cryptographic controls, not chain/state/durability evidence."""
import copy
import importlib
import json
from pathlib import Path

import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak
from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / 'interfaces/v2'
VECTORS = json.loads((V2 / 'vectors/signing.json').read_text())['vectors']
WITNESSES = [r['address'] for r in json.loads((V2 / 'vectors/witnesses.json').read_text())['witnesses']]
BAD = (ValueError, ValidationError)


@pytest.fixture
def subject():
    return importlib.import_module('evaluation.certificates_v2')


def context(vector):
    domain = vector['typedData']['domain']
    return dict(chain_id=domain['chainId'], verifying_contract=domain['verifyingContract'])


def verify(subject, vector, *, message=None, signatures=None, **overrides):
    options = context(vector) | dict(witnesses=WITNESSES, witness_set_version='2', required_signatures=3)
    options.update(overrides)
    return subject.verify_certificate(vector['name'], vector['typedData']['message'] if message is None else message,
        [r['signature'] for r in vector['signatures']] if signatures is None else signatures, **options)


@pytest.mark.parametrize('i', range(6))
def test_frozen_digests_and_sorted_signers(subject, i):
    row = VECTORS[i]
    original = copy.deepcopy(row)
    assert subject.message_digest(row['name'], row['typedData']['message'], **context(row)) == row['digest']
    assert verify(subject, row) == [r['signer'] for r in row['signatures']]
    assert row == original


FIELDS = [(i, f['name'], f['type']) for i, v in enumerate(VECTORS) for f in v['typedData']['types'][v['name']]]


@pytest.mark.parametrize('i,field,kind', FIELDS)
def test_every_signed_field_is_bound(subject, i, field, kind):
    row = VECTORS[i]
    message = copy.deepcopy(row['typedData']['message'])
    if kind == 'bytes32': message[field] = '0x' + '99' * 32
    elif kind == 'address': message[field] = '0x' + '99' * 20
    elif kind == 'address[]': message[field] = ['0x' + '99' * 20]
    else: message[field] = str(int(message[field]) + 1)
    with pytest.raises(BAD):
        verify(subject, row, message=message)


@pytest.mark.parametrize('i', range(6))
@pytest.mark.parametrize('field,value', [('chain_id', '28546'), ('verifying_contract', '0x' + '99' * 20)])
def test_domain_chain_and_contract_are_bound(subject, i, field, value):
    with pytest.raises(BAD):
        verify(subject, VECTORS[i], **{field: value})


@pytest.mark.parametrize('field,value', [('name', 'HMBCDecision'), ('version', '2')])
def test_domain_name_and_version_cannot_come_from_artifact(subject, field, value):
    row = VECTORS[0]
    typed = copy.deepcopy(row['typedData'])
    typed['domain'][field] = value
    # Public deterministic SYNTHETIC fixture key, not a credential.
    key = keccak(text='hmbc-e0-synthetic-key:witness-1')
    signature = '0x' + Account.sign_message(encode_typed_data(full_message=typed), key).signature.hex()
    with pytest.raises(BAD):
        verify(subject, row, signatures=[signature], required_signatures=1)


@pytest.mark.parametrize('change', ['duplicate', 'reversed', 'unknown', 'short', 'long', 'bad-v', 'high-s', 'r-zero'])
def test_certificate_controls(subject, change):
    row = VECTORS[0]
    signatures = [r['signature'] for r in row['signatures']]
    witnesses = WITNESSES
    if change == 'duplicate': signatures[1] = signatures[0]
    elif change == 'reversed': signatures.reverse()
    elif change == 'unknown': witnesses = ['0x'+'99'*20] + WITNESSES[1:]
    elif change == 'short': signatures.pop()
    elif change == 'long': signatures.append(signatures[0])
    else:
        raw = bytearray.fromhex(signatures[0][2:])
        if change == 'bad-v': raw[-1] = 0
        elif change == 'high-s': raw[32:64] = (2**256-1).to_bytes(32, 'big')
        else: raw[:32] = bytes(32)
        signatures[0] = '0x' + raw.hex()
    with pytest.raises(BAD):
        verify(subject, row, signatures=signatures, witnesses=witnesses)


@pytest.mark.parametrize('option,value', [
    ('chain_id', 28545), ('chain_id', True), ('chain_id', '01'), ('chain_id', str(2**256)),
    ('verifying_contract', '0x'+'00'*20), ('verifying_contract', 'not-an-address'),
    ('witness_set_version', '1'), ('witness_set_version', '02'), ('witness_set_version', 2),
    ('required_signatures', True), ('required_signatures', 0), ('required_signatures', 5),
    ('required_signatures', '3'), ('witnesses', []), ('witnesses', WITNESSES+[WITNESSES[0]]),
    ('witnesses', ['0x'+'00'*20]), ('witnesses', 'invalid'),
], ids=lambda value: str(value)[:30])
def test_bad_or_mismatched_context_refuses(subject, option, value):
    with pytest.raises(BAD):
        verify(subject, VECTORS[0], **{option: value})


def test_explicit_q2_and_single_controls_are_not_q3(subject):
    row = VECTORS[0]
    signatures = [r['signature'] for r in row['signatures']]
    assert verify(subject, row, signatures=signatures[:2], required_signatures=2) == [r['signer'] for r in row['signatures'][:2]]
    assert verify(subject, row, signatures=signatures[:1], required_signatures=1) == [WITNESSES[0]]
    with pytest.raises(BAD):
        verify(subject, row, signatures=signatures[:2])


def test_unsupported_message_type_refuses(subject):
    with pytest.raises(ValueError, match='message type'):
        subject.message_digest('EIP712Domain', {}, **context(VECTORS[0]))


WIRES = json.loads((V2 / 'vectors/wire.json').read_text())['responses']


def reports(response):
    payload = response['result'] if response['ok'] else response['error']
    values = []
    if 'recorded' in payload:
        values.append((0, payload['recorded']))
    collection = payload.get('collection', {})
    values += [(int(r['witnessIndex']), r) for k in ('recordedReports', 'lateReports') for r in collection.get(k, [])]
    values += [(int(r['witnessIndex']), x) for r in collection.get('inconsistentReports', []) for x in r['reports']]
    return values


def check_reports(subject, response, **overrides):
    options = context(VECTORS[0]) | dict(witnesses=WITNESSES, witness_set_version='2', selected_index='0')
    options.update(overrides)
    return subject.verify_checkpoint_reports(response, **options)


@pytest.mark.parametrize('i', range(len(WIRES)))
def test_all_frozen_report_paths(subject, i):
    response = copy.deepcopy(WIRES[i])
    assert check_reports(subject, response) == len(reports(response))
    assert response == WIRES[i]


REPORT_CASES = [(i, j) for i, r in enumerate(WIRES) for j, _ in enumerate(reports(r))]


@pytest.mark.parametrize('i,j', REPORT_CASES)
def test_each_report_path_binds_owner_signature_and_message(subject, i, j):
    response = copy.deepcopy(WIRES[i])
    index, report = reports(response)[j]
    report['message']['sourceBlockNumber'] = str(int(report['message']['sourceBlockNumber'])+1)
    with pytest.raises(BAD):
        check_reports(subject, response)


def test_pinned_report_requires_explicit_selected_index(subject):
    response = next(r for r in WIRES if 'recorded' in (r.get('error') or {}))
    for selected in (None, '1', '4', 0):
        with pytest.raises(BAD):
            check_reports(subject, response, selected_index=selected)


def test_report_index_cannot_substitute_for_recovered_owner(subject):
    response = copy.deepcopy(next(r for r in WIRES if (r.get('error') or {}).get('collection', {}).get('recordedReports')))
    # Keep each index, message, partition and signature shape; change the mapping.
    swapped = WITNESSES.copy()
    swapped[0], swapped[1] = swapped[1], swapped[0]
    with pytest.raises(BAD):
        check_reports(subject, response, witnesses=swapped)


def test_carried_e_version_one_certificate(subject):
    row = copy.deepcopy(VECTORS[0])
    row['typedData']['message']['witnessSetVersion'] = '1'
    key = keccak(text='hmbc-e0-synthetic-key:witness-1')
    signature = '0x'+Account.sign_message(encode_typed_data(full_message=row['typedData']), key).signature.hex()
    assert verify(subject, row, signatures=[signature], witnesses=WITNESSES[:1],
                  witness_set_version='1', required_signatures=1) == WITNESSES[:1]
