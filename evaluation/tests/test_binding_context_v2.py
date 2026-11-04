"""Synthetic D50 context joins; no RPC, owner implementation or chain proof.

Every refusal control breaks an independently required observation, pin or
fixture equality. Removing the corresponding join would accept that bad input.
"""
import copy
import hashlib
import importlib
import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[2]
BAD = (ValueError, ValidationError)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def address(n):
    return '0x' + f'{n:040x}'


def fixture(f=True, mask='0', threshold='3'):
    """Declared schema-valid manifest plus independently enumerated observations."""
    shape = json.loads((ROOT / 'interfaces/v2/vectors/ledger-export-shape.json').read_text())
    # Published synthetic schema example supplies unrelated required metadata.
    manifest = json.loads((ROOT / 'interfaces/proposals/v2-e-source-closure/e-complete-example.json').read_text())
    manifest['schemaVersion'] = 'hmbc-ledger-deployment/v2'
    manifest['interfaceVersion'] = 'v2'
    manifest['profile'] = 'repaired-f' if f else 'repaired-e'
    manifest['profileEnum'] = '3' if f else '2'
    manifest['mutations'] = mask
    manifest['mutantNote'] = 'synthetic evaluator fixture'
    if not f:
        del manifest['sources']['src/Governance.sol']
        del manifest['sources']['src/interfaces/IPolicyVersion.sol']
    if f:
        manifest['chains']['pbc']['contracts']['Governance'] = address(77)
        manifest['sources']['src/Governance.sol'] = 'aa' * 32
        manifest['sources']['src/interfaces/IPolicyVersion.sol'] = 'bb' * 32
        manifest['fixture']['governance'] = {'maxGovernanceTtl': '120', 'maxAdmins': '8'}
        group = {'version': '2', 'threshold': threshold,
                 'witnesses': [address(i) for i in range(101, 105)],
                 'keyLabels': ['witness-1', 'witness-2', 'witness-3', 'witness-4'],
                 'usedBy': 'repaired-f only'}
        manifest['fixture']['witnessSet'] = group
    observation = {}
    expected = {'interfaceVersion': 'v2',
                'profile': {'name': manifest['profile'], 'enum': manifest['profileEnum']},
                'chains': {}, 'immutables': {}, 'witnessSets': {}, 'wiring': {}}
    all_addresses = {k: v for c in manifest['chains'].values() for k, v in c['contracts'].items()}
    enum = manifest['profileEnum']
    group = {k: manifest['fixture']['witnessSet'][k] for k in ('version', 'threshold', 'witnesses')}
    for chain_name, chain in manifest['chains'].items():
        anchor = {'number': str(int(chain['deployBlock']) + 5), 'hash': '0x' + ('ab' if chain_name == 'pbc' else 'cd') * 32}
        deploy = {'number': chain['deployBlock'], 'hash': '0x' + ('12' if chain_name == 'pbc' else '34') * 32}
        genesis = '0x' + ('56' if chain_name == 'pbc' else '78') * 32
        observed = {'chainId': chain['chainId'], 'genesisHash': genesis,
                    'deployBlock': deploy, 'anchor': anchor, 'confirmedAnchor': copy.deepcopy(anchor),
                    'code': {}, 'views': {}}
        bound = {'chainId': chain['chainId'], 'genesisHash': genesis,
                 'deployBlock': deploy, 'contracts': {}}
        for i, (name, addr) in enumerate(chain['contracts'].items()):
            raw = bytes([i + 1]) * 96
            refs = [{'start': '16', 'length': '32'}]
            masked = raw[:16] + bytes(32) + raw[48:]
            entry = copy.deepcopy(shape['entry'])
            entry.update(runtimeBytes='96', runtimeSha256=digest(masked),
                         immutableReferences=refs, immutableRefsSha256=digest(canonical(refs).encode()))
            manifest['abi'][name] = entry
            observed['code'][name] = {'anchor': copy.deepcopy(anchor), 'value': '0x' + raw.hex()}
            views = {}
            if name != 'Governance': views['configured'] = True
            if name in ('TMSC', 'PSC', 'KSSC', 'ACSC'):
                views.update(profile=enum, mutations=mask)
                expected['immutables'][name] = {'profile': enum, 'mutations': mask}
            if name in ('PSC', 'KSSC', 'Governance'):
                views.update(witnessSetVersion=group['version'], threshold=group['threshold'], witnesses=group['witnesses'])
                expected['witnessSets'][name.lower()] = copy.deepcopy(group)
            if name == 'PSC': views.update(rsc=all_addresses['RSC'], tmsc=all_addresses['TMSC'], lsc=all_addresses['LSC'], ksscForChain=all_addresses['KSSC'])
            if name == 'RSC': views.update(tmsc=all_addresses['TMSC'], lsc=all_addresses['LSC'])
            if name == 'TMSC':
                views.update(psc=all_addresses['PSC'], rsc=all_addresses['RSC'])
                if f: views['governance'] = all_addresses['Governance']
            if name == 'LSC': views.update(rsc=all_addresses['RSC'], tmsc=all_addresses['TMSC'], psc=all_addresses['PSC'])
            if name == 'KSSC': views['acsc'] = all_addresses['ACSC']
            if name == 'ACSC': views.update(kssc=all_addresses['KSSC'], pscRelay=manifest['fixture']['relay']['address'])
            if name == 'Governance':
                views.update(mutations=mask, target=all_addresses['TMSC'], governanceChainId=manifest['chains']['pbc']['chainId'], maxGovernanceTtl='120')
                expected['immutables'][name] = {'mutations': mask}
            observed['views'][name] = {key: {'anchor': copy.deepcopy(anchor), 'value': copy.deepcopy(value)} for key, value in views.items()}
            bound['contracts'][name] = {'address': addr, 'abiSha256': entry['abiSha256'],
                'codeSha256': digest(raw), 'runtimeSha256': entry['runtimeSha256'],
                'runtimeBytes': '96', 'immutableRefsSha256': entry['immutableRefsSha256']}
        observation[chain_name] = observed
        expected['chains'][chain_name] = bound
    expected['wiring'] = {'ksscForChain': all_addresses['KSSC'], 'acsc': all_addresses['ACSC'],
        'kssc': all_addresses['KSSC'], 'pscRelay': manifest['fixture']['relay']['address'],
        'tmsc': {'psc': all_addresses['PSC'], 'rsc': all_addresses['RSC']},
        'lsc': {'rsc': all_addresses['RSC'], 'tmsc': all_addresses['TMSC'], 'psc': all_addresses['PSC']}}
    if f: expected['wiring']['governance'] = {'tmsc': all_addresses['Governance'], 'target': all_addresses['TMSC']}
    return manifest, observation, expected


