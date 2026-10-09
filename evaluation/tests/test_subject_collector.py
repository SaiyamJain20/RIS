"""Synthetic RPC sensitivity for the pre-release collector; no live gate evidence.

Missing transaction/signature/block joins or an accidental legitimate release
must fail these tests. Real ABI encoding, signatures, read groups and the oracle
run on controlled native inputs.
"""
import json
from types import SimpleNamespace

import pytest
from eth_utils import keccak

from evaluation.access_execution import execute_access
from evaluation.chain import PublicChain
from evaluation.evm import _decode
from evaluation.native import NativeReceipt
from evaluation.tests.test_access_artifacts import artifacts
from evaluation.tests.test_bootstrap import inputs
from evaluation.tests.test_access_execution import Model


def fixture(artifacts, inputs, tmp_path, profile, mutation):
    m = Model(artifacts, inputs, profile)
    histories = {'pbc': [], 'dbc': []}; transactions = {}
    for label, chain in [('pbc', m.pbc), ('dbc', m.dbc)]:
        submit, call = chain.submit, chain.call
        def wrapped_submit(signer, role, method, *args, expect_success=True,
                           chain=chain, label=label, submit=submit):
            if method == 'consumeDecision':
                chain.number += 1; block = chain.latest_block(); tx = '0x'+'aa'*32
                receipt = dict(status='0x0', transactionHash=tx, blockHash=block['hash'],
                    blockNumber=block['number'], transactionIndex='0x0', gasUsed='0x1234', logs=[])
                native = NativeReceipt(receipt=receipt, transaction=dict(hash=tx, chainId=hex(int(chain.chain_id)),
                    blockHash=block['hash'], blockNumber=block['number'], transactionIndex='0x0'),
                    block=dict(block, transactions=[tx]), chain_id=chain.chain_id)
            elif method == 'policyEnf':
                original = m.req
                m.req = dict(original, gid=args[0]['gid'])
                try: native = submit(signer, role, method, *args)
                finally: m.req = original
            else:
                native = submit(signer, role, method, *args)
            histories[label].extend(native.receipt['logs'])
            tx = dict(hash=native.receipt['transactionHash'], input=chain.contracts[role].calldata(method, *args),
                      to=chain.contracts[role].address, **{'from': m.dep['fixture']['relay']['address']},
                      blockNumber=hex(int(native.block_number)), blockHash=native.block_hash)
            if method in ('policyEnf', 'consumeDecision'):
                if mutation == 'wrong-relay': tx['from'] = '0x'+'bb'*20
                if mutation == 'wrong-calldata': tx['input'] += '00'
                if mutation == 'wrong-block': tx['blockHash'] = '0x'+'bb'*32
            if method == 'requestAccess' and mutation == 'original-call': tx['input'] += '00'
            if method == 'requestAccess' and mutation == 'original-bundle':
                other_bundle = m.users['bob']['bundle']
                tx['input'] = chain.contracts[role].calldata(method, args[0], args[1], other_bundle)
            transactions[(label, tx['hash'])] = tx
            return native
        def wrapped_call(method, args=None, chain=chain, label=label, call=call):
            if method == 'eth_getLogs': return histories[label]
            if method == 'eth_getTransactionByHash': return transactions.get((label, args[0]))
            if method == 'eth_chainId': return hex(int(chain.chain_id))
            if method == 'eth_getBlockByNumber' and args[0] == 'latest': return chain.latest_block()
            if method == 'eth_call':
                tx, number = args
                c = next(c for c in chain.contracts.values() if c.address == tx['to'])
                f = next(f for f in c.abi if f['type'] == 'function'
                         and '0x'+keccak(text=c._signature(f))[:4].hex() == tx['data'][:10])
                values = _decode(f['inputs'], bytes.fromhex(tx['data'][10:]))
                return chain.observe(next(r for r,v in chain.contracts.items() if v is c),
                                     f['name'], *values, block=call('eth_getBlockByNumber', [number, False]))['returnData']
            return call(method, args)
        chain.submit = wrapped_submit; chain.call = wrapped_call
        reader = PublicChain(SimpleNamespace(call=wrapped_call), chain_id=chain.chain_id,
                             contracts=chain.contracts, output=tmp_path/(label+'-views'))
        chain.read_group = reader.read_group
    m.dbc.rejection_code = lambda native: '3' if mutation == 'wrong-code' else '2'
    # The base E1 model has one nonce bit; paper stress consumes neither, and
    # the repaired rejection also leaves both false.
    return m


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal', 'repaired-e'])
def test_pre_release_subject_collector_preserves_original_request_and_stops_before_release(artifacts, inputs, tmp_path, profile):
    m = fixture(artifacts, inputs, tmp_path, profile, None)
    result = execute_access(m.pbc, m.dbc, m, deployment_bytes=json.dumps(m.dep).encode(),
        user_label='alice', user=m.users['alice'], record=m.record, policy=m.policy, expected_allow=True,
        worker_snapshot=m.snapshot, output=tmp_path/'access', subject_substitution=m.users['bob']['gid'])
    proof = json.loads((tmp_path/'access/subject-substitution/result.json').read_text())
    assert result['ok'] and proof['ok'] and proof['releaseTested'] is False
    assert proof['classification'] == ('REPAIR_SUPPORTED' if profile == 'repaired-e' else 'SPEC_GAP')
    assert not any(op in m.calls for op in ('release', 'finish_decryption', 'attest_grant'))
    assert m.request_state['gid'] == m.users['alice']['gid'] and m.request_state['status'] == '1'
    assert m.grant['exists'] is (profile != 'repaired-e')
    if profile != 'repaired-e': assert m.grant['gid'] == m.users['bob']['gid']
    anchors = json.loads((tmp_path/'access/subject-substitution/before-blocks.json').read_text())
    assert set(anchors) == {'pbc', 'dbc'}


