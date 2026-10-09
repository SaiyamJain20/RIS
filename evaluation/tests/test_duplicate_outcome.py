"""Independent duplicate reconciliation checks; synthetic facts are not live evidence."""
import copy
import importlib
import json

import pytest
from evaluation.tests.test_access_artifacts import artifacts
from evaluation.tests.test_bootstrap import inputs
from evaluation.tests.test_access_execution import Model, execute


def module():
    assert importlib.util.find_spec('evaluation.duplicate_outcome') is not None, 'Duplicate outcome collector missing'
    return importlib.import_module('evaluation.duplicate_outcome')


def facts():
    state = dict(request={'status': '2', 'outcomeLogId': '9', 'gid': 'alice', 'dataId': 'record', 'requestLogId': '7'},
                 grant={'exists': True, 'allowed': True, 'requestDigest': 'digest', 'gid': 'alice', 'dataId': 'record'},
                 logs={'pbc': [{'outcome': 'one'}], 'dbc': [{'grant': 'one'}]}, worker={'cache': 'unchanged'})
    return dict(before=state, after=copy.deepcopy(state), request_digest='digest', rejection_code='8',
                success=False, receipt_logs=[], original_outcomes=1, original_grants=1)


def test_duplicate_reconciliation_preserves_one_prior_successful_outcome():
    proof = module().check_duplicate_outcome(**facts())
    assert proof['ok'] and proof['error'] == 'REPLAY' and proof['delivery'] == 'unknown'


@pytest.mark.parametrize('mutation', ['no-positive', 'two-positive', 'no-grant', 'success', 'wrong-code',
                                      'receipt-event', 'request', 'grant', 'worker', 'pbc-log', 'dbc-log',
                                      'pending', 'wrong-subject', 'wrong-data', 'wrong-digest', 'no-log'])
def test_duplicate_collector_rejects_false_no_change_evidence(mutation):
    data = facts()
    if mutation == 'no-positive': data['original_outcomes'] = 0
    if mutation == 'two-positive': data['original_outcomes'] = 2
    if mutation == 'no-grant': data['original_grants'] = 0
    if mutation == 'success': data['success'] = True
    if mutation == 'wrong-code': data['rejection_code'] = '16'
    if mutation == 'receipt-event': data['receipt_logs'] = [{'event': 'outcome'}]
    if mutation == 'request': data['after']['request']['outcomeLogId'] = '10'
    if mutation == 'grant': data['after']['grant']['exists'] = False
    if mutation == 'worker': data['after']['worker']['cache'] = 'changed'
    if mutation == 'pbc-log': data['after']['logs']['pbc'].append({'outcome': 'two'})
    if mutation == 'dbc-log': data['after']['logs']['dbc'].append({'grant': 'two'})
    if mutation == 'pending': data['before']['request']['status'] = '1'
    if mutation == 'wrong-subject': data['before']['grant']['gid'] = 'bob'
    if mutation == 'wrong-data': data['before']['grant']['dataId'] = 'other'
    if mutation == 'wrong-digest': data['before']['grant']['requestDigest'] = 'other'
    if mutation == 'no-log': data['before']['request']['outcomeLogId'] = '0'
    with pytest.raises(ValueError): module().check_duplicate_outcome(**data)


@pytest.mark.parametrize('profile', ['paper-strict', 'paper-minimal', 'repaired-e'])
@pytest.mark.parametrize('transaction_mutation', ['none', 'changed-call', 'same-nonce', 'wrong-relay'])
def test_duplicate_probe_replays_identical_public_call_after_positive_control(artifacts, inputs, tmp_path, profile, transaction_mutation):
    from evaluation.native import NativeReceipt
    m = Model(artifacts, inputs, profile)
    original_submit = m.pbc.submit
    original_call = m.pbc.call
    original_calls = []
    public_logs = {'pbc': [], 'dbc': []}
    def submit(signer, role, method, *args, expect_success=True):
        if expect_success:
            native = original_submit(signer, role, method, *args)
            public_logs['pbc'].extend(native.receipt['logs'])
            if method in ('reportOutcome', 'reportAttestedOutcome'):
                original_calls.append((method, copy.deepcopy(args), native))
            return native
        assert (method, args) == original_calls[0][:2]
        assert m.request_state['status'] == '2'
        n = original_calls[0][2]
        receipt = dict(n.receipt, status='0x0', logs=[], transactionHash='0x'+'aa'*32)
        return NativeReceipt(receipt=receipt, transaction=dict(hash=receipt['transactionHash'], chainId=hex(int(m.pbc.chain_id)),
                              blockHash=n.block_hash, blockNumber=hex(int(n.block_number)), transactionIndex='0x0'),
                             block=dict(hash=n.block_hash, number=hex(int(n.block_number)), timestamp=hex(int(n.timestamp)),
                                        transactions=[receipt['transactionHash']]), chain_id=m.pbc.chain_id)
    def call(method, args=None):
        if method == 'eth_getLogs': return public_logs['pbc']
        if method == 'eth_getTransactionByHash':
            method_name, arguments, native = original_calls[0]
            duplicate = args[0] != native.receipt['transactionHash']
            data = dict(hash=args[0], input=m.pbc.contracts['PSC'].calldata(method_name, *arguments),
                        to=m.pbc.contracts['PSC'].address, **{'from': m.dep['fixture']['relay']['address']},
                        nonce='0x2' if duplicate else '0x1')
            if duplicate and transaction_mutation == 'changed-call': data['input'] += '00'
            if duplicate and transaction_mutation == 'same-nonce': data['nonce'] = '0x1'
            if duplicate and transaction_mutation == 'wrong-relay': data['from'] = '0x'+'bb'*20
            return data
        return original_call(method, args)
    m.pbc.submit = submit; m.pbc.call = call
    dbc_call = m.dbc.call
    dbc_submit = m.dbc.submit
    def submit_dbc(*args, **kwargs):
        native = dbc_submit(*args, **kwargs); public_logs['dbc'].extend(native.receipt['logs']); return native
    m.dbc.submit = submit_dbc
    m.dbc.call = lambda method, args=None: public_logs['dbc'] if method == 'eth_getLogs' else dbc_call(method, args)
    m.pbc.rejection_code = lambda native: '8'
    from evaluation.access_execution import execute_access
    kwargs = dict(deployment_bytes=json.dumps(m.dep).encode(),
                  user_label='alice', user=m.users['alice'], record=m.record, policy=m.policy,
                  expected_allow=True, worker_snapshot=m.snapshot, output=tmp_path/'access', duplicate_outcome=True)
    if transaction_mutation != 'none':
        with pytest.raises(ValueError): execute_access(m.pbc, m.dbc, m, **kwargs)
        return
    result = execute_access(m.pbc, m.dbc, m, **kwargs)
    proof = json.loads((tmp_path/'access/duplicate-outcome/result.json').read_text())
    assert result['ok'] and proof['ok'] and proof['error'] == 'REPLAY'
    assert proof['classification'] == ('REPAIR_SUPPORTED' if profile == 'repaired-e' else 'SUPPORTED')
    assert proof['identicalCalldata'] is True
