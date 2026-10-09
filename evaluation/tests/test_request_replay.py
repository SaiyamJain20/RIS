"""Replay evidence sensitivity; synthetic observations are not integrated trials.

Deleting any positive join, transaction binding or no-change check must accept
the corresponding false-evidence fixture below and fail this test.
"""
import copy
import importlib

import pytest


def oracle():
    assert importlib.util.find_spec('evaluation.oracles.replay') is not None, 'E01 replay oracle missing'
    return importlib.import_module('evaluation.oracles.replay').check_request_replay


def facts(profile='paper-strict'):
    state = dict(request=dict(status='1', requestLogId='7', outcomeLogId='0',
                              gid='alice', dataId='record', expiresAt='130'),
                 grant=dict(exists=True, allowed=True, requestDigest='digest', gid='alice',
                            dataId='record', issuedAt='100', expiresAt='120'),
                 nonceConsumed=profile == 'repaired-e', accessLogCount='1',
                 logs=dict(pbc=[{'request': 'one'}], dbc=[{'grant': 'one'}]),
                 worker=dict(events=[], releases=[]))
    original = dict(hash='tx-original', input='exact-call', to='acsc', **{'from': 'relay'}, nonce='0x1')
    replay = dict(original, hash='tx-replay', nonce='0x2')
    return dict(profile=profile, request_digest='digest', gid='alice', data_id='record',
                before=state, after=copy.deepcopy(state), original_transaction=original,
                replay_transaction=replay, rejection_code='8', success=False,
                receipt_logs=[], original_grants=1, replay_timestamp='110')


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal', 'repaired-e'])
def test_replay_requires_prior_allowed_grant_and_identical_fresh_transaction(profile):
    proof = oracle()(**facts(profile))
    assert proof['ok'] is True and proof['error'] == 'REPLAY'
    assert proof['classification'] == ('REPAIR_SUPPORTED' if profile == 'repaired-e' else 'SUPPORTED')
    assert proof['delivery'] == 'unknown' and proof['nativeUnchanged'] and proof['workerUnchanged']


@pytest.mark.parametrize('mutation', [
    'no-positive', 'two-grants', 'denied', 'no-grant', 'wrong-digest', 'wrong-gid',
    'wrong-data', 'unlogged', 'not-forwarded', 'nonce', 'success', 'wrong-code',
    'receipt-event', 'new-grant', 'request-state', 'worker', 'pbc-log', 'dbc-log',
    'access-count', 'same-hash', 'same-nonce', 'lower-nonce', 'changed-call',
    'wrong-caller', 'wrong-destination', 'expired', 'before-grant', 'missing-chain',
    'empty-grant-log', 'unknown-profile',
])
def test_replay_oracle_rejects_false_evidence(mutation):
    data = facts()
    if mutation == 'no-positive': data['original_grants'] = 0
    if mutation == 'two-grants': data['original_grants'] = 2
    if mutation == 'denied': data['before']['grant']['allowed'] = False
    if mutation == 'no-grant': data['before']['grant']['exists'] = False
    if mutation == 'wrong-digest': data['before']['grant']['requestDigest'] = 'other'
    if mutation == 'wrong-gid': data['before']['grant']['gid'] = 'bob'
    if mutation == 'wrong-data': data['before']['request']['dataId'] = 'other'
    if mutation == 'unlogged': data['before']['request']['requestLogId'] = '0'
    if mutation == 'not-forwarded': data['before']['request']['status'] = '0'
    if mutation == 'nonce': data['before']['nonceConsumed'] = True
    if mutation == 'success': data['success'] = True
    if mutation == 'wrong-code': data['rejection_code'] = '6'
    if mutation == 'receipt-event': data['receipt_logs'] = [{'event': 'new-grant'}]
    if mutation == 'new-grant': data['after']['grant']['expiresAt'] = '140'
    if mutation == 'request-state': data['after']['request']['outcomeLogId'] = '8'
    if mutation == 'worker': data['after']['worker']['events'].append('RELEASE_INTENT')
    if mutation == 'pbc-log': data['after']['logs']['pbc'].append({'request': 'two'})
    if mutation == 'dbc-log': data['after']['logs']['dbc'].append({'grant': 'two'})
    if mutation == 'access-count': data['after']['accessLogCount'] = '2'
    if mutation == 'same-hash': data['replay_transaction']['hash'] = 'tx-original'
    if mutation == 'same-nonce': data['replay_transaction']['nonce'] = '0x1'
    if mutation == 'lower-nonce': data['replay_transaction']['nonce'] = '0x0'
    if mutation == 'changed-call': data['replay_transaction']['input'] = 'other-call'
    if mutation == 'wrong-caller': data['replay_transaction']['from'] = 'other-relay'
    if mutation == 'wrong-destination': data['replay_transaction']['to'] = 'other-acsc'
    if mutation == 'expired': data['replay_timestamp'] = '120'
    if mutation == 'before-grant': data['replay_timestamp'] = '99'
    if mutation == 'missing-chain': data['before']['logs'].pop('pbc')
    if mutation == 'empty-grant-log': data['before']['logs']['dbc'] = []
    if mutation == 'unknown-profile': data['profile'] = 'mutant-no-nonce'
    with pytest.raises(ValueError): oracle()(**data)


