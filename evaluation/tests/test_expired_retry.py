"""Expiry refusal must preserve the recovered cache and all native evidence.

Synthetic facts only. Mutations name false success, premature probes, renewed
permission, new events and changed cache/attempts that the independent join must reject.
"""
import copy
import importlib
import json

import pytest
from evaluation.tests.test_recovery import examples
from evaluation.tests.test_access_artifacts import artifacts
from evaluation.tests.test_bootstrap import inputs
from evaluation.tests.test_recovery_execution import RecoveryModel


def facts():
    data = examples('after_send')
    pending = dict(status='2', grantId=data['grant_id'])
    return dict(before=data['after'], after=copy.deepcopy(data['after']),
                response=dict(schemaVersion='v1', ok=False, result=None,
                              error=dict(code='EXPIRED', message='Expired grant')),
                grant_before=data['grant'], grant_after=copy.deepcopy(data['grant']),
                pending_before=pending, pending_after=copy.deepcopy(pending),
                grant_id=data['grant_id'], fingerprint=data['fingerprint'], dbc_now='130',
                logs_before={'pbc': [], 'dbc': []}, logs_after={'pbc': [], 'dbc': []})


def check(data):
    assert importlib.util.find_spec('evaluation.expired_retry') is not None, 'Expired-retry collector missing'
    return importlib.import_module('evaluation.expired_retry').check_expired_retry(**data)


@pytest.mark.parametrize('clock', ['130', '131'])
def test_expired_retry_refuses_at_or_after_original_expiry_without_changes(clock):
    data = facts(); data['dbc_now'] = clock
    proof = check(data)
    assert proof['ok'] and proof['error'] == 'EXPIRED'
    assert proof['originalExpiry'] == '130' and proof['delivery'] == 'unknown'


@pytest.mark.parametrize('change', ['premature', 'false-success', 'wrong-error', 'retryable',
                                  'cache-token', 'attempt', 'new-send', 'renewed-grant',
                                  'changed-outcome', 'pbc-event', 'dbc-event', 'no-cache'])
def test_false_expired_refusal_evidence_is_rejected(change):
    data = facts()
    if change == 'premature': data['dbc_now'] = '129'
    if change == 'false-success': data['response'].update(ok=True, error=None, result={})
    if change == 'wrong-error': data['response']['error']['code'] = 'POLICY_DENIED'
    if change == 'retryable': data['response']['error']['retryable'] = True
    if change == 'cache-token': data['after']['releases'][0]['tokenDigest'] = '0x'+'77'*32
    if change == 'attempt': data['after']['releases'][0]['sendAttempts'] += 1
    if change == 'new-send':
        data['after']['events'].append(dict(data['after']['events'][-1], timestamp='130'))
        data['after']['releases'][0]['sendAttempts'] += 1
        data['after']['counts']['releaseSentCount'] = '3'
    if change == 'renewed-grant': data['grant_after']['expiresAt'] = '160'
    if change == 'changed-outcome': data['pending_after']['status'] = '1'
    if change == 'pbc-event': data['logs_after']['pbc'].append({'event': 'new'})
    if change == 'dbc-event': data['logs_after']['dbc'].append({'event': 'new'})
    if change == 'no-cache': data['before']['releases'] = []
    with pytest.raises(ValueError): check(data)


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal', 'repaired-e'])
@pytest.mark.parametrize('point', ['after_intent', 'after_send'])
def test_public_expiry_probe_after_real_collector_recovery(artifacts, inputs, tmp_path, profile, point):
    m = RecoveryModel(artifacts, inputs, profile)
    from evaluation.recovery_execution import RecoveryAdapter
    from evaluation.access_execution import execute_access
    session = RecoveryAdapter(m, restart=m.restart, point=point, pbc=m.pbc, dbc=m.dbc,
                              deployment=m.dep, worker_snapshot=m.snapshot, output=tmp_path/'recovery')
    result = execute_access(m.pbc, m.dbc, session, deployment_bytes=json.dumps(m.dep).encode(),
                            user_label='alice', user=m.users['alice'], record=m.record, policy=m.policy,
                            expected_allow=True, worker_snapshot=m.snapshot, output=tmp_path/'access', recovery_point=point)
    gid = next(e['grantId'] for e in result['observed']['events'] if e['type'] == 'DBC_AUTHORIZED')
    old_exchange = m.exchange
    clock = int(m.grant['expiresAt'])-1
    expired = False

    class ClockRpc:
        def call(self, method, args=None):
            nonlocal clock, expired
            if method == 'evm_setNextBlockTimestamp':
                assert args == [int(m.grant['expiresAt'])]
                clock = args[0]; return None
            if method == 'evm_mine':
                expired = True; return '0x0'
            if method == 'eth_getBlockByNumber': return dict(timestamp=hex(clock))
            if method == 'eth_getLogs':
                assert args[0]['fromBlock'] == '0x0' and args[0]['toBlock'] == 'latest'
                assert len(args[0]['address']) > 0
                return []
            raise AssertionError(method)

    def exchange(request):
        if expired and request['operation'] == 'release':
            assert request == dict(schemaVersion='v1', operation='release', input=dict(grantId=gid), deploymentManifest=m.dep)
            return dict(schemaVersion='v1', ok=False, result=None, error=dict(code='EXPIRED', message='Expired grant'))
        return old_exchange(request)

    m.exchange = exchange
    m.dbc.rpc = ClockRpc(); m.pbc.rpc = ClockRpc()
    old_latest = m.dbc.latest_block
    m.dbc.latest_block = lambda: dict(old_latest(), timestamp=hex(clock))
    before = m.snapshot()
    mod = importlib.import_module('evaluation.expired_retry')
    assert hasattr(mod, 'execute_expired_retry'), 'Public expiry-probe execution missing'
    proof = mod.execute_expired_retry(m.pbc, m.dbc, session, deployment=m.dep,
                                     grant_id=gid, worker_snapshot=m.snapshot, output=tmp_path/'expired')
    assert proof['ok'] and proof['error'] == 'EXPIRED' and proof['workerUnchanged']
    assert m.snapshot() == before and m.restarts == 1
    assert json.loads((tmp_path/'expired/result.json').read_text())['ok']
