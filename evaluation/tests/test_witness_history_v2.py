"""Declared signing-history controls; synthetic observations, real signatures."""
import copy
from functools import lru_cache
import hashlib
import importlib
import json

from eth_account.messages import encode_typed_data
from jsonschema import ValidationError
import pytest

from evaluation.binding_context_v2 import reconstruct
from evaluation.tests.test_signing_context_v2 import case, message, sign, domain
from evaluation.tests.test_certificates_v2 import VECTORS

NAMES = ['AccessDecision', 'StateCheckpoint', 'GrantReceipt', 'GovernanceAction']
BAD = (ValueError, ValidationError)


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True).encode()).hexdigest()


def fingerprint(evidence):
    evidence['evidenceSha256'] = sha({k: v for k, v in evidence.items() if k != 'evidenceSha256'})


def observation(chain, number=30, timestamp=1400, block_hash=None):
    return dict(chainId=chain, blockNumber=str(number), timestamp=str(timestamp),
                blockHash=block_hash or '0x' + f'{number:064x}')


def record(manifest, name, generation=0):
    value = message(manifest, name)
    field = {'AccessDecision': 'credentialDigest', 'StateCheckpoint': 'authEpoch',
             'GrantReceipt': 'grantId', 'GovernanceAction': 'root'}[name]
    value[field] = ('0x' + f'{generation + 10:064x}' if field in ('credentialDigest', 'grantId') else
                    '0x' + f'{generation + 10:040x}' if field == 'root' else str(generation + 10))
    if name != 'GrantReceipt':
        value['expiresAt'] = str(1050 + generation * 100)
    key = {'AccessDecision': 'requestDigest', 'StateCheckpoint': 'sequence',
           'GrantReceipt': 'requestDigest', 'GovernanceAction': 'nonce'}[name]
    typed = copy.deepcopy(next(v['typedData'] for v in VECTORS if v['name'] == name))
    chain, contract = domain(manifest, name)
    typed['domain'].update(chainId=chain, verifyingContract=contract)
    typed['message'] = value
    from eth_utils import keccak
    encoded = encode_typed_data(full_message=typed)
    digest = '0x' + keccak(b'\x19' + encoded.version + encoded.header + encoded.body).hex()
    effect = {k: v for k, v in value.items() if k not in (key, 'expiresAt')}
    signed = dict(digest=digest, signature=sign(manifest, name, value)[0],
                  observation=observation(chain, 10 + generation * 10, 1000 + generation * 100))
    if name != 'GrantReceipt': signed['expiresAt'] = value['expiresAt']
    return dict(type=name, domainSeparator='0x' + encoded.header.hex(),
                witnessSetVersion=value['witnessSetVersion'], keyField=value[key],
                effect=effect, vHash=sha(effect), digests=[signed])


@lru_cache
def _fixture(f=True, q='3'):
    manifest, observed, _ = case(f, q)
    document = reconstruct(manifest, observed, compiled_max_admins='8' if f else None)
    from evaluation.schema_v2 import _binding_digest
    binding = dict(document=document, binding_v2=_binding_digest(document))
    owner = 'witness:' + sorted(manifest['fixture']['witnessSet']['witnesses'])[0]
    evidence = dict(schemaVersion='hmbc-witness-evidence/v2', owner=owner, binding=binding,
                    marker=dict(binding_v2=binding['binding_v2'], owner=owner, schema='2'),
                    observations=sorted([observation(v['chainId']) for v in manifest['chains'].values()],
                                        key=lambda v: int(v['chainId'])),
                    faulted=None, faultLog=[], superseded=[],
                    conflicts=[record(manifest, n) for n in NAMES if f or n != 'GovernanceAction'])
    fingerprint(evidence)
    return manifest, observed, evidence


def fixture(f=True, q='3'):
    return copy.deepcopy(_fixture(f, q))


def check(manifest, observed, evidence, owner=None):
    return importlib.import_module('evaluation.witness_history_v2').verify_signed_history(
        evidence, manifest=manifest, observations=observed,
        expected_owner=evidence['owner'] if owner is None else owner,
        compiled_max_admins='8' if manifest['profileEnum'] == '3' else None)


