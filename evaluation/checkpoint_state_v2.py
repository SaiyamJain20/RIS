"""Check one checkpoint signature against supplied raw state and clock captures.

Paper-derived HMBC2020 reconstruction/extension, internal API. This verifies
consistency of independently selected context, signature and hash-selected public
ABI captures. It authenticates no RPC, ancestry, latest head or actual sign time.
The caller must establish acquisition provenance and join history/store coverage
separately. No service, consumer switch, quorum or integrated E/F result follows.
Fault/clear histories and their mutation exclusions are outside this per-signature
API; it must not be used to relabel them as safe-ledger evidence.
"""
from evaluation.evm import AbiContract, _hex
from evaluation.schema_v2 import validate
from evaluation.signing_context_v2 import verify_bound_signature
from evaluation.witness_native_v2 import _quantity


def _require(condition, message):
    if not condition:
        raise ValueError('Invalid checkpoint state: ' + message)


def verify_checkpoint_signature(message, signature, *, owner, manifest,
                                observations, abi_paths, pbc_head,
                                dbc_observation, blocks, calls,
                                compiled_max_admins=None):
    """Verify R6 checkpoint duties against exact supplied PBC/DBC observations.

    blocks/calls use the raw capture shapes of witness_native_v2. All required
    captures must be present, canonical, unique and used. The window is relative
    to supplied dbc_observation, never a claim that signing happened at that time.
    A source older than pbc_head is allowed if its epochs remain semantically
    current. Cross-height ancestry and contemporaneous capture remain unproved.
    """
    _require(manifest.get('profileEnum') == '3', 'repaired-f profile required')
    checked = verify_bound_signature('StateCheckpoint', message, signature,
        owner=owner, manifest=manifest, observations=observations,
        compiled_max_admins=compiled_max_admins)
    _require(isinstance(abi_paths, dict) and set(abi_paths) == set(manifest['abi']), 'ABI inventory')
    contracts = {name: AbiContract(abi_paths[name], address, manifest['abi'][name]['abiSha256'])
                 for chain in manifest['chains'].values() for name, address in chain['contracts'].items()}
    pbc, dbc = (manifest['chains'][c] for c in ('pbc', 'dbc'))
    chain_ids = {pbc['chainId'], dbc['chainId']}
    for ob, chain in ((pbc_head, pbc), (dbc_observation, dbc)):
        validate('EvidenceObservation', ob)
        _require(ob['chainId'] == chain['chainId'], 'observation chain')
    _require(isinstance(blocks, list) and isinstance(calls, list), 'capture lists')
    headers, raw_calls = {}, {}
    for row in blocks:
        _require(isinstance(row, dict) and set(row) == {'chainId', 'raw'}, 'block fields')
        _require(row['chainId'] in chain_ids, 'block chain')
        raw = row['raw']
        _require(isinstance(raw, dict) and {'number','hash','timestamp'} <= raw.keys(), 'block header')
        _hex(raw['hash'], 32)
        key = row['chainId'], raw['hash']
        _require(key not in headers, 'duplicate block')
        headers[key] = (_quantity(raw['number']), _quantity(raw['timestamp']))
    for row in calls:
        _require(isinstance(row, dict) and set(row) == {'chainId','blockHash','to','data','result'}, 'call fields')
        _require(row['chainId'] in chain_ids, 'call chain')
        _hex(row['blockHash'], 32); _hex(row['to'], 20)
        _hex(row['data']); _hex(row['result'])
        key = row['chainId'], row['blockHash'], row['to'], row['data']
        _require(key not in raw_calls, 'duplicate call')
        raw_calls[key] = row['result']
    used_blocks, used_calls = set(), set()

    def header(chain_id, number, hash_, timestamp=None):
        key = chain_id, hash_
        _require(key in headers, 'missing block')
        n, ts = headers[key]
        _require(n == number and (timestamp is None or ts == timestamp), 'block observation mismatch')
        used_blocks.add(key)

    def read(chain, at, name, getter):
        contract = contracts[name]
        _require(contract._function(getter).get('stateMutability') in ('view','pure'), 'read-only getter')
        key = chain['chainId'], at, contract.address, contract.calldata(getter)
        _require(key in raw_calls, 'missing exact state call')
        result = contract.decode_return(getter, raw_calls[key])
        used_calls.add(key)
        return result

    n, h = message['sourceBlockNumber'], message['sourceBlockHash']
    header(pbc['chainId'], n, h)
    for ob in (pbc_head, dbc_observation):
        header(ob['chainId'], ob['blockNumber'], ob['blockHash'], ob['timestamp'])
    _require(int(n) <= int(pbc_head['blockNumber']), 'source after supplied head')
    _require(n != pbc_head['blockNumber'] or h == pbc_head['blockHash'], 'source/head hash mismatch')
    exists, current = read(dbc, dbc_observation['blockHash'], 'KSSC', 'currentCheckpoint')
    expected = int(current['sequence']) + 1 if exists else 1
    _require(int(message['sequence']) == expected, 'next sequence')
    _require(not exists or int(n) >= int(current['sourceBlockNumber']), 'source block regression')
    _require(message['keyEpoch'] == '0', 'key epoch must be zero')
    for field, contract, getter in (('authEpoch','TMSC','authEpoch'),
                                    ('policyVersion','PSC','policyVersion'),
                                    ('witnessSetVersion','PSC','witnessSetVersion')):
        value, = read(pbc, h, contract, getter)
        _require(message[field] == value, 'source state ' + field)
        if field != 'witnessSetVersion':
            latest, = read(pbc, pbc_head['blockHash'], contract, getter)
            _require(message[field] == latest, 'semantic freshness ' + field)
    ttl, = read(dbc, dbc_observation['blockHash'], 'KSSC', 'maxCheckpointTtl')
    ts, expiry = int(dbc_observation['timestamp']), int(message['expiresAt'])
    _require(ts < expiry <= ts + int(ttl), 'expiry window')
    _require(used_blocks == set(headers), 'unused block')
    _require(used_calls == set(raw_calls), 'unused state call')
    return checked | dict(owner=owner, sourceStateChecked=True, suppliedWindowChecked=True,
                          blocksChecked=len(used_blocks), callsChecked=len(used_calls))
