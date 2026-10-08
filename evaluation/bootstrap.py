"""Verify the selected E1 public bootstrap before submitting any transaction.

This is a paper-derived reconstruction using synthetic fixtures. Signatures
bind the actual deployment; public actor/bundle checks keep Bob a registered
policy-denied control. No authority, GID, user or witness key is loaded here.
Native source-block/version observations must be collected by the executor.
"""
import copy
import hashlib
import json
from pathlib import Path

from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_keys.exceptions import BadSignature
from eth_utils import keccak
from jsonschema import Draft202012Validator, ValidationError

from evaluation.native import _quantity
from evaluation.processes import _pairs, _constant, _float
from evaluation.schema import FORMATS, semantics

ROOT = Path(__file__).resolve().parents[1]
FREEZE_SHA256 = 'f700292ec7e3b2c8f2b59c7a728a991cd7d6dea2e4a06cea71f6f6c97b9962a2'
USERS = {'alice': '0xc4ff0022e776c3471e39abf6c69ce679440c956d',
         'bob': '0xac5a40f1b6d99eca704aebc1fd7ffa5dbb5be59a'}


def strict_json(raw):
    if not isinstance(raw, bytes) or len(raw) > 1048576:
        raise ValueError('Public JSON exceeds the 1 MiB budget')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                           parse_constant=_constant, parse_float=_float)
    except (ValueError, RecursionError) as error:
        raise ValueError('Malformed public JSON') from error
    if not isinstance(value, dict):
        raise ValueError('Public JSON object required')
    return value


