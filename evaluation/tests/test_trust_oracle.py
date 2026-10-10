"""Independent E02 trust-freshness oracle (SL5, frozen rows E02-wrong-issuer-* and E02-signed-list-rollback-*).

Expectations: frozen catalog rows; pinned ledger TMSC (933d2a7): _authorizeUpdate checks a known
authority, then an issuer-scoped CA-admin caller (UNAUTHORIZED_CALLER 16), then (not paper-minimal) the
issuer root signature; _checkFreshness exists only in repaired-e (version strictly increasing, list
still valid: STALE_ANCHOR 5). Paper profiles treat the latest appended list as current, so a replayed
older signed CRL un-revokes a credential (SPEC_GAP). A credential revoked in the current generation
gives REVOKED (19) and PSC.requestAccess emits AccessDenied without a request record. Synthetic facts.
"""
import copy
import importlib
import json

import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak

from evaluation.tests.test_access_artifacts import artifacts
from evaluation.tests.test_bootstrap import inputs

ROOT_KEYS = {'H1': 'H1-root', 'H2': 'H2-root'}
SERIAL = '101'
ALICE = '0xc4ff0022e776c3471e39abf6c69ce679440c956d'
PROFILES = ['paper-strict', 'paper-minimal', 'repaired-e']


def oracle(name):
    module = importlib.import_module('evaluation.oracles.trust')
    assert hasattr(module, name), 'trust oracle missing'
    return getattr(module, name)


def sign_list(body, dep, label):
    vectors = json.load(open('interfaces/v1/vectors/eip712-agent1.json'))['vectors']
    typed = copy.deepcopy(next(v['typedData'] for v in vectors if v['name'] == 'RevocationList'))
    pbc = dep['chains']['pbc']
    typed['domain'].update(chainId=pbc['chainId'], verifyingContract=pbc['contracts']['TMSC'])
    typed['message'] = body
    signed = Account.sign_message(encode_typed_data(full_message=typed), keccak(text='hmbc-e0-synthetic-key:'+label))
    return '0x'+signed.signature.hex(), '0x'+signed.message_hash.hex()


def authority(dep, hid):
    return next(a for a in dep['fixture']['authorities'] if a['id'] == hid)


def item(dep, hid, version, valid_until, revoked):
    root = authority(dep, hid)['root']
    body = dict(authority=root, version=version, validUntil=valid_until, revokedSerials=list(revoked))
    signature, digest = sign_list(body, dep, ROOT_KEYS[hid])
    return dict(kind='RevocationList', call='TMSC.updateRevocationList', submitterRole=hid+'-ca-admin',
                submitter=authority(dep, hid)['caAdmins'][0], list=body, signature=signature, signer=root), digest


def anchor(version, generation, digest, block, prev, valid_until='1791699757'):
    return dict(published=True, version=version, validUntil=valid_until, generation=generation, contentDigest=digest,
                blockNumber=block, prevBlockNumber=prev)


NEVER = dict(instantiated=False, exitCode=1, message='no worker.sqlite in /tmp/p3/t (looked in <dir>/worker/ and in <dir>)\n',
             checkedAbsent=['/tmp/p3/t/worker/worker.sqlite', '/tmp/p3/t/worker.sqlite'])


def snapshot(dep, anchors, epoch, revoked, code, records, pbc_logs):
    return dict(anchors=copy.deepcopy(anchors), authEpoch=epoch, revoked={SERIAL: revoked}, credentials=dict(code=code, records=records),
                logs=dict(pbc=copy.deepcopy(pbc_logs), dbc=[dict(name='DataRegistered', fields={})]), worker=copy.deepcopy(NEVER))


def update_events(dep, it, digest, generation, epoch, prev, hid):
    root = authority(dep, hid)['root']; body = it['list']
    return [dict(name='LogRecorded', fields=dict(logId='9', kind='2', subject='0x'+'5a'*32, detailsHash='0x'+'5b'*32, details='0x')),
            dict(name='TrustAnchorUpdated', fields=dict(authority=root, kind='1', version=body['version'], validUntil=body['validUntil'],
                                                        generation=generation, contentDigest=digest, prevBlockNumber=prev,
                                                        authEpoch=epoch, submitter=it['submitter']))]


def records(dep, crl_version):
    h1 = authority(dep, 'H1')['root']
    return [dict(issuer=h1, role='0x'+keccak(text='HMBC.role.Doctor').hex(), kind='1', serial=SERIAL, anchorVersion=crl_version,
                 validUntil='1791699757'),
            dict(issuer=h1, role='0x'+keccak(text='HMBC.role.OnDuty').hex(), kind='2', serial='0', anchorVersion='1', validUntil='1791642157')]


