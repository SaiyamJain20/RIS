"""Independent synthetic routing/completion checks; no live catalog evidence."""
import copy
import importlib

import pytest
from eth_utils import keccak

from evaluation.tests.test_subject_substitution import facts as pre_release_facts


def oracle():
    module = importlib.import_module('evaluation.oracles.subject')
    assert hasattr(module, 'check_subject_completion'), 'subject completion oracle missing'
    return module.check_subject_completion


def facts(profile='paper-strict'):
    aliases = dict(alice='0x'+'11'*20, bob='0x'+'22'*20, record='0x'+'33'*32,
                   digest='0x'+'44'*32, grant='0x'+'55'*32,
                   **{'alice-key': '0x'+'66'*32})
    def canonical(value):
        if isinstance(value, dict): return {k: canonical(v) for k, v in value.items()}
        if isinstance(value, list): return [canonical(v) for v in value]
        return aliases.get(value, value) if isinstance(value, str) else value
    pre = canonical(pre_release_facts(profile))
    fingerprint = 'aa'*32
    worker = dict(schemaVersion='hmbc-worker-log/v0', adapterMode='symbolic',
                  deploymentFingerprint=fingerprint, note='synthetic; delivery unknown',
                  events=[], releases=[], counts=dict(releaseIntentCount='0', releaseSentCount='0'))
    pre['before']['worker'] = copy.deepcopy(worker)
    pre['after']['worker'] = copy.deepcopy(worker)
    identity = dict(requestDigest=aliases['digest'], grantId=aliases['grant'],
                    gid=aliases['bob'], dataId=aliases['record'])
    recipient, ciphertext, token = ['0x'+b*32 for b in ('77', '88', '99')]
    response = dict(schemaVersion='v1', adapterMode='symbolic',
                    **{k: identity[k] for k in ('requestDigest', 'grantId', 'dataId')},
                    recipientKeyHash=recipient, ciphertextDigest=ciphertext, keyEpoch='0',
                    responseEnvelope=dict(kind='symbolic-partial/v1', token=token))
    worker['events'] = [dict(type=t, timestamp='111', **identity) for t in ('RELEASE_INTENT', 'RELEASE_SENT')]
    worker['releases'] = [dict(**identity, recipientKeyHash=recipient, ciphertextDigest=ciphertext,
                             keyEpoch='0', tokenDigest='0x'+keccak(bytes.fromhex(token[2:])).hex(),
                             grantExpiresAt='140', createdAt='111', delivery='unknown',
                             sendAttempts=1, completedAttempts=1)]
    worker['counts'] = dict(releaseIntentCount='1', releaseSentCount='1')
    after = copy.deepcopy(pre['after']); after['worker'] = worker
    bob = dict(schemaVersion='v1', ok=True, error=None,
               result=dict(schemaVersion='v1', adapterMode='symbolic', decryptable=True,
                           dataId=aliases['record'], ciphertextDigest=ciphertext))
    alice = dict(schemaVersion='v1', ok=False, result=None,
                 error=dict(code='WRONG_SUBJECT', message='synthetic wrong recipient'))
    return dict(pre_release=pre, registered_recipient=recipient,
                original_recipient=aliases['alice-key'], ciphertext_digest=ciphertext,
                response=response, bob_completion=bob, alice_completion=alice,
                after_release=after, after_completion=copy.deepcopy(after),
                dbc_now='112', fingerprint=fingerprint)


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal'])
def test_paper_subject_response_routes_to_bob_and_refuses_alice(profile):
    result = oracle()(**facts(profile))
    assert result['ok'] and result['classification'] == 'SPEC_GAP'
    assert result['delivery'] == 'unknown' and result['adapterMode'] == 'symbolic'
    assert result['bobDecryptable'] and result['aliceError'] == 'WRONG_SUBJECT'
    assert result['outcomeTested'] is False and result['integratedCaseComplete'] is False


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal'])
@pytest.mark.parametrize('mutation', [
    'pre-subject', 'native-recipient', 'original-recipient', 'unregistered', 'same-key',
    'response-recipient', 'response-digest', 'response-grant', 'response-data',
    'response-ciphertext', 'response-epoch', 'response-mode', 'response-token',
    'cache-gid', 'cache-expiry', 'cache-ciphertext', 'cache-token', 'cache-delivery',
    'cache-time', 'event-time', 'event-expired', 'event-gid', 'extra-send',
    'incomplete-send', 'prior-worker', 'fingerprint', 'clock-expired', 'clock-before-send',
    'ledger-grant', 'ledger-nonce', 'ledger-request', 'ledger-history', 'ledger-count',
    'bob-denied', 'bob-data', 'bob-ciphertext', 'bob-false', 'bob-mode',
    'alice-allowed', 'alice-error', 'completion-worker', 'completion-native',
])
def test_subject_completion_rejects_false_bindings_and_state(profile, mutation):
    d = facts(profile); row = d['after_release']['worker']['releases'][0]
    if mutation == 'pre-subject': d['pre_release']['submitted_arguments'][0]['gid'] = d['pre_release']['original_request']['gid']
    if mutation == 'native-recipient': d['pre_release']['after']['grant']['recipientKeyHash'] = d['registered_recipient']
    if mutation == 'original-recipient': d['original_recipient'] = '0x'+'aa'*32
    if mutation == 'unregistered': d['registered_recipient'] = '0x'+'00'*32
    if mutation == 'same-key': d['registered_recipient'] = d['original_recipient']
    if mutation.startswith('response-'):
        key = {'recipient': 'recipientKeyHash', 'digest': 'requestDigest', 'grant': 'grantId',
               'data': 'dataId', 'ciphertext': 'ciphertextDigest', 'epoch': 'keyEpoch',
               'mode': 'adapterMode', 'token': 'responseEnvelope'}[mutation[9:]]
        d['response'][key] = ({'kind': 'symbolic-partial/v1', 'token': '0x'+'ab'*32} if key == 'responseEnvelope'
                              else '1' if key == 'keyEpoch' else 'abe-real' if key == 'adapterMode' else '0x'+'ab'*32)
    if mutation == 'cache-gid': row['gid'] = d['pre_release']['original_request']['gid']
    if mutation == 'cache-expiry': row['grantExpiresAt'] = '150'
    if mutation == 'cache-ciphertext': row['ciphertextDigest'] = '0x'+'ab'*32
    if mutation == 'cache-token': row['tokenDigest'] = '0x'+'ab'*32
    if mutation == 'cache-delivery': row['delivery'] = 'delivered'
    if mutation == 'cache-time':
        row['createdAt'] = '109'
        for e in d['after_release']['worker']['events']: e['timestamp'] = '109'
    if mutation == 'event-time': d['after_release']['worker']['events'][1]['timestamp'] = '113'
    if mutation == 'event-expired': d['after_release']['worker']['events'][1]['timestamp'] = '140'
    if mutation == 'event-gid': d['after_release']['worker']['events'][1]['gid'] = d['pre_release']['original_request']['gid']
    if mutation == 'extra-send':
        w = d['after_release']['worker']; w['events'].append(copy.deepcopy(w['events'][1])); row['sendAttempts'] = 2; w['counts']['releaseSentCount'] = '2'
    if mutation == 'incomplete-send': row['completedAttempts'] = 0
    if mutation == 'prior-worker':
        for state in (d['pre_release']['before'], d['pre_release']['after']): state['worker'] = copy.deepcopy(d['after_release']['worker'])
    if mutation == 'fingerprint': d['fingerprint'] = 'bb'*32
    if mutation == 'clock-expired': d['dbc_now'] = '140'
    if mutation == 'clock-before-send': d['dbc_now'] = '110'
    if mutation == 'ledger-grant': d['after_release']['grant']['gid'] = d['pre_release']['original_request']['gid']
    if mutation == 'ledger-nonce': d['after_release']['nonceBob'] = True
    if mutation == 'ledger-request': d['after_release']['request']['status'] = '2'
    if mutation == 'ledger-history': d['after_release']['logs']['pbc'].append({'name': 'OutcomeRecorded'})
    if mutation == 'ledger-count': d['after_release']['accessLogCount'] = '2'
    if mutation == 'bob-denied': d['bob_completion'] = copy.deepcopy(d['alice_completion'])
    if mutation == 'bob-data': d['bob_completion']['result']['dataId'] = '0x'+'ab'*32
    if mutation == 'bob-ciphertext': d['bob_completion']['result']['ciphertextDigest'] = '0x'+'ab'*32
    if mutation == 'bob-false': d['bob_completion']['result']['decryptable'] = False
    if mutation == 'bob-mode': d['bob_completion']['result']['adapterMode'] = 'abe-real'
    if mutation == 'alice-allowed': d['alice_completion'] = copy.deepcopy(d['bob_completion'])
    if mutation == 'alice-error': d['alice_completion']['error']['code'] = 'EXPIRED'
    if mutation == 'completion-worker': d['after_completion']['worker']['note'] += ' changed'
    if mutation == 'completion-native': d['after_completion']['request']['outcomeLogId'] = '8'
    # Match post-completion with a falsified release snapshot for release-specific
    # controls, so equality alone cannot mask a missing native/worker join.
    if not mutation.startswith('completion-'): d['after_completion'] = copy.deepcopy(d['after_release'])
    with pytest.raises(ValueError): oracle()(**d)


def test_completion_oracle_does_not_accept_repaired_grant_denial_as_release():
    d = facts(); d['pre_release']['profile'] = 'repaired-e'
    with pytest.raises(ValueError): oracle()(**d)
