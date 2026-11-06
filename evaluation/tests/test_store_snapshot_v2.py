"""Synthetic real-SQLite controls; no owner store/runtime imports."""
import hashlib
import importlib
import json
from pathlib import Path
import sqlite3

import pytest


@pytest.fixture
def api():
    return importlib.import_module('evaluation.store_snapshot_v2')


@pytest.fixture
def store(tmp_path):
    database, marker, lock = (tmp_path / name for name in ('signing.sqlite', 'INITIALIZED', '.lock'))
    marker.write_bytes(b'{"schema":"2"}\n')
    lock.touch()
    con = sqlite3.connect(database)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA wal_autocheckpoint=0')
    con.execute('CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)')
    con.execute('CREATE TABLE refusals (body TEXT)')
    con.execute("INSERT INTO meta VALUES ('owner', 'synthetic-witness')")
    con.commit()
    con.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    yield database, marker, lock, con
    con.close()


def reader(api, store):
    return api.locked_store(*store[:3])


def test_wal_only_refusal_is_not_in_main_hash(api, store):
    db, _, _, con = store
    with reader(api, store) as view:
        before = view.snapshot()
        con.execute("INSERT INTO refusals VALUES ('OBSERVED_FAULT')")
        con.commit()
        after = view.snapshot()
        assert before.main_sha256 == after.main_sha256 == hashlib.sha256(db.read_bytes()).hexdigest()
        assert before.wal_sha256 != after.wal_sha256
        assert before.logical_sha256 != after.logical_sha256
        assert json.loads(after.logical)['tables']['refusals']['rows'] == [[1, [['text', 'OBSERVED_FAULT']]]]
        with pytest.raises(ValueError, match='logical'):
            api.require_unchanged(before, after)


def test_checkpoint_changes_physical_bytes_but_not_logical_state(api, store):
    *_, con = store
    con.execute("INSERT INTO refusals VALUES ('SYNTHETIC')")
    con.commit()
    with reader(api, store) as view:
        before = view.snapshot()
        assert con.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0] == 0
        after = view.snapshot()
        assert before.main_sha256 != after.main_sha256
        assert before.wal_sha256 != after.wal_sha256
        assert before.logical == after.logical
        api.require_unchanged(before, after)


def test_exact_marker_bytes_are_separate_from_logical_state(api, store):
    with reader(api, store) as view:
        before = view.snapshot()
        store[1].write_bytes(b'{ "schema": "2" }\n')
        after = view.snapshot()
        assert before.logical == after.logical
        assert before.marker != after.marker
        assert before.marker_sha256 != after.marker_sha256
        with pytest.raises(ValueError, match='marker'):
            api.require_unchanged(before, after)


@pytest.mark.parametrize('sql', [
    'CREATE TABLE empty (value TEXT)',
    'CREATE INDEX refusal_index ON refusals(body)',
    'CREATE VIEW refusal_view AS SELECT body FROM refusals',
    'CREATE TRIGGER refusal_trigger AFTER INSERT ON refusals BEGIN SELECT 1; END',
    'PRAGMA user_version=9', 'PRAGMA application_id=19',
    "UPDATE meta SET value='changed'", "DELETE FROM meta",
    'DROP TABLE refusals',
])
def test_schema_all_tables_and_header_changes_are_detected(api, store, sql):
    with reader(api, store) as view:
        before = view.snapshot()
        store[3].execute(sql)
        store[3].commit()
        after = view.snapshot()
        with pytest.raises(ValueError, match='logical'):
            api.require_unchanged(before, after)


