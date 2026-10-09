"""Synthetic sensitivity of the SL1 paper subject completion collector.

Controlled RPC/adapter doubles only; no services and no live catalog result.
The release must route the substituted grant to the registered target key, the
same response must decrypt for the target and be refused for the original
subject, and nothing may report an outcome or change native state.
"""
import json

import pytest
from eth_utils import keccak

from evaluation.access_execution import execute_access
from evaluation.tests.test_access_artifacts import artifacts
from evaluation.tests.test_access_execution import NOW
from evaluation.tests.test_bootstrap import inputs
from evaluation.tests.test_subject_collector import fixture

ZERO = '0x'+'00'*32


def key(label):
    return '0x'+keccak(text='HMBC.recipient-key.'+label).hex()


def subject_model(artifacts, inputs, tmp_path, profile, control=None):
    m = fixture(artifacts, inputs, tmp_path, profile, None)
    original = m.exchange

    def exchange(envelope):
        op, inp = envelope['operation'], envelope['input']
        if op == 'release':
            m.calls.append(op)
            grant = m.grant; target = 'alice' if control == 'route-original' else 'bob'
            identity = dict(requestDigest=m.digest, grantId=m.gid, gid=grant['gid'], dataId=m.req['dataId'])
            if control == 'cache-gid': identity['gid'] = m.req['gid']
            m.worker_events = [dict(type=t, timestamp=str(NOW), **identity) for t in ('RELEASE_INTENT', 'RELEASE_SENT')]
            if control == 'extra-send': m.worker_events.append(dict(type='RELEASE_SENT', timestamp=str(NOW), **identity))
            m.releases = [dict(**identity, ciphertextDigest=m.cipher, recipientKeyHash=key(target), keyEpoch='0',
                               tokenDigest='0x290decd9548b62a8d60345a988386fc84ba6bc95484008f6362f93160ef3e563',
                               grantExpiresAt=grant['expiresAt'], createdAt=str(NOW), delivery='unknown',
                               sendAttempts=1, completedAttempts=1)]
            result = dict(schemaVersion='v1', adapterMode='symbolic', requestDigest=m.digest, grantId=m.gid,
                          dataId=m.req['dataId'], ciphertextDigest=m.cipher, recipientKeyHash=key(target), keyEpoch='0',
                          responseEnvelope=dict(kind='symbolic-partial/v1', token=ZERO))
            return dict(schemaVersion='v1', ok=True, result=result, error=None)
        if op == 'finish_decryption':
            m.calls.append(op)
            label = inp['userKeyRef'].split(':')[-1]
            allowed = inp['response']['recipientKeyHash'] == key(label)
            if control == 'original-decrypts': allowed = True
            if control == 'target-refused' and label == 'bob': allowed = False
            if control == 'completion-worker': m.worker_events = m.worker_events+[dict(m.worker_events[-1])]
            if allowed:
                return dict(schemaVersion='v1', ok=True, error=None,
                            result=dict(schemaVersion='v1', adapterMode='symbolic', decryptable=True,
                                        dataId=m.req['dataId'], ciphertextDigest=m.cipher))
            return dict(schemaVersion='v1', ok=False, result=None,
                        error=dict(code='WRONG_SUBJECT', message='synthetic wrong recipient'))
        return original(envelope)

    m.exchange = exchange
    return m


def run(m, tmp_path, **options):
    return execute_access(m.pbc, m.dbc, m, deployment_bytes=json.dumps(m.dep).encode(),
        user_label='alice', user=m.users['alice'], record=m.record, policy=m.policy, expected_allow=True,
        worker_snapshot=m.snapshot, output=tmp_path/'access', subject_substitution=m.users['bob']['gid'], **options)


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal'])
def test_paper_completion_routes_to_target_and_refuses_original_without_outcome(artifacts, inputs, tmp_path, profile):
    m = subject_model(artifacts, inputs, tmp_path, profile)
    result = run(m, tmp_path, subject_completion=True)
    proof = json.loads((tmp_path/'access/subject-completion/result.json').read_text())
    assert result['ok'] and proof['ok'] and proof['classification'] == 'SPEC_GAP'
    assert proof['bobDecryptable'] is True and proof['aliceError'] == 'WRONG_SUBJECT' and proof['delivery'] == 'unknown'
    assert proof['targetCompletion'] == dict(ok=True, decryptable=True)
    assert proof['originalCompletion'] == dict(ok=False, error='WRONG_SUBJECT')
    assert m.calls.count('release') == 1 and m.calls.count('finish_decryption') == 2
    assert 'attest_grant' not in m.calls and m.request_state['status'] == '1'
    exchanges = (tmp_path/'access/exchanges.json').read_text()
    assert '"token"' not in exchanges
    for name in ('after-release', 'after-completion', 'recipients'):
        assert (tmp_path/'access/subject-completion'/(name+'.json')).is_file()


@pytest.mark.parametrize('control', ['route-original', 'cache-gid', 'extra-send', 'original-decrypts',
                                     'target-refused', 'completion-worker'])
def test_false_routing_completion_or_worker_delta_cannot_pass(artifacts, inputs, tmp_path, control):
    m = subject_model(artifacts, inputs, tmp_path, 'paper-strict', control)
    with pytest.raises(ValueError):
        run(m, tmp_path, subject_completion=True)


def test_repaired_completion_is_refused_before_any_side_effect(artifacts, inputs, tmp_path):
    m = subject_model(artifacts, inputs, tmp_path, 'repaired-e')
    with pytest.raises(ValueError):
        run(m, tmp_path, subject_completion=True)
    assert m.calls == [] and m.request_state == {'status': '0'}


@pytest.mark.parametrize('value', ['yes', 1])
def test_completion_flag_must_be_explicit_boolean(artifacts, inputs, tmp_path, value):
    m = subject_model(artifacts, inputs, tmp_path, 'paper-strict')
    with pytest.raises(ValueError):
        run(m, tmp_path, subject_completion=value)
    assert m.calls == []


def test_completion_requires_subject_stress(artifacts, inputs, tmp_path):
    m = subject_model(artifacts, inputs, tmp_path, 'paper-strict')
    with pytest.raises(ValueError):
        execute_access(m.pbc, m.dbc, m, deployment_bytes=json.dumps(m.dep).encode(), user_label='alice',
                       user=m.users['alice'], record=m.record, policy=m.policy, expected_allow=True,
                       worker_snapshot=m.snapshot, output=tmp_path/'access', subject_completion=True)
    assert m.calls == []


def test_pre_release_stage_alone_still_never_releases(artifacts, inputs, tmp_path):
    m = subject_model(artifacts, inputs, tmp_path, 'paper-minimal')
    result = run(m, tmp_path)
    assert result['ok'] and 'subjectCompletion' not in result
    assert 'release' not in m.calls and 'finish_decryption' not in m.calls
