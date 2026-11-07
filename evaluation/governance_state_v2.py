"""Check one governance signature against supplied PBC state and approval.

Paper-derived HMBC2020 extension, internal API only. The caller independently
pins context, ABI paths, observation and a TEST-ONLY local approval fixture.
Matching these bytes authenticates neither RPC nor actual signing time, latest
head, witness policy/configuration, complete store/history or a quorum. History
and fault/clear scope must be joined separately; no consumer is switched here.
"""
from evaluation.evm import AbiContract, _hex
from evaluation.schema_v2 import validate
from evaluation.signing_context_v2 import verify_bound_signature
from evaluation.witness_native_v2 import _quantity


def _require(condition, message):
    if not condition:
        raise ValueError('Invalid governance state: ' + message)


def verify_governance_signature(message, signature, *, owner, manifest,
                                observations, abi_paths, pbc_observation,
                                blocks, calls, approvals,
                                compiled_max_admins=None):
    """Verify R6 duties at the exact supplied PBC hash and clock observation.

    blocks/calls use the raw capture shapes of witness_native_v2. Only required
    captures are accepted. approvals is a list of closed {action,root,admins}
    tuples; each is validated, and one must exactly match this message. Caller
    assertions are not evidence of what a producer actually approved or read.
    """
    _require(manifest.get('profileEnum') == '3', 'repaired-f profile required')
    checked = verify_bound_signature('GovernanceAction', message, signature,
        owner=owner, manifest=manifest, observations=observations,
        compiled_max_admins=compiled_max_admins)
    _require(isinstance(approvals, list), 'approval list')
    fields = {'action', 'root', 'admins'}
    for approval in approvals:
        _require(isinstance(approval, dict) and set(approval) == fields, 'approval fields')
        validate('GovernanceAction', message | approval)
    _require({k:message[k] for k in fields} in approvals, 'approval tuple missing')

    _require(isinstance(abi_paths, dict) and set(abi_paths) == set(manifest['abi']), 'ABI inventory')
    contracts = {name: AbiContract(abi_paths[name], address, manifest['abi'][name]['abiSha256'])
                 for chain in manifest['chains'].values() for name, address in chain['contracts'].items()}
    pbc = manifest['chains']['pbc']
    validate('EvidenceObservation', pbc_observation)
    _require(pbc_observation['chainId'] == pbc['chainId'], 'observation chain')
    _require(isinstance(blocks, list) and isinstance(calls, list), 'capture lists')
    headers, raw_calls = {}, {}
    for row in blocks:
        _require(isinstance(row, dict) and set(row) == {'chainId', 'raw'}, 'block fields')
        _require(row['chainId'] == pbc['chainId'], 'block chain')
        raw = row['raw']
        _require(isinstance(raw, dict) and {'number','hash','timestamp'} <= raw.keys(), 'block header')
        _hex(raw['hash'], 32)
        _require(raw['hash'] not in headers, 'duplicate block')
        headers[raw['hash']] = (_quantity(raw['number']), _quantity(raw['timestamp']))
    for row in calls:
        _require(isinstance(row, dict) and set(row) == {'chainId','blockHash','to','data','result'}, 'call fields')
        _require(row['chainId'] == pbc['chainId'], 'call chain')
        _hex(row['blockHash'], 32); _hex(row['to'], 20)
        _hex(row['data']); _hex(row['result'])
        key = row['blockHash'], row['to'], row['data']
        _require(key not in raw_calls, 'duplicate call')
        raw_calls[key] = row['result']
    at = pbc_observation['blockHash']
    _require(headers.get(at) == (pbc_observation['blockNumber'], pbc_observation['timestamp']),
             'block observation mismatch')
    _require(set(headers) == {at}, 'unused block')
    used_calls = set()

    def read(name, getter, *args):
        contract = contracts[name]
        _require(contract._function(getter).get('stateMutability') in ('view','pure'), 'read-only getter')
        key = at, contract.address, contract.calldata(getter, *args)
        _require(key in raw_calls, 'missing exact state call')
        result = contract.decode_return(getter, raw_calls[key])
        used_calls.add(key)
        return result

    nonce, = read('Governance', 'governanceNonce')
    _require(int(message['nonce']) == int(nonce) + 1, 'next nonce')
    version, = read('Governance', 'witnessSetVersion')
    _require(message['witnessSetVersion'] == version, 'state witness version')
    authority, = read('TMSC', 'isAuthority', message['root'])
    if message['action'] == '1':
        _require(authority is False, 'ADD existing authority')
        removed, = read('TMSC', 'removedAuthority', message['root'])
        _require(removed is False, 'ADD tombstone')
    else:
        _require(authority is True, 'REMOVE/SET missing authority')
    ttl, = read('Governance', 'maxGovernanceTtl')
    ts, expiry = int(pbc_observation['timestamp']), int(message['expiresAt'])
    _require(ts < expiry <= ts + int(ttl), 'expiry window')
    _require(used_calls == set(raw_calls), 'unused state call')
    return checked | dict(owner=owner, sourceStateChecked=True, suppliedWindowChecked=True,
                          approvalFixtureMatched=True, signTimeEstablished=False,
                          latestHeadEstablished=False, blocksChecked=1, callsChecked=len(used_calls))