@pytest.mark.parametrize('mutation', ['wrong-relay', 'wrong-calldata', 'wrong-block', 'original-call', 'original-bundle'])
@pytest.mark.parametrize('profile', ['paper-strict', 'repaired-e'])
def test_subject_collector_refuses_unbound_native_transactions(artifacts, inputs, tmp_path, profile, mutation):
    m = fixture(artifacts, inputs, tmp_path, profile, mutation)
    with pytest.raises(ValueError):
        execute_access(m.pbc, m.dbc, m, deployment_bytes=json.dumps(m.dep).encode(),
            user_label='alice', user=m.users['alice'], record=m.record, policy=m.policy, expected_allow=True,
            worker_snapshot=m.snapshot, output=tmp_path/'access', subject_substitution=m.users['bob']['gid'])


def test_subject_collector_refuses_wrong_repaired_rejection_code(artifacts, inputs, tmp_path):
    m = fixture(artifacts, inputs, tmp_path, 'repaired-e', 'wrong-code')
    with pytest.raises(ValueError):
        execute_access(m.pbc, m.dbc, m, deployment_bytes=json.dumps(m.dep).encode(),
            user_label='alice', user=m.users['alice'], record=m.record, policy=m.policy, expected_allow=True,
            worker_snapshot=m.snapshot, output=tmp_path/'access', subject_substitution=m.users['bob']['gid'])


@pytest.mark.parametrize('selection', ['same-gid', 'bob-control', 'crash', 'nonce-replay', 'duplicate', 'bad-address'])
def test_subject_selection_refuses_before_any_request_or_worker_side_effect(artifacts, inputs, tmp_path, selection):
    m = fixture(artifacts, inputs, tmp_path, 'paper-strict', None)
    label = 'bob' if selection == 'bob-control' else 'alice'
    options = dict(subject_substitution=m.users['alice' if selection == 'same-gid' else 'bob']['gid'])
    if selection == 'crash': options['recovery_point'] = 'after_intent'
    if selection == 'nonce-replay': options['nonce_replay'] = True
    if selection == 'duplicate': options['duplicate_outcome'] = True
    if selection == 'bad-address': options['subject_substitution'] = 'not-an-address'
    with pytest.raises(ValueError):
        execute_access(m.pbc, m.dbc, m, deployment_bytes=json.dumps(m.dep).encode(),
            user_label=label, user=m.users[label], record=m.record, policy=m.policy, expected_allow=label == 'alice',
            worker_snapshot=m.snapshot, output=tmp_path/'access', **options)
    assert m.request_state == {'status': '0'} and m.calls == []