def supersede(manifest, evidence, name, count=1, kind='expiry'):
    live = next(r for r in evidence['conflicts'] if r['type'] == name)
    evidence['conflicts'].remove(live)
    for generation in range(count):
        row = record(manifest, name, generation)
        row.update(seq=str(len(evidence['superseded']) + 1), death=dict(kind=kind,
            observation=observation(domain(manifest, name)[0], 15 + generation * 10, 1050 + generation * 100)))
        if kind.startswith('overtaken-') and kind != 'overtaken-decision-grant':
            row['death']['observed'] = str(int(row['effect'].get('stateSequence', row['keyField'])) + 1)
        evidence['superseded'].append(row)
    evidence['conflicts'].append(record(manifest, name, count))
    evidence['conflicts'].sort(key=lambda r: NAMES.index(r['type']))
    fingerprint(evidence)


@pytest.mark.parametrize('f,q', [(True, '3'), (True, '2'), (False, '1')])
def test_positive_empty_and_populated_history(f, q):
    m, o, e = fixture(f, q)
    before = copy.deepcopy((m, o, e))
    result = check(m, o, e)
    assert result == dict(recordsChecked=4 if f else 3, signaturesChecked=4 if f else 3,
                          declaredSafeLedgerInterval=True, excludedDeathSeqs=[])
    assert (m, o, e) == before
    e['conflicts'] = []; e['observations'] = []; fingerprint(e)
    assert check(m, o, e)['recordsChecked'] == 0


@pytest.mark.parametrize('name', NAMES)
def test_live_successor_and_all_death_kinds(name):
    kinds = {'AccessDecision': ['expiry', 'overtaken-decision-sequence', 'overtaken-decision-grant'],
             'StateCheckpoint': ['expiry', 'overtaken-checkpoint'],
             'GovernanceAction': ['expiry', 'overtaken-governance'],
             'GrantReceipt': ['executed-receipt']}[name]
    for kind in kinds:
        m, o, e = fixture()
        supersede(m, e, name, kind=kind)
        assert check(m, o, e)['recordsChecked'] == 5


@pytest.mark.parametrize('name', NAMES)
@pytest.mark.parametrize('change', ['digest', 'signature', 'domain', 'version', 'effect', 'key', 'owner'])
def test_signed_record_cannot_choose_its_own_identity(name, change):
    m, o, e = fixture()
    row = next(r for r in e['conflicts'] if r['type'] == name)
    if change == 'digest': row['digests'][0]['digest'] = '0x' + '99' * 32
    if change == 'signature':
        row['digests'][0]['signature'] = sign(m, name, message(m, name))[-1]
    if change == 'domain': row['domainSeparator'] = '0x' + '99' * 32
    if change == 'version': row['witnessSetVersion'] = '1'
    if change == 'effect':
        row['effect'][next(k for k in row['effect'] if k not in ('witnessSetVersion', 'admins'))] = '0'
        row['vHash'] = sha(row['effect'])
    if change == 'key': row['keyField'] = '2' if name in ('StateCheckpoint', 'GovernanceAction') else '0x' + '99' * 32
    if change == 'owner':
        e['owner'] = 'witness:' + sorted(m['fixture']['witnessSet']['witnesses'])[-1]
        e['marker']['owner'] = e['owner']
    fingerprint(e)
    with pytest.raises(BAD): check(m, o, e)


@pytest.mark.parametrize('change', ['owner', 'marker', 'binding', 'observation', 'fingerprint', 'vhash',
                                  'live-order', 'live-duplicate', 'digest-duplicate', 'target-chain',
                                  'missing-target', 'last-number', 'last-time', 'equal-block-hash'])
def test_declared_document_joins(change):
    m, o, e = fixture()
    row = e['conflicts'][0]
    signed = row['digests'][0]
    if change == 'owner':
        with pytest.raises(ValueError, match='owner'): check(m, o, e, 'witness:' + '99' * 20)
        return
    if change == 'marker': e['marker']['owner'] = 'witness:' + '99' * 20
    if change == 'binding': e['binding']['document']['chains']['pbc']['chainId'] = '999'
    if change == 'observation': o['pbc']['confirmedAnchor']['hash'] = '0x' + '99' * 32
    if change == 'vhash': row['vHash'] = '99' * 32
    if change == 'live-order': e['conflicts'].reverse()
    if change == 'live-duplicate': e['conflicts'].insert(0, copy.deepcopy(row))
    if change == 'digest-duplicate': row['digests'].append(copy.deepcopy(signed))
    if change == 'target-chain': signed['observation']['chainId'] = m['chains']['pbc']['chainId']
    if change == 'missing-target': e['observations'] = [v for v in e['observations'] if v['chainId'] != signed['observation']['chainId']]
    if change.startswith('last-') or change == 'equal-block-hash':
        last = next(v for v in e['observations'] if v['chainId'] == signed['observation']['chainId'])
        if change == 'last-number': last['blockNumber'] = '9'
        if change == 'last-time': last['timestamp'] = '999'
        if change == 'equal-block-hash': last.update(blockNumber='10', blockHash='0x' + '99' * 32)
    fingerprint(e)
    if change == 'fingerprint': e['evidenceSha256'] = '99' * 32
    with pytest.raises(BAD): check(m, o, e)


