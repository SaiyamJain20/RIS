"""D50 store identity of the key worker and its opt-in `--binding` export (HMBC2020 successor, F task 2 slice 5b).

PAPER-DERIVED RECONSTRUCTION of D50 section 5 and SUCCESSOR-WIRE section 5 for the worker store (`<state-dir>/worker/`, `owner = "worker"`, NO key and NO membership check). It gives the existing E
`worker.sqlite` the same identity a witness store has: `meta` rows `binding_v2`, `binding_v2_doc`, `owner`, `schema` (and `anchor`, the pinned block per chain at which the live fields were read), the
`INITIALIZED` marker, the initialisation order with its crash points, the refusal reasons, and a read-only export `python -m hmbc_protocol.worker_log --state-dir D --binding` printing
`{owner, binding_v2, document, anchor}` on one canonical line (EXPORT-LAYOUTS sections 1 and 2).

The carried E `Worker` class, its schema (`worker._SCHEMA`, run here unchanged), its `deployment` fingerprint row and the default `worker_log` export are NOT changed: the only edit to a carried file is the
opt-in `--binding` flag of `worker_log.py`. A caller binds the directory FIRST (`bind_worker_dir`, after the open-time checks of `binding_open`) and constructs the E `Worker` afterwards.

Rules (D50 section 5): an E-created EMPTY store (schema and the v1 `deployment` row, no `records`/`releases`/`events` rows) is bound on first open; a store with such rows and no binding rows is refused
LEGACY_STATE (there is no adopt command); a marker without a database is STORE_MISSING; a failed integrity check, a marker that differs from the identity rows, record rows without the marker, or binding
rows missing next to a marker is STORE_CORRUPT; another binding is BINDING_MISMATCH, another owner OWNER_MISMATCH. A refused open performs no write transaction. Only process death is modelled for crash
points; power loss is untested. Standard library plus my own `witness_state` helpers; no clock, no network, no key.
"""
from __future__ import annotations

import fcntl
import json
import os
import sqlite3

from . import binding as bd
from . import witness_state as ws

OWNER = "worker"
SCHEMA = ws.SCHEMA
RECORD_TABLES = ("records", "releases", "events")
_REQUIRED = ("binding_v2", "binding_v2_doc", "owner", "schema")


def _db_path(directory):
    return os.path.join(directory, "worker.sqlite")


def _classify(directory):
    """Read-only inspection (SUCCESSOR-WIRE section 5). Returns ("fresh", None), ("interrupted", meta) or ("open", meta); raises the stage-9 refusals and writes nothing."""
    db = _db_path(directory)
    _, marker, _tmp = ws._paths(directory)
    has_db, has_marker = os.path.exists(db), os.path.exists(marker)
    if not has_db and not has_marker:
        return "fresh", None
    if has_marker and not has_db:
        raise ws.StoreError("STORE_MISSING", "the INITIALIZED marker exists but the database does not")
    try:
        con = ws._ro(db)
        try:
            if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ws.StoreError("STORE_CORRUPT", "integrity_check failed")
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            meta = dict(con.execute("SELECT key, value FROM meta")) if "meta" in tables else {}
            rows = sum(con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in RECORD_TABLES if t in tables)
        finally:
            con.close()
    except sqlite3.DatabaseError as e:
        raise ws.StoreError("STORE_CORRUPT", f"the database cannot be read: {e}") from None
    if not all(k in meta for k in _REQUIRED):
        if has_marker:
            raise ws.StoreError("STORE_CORRUPT", "the INITIALIZED marker exists but the binding rows are missing")
        if rows:
            raise ws.StoreError("LEGACY_STATE", "a worker store with rows and no binding rows (an unbound E store)")
        return "fresh", None                                       # an E-created empty store: schema and the v1 deployment row, nothing recorded
    if not has_marker:
        if rows:
            raise ws.StoreError("STORE_CORRUPT", "record rows exist but the INITIALIZED marker is missing")
        return "interrupted", meta
    try:
        mk = json.loads(open(marker).read())
    except (OSError, ValueError):
        raise ws.StoreError("STORE_CORRUPT", "the INITIALIZED marker is unreadable") from None
    if mk != {"binding_v2": meta["binding_v2"], "owner": meta["owner"], "schema": meta["schema"]} or meta["schema"] != SCHEMA:
        raise ws.StoreError("STORE_CORRUPT", "the marker differs from the database's identity rows")
    return "open", meta


