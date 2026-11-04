"""Context-bound signature checks for the HMBC2020 reconstruction's F extension.

Caller context must come from independently anchored deployment/set observations,
not the artifact being checked. Recovery authenticates bytes to a configured key;
it does not establish source-state truth, expiry at consumption, storage history,
arrival completeness, process independence or transaction acceptance. No existing
consumer is switched to this module. These checks alone cannot pass an RQ gate.
"""
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_keys.exceptions import BadSignature
from eth_utils import keccak

from evaluation.schema_v2 import validate, validate_response

# Normative field order from frozen v1, plus accepted v2 GovernanceAction.
# Never accept a producer's choice of domain name, version or type definitions.
_TYPES = {
    'StateCheckpoint': ('HMBCState', (
        ('sequence', 'uint64'), ('authEpoch', 'uint64'), ('policyVersion', 'uint64'),
        ('keyEpoch', 'uint64'), ('witnessSetVersion', 'uint64'),
        ('sourceChainId', 'uint256'), ('psc', 'address'),
        ('sourceBlockNumber', 'uint256'), ('sourceBlockHash', 'bytes32'), ('expiresAt', 'uint64'))),
    'AccessDecision': ('HMBCDecision', (
        ('requestDigest', 'bytes32'), ('result', 'uint8'), ('credentialDigest', 'bytes32'),
        ('stateSequence', 'uint64'), ('witnessSetVersion', 'uint64'),
        ('sourceBlockNumber', 'uint256'), ('sourceBlockHash', 'bytes32'), ('expiresAt', 'uint64'))),
    'GrantReceipt': ('HMBCReceipt', (
        ('requestDigest', 'bytes32'), ('grantId', 'bytes32'), ('gid', 'address'),
        ('dataId', 'bytes32'), ('keyEpoch', 'uint64'), ('grantExpiresAt', 'uint64'),
        ('witnessSetVersion', 'uint64'), ('dbcChainId', 'uint256'), ('kssc', 'address'),
        ('dbcBlockNumber', 'uint256'), ('dbcBlockHash', 'bytes32'))),
    'GovernanceAction': ('HMBCGovernance', (
        ('action', 'uint8'), ('root', 'address'), ('admins', 'address[]'),
        ('nonce', 'uint64'), ('witnessSetVersion', 'uint64'), ('expiresAt', 'uint64'))),
}
_DOMAIN = (('name', 'string'), ('version', 'string'),
           ('chainId', 'uint256'), ('verifyingContract', 'address'))


def _require(condition, message):
    if not condition:
        raise ValueError('Invalid witness evidence: ' + message)


def _address(value):
    validate('Address', value)
    _require(int(value, 16) != 0, 'zero context address')


def _typed_message(name, message, chain_id, verifying_contract):
    _require(isinstance(name, str) and name in _TYPES, 'unsupported message type')
    validate(name, message)
    validate('Uint256', chain_id)
    _address(verifying_contract)
    domain_name, fields = _TYPES[name]
    return encode_typed_data(full_message={
        'types': {key: [{'name': n, 'type': t} for n, t in items]
                  for key, items in [('EIP712Domain', _DOMAIN), (name, fields)]},
        'primaryType': name,
        'domain': {'name': domain_name, 'version': '1', 'chainId': chain_id,
                   'verifyingContract': verifying_contract},
        'message': message,
    })


def _witness_context(witnesses, witness_set_version):
    validate('Uint64', witness_set_version)
    _require(witness_set_version in ('1', '2'), 'unsupported witness-set version')
    _require(isinstance(witnesses, list) and len(witnesses) in (1, 4), 'configured witness list')
    for address in witnesses:
        _address(address)
    _require(len(set(witnesses)) == len(witnesses), 'duplicate configured witness')


def message_digest(name, message, *, chain_id, verifying_contract):
    """Recompute EIP-712 digest under fixed types and caller-supplied domain."""
    encoded = _typed_message(name, message, chain_id, verifying_contract)
    return '0x' + keccak(b'\x19' + encoded.version + encoded.header + encoded.body).hex()


def verify_certificate(name, message, signatures, *, chain_id, verifying_contract,
                       witnesses, witness_set_version, required_signatures):
    """Return distinct ascending configured signers for exactly the stated count.

    The caller explicitly selects a pool q3, q2 negative control or single-witness
    check. This primitive does not infer a quorum requirement from the artifact.
    """
    encoded = _typed_message(name, message, chain_id, verifying_contract)
    _witness_context(witnesses, witness_set_version)
    _require(message['witnessSetVersion'] == witness_set_version, 'witness-set mismatch')
    _require(type(required_signatures) is int and required_signatures in (1, 2, 3)
             and required_signatures <= len(witnesses), 'certificate count context')
    _require(isinstance(signatures, list) and len(signatures) == required_signatures,
             'certificate signature count')
    recovered = []
    for signature in signatures:
        validate('Signature', signature)
        try:
            address = Account.recover_message(encoded, signature=signature).lower()
        except (ValueError, TypeError, BadSignature) as error:
            raise ValueError('Invalid witness evidence: signature recovery failed') from error
        _require(address in witnesses, 'unknown recovered signer')
        recovered.append(address)
    _require(recovered == sorted(set(recovered)), 'duplicate or out-of-order recovered signer')
    return recovered


def verify_checkpoint_reports(response, *, chain_id, verifying_contract,
                              witnesses, witness_set_version, selected_index=None):
    """Check every declared retry report's signature against its configured owner.

    Counts reports checked, including late duplicates; checks no success
    certificate here. A pinned single-witness refusal requires the original
    request's selected index. Transport identity/completeness need runner evidence.
    """
    validate_response('collect_checkpoint', response)
    _witness_context(witnesses, witness_set_version)
    validate('Uint256', chain_id)
    _address(verifying_contract)
    payload = response['result'] if response['ok'] else response['error']
    reports = []
    if 'recorded' in payload:
        _require(isinstance(selected_index, str) and selected_index in ('0', '1', '2', '3')
                 and int(selected_index) < len(witnesses), 'selected witness index required')
        reports.append((int(selected_index), payload['recorded']))
    collection = payload.get('collection', {})
    reports.extend((int(r['witnessIndex']), r)
                   for key in ('recordedReports', 'lateReports') for r in collection.get(key, []))
    reports.extend((int(r['witnessIndex']), report)
                   for r in collection.get('inconsistentReports', []) for report in r['reports'])
    for index, report in reports:
        _require(index < len(witnesses), 'report witness index outside configuration')
        verify_certificate('StateCheckpoint', report['message'], [report['signature']],
            chain_id=chain_id, verifying_contract=verifying_contract,
            witnesses=[witnesses[index]], witness_set_version=witness_set_version,
            required_signatures=1)
    return len(reports)
