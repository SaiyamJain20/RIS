"""Acquire successor deployment observations through pinned public ABIs.

Use the existing loopback-only, tool-pinned RpcClient in an authorized execution
recipe. Injected transports are useful for synthetic tests, never chain evidence.
Raw calls survive failure; normalized observations publish only after all joins.
Block identity bracketing checks RPC consistency under safe-ledger assumptions,
not source/constructor attestation, transient reorg absence or consensus safety.
No existing consumer is switched, and this API does not authorize services.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import time

from evaluation.binding_context_v2 import _expected_views, reconstruct
from evaluation.evm import AbiContract, _hex
from evaluation.manifests import canonical_hash, now
from evaluation.native import _quantity
from evaluation.schema_v2 import validate


def _require(condition, message):
    if not condition:
        raise ValueError('Invalid public deployment observations: ' + message)


def _block(raw, number=None):
    _require(isinstance(raw, dict) and {'number', 'hash'} <= raw.keys(), 'missing block')
    actual = str(_quantity(raw['number']))
    _hex(raw['hash'], 32)
    _require(number is None or actual == number, 'block number mismatch')
    return {'number': actual, 'hash': raw['hash']}


def collect(manifest, rpcs, abi_paths, *, output, compiled_max_admins=None, timeout=10.0, anchors=None):
    """Return {observations, document}, retaining raw calls in a fresh directory.

    manifest and compiled_max_admins are caller-selected reviewed pins, not a
    producer export's assertion. rpcs is exactly pbc/dbc -> RpcClient; abi_paths
    is exactly contract name -> exact owner-exported ABI file. All code/getter
    requests use the selected explicit historical block. A finite whole-call
    deadline is checked around transport calls; the RpcClient has a separate
    per-call subprocess timeout. A blocking custom transport cannot be preempted.

    anchors=None reads at each chain's latest block. Otherwise it is exactly
    pbc/dbc -> {number (canonical decimal string), hash}: every code/getter read
    uses that block and its hash must equal the node's. A producer export's
    anchor is fixed at store initialization, so joining one needs this selection.

    The transcript records API-level raw results and call parameters; RpcClient
    separately retains command/output hashes and tool/endpoint provenance. A
    transcript alone is neither authenticated evidence nor a light-client proof.
    """
    _require(type(timeout) in (float, int) and math.isfinite(timeout) and timeout > 0,
             'finite positive timeout required')
    pin = copy.deepcopy(manifest)
    marker = pin.get('schemaVersion') if isinstance(pin, dict) else None
    _require(marker in ('hmbc-ledger-deployment/v2', 'hmbc-ledger-deployment/v2.1'), 'unselected carrier')
    validate('LedgerDeployment', pin, schema_revision='v2.1' if marker.endswith('/v2.1') else 'v2')
    expected = _expected_views(pin)
    if anchors is not None:
        _require(isinstance(anchors, dict) and set(anchors) == {'pbc', 'dbc'}, 'anchor inventory')
        anchors = copy.deepcopy(anchors)
        for row in anchors.values():
            _require(isinstance(row, dict) and set(row) == {'number', 'hash'}, 'anchor shape')
            _require(type(row['number']) is str and row['number'].isascii() and row['number'].isdigit()
                     and str(int(row['number'])) == row['number'], 'anchor number')
            _hex(row['hash'], 32)
    _require(isinstance(rpcs, dict) and set(rpcs) == {'pbc', 'dbc'}, 'RPC inventory')
    _require(isinstance(abi_paths, dict) and set(abi_paths) == set(pin['abi']), 'ABI inventory')
    # Snapshot caller containers before any transport can yield or mutate them.
    clients = dict(rpcs)
    contracts = {}
    for chain in pin['chains'].values():
        for name, address in chain['contracts'].items():
            contracts[name] = AbiContract(abi_paths[name], address, pin['abi'][name]['abiSha256'])
            for getter in expected[name]:
                function = contracts[name]._function(getter)
                _require(function.get('stateMutability') in ('view', 'pure') and len(function['outputs']) == 1,
                         'getter ABI must be a single-output view')
                args = [pin['chains']['dbc']['chainId']] if getter == 'ksscForChain' else []
                contracts[name].calldata(getter, *args)

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    transcript = {'status': 'collecting', 'startedAt': now(),
                  'manifestSha256': canonical_hash(pin),
                  'abiSha256': {n: c.abi_sha256 for n, c in contracts.items()},
                  'timeoutSeconds': timeout, 'maxCalls': 128, 'calls': []}

    def save():
        (output / 'transcript.json').write_text(json.dumps(transcript, indent=2) + '\n')

    deadline = time.monotonic() + timeout

    def budget():
        if time.monotonic() >= deadline:
            raise TimeoutError('Public deployment collection deadline exceeded')

    def call(chain, method, params=None):
        budget()
        _require(len(transcript['calls']) < 128, 'RPC call budget exceeded')
        params = [] if params is None else params
        row = {'chain': chain, 'method': method, 'params': copy.deepcopy(params), 'status': 'started'}
        transcript['calls'].append(row)
        save()
        try:
            raw = clients[chain].call(method, params)
        except Exception as error:
            row.update(status='failed', exception=type(error).__name__)
            save()
            raise
        row.update(status='returned', result=copy.deepcopy(raw))
        save()
        budget()
        return raw

    def checkpoint(chain, label):
        # RpcClient checkpoint-policy clients must hash Cast at both boundaries.
        check = getattr(clients[chain], 'checkpoint', None)
        if check is not None:
            check(label)
        budget()

    def chain_id(chain):
        value = str(_quantity(call(chain, 'eth_chainId')))
        _require(value == pin['chains'][chain]['chainId'], chain + ' chain ID mismatch')
        return value

    def block(chain, number):
        return _block(call(chain, 'eth_getBlockByNumber', [hex(int(number)), False]), number)

    observations = {}
    save()
    try:
        for chain in ('pbc', 'dbc'):
            checkpoint(chain, 'binding-read-before')
            observed = {'chainId': chain_id(chain)}
            observed['genesisHash'] = block(chain, '0')['hash']
            observed['deployBlock'] = block(chain, pin['chains'][chain]['deployBlock'])
            if anchors is None:
                anchor = _block(call(chain, 'eth_getBlockByNumber', ['latest', False]))
            else:
                anchor = block(chain, anchors[chain]['number'])
                _require(anchor['hash'] == anchors[chain]['hash'], chain + ' anchor hash mismatch')
            _require(int(anchor['number']) >= int(observed['deployBlock']['number']), 'anchor before deployment')
            observed.update(anchor=anchor, code={}, views={})
            number = hex(int(anchor['number']))
            for name, address in pin['chains'][chain]['contracts'].items():
                raw = call(chain, 'eth_getCode', [address, number])
                observed['code'][name] = {'anchor': copy.deepcopy(anchor), 'value': raw}
                observed['views'][name] = {}
                contract = contracts[name]
                for getter in expected[name]:
                    args = [pin['chains']['dbc']['chainId']] if getter == 'ksscForChain' else []
                    data = contract.calldata(getter, *args)
                    raw = call(chain, 'eth_call', [{'to': address, 'data': data}, number])
                    value, = contract.decode_return(getter, raw)
                    observed['views'][name][getter] = {'anchor': copy.deepcopy(anchor), 'value': value}
            observations[chain] = observed

        # Recheck BOTH chains after all reads: PBC may drift while DBC is read.
        for chain in ('pbc', 'dbc'):
            observed = observations[chain]
            observed['confirmedAnchor'] = block(chain, observed['anchor']['number'])
            _require(observed['confirmedAnchor'] == observed['anchor'], chain + ' anchor changed')
            _require(block(chain, '0')['hash'] == observed['genesisHash'], chain + ' genesis changed')
            _require(block(chain, observed['deployBlock']['number']) == observed['deployBlock'], chain + ' deploy block changed')
            chain_id(chain)
            checkpoint(chain, 'binding-read-after')
        for contract in contracts.values():
            _require(hashlib.sha256(contract.path.read_bytes()).hexdigest() == contract.abi_sha256, 'ABI changed')
        _require(manifest == pin, 'manifest changed')
        document = reconstruct(pin, observations, compiled_max_admins=compiled_max_admins)
        budget()
        result = {'observations': observations, 'document': document}
        # Keep an interrupted/failed write out of the published result path.
        pending = output / 'result.pending.json'
        pending.write_text(json.dumps(result, indent=2) + '\n')
        transcript.update(status='complete', endedAt=now(), resultSha256=canonical_hash(result))
        save()
        pending.rename(output / 'result.json')
        return result
    except Exception as error:
        transcript.update(status='failed', endedAt=now(), exception=type(error).__name__)
        save()
        raise
