"""Acquire declared witness history through caller-selected public RPC clients.

Paper-derived HMBC2020 reconstruction/extension; internal API only. This retains
API-level parameters/results and uses EIP-1898 hash-selected death getters.
RpcClient separately retains CLI/tool/endpoint receipts. Before/after identity
checks detect endpoint inconsistency; they authenticate no RPC or consensus.
A consistently lying transport can pass. No source-state/sign-time, exporter/store
completeness, arrival, durability or integrated E/F claim follows. This API does
not authorize services or switch an existing consumer. Node support is required;
there is deliberately no numeric-block fallback for hash-selected eth_call.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import time

from eth_abi import encode
from eth_utils import keccak

from evaluation.evm import AbiContract, _hex
from evaluation.manifests import canonical_hash, now
from evaluation.witness_history_v2 import verify_signed_history
from evaluation.witness_native_v2 import _quantity, verify_native_history


def _require(condition, message):
    if not condition:
        raise ValueError('Invalid history RPC capture: ' + message)


def _header(raw, *, timestamp=False):
    _require(isinstance(raw, dict) and {'number', 'hash'} <= raw.keys(), 'missing block')
    value = {'number': _quantity(raw['number']), 'hash': raw['hash']}
    _hex(value['hash'], 32)
    if timestamp:
        _require('timestamp' in raw, 'missing block timestamp')
        value['timestamp'] = _quantity(raw['timestamp'])
    return value


def _plan(evidence, manifest, contracts):
    """Plan exact required captures; final native verification checks all joins."""
    blocks, calls = {}, {}

    def block(chain, number, hash_):
        key = chain, hash_
        _require(key not in blocks or blocks[key] == number, 'one hash at multiple heights')
        blocks[key] = number

    def observation(ob):
        block(ob['chainId'], ob['blockNumber'], ob['blockHash'])

    def call(ob, name, getter, *args):
        contract = contracts[name]
        _require(contract._function(getter).get('stateMutability') in ('view', 'pure'), 'read-only death getter')
        calls[(ob['chainId'], ob['blockHash'], contract.address, contract.calldata(getter, *args))] = None

    for ob in evidence['observations']:
        observation(ob)
    faults = ([evidence['faulted']] if evidence['faulted'] else []) + [r['fault'] for r in evidence['faultLog']]
    for row in faults:
        observation(row['previous']); observation(row['observed'])
    for row in evidence['faultLog']:
        observation(row['clearedAgainst'])
    for row in evidence['superseded'] + evidence['conflicts']:
        for signed in row['digests']:
            observation(signed['observation'])
        effect = row['effect']
        if row['type'] in ('AccessDecision', 'StateCheckpoint'):
            block(manifest['chains']['pbc']['chainId'], effect['sourceBlockNumber'], effect['sourceBlockHash'])
        elif row['type'] == 'GrantReceipt':
            block(manifest['chains']['dbc']['chainId'], effect['dbcBlockNumber'], effect['dbcBlockHash'])
        if 'death' not in row:
            continue
        death = row['death']; ob = death['observation']; kind = death['kind']
        observation(ob)
        if kind in ('overtaken-checkpoint', 'overtaken-decision-sequence'):
            call(ob, 'KSSC', 'currentCheckpoint')
        elif kind == 'overtaken-governance':
            call(ob, 'Governance', 'governanceNonce')
        elif kind == 'overtaken-decision-grant':
            dbc = manifest['chains']['dbc']
            grant_id = '0x' + keccak(encode(['bytes32', 'address', 'uint256'],
                [_hex(row['keyField'], 32), dbc['contracts']['KSSC'], int(dbc['chainId'])])).hex()
            call(ob, 'KSSC', 'grantDetails', grant_id)
        elif kind == 'executed-receipt':
            call(ob, 'PSC', 'getRequest', row['keyField'])
    return blocks, calls


def collect(evidence, *, manifest, observations, expected_owner, abi_paths, rpcs,
            output, compiled_max_admins=None, timeout=10.0, max_calls=1024):
    """Return {blocks, calls, verification}; retain raw transcript on failure.

    Inputs must be independently selected reviewed pins. rpcs is exactly pbc/dbc
    -> RpcClient (or synthetic transport with call/checkpoint/url). Each url must
    match the selected manifest. Hash getters use requireCanonical=true for a
    declared safe interval and false for an explicitly labelled fault interval.
    Fault captures retain separate hashes at one height. Identity/genesis/deploy/
    binding-anchor checks surround ALL cross-chain reads, including empty history.

    timeout and max_calls bound this acquisition, not an experiment's liveness.
    A blocking injected transport cannot be preempted here; RpcClient supplies its
    own per-call timeout. No fallback, retry or service is started by this helper.
    """
    _require(type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0, 'finite positive timeout')
    _require(type(max_calls) is int and max_calls > 0, 'positive integer call budget')
    m, o, e = copy.deepcopy((manifest, observations, evidence))
    checked = verify_signed_history(e, manifest=m, observations=o, expected_owner=expected_owner,
                                   compiled_max_admins=compiled_max_admins)
    _require(isinstance(rpcs, dict) and set(rpcs) == {'pbc', 'dbc'}, 'RPC inventory')
    clients = dict(rpcs)
    origins = {c: getattr(clients[c], 'url', None) for c in clients}
    _require(all(origins[c] == m['chains'][c]['rpcUrl'] for c in clients), 'RPC origin mismatch')
    _require(isinstance(abi_paths, dict) and set(abi_paths) == set(m['abi']), 'ABI inventory')
    paths = dict(abi_paths)
    contracts = {n: AbiContract(paths[n], a, m['abi'][n]['abiSha256'])
                 for chain in m['chains'].values() for n, a in chain['contracts'].items()}
    required_blocks, required_calls = _plan(e, m, contracts)
    names = {v['chainId']: c for c, v in m['chains'].items()}
    safe = checked['declaredSafeLedgerInterval']
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    transcript = dict(status='collecting', startedAt=now(), timeoutSeconds=timeout,
        maxCalls=max_calls, manifestSha256=canonical_hash(m), evidenceSha256=canonical_hash(e),
        observationsSha256=canonical_hash(o), abiSha256={n:c.abi_sha256 for n,c in contracts.items()},
        declaredSafeLedgerInterval=safe, calls=[])
    deadline = time.monotonic() + timeout

    def save():
        (output/'transcript.json').write_text(json.dumps(transcript, indent=2, allow_nan=False)+'\n')

    def budget():
        if time.monotonic() >= deadline:
            raise TimeoutError('History RPC capture deadline exceeded')

    def rpc(chain, method, params):
        budget()
        _require(len(transcript['calls']) < max_calls, 'RPC call budget exceeded')
        row = dict(chain=chain, origin=origins[chain], method=method,
                   params=copy.deepcopy(params), status='started')
        transcript['calls'].append(row); save()
        try:
            raw = clients[chain].call(method, copy.deepcopy(params))
        except Exception as error:
            row.update(status='failed', exception=type(error).__name__); save()
            raise
        row.update(status='returned', result=copy.deepcopy(raw)); save(); budget()
        return copy.deepcopy(raw)

    def checkpoint(chain, label):
        check = getattr(clients[chain], 'checkpoint', None)
        if check is not None:
            check(label)
        budget()

    def identity(chain):
        _require(_quantity(rpc(chain, 'eth_chainId', [])) == m['chains'][chain]['chainId'], chain+' chain ID mismatch')
        expected = [{'number':'0', 'hash':o[chain]['genesisHash']}, o[chain]['deployBlock'], o[chain]['anchor']]
        for pin in expected:
            raw = rpc(chain, 'eth_getBlockByNumber', [hex(int(pin['number'])), False])
            _require(_header(raw) == pin, chain+' deployment identity mismatch')

    def header(chain_id, hash_, number):
        chain = names[chain_id]
        raw = rpc(chain, 'eth_getBlockByHash', [hash_, False])
        normalized = _header(raw, timestamp=True)
        _require(normalized['hash'] == hash_ and normalized['number'] == number, 'selected block mismatch')
        if safe:
            current = rpc(chain, 'eth_getBlockByNumber', [hex(int(number)), False])
            _require(_header(current, timestamp=True) == normalized, 'canonical block mismatch')
        return raw, normalized

    save()
    try:
        for chain in ('pbc','dbc'):
            checkpoint(chain, 'history-read-before'); identity(chain)
        blocks, calls, headers = [], [], {}
        for (chain_id, hash_), number in required_blocks.items():
            raw, normalized = header(chain_id, hash_, number)
            blocks.append(dict(chainId=chain_id, raw=raw)); headers[(chain_id,hash_)]=normalized
        for chain_id, hash_, to, data in required_calls:
            raw = rpc(names[chain_id], 'eth_call', [{'to':to,'data':data}, {'blockHash':hash_,'requireCanonical':safe}])
            calls.append(dict(chainId=chain_id, blockHash=hash_, to=to, data=data, result=raw))
        # Recheck after every read on BOTH chains, including all faulted hashes.
        for (chain_id,hash_), number in required_blocks.items():
            _, confirmed = header(chain_id, hash_, number)
            _require(confirmed == headers[(chain_id,hash_)], 'block changed after capture')
        for chain in ('pbc','dbc'):
            identity(chain); checkpoint(chain, 'history-read-after')
        _require(manifest==m and observations==o and evidence==e, 'caller input changed')
        _require(set(rpcs)==set(clients) and all(rpcs[c] is clients[c] and getattr(clients[c],'url',None)==origins[c] for c in clients), 'RPC inventory changed')
        _require(abi_paths==paths, 'ABI path selection changed')
        for contract in contracts.values():
            _require(hashlib.sha256(contract.path.read_bytes()).hexdigest()==contract.abi_sha256, 'ABI changed')
        verified = verify_native_history(e, manifest=m, observations=o, expected_owner=expected_owner,
            abi_paths=paths, blocks=blocks, calls=calls, compiled_max_admins=compiled_max_admins)
        budget()
        result = dict(blocks=blocks, calls=calls, verification=verified)
        pending = output/'result.pending.json'
        pending.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
        transcript.update(status='complete', endedAt=now(), resultSha256=canonical_hash(result))
        save(); budget(); pending.rename(output/'result.json')
        return result
    except Exception as error:
        transcript.update(status='failed', endedAt=now(), exception=type(error).__name__); save()
        raise
