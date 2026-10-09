"""Synthetic RPC sensitivity controls; no live reorg or timing proof."""
import json
import pytest
from evaluation.evm import AbiContract
from evaluation.manifests import sha256
from evaluation.tests.test_chain import Replies, executor, contract, BLOCK_HASH


def test_group_retains_individual_bindings_and_pins_history(tmp_path):
    rpc = Replies(); original = rpc.call
    def call(method, params=None):
        if method == 'eth_getLogs':
            rpc.calls.append((method, params)); return []
        return original(method, params)
    rpc.call = call; chain = executor(tmp_path, rpc)
    with chain.read_group(('TMSC',)) as group:
        assert group.read('TMSC', 'authEpoch') == ['3']
        assert group.read('TMSC', 'authEpoch') == ['3']
        assert group.logs() == []
    assert len(chain.views) == 2
    assert all(r['blockHash'] == BLOCK_HASH and r['blockNumber'] == '2' for r in chain.views)
    assert len([m for m, _ in rpc.calls if m == 'eth_chainId']) == 2
    assert len([m for m, _ in rpc.calls if m == 'eth_getBlockByNumber']) == 3
    log_args = next(p for m,p in rpc.calls if m == 'eth_getLogs')
    assert log_args == [{'fromBlock': '0x0', 'toBlock': '0x2', 'address': [contract().address]}]
    assert json.loads((tmp_path/'chain/views.json').read_text()) == chain.views
    with pytest.raises(ValueError): group.read('TMSC', 'authEpoch')


@pytest.mark.parametrize('fault', ['wrong-chain-before', 'wrong-chain-during', 'reorg-before', 'reorg-during',
                                  'abi-before', 'abi-during', 'return-malformed', 'logs-malformed', 'timeout'])
def test_group_refuses_identity_drift_without_publishing_partial_views(tmp_path, fault):
    rpc = Replies(); original = rpc.call; chain = executor(tmp_path, rpc)
    abi = tmp_path/'TMSC.json'; abi.write_bytes(contract().path.read_bytes())
    chain.contracts['TMSC'] = AbiContract(abi, contract().address, sha256(abi))
    if fault == 'abi-before': abi.write_text('[]')
    counts = {'blocks': 0, 'chains': 0}
    def call(method, params=None):
        if method == 'eth_chainId':
            counts['chains'] += 1
            if fault == 'wrong-chain-before' or (fault == 'wrong-chain-during' and counts['chains'] == 2): return '0x1'
        if method == 'eth_getLogs': return {} if fault == 'logs-malformed' else []
        result = original(method, params)
        if method == 'eth_getBlockByNumber':
            counts['blocks'] += 1
            if ((fault == 'reorg-before' and counts['blocks'] == 2)
                    or (fault == 'reorg-during' and counts['blocks'] == 3)):
                result['hash'] = '0x'+'ff'*32
        if method == 'eth_call':
            if fault == 'abi-during': abi.write_text('[]')
            if fault == 'return-malformed': return '0x01'
            if fault == 'timeout':
                import time
                time.sleep(.06)
        return result
    rpc.call = call
    with pytest.raises((ValueError, TimeoutError)):
        with chain.read_group(('TMSC',)) as group:
            group.read('TMSC', 'authEpoch'); group.logs()
    assert chain.views == []
    assert json.loads((tmp_path/'chain/views.json').read_text()) == []


@pytest.mark.parametrize('fault', ['scope', 'nested', 'budget', 'body-error'])
def test_group_has_bounded_scope_and_never_certifies_failed_body(tmp_path, fault):
    rpc = Replies(); chain = executor(tmp_path, rpc)
    with pytest.raises(ValueError):
        with chain.read_group(('TMSC',)) as group:
            if fault == 'scope': group.read('PSC', 'getRequest', 'bad')
            if fault == 'nested':
                with chain.read_group(('TMSC',)): pass
            if fault == 'budget':
                for _ in range(17): group.read('TMSC', 'authEpoch')
            if fault == 'body-error':
                group.read('TMSC', 'authEpoch'); raise ValueError('control')
    assert not chain.views
    with chain.read_group(('TMSC',)) as group:
        assert group.read('TMSC', 'authEpoch') == ['3']
