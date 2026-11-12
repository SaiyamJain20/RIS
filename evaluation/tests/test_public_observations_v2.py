"""Synthetic public RPC byte tests, with exact owner ABIs and no services.

Controls catch incorrect block/call selection, missing ABI and identity checks,
bad decoding, unchecked getters, lost failure logs and input drift. The fake
transport is the only replaced layer; actual ABI decoding/reconstruction runs.
"""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys

from eth_abi import encode
from eth_utils import keccak
from jsonschema import ValidationError
import pytest

from evaluation.tests.test_binding_context_v2 import fixture

ROOT = Path(__file__).resolve().parents[2]
ABI = ROOT / 'evaluation/fixtures/f/abi'
BAD = (ValueError, ValidationError)


def subject():
    return importlib.import_module('evaluation.public_observations_v2')


class SyntheticRpc:
    def __init__(self, manifest, observed, chain):
        self.pin = manifest['chains'][chain]
        self.observed = observed[chain]
        self.calls = []
        self.checkpoints = []
        self.rewrite = lambda method, params, result: result
        self.answers = {}
        types = {'configured': 'bool', 'profile': 'uint8', 'mutations': 'uint256',
                 'witnessSetVersion': 'uint64', 'threshold': 'uint256',
                 'witnesses': 'address[]', 'governanceChainId': 'uint256',
                 'maxGovernanceTtl': 'uint64'}
        for name, views in self.observed['views'].items():
            for getter, row in views.items():
                signature = getter + ('(uint256)' if getter == 'ksscForChain' else '()')
                data = '0x' + keccak(text=signature)[:4].hex()
                if getter == 'ksscForChain':
                    data += encode(['uint256'], [int(manifest['chains']['dbc']['chainId'])]).hex()
                kind = types.get(getter, 'address')
                value = int(row['value']) if kind.startswith('uint') else row['value']
                self.answers[(self.pin['contracts'][name], data)] = '0x' + encode([kind], [value]).hex()

    def checkpoint(self, label):
        self.checkpoints.append(label)

    def call(self, method, params=None):
        params = [] if params is None else params
        self.calls.append((method, copy.deepcopy(params)))
        if method == 'eth_chainId':
            result = hex(int(self.pin['chainId']))
        elif method == 'eth_getBlockByNumber':
            number = params[0]
            if number in ('latest', hex(int(self.observed['anchor']['number']))):
                row = self.observed['anchor']
            elif number == '0x0':
                row = {'number': '0', 'hash': self.observed['genesisHash']}
            elif number == hex(int(self.pin['deployBlock'])):
                row = self.observed['deployBlock']
            else:
                raise AssertionError('Unexpected block request')
            assert params[1] is False
            result = {'number': hex(int(row['number'])), 'hash': row['hash']}
        elif method == 'eth_getCode':
            assert params[1] == hex(int(self.observed['anchor']['number']))
            name = next(n for n, a in self.pin['contracts'].items() if a == params[0])
            result = self.observed['code'][name]['value']
        elif method == 'eth_call':
            assert params[1] == hex(int(self.observed['anchor']['number']))
            assert set(params[0]) == {'to', 'data'}
            result = self.answers[(params[0]['to'], params[0]['data'])]
        else:
            raise AssertionError('Unexpected RPC method: ' + method)
        return self.rewrite(method, params, copy.deepcopy(result))


def setup(f=True, mask='0', threshold='3'):
    manifest, observed, expected = fixture(f, mask, threshold)
    paths = {n: ABI / (n + '.json') for n in manifest['abi']}
    for n, path in paths.items():
        pin = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest['abi'][n]['abiSha256'] = pin
        for chain in expected['chains'].values():
            if n in chain['contracts']:
                chain['contracts'][n]['abiSha256'] = pin
    rpcs = {c: SyntheticRpc(manifest, observed, c) for c in ('pbc', 'dbc')}
    return manifest, observed, expected, paths, rpcs


def collect(tmp_path, case, **kwargs):
    manifest, _, _, paths, rpcs = case
    return subject().collect(manifest, rpcs, paths, output=tmp_path / 'collection',
                             compiled_max_admins='8' if manifest['profileEnum'] == '3' else None, **kwargs)


@pytest.mark.parametrize('f,mask,q', [(False, '0', '3'), (True, '0', '3'), (True, '0', '2'), (True, '256', '3')])
def test_raw_rpc_to_exact_binding_and_auditable_calls(tmp_path, f, mask, q):
    case = setup(f, mask, q)
    result = collect(tmp_path, case)
    assert result['document'] == case[2]
    assert result['observations'] == case[1]
    report = json.loads((tmp_path / 'collection/transcript.json').read_text())
    assert report['status'] == 'complete'
    assert report['calls'] and all(r['status'] == 'returned' for r in report['calls'])
    assert {r['method'] for r in report['calls']} == {'eth_chainId', 'eth_getBlockByNumber', 'eth_getCode', 'eth_call'}
    assert json.loads((tmp_path / 'collection/result.json').read_text()) == result