@pytest.mark.parametrize('name', NAMES)
@pytest.mark.parametrize('change', ['orphan', 'same-effect', 'seq-gap', 'generation-number', 'generation-time', 'generation-hash'])
def test_generation_integrity(name, change):
    m, o, e = fixture()
    supersede(m, e, name, kind='executed-receipt' if name == 'GrantReceipt' else 'expiry')
    old = e['superseded'][0]; live = next(r for r in e['conflicts'] if r['type'] == name)
    if change == 'orphan': e['conflicts'].remove(live)
    if change == 'same-effect':
        live['effect'] = copy.deepcopy(old['effect']); live['vHash'] = old['vHash']
    if change == 'seq-gap': old['seq'] = '2'
    if change.startswith('generation-'):
        ob = live['digests'][0]['observation']; death = old['death']['observation']
        if change == 'generation-number': ob['blockNumber'] = '14'
        if change == 'generation-time': ob['timestamp'] = '1049'
        if change == 'generation-hash': ob.update(blockNumber=death['blockNumber'], blockHash='0x' + '99' * 32)
    fingerprint(e)
    with pytest.raises(BAD): check(m, o, e)


def test_nonadjacent_effect_recurrence_and_equal_generation_block_are_legal():
    m, o, e = fixture(); supersede(m, e, 'GovernanceAction', count=2)
    live = e['conflicts'][-1]; first = e['superseded'][0]
    # A -> B -> A, with a fresh liveness value and correctly recomputed signature.
    value = message(m, 'GovernanceAction'); value.update(first['effect'])
    value.update(nonce=live['keyField'], expiresAt=live['digests'][0]['expiresAt'])
    live['effect'] = copy.deepcopy(first['effect']); live['vHash'] = first['vHash']
    typed = copy.deepcopy(next(v['typedData'] for v in VECTORS if v['name'] == 'GovernanceAction'))
    chain, contract = domain(m, 'GovernanceAction'); typed['domain'].update(chainId=chain, verifyingContract=contract)
    typed['message'] = value
    from eth_utils import keccak
    encoded = encode_typed_data(full_message=typed)
    live['digests'][0].update(digest='0x' + keccak(b'\x19' + encoded.version + encoded.header + encoded.body).hex(),
                            signature=sign(m, 'GovernanceAction', value)[0],
                            observation=copy.deepcopy(e['superseded'][-1]['death']['observation']))
    fingerprint(e)
    assert check(m, o, e)['recordsChecked'] == 6


@pytest.mark.parametrize('name,kind,invalid', [
    ('AccessDecision', 'expiry', 'time'), ('StateCheckpoint', 'expiry', 'time'),
    ('GovernanceAction', 'expiry', 'time'),
    ('AccessDecision', 'overtaken-decision-sequence', 'sequence'),
    ('StateCheckpoint', 'overtaken-checkpoint', 'sequence'),
    ('GovernanceAction', 'overtaken-governance', 'sequence'),
    ('AccessDecision', 'overtaken-decision-grant', 'deny'),
])
def test_invalid_death_predicates(name, kind, invalid):
    m, o, e = fixture(); supersede(m, e, name, kind=kind)
    row = e['superseded'][0]
    if invalid == 'time': row['death']['observation']['timestamp'] = '1049'
    if invalid == 'sequence': row['death']['observed'] = '0'
    if invalid == 'deny': row['effect']['result'] = '0'; row['vHash'] = sha(row['effect'])
    fingerprint(e)
    with pytest.raises(BAD): check(m, o, e)


