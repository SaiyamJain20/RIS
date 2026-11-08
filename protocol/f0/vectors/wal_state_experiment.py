"""WAL and "what is state" for the F0 store rules (agent 2, F0 revision 4; answers A3-0059 R2). Standard library only.

Question: SUCCESSOR-WIRE revision 3 called SQLite's `-wal`/`-shm` side files "not state" and compared main-database and marker hashes on a refused open. Is that right?

PREDICTIONS (written before the first run; SQLite is the system library of the Python used):
  W1  after a commit with another connection still open, the main database file's sha256 is UNCHANGED while the -wal file is non-empty (the row lives only in the WAL).
  W2  a second read-only connection (mode=ro) sees the committed row.
  W3  a copy of the MAIN FILE ONLY (no -wal) opened read-only does NOT see the row (a partial copy is a rollback).
  W4  a copy of main file + -wal taken while no writer is active DOES see the row.
  W5  opening the original with immutable=1 does NOT see the row (it ignores the WAL).
  W6  a main-file-hash oracle reports "no change" although the logical state changed (the oracle's negative control); a logical-snapshot oracle reports the change.
  W7  after every connection is closed the WAL is checkpointed and removed or emptied, the main file bytes CHANGE, and the logical snapshot is IDENTICAL to the one before closing (a checkpoint is not a state change).
  W8  taking the logical snapshot through a mode=ro connection changes neither the main file bytes nor the logical state.

    python3 -B -I wal_state_experiment.py   -> JSON on stdout, exit 0 iff all predictions hold. Works in a temporary directory; writes nothing else.
"""
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile


def sha(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except FileNotFoundError:
        return None


def size(path):
    try:
        return os.path.getsize(path)
    except FileNotFoundError:
        return None


def ro(path, **kw):
    return sqlite3.connect("file:" + path + "?mode=ro" + ("&immutable=1" if kw.get("immutable") else ""), uri=True, isolation_level=None)


def logical_snapshot(path):
    """Deterministic hash of the logical content (schema + every row of every table) read in ONE read transaction through a WAL-aware read-only connection."""
    db = ro(path)
    try:
        db.execute("begin")
        h = hashlib.sha256()
        for name, sql in db.execute("select name, sql from sqlite_master where type='table' order by name").fetchall():
            h.update(repr((name, sql)).encode())
            for row in db.execute(f'select * from "{name}" order by rowid'):
                h.update(repr(row).encode())
        db.execute("commit")
        return h.hexdigest()
    finally:
        db.close()


def rows(path, **kw):
    db = ro(path, **kw)
    try:
        return db.execute("select count(*) from t").fetchone()[0]
    finally:
        db.close()


def main():
    out, ok = {"sqlite": sqlite3.sqlite_version, "python": sys.version.split()[0]}, True
    with tempfile.TemporaryDirectory() as d:
        db_path, marker = os.path.join(d, "store.sqlite"), os.path.join(d, "INITIALIZED")
        open(marker, "wb").write(b'{"binding_v2":"synthetic","owner":"worker","schema":2}')
        a = sqlite3.connect(db_path, isolation_level=None)
        a.execute("pragma journal_mode=wal")
        a.execute("pragma synchronous=full")
        a.execute("create table t(id integer primary key, v text)")
        a.execute("insert into t(v) values('before')")
        # make the baseline a checkpointed main file with a held-open writer connection
        a.execute("pragma wal_checkpoint(TRUNCATE)")
        main_before, marker_before, snap_before = sha(db_path), sha(marker), logical_snapshot(db_path)
        a.execute("insert into t(v) values('committed-only-in-wal')")          # committed (autocommit); connection `a` stays open
        main_after, marker_after, snap_after = sha(db_path), sha(marker), logical_snapshot(db_path)
        wal = db_path + "-wal"
        out["W1"] = {"mainFileUnchanged": main_before == main_after, "walBytes": size(wal), "holds": main_before == main_after and (size(wal) or 0) > 0}
        out["W2"] = {"readOnlySeesRow": rows(db_path) == 2, "holds": rows(db_path) == 2}
        only_main = os.path.join(d, "copy-main-only.sqlite")
        shutil.copyfile(db_path, only_main)
        w3 = rows(only_main) == 1
        out["W3"] = {"mainOnlyCopyRowCount": rows(only_main), "holds": w3}
        full = os.path.join(d, "copy-full.sqlite")
        shutil.copyfile(db_path, full)
        shutil.copyfile(wal, full + "-wal")
        w4 = rows(full) == 2
        out["W4"] = {"mainPlusWalCopyRowCount": rows(full), "holds": w4}
        try:
            n_imm = rows(db_path, immutable=True)
        except sqlite3.Error as e:
            n_imm = f"error: {e}"
        out["W5"] = {"immutableRowCount": n_imm, "holds": n_imm == 1}
        out["W6"] = {"mainFileOracleSawChange": main_before != main_after or marker_before != marker_after, "logicalOracleSawChange": snap_before != snap_after,
                     "holds": (main_before == main_after and marker_before == marker_after) and snap_before != snap_after}
        # W8: reading through mode=ro must not change anything
        m1, s1 = sha(db_path), logical_snapshot(db_path)
        logical_snapshot(db_path)
        out["W8"] = {"mainBytesUnchangedByRead": sha(db_path) == m1, "logicalUnchangedByRead": logical_snapshot(db_path) == s1,
                     "holds": sha(db_path) == m1 and logical_snapshot(db_path) == s1}
        snap_open = logical_snapshot(db_path)
        main_open = sha(db_path)
        a.close()                                                               # last connection: SQLite checkpoints
        snap_closed = logical_snapshot(db_path)
        out["W7"] = {"walBytesAfterClose": size(wal), "mainFileChanged": sha(db_path) != main_open, "logicalIdentical": snap_closed == snap_open,
                     "holds": (size(wal) in (None, 0)) and sha(db_path) != main_open and snap_closed == snap_open}
    ok = all(out[k]["holds"] for k in ("W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8"))
    out["allPredictionsHold"] = ok
    json.dump(out, sys.stdout, indent=1, sort_keys=True)
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