def wrong_issuer_facts(artifacts, profile):
    dep = artifacts[0]; h2 = authority(dep, 'H2')
    it, digest = item(dep, 'H2', '2', '1791700000', [])
    anchors = {authority(dep, 'H1')['root']: anchor('1', '1', '0x'+'11'*32, '30', '0'), h2['root']: anchor('1', '1', '0x'+'22'*32, '31', '0')}
    before = snapshot(dep, anchors, '3', False, '0', records(dep, '1'), [dict(name='TrustAnchorUpdated', fields={})])
    return dict(profile=profile, before=before, after=copy.deepcopy(before), item=it, item_digest=digest, authority=h2['root'],
                membership=dict(wrongAdmin=False, rightAdmin=True), simulated_generation='2', success=False, rejection_code='16',
                receipt_events=[], pbc_chain_id=dep['chains']['pbc']['chainId'], tmsc=dep['chains']['pbc']['contracts']['TMSC'])


def rollback_facts(artifacts, profile):
    dep = artifacts[0]; h1 = authority(dep, 'H1')['root']; h2 = authority(dep, 'H2')['root']
    old, old_digest = item(dep, 'H1', '1', '1791699757', [])
    new, new_digest = item(dep, 'H1', '2', '1791700100', [SERIAL])
    base_logs = [dict(name='TrustAnchorUpdated', fields={})]
    a0 = {h1: anchor('1', '1', old_digest, '30', '0'), h2: anchor('1', '1', '0x'+'22'*32, '31', '0')}
    initial = snapshot(dep, a0, '3', False, '0', records(dep, '1'), base_logs)
    install = update_events(dep, new, new_digest, '2', '4', '30', 'H1')
    a1 = dict(a0, **{h1: anchor('2', '2', new_digest, '50', '30', '1791700100')})
    installed = snapshot(dep, a1, '4', True, '19', [], base_logs+install)
    paper = profile != 'repaired-e'
    digest = '0x'+'d1'*32
    if paper:
        replay = update_events(dep, old, old_digest, '3', '5', '50', 'H1')
        a2 = dict(a1, **{h1: anchor('1', '3', old_digest, '51', '50')})
        replayed = snapshot(dep, a2, '5', False, '0', records(dep, '1'), base_logs+install+replay)
        request = dict(digest=digest, authEpoch='5', events=[
            dict(name='LogRecorded', fields=dict(logId='12', kind='3', subject=digest)),
            dict(name='AccessForwarded', fields=dict(requestDigest=digest, gid=ALICE, verifiedAttributes=records(dep, '1')))],
            state=dict(status='1'), denialCount='0')
    else:
        replay = []
        replayed = copy.deepcopy(installed)
        request = dict(digest=digest, authEpoch='4', events=[
            dict(name='LogRecorded', fields=dict(logId='12', kind='3', subject=digest)),
            dict(name='AccessDenied', fields=dict(requestDigest=digest, claimedGid=ALICE, code='19', requestLogId='12'))],
            state=dict(status='0'), denialCount='1')
    return dict(profile=profile, initial=initial, installed=installed, replayed=replayed, new_item=new, new_digest=new_digest,
                old_item=old, old_digest=old_digest, install_success=True, install_events=install, replay_success=paper,
                replay_code=None if paper else '5', replay_events=replay, replay_timestamp='1791613500', request=request,
                alice=ALICE, serial=SERIAL, pbc_chain_id=dep['chains']['pbc']['chainId'], tmsc=dep['chains']['pbc']['contracts']['TMSC'])



@pytest.mark.parametrize('profile', PROFILES)
def test_wrong_issuer_rejected_in_every_profile(artifacts, profile):
    result = oracle('check_wrong_issuer')(**wrong_issuer_facts(artifacts, profile))
    assert result['ok'] and (result['classification'], result['error'], result['outcome']) == ('SUPPORTED', 'UNAUTHORIZED_CALLER', 'REJECT')


@pytest.mark.parametrize('profile', PROFILES)
@pytest.mark.parametrize('mutation', ['accepted', 'other-code', 'state-changed', 'epoch-changed', 'right-admin', 'wrong-is-admin',
                                      'simulation-failed', 'other-authority', 'bad-signature', 'stale-version', 'worker-changed', 'logs'])