def subject():
    return importlib.import_module('evaluation.binding_context_v2')


@pytest.mark.parametrize('f,mask,q', [(True, '0', '3'), (True, '0', '2'), (True, '256', '3'), (False, '0', '3')])
def test_reconstructs_code_views_and_binding_without_using_an_export(f, mask, q):
    manifest, observations, expected = fixture(f, mask, q)
    before = copy.deepcopy((manifest, observations))
    actual = subject().reconstruct(manifest, observations, compiled_max_admins='8' if f else None)
    assert actual == expected
    assert (manifest, observations) == before
    export = {'owner': 'worker', 'document': expected, 'binding_v2': digest(b'hmbc-deployment-binding/v2\n' + canonical(expected).encode()),
              'anchor': {k: v['anchor'] for k, v in observations.items()}}
    assert subject().verify_export(export, manifest, observations, expected_owner='worker', compiled_max_admins='8' if f else None) == actual


@pytest.mark.parametrize('chain', ['pbc', 'dbc'])
@pytest.mark.parametrize('change', ['chainId', 'deployBlock', 'confirmedAnchor', 'old-anchor', 'mixed-code', 'mixed-view', 'missing-code', 'missing-view', 'extra-view', 'code-case', 'code-length', 'build', 'range-hash'])
def test_rejects_bad_identity_build_and_incomplete_or_mixed_block_reads(chain, change):
    m, o, _ = fixture()
    c = o[chain]; name = next(iter(c['code']))
    if change == 'chainId': c['chainId'] = '1'
    elif change == 'deployBlock': c['deployBlock']['number'] = '1'
    elif change == 'confirmedAnchor': c['confirmedAnchor']['hash'] = '0x' + 'ff' * 32
    elif change == 'old-anchor': c['anchor']['number'] = '0'
    elif change == 'mixed-code': c['code'][name]['anchor']['number'] = '0'
    elif change == 'mixed-view': next(iter(c['views'][name].values()))['anchor']['hash'] = '0x' + 'ff' * 32
    elif change == 'missing-code': del c['code'][name]
    elif change == 'missing-view': c['views'][name].pop(next(iter(c['views'][name])))
    elif change == 'extra-view': c['views'][name]['owner'] = {'anchor': c['anchor'], 'value': address(99)}
    elif change == 'code-case': c['code'][name]['value'] = '0x' + 'AF' * 96
    elif change == 'code-length': c['code'][name]['value'] += '00'
    elif change == 'build': c['code'][name]['value'] = '0xff' + c['code'][name]['value'][4:]
    else: m['abi'][name]['immutableRefsSha256'] = 'ff' * 32
    with pytest.raises(BAD): subject().reconstruct(m, o, compiled_max_admins='8')


