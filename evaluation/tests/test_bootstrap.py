"""Bootstrap must reject a valid-looking artifact from another instance/actor.

The copied owner sample is public, synthetic and from an old deployment. Test
metadata binds it to an adapted frozen deployment; no chain or producer runs.
"""
import copy
import hashlib
import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def checker():
    assert importlib.util.find_spec('evaluation.bootstrap') is not None, 'Instance-bound bootstrap verifier is missing'
    return importlib.import_module('evaluation.bootstrap').validate_bootstrap


@pytest.fixture
def inputs():
    sample = json.loads((ROOT/'evaluation/fixtures/e1/bootstrap-owner-sample.json').read_text())
    deployment = copy.deepcopy(json.loads((ROOT/'interfaces/v1/vectors/deployment-agent1.json').read_text())['deployments'][-1])
    deployment.update(interfaceVersion='v1', profile='repaired-e', profileEnum='2', mutations='0')
    binding = sample['binding']
    deployment['chains']['pbc']['contracts'].update(TMSC=binding['tmsc'], RSC=binding['rsc'])
    raw = json.dumps(deployment).encode()
    sample['binding']['deploymentSha256'] = hashlib.sha256(raw).hexdigest()
    versions = {a['root']: {'revocation': '0', 'temporal': '0'} for a in deployment['fixture']['authorities']}
    return sample, dict(deployment_bytes=raw, source_block={'number': '0x152', 'timestamp': '0x6ac7c114'},
                        versions=versions, now_timestamp='1791475988')


def test_positive_bootstrap_retains_registered_policy_denied_bob(inputs):
    sample, kwargs = inputs
    # Native block number 338 and time 1791475988, independent of producer metadata.
    kwargs['source_block']['timestamp'] = hex(1791475988)
    result = checker()(sample, **kwargs)
    assert result['users']['bob']['bundle']['temporalClaims'] == []
    assert result['users']['alice']['registration']['certDigest'] == '0xc11f902acedc00001a32ef6593fe463d95116c8d1da420b41fc4d4140ee37cd3'
    assert result['signatureChecks'] == 7
    result['users']['alice']['bundle']['certificates'].clear()
    assert sample['users']['alice']['bundle']['certificates']


@pytest.mark.parametrize('field,value', [
    ('deploymentSha256', 'f'*64), ('pbcChainId', '28545'),
    ('tmsc', '0x'+'11'*20), ('rsc', '0x'+'22'*20), ('profile', '0'),
    ('blockNumber', '339'), ('blockTimestamp', '1791475989')])
def test_wrong_instance_or_source_block_refuses_before_submission(inputs, field, value):
    sample, kwargs = inputs
    kwargs['source_block']['timestamp'] = hex(1791475988)
    sample['binding'][field] = value
    with pytest.raises(ValueError): checker()(sample, **kwargs)


@pytest.mark.parametrize('change', [
    'unknown-root', 'wrong-admin', 'wrong-kind', 'wrong-call', 'version',
    'list-expired', 'unexpected-revocation', 'root-signature', 'missing-list',
    'reordered-list', 'extra-secret', 'not-test-only', 'unknown-user',
    'gid-substitution', 'bundle-substitution', 'recipient-label', 'recipient-hash',
    'certificate-digest', 'possession-signature', 'duty-claim', 'certificate-role',
    'registration-expiry', 'stale-current-version', 'extra-field'])
def test_wrong_actor_bundle_or_unsigned_metadata_is_rejected(inputs, change):
    sample, kwargs = inputs
    kwargs['source_block']['timestamp'] = hex(1791475988)
    item = sample['trustLists'][0]; alice = sample['users']['alice']
    if change == 'unknown-root': item['signer'] = item['list']['authority'] = '0x'+'11'*20
    elif change == 'wrong-admin': item['submitter'] = sample['trustLists'][2]['submitter']
    elif change == 'wrong-kind': item['kind'] = 'Registration'
    elif change == 'wrong-call': item['call'] = 'TMSC.addCA'
    elif change == 'version': item['list']['version'] = '2'
    elif change == 'list-expired': item['list']['validUntil'] = '1791475988'
    elif change == 'unexpected-revocation': item['list']['revokedSerials'] = ['101']
    elif change == 'root-signature': item['signature'] = sample['trustLists'][2]['signature']
    elif change == 'missing-list': sample['trustLists'].pop()
    elif change == 'reordered-list': sample['trustLists'].reverse()
    elif change == 'extra-secret': alice['privateKey'] = 'never print this value'
    elif change == 'not-test-only': sample['testOnly'] = False
    elif change == 'unknown-user': sample['users']['eve'] = copy.deepcopy(alice)
    elif change == 'gid-substitution': alice['gid'] = sample['users']['bob']['gid']
    elif change == 'bundle-substitution': alice['bundle'] = copy.deepcopy(sample['users']['bob']['bundle'])
    elif change == 'recipient-label': alice['recipientKeyLabel'] = 'HMBC.recipient-key.bob'
    elif change == 'recipient-hash': alice['recipientKeyHash'] = '0x'+'11'*32
    elif change == 'certificate-digest': alice['registration']['certDigest'] = '0x'+'11'*32
    elif change == 'possession-signature': alice['possessionSignature'] = sample['users']['bob']['possessionSignature']
    elif change == 'duty-claim': alice['bundle']['temporalClaims'].clear()
    elif change == 'certificate-role': alice['certificate']['cert']['roles'] = sample['users']['bob']['certificate']['cert']['roles']
    elif change == 'registration-expiry': alice['registration']['expiresAt'] = '1791475988'
    elif change == 'stale-current-version': kwargs['versions'][item['signer']]['revocation'] = '1'
    elif change == 'extra-field': sample['binding']['ignored'] = '1'
    with pytest.raises(ValueError): checker()(sample, **kwargs)


def test_registration_at_expiry_is_not_reusable_authorization(inputs):
    sample, kwargs = inputs
    kwargs['source_block']['timestamp'] = hex(1791475988)
    kwargs['now_timestamp'] = '1791479588'
    with pytest.raises(ValueError): checker()(sample, **kwargs)


@pytest.mark.parametrize('bad', [b'{"x":1,"x":2}', b'{"x":NaN}', b'[]', b'x'*1048577])
def test_raw_bootstrap_uses_bounded_strict_json(inputs, bad):
    _, kwargs = inputs
    with pytest.raises(ValueError): checker()(bad, **kwargs)
