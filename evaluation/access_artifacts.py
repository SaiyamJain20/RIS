"""Independent public artifact joins for the paper-derived C-E1 reconstruction.

No user/authority/witness key is loaded here. Caller-supplied native observations
must come from the pinned public executor at stable blocks, with raw evidence
retained. Agreement with those observations is not provider authentication.
"""
import copy

from evaluation.bootstrap import frozen_validate, signed_digest
from evaluation.native import _quantity
from evaluation.vectors import credential_digest


def require(condition, label):
    if not condition:
        raise ValueError('Public access '+label+' failed')


def _binding(request, deployment):
    frozen_validate('AccessRequest', request)
    pbc, dbc = (deployment['chains'][name] for name in ('pbc', 'dbc'))
    require(request['sourceChainId'] == pbc['chainId'] and request['psc'] == pbc['contracts']['PSC']
            and request['destinationChainId'] == dbc['chainId'] and request['kssc'] == dbc['contracts']['KSSC'], 'request destination')
    require(request['action'] == '1' and request['policyVersion'] == '1' and request['keyEpoch'] == '0', 'E1 request phase')


def verify_prepared(result, *, request, deployment):
    frozen_validate('PrepareRequestResult', result)
    _binding(request, deployment)
    require(result['request'] == request and result['signer'] == request['gid'], 'prepared body/signer')
    digest = signed_digest('AccessRequest', request, result['signature'], request['gid'], request['sourceChainId'], request['psc'])
    require(result['requestDigest'] == digest, 'prepared digest')
    return digest


def _source(message, block, number_key, hash_key):
    require(str(_quantity(block['number'])) == message[number_key] and block['hash'] == message[hash_key], 'native source block')
    frozen_validate('Hash', block['hash'])
    _quantity(block['timestamp'])


def _witness(kind, result, deployment):
    require(deployment['profile'] == 'repaired-e' and deployment['mutations'] == '0', 'witness profile')
    ws = deployment['fixture']['witnessSet']
    require(ws['version'] == '1' and ws['threshold'] == '1' and len(ws['witnesses']) == 1, 'E1 witness configuration')
    chain = deployment['chains']['pbc' if kind == 'GrantReceipt' else 'dbc']
    role = 'PSC' if kind == 'GrantReceipt' else 'KSSC'
    message = result[{'StateCheckpoint': 'checkpoint', 'AccessDecision': 'decision', 'GrantReceipt': 'receipt'}[kind]]
    signed_digest(kind, message, result['signatures'][0], ws['witnesses'][0], chain['chainId'], chain['contracts'][role])


def verify_checkpoint(result, *, deployment, source_block, auth_epoch, policy_version,
                      dbc_now, current_checkpoint, request_block_number):
    frozen_validate('CollectCheckpointResult', result)
    cp = result['checkpoint']; _witness('StateCheckpoint', result, deployment)
    _source(cp, source_block, 'sourceBlockNumber', 'sourceBlockHash')
    pbc = deployment['chains']['pbc']
    require(cp['sourceChainId'] == pbc['chainId'] and cp['psc'] == pbc['contracts']['PSC'], 'checkpoint source')
    require(cp['authEpoch'] == auth_epoch and cp['policyVersion'] == policy_version == '1', 'checkpoint native epoch/policy')
    exists, current = current_checkpoint
    require(type(exists) is bool, 'checkpoint presence')
    require(int(cp['sequence']) == int(current['sequence'])+1 if exists else cp['sequence'] == '1', 'checkpoint next sequence')
    if exists:
        require(all(int(cp[key]) >= int(current[key]) for key in ('authEpoch', 'policyVersion', 'keyEpoch', 'sourceBlockNumber')),
                'checkpoint monotonic fields')
    require(int(cp['sourceBlockNumber']) >= int(request_block_number), 'checkpoint after request')
    require(int(dbc_now) < int(cp['expiresAt']) <= int(dbc_now)+60, 'checkpoint lifetime')
    return copy.deepcopy(cp)


def verify_decision(result, *, request, request_digest, deployment, checkpoint, source_block,
                    dbc_now, pbc_now, request_block_number, native_records, credentials_code,
                    policy_allowed, nonce_consumed):
    frozen_validate('CollectDecisionResult', result)
    _binding(request, deployment); _witness('AccessDecision', result, deployment)
    frozen_validate('StateCheckpoint', checkpoint)
    d = result['decision']; cp = checkpoint
    _source(cp, source_block, 'sourceBlockNumber', 'sourceBlockHash')
    require(d['requestDigest'] == request_digest, 'decision request')
    require(all(d[key] == cp[cp_key] for key, cp_key in [('stateSequence', 'sequence'), ('witnessSetVersion', 'witnessSetVersion'),
                                                       ('sourceBlockNumber', 'sourceBlockNumber'), ('sourceBlockHash', 'sourceBlockHash')]),
            'decision current checkpoint')
    require(all(request[key] == cp[key] for key in ('authEpoch', 'policyVersion', 'keyEpoch')), 'request/checkpoint epoch')
    require(cp['sourceChainId'] == request['sourceChainId'] and cp['psc'] == request['psc'], 'decision source')
    require(int(cp['sourceBlockNumber']) >= int(request_block_number), 'decision after request')
    require(nonce_consumed is False, 'unconsumed nonce')
    require(max(int(dbc_now), int(pbc_now)) < int(request['expiresAt']), 'request clocks')
    require(int(dbc_now) < int(d['expiresAt']) <= min(int(request['expiresAt']), int(cp['expiresAt']), int(dbc_now)+30),
            'decision lifetime')
    frozen_validate('CredentialRecords', native_records)
    # The owner witness removes records which elapsed between the source and
    # destination clocks. A current-time lapse can never be converted to ALLOW.
    lapsed = credentials_code == '0' and any(int(row['validUntil']) <= int(dbc_now) for row in native_records)
    records = [] if lapsed else native_records
    require(result['credentialRecords'] == records, 'historical credential records')
    require(d['credentialDigest'] == credential_digest(records), 'credential array digest')
    require(type(policy_allowed) is bool, 'native policy result')
    allow = credentials_code == '0' and not lapsed and policy_allowed
    require(d['result'] == ('1' if allow else '0'), 'independent policy decision')
    return copy.deepcopy(result)
