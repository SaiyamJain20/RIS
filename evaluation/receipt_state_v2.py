"""Join one F receipt signature to supplied raw grant/request/event captures.

Paper-derived HMBC2020 extension, internal API only. The caller pins context,
ABIs and observations in a declared safe-ledger interval. Supplied bytes do not
prove RPC truth, ancestry, signing time, latest head, complete logs/history,
persistence, producer behavior, a quorum, delivery or any integrated gate.
"""
from eth_abi import encode
from eth_utils import keccak

from evaluation.evm import AbiContract, _hex
from evaluation.schema_v2 import validate
from evaluation.signing_context_v2 import verify_bound_signature
from evaluation.witness_native_v2 import _quantity


def _require(condition, message):
    if not condition:
        raise ValueError('Invalid receipt state: '+message)


def verify_receipt_signature(message, signature, *, owner, manifest, observations,
                             abi_paths, pbc_observation, dbc_observation,
                             blocks, calls, logs, compiled_max_admins=None):
    """Check one declared GrantIssued event, not completeness of an RPC range.

    blocks/calls use witness_native_v2 raw capture shapes. logs is a list with
    exactly one raw KSSC GrantIssued log, including blockNumber and blockHash.
    Receipt reconciliation may occur after grant/request expiry; it grants no
    fresh release. Only this supplied state/event consistency is established.
    """
    _require(manifest.get('profileEnum') == '3', 'repaired-f profile required')
    checked=verify_bound_signature('GrantReceipt',message,signature,owner=owner,
        manifest=manifest,observations=observations,compiled_max_admins=compiled_max_admins)
    _require(isinstance(abi_paths,dict) and set(abi_paths)==set(manifest['abi']), 'ABI inventory')
    contracts={name:AbiContract(abi_paths[name],address,manifest['abi'][name]['abiSha256'])
        for chain in manifest['chains'].values() for name,address in chain['contracts'].items()}
    chain_ids={c['chainId'] for c in manifest['chains'].values()}
    _require(isinstance(blocks,list) and isinstance(calls,list), 'capture lists')
    headers,heights,raw_calls={},{},{}
    for row in blocks:
        _require(isinstance(row,dict) and set(row)=={'chainId','raw'}, 'block fields')
        _require(row['chainId'] in chain_ids, 'block chain')
        raw=row['raw']
        _require(isinstance(raw,dict) and {'number','hash','timestamp'}<=raw.keys(), 'block header')
        _hex(raw['hash'],32)
        number,timestamp=_quantity(raw['number']),_quantity(raw['timestamp'])
        key=row['chainId'],raw['hash'];height=row['chainId'],number
        _require(key not in headers, 'duplicate block')
        _require(height not in heights or heights[height]==raw['hash'], 'conflicting safe block hashes')
        headers[key]=(number,timestamp);heights[height]=raw['hash']
    for row in calls:
        _require(isinstance(row,dict) and set(row)=={'chainId','blockHash','to','data','result'}, 'call fields')
        _require(row['chainId'] in chain_ids, 'call chain')
        _hex(row['blockHash'],32);_hex(row['to'],20);_hex(row['data']);_hex(row['result'])
        key=row['chainId'],row['blockHash'],row['to'],row['data']
        _require(key not in raw_calls, 'duplicate call')
        raw_calls[key]=row['result']
    used_blocks,used_calls=set(),set()

    def header(chain,number,hash_,timestamp=None):
        key=chain,hash_
        _require(key in headers, 'missing raw block')
        n,ts=headers[key]
        _require(n==number and (timestamp is None or timestamp==ts), 'block observation mismatch')
        used_blocks.add(key)
        return ts

    for chain,ob in (('pbc',pbc_observation),('dbc',dbc_observation)):
        validate('EvidenceObservation',ob)
        _require(ob['chainId']==manifest['chains'][chain]['chainId'], 'observation chain')
        header(ob['chainId'],ob['blockNumber'],ob['blockHash'],ob['timestamp'])

    def read(name,getter,ob,arg):
        contract=contracts[name]
        _require(contract._function(getter).get('stateMutability') in ('view','pure'), 'read-only getter')
        key=ob['chainId'],ob['blockHash'],contract.address,contract.calldata(getter,arg)
        _require(key in raw_calls, 'missing exact state call')
        used_calls.add(key)
        return contract.decode_return(getter,raw_calls[key])

    expected_id='0x'+keccak(encode(['bytes32','address','uint256'],
        [_hex(message['requestDigest'],32),message['kssc'],int(message['dbcChainId'])])).hex()
    _require(message['grantId']==expected_id, 'grant id')
    grant,=read('KSSC','grantDetails',dbc_observation,message['grantId'])
    _require(grant['exists'] is True and grant['allowed'] is True, 'allowed grant required')
    for field,target in (('requestDigest','requestDigest'),('gid','gid'),('dataId','dataId'),
                         ('keyEpoch','keyEpoch'),('expiresAt','grantExpiresAt')):
        _require(grant[field]==message[target], 'grant '+field)
    request,=read('PSC','getRequest',pbc_observation,message['requestDigest'])
    _require(request['status']=='1', 'pending request required')
    for field,target in (('gid','gid'),('dataId','dataId'),('destinationChainId','dbcChainId'),('kssc','kssc')):
        _require(request[field]==message[target], 'request '+field)
    _require(0<int(message['grantExpiresAt'])<=int(request['expiresAt']), 'request expiry bound')

    _require(isinstance(logs,list) and len(logs)==1, 'one declared grant event required')
    log=logs[0]
    _require(isinstance(log,dict), 'log object')
    event=contracts['KSSC'].decode_log(log)
    _require(event is not None and event['name']=='GrantIssued', 'GrantIssued event required')
    fields=event['fields']
    _require(fields['grantId']==message['grantId'], 'event grant id')
    for field in ('requestDigest','gid','dataId','keyEpoch','expiresAt','recipientKeyHash'):
        _require(fields[field]==grant[field], 'event '+field)
    _require(_quantity(log.get('blockNumber'))==message['dbcBlockNumber']
             and log.get('blockHash')==message['dbcBlockHash'], 'event block reference')
    issued_at=header(message['dbcChainId'],message['dbcBlockNumber'],message['dbcBlockHash'])
    _require(issued_at==grant['issuedAt'], 'grant issuance timestamp')
    _require(int(message['dbcBlockNumber'])<=int(dbc_observation['blockNumber'])
             and int(issued_at)<=int(dbc_observation['timestamp']), 'event after observation')
    _require(used_blocks==set(headers), 'unused block')
    _require(used_calls==set(raw_calls), 'unused state call')
    return checked | dict(owner=owner,sourceStateChecked=True,declaredEventChecked=True,
        signTimeEstablished=False,latestHeadEstablished=False,logCompletenessEstablished=False,
        blocksChecked=len(used_blocks),callsChecked=len(used_calls))
