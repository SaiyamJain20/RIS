"""Capture retrospective governance state with explicit unsigned provenance.

Paper-derived HMBC2020 extension, internal API only. Exported observations and
caller TEST-ONLY approvals authenticate neither signing time nor witness policy.
Endpoint/header brackets detect inconsistent replies, not a consistently lying
RPC. No latest head, ancestry, native deaths, complete stores, quorum, consensus
or E/F gate follows. No existing consumer or frozen interface is changed.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import time

from evaluation.evm import AbiContract
from evaluation.governance_history_v2 import verify_governance_history
from evaluation.history_rpc_v2 import _header
from evaluation.manifests import canonical_hash, now
from evaluation.witness_history_v2 import verify_signed_history
from evaluation.witness_native_v2 import _quantity


def _require(condition, message):
    if not condition:
        raise ValueError('Invalid governance RPC capture: ' + message)


def _plan(evidence, manifest, contracts):
    blocks, calls, plans, provenance = {}, {}, [], []
    chain = manifest['chains']['pbc']['chainId']
    for collection in ('superseded', 'conflicts'):
        for index, row in enumerate(evidence[collection]):
            if row['type'] != 'GovernanceAction':
                continue
            for digest_index, signed in enumerate(row['digests']):
                observation = signed['observation']
                _require(observation['chainId'] == chain, 'PBC observation chain')
                at = observation['blockHash']
                fact = observation['blockNumber'], observation['timestamp']
                _require(at not in blocks or blocks[at] == fact, 'contradictory planned block')
                blocks[at] = fact
                getters = [('Governance', 'governanceNonce', ()),
                           ('Governance', 'witnessSetVersion', ()),
                           ('TMSC', 'isAuthority', (row['effect']['root'],)),
                           ('Governance', 'maxGovernanceTtl', ())]
                if row['effect']['action'] == '1':
                    getters.append(('TMSC', 'removedAuthority', (row['effect']['root'],)))
                keys = []
                for name, getter, args in getters:
                    contract = contracts[name]
                    _require(contract._function(getter).get('stateMutability') in ('view', 'pure'),
                             'read-only getter')
                    key = at, contract.address, contract.calldata(getter, *args)
                    calls[key] = None
                    keys.append(key)
                plans.append(dict(digest=signed['digest'], blockHash=at, callKeys=keys))
                provenance.append(dict(digest=signed['digest'], historyLocation=[collection,index,digest_index],
                    pbcObservation=observation, pbcObservationBasis='unsigned-exporter-observation',
                    signatureBindsObservation=False))
    return blocks, calls, plans, provenance


def collect(evidence, *, manifest, observations, expected_owner, abi_paths, approvals,
            approval_reason, rpcs, output, compiled_max_admins=None, timeout=10.0, max_calls=1024):
    """Capture every declared governance digest at its exact stored PBC hash.

    approvals is a separate caller TEST-ONLY list; approval_reason records its
    asserted provenance, never authenticates producer policy. rpcs is exactly
    pbc/dbc -> RpcClient (or synthetic call/checkpoint/url client). Both endpoints
    must match the selected deployment. EIP-1898 hash calls require canonicality
    only in declared safe intervals; there is no numeric/latest fallback or retry.
    Partial failures are saved; no complete result is published on refusal.
    A blocking injected call cannot be preempted here; RpcClient has a call timeout.
    """
    _require(type(timeout) in (int,float) and math.isfinite(timeout) and timeout > 0,
             'finite positive timeout')
    _require(type(max_calls) is int and max_calls > 0, 'positive integer call budget')
    _require(isinstance(approval_reason, str) and bool(approval_reason.strip()), 'approval reason')
    m, o, e, a = copy.deepcopy((manifest, observations, evidence, approvals))
    _require(m.get('profileEnum') == '3', 'repaired-f profile required')
    checked = verify_signed_history(e, manifest=m, observations=o, expected_owner=expected_owner,
                                    compiled_max_admins=compiled_max_admins)
    _require(isinstance(rpcs, dict) and set(rpcs) == {'pbc','dbc'}, 'RPC inventory')
    clients = dict(rpcs)
    origins = {c:getattr(clients[c], 'url', None) for c in clients}
    _require(all(origins[c] == m['chains'][c]['rpcUrl'] for c in clients), 'RPC origin mismatch')
    _require(isinstance(abi_paths, dict) and set(abi_paths) == set(m['abi']), 'ABI inventory')
    paths = dict(abi_paths)
    contracts = {n:AbiContract(paths[n], address, m['abi'][n]['abiSha256'])
                 for chain in m['chains'].values() for n,address in chain['contracts'].items()}
    required_blocks, required_calls, plans, provenance = _plan(e, m, contracts)
    safe = checked['declaredSafeLedgerInterval']
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    transcript = dict(status='collecting', startedAt=now(), timeoutSeconds=timeout, maxCalls=max_calls,
        manifestSha256=canonical_hash(m), evidenceSha256=canonical_hash(e),
        observationsSha256=canonical_hash(o), approvalsSha256=canonical_hash(a),
        approvalReason=approval_reason, approvalBasis='caller-supplied-test-only-fixture',
        abiSha256={n:c.abi_sha256 for n,c in contracts.items()}, declaredSafeLedgerInterval=safe,
        signTimeEstablished=False, latestHeadEstablished=False, approvalPolicyEstablished=False,
        provenance=provenance, calls=[])
    deadline = time.monotonic() + timeout

    def save():
        (output/'transcript.json').write_text(json.dumps(transcript, indent=2, allow_nan=False)+'\n')

    def budget():
        if time.monotonic() >= deadline:
            raise TimeoutError('Governance RPC capture deadline exceeded')

    def rpc(chain, method, params):
        budget()
        _require(len(transcript['calls']) < max_calls, 'RPC call budget exceeded')
        row = dict(chain=chain, origin=origins[chain], method=method,
                   params=copy.deepcopy(params), status='started')
        transcript['calls'].append(row)
        save()
        try:
            raw = clients[chain].call(method, copy.deepcopy(params))
        except Exception as error:
            row.update(status='failed', exception=type(error).__name__)
            save()
            raise
        row.update(status='returned', result=copy.deepcopy(raw))
        save()
        budget()
        return copy.deepcopy(raw)

    def checkpoint(chain, label):
        hook = getattr(clients[chain], 'checkpoint', None)
        if hook is not None:
            hook(label)
        budget()

    def identity(chain):
        _require(_quantity(rpc(chain, 'eth_chainId', [])) == m['chains'][chain]['chainId'],
                 chain+' chain ID mismatch')
        for pin in ({'number':'0', 'hash':o[chain]['genesisHash']}, o[chain]['deployBlock'], o[chain]['anchor']):
            raw = rpc(chain, 'eth_getBlockByNumber', [hex(int(pin['number'])),False])
            _require(_header(raw) == pin, chain+' deployment identity mismatch')

    def header(at, number, timestamp):
        raw = rpc('pbc', 'eth_getBlockByHash', [at,False])
        normalized = _header(raw, timestamp=True)
        _require(normalized == dict(number=number, hash=at, timestamp=timestamp), 'selected block mismatch')
        if safe:
            current = rpc('pbc', 'eth_getBlockByNumber', [hex(int(number)),False])
            _require(_header(current,timestamp=True) == normalized, 'canonical block mismatch')
        return dict(chainId=m['chains']['pbc']['chainId'], raw=raw)

    save()
    try:
        for chain in ('pbc','dbc'):
            checkpoint(chain, 'governance-read-before')
            identity(chain)
        blocks = {at:header(at, *fact) for at,fact in required_blocks.items()}
        calls = {}
        for at,to,data in required_calls:
            raw = rpc('pbc', 'eth_call', [{'to':to,'data':data}, {'blockHash':at,'requireCanonical':safe}])
            calls[(at,to,data)] = dict(chainId=m['chains']['pbc']['chainId'], blockHash=at,
                                      to=to, data=data, result=raw)
        for at,fact in required_blocks.items():
            header(at, *fact)
        for chain in ('pbc','dbc'):
            identity(chain)
            checkpoint(chain, 'governance-read-after')
        _require((manifest,observations,evidence,approvals) == (m,o,e,a), 'caller input changed')
        _require(set(rpcs) == set(clients) and all(rpcs[c] is clients[c] and getattr(clients[c],'url',None) == origins[c]
                 for c in clients), 'RPC inventory changed')
        _require(abi_paths == paths, 'ABI path selection changed')
        for contract in contracts.values():
            _require(hashlib.sha256(contract.path.read_bytes()).hexdigest() == contract.abi_sha256, 'ABI changed')
        captures = [dict(digest=p['digest'], blocks=[blocks[p['blockHash']]],
                         calls=[calls[k] for k in p['callKeys']]) for p in plans]
        verified = verify_governance_history(e, manifest=m, observations=o, expected_owner=expected_owner,
            abi_paths=paths, captures=captures, approvals=a, compiled_max_admins=compiled_max_admins)
        budget()
        result = dict(captures=captures, provenance=provenance, verification=verified,
                      signTimeEstablished=False, latestHeadEstablished=False, approvalPolicyEstablished=False)
        pending = output/'result.pending.json'
        pending.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
        transcript.update(status='complete', endedAt=now(), resultSha256=canonical_hash(result))
        save()
        budget()
        pending.rename(output/'result.json')
        return result
    except Exception as error:
        transcript.update(status='failed', endedAt=now(), exception=type(error).__name__)
        save()
        raise
