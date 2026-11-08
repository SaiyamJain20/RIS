"""Manual raw-RPC probes; no sockets, owner test helpers or real ledger.

Use the real carried Chain decoding and the real new witness view. Diagnostic
expectations come from the view's documented fault contract; gaps are results,
not silently passing assertions or claims of incorrect authorization.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SNAP = ROOT / 'evaluation/runs/a2-witness-rpc-20261106/snapshot'
sys.path.insert(0, str(SNAP / 'protocol'))
from hmbc_protocol.chain import Chain, ChainError
from hmbc_protocol.abi import Contract
from hmbc_protocol.rpc_witness_view import RpcWitnessView
from hmbc_protocol.witness_service import LedgerUnreachable

H = '0x' + 'ab' * 32
A = '0x' + '11' * 20
WORD = lambda n: n.to_bytes(32, 'big').hex()
rows = []


class Raw(Chain):
    def __init__(self, replies):
        super().__init__('http://127.0.0.1:1', 1)
        self.replies, self.requests = replies, []

    def rpc(self, method, params=None):
        self.requests.append([method, params])
        value = self.replies.get(method, '0x1' if method == 'eth_chainId' else None)
        if isinstance(value, Exception):
            raise value
        return value


def probe(label, replies, invoke, expected, value=None, diagnostic=False):
    clients = {s: Raw(replies) for s in ('pbc', 'dbc')}
    contracts = {n: Contract(json.loads((SNAP / 'protocol/tests/fixtures/agent1-85c59f5-abi' / (n + '.json')).read_text()), A)
                 for n in ('PSC', 'TMSC', 'KSSC', 'ACSC', 'Governance')}
    view = RpcWitnessView(chains=clients, contracts=contracts)
    result = None
    try:
        result = invoke(view)
        actual = 'ACCEPT'
    except LedgerUnreachable:
        actual = 'LEDGER_UNREACHABLE'
    except Exception as exc:
        actual = type(exc).__name__
    row = dict(label=label, replies={k: (type(v).__name__ if isinstance(v, Exception) else v) for k, v in replies.items()},
               expected=expected, actual=actual, returned=result, diagnostic=diagnostic,
               requests={k: c.requests for k, c in clients.items()})
    rows.append(row)
    if not diagnostic:
        assert actual == expected, row
        if actual == 'ACCEPT':
            assert result == value, row


block = dict(number='0x1', hash=H, timestamp='0x10')
probe('canonical observe', {'eth_getBlockByNumber': block}, lambda v: v.observe('pbc'), 'ACCEPT',
      dict(chainId='1', blockNumber='1', blockHash=H, timestamp='16'))
probe('canonical numbered block', {'eth_getBlockByNumber': block}, lambda v: v.pbc_block(1), 'ACCEPT',
      dict(number='1', hash=H, timestamp='16'))
probe('canonical governance nonce', {'eth_call': '0x' + WORD(7)}, lambda v: v.governance_nonce(), 'ACCEPT', '7')
probe('canonical authority true', {'eth_call': '0x' + WORD(1)}, lambda v: v.is_authority(A), 'ACCEPT', True)
probe('canonical authority false', {'eth_call': '0x' + WORD(0)}, lambda v: v.is_authority(A), 'ACCEPT', False)
probe('missing numbered block', {}, lambda v: v.pbc_block(1), 'ACCEPT', None)
probe('missing transaction', {}, lambda v: v.forwarding_call(H), 'LEDGER_UNREACHABLE')
probe('undecodable transaction', {'eth_getTransactionByHash': {'to': A, 'input': '0x1234'}}, lambda v: v.forwarding_call(H), 'ACCEPT', None)
probe('transport failure', {'eth_getBlockByNumber': ChainError('synthetic transport failure')}, lambda v: v.observe('pbc'), 'LEDGER_UNREACHABLE')
probe('wrong chain', {'eth_chainId': '0x2'}, lambda v: v.observe('pbc'), 'LEDGER_UNREACHABLE')
probe('malformed block quantity', {'eth_getBlockByNumber': dict(block, number='0xzz')}, lambda v: v.observe('pbc'), 'LEDGER_UNREACHABLE')
probe('short ABI', {'eth_call': '0x12'}, lambda v: v.governance_nonce(), 'LEDGER_UNREACHABLE')
probe('missing log fields', {'eth_getLogs': [{}]}, lambda v: v.forwarded_logs(H), 'LEDGER_UNREACHABLE')

for value in ([], 'bad', 4, True):
    probe('transaction shape ' + type(value).__name__, {'eth_getTransactionByHash': value},
          lambda v: v.forwarding_call(H), 'LEDGER_UNREACHABLE', diagnostic=True)
for raw in ('0x1_0', '0x01', '0xA', '0x-1', '0x+1', '0x 1'):
    probe('noncanonical observed number ' + raw, {'eth_getBlockByNumber': dict(block, number=raw)},
          lambda v: v.observe('pbc'), 'LEDGER_UNREACHABLE', diagnostic=True)
probe('ABI trailing word', {'eth_call': '0x' + WORD(7) + WORD(0)}, lambda v: v.governance_nonce(), 'LEDGER_UNREACHABLE', diagnostic=True)
probe('ABI nonhex prefix', {'eth_call': 'zz' + WORD(7)}, lambda v: v.governance_nonce(), 'LEDGER_UNREACHABLE', diagnostic=True)
probe('ABI result wrong shape', {'eth_call': 7}, lambda v: v.governance_nonce(), 'LEDGER_UNREACHABLE', diagnostic=True)
probe('numbered block missing hash', {'eth_getBlockByNumber': {'timestamp': '0x10'}}, lambda v: v.pbc_block(1), 'LEDGER_UNREACHABLE')

result = dict(controls=sum(not r['diagnostic'] for r in rows), diagnostics=sum(r['diagnostic'] for r in rows),
              gaps=[r['label'] for r in rows if r['expected'] != r['actual']], rows=rows,
              classification='tested reconstruction result; no authorization failure demonstrated', liveNode=False)
(OUT / 'probes.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
