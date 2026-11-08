"""Pure independent reconstruction of successor D50 deployment context.

The caller must pin the manifest/build attestation and independently acquire
observations. Each normalized code/view read carries its explicit block anchor;
the collector must confirm the anchor after acquisition. This module performs
no RPC and cannot authenticate a fabricated observation or attest source code.
Masked equality covers runtime bytes outside trusted immutable ranges only.
No existing E/F consumer is switched, and this check cannot pass an RQ gate.
"""
import copy
import hashlib
import json
import re

from evaluation.schema_v2 import binding_hash, validate

_BASE = {'0': 'paper-strict', '1': 'paper-minimal', '2': 'repaired-e', '3': 'repaired-f'}
_PROFILES = {'paper-strict': ('0', '0'), 'paper-minimal': ('1', '0'), 'repaired-e': ('2', '0')}
_PROFILES.update({name: ('2', str(1 << i)) for i, name in enumerate((
    'mutant-no-destination-binding', 'mutant-no-state-barrier',
    'mutant-no-record-freshness', 'mutant-no-nonce',
    'mutant-no-version-monotone', 'mutant-no-receipt-binding'))})
_PROFILE_HOLDERS = {'TMSC', 'PSC', 'KSSC', 'ACSC'}
_CONFIGURED = {'LSC', 'TMSC', 'RSC', 'PSC', 'KSSC', 'ACSC'}


def _require(condition, message):
    if not condition:
        raise ValueError('Invalid deployment context: ' + message)


def _closed(value, fields, label):
    _require(isinstance(value, dict) and set(value) == set(fields), label + ' fields')


def _same(actual, expected, label):
    # A JSON boolean must never compare equal to a numeric fixture value.
    _require(type(actual) is type(expected) and actual == expected, label + ' mismatch')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _anchor(value):
    _closed(value, ('number', 'hash'), 'anchor')
    validate('Uint256', value['number'])
    validate('Hash', value['hash'])


def _read(row, anchor, label):
    _closed(row, ('anchor', 'value'), label)
    _same(row['anchor'], anchor, label + ' block')
    return row['value']


def _masked_code(code, entry):
    # Range shape, widths, sorted disjoint bounds and object-list digest have
    # already been checked against the pinned manifest by schema_v2.
    _require(isinstance(code, str) and re.fullmatch(r'0x(?:[0-9a-f]{2})+', code), 'code hex')
    raw = bytes.fromhex(code[2:])
    _require(len(raw) == int(entry['runtimeBytes']), 'code length')
    segments = []
    end = 0
    for span in entry['immutableReferences']:
        start = int(span['start'])
        end_of_span = start + int(span['length'])
        segments.extend((raw[end:start], bytes(end_of_span - start)))
        end = end_of_span
    segments.append(raw[end:])
    _same(_sha(b''.join(segments)), entry['runtimeSha256'], 'masked build')
    return raw


def _expected_views(manifest):
    """Derive only expected assertions from trusted pins, never from an export."""
    chains = manifest['chains']
    addresses = {name: addr for chain in chains.values() for name, addr in chain['contracts'].items()}
    _require(all(int(addr, 16) != 0 for addr in addresses.values()), 'zero contract address')
    enum, mask = manifest['profileEnum'], manifest['mutations']
    group = manifest['fixture']['witnessSet']
    views = {name: {} for name in addresses}
    for name in _CONFIGURED:
        views[name]['configured'] = True
    for name in _PROFILE_HOLDERS:
        views[name].update(profile=enum, mutations=mask)
    for name in ('PSC', 'KSSC') + (('Governance',) if enum == '3' else ()):
        views[name].update(witnesses=group['witnesses'], threshold=group['threshold'], witnessSetVersion=group['version'])
    views['PSC'].update(rsc=addresses['RSC'], tmsc=addresses['TMSC'], lsc=addresses['LSC'], ksscForChain=addresses['KSSC'])
    views['RSC'].update(tmsc=addresses['TMSC'], lsc=addresses['LSC'])
    views['TMSC'].update(psc=addresses['PSC'], rsc=addresses['RSC'])
    views['LSC'].update(rsc=addresses['RSC'], tmsc=addresses['TMSC'], psc=addresses['PSC'])
    views['KSSC']['acsc'] = addresses['ACSC']
    views['ACSC'].update(kssc=addresses['KSSC'], pscRelay=manifest['fixture']['relay']['address'])
    if enum == '3':
        views['TMSC']['governance'] = addresses['Governance']
        views['Governance'].update(mutations=mask, target=addresses['TMSC'],
            governanceChainId=chains['pbc']['chainId'], maxGovernanceTtl=manifest['fixture']['governance']['maxGovernanceTtl'])
    return views