def test_every_value_type_and_sparse_rowid_order(api, store):
    con = store[3]
    con.execute('CREATE TABLE mixed (value)')
    values = [(8, None), (2, 3), (12, 3.5), (6, '3'), (4, b'3')]
    con.executemany('INSERT INTO mixed(rowid,value) VALUES (?,?)', values)
    con.commit()
    with reader(api, store) as view:
        state = json.loads(view.snapshot().logical)
    table = state['tables']['mixed']
    assert table['columns'] == ['value']
    assert table['rows'] == [
        [2, [['integer', '3']]], [4, [['blob', '33']]],
        [6, [['text', '3']]], [8, [['null', None]]],
        [12, [['real', '400c000000000000']]],
    ]
    assert set(state['tables']) == {'meta', 'refusals', 'mixed'}


def test_sqlite_sequence_rows_are_included(api, store):
    con = store[3]
    con.execute('CREATE TABLE numbered (id INTEGER PRIMARY KEY AUTOINCREMENT)')
    con.execute('INSERT INTO numbered DEFAULT VALUES')
    con.commit()
    with reader(api, store) as view:
        assert 'sqlite_sequence' in json.loads(view.snapshot().logical)['tables']


def test_quoted_identifiers_and_shadowed_rowid(api, store):
    con = store[3]
    con.execute('CREATE TABLE "odd\""name" (rowid TEXT, _rowid_ TEXT, value TEXT)')
    con.execute('INSERT INTO "odd\""name" VALUES (?,?,?)', ('not-a-rowid', 'nor-this', 'data'))
    con.commit()
    with reader(api, store) as view:
        row = json.loads(view.snapshot().logical)['tables']['odd"name']['rows'][0]
        assert row[0] == 1 and row[1][0] == ['text', 'not-a-rowid']


@pytest.mark.parametrize('sql', [
    'CREATE TABLE unsupported (key TEXT PRIMARY KEY) WITHOUT ROWID',
    'CREATE VIRTUAL TABLE unsupported USING fts5(value)',
    'CREATE TABLE unsupported (rowid TEXT, _rowid_ TEXT, oid TEXT)',
])
def test_unsupported_tables_fail_closed(api, store, sql):
    store[3].execute(sql)
    store[3].commit()
    with reader(api, store) as view:
        with pytest.raises(ValueError, match='rowid|virtual'):
            view.snapshot()


def test_lock_is_exclusive_and_released_after_exception(api, store):
    with pytest.raises(RuntimeError, match='synthetic'):
        with reader(api, store):
            with pytest.raises(ValueError, match='lock'):
                with reader(api, store):
                    pytest.fail('second lock acquired')
            raise RuntimeError('synthetic')
    with reader(api, store) as view:
        assert view.snapshot().logical
    with pytest.raises(ValueError, match='closed'):
        view.snapshot()


@pytest.mark.parametrize('index', [0, 1, 2])
def test_missing_inputs_refused_without_creating_files(api, store, index):
    store[index].unlink()
    with pytest.raises(ValueError):
        with reader(api, store) as view:
            view.snapshot()
    assert not store[index].exists()


@pytest.mark.parametrize('index', [0, 1, 2])
def test_symlink_inputs_refused(api, store, index):
    target = store[index].with_name('moved')
    store[index].rename(target)
    store[index].symlink_to(target)
    with pytest.raises(ValueError):
        with reader(api, store) as view:
            view.snapshot()


def test_replaced_lock_path_refused(api, store):
    with pytest.raises(ValueError, match='identity'):
        with reader(api, store) as view:
            store[2].rename(store[2].with_name('old-lock'))
            store[2].touch()
            view.snapshot()


def test_corrupt_database_refused_and_lock_released(api, store):
    store[3].close()
    store[0].write_bytes(b'not sqlite')
    with reader(api, store) as view:
        with pytest.raises(ValueError, match='SQLite'):
            view.snapshot()
    with reader(api, store):
        pass


