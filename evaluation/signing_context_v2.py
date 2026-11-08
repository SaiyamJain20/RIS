"""Bind signature checks to independently acquired successor deployment facts.

Caller-selected reviewed manifest/build pins and public observations supply the
context. No domain, quorum or membership comes from the certificate/export under
test. Reconstructing B checks consistency under the stated safe-ledger and
trusted-build assumptions; it cannot authenticate fabricated observations.

These internal APIs do not switch a runner or authorize execution. Signatures
do not establish source-state truth, expiry, event membership, request/grant
correspondence, exporter completeness, storage durability or an RQ result.
"""
from evaluation.binding_context_v2 import reconstruct
from evaluation.certificates_v2 import (verify_certificate, verify_checkpoint_reports,
                                        message_digest, _typed_message)
from evaluation.schema_v2 import validate, validate_response

_DESTINATIONS = {
    'StateCheckpoint': ('dbc', 'KSSC'),
    'AccessDecision': ('dbc', 'KSSC'),
    'GrantReceipt': ('pbc', 'PSC'),
    'GovernanceAction': ('pbc', 'Governance'),
}


def _require(condition, message):
    if not condition:
        raise ValueError('Invalid bound signing context: ' + message)


def _context(name, manifest, observations, compiled_max_admins):
    _require(isinstance(name, str) and name in _DESTINATIONS, 'unsupported message type')
    document = reconstruct(manifest, observations, compiled_max_admins=compiled_max_admins)
    chain, contract = _DESTINATIONS[name]
    _require(contract in document['chains'][chain]['contracts'], 'governance unavailable in this profile')
    destination = document['chains'][chain]
    group = document['witnessSets'][contract.lower()]
    return document, {
        'chain_id': destination['chainId'],
        'verifying_contract': destination['contracts'][contract]['address'],
        'witnesses': group['witnesses'], 'witness_set_version': group['version'],
        'required_signatures': int(group['threshold']),
    }


def _embedded_identity(name, message, document):
    if name == 'StateCheckpoint':
        chain = document['chains']['pbc']
        _require(message['sourceChainId'] == chain['chainId']
                 and message['psc'] == chain['contracts']['PSC']['address'], 'embedded PBC identity mismatch')
    elif name == 'GrantReceipt':
        chain = document['chains']['dbc']
        _require(message['dbcChainId'] == chain['chainId']
                 and message['kssc'] == chain['contracts']['KSSC']['address'], 'embedded DBC identity mismatch')


def verify_bound_certificate(name, message, signatures, *, manifest, observations,
                             compiled_max_admins=None):
    """Return sorted distinct configured signers for the observed exact quorum.

    Domain destinations are KSSC/DBC for checkpoints and decisions, PSC/PBC for
    receipts, and Governance/PBC for governance. q2 is accepted only if pinned
    and observed as that negative-control deployment; a q3 artifact cannot lower
    its own count. Carried E uses its observed single witness; no E governance.
    """
    document, context = _context(name, manifest, observations, compiled_max_admins)
    validate(name, message)
    _embedded_identity(name, message, document)
    return verify_certificate(name, message, signatures, **context)


def verify_bound_signature(name, message, signature, *, owner, manifest, observations,
                           compiled_max_admins=None):
    """Verify one caller-pinned store owner; return the digest and fixed domain.

    A single stored signature is not a quorum certificate. Membership, version,
    destination and embedded identities still come from reconstructed B.
    """
    document, context = _context(name, manifest, observations, compiled_max_admins)
    _require(owner in context['witnesses'], 'unconfigured signature owner')
    _embedded_identity(name, message, document)
    context.update(witnesses=[owner], required_signatures=1)
    verify_certificate(name, message, [signature], **context)
    domain = {k: context[k] for k in ('chain_id', 'verifying_contract')}
    return {'digest': message_digest(name, message, **domain),
            'domainSeparator': '0x' + _typed_message(name, message, **domain).header.hex()}


def verify_bound_checkpoint_reports(response, *, manifest, observations,
                                   compiled_max_admins=None, selected_index=None):
    """Check every declared retry report, returning the number checked.

    Includes refusal, late, duplicate and inconsistent report paths. Pinned
    single-witness reports still require the original request's selected index.
    This checks report signatures/embedded identity only: success certificates
    need verify_bound_certificate separately; response/arrival completeness and
    selection history require independent runner/exporter evidence.
    """
    document, context = _context('StateCheckpoint', manifest, observations, compiled_max_admins)
    validate_response('collect_checkpoint', response)
    payload = response['result'] if response['ok'] else response['error']
    declared = [payload['recorded']] if 'recorded' in payload else []
    collection = payload.get('collection', {})
    declared.extend(row for key in ('recordedReports', 'lateReports') for row in collection.get(key, []))
    declared.extend(report for row in collection.get('inconsistentReports', []) for report in row['reports'])
    for report in declared:
        _embedded_identity('StateCheckpoint', report['message'], document)
    context.pop('required_signatures')
    return verify_checkpoint_reports(response, selected_index=selected_index, **context)
