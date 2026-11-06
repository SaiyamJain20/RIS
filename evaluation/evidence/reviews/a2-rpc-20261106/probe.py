"""Independent raw-reply probes; report acceptance gaps without owner edits.

No node, socket, Chain implementation or owner test helper is used. ABI words
are assembled directly. A completed probe is not a passing refusal property.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SCRATCH = ROOT / 'evaluation/runs/a2-rpc-20261106/snapshot'
sys.path.insert(0, str(SCRATCH / 'protocol'))
from hmbc_protocol.binding_open import LedgerUnreachable
from hmbc_protocol.rpc_binding_view import RpcBindingView

A = '0x' + '11' * 20
B = '0x' + '22' * 20
ABIS = json.loads((SCRATCH / 'protocol/tests/fixtures/agent1-85c59f5-abi/PSC.json').read_text())


class Raw:
    chain_id = 1

    def __init__(self, result):
        self.result = result
        self.requests = []

    def rpc(self, method, params):
        self.requests.append((method, params))
        return self.result


def view(raw):
    clients = {'pbc': Raw(raw), 'dbc': Raw(raw)}
    return RpcBindingView(chains=clients, contracts={'pbc': {'PSC': A}, 'dbc': {}},
                          abis={'PSC': ABIS}), clients


def word(n):
    return n.to_bytes(32, 'big').hex()


rows = []


def probe(label, raw, invoke, *, expect, value=None, classification='control'):
    instance, clients = view(raw)
    try:
        result = invoke(instance)
        actual = 'ACCEPT'
    except LedgerUnreachable:
        result, actual = None, 'REFUSE'
    row = dict(label=label, rawReply=raw, expected=expect, actual=actual,
               returned=result, classification=classification,
               requests=clients['pbc'].requests)
    rows.append(row)
    if classification == 'control':
        assert actual == expect, row
        if expect == 'ACCEPT':
            assert result == value, row
    return row


for raw, expected in [('0x0', '0'), ('0x1', '1'), ('0xff', '255')]:
    probe('canonical quantity ' + raw, raw, lambda v: v.chain_id('pbc'),
          expect='ACCEPT', value=expected)
for raw in (None, True, '0x', '0xzz', '12'):
    probe('malformed quantity ' + repr(raw), raw, lambda v: v.chain_id('pbc'), expect='REFUSE')
for raw in ('0x-1', '0x+1', '0x1_0', '0x 1', '0x01', '0xA'):
    probe('quantity normalization gap ' + raw, raw, lambda v: v.chain_id('pbc'),
          expect='REFUSE', classification='tested reconstruction result: permissive reply parsing')
probe('negative latest block', {'number': '0x-1', 'hash': '0x' + 'ab' * 32},
      lambda v: v.latest('pbc'), expect='REFUSE',
      classification='tested reconstruction result: permissive reply parsing')

for fn, raw, expected in [('threshold', '0x' + word(3), '3'),
                          ('configured', '0x' + word(1), True),
                          ('rsc', '0x' + word(int(B, 16)), B),
                          ('witnesses', '0x' + word(32) + word(2) + word(int(A, 16)) + word(int(B, 16)), [A, B])]:
    probe('canonical ABI ' + fn, raw, lambda v, fn=fn: v.call('pbc', A, fn, [], 7),
          expect='ACCEPT', value=expected)
    probe('trailing ABI bytes ' + fn, raw + 'deadbeef',
          lambda v, fn=fn: v.call('pbc', A, fn, [], 7), expect='REFUSE',
          classification='tested reconstruction result: trailing bytes tolerated; no altered value shown')
for label, raw, fn in [('short uint', '0x' + word(3)[:-2], 'threshold'),
                       ('invalid bool', '0x' + word(2), 'configured'),
                       ('bad address padding', '0x' + 'ff' * 12 + B[2:], 'rsc')]:
    probe(label, raw, lambda v, fn=fn: v.call('pbc', A, fn, [], 7), expect='REFUSE')
raw = '0x' + word(64) + word(0) + word(2) + word(int(A, 16)) + word(int(B, 16))
probe('ABI dynamic offset gap', raw, lambda v: v.call('pbc', A, 'witnesses', [], 7),
      expect='REFUSE', classification='tested reconstruction result: non-minimal dynamic layout tolerated')

data = dict(scope='synthetic public API reply parsing; no services or chain truth',
            controlCount=sum(r['classification'] == 'control' for r in rows),
            propertyProbeCount=sum(r['classification'] != 'control' for r in rows),
            acceptanceGaps=[r['label'] for r in rows if r['actual'] != r['expected']], rows=rows)
(OUT / 'probes.json').write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps({k: v for k, v in data.items() if k != 'rows'}, indent=2))