@pytest.mark.parametrize('method', ['eth_chainId', 'eth_getBlockByNumber', 'eth_getCode', 'eth_call'])
def test_transport_failure_keeps_partial_raw_transcript_without_result(tmp_path, method):
    case = setup()
    def fail(m, p, r):
        if m == method:
            raise RuntimeError('controlled transport failure')
        return r
    case[4]['pbc'].rewrite = fail
    with pytest.raises(RuntimeError):
        collect(tmp_path, case)
    report = json.loads((tmp_path / 'collection/transcript.json').read_text())
    assert report['status'] == 'failed'
    assert report['calls'][-1]['status'] == 'failed'
    assert not (tmp_path / 'collection/result.json').exists()


@pytest.mark.parametrize('raw', ['0x', '0x01', '0x' + '00' * 33, '0x' + '00' * 31 + '02', '0X00'])
def test_noncanonical_boolean_return_never_becomes_an_observation(tmp_path, raw):
    case = setup()
    selector = '0x' + keccak(text='configured()')[:4].hex()
    case[4]['pbc'].rewrite = lambda m, p, r: raw if m == 'eth_call' and p[0]['data'] == selector else r
    with pytest.raises(ValueError):
        collect(tmp_path, case)
    assert not (tmp_path / 'collection/result.json').exists()


@pytest.mark.parametrize('chain', ['pbc', 'dbc'])
@pytest.mark.parametrize('target', ['chain', 'genesis', 'deployment', 'anchor'])
def test_identity_drift_is_refused_after_collection(tmp_path, chain, target):
    case = setup()
    rpc = case[4][chain]
    count = 0
    tag = {'genesis': '0x0', 'deployment': hex(int(rpc.pin['deployBlock'])),
           'anchor': hex(int(rpc.observed['anchor']['number']))}.get(target)
    def drift(m, p, r):
        nonlocal count
        hit = m == 'eth_chainId' if target == 'chain' else m == 'eth_getBlockByNumber' and p[0] == tag
        if hit:
            count += 1
            if count >= (1 if target == 'anchor' else 2):
                return '0x1' if target == 'chain' else {**r, 'hash': '0x' + '99' * 32}
        return r
    rpc.rewrite = drift
    with pytest.raises(ValueError):
        collect(tmp_path, case)
    assert not (tmp_path / 'collection/result.json').exists()


def test_pbc_is_rechecked_after_dbc_reads(tmp_path):
    case = setup()
    def drift(m, p, r):
        if m == 'eth_chainId' and case[4]['dbc'].calls:
            return '0x1'
        return r
    case[4]['pbc'].rewrite = drift
    with pytest.raises(ValueError):
        collect(tmp_path, case)


@pytest.mark.parametrize('target', ['missing', 'extra', 'wrong-hash'])
def test_abi_inventory_is_closed_and_hash_bound_before_rpc(tmp_path, target):
    case = setup()
    if target == 'missing':
        del case[3]['PSC']
    elif target == 'extra':
        case[3]['Unknown'] = ABI / 'PSC.json'
    else:
        case[0]['abi']['PSC']['abiSha256'] = '00' * 32
    with pytest.raises(ValueError):
        collect(tmp_path, case)
    assert not any(rpc.calls for rpc in case[4].values())


def test_abi_file_drift_is_refused_before_success(tmp_path):
    case = setup()
    target = tmp_path / 'PSC.json'
    target.write_bytes(case[3]['PSC'].read_bytes())
    case[3]['PSC'] = target
    def drift(m, p, r):
        target.write_bytes(target.read_bytes() + b' ')
        return r
    case[4]['dbc'].rewrite = drift
    with pytest.raises(ValueError):
        collect(tmp_path, case)


def test_manifest_drift_is_refused_before_success(tmp_path):
    case = setup()
    def drift(m, p, r):
        case[0]['fixture']['relay']['address'] = '0x' + 'aa' * 20
        return r
    case[4]['dbc'].rewrite = drift
    with pytest.raises(ValueError):
        collect(tmp_path, case)


@pytest.mark.parametrize('getter,value,kind', [('maxGovernanceTtl', 121, 'uint64'), ('governanceChainId', 1, 'uint256'),
    ('mutations', 1, 'uint256'), ('profile', 2, 'uint8'), ('configured', False, 'bool')])
def test_live_getter_mismatch_refuses_publication(tmp_path, getter, value, kind):
    case = setup()
    selector = '0x' + keccak(text=getter + '()')[:4].hex()
    case[4]['pbc'].rewrite = lambda m, p, r: '0x' + encode([kind], [value]).hex() if m == 'eth_call' and p[0]['data'] == selector else r
    with pytest.raises(BAD):
        collect(tmp_path, case)
    assert not (tmp_path / 'collection/result.json').exists()


