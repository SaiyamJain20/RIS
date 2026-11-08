"""Join declared witness histories to supplied raw block and owner-ABI bytes.

Paper-derived HMBC2020 reconstruction/extension, internal API only. The caller
must independently select context, owner and ABI pins and acquire the captures.
This pure checker authenticates no RPC, chain, store or arrival history. Matching
bytes do not establish source-state truth, sign-time validity, exporter/store
completeness, persistence, consensus or an integrated E/F result. Fault/clear
intervals and mutation death exclusions remain explicit in the returned result.
"""
import re

from eth_abi import encode
from eth_utils import keccak

from evaluation.evm import AbiContract, _hex
from evaluation.schema_v2 import validate
from evaluation.witness_history_v2 import verify_signed_history


def _require(condition, message):
    if not condition:
        raise ValueError('Invalid native witness history: ' + message)


def _closed(value, fields, label):
    _require(isinstance(value, dict) and set(value) == set(fields), label + ' fields')


def _quantity(value):
    _require(isinstance(value, str) and re.fullmatch(r'0x(?:0|[1-9a-f][0-9a-f]*)', value),
             'noncanonical block quantity')
    result = str(int(value, 16))
    validate('Uint256', result)
    return result


def verify_native_history(evidence, *, manifest, observations, expected_owner,
                          abi_paths, blocks, calls, compiled_max_admins=None):
    """Check every declared observation and death against caller-supplied bytes.

    blocks is a list of {chainId, raw}, raw being an RPC block with number/hash/
    timestamp. calls is a list of {chainId, blockHash, to, data, result}, retaining
    raw eth_call input/output bytes at that block hash. Exact duplicate and unused
    captures refuse; identical required reads can share one capture. Blocks with
    different hashes at one height are retained only in declared fault/clear
    intervals, without making a canonical-chain claim. No RPC or file is written.
    """
    checked = verify_signed_history(evidence, manifest=manifest, observations=observations,
        expected_owner=expected_owner, compiled_max_admins=compiled_max_admins)
    _require(isinstance(abi_paths, dict) and set(abi_paths) == set(manifest['abi']), 'ABI inventory')
    contracts = {}
    for chain in manifest['chains'].values():
        for name, address in chain['contracts'].items():
            contracts[name] = AbiContract(abi_paths[name], address, manifest['abi'][name]['abiSha256'])

    chain_ids = {c['chainId'] for c in manifest['chains'].values()}
    _require(isinstance(blocks, list) and isinstance(calls, list), 'capture lists')
    headers, heights = {}, {}
    for row in blocks:
        _closed(row, ('chainId', 'raw'), 'block capture')
        _require(row['chainId'] in chain_ids, 'block chain')
        raw = row['raw']
        _require(isinstance(raw, dict) and {'number', 'hash', 'timestamp'} <= raw.keys(), 'block header')
        number, timestamp = _quantity(raw['number']), _quantity(raw['timestamp'])
        _hex(raw['hash'], 32)
        key = row['chainId'], raw['hash']
        _require(key not in headers, 'duplicate block capture')
        headers[key] = (number, timestamp)
        height = row['chainId'], number
        if checked['declaredSafeLedgerInterval']:
            _require(height not in heights or heights[height] == raw['hash'], 'conflicting safe block hashes')
        heights[height] = raw['hash']

    raw_calls = {}
    for row in calls:
        _closed(row, ('chainId', 'blockHash', 'to', 'data', 'result'), 'call capture')
        _require(row['chainId'] in chain_ids, 'call chain')
        _hex(row['blockHash'], 32); _hex(row['to'], 20)
        _hex(row['data']); _hex(row['result'])
        key = row['chainId'], row['blockHash'], row['to'], row['data']
        _require(key not in raw_calls, 'duplicate call capture')
        raw_calls[key] = row['result']
    used_blocks, used_calls = set(), set()

    def header(chain, number, hash_, timestamp=None):
        key = chain, hash_
        _require(key in headers, 'missing raw block')
        actual_number, actual_time = headers[key]
        _require(actual_number == number, 'raw block number mismatch')
        _require(timestamp is None or actual_time == timestamp, 'raw block timestamp mismatch')
        used_blocks.add(key)

    def observation(value):
        header(value['chainId'], value['blockNumber'], value['blockHash'], value['timestamp'])

    def call(name, method, death, *args):
        contract = contracts[name]
        function = contract._function(method)
        _require(function.get('stateMutability') in ('view', 'pure'), 'death getter must be read-only')
        key = death['chainId'], death['blockHash'], contract.address, contract.calldata(method, *args)
        _require(key in raw_calls, 'missing exact death call')
        result = contract.decode_return(method, raw_calls[key])
        used_calls.add(key)
        return result

    for value in evidence['observations']:
        observation(value)
    faults = ([evidence['faulted']] if evidence['faulted'] else []) + [r['fault'] for r in evidence['faultLog']]
    for fault in faults:
        observation(fault['previous']); observation(fault['observed'])
    for clear in evidence['faultLog']:
        observation(clear['clearedAgainst'])

    deaths = 0
    for row in evidence['superseded'] + evidence['conflicts']:
        for signed in row['digests']:
            observation(signed['observation'])
        effect = row['effect']
        if row['type'] in ('AccessDecision', 'StateCheckpoint'):
            header(manifest['chains']['pbc']['chainId'], effect['sourceBlockNumber'], effect['sourceBlockHash'])
        elif row['type'] == 'GrantReceipt':
            header(manifest['chains']['dbc']['chainId'], effect['dbcBlockNumber'], effect['dbcBlockHash'])
        if 'death' not in row:
            continue
        death = row['death']; ob = death['observation']; kind = death['kind']
        observation(ob)
        # The composed checker already enforces expiry against every digest,
        # exact target chains, ALLOW-only grant death and numeric inequalities.
        if kind in ('overtaken-checkpoint', 'overtaken-decision-sequence'):
            exists, checkpoint = call('KSSC', 'currentCheckpoint', ob)
            _require(exists is True and checkpoint['sequence'] == death['observed'], 'checkpoint death fact')
        elif kind == 'overtaken-governance':
            nonce, = call('Governance', 'governanceNonce', ob)
            _require(nonce == death['observed'], 'governance death fact')
        elif kind == 'overtaken-decision-grant':
            dbc = manifest['chains']['dbc']
            grant_id = '0x' + keccak(encode(['bytes32', 'address', 'uint256'],
                [_hex(row['keyField'], 32), dbc['contracts']['KSSC'], int(dbc['chainId'])])).hex()
            grant, = call('KSSC', 'grantDetails', ob, grant_id)
            _require(grant['exists'] is True and grant['requestDigest'] == row['keyField'], 'grant death fact')
        elif kind == 'executed-receipt':
            request, = call('PSC', 'getRequest', ob, row['keyField'])
            _require(request['status'] == '2', 'OUTCOME_RECORDED death fact')
        deaths += 1

    _require(used_blocks == set(headers), 'unused block capture')
    _require(used_calls == set(raw_calls), 'unused call capture')
    return checked | dict(nativeBlocksChecked=len(used_blocks), nativeCallsChecked=len(used_calls),
                          nativeDeathsChecked=deaths)
