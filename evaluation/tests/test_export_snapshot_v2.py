"""Synthetic exporter bytes and real local snapshots; no owner runtime imports."""
import copy
import hashlib
import importlib
import json
import sqlite3

import pytest
from jsonschema import ValidationError

from evaluation.store_snapshot_v2 import Snapshot, locked_store
from evaluation.tests.test_witness_history_v2 import fixture, fingerprint, supersede, fault

BAD = (ValueError, ValidationError)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def setup(kind='BindingExport', f=True, q='3', worker=False):
    m, o, e = fixture(f, q)
    owner = 'worker' if worker else e['owner']
    marker = dict(e['marker'], owner=owner)
    export = (dict(e['binding'], owner=owner,
                   anchor={k: o[k]['anchor'] for k in ('pbc', 'dbc')})
              if kind == 'BindingExport' else e)
    snapshot = Snapshot(b'PRIVATE synthetic rows', canonical(marker), 'aa' * 32, None)
    return dict(kind=kind, snapshot=snapshot, manifest=m, observations=o,
                expected_owner=owner, compiled_max_admins='8' if f else None), export


def check(args, export, **changes):
    kw = dict(stderr=b'', exit_code=0, **args)
    kw.update(changes)
    return importlib.import_module('evaluation.export_snapshot_v2').verify_export_snapshot(
        canonical(export) + b'\n', **kw)


@pytest.mark.parametrize('kind', ['BindingExport', 'WitnessEvidence'])
@pytest.mark.parametrize('f,q', [(True, '3'), (True, '2'), (False, '1')])
def test_positive_profiles_real_signatures_and_no_input_mutation(kind, f, q):
    args, export = setup(kind, f, q)
    before = copy.deepcopy((args, export))
    result = check(args, export)
    assert result['owner'] == args['expected_owner']
    assert result['markerSha256'] == args['snapshot'].marker_sha256
    assert result['logicalSha256'] == args['snapshot'].logical_sha256
    assert result['stdoutSha256'] == hashlib.sha256(canonical(export) + b'\n').hexdigest()
    assert result['binding_v2'] == (export['binding_v2'] if kind == 'BindingExport'
                                   else export['binding']['binding_v2'])
    assert result['history'] is None if kind == 'BindingExport' else result['history']['signaturesChecked'] == (4 if f else 3)
    assert (args, export) == before


def test_worker_binding_is_supported():
    args, export = setup(worker=True)
    assert check(args, export)['owner'] == 'worker'


@pytest.mark.parametrize('kind', ['BindingExport', 'WitnessEvidence'])
@pytest.mark.parametrize('change', ['owner', 'binding_v2', 'schema', 'extra', 'missing'])
def test_physical_marker_cannot_be_self_declared(kind, change):
    args, export = setup(kind)
    marker = json.loads(args['snapshot'].marker)
    if change == 'owner': marker['owner'] = 'worker'
    if change == 'binding_v2': marker['binding_v2'] = '99' * 32
    if change == 'schema': marker['schema'] = 2
    if change == 'extra': marker['extra'] = None
    if change == 'missing': del marker['schema']
    args['snapshot'] = Snapshot(args['snapshot'].logical, canonical(marker), 'aa' * 32, None)
    with pytest.raises(ValueError, match='marker'): check(args, export)


@pytest.mark.parametrize('raw', [b'', b'null', b'[]', b'{}x', b'{', b'\xff',
    b'{"schema":"1","schema":"2"}', b'{"a":NaN}', b'{"a":Infinity}',
    b'\xef\xbb\xbf{}'])
def test_invalid_marker_json_refused(raw):
    args, export = setup()
    args['snapshot'] = Snapshot(b'rows', raw, 'aa' * 32, None)
    with pytest.raises(ValueError, match='marker'): check(args, export)


def test_marker_whitespace_permitted_but_exact_bytes_fingerprinted():
    args, export = setup()
    original = args['snapshot']
    raw = b' \n' + json.dumps(json.loads(original.marker), indent=2).encode() + b'\n'
    args['snapshot'] = Snapshot(original.logical, raw, original.main_sha256, None)
    assert check(args, export)['markerSha256'] != original.marker_sha256


@pytest.mark.parametrize('key', ['schema', 'owner', 'binding_v2'])
def test_duplicate_marker_keys_refused_even_if_last_value_matches(key):
    args, export = setup()
    original = args['snapshot']
    raw = b'{' + canonical(key) + b':"wrong",' + original.marker[1:]
    args['snapshot'] = Snapshot(original.logical, raw, original.main_sha256, None)
    with pytest.raises(ValueError, match='marker'): check(args, export)


@pytest.mark.parametrize('framing', ['no-lf', 'extra-lf', 'crlf', 'prefix', 'suffix',
    'pretty', 'duplicate', 'bom', 'garbage', 'nonascii', 'nonbytes'])
