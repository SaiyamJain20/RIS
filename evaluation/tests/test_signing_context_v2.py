"""Synthetic context joins using real EIP-712 signatures; no live-chain claim."""
import copy
import importlib
import json
from pathlib import Path

from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak
from jsonschema import ValidationError
import pytest

from evaluation.tests.test_certificates_v2 import VECTORS, WITNESSES, WIRES, reports
from evaluation.tests.test_public_observations_v2 import setup, SyntheticRpc

BAD = (ValueError, ValidationError)


def subject():
    return importlib.import_module('evaluation.signing_context_v2')


def case(f=True, q='3'):
    manifest, observed, _, paths, _ = setup(f, threshold=q)
    witnesses = WITNESSES if f else WITNESSES[:1]
    manifest['fixture']['witnessSet']['witnesses'] = witnesses.copy()
    for chain in observed.values():
        for views in chain['views'].values():
            if 'witnesses' in views:
                views['witnesses']['value'] = witnesses.copy()
    return manifest, observed, paths


def domain(manifest, name):
    chain, contract = {
        'StateCheckpoint': ('dbc', 'KSSC'), 'AccessDecision': ('dbc', 'KSSC'),
        'GrantReceipt': ('pbc', 'PSC'), 'GovernanceAction': ('pbc', 'Governance'),
    }[name]
    pin = manifest['chains'][chain]
    return pin['chainId'], pin['contracts'].get(contract, '0x' + '99' * 20)


def message(manifest, name):
    value = copy.deepcopy(next(v['typedData']['message'] for v in VECTORS if v['name'] == name))
    value['witnessSetVersion'] = manifest['fixture']['witnessSet']['version']
    if name == 'StateCheckpoint':
        value.update(sourceChainId=manifest['chains']['pbc']['chainId'],
                     psc=manifest['chains']['pbc']['contracts']['PSC'])
    if name == 'GrantReceipt':
        value.update(dbcChainId=manifest['chains']['dbc']['chainId'],
                     kssc=manifest['chains']['dbc']['contracts']['KSSC'])
    return value


def sign(manifest, name, value, *, signers=None, changed_domain=None):
    # Field layouts come from the immutable published vectors, not the subject.
    typed = copy.deepcopy(next(v['typedData'] for v in VECTORS if v['name'] == name))
    chain, contract = domain(manifest, name)
    typed['domain'].update(chainId=chain, verifyingContract=contract)
    typed['domain'].update(changed_domain or {})
    typed['message'] = value
    encoded = encode_typed_data(full_message=typed)
    selected = manifest['fixture']['witnessSet']['witnesses'] if signers is None else signers
    keys = {Account.from_key(keccak(text=f'hmbc-e0-synthetic-key:witness-{n}')).address.lower():
            keccak(text=f'hmbc-e0-synthetic-key:witness-{n}') for n in range(1, 5)}
    return ['0x' + Account.sign_message(encoded, keys[a]).signature.hex() for a in sorted(selected)]


def check(manifest, observed, name, value=None, signatures=None):
    value = message(manifest, name) if value is None else value
    q = int(manifest['fixture']['witnessSet']['threshold'])
    signatures = sign(manifest, name, value)[:q] if signatures is None else signatures
    return subject().verify_bound_certificate(name, value, signatures, manifest=manifest,
        observations=observed, compiled_max_admins='8' if manifest['profileEnum'] == '3' else None)


@pytest.mark.parametrize('f,q', [(True, '3'), (True, '2'), (False, '1')])
@pytest.mark.parametrize('name', ['StateCheckpoint', 'AccessDecision', 'GrantReceipt', 'GovernanceAction'])
def test_bound_certificate_positive_profiles(f, q, name):
    manifest, observed, _ = case(f, q)
    original = copy.deepcopy((manifest, observed))
    if name == 'GovernanceAction' and not f:
        with pytest.raises(ValueError, match='governance'):
            check(manifest, observed, name)
    else:
        assert check(manifest, observed, name) == sorted(manifest['fixture']['witnessSet']['witnesses'])[:int(q)]
    assert (manifest, observed) == original


