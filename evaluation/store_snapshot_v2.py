"""Private WAL-aware logical snapshots for independently pinned local stores.

Internal evaluator API, not an exporter or shared wire contract. Caller selects
the reviewed database/marker/lock paths and holds this context over a bounded
action. A cooperative writer must honor the same flock. No authentication,
export completeness, native fact or persistence/power-loss claim follows.
Raw snapshots may contain private data: retain them in private run storage.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import struct


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class Snapshot:
    logical: bytes
    marker: bytes
    main_sha256: str
    wal_sha256: str | None

    @property
    def logical_sha256(self):
        return _sha(self.logical)

    @property
    def marker_sha256(self):
        return _sha(self.marker)


def require_unchanged(before: Snapshot, after: Snapshot):
    """Physical layout may change on checkpoint; logical/marker bytes may not."""
    if before.logical != after.logical:
        raise ValueError('Store logical state changed')
    if before.marker != after.marker:
        raise ValueError('Store marker bytes changed')


def _identity(st):
    return st.st_dev, st.st_ino


def _check_identity(path, fd):
    st = os.lstat(path)
    if not stat.S_ISREG(st.st_mode) or _identity(st) != _identity(os.fstat(fd)):
        raise ValueError('Store file identity changed')


@contextmanager
def _regular(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('Store input is not a regular file')
        _check_identity(path, fd)
        yield fd
        _check_identity(path, fd)
    finally:
        os.close(fd)


def _read(path):
    with _regular(path) as fd:
        return _read_fd(fd)


def _read_fd(fd):
    parts = []
    while chunk := os.read(fd, 1024 * 1024):
        parts.append(chunk)
    return b''.join(parts)


def _quote(name):
    return '"' + name.replace('"', '""') + '"'


def _cell(value):
    if value is None:
        return ['null', None]
    if type(value) is int:
        return ['integer', str(value)]
    if type(value) is float:
        return ['real', struct.pack('>d', value).hex()]
    if type(value) is str:
        return ['text', value]
    if type(value) is bytes:
        return ['blob', value.hex()]
    raise ValueError('Unsupported SQLite cell type')


def _logical(con):
    # Exclude rootpage (a physical layout fact), retain every schema definition.
    schema = con.execute('SELECT type,name,tbl_name,sql FROM sqlite_schema '
                         'ORDER BY type,name,tbl_name').fetchall()
    tables = {}
    for kind, name, _, sql in schema:
        if kind != 'table':
            continue
        table = _quote(name)
        # table_list distinguishes WITHOUT ROWID and virtual/shadow tables even
        # when formatting/comments in CREATE SQL would defeat a text search.
        info = [r for r in con.execute('PRAGMA table_list') if r[0] == 'main' and r[1] == name]
        if len(info) != 1 or info[0][2] != 'table' or info[0][4]:
            raise ValueError('Unsupported virtual or WITHOUT rowid table')
        columns = [r[1] for r in con.execute(f'PRAGMA table_xinfo({table})')]
        rowid = next((n for n in ('rowid', '_rowid_', 'oid') if n not in {c.lower() for c in columns}), None)
        if rowid is None:
            raise ValueError('Hidden rowid is fully shadowed')
        cursor = con.execute(f'SELECT {_quote(rowid)}, * FROM {table} ORDER BY {_quote(rowid)}')
        tables[name] = {'columns': [c[0] for c in cursor.description][1:],
                        'rows': [[r[0], [_cell(v) for v in r[1:]]] for r in cursor]}
    state = {'schema': schema, 'tables': tables,
             'pragmas': {p: con.execute('PRAGMA ' + p).fetchone()[0]
                         for p in ('user_version', 'application_id', 'schema_version', 'encoding')}}
    return json.dumps(state, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


class _Reader:
    def __init__(self, database, marker, lock, lock_fd):
        self.database, self.marker, self.lock, self.lock_fd = database, marker, lock, lock_fd
        self.active = True

    def snapshot(self):
        if not self.active:
            raise ValueError('Store reader is closed')
        try:
            _check_identity(self.lock, self.lock_fd)
            with _regular(self.marker) as marker_fd, _regular(self.database):
                marker = _read_fd(marker_fd)
                # as_uri percent-encodes '?'/'#'/'%' in the actual filename.
                con = sqlite3.connect(self.database.as_uri() + '?mode=ro', uri=True, isolation_level=None)
                try:
                    con.execute('BEGIN')
                    if con.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                        raise ValueError('SQLite integrity check failed')
                    logical = _logical(con)
                    main = _sha(_read(self.database))
                    wal_path = Path(str(self.database) + '-wal')
                    try:
                        wal = _sha(_read(wal_path))
                    except FileNotFoundError:
                        wal = None
                    if marker != _read(self.marker):
                        raise ValueError('Store marker bytes changed during snapshot')
                    _check_identity(self.lock, self.lock_fd)
                finally:
                    con.close()  # Ends the sole read transaction on success or refusal.
            return Snapshot(logical, marker, main, wal)
        except (OSError, sqlite3.Error) as exc:
            raise ValueError('SQLite store snapshot refused: ' + str(exc)) from exc


@contextmanager
def locked_store(database, marker, lock):
    """Hold the existing owner lock across before/action/after snapshots.

    Missing/busy locks refuse immediately; no store or lock file is created.
    Explicit paths prevent assuming the layout of a NOT_READY owner module.
    SQLite may maintain its recreatable WAL shared-memory index on a ro open;
    application tables, WAL contents and INITIALIZED are never written here.
    """
    database, marker, lock = (Path(os.path.abspath(p)) for p in (database, marker, lock))
    if len({database, marker, lock}) != 3:
        raise ValueError('Store paths must be distinct')
    try:
        with _regular(lock) as fd:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValueError('Store lock is busy') from exc
            reader = _Reader(database, marker, lock, fd)
            try:
                yield reader
            finally:
                reader.active = False
                fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError as exc:
        raise ValueError('Store lock/file unavailable: ' + str(exc)) from exc