GETTERS = [('pbc', 'PSC', k) for k in ('profile', 'mutations', 'threshold', 'witnessSetVersion', 'witnesses', 'rsc', 'tmsc', 'lsc', 'ksscForChain', 'configured')]
GETTERS += [('pbc', 'TMSC', k) for k in ('profile', 'mutations', 'psc', 'rsc', 'governance', 'configured')]
GETTERS += [('pbc', 'LSC', k) for k in ('rsc', 'tmsc', 'psc', 'configured')]
GETTERS += [('pbc', 'RSC', k) for k in ('tmsc', 'lsc', 'configured')]
GETTERS += [('pbc', 'Governance', k) for k in ('mutations', 'threshold', 'witnessSetVersion', 'witnesses', 'target', 'governanceChainId', 'maxGovernanceTtl')]
GETTERS += [('dbc', 'KSSC', k) for k in ('profile', 'mutations', 'threshold', 'witnessSetVersion', 'witnesses', 'acsc', 'configured')]
GETTERS += [('dbc', 'ACSC', k) for k in ('profile', 'mutations', 'kssc', 'pscRelay', 'configured')]


@pytest.mark.parametrize('chain,name,key', GETTERS)
def test_each_required_getter_is_checked_against_the_independent_fixture(chain, name, key):
    m, o, _ = fixture()
    row = o[chain]['views'][name][key]
    v = row['value']
    if key == 'configured': row['value'] = False
    elif key == 'witnesses': row['value'] = list(reversed(v))
    elif v.startswith('0x'): row['value'] = address(999)
    else: row['value'] = str(int(v) + 1)
    with pytest.raises(BAD): subject().reconstruct(m, o, compiled_max_admins='8')


@pytest.mark.parametrize('field', ['owner', 'document', 'binding_v2', 'anchor'])
def test_export_cannot_choose_its_own_context_even_with_a_recomputed_hash(field):
    m, o, d = fixture()
    e = {'owner': 'worker', 'document': d, 'binding_v2': digest(b'hmbc-deployment-binding/v2\n' + canonical(d).encode()),
         'anchor': {k: copy.deepcopy(v['anchor']) for k, v in o.items()}}
    if field == 'owner': e['owner'] = 'witness:' + address(101)
    elif field == 'anchor': e['anchor']['pbc']['number'] = '1'
    elif field == 'binding_v2': e[field] = 'ff' * 32
    else:
        e['document']['chains']['pbc']['genesisHash'] = '0x' + 'ff' * 32
        e['binding_v2'] = digest(b'hmbc-deployment-binding/v2\n' + canonical(e['document']).encode())
    with pytest.raises(BAD): subject().verify_export(e, m, o, expected_owner='worker', compiled_max_admins='8')


@pytest.mark.parametrize('bad', [None, '7', 8, True])
def test_governance_requires_the_separate_compiled_admin_bound(bad):
    m, o, _ = fixture()
    with pytest.raises(BAD): subject().reconstruct(m, o, compiled_max_admins=bad)


