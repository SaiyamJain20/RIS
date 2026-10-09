"""Controlled RPC replies test executor joins; they are not live chain evidence."""
import copy
import importlib
from pathlib import Path

from eth_abi import encode
from eth_account import Account
from eth_utils import keccak
import pytest

from evaluation.evm import AbiContract
from evaluation.manifests import sha256

ROOT = Path(__file__).resolve().parents[2]
ADDRESS = '0x'+'11'*20
BLOCK_HASH = '0x'+'ab'*32
RELAY = '0x3df38017505bb45d1d4c77065e09aa9175a67c48'


def contract():
    path = ROOT/'evaluation/fixtures/e1/abi/TMSC.json'
    return AbiContract(path, ADDRESS, sha256(path))


class Replies:
    def __init__(self):
        self.calls = []; self.raw = None; self.mutation = None; self.polls = 0
        self.failure = False; self.pending = False; self.move_block = False; self.foreign_hash = False

    def call(self, method, params=None):
        self.calls.append((method, params))
        if method == 'eth_chainId': return '0x4871'
        if method == 'eth_getTransactionCount': return '0x0'
        if method == 'eth_gasPrice': return '0x3b9aca00'
        if method == 'eth_sendRawTransaction':
            self.raw = params[0]; return '0x'+keccak(bytes.fromhex(self.raw[2:])).hex()
        tx_hash = '0x'+keccak(bytes.fromhex(self.raw[2:])).hex() if self.raw else '0x'+'cc'*32
        if self.foreign_hash:
            tx_hash = '0x'+'ff'*32
        if method == 'eth_getTransactionReceipt':
            self.polls += 1
            if self.pending: return None
            return {'status': '0x0' if self.failure else '0x1', 'transactionHash': tx_hash,
                    'blockHash': BLOCK_HASH, 'blockNumber': '0x2', 'transactionIndex': '0x0',
                    'gasUsed': '0x5208', 'logs': []}
        if method == 'eth_getTransactionByHash':
            tx = {'hash': tx_hash, 'chainId': '0x4871', 'blockHash': BLOCK_HASH,
                  'blockNumber': '0x2', 'transactionIndex': '0x0', 'from': RELAY,
                  'to': ADDRESS, 'input': contract().calldata('authEpoch'), 'nonce': '0x0',
                  'gas': '0x2dc6c0', 'value': '0x0'}
            if self.mutation: tx.update(self.mutation)
            return tx
        if method == 'eth_getBlockByNumber':
            return {'hash': BLOCK_HASH, 'number': '0x2', 'timestamp': '0x64', 'transactions': [tx_hash]}
        if method == 'eth_call':
            return '0x'+encode(['uint64'], [3]).hex()
        if method == 'debug_traceTransaction':
            data = keccak(text='Rejected(uint8)')[:4]+encode(['uint8'], [16])
            return {'failed': True, 'returnValue': data.hex()}
        raise AssertionError(method)


def executor(tmp_path, replies):
    assert importlib.util.find_spec('evaluation.chain') is not None, 'Public ABI executor is missing'
    cls = importlib.import_module('evaluation.chain').PublicChain
    return cls(replies, chain_id='18545', contracts={'TMSC': contract()}, output=tmp_path/'chain', timeout=0.05)


def test_transaction_signing_binds_only_runner_owned_relay_and_retains_native_result(tmp_path):
    replies = Replies(); chain = executor(tmp_path, replies)
    native = chain.submit('relay', 'TMSC', 'authEpoch')
    assert native.success and native.chain_id == '18545'
    assert Account.recover_transaction(replies.raw).lower() == RELAY
    evidence = (tmp_path/'chain/transactions.json').read_text()
    assert 'privateKey' not in evidence and 'hmbc-e0-synthetic-key:' not in evidence
    assert 'authEpoch' in evidence and native.block_hash == BLOCK_HASH


@pytest.mark.parametrize('field,value', [
    ('from', '0x'+'22'*20), ('to', '0x'+'22'*20), ('input', '0x1234'),
    ('nonce', '0x1'), ('chainId', '0x6f'), ('value', '0x1'), ('gas', '0x1'),
    ('blockHash', '0x'+'ff'*32), ('transactionIndex', '0x1')])