def test_wrong_issuer_refuses_false_observations(artifacts, profile, mutation):
    f = wrong_issuer_facts(artifacts, profile); dep = artifacts[0]
    if mutation == 'accepted': f.update(success=True, rejection_code=None)
    if mutation == 'other-code': f['rejection_code'] = '1'
    if mutation == 'state-changed': f['after']['anchors'][f['authority']]['version'] = '2'
    if mutation == 'epoch-changed': f['after']['authEpoch'] = '4'
    if mutation == 'right-admin': f['membership']['rightAdmin'] = False
    if mutation == 'wrong-is-admin': f['membership']['wrongAdmin'] = True
    if mutation == 'simulation-failed': f['simulated_generation'] = None
    if mutation == 'other-authority':
        f['item'], f['item_digest'] = item(dep, 'H1', '2', '1791700000', [])
    if mutation == 'bad-signature': f['item']['signature'] = sign_list(f['item']['list'], dep, 'H1-root')[0]
    if mutation == 'stale-version':
        f['item'], f['item_digest'] = item(dep, 'H2', '1', '1791700000', [])
    if mutation == 'worker-changed': f['after']['worker'] = dict(instantiated=True, log=dict(events=[], releases=[]))
    if mutation == 'logs': f['receipt_events'] = [dict(name='TrustAnchorUpdated', fields={})]
    with pytest.raises(ValueError):
        oracle('check_wrong_issuer')(**f)


@pytest.mark.parametrize('profile', PROFILES)
def test_rollback_expected_classes(artifacts, profile):
    result = oracle('check_list_rollback')(**rollback_facts(artifacts, profile))
    expected = ('REPAIR_SUPPORTED', 'STALE_ANCHOR', 'REJECT') if profile == 'repaired-e' else ('SPEC_GAP', None, 'ACCEPT')
    assert result['ok'] and (result['classification'], result['error'], result['outcome']) == expected
    assert result['rolledBack'] is (profile != 'repaired-e')


@pytest.mark.parametrize('profile', PROFILES)
@pytest.mark.parametrize('mutation', ['install-missing-revocation', 'install-not-revoked', 'new-not-newer', 'old-not-bootstrap-version',
                                      'old-expired', 'old-revokes', 'old-bad-signature', 'replay-other-outcome', 'replay-other-code',
                                      'replay-state', 'request-other', 'request-stale-epoch', 'worker-changed', 'initial-revoked'])
def test_rollback_refuses_false_observations(artifacts, profile, mutation):
    f = rollback_facts(artifacts, profile); dep = artifacts[0]; paper = profile != 'repaired-e'; h1 = authority(dep, 'H1')['root']
    if mutation == 'install-missing-revocation':
        f['new_item'], f['new_digest'] = item(dep, 'H1', '2', '1791700100', [])
    if mutation == 'install-not-revoked': f['installed']['revoked'][SERIAL] = False
    if mutation == 'new-not-newer':
        f['new_item'], f['new_digest'] = item(dep, 'H1', '1', '1791700100', [SERIAL])
    if mutation == 'old-not-bootstrap-version':
        f['old_item'], f['old_digest'] = item(dep, 'H1', '3', '1791699757', [])
    if mutation == 'old-expired': f['replay_timestamp'] = '1791699757'
    if mutation == 'old-revokes':
        f['old_item'], f['old_digest'] = item(dep, 'H1', '1', '1791699757', [SERIAL])
    if mutation == 'old-bad-signature': f['old_item']['signature'] = sign_list(f['old_item']['list'], dep, 'H2-root')[0]
    if mutation == 'replay-other-outcome':
        f.update(replay_success=not paper, replay_code='5' if paper else None)
    if mutation == 'replay-other-code':
        if paper: f.update(replay_success=False, replay_code='1', replay_events=[], replayed=copy.deepcopy(f['installed']))
        else: f['replay_code'] = '8'
    if mutation == 'replay-state':
        f['replayed']['revoked'][SERIAL] = not f['replayed']['revoked'][SERIAL]
    if mutation == 'request-other':
        if paper: f['request']['events'][1] = dict(name='AccessDenied', fields=dict(requestDigest=f['request']['digest'], claimedGid=ALICE,
                                                                                    code='19', requestLogId='12'))
        else: f['request']['events'][1]['fields']['code'] = '0'
    if mutation == 'request-stale-epoch': f['request']['authEpoch'] = str(int(f['request']['authEpoch'])-1)
    if mutation == 'worker-changed': f['replayed']['worker'] = dict(instantiated=True, log=dict(events=[], releases=[]))
    if mutation == 'initial-revoked': f['initial']['revoked'][SERIAL] = True
    with pytest.raises(ValueError):
        oracle('check_list_rollback')(**f)