def _frozen(relative):
    freeze_raw = (ROOT/'interfaces/v1/FREEZE.json').read_bytes()
    if hashlib.sha256(freeze_raw).hexdigest() != FREEZE_SHA256:
        raise ValueError('Interface freeze pin changed')
    freeze = json.loads(freeze_raw)
    path = 'interfaces/v1/'+relative
    raw = (ROOT/path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != freeze['frozenCopies'][path]['sha256']:
        raise ValueError('Frozen interface bytes changed')
    return json.loads(raw)


def frozen_validate(name, value):
    schema = _frozen('hmbc.schema.json')
    if name not in schema['$defs']:
        raise ValueError('Unknown frozen schema')
    schema['$ref'] = '#/$defs/'+name
    try:
        Draft202012Validator(schema, format_checker=FORMATS).validate(value)
        semantics(name, value)
    except ValidationError as error:
        raise ValueError('Public artifact violates frozen '+name) from error


def signed_digest(kind, message, signature, signer, chain_id, contract):
    """Recover a public EIP-712 signature under instance-local domain facts."""
    frozen_validate(kind, message)
    frozen_validate('Signature', signature)
    frozen_validate('Address', signer)
    frozen_validate('Uint256', chain_id)
    frozen_validate('Address', contract)
    vectors = _frozen('vectors/eip712-agent1.json')['vectors']
    template = next(v['typedData'] for v in vectors if v['name'] == kind)
    typed = copy.deepcopy(template)
    typed['message'] = message
    typed['domain'].update(chainId=chain_id, verifyingContract=contract)
    encoded = encode_typed_data(full_message=typed)
    try:
        recovered = Account.recover_message(encoded, signature=signature).lower()
    except (ValueError, BadSignature) as error:
        raise ValueError('Public signature recovery failed') from error
    if recovered != signer:
        raise ValueError('Public signature signer/domain mismatch')
    return '0x'+keccak(b'\x19'+encoded.version+encoded.header+encoded.body).hex()


def _fields(value, names):
    if not isinstance(value, dict) or set(value) != set(names):
        raise ValueError('Unexpected bootstrap fields')


def _same(actual, expected, label):
    if actual != expected:
        raise ValueError('Bootstrap '+label+' mismatch')


def validate_bootstrap(value, *, deployment_bytes, source_block, versions, now_timestamp):
    """Return copied checked public leaves; caller retains/hashes raw inputs.

    `versions` maps each authority to decimal-string revocation/temporal versions
    at the producer block. That block and `now_timestamp` come from the pinned
    PBC, not from the producer. Current transaction-time freshness still needs
    ledger checks; this function does not prove RPC integrity or authorization.
    """
    value = strict_json(value) if isinstance(value, bytes) else copy.deepcopy(value)
    deployment = strict_json(deployment_bytes)
    frozen_validate('LedgerDeployment', deployment)
    _same(deployment['interfaceVersion'], 'v1', 'interface')
    if deployment['profile'] not in ('paper-strict', 'paper-minimal', 'repaired-e') or deployment['mutations'] != '0':
        raise ValueError('Only E1 baseline profiles are permitted')
    _fields(value, ('schemaVersion', 'producer', 'testOnly', 'binding', 'trustLists', 'users', 'order', 'limits'))
    _same(value['schemaVersion'], 'hmbc-ledger-bootstrap/v0', 'producer version')
    _same(value['producer'], 'agent-1 ledger/tools/bootstrap_fixture.sh (script/BootstrapFixture.s.sol)', 'producer')
    if value['testOnly'] is not True:
        raise ValueError('Synthetic TEST-ONLY bootstrap required')
    for name in ('order', 'limits'):
        if not isinstance(value[name], list) or not all(isinstance(x, str) for x in value[name]):
            raise ValueError('Malformed bootstrap notes')
    binding = value['binding']
    _fields(binding, ('pbcChainId', 'tmsc', 'rsc', 'blockNumber', 'blockTimestamp', 'deploymentSha256', 'profile'))
    pbc = deployment['chains']['pbc']
    expected = {'pbcChainId': pbc['chainId'], 'tmsc': pbc['contracts']['TMSC'],
                'rsc': pbc['contracts']['RSC'], 'profile': deployment['profileEnum'],
                'deploymentSha256': hashlib.sha256(deployment_bytes).hexdigest(),
                'blockNumber': str(_quantity(source_block['number'])),
                'blockTimestamp': str(_quantity(source_block['timestamp']))}
    _same(binding, expected, 'instance/source block')
    frozen_validate('Uint64', now_timestamp)
    timestamp = int(binding['blockTimestamp'])
    current = int(now_timestamp)
    if current < timestamp:
        raise ValueError('PBC observation precedes producer block')
    authorities = {a['id']: a for a in deployment['fixture']['authorities']}
    _same(set(authorities), {'H1', 'H2', 'H3', 'H4'}, 'authority inventory')
    _same(set(versions), {a['root'] for a in authorities.values()}, 'observed authority versions')
    _fields(value['users'], USERS)
    lists = value['trustLists']
    if not isinstance(lists, list) or len(lists) != 3:
        raise ValueError('Three ordered bootstrap trust lists required')
    checks = 0
    for item, (hospital, kind, state) in zip(lists, [('H1', 'RevocationList', 'revocation'),
                                                  ('H1', 'TemporalAcl', 'temporal'),
                                                  ('H2', 'RevocationList', 'revocation')], strict=True):
        _fields(item, ('kind', 'call', 'submitterRole', 'submitter', 'list', 'signature', 'signer'))
        authority = authorities[hospital]
        method = 'updateRevocationList' if state == 'revocation' else 'updateTemporalAcl'
        _same(item['kind'], kind, 'list order/kind')
        _same(item['call'], 'TMSC.'+method, 'list call')
        _same(item['submitterRole'], hospital+'-ca-admin', 'admin role')
        _same(item['submitterRole'], authority['caAdminKeyLabel'], 'deployment admin role')
        if item['submitter'] not in authority['caAdmins']:
            raise ValueError('Bootstrap issuer-scoped admin mismatch')
        _same(item['signer'], authority['root'], 'list signer')
        body = item['list']
        frozen_validate(kind, body)
        _same(body['authority'], authority['root'], 'list authority')
        observed = versions[authority['root']][state]
        frozen_validate('Uint64', observed)
        _same(body['version'], str(int(observed)+1), 'next list version')
        _same(body['validUntil'], str(timestamp+86400), 'list TTL')
        if current >= int(body['validUntil']):
            raise ValueError('Bootstrap trust list expired')
        if state == 'revocation':
            _same(body['revokedSerials'], [], 'fresh unrevoked control')
        else:
            duty = '0x'+keccak(text='HMBC.role.OnDuty').hex()
            _same(body['entries'], [{'gid': USERS['alice'], 'role': duty,
                                    'validFrom': str(timestamp-60), 'validUntil': str(timestamp+28800)}], 'Alice duty entry')
        signed_digest(kind, body, item['signature'], authority['root'], pbc['chainId'], binding['tmsc'])
        checks += 1
    for label, (hospital, role, serial) in {'alice': ('H1', 'Doctor', '101'), 'bob': ('H2', 'Researcher', '201')}.items():
        user = value['users'][label]
        _fields(user, ('gid', 'recipientKeyLabel', 'recipientKeyHash', 'certificate', 'registration', 'possessionSignature', 'bundle'))
        gid = USERS[label]
        _same(user['gid'], gid, 'fixture GID')
        key_label = 'HMBC.recipient-key.'+label
        recipient = '0x'+keccak(text=key_label).hex()
        _same(user['recipientKeyLabel'], key_label, 'recipient label')
        _same(user['recipientKeyHash'], recipient, 'recipient hash')
        cert = user['certificate']
        frozen_validate('SignedRoleCertificate', cert)
        _same(cert['cert'], {'issuer': authorities[hospital]['root'], 'gid': gid,
                            'roles': ['0x'+keccak(text='HMBC.role.'+role).hex()], 'serial': serial,
                            'validFrom': '1700000000', 'validUntil': '2100000000'}, 'fixture certificate')
        if not 1700000000 <= current < 2100000000:
            raise ValueError('Bootstrap certificate outside its validity interval')
        digest = signed_digest('RoleCertificate', cert['cert'], cert['signature'],
                               authorities[hospital]['root'], pbc['chainId'], binding['tmsc'])
        reg = user['registration']
        frozen_validate('Registration', reg)
        _same(reg, {'gid': gid, 'certDigest': digest, 'recipientKeyHash': recipient,
                    'expiresAt': str(timestamp+3600)}, 'registration join/TTL')
        if current >= int(reg['expiresAt']):
            raise ValueError('Bootstrap registration expired')
        signed_digest('Registration', reg, user['possessionSignature'], gid, pbc['chainId'], binding['rsc'])
        bundle = user['bundle']
        frozen_validate('CredentialBundle', bundle)
        claims = [{'authority': authorities['H1']['root'], 'role': '0x'+keccak(text='HMBC.role.OnDuty').hex()}] if label == 'alice' else []
        _same(bundle, {'certificates': [cert], 'temporalClaims': claims}, 'credential bundle')
        checks += 2
    return {'binding': binding, 'trustLists': lists, 'users': value['users'], 'signatureChecks': checks}