def test_explicit_v21_e_selection_and_profile_normalization():
    m, o, expected = fixture(False, '8')
    m['schemaVersion'] = 'hmbc-ledger-deployment/v2.1'
    m['sources']['src/Governance.sol'] = 'aa' * 32
    m['sources']['src/interfaces/IPolicyVersion.sol'] = 'bb' * 32
    m['profile'] = 'mutant-no-nonce'
    expected['profile']['name'] = 'repaired-e'
    assert subject().reconstruct(m, o) == expected


@pytest.mark.parametrize('marker', ['hmbc-ledger-deployment/v1', 'hmbc-ledger-deployment/v9'])
def test_unselected_carriers_refuse_without_structural_fallback(marker):
    m, o, _ = fixture(); m['schemaVersion'] = marker
    with pytest.raises(BAD): subject().reconstruct(m, o, compiled_max_admins='8')


def test_same_address_on_distinct_chains_is_a_valid_namespace():
    m, o, expected = fixture()
    repeated = m['chains']['pbc']['contracts']['LSC']
    m['chains']['dbc']['contracts']['KSSC'] = repeated
    o['pbc']['views']['PSC']['ksscForChain']['value'] = repeated
    o['dbc']['views']['ACSC']['kssc']['value'] = repeated
    expected['chains']['dbc']['contracts']['KSSC']['address'] = repeated
    expected['wiring']['ksscForChain'] = repeated
    expected['wiring']['kssc'] = repeated
    assert subject().reconstruct(m, o, compiled_max_admins='8') == expected


@pytest.mark.parametrize('name,enum,mask', [
    ('paper-strict', '0', '0'), ('paper-minimal', '1', '0'), ('repaired-e', '2', '0'),
    ('mutant-no-destination-binding', '2', '1'), ('mutant-no-state-barrier', '2', '2'),
    ('mutant-no-record-freshness', '2', '4'), ('mutant-no-nonce', '2', '8'),
    ('mutant-no-version-monotone', '2', '16'), ('mutant-no-receipt-binding', '2', '32')])
def test_all_nine_e_profile_names_are_normalized_by_the_closed_table(name, enum, mask):
    m, o, expected = fixture(False, mask)
    m.update(profile=name, profileEnum=enum)
    base = {'0': 'paper-strict', '1': 'paper-minimal', '2': 'repaired-e'}[enum]
    expected['profile'] = {'name': base, 'enum': enum}
    for chain in o.values():
        for views in chain['views'].values():
            if 'profile' in views: views['profile']['value'] = enum
    for views in expected['immutables'].values(): views['profile'] = enum
    assert subject().reconstruct(m, o) == expected


@pytest.mark.parametrize('change', ['code-immutable', 'genesis'])
def test_identity_changes_affect_binding_even_when_masked_build_is_unchanged(change):
    m, o, d = fixture()
    if change == 'code-immutable':
        o['dbc']['code']['ACSC']['value'] = '0x' + (bytes([1]) * 16 + bytes([99]) * 32 + bytes([1]) * 48).hex()
    else: o['pbc']['genesisHash'] = '0x' + 'fe' * 32
    actual = subject().reconstruct(m, o, compiled_max_admins='8')
    assert actual != d
    assert subject().binding_hash(actual) != subject().binding_hash(d)


@pytest.mark.parametrize('owner,valid', [('worker', True), ('witness:' + address(101), True), ('witness:' + address(900), False)])
def test_witness_export_owner_must_also_belong_to_the_reconstructed_set(owner, valid):
    m, o, d = fixture()
    e = {'owner': owner, 'document': d, 'binding_v2': digest(b'hmbc-deployment-binding/v2\n' + canonical(d).encode()),
         'anchor': {k: v['anchor'] for k, v in o.items()}}
    if valid:
        assert subject().verify_export(e, m, o, expected_owner=owner, compiled_max_admins='8') == d
    else:
        with pytest.raises(ValueError, match='owner membership'):
            subject().verify_export(e, m, o, expected_owner=owner, compiled_max_admins='8')