def reconstruct(manifest, observations, *, compiled_max_admins=None):
    """Build B from pinned successor metadata and independently acquired reads.

    observations has pbc/dbc entries: chainId, genesisHash, deployBlock,
    anchor, confirmedAnchor, code and views. code is contract -> read record;
    views is contract -> getter -> read record. Every read record is exactly
    {anchor, value}. PSC.ksscForChain is the read for the pinned DBC chain ID.
    No trust is derived from this structure; the future collector must retain
    and authenticate its public ABI calldata, return bytes and RPC provenance.
    """
    marker = manifest.get('schemaVersion') if isinstance(manifest, dict) else None
    _require(marker in ('hmbc-ledger-deployment/v2', 'hmbc-ledger-deployment/v2.1'), 'unselected carrier')
    revision = 'v2.1' if marker.endswith('/v2.1') else 'v2'
    validate('LedgerDeployment', manifest, schema_revision=revision)
    enum, mask = manifest['profileEnum'], manifest['mutations']
    if manifest['profile'] == 'repaired-f':
        _same(enum, '3', 'profile')
        _same(compiled_max_admins, '8', 'compiled MAX_ADMINS attestation')
    else:
        _same((enum, mask), _PROFILES.get(manifest['profile']), 'profile table')
    expected = _expected_views(manifest)
    _closed(observations, ('pbc', 'dbc'), 'observations')
    document = {'interfaceVersion': manifest['interfaceVersion'],
        'profile': {'name': _BASE[enum], 'enum': enum},
        'chains': {}, 'immutables': {}, 'witnessSets': {}, 'wiring': {}}
    live = {}
    for chain_name in ('pbc', 'dbc'):
        observed = observations[chain_name]
        pin = manifest['chains'][chain_name]
        _closed(observed, ('chainId', 'genesisHash', 'deployBlock', 'anchor', 'confirmedAnchor', 'code', 'views'), chain_name)
        _same(observed['chainId'], pin['chainId'], chain_name + ' chain ID')
        validate('Hash', observed['genesisHash'])
        for key in ('anchor', 'confirmedAnchor', 'deployBlock'):
            _anchor(observed[key])
        anchor = observed['anchor']
        _same(observed['confirmedAnchor'], anchor, chain_name + ' confirming anchor')
        _same(observed['deployBlock']['number'], pin['deployBlock'], chain_name + ' deploy block')
        _require(int(anchor['number']) >= int(pin['deployBlock']), 'anchor before deployment')
        if anchor['number'] == pin['deployBlock']:
            _same(anchor['hash'], observed['deployBlock']['hash'], 'deployment anchor hash')
        _closed(observed['code'], pin['contracts'], chain_name + ' code')
        _closed(observed['views'], pin['contracts'], chain_name + ' views')
        bound = {'chainId': observed['chainId'], 'genesisHash': observed['genesisHash'],
                 'deployBlock': copy.deepcopy(observed['deployBlock']), 'contracts': {}}
        for name, address in pin['contracts'].items():
            entry = manifest['abi'][name]
            raw = _masked_code(_read(observed['code'][name], anchor, name + ' code'), entry)
            bound['contracts'][name] = {'address': address, 'codeSha256': _sha(raw),
                **{k: entry[k] for k in ('abiSha256', 'runtimeSha256', 'runtimeBytes', 'immutableRefsSha256')}}
            _closed(observed['views'][name], expected[name], name + ' getters')
            live[name] = {}
            for getter, value in expected[name].items():
                actual = _read(observed['views'][name][getter], anchor, name + '.' + getter)
                _same(actual, value, name + '.' + getter)
                live[name][getter] = copy.deepcopy(actual)
        document['chains'][chain_name] = bound
    for name in _PROFILE_HOLDERS | ({'Governance'} if enum == '3' else set()):
        document['immutables'][name] = {k: live[name][k] for k in ('profile', 'mutations') if k in live[name]}
    for name in ('PSC', 'KSSC') + (('Governance',) if enum == '3' else ()):
        document['witnessSets'][name.lower()] = {'version': live[name]['witnessSetVersion'],
            'threshold': live[name]['threshold'], 'witnesses': live[name]['witnesses']}
    document['wiring'] = {'ksscForChain': live['PSC']['ksscForChain'], 'acsc': live['KSSC']['acsc'],
        'kssc': live['ACSC']['kssc'], 'pscRelay': live['ACSC']['pscRelay'],
        'tmsc': {k: live['TMSC'][k] for k in ('psc', 'rsc')},
        'lsc': {k: live['LSC'][k] for k in ('rsc', 'tmsc', 'psc')}}
    if enum == '3':
        document['wiring']['governance'] = {'tmsc': live['TMSC']['governance'], 'target': live['Governance']['target']}
    validate('DeploymentBindingDocument', document)
    return document


def verify_export(export, manifest, observations, *, expected_owner, compiled_max_admins=None):
    """Compare an untrusted export with reconstructed B and a caller-bound owner."""
    document = reconstruct(manifest, observations, compiled_max_admins=compiled_max_admins)
    validate('BindingExport', export)
    _same(export['document'], document, 'export document')
    _same(export['binding_v2'], binding_hash(document), 'export digest')
    _same(export['anchor'], {k: observations[k]['anchor'] for k in ('pbc', 'dbc')}, 'export anchor')
    _same(export['owner'], expected_owner, 'export owner')
    if expected_owner != 'worker':
        witnesses = document['witnessSets']['psc']['witnesses']
        _require(expected_owner.removeprefix('witness:') in witnesses, 'owner membership')
    return document