def fault(e, reason='number-regression'):
    previous = copy.deepcopy(e['observations'][0]); seen = copy.deepcopy(previous)
    if reason == 'number-regression': seen['blockNumber'] = '1'
    if reason == 'timestamp-regression': seen['timestamp'] = '1'
    if reason == 'hash-changed': seen['blockHash'] = '0x' + '99' * 32
    return dict(reason=reason, previous=previous, observed=seen)


@pytest.mark.parametrize('reason', ['number-regression', 'timestamp-regression', 'hash-changed'])
@pytest.mark.parametrize('cleared', [False, True])
def test_fault_intervals_are_labelled_and_cannot_erase_orphans(reason, cleared):
    m, o, e = fixture(); f = fault(e, reason)
    if cleared: e['faultLog'] = [dict(seq='1', fault=f, clearedAgainst=copy.deepcopy(e['observations'][0]), note='synthetic clear')]
    else: e['faulted'] = f
    # Declared monotonicity is deliberately not applied outside its assumption.
    e['conflicts'][0]['digests'][0]['observation']['blockNumber'] = '999'
    fingerprint(e)
    assert check(m, o, e)['declaredSafeLedgerInterval'] is False
    supersede(m, e, 'GovernanceAction'); e['conflicts'].pop(); fingerprint(e)
    with pytest.raises(ValueError, match='successor'): check(m, o, e)


@pytest.mark.parametrize('bit,name,kind', [(1, 'AccessDecision', 'overtaken-decision-sequence'),
    (1, 'StateCheckpoint', 'overtaken-checkpoint'), (5, 'GrantReceipt', 'executed-receipt')])
def test_mutant_death_exclusions_are_explicit(bit, name, kind):
    m, o, e = fixture()
    m['mutations'] = str(1 << bit)
    for views in o.values():
        for v in views['views'].values():
            if 'mutations' in v: v['mutations']['value'] = m['mutations']
    document = reconstruct(m, o, compiled_max_admins='8')
    from evaluation.schema_v2 import _binding_digest
    e['binding'] = dict(document=document, binding_v2=_binding_digest(document))
    e['marker']['binding_v2'] = e['binding']['binding_v2']
    supersede(m, e, name, kind=kind)
    assert check(m, o, e)['excludedDeathSeqs'] == ['1']


def resign(manifest, row, *, changed_domain=None, signer=None, expires=None):
    name = row['type']
    value = dict(row['effect']); value[{'AccessDecision': 'requestDigest', 'StateCheckpoint': 'sequence',
                                      'GrantReceipt': 'requestDigest', 'GovernanceAction': 'nonce'}[name]] = row['keyField']
    signed = copy.deepcopy(row['digests'][0])
    if name != 'GrantReceipt':
        value['expiresAt'] = expires or signed['expiresAt']; signed['expiresAt'] = value['expiresAt']
    typed = copy.deepcopy(next(v['typedData'] for v in VECTORS if v['name'] == name))
    chain, contract = domain(manifest, name); typed['domain'].update(chainId=chain, verifyingContract=contract)
    typed['domain'].update(changed_domain or {}); typed['message'] = value
    from eth_utils import keccak
    encoded = encode_typed_data(full_message=typed)
    signed.update(digest='0x' + keccak(b'\x19' + encoded.version + encoded.header + encoded.body).hex(),
                  signature=sign(manifest, name, value, changed_domain=changed_domain,
                                 signers=None if signer is None else [signer])[0])
    row['vHash'] = sha(row['effect']); row['domainSeparator'] = '0x' + encoded.header.hex()
    return signed


@pytest.mark.parametrize('name', NAMES)
@pytest.mark.parametrize('change', [{'chainId': '999'}, {'name': 'WrongDomain'}, {'version': '2'},
                                  {'verifyingContract': '0x' + '99' * 20}])
def test_valid_signature_and_self_consistent_digest_cannot_select_domain(name, change):
    m, o, e = fixture(); row = next(r for r in e['conflicts'] if r['type'] == name)
    row['digests'] = [resign(m, row, changed_domain=change)]; fingerprint(e)
    with pytest.raises(ValueError): check(m, o, e)


@pytest.mark.parametrize('name,field,value', [
    ('StateCheckpoint', 'sourceChainId', '999'), ('StateCheckpoint', 'psc', '0x' + '99' * 20),
    ('GrantReceipt', 'dbcChainId', '999'), ('GrantReceipt', 'kssc', '0x' + '99' * 20)])
