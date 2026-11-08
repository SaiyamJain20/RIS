"""Independent declared witness-history joins for the HMBC2020 reconstruction.

Rebuild signed messages from K/effect/liveness, recover the caller-pinned owner
under independently reconstructed context, and check declared layout/generations.
This internal API does not switch consumers or authorize services. A consistent
signed export does not establish native ledger facts or completeness relative to
WAL-aware SQLite rows and INITIALIZED bytes. Those joins remain caller work.
Faults/clears explicitly leave the safe-ledger interval; mutation death exclusions
are returned, never silently promoted to baseline evidence.
"""
import hashlib
import json

from evaluation.binding_context_v2 import reconstruct
from evaluation.schema_v2 import validate
from evaluation.signing_context_v2 import verify_bound_signature

_TYPES = ('AccessDecision', 'StateCheckpoint', 'GrantReceipt', 'GovernanceAction')
_KEYS = dict(zip(_TYPES, ('requestDigest', 'sequence', 'requestDigest', 'nonce')))
_CHAINS = dict(zip(_TYPES, ('dbc', 'dbc', 'pbc', 'pbc')))


def _require(condition, message):
    if not condition:
        raise ValueError('Invalid witness history: ' + message)


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True).encode()).hexdigest()


def _key(row):
    key = row['keyField']
    if row['type'] in ('StateCheckpoint', 'GovernanceAction'):
        key = int(key)
    return (_TYPES.index(row['type']), row['domainSeparator'], int(row['witnessSetVersion']), key)


def _not_before(later, earlier):
    return (later['chainId'] == earlier['chainId']
            and int(later['blockNumber']) >= int(earlier['blockNumber'])
            and int(later['timestamp']) >= int(earlier['timestamp'])
            and (later['blockNumber'] != earlier['blockNumber'] or later['blockHash'] == earlier['blockHash']))


def _fault(fault, last):
    previous, observed = fault['previous'], fault['observed']
    _require(previous['chainId'] == observed['chainId'] and previous['chainId'] in last,
             'fault chain')
    reason = fault['reason']
    predicate = {
        'number-regression': int(observed['blockNumber']) < int(previous['blockNumber']),
        'timestamp-regression': int(observed['timestamp']) < int(previous['timestamp']),
        'hash-changed': observed['blockNumber'] == previous['blockNumber']
                        and observed['blockHash'] != previous['blockHash'],
    }
    _require(predicate[reason], 'fault predicate')


def _death(row, chain_id):
    death = row['death']
    _require(death['observation']['chainId'] == chain_id, 'death target chain')
    kind = death['kind']
    if kind == 'expiry':
        _require(all(int(death['observation']['timestamp']) >= int(d['expiresAt'])
                     for d in row['digests']), 'death before latest expiry')
    elif kind == 'overtaken-decision-sequence':
        _require(int(death['observed']) > int(row['effect']['stateSequence']), 'decision death sequence')
    elif kind in ('overtaken-checkpoint', 'overtaken-governance'):
        _require(int(death['observed']) >= int(row['keyField']), 'death sequence')
    # Type/ALLOW-only/closed death fields are enforced by the published schema.