def test_export_requires_exact_canonical_single_line(framing):
    args, export = setup()
    raw = canonical(export) + b'\n'
    raw = {'no-lf': raw[:-1], 'extra-lf': raw + b'\n', 'crlf': raw[:-1] + b'\r\n',
           'prefix': b' ' + raw, 'suffix': raw + b' ',
           'pretty': json.dumps(export, indent=2).encode() + b'\n',
           'duplicate': b'{"owner":"worker",' + raw[1:], 'bom': b'\xef\xbb\xbf' + raw,
           'garbage': b'null\n', 'nonascii': b'{"x":"\xff"}\n',
           'nonbytes': raw.decode()}[framing]
    api = importlib.import_module('evaluation.export_snapshot_v2')
    with pytest.raises(ValueError, match='export'):
        api.verify_export_snapshot(raw, stderr=b'', exit_code=0, **args)


@pytest.mark.parametrize('changes', [dict(exit_code=3), dict(exit_code=2), dict(exit_code=-9),
    dict(exit_code=False), dict(stderr=b'warning\n'), dict(stderr=''), dict(kind='Error')])
def test_refusal_usage_failure_or_wrong_kind_never_succeeds(changes):
    args, export = setup()
    with pytest.raises(ValueError, match='export'): check(args, export, **changes)


@pytest.mark.parametrize('kind', ['BindingExport', 'WitnessEvidence'])
@pytest.mark.parametrize('change', ['owner', 'context', 'digest', 'anchor-or-signature'])
def test_existing_context_and_signature_checks_are_composed(kind, change):
    args, export = setup(kind)
    binding = export if kind == 'BindingExport' else export['binding']
    if change == 'owner': args['expected_owner'] = 'worker'
    if change == 'context': args['observations']['pbc']['chainId'] = '777'
    if change == 'digest': binding['binding_v2'] = '99' * 32
    if change == 'anchor-or-signature':
        if kind == 'BindingExport': export['anchor']['pbc']['hash'] = '0x' + '99' * 32
        else: export['conflicts'][0]['digests'][0]['signature'] = '0x' + '00' * 65
    if kind == 'WitnessEvidence': fingerprint(export)
    with pytest.raises(BAD): check(args, export)


def test_generations_survive_composition():
    args, export = setup('WitnessEvidence')
    supersede(args['manifest'], export, 'GovernanceAction', count=2)
    assert check(args, export)['history']['recordsChecked'] == 6


@pytest.mark.parametrize('cleared', [False, True])
def test_fault_labels_survive_composition(cleared):
    args, export = setup('WitnessEvidence')
    f = fault(export)
    if cleared:
        export['faultLog'] = [dict(seq='1', fault=f,
            clearedAgainst=copy.deepcopy(export['observations'][0]), note='synthetic clear')]
    else:
        export['faulted'] = f
    fingerprint(export)
    assert check(args, export)['history']['declaredSafeLedgerInterval'] is False


@pytest.mark.parametrize('bit,name,kind', [(1, 'StateCheckpoint', 'overtaken-checkpoint'),
                                         (5, 'GrantReceipt', 'executed-receipt')])
def test_death_exclusions_survive_composition(bit, name, kind):
    from evaluation.binding_context_v2 import reconstruct
    from evaluation.schema_v2 import _binding_digest
    args, export = setup('WitnessEvidence')
    args['manifest']['mutations'] = str(1 << bit)
    for views in args['observations'].values():
        for v in views['views'].values():
            if 'mutations' in v:
                v['mutations']['value'] = args['manifest']['mutations']
    document = reconstruct(args['manifest'], args['observations'], compiled_max_admins='8')
    export['binding'] = dict(document=document, binding_v2=_binding_digest(document))
    export['marker']['binding_v2'] = export['binding']['binding_v2']
    supersede(args['manifest'], export, name, kind=kind)
    args['snapshot'] = Snapshot(b'rows', canonical(export['marker']), 'aa' * 32, None)
    assert check(args, export)['history']['excludedDeathSeqs'] == ['1']


@pytest.mark.parametrize('kind', ['BindingExport', 'WitnessEvidence'])
def test_real_locked_snapshot_wal_rows_are_not_export_completeness(kind, tmp_path):
    args, export = setup(kind)
    db, marker, lock = [tmp_path / n for n in ('store.sqlite', 'INITIALIZED', '.lock')]
    marker.write_bytes(args['snapshot'].marker)
    lock.touch()
    con = sqlite3.connect(db)
    try:
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('PRAGMA wal_autocheckpoint=0')
        con.execute('CREATE TABLE unexported (private TEXT)')
        con.commit()
        con.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        with locked_store(db, marker, lock) as reader:
            args['snapshot'] = reader.snapshot()
            first = check(args, export)
            con.execute("INSERT INTO unexported VALUES ('SYNTHETIC OMITTED ROW')")
            con.commit()
            args['snapshot'] = reader.snapshot()
            second = check(args, export)
            assert first['logicalSha256'] != second['logicalSha256']
            assert first['stdoutSha256'] == second['stdoutSha256']
            assert first['markerSha256'] == second['markerSha256']
    finally:
        con.close()