@pytest.mark.parametrize('name,field,wrong', [
    ('StateCheckpoint', 'sourceChainId', '999'),
    ('StateCheckpoint', 'psc', '0x' + '99' * 20),
    ('GrantReceipt', 'dbcChainId', '999'),
    ('GrantReceipt', 'kssc', '0x' + '99' * 20),
])
def test_valid_signatures_cannot_authorize_wrong_embedded_identity(name, field, wrong):
    manifest, observed, _ = case()
    value = message(manifest, name)
    value[field] = wrong
    with pytest.raises(ValueError, match='embedded'):
        check(manifest, observed, name, value)


@pytest.mark.parametrize('name', ['StateCheckpoint', 'AccessDecision', 'GrantReceipt', 'GovernanceAction'])
@pytest.mark.parametrize('change', [
    {'chainId': '999'}, {'verifyingContract': '0x' + '99' * 20},
    {'name': 'WrongDomain'}, {'version': '2'},
])
def test_artifact_cannot_select_signing_domain(name, change):
    manifest, observed, _ = case()
    value = message(manifest, name)
    signatures = sign(manifest, name, value, changed_domain=change)[:3]
    with pytest.raises(BAD):
        check(manifest, observed, name, value, signatures)


@pytest.mark.parametrize('change', ['count-two', 'count-four', 'duplicate', 'reverse', 'set-one', 'unknown'])
def test_artifact_cannot_select_quorum_or_membership(change):
    manifest, observed, _ = case()
    value = message(manifest, 'AccessDecision')
    if change == 'set-one': value['witnessSetVersion'] = '1'
    signatures = sign(manifest, 'AccessDecision', value)[:3]
    if change == 'count-two': signatures.pop()
    if change == 'count-four': signatures = sign(manifest, 'AccessDecision', value)
    if change == 'duplicate': signatures[1] = signatures[0]
    if change == 'reverse': signatures.reverse()
    if change == 'unknown':
        # Replace configured membership AND observed getter with another valid
        # synthetic identity. An original signer then lies outside this context.
        replacement = '0x' + '99' * 20
        manifest['fixture']['witnessSet']['witnesses'][0] = replacement
        for chain in observed.values():
            for views in chain['views'].values():
                if 'witnesses' in views: views['witnesses']['value'][0] = replacement
    with pytest.raises(BAD):
        check(manifest, observed, 'AccessDecision', value, signatures)


@pytest.mark.parametrize('change', ['anchor', 'chain', 'code', 'configured', 'set', 'wiring', 'max-admins'])
def test_observations_are_revalidated_before_signature_check(change):
    manifest, observed, _ = case()
    kwargs = dict(manifest=manifest, observations=observed, compiled_max_admins='8')
    if change == 'anchor': observed['pbc']['confirmedAnchor']['hash'] = '0x' + '99' * 32
    if change == 'chain': observed['dbc']['chainId'] = '999'
    if change == 'code': observed['dbc']['code']['KSSC']['value'] = '0x00'
    if change == 'configured': observed['pbc']['views']['PSC']['configured']['value'] = False
    if change == 'set': observed['dbc']['views']['KSSC']['threshold']['value'] = '2'
    if change == 'wiring': observed['pbc']['views']['PSC']['ksscForChain']['value'] = '0x' + '99' * 20
    if change == 'max-admins': kwargs['compiled_max_admins'] = '9'
    value = message(manifest, 'AccessDecision')
    with pytest.raises(BAD):
        subject().verify_bound_certificate('AccessDecision', value,
            sign(manifest, 'AccessDecision', value)[:3], **kwargs)


def replace_source(value, manifest, *, psc=None):
    if isinstance(value, dict):
        if 'sourceChainId' in value and 'psc' in value:
            value.update(sourceChainId=manifest['chains']['pbc']['chainId'],
                         psc=psc or manifest['chains']['pbc']['contracts']['PSC'])
        for child in value.values(): replace_source(child, manifest, psc=psc)
    elif isinstance(value, list):
        for child in value: replace_source(child, manifest, psc=psc)