def verify_signed_history(evidence, *, manifest, observations, expected_owner,
                          compiled_max_admins=None):
    """Return checked counts, declared interval status and excluded death seqs.

    expected_owner is selected independently by the caller for this store. The
    export cannot select its own trust context. Every historical K must retain a
    live successor, including after a declared fault or clear. This API verifies
    the declared document only; it does not prove the exporter omitted no rows.
    """
    validate('WitnessEvidence', evidence)
    document = reconstruct(manifest, observations, compiled_max_admins=compiled_max_admins)
    _require(evidence['binding']['document'] == document, 'binding differs from reconstructed context')
    _require(evidence['owner'] == expected_owner, 'caller-pinned owner mismatch')
    owner = expected_owner.removeprefix('witness:')
    _require(expected_owner == 'witness:' + owner and
             owner in document['witnessSets']['kssc']['witnesses'], 'unconfigured owner')
    marker = evidence['marker']
    _require(marker == dict(binding_v2=evidence['binding']['binding_v2'], owner=expected_owner, schema='2'),
             'declared marker mismatch')
    _require(evidence['evidenceSha256'] == _sha({k: v for k, v in evidence.items() if k != 'evidenceSha256'}),
             'evidence fingerprint')

    chain_ids = {v['chainId'] for v in document['chains'].values()}
    ids = [o['chainId'] for o in evidence['observations']]
    _require(ids == sorted(set(ids), key=int) and set(ids) <= chain_ids, 'last observation order/chains')
    last = {o['chainId']: o for o in evidence['observations']}
    safe = evidence['faulted'] is None and not evidence['faultLog']
    if evidence['faulted'] is not None:
        _fault(evidence['faulted'], last)
        _require(evidence['faulted']['previous'] == last[evidence['faulted']['previous']['chainId']],
                 'fault previous differs from last observation')
    for i, cleared in enumerate(evidence['faultLog'], 1):
        _require(cleared['seq'] == str(i), 'clear append sequence')
        _fault(cleared['fault'], last)
        baseline = cleared['clearedAgainst']
        _require(baseline['chainId'] == cleared['fault']['observed']['chainId']
                 and _not_before(last[baseline['chainId']], baseline), 'clear baseline')

    live = evidence['conflicts']
    keys = [_key(row) for row in live]
    _require(keys == sorted(set(keys)), 'live key order/uniqueness')
    generations = {key: [] for key in keys}
    superseded = evidence['superseded']
    for i, row in enumerate(superseded, 1):
        _require(row['seq'] == str(i), 'superseded append sequence')
        key = _key(row)
        _require(key in generations, 'superseded key missing live successor')
        generations[key].append(row)
    for key, row in zip(keys, live):
        generations[key].append(row)

    seen = set()
    signatures = 0
    excluded = []
    mutations = int(manifest['mutations'])
    for rows in generations.values():
        previous = None
        for row in rows:
            name = row['type']
            chain_id = document['chains'][_CHAINS[name]]['chainId']
            _require(chain_id in last, 'missing target last observation')
            _require(row['witnessSetVersion'] == row['effect']['witnessSetVersion'], 'record/effect set mismatch')
            _require(row['vHash'] == _sha(row['effect']), 'effect fingerprint')
            if previous:
                _require(previous['vHash'] != row['vHash'], 'adjacent equal generation effects')
            digest_keys = [(int(d.get('expiresAt', '0')), d['digest']) for d in row['digests']]
            _require(digest_keys == sorted(digest_keys), 'digest order')
            for signed in row['digests']:
                _require(signed['digest'] not in seen, 'duplicate digest across store')
                seen.add(signed['digest'])
                ob = signed['observation']
                _require(ob['chainId'] == chain_id, 'digest target chain')
                if safe:
                    _require(_not_before(last[chain_id], ob), 'digest exceeds last observation')
                    if previous:
                        _require(_not_before(ob, previous['death']['observation']), 'generation before prior death')
                message = dict(row['effect'])
                message[_KEYS[name]] = row['keyField']
                if name != 'GrantReceipt':
                    message['expiresAt'] = signed['expiresAt']
                checked = verify_bound_signature(name, message, signed['signature'], owner=owner,
                    manifest=manifest, observations=observations, compiled_max_admins=compiled_max_admins)
                _require(checked['digest'] == signed['digest'], 'signed digest mismatch')
                _require(checked['domainSeparator'] == row['domainSeparator'], 'domain separator mismatch')
                signatures += 1
            if 'death' in row:
                _death(row, chain_id)
                if safe:
                    _require(_not_before(last[chain_id], row['death']['observation']), 'death exceeds last observation')
                kind = row['death']['kind']
                if (mutations & (1 << 1) and kind in ('overtaken-checkpoint', 'overtaken-decision-sequence')
                        or mutations & (1 << 5) and kind == 'executed-receipt'):
                    excluded.append(row['seq'])
            previous = row
    return dict(recordsChecked=len(live) + len(superseded), signaturesChecked=signatures,
                declaredSafeLedgerInterval=safe, excludedDeathSeqs=sorted(excluded, key=int))