def test_repaired_replay_requires_already_consumed_nonce():
    data = facts('repaired-e')
    data['before']['nonceConsumed'] = False
    with pytest.raises(ValueError): oracle()(**data)


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal', 'repaired-e'])
@pytest.mark.parametrize('transaction_mutation', ['none', 'changed-call', 'same-nonce', 'wrong-relay'])
def test_public_replay_probe_checks_mined_call_before_worker_release(artifacts, inputs, tmp_path, profile, transaction_mutation):
    import json
    from evaluation.native import NativeReceipt
    from evaluation.tests.test_access_execution import Model
    from evaluation.access_execution import execute_access
    m = Model(artifacts, inputs, profile)
    logs = {'pbc': [], 'dbc': []}; grants = []
    for label, chain in [('pbc', m.pbc), ('dbc', m.dbc)]:
        submit = chain.submit; call = chain.call
        def wrapped_submit(signer, role, method, *args, expect_success=True, chain=chain, label=label, submit=submit):
            if expect_success:
                native = submit(signer, role, method, *args)
                logs[label].extend(native.receipt['logs'])
                if method in ('policyEnf', 'consumeDecision'): grants.append((method, copy.deepcopy(args), native))
                return native
            assert label == 'dbc' and (method, args) == grants[0][:2]
            assert m.request_state['status'] == '1' and m.snapshot()  # exporter remains usable before release
            n = grants[0][2]
            receipt = dict(n.receipt, status='0x0', logs=[], transactionHash='0x'+'aa'*32)
            return NativeReceipt(receipt=receipt, transaction=dict(hash=receipt['transactionHash'], chainId=hex(int(chain.chain_id)),
                                  blockHash=n.block_hash, blockNumber=hex(int(n.block_number)), transactionIndex='0x0'),
                                 block=dict(hash=n.block_hash, number=hex(int(n.block_number)), timestamp=hex(int(n.timestamp)),
                                            transactions=[receipt['transactionHash']]), chain_id=chain.chain_id)
        def wrapped_call(method, args=None, chain=chain, label=label, call=call):
            if method == 'eth_getLogs': return logs[label]
            if method == 'eth_getTransactionByHash':
                name, arguments, native = grants[0]
                duplicate = args[0] != native.receipt['transactionHash']
                data = dict(hash=args[0], input=chain.contracts['ACSC'].calldata(name, *arguments),
                            to=chain.contracts['ACSC'].address, **{'from': m.dep['fixture']['relay']['address']},
                            nonce='0x2' if duplicate else '0x1')
                if duplicate and transaction_mutation == 'changed-call': data['input'] += '00'
                if duplicate and transaction_mutation == 'same-nonce': data['nonce'] = '0x1'
                if duplicate and transaction_mutation == 'wrong-relay': data['from'] = '0x'+'bb'*20
                return data
            return call(method, args)
        chain.submit = wrapped_submit; chain.call = wrapped_call
    # Exercise the production grouped reader against model ABI/RPC inputs.
    from evaluation.chain import PublicChain
    from evaluation.evm import _decode
    from types import SimpleNamespace
    for chain, label in ((m.pbc, 'pbc'), (m.dbc, 'dbc')):
        old_call = chain.call
        def grouped_rpc(method, params=None, chain=chain, old_call=old_call):
            if method == 'eth_chainId': return hex(int(chain.chain_id))
            if method == 'eth_getBlockByNumber' and params[0] == 'latest': return chain.latest_block()
            if method == 'eth_call':
                tx, number = params
                c = next(c for c in chain.contracts.values() if c.address == tx['to'])
                f = next(f for f in c.abi if f['type'] == 'function'
                         and '0x'+__import__('eth_utils').keccak(text=c._signature(f))[:4].hex() == tx['data'][:10])
                args = _decode(f['inputs'], bytes.fromhex(tx['data'][10:]))
                block = old_call('eth_getBlockByNumber', [number, False])
                return chain.observe(next(r for r,candidate in chain.contracts.items() if candidate is c),
                                     f['name'], *args, block=block)['returnData']
            return old_call(method, params)
        reader = PublicChain(SimpleNamespace(call=grouped_rpc), chain_id=chain.chain_id,
                             contracts=chain.contracts, output=tmp_path/(label+'-views'))
        chain.read_group = reader.read_group
    m.dbc.rejection_code = lambda native: '8'
    kwargs = dict(deployment_bytes=json.dumps(m.dep).encode(), user_label='alice', user=m.users['alice'],
                  record=m.record, policy=m.policy, expected_allow=True, worker_snapshot=m.snapshot,
                  output=tmp_path/'access', nonce_replay=True)
    if transaction_mutation != 'none':
        with pytest.raises(ValueError): execute_access(m.pbc, m.dbc, m, **kwargs)
        return
    result = execute_access(m.pbc, m.dbc, m, **kwargs)
    proof = json.loads((tmp_path/'access/nonce-replay/result.json').read_text())
    anchors = json.loads((tmp_path/'access/nonce-replay/before-blocks.json').read_text())
    assert set(anchors) == {'pbc', 'dbc'}
    assert all(anchor['number'].startswith('0x') for anchor in anchors.values())
    assert result['ok'] and proof['ok'] and proof['identicalCalldata'] and proof['error'] == 'REPLAY'
    assert proof['classification'] == ('REPAIR_SUPPORTED' if profile == 'repaired-e' else 'SUPPORTED')


from evaluation.tests.test_access_artifacts import artifacts
from evaluation.tests.test_bootstrap import inputs
