"""Acquire retrospective checkpoint state with explicit observation provenance.

Paper-derived HMBC2020 extension; internal API, no existing consumer switch.
The caller selects historical PBC observations. Stored DBC observations are
unsigned exporter data. Capturing them now cannot establish actual validation/
signing time, latest heads, RPC authenticity, ancestry or producer misconduct.
Endpoint/header brackets detect inconsistency, not a consistently lying RPC.
No native-death, store completeness, persistence, consensus or E/F gate claim.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import time

from evaluation.checkpoint_history_v2 import verify_checkpoint_history
from evaluation.evm import AbiContract
from evaluation.history_rpc_v2 import _header
from evaluation.manifests import canonical_hash, now
from evaluation.schema_v2 import validate
from evaluation.witness_history_v2 import verify_signed_history
from evaluation.witness_native_v2 import _quantity


def _require(condition, message):
    if not condition:
        raise ValueError('Invalid checkpoint RPC capture: ' + message)


def _plan(evidence, manifest, contracts, selections):
    _require(isinstance(selections, list), 'selection list')
    selected = {}
    for row in selections:
        _require(isinstance(row, dict) and set(row) == {'digest', 'pbcHead', 'reason'}, 'selection fields')
        _require(isinstance(row['digest'], str) and row['digest'] not in selected, 'duplicate/invalid digest')
        _require(isinstance(row['reason'], str) and bool(row['reason'].strip()), 'selection reason')
        validate('EvidenceObservation', row['pbcHead'])
        _require(row['pbcHead']['chainId'] == manifest['chains']['pbc']['chainId'], 'PBC observation chain')
        selected[row['digest']] = row
    expected = {s['digest'] for collection in ('superseded', 'conflicts')
                for r in evidence[collection] if r['type'] == 'StateCheckpoint' for s in r['digests']}
    _require(set(selected) == expected, 'exact checkpoint digest coverage')
    blocks, calls, plans, provenance = {}, {}, [], []
    pbc, dbc = (manifest['chains'][c] for c in ('pbc', 'dbc'))
    for collection in ('superseded', 'conflicts'):
        for index, row in enumerate(evidence[collection]):
            if row['type'] != 'StateCheckpoint':
                continue
            for digest_index, signed in enumerate(row['digests']):
                selection = selected[signed['digest']]
                head, target = selection['pbcHead'], signed['observation']
                block_keys, call_keys = [], []

                def block(chain, number, hash_, timestamp=None):
                    key = chain, hash_
                    if key in blocks:
                        old_n, old_t = blocks[key]
                        _require(old_n == number and (old_t is None or timestamp is None or old_t == timestamp),
                                 'contradictory planned block')
                        timestamp = old_t if timestamp is None else timestamp
                    blocks[key] = number, timestamp
                    if key not in block_keys:
                        block_keys.append(key)

                def call(chain, at, name, getter):
                    contract = contracts[name]
                    _require(contract._function(getter).get('stateMutability') in ('view','pure'), 'read-only getter')
                    key = chain['chainId'], at, contract.address, contract.calldata(getter)
                    calls[key] = None
                    if key not in call_keys:
                        call_keys.append(key)

                effect = row['effect']
                source_hash = effect['sourceBlockHash']
                block(pbc['chainId'], effect['sourceBlockNumber'], source_hash)
                for ob in (head, target):
                    block(ob['chainId'], ob['blockNumber'], ob['blockHash'], ob['timestamp'])
                for name, getter in (('TMSC','authEpoch'), ('PSC','policyVersion')):
                    call(pbc, source_hash, name, getter)
                    call(pbc, head['blockHash'], name, getter)
                call(pbc, source_hash, 'PSC', 'witnessSetVersion')
                for getter in ('currentCheckpoint', 'maxCheckpointTtl'):
                    call(dbc, target['blockHash'], 'KSSC', getter)
                plans.append(dict(digest=signed['digest'], pbcHead=head, blockKeys=block_keys, callKeys=call_keys))
                provenance.append(dict(digest=signed['digest'], historyLocation=[collection,index,digest_index],
                    pbcHead=head, dbcObservation=target, reason=selection['reason'],
                    pbcHeadBasis='caller-selected-historical-observation',
                    dbcObservationBasis='unsigned-exporter-observation',
                    signatureBindsPbcHeadOrDbcObservation=False))
    return blocks, calls, plans, provenance


def collect(evidence, *, manifest, observations, expected_owner, abi_paths, selections,
            rpcs, output, compiled_max_admins=None, timeout=10.0, max_calls=1024):
    """Collect every declared checkpoint's exact state; save partial failures.

    selections is exactly [{digest, pbcHead, reason}], without a target override.
    Reasons record caller assertions, never attestations. rpcs is exactly pbc/dbc
    -> RpcClient (or synthetic client with call/checkpoint/url). Each endpoint
    must match its independently selected manifest. EIP-1898 eth_call selectors
    have requireCanonical=true only for declared safe intervals. No fallback,
    service, latest-head lookup or retry. A blocking injected transport cannot
    be preempted here; RpcClient supplies its own call timeout.
    """
    _require(type(timeout) in (int,float) and math.isfinite(timeout) and timeout > 0, 'finite positive timeout')
    _require(type(max_calls) is int and max_calls > 0, 'positive integer call budget')
    m, o, e, s = copy.deepcopy((manifest, observations, evidence, selections))
    _require(m.get('profileEnum') == '3', 'repaired-f profile required')
    checked = verify_signed_history(e, manifest=m, observations=o, expected_owner=expected_owner,
                                    compiled_max_admins=compiled_max_admins)
    _require(isinstance(rpcs, dict) and set(rpcs) == {'pbc','dbc'}, 'RPC inventory')
    clients = dict(rpcs)
    origins = {c:getattr(clients[c], 'url', None) for c in clients}
    _require(all(origins[c] == m['chains'][c]['rpcUrl'] for c in clients), 'RPC origin mismatch')
    _require(isinstance(abi_paths, dict) and set(abi_paths) == set(m['abi']), 'ABI inventory')
    paths = dict(abi_paths)
    contracts = {n:AbiContract(paths[n], a, m['abi'][n]['abiSha256'])
                 for chain in m['chains'].values() for n,a in chain['contracts'].items()}
    required_blocks, required_calls, plans, provenance = _plan(e,m,contracts,s)
    names = {v['chainId']:c for c,v in m['chains'].items()}
    safe = checked['declaredSafeLedgerInterval']
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    transcript = dict(status='collecting', startedAt=now(), timeoutSeconds=timeout, maxCalls=max_calls,
        manifestSha256=canonical_hash(m), evidenceSha256=canonical_hash(e),
        observationsSha256=canonical_hash(o), selectionsSha256=canonical_hash(s),
        abiSha256={n:c.abi_sha256 for n,c in contracts.items()}, declaredSafeLedgerInterval=safe,
        signTimeEstablished=False, latestHeadEstablished=False, provenance=provenance, calls=[])
    deadline = time.monotonic() + timeout

    def save():
        (output/'transcript.json').write_text(json.dumps(transcript, indent=2, allow_nan=False)+'\n')

    def budget():
        if time.monotonic() >= deadline:
            raise TimeoutError('Checkpoint RPC capture deadline exceeded')

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
        hook = getattr(clients[chain], 'checkpoint', None)
        if hook is not None:
            hook(label)
        budget()

    def identity(chain):
        _require(_quantity(rpc(chain,'eth_chainId',[])) == m['chains'][chain]['chainId'], chain+' chain ID mismatch')
        for pin in ({'number':'0','hash':o[chain]['genesisHash']}, o[chain]['deployBlock'], o[chain]['anchor']):
            raw = rpc(chain, 'eth_getBlockByNumber', [hex(int(pin['number'])),False])
            _require(_header(raw) == pin, chain+' deployment identity mismatch')

    def header(chain_id, hash_, number, timestamp):
        chain = names[chain_id]
        raw = rpc(chain, 'eth_getBlockByHash', [hash_,False])
        normalized = _header(raw, timestamp=True)
        _require(normalized['hash'] == hash_ and normalized['number'] == number, 'selected block mismatch')
        _require(timestamp is None or normalized['timestamp'] == timestamp, 'selected timestamp mismatch')
        if safe:
            current = rpc(chain, 'eth_getBlockByNumber', [hex(int(number)),False])
            _require(_header(current,timestamp=True) == normalized, 'canonical block mismatch')
        return dict(chainId=chain_id, raw=raw), normalized

    save()
    try:
        for chain in ('pbc','dbc'):
            checkpoint(chain,'checkpoint-read-before'); identity(chain)
        blocks, headers, calls = {}, {}, {}
        for (chain_id,hash_), (number,timestamp) in required_blocks.items():
            blocks[(chain_id,hash_)], headers[(chain_id,hash_)] = header(chain_id,hash_,number,timestamp)
        for chain_id,hash_,to,data in required_calls:
            raw = rpc(names[chain_id], 'eth_call', [{'to':to,'data':data}, {'blockHash':hash_,'requireCanonical':safe}])
            calls[(chain_id,hash_,to,data)] = dict(chainId=chain_id, blockHash=hash_, to=to, data=data, result=raw)
        for (chain_id,hash_), (number,timestamp) in required_blocks.items():
            _, confirmed = header(chain_id,hash_,number,timestamp)
            _require(confirmed == headers[(chain_id,hash_)], 'block changed after capture')
        for chain in ('pbc','dbc'):
            identity(chain); checkpoint(chain,'checkpoint-read-after')
        _require((manifest,observations,evidence,selections) == (m,o,e,s), 'caller input changed')
        _require(set(rpcs) == set(clients) and all(rpcs[c] is clients[c] and getattr(clients[c],'url',None) == origins[c]
                 for c in clients), 'RPC inventory changed')
        _require(abi_paths == paths, 'ABI path selection changed')
        for contract in contracts.values():
            _require(hashlib.sha256(contract.path.read_bytes()).hexdigest() == contract.abi_sha256, 'ABI changed')
        captures = [dict(digest=p['digest'], pbcHead=p['pbcHead'], blocks=[blocks[k] for k in p['blockKeys']],
                         calls=[calls[k] for k in p['callKeys']]) for p in plans]
        verified = verify_checkpoint_history(e, manifest=m, observations=o, expected_owner=expected_owner,
            abi_paths=paths, captures=captures, compiled_max_admins=compiled_max_admins)
        budget()
        result = dict(captures=captures, provenance=provenance, verification=verified,
                      signTimeEstablished=False, latestHeadEstablished=False)
        pending = output/'result.pending.json'
        pending.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
        transcript.update(status='complete', endedAt=now(), resultSha256=canonical_hash(result))
        save(); budget(); pending.rename(output/'result.json')
        return result
    except Exception as error:
        transcript.update(status='failed', endedAt=now(), exception=type(error).__name__); save()
        raise
