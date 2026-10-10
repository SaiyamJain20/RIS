"""Block-pinned read groups (A1-0061 D-5c): an explicit historical block, never 'latest'.

Controlled replies only. Historical eth_call/eth_getLogs at a fixed, identity-checked
block are immutable under the safe-ledger assumption, so a snapshot may be taken after
a later transaction without changing what it observes.
"""
import pytest

from evaluation.tests.test_chain import Replies, executor, contract, BLOCK_HASH


def test_pinned_group_reads_only_the_requested_block(tmp_path):
    rpc = Replies(); original = rpc.call
    def call(method, params=None):
        if method == 'eth_getLogs':
            rpc.calls.append((method, params)); return []
        return original(method, params)
    rpc.call = call; chain = executor(tmp_path, rpc)
    with chain.read_group(('TMSC',), block='2') as group:
        assert group.read('TMSC', 'authEpoch') == ['3'] and group.logs() == []
    blocks = [p[0] for m, p in rpc.calls if m == 'eth_getBlockByNumber']
    assert blocks == ['0x2', '0x2', '0x2'] and 'latest' not in blocks
    assert [p[1] for m, p in rpc.calls if m == 'eth_call'] == ['0x2']
    assert next(p for m, p in rpc.calls if m == 'eth_getLogs')[0]['toBlock'] == '0x2'
    assert chain.views[0]['blockNumber'] == '2' and chain.views[0]['blockHash'] == BLOCK_HASH


@pytest.mark.parametrize('block', ['latest', '0x2', '-1', '02', 2, ''])
def test_pinned_group_requires_canonical_decimal_block(tmp_path, block):
    chain = executor(tmp_path, Replies())
    with pytest.raises(ValueError):
        with chain.read_group(('TMSC',), block=block): pass
    assert chain.views == []


def test_pinned_group_refuses_unmined_or_mismatched_block(tmp_path):
    rpc = Replies(); original = rpc.call
    def call(method, params=None):
        if method == 'eth_getBlockByNumber' and params[0] == '0x7': return None
        return original(method, params)
    rpc.call = call; chain = executor(tmp_path, rpc)
    with pytest.raises(ValueError):
        with chain.read_group(('TMSC',), block='7'): pass
    with pytest.raises(ValueError):
        # Replies always answers block 2; asking for 3 must not be silently accepted.
        with chain.read_group(('TMSC',), block='3'): pass
    assert chain.views == []