def bind_worker_dir(directory, binding_v2, document, anchor, *, crash_hook=None):
    """Bind the worker directory to the deployment, or check that it already is. Initialises a fresh (or E-created empty, or interrupted) directory in the order of SUCCESSOR-WIRE section 5 and returns
    nothing; an open directory is only compared. The caller has already verified the deployment (stages 1 to 8) and computed `binding_v2`."""
    hook = crash_hook or (lambda p: None)
    if not isinstance(binding_v2, str) or not ws._SHA.fullmatch(binding_v2) or not isinstance(document, dict):
        raise ValueError("binding_v2 or document is malformed")
    ws._check_anchor(anchor)
    if os.path.isdir(directory):
        state, meta = _classify(directory)
    else:
        state, meta = "fresh", None
    if state == "open":
        ws._identity(meta, binding_v2, OWNER)
        return
    os.makedirs(directory, mode=0o700, exist_ok=True)
    os.chmod(directory, 0o700)
    lock = os.open(os.path.join(directory, ".init.lock"), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        hook("after_dir")
        state, meta = _classify(directory)                         # again, under the lock: another initialiser may have finished
        if state == "open":
            ws._identity(meta, binding_v2, OWNER)
            return
        db = _db_path(directory)
        _, _marker, tmp = ws._paths(directory)
        if state == "interrupted":
            ws._identity(meta, binding_v2, OWNER)
            if os.path.exists(tmp):
                os.remove(tmp)
        else:
            from .worker import _SCHEMA                           # the E schema, unchanged (lazy: the exporter path never imports the worker)
            con = sqlite3.connect(db)
            con.isolation_level = None
            try:
                con.execute("PRAGMA journal_mode=WAL")
                con.execute("PRAGMA synchronous=FULL")
                con.execute("BEGIN")
                for stmt in (s.strip() for s in _SCHEMA.split(";") if s.strip()):
                    con.execute(stmt)
                rows = [("schema", SCHEMA), ("binding_v2", binding_v2), ("binding_v2_doc", ws.canonical_json(document)), ("owner", OWNER), ("anchor", ws.canonical_json(anchor))]
                for k, v in rows:
                    con.execute("INSERT INTO meta (key, value) VALUES (?, ?)", (k, v))
                con.execute("COMMIT")
            finally:
                con.close()
            os.chmod(db, 0o600)
        hook("after_db_commit")
        ws._write_marker(directory, binding_v2, OWNER, hook)
    finally:
        os.close(lock)


def view_for_export(directory):
    """The read-only entry of the exporter: only a missing, corrupt or legacy store is refused; identity is not compared, nothing is written. Returns {owner, binding_v2, document, anchor}."""
    if not os.path.isdir(directory):
        raise ws.StoreError("STORE_MISSING", "no store directory")
    state, meta = _classify(directory)
    if state != "open":
        raise ws.StoreError("STORE_MISSING", "the store was never initialised (no INITIALIZED marker)")
    try:
        document = json.loads(meta["binding_v2_doc"])
        anchor = json.loads(meta["anchor"]) if "anchor" in meta else None
    except ValueError:
        raise ws.StoreError("STORE_CORRUPT", "the binding rows are not JSON") from None
    if anchor is None:
        raise ws.StoreError("STORE_CORRUPT", "the binding rows carry no anchor")
    try:
        if bd.binding_v2(document) != meta["binding_v2"]:
            raise ws.StoreError("STORE_CORRUPT", "the stored document does not hash to the stored binding")
    except ValueError:
        raise ws.StoreError("STORE_CORRUPT", "the stored document is not a valid binding document") from None
    return {"owner": meta["owner"], "binding_v2": meta["binding_v2"], "document": document, "anchor": anchor}


def binding_main(state_dir):
    """`worker_log --state-dir D --binding`: exit 0 with ONE canonical JSON line plus LF and an empty stderr; a refusal is exit 3 with an empty stdout and ONE canonical {code, message, reason} line on
    stderr. Reads `<D>/worker/` only, read-only, no RPC, no key material."""
    import sys
    try:
        try:
            doc = view_for_export(os.path.join(state_dir, "worker"))
        except sqlite3.DatabaseError as e:
            raise ws.StoreError("STORE_CORRUPT", f"the database cannot be read: {e}") from None
    except ws.StoreError as e:
        sys.stderr.write(ws.canonical_json({"code": e.code, "message": e.message, "reason": e.reason}) + "\n")
        return 3
    sys.stdout.write(ws.canonical_json(doc) + "\n")
    return 0