@pytest.mark.parametrize('timeout', [0, -1, float('inf'), float('nan'), True])
def test_invalid_budgets_refuse_before_io(tmp_path, timeout):
    case = setup()
    with pytest.raises(ValueError):
        collect(tmp_path, case, timeout=timeout)
    assert not any(rpc.calls for rpc in case[4].values())


def test_deadline_is_enforced_after_slow_transport_return(tmp_path, monkeypatch):
    case = setup()
    clock = [0.0]
    monkeypatch.setattr(subject().time, 'monotonic', lambda: clock[0])
    case[4]['pbc'].rewrite = lambda m, p, r: (clock.__setitem__(0, 11.0), r)[1]
    with pytest.raises(TimeoutError):
        collect(tmp_path, case, timeout=10)
    assert not (tmp_path / 'collection/result.json').exists()


def test_previous_output_is_never_overwritten(tmp_path):
    case = setup()
    collect(tmp_path, case)
    path = tmp_path / 'collection/result.json'
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        collect(tmp_path, case)
    assert path.read_bytes() == before


def test_result_write_failure_does_not_publish_a_partial_result(tmp_path, monkeypatch):
    case = setup()
    original = Path.write_text
    def fail(path, data, *args, **kwargs):
        if path.name.startswith('result'):
            original(path, 'partial', *args, **kwargs)
            raise OSError('controlled result write failure')
        return original(path, data, *args, **kwargs)
    monkeypatch.setattr(Path, 'write_text', fail)
    with pytest.raises(OSError):
        collect(tmp_path, case)
    assert not (tmp_path / 'collection/result.json').exists()
    assert json.loads((tmp_path / 'collection/transcript.json').read_text())['status'] == 'failed'


@pytest.mark.parametrize('chain', ['pbc', 'dbc'])
@pytest.mark.parametrize('raw', ['0x', '0x01', '0x' + '00' * 96])
def test_live_code_must_match_pinned_length_and_masked_build(tmp_path, chain, raw):
    case = setup()
    case[4][chain].rewrite = lambda m, p, r: raw if m == 'eth_getCode' else r
    with pytest.raises(ValueError):
        collect(tmp_path, case)
    assert not (tmp_path / 'collection/result.json').exists()


@pytest.mark.parametrize('raw', [None, {}, {'number': '0x00', 'hash': '0x' + 'aa' * 32},
    {'number': '0x1', 'hash': '0x' + 'aa' * 32}, {'number': '0x0', 'hash': '0x12'}])
def test_missing_or_malformed_genesis_block_is_refused(tmp_path, raw):
    case = setup()
    case[4]['pbc'].rewrite = lambda m, p, r: raw if m == 'eth_getBlockByNumber' and p[0] == '0x0' else r
    with pytest.raises(ValueError):
        collect(tmp_path, case)


def test_successor_e_v21_is_selected_explicitly(tmp_path):
    case = setup(False)
    case[0]['schemaVersion'] = 'hmbc-ledger-deployment/v2.1'
    case[0]['sources']['src/interfaces/IPolicyVersion.sol'] = 'bb' * 32
    case[0]['sources']['src/Governance.sol'] = 'aa' * 32
    assert collect(tmp_path, case)['document'] == case[2]


def test_contract_addresses_are_namespaced_by_chain(tmp_path):
    case = setup()
    old = case[0]['chains']['dbc']['contracts']['KSSC']
    new = case[0]['chains']['pbc']['contracts']['PSC']
    def replace(value):
        if isinstance(value, dict):
            return {k: replace(v) for k, v in value.items()}
        if isinstance(value, list):
            return [replace(v) for v in value]
        return new if value == old else value
    manifest, observed, expected = (replace(v) for v in case[:3])
    rpcs = {c: SyntheticRpc(manifest, observed, c) for c in ('pbc', 'dbc')}
    assert collect(tmp_path, (manifest, observed, expected, case[3], rpcs))['document'] == expected