def test_receipt_cannot_certify_a_different_submitted_call(tmp_path, field, value):
    replies = Replies(); replies.mutation = {field: value}
    chain = executor(tmp_path, replies)
    with pytest.raises(ValueError): chain.submit('relay', 'TMSC', 'authEpoch')
    assert replies.raw is not None


def test_mutually_consistent_receipt_cannot_replace_the_signed_transaction(tmp_path):
    replies = Replies(); replies.foreign_hash = True; chain = executor(tmp_path, replies)
    with pytest.raises(ValueError): chain.submit('relay', 'TMSC', 'authEpoch')


@pytest.mark.parametrize('role', ['H1-root', 'alice', 'bob', 'witness-1', 'deployer', 'arbitrary-ca-admin'])
def test_runner_never_derives_peer_owned_keys(tmp_path, role):
    replies = Replies(); chain = executor(tmp_path, replies)
    with pytest.raises(ValueError): chain.submit(role, 'TMSC', 'authEpoch')
    assert replies.calls == []


def test_wrong_chain_is_refused_before_broadcast(tmp_path):
    replies = Replies(); chain = executor(tmp_path, replies)
    chain.chain_id = '28545'
    with pytest.raises(ValueError): chain.submit('relay', 'TMSC', 'authEpoch')
    assert replies.raw is None


def test_mined_rejection_retains_exact_public_custom_error(tmp_path):
    replies = Replies(); replies.failure = True; chain = executor(tmp_path, replies)
    native = chain.submit('relay', 'TMSC', 'authEpoch', expect_success=False)
    assert not native.success
    assert chain.rejection_code(native) == '16'


def test_rejection_trace_is_not_a_generic_failed_transaction(tmp_path):
    replies = Replies(); replies.failure = True; original = replies.call
    def bad_trace(method, params=None):
        return {'failed': True, 'returnValue': ''} if method == 'debug_traceTransaction' else original(method, params)
    replies.call = bad_trace
    chain = executor(tmp_path, replies)
    native = chain.submit('relay', 'TMSC', 'authEpoch', expect_success=False)
    with pytest.raises(ValueError): chain.rejection_code(native)


def test_reverted_transaction_never_counts_as_expected_success(tmp_path):
    replies = Replies(); replies.failure = True; chain = executor(tmp_path, replies)
    with pytest.raises(ValueError): chain.submit('relay', 'TMSC', 'authEpoch')


def test_pending_transaction_has_bounded_wait_and_retained_failure(tmp_path):
    replies = Replies(); replies.pending = True; chain = executor(tmp_path, replies)
    with pytest.raises(TimeoutError): chain.submit('relay', 'TMSC', 'authEpoch')
    assert replies.raw is not None and replies.polls < 10
    assert 'TimeoutError' in (tmp_path/'chain/transactions.json').read_text()


def test_view_returns_block_address_and_calldata_bound_evidence(tmp_path):
    replies = Replies(); chain = executor(tmp_path, replies)
    block = replies.call('eth_getBlockByNumber', ['latest', False])
    row = chain.observe('TMSC', 'authEpoch', block=block)
    assert row['chainId'] == '18545' and row['blockHash'] == BLOCK_HASH
    assert row['blockNumber'] == '2' and row['address'] == ADDRESS
    assert contract().decode_return('authEpoch', row['returnData']) == ['3']
    assert ('eth_call', [{'to': ADDRESS, 'data': contract().calldata('authEpoch')}, '0x2']) in replies.calls


def test_changed_block_invalidates_historical_view(tmp_path):
    replies = Replies(); chain = executor(tmp_path, replies)
    block = replies.call('eth_getBlockByNumber', ['latest', False]); block['hash'] = '0x'+'ff'*32
    with pytest.raises(ValueError): chain.observe('TMSC', 'authEpoch', block=block)


def test_unregistered_contract_and_abi_drift_refuse_before_broadcast(tmp_path):
    replies = Replies(); chain = executor(tmp_path, replies)
    with pytest.raises(ValueError): chain.submit('relay', 'PSC', 'authEpoch')
    p = tmp_path/'TMSC.json'; p.write_bytes(contract().path.read_bytes())
    changed = AbiContract(p, ADDRESS, sha256(p)); chain.contracts['TMSC'] = changed
    p.write_text('[]')
    with pytest.raises(ValueError): chain.submit('relay', 'TMSC', 'authEpoch')
    assert replies.raw is None