def test_reader_uses_one_read_only_transaction_never_immutable(api, store, monkeypatch):
    real = sqlite3.connect
    traces, uris = [], []

    def connect(database, **kwargs):
        uris.append((database, kwargs))
        con = real(database, **kwargs)
        con.set_trace_callback(traces.append)
        return con

    monkeypatch.setattr(api.sqlite3, 'connect', connect)
    with reader(api, store) as view:
        before = view.snapshot()
        after = view.snapshot()
        api.require_unchanged(before, after)
        assert before.main_sha256 == after.main_sha256
        assert before.wal_sha256 == after.wal_sha256
    assert len(uris) == 2
    assert all(uri.endswith('?mode=ro') and 'immutable' not in uri and kw['uri'] for uri, kw in uris)
    assert sum(s.upper() == 'BEGIN' for s in traces) == 2
    assert not any(s.upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'REPLACE')) for s in traces)


def test_snapshot_does_not_create_missing_database(api, tmp_path):
    marker, lock = tmp_path / 'INITIALIZED', tmp_path / '.lock'
    marker.write_bytes(b'{}')
    lock.touch()
    with api.locked_store(tmp_path / 'missing.sqlite', marker, lock) as view:
        with pytest.raises(ValueError):
            view.snapshot()
    assert not (tmp_path / 'missing.sqlite').exists()


def test_uri_special_characters(api, tmp_path):
    folder = tmp_path / 'question?#percent%'
    folder.mkdir()
    db, marker, lock = [folder / n for n in ('db?#%.sqlite', 'INITIALIZED', '.lock')]
    marker.write_bytes(b'{}')
    lock.touch()
    con = sqlite3.connect(db)
    con.execute('CREATE TABLE values_table(value)')
    con.commit()
    con.close()
    with api.locked_store(db, marker, lock) as view:
        assert set(json.loads(view.snapshot().logical)['tables']) == {'values_table'}


@pytest.mark.parametrize('index', [0, 1, 2])
@pytest.mark.parametrize('kind', ['directory', 'fifo'])
def test_nonregular_inputs_refused(api, store, index, kind):
    import os
    store[index].unlink()
    if kind == 'directory':
        store[index].mkdir()
    else:
        os.mkfifo(store[index])
    with pytest.raises(ValueError):
        with reader(api, store) as view:
            view.snapshot()


def test_marker_replacement_with_identical_bytes_during_read_refused(api, store, monkeypatch):
    original = api._logical

    def replace_marker(con):
        result = original(con)
        marker = store[1]
        marker.rename(marker.with_name('old-marker'))
        marker.write_bytes(b'{"schema":"2"}\n')
        return result

    monkeypatch.setattr(api, '_logical', replace_marker)
    with reader(api, store) as view:
        with pytest.raises(ValueError, match='identity'):
            view.snapshot()


def test_single_transaction_pins_all_tables_even_with_noncooperative_writer(api, store, monkeypatch):
    original = api._logical

    def intervening_commit(con):
        store[3].execute("UPDATE meta SET value='outside-lock'")
        store[3].execute("INSERT INTO refusals VALUES ('outside-lock')")
        store[3].commit()
        return original(con)

    with reader(api, store) as view:
        before = view.snapshot()
        monkeypatch.setattr(api, '_logical', intervening_commit)
        during = view.snapshot()
        assert before.logical == during.logical
        monkeypatch.setattr(api, '_logical', original)
        after = view.snapshot()
        assert before.logical != after.logical


def test_generated_column_is_captured(api, store):
    con = store[3]
    con.execute('CREATE TABLE generated (value INTEGER, doubled INTEGER GENERATED ALWAYS AS (value*2))')
    con.execute('INSERT INTO generated(value) VALUES (4)')
    con.commit()
    with reader(api, store) as view:
        table = json.loads(view.snapshot().logical)['tables']['generated']
        assert table['columns'] == ['value', 'doubled']
        assert table['rows'] == [[1, [['integer', '4'], ['integer', '8']]]]


def test_same_paths_are_refused(api, store):
    with pytest.raises(ValueError, match='distinct'):
        with api.locked_store(store[0], store[0], store[2]):
            pytest.fail('alias accepted')