def test_existing_rpcclient_retains_tool_pins_and_raw_command_logs(tmp_path):
    """A synthetic CLI replaces Cast, while real RpcClient subprocesses run."""
    from evaluation.rpc import RpcClient
    case = setup()
    replies = {}
    for chain, fake in case[4].items():
        chain_replies = {}
        def add(method, params):
            key = json.dumps([method, params], separators=(',', ':'))
            chain_replies[key] = fake.call(method, params)
        add('eth_chainId', [])
        for number in ['0x0', hex(int(fake.pin['deployBlock'])), 'latest', hex(int(fake.observed['anchor']['number']))]:
            add('eth_getBlockByNumber', [number, False])
        anchor = hex(int(fake.observed['anchor']['number']))
        for address in fake.pin['contracts'].values():
            add('eth_getCode', [address, anchor])
        for address, data in fake.answers:
            add('eth_call', [{'to': address, 'data': data}, anchor])
        replies[chain] = chain_replies
    dataset = tmp_path / 'dataset.json'
    dataset.write_text(json.dumps(replies))
    tool = tmp_path / 'synthetic-cast'
    tool.write_text('#!' + sys.executable + '\n' + '''import json, sys
from pathlib import Path
argv = sys.argv[1:]
assert argv[0] == 'rpc'
chain = 'pbc' if argv[argv.index('--rpc-url') + 1].endswith(':18545') else 'dbc'
key = json.dumps([argv[1], json.loads(argv[2])], separators=(',', ':'))
print(json.dumps(json.loads(Path(__file__).with_name('dataset.json').read_text())[chain][key]))
''')
    tool.chmod(0o700)
    pin = hashlib.sha256(tool.read_bytes()).hexdigest()
    rpcs = {chain: RpcClient('http://127.0.0.1:' + port, cast=tool, cast_sha256=pin,
            cwd=ROOT, output=tmp_path / ('rpc-' + chain), timeout=2, hash_policy='checkpoint')
            for chain, port in [('pbc', '18545'), ('dbc', '28545')]}
    result = collect(tmp_path, (*case[:4], rpcs), timeout=20)
    assert result['document'] == case[2]
    for chain, rpc in rpcs.items():
        assert {r['label'] for r in rpc.checkpoints} == {'construct', 'binding-read-before', 'binding-read-after'}
        assert all(r['ok'] and r['sha256'] == pin for r in rpc.checkpoints)
        assert rpc.commands and all(r['exitCode'] == 0 and r['parseFailure'] is None for r in rpc.commands)
        for i, command in enumerate(rpc.commands):
            assert hashlib.sha256((tmp_path / ('rpc-' + chain) / f'{i:04}.txt').read_bytes()).hexdigest() == command['outputSha256']


def _moved_chain(case):
    """Make `latest` answer a newer block than the pinned anchor on both chains."""
    for chain, rpc in case[4].items():
        anchor = case[1][chain]['anchor']

        def rewrite(method, params, result, anchor=anchor):
            if method == 'eth_getBlockByNumber' and params[0] == 'latest':
                return {'number': hex(int(anchor['number']) + 2), 'hash': '0x' + 'ee' * 32}
            return result
        rpc.rewrite = rewrite


def _anchors(case):
    return {c: copy.deepcopy(case[1][c]['anchor']) for c in ('pbc', 'dbc')}


@pytest.mark.parametrize('f,mask,q', [(True, '0', '3'), (True, '256', '3')])
def test_explicit_anchors_read_the_pinned_block_even_after_the_chain_moved(tmp_path, f, mask, q):
    case = setup(f, mask, q)
    _moved_chain(case)
    result = collect(tmp_path, case, anchors=_anchors(case))
    assert result['observations'] == case[1]
    assert result['document'] == case[2]
    report = json.loads((tmp_path / 'collection/transcript.json').read_text())
    assert not any(r['method'] == 'eth_getBlockByNumber' and r['params'][0] == 'latest' for r in report['calls'])


def test_without_anchors_the_moved_latest_block_is_still_the_anchor(tmp_path):
    case = setup()
    _moved_chain(case)
    with pytest.raises(AssertionError):  # synthetic node only serves the pinned block for code/views
        collect(tmp_path, case)


@pytest.mark.parametrize('chain', ['pbc', 'dbc'])
def test_explicit_anchor_hash_must_match_the_node(tmp_path, chain):
    case = setup()
    anchors = _anchors(case)
    real = anchors[chain]['hash']
    anchors[chain]['hash'] = '0x' + ('cd' if real[2:4] == 'ab' else 'ab') * 32
    assert anchors[chain]['hash'] != real
    with pytest.raises(BAD):
        collect(tmp_path, case, anchors=anchors)
    assert not (tmp_path / 'collection/result.json').exists()


@pytest.mark.parametrize('mutate', [
    lambda a: a.pop('dbc'), lambda a: a.update(extra=a['pbc']), lambda a: a['pbc'].pop('hash'),
    lambda a: a['pbc'].update(number=7), lambda a: a['pbc'].update(number='07'),
    lambda a: a['dbc'].update(hash='0x12'), lambda a: a.update(pbc=None)])
def test_anchor_inventory_is_closed_and_refused_before_io(tmp_path, mutate):
    case = setup()
    anchors = _anchors(case)
    mutate(anchors)
    with pytest.raises(BAD):
        collect(tmp_path, case, anchors=anchors)
    assert not (tmp_path / 'collection').exists()
    assert all(not rpc.calls for rpc in case[4].values())