def response_for(manifest, index, *, wrong_source=False):
    response = copy.deepcopy(WIRES[index])
    # Preserve original distinct messages, adopted copies and timing relations.
    replace_source(response, manifest, psc='0x' + '99' * 20 if wrong_source else None)
    for owner, report in reports(response):
        report['signature'] = sign(manifest, 'StateCheckpoint', report['message'], signers=[WITNESSES[owner]])[0]
    return response


def check_reports(manifest, observed, response, selected='0'):
    return subject().verify_bound_checkpoint_reports(response, manifest=manifest,
        observations=observed, compiled_max_admins='8', selected_index=selected)


@pytest.mark.parametrize('index', range(len(WIRES)))
def test_every_declared_retry_report_uses_bound_context(index):
    manifest, observed, _ = case()
    response = response_for(manifest, index)
    original = copy.deepcopy(response)
    assert check_reports(manifest, observed, response) == len(reports(response))
    assert response == original


REPORT_PATHS = [(i, j) for i, response in enumerate(WIRES) for j, _ in enumerate(reports(response))]


@pytest.mark.parametrize('index,report_index', REPORT_PATHS)
def test_each_retry_report_refuses_signature_from_wrong_domain(index, report_index):
    manifest, observed, _ = case()
    response = response_for(manifest, index)
    owner, report = reports(response)[report_index]
    report['signature'] = sign(manifest, 'StateCheckpoint', report['message'],
        signers=[WITNESSES[owner]], changed_domain={'chainId': '999'})[0]
    with pytest.raises(ValueError, match='unknown recovered signer'):
        check_reports(manifest, observed, response)


@pytest.mark.parametrize('index', [i for i, r in enumerate(WIRES) if reports(r)])
def test_retry_shapes_refuse_valid_signatures_on_wrong_source(index):
    manifest, observed, _ = case()
    response = response_for(manifest, index, wrong_source=True)
    with pytest.raises(ValueError, match='embedded'):
        check_reports(manifest, observed, response)


def test_pinned_report_owner_still_requires_request_selection():
    manifest, observed, _ = case()
    index = next(i for i, r in enumerate(WIRES) if 'recorded' in (r.get('error') or {}))
    response = response_for(manifest, index)
    for selected in (None, '1', '4', 0):
        with pytest.raises(BAD):
            check_reports(manifest, observed, response, selected)


def test_collector_to_signatures_uses_actual_normalized_public_reads(tmp_path):
    manifest, observed, paths = case()
    clients = {c: SyntheticRpc(manifest, observed, c) for c in ('pbc', 'dbc')}
    collected = importlib.import_module('evaluation.public_observations_v2').collect(
        manifest, clients, paths, output=tmp_path / 'public', compiled_max_admins='8')
    for name in ('StateCheckpoint', 'AccessDecision', 'GrantReceipt', 'GovernanceAction'):
        assert check(manifest, collected['observations'], name) == sorted(WITNESSES)[:3]


def test_unsupported_name_refuses():
    manifest, observed, _ = case()
    with pytest.raises(ValueError, match='message type'):
        check(manifest, observed, 'Unknown', {}, [])


def test_complete_e_successor_carrier_keeps_single_witness_context():
    manifest, observed, _ = case(False, '1')
    example = Path(__file__).resolve().parents[2] / 'interfaces/proposals/v2-e-source-closure/e-complete-example.json'
    manifest['schemaVersion'] = 'hmbc-ledger-deployment/v2.1'
    manifest['sources'] = json.loads(example.read_text())['sources']
    assert check(manifest, observed, 'AccessDecision') == WITNESSES[:1]


def test_no_reports_does_not_skip_deployment_validation():
    manifest, observed, _ = case()
    observed['pbc']['views']['PSC']['configured']['value'] = False
    with pytest.raises(ValueError, match='configured'):
        check_reports(manifest, observed, response_for(manifest, 2))