def test_valid_signature_cannot_change_embedded_ledger(name, field, value):
    m, o, e = fixture(); row = next(r for r in e['conflicts'] if r['type'] == name)
    row['effect'][field] = value; row['digests'] = [resign(m, row)]; fingerprint(e)
    with pytest.raises(ValueError, match='embedded'): check(m, o, e)


@pytest.mark.parametrize('name', NAMES)
def test_configured_signature_is_bound_to_exact_store_owner(name):
    m, o, e = fixture(); row = next(r for r in e['conflicts'] if r['type'] == name)
    row['digests'] = [resign(m, row, signer=sorted(m['fixture']['witnessSet']['witnesses'])[-1])]
    fingerprint(e)
    with pytest.raises(ValueError, match='signer'): check(m, o, e)


@pytest.mark.parametrize('name', ['AccessDecision', 'StateCheckpoint', 'GovernanceAction'])
@pytest.mark.parametrize('change', ['none', 'bad-second-signature', 'bad-second-digest', 'order', 'latest-expiry'])
def test_every_liveness_digest_is_checked(name, change):
    m, o, e = fixture(); row = next(r for r in e['conflicts'] if r['type'] == name)
    second = resign(m, row, expires='1060'); row['digests'].append(second)
    if change == 'bad-second-signature': second['signature'] = sign(m, name, message(m, name))[-1]
    if change == 'bad-second-digest': second['digest'] = '0x' + '99' * 32
    if change == 'order': row['digests'].reverse()
    if change == 'latest-expiry':
        e['conflicts'].remove(row)
        row.update(seq='1', death=dict(kind='expiry', observation=observation(domain(m, name)[0], 15, 1055)))
        e['superseded'].append(row); e['conflicts'].append(record(m, name, 1))
        e['conflicts'].sort(key=lambda r: NAMES.index(r['type']))
    fingerprint(e)
    if change == 'none': assert check(m, o, e)['signaturesChecked'] == 5
    else:
        with pytest.raises(BAD): check(m, o, e)


@pytest.mark.parametrize('change', ['predicate', 'previous-last', 'chain', 'clear-seq', 'clear-baseline-number',
                                  'clear-baseline-time', 'clear-baseline-chain', 'clear-baseline-hash'])
def test_fault_and_clear_layout_is_checked(change):
    m, o, e = fixture(); f = fault(e)
    e['faulted'] = f
    if change == 'predicate': f['observed'] = copy.deepcopy(f['previous'])
    if change == 'previous-last': f['previous']['blockHash'] = '0x' + '99' * 32
    if change == 'chain': f['observed']['chainId'] = '999'
    if change.startswith('clear-'):
        e['faulted'] = None
        c = dict(seq='1', fault=f, clearedAgainst=copy.deepcopy(e['observations'][0]), note='synthetic')
        e['faultLog'] = [c]
        if change == 'clear-seq': c['seq'] = '2'
        if change == 'clear-baseline-number': c['clearedAgainst']['blockNumber'] = '31'
        if change == 'clear-baseline-time': c['clearedAgainst']['timestamp'] = '1401'
        if change == 'clear-baseline-chain': c['clearedAgainst']['chainId'] = m['chains']['dbc']['chainId']
        if change == 'clear-baseline-hash': c['clearedAgainst']['blockHash'] = '0x' + '99' * 32
    fingerprint(e)
    with pytest.raises(ValueError): check(m, o, e)


@pytest.mark.parametrize('where', ['superseded', 'live'])
def test_every_history_signature_and_death_target_are_checked(where):
    m, o, e = fixture(); supersede(m, e, 'AccessDecision')
    row = e['superseded'][0] if where == 'superseded' else e['conflicts'][0]
    row['digests'][0]['signature'] = sign(m, 'AccessDecision', message(m, 'AccessDecision'))[-1]
    fingerprint(e)
    with pytest.raises(ValueError): check(m, o, e)
    m, o, e = fixture(); supersede(m, e, 'AccessDecision')
    e['superseded'][0]['death']['observation']['chainId'] = m['chains']['pbc']['chainId']; fingerprint(e)
    with pytest.raises(ValueError, match='death target'): check(m, o, e)
