"""TEST-ONLY helpers for durable-state tests (hook H7: stopped/locked state copy; the WAL-aware logical snapshot oracle of SUCCESSOR-WIRE section 5).

Not imported by any production module and not an adapter operation. The logical snapshot reads the committed state of a witness store the way the evidence says it must:
one read transaction through a WAL-aware read-only connection (`mode=ro`, never `immutable=1`) hashing the schema and every row of every table in rowid order, plus the bytes of the
INITIALIZED marker. A main-file hash is NOT the oracle: a committed transaction can live only in the -wal file.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3


def logical_snapshot(directory: str) -> str:
    """sha256 over (schema, every row of every table in rowid order, marker bytes); `-` marks an absent database or marker."""
    h = hashlib.sha256()
    db = os.path.join(directory, "signing.sqlite")
    if os.path.exists(db):
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            con.isolation_level = None
            con.execute("BEGIN")                                  # one read transaction: a consistent view including committed WAL frames
            for name, sql in con.execute("SELECT name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
                h.update(f"schema:{name}:{sql}\n".encode())
                if sql and sql.startswith("CREATE TABLE"):
                    for row in con.execute(f'SELECT * FROM "{name}" ORDER BY rowid'):
                        h.update(json.dumps(row, separators=(",", ":"), default=str).encode() + b"\n")
            con.execute("COMMIT")
        finally:
            con.close()
    else:
        h.update(b"no-database\n")
    marker = os.path.join(directory, "INITIALIZED")
    h.update(open(marker, "rb").read() if os.path.exists(marker) else b"no-marker")
    return h.hexdigest()


def main_file_sha256(directory: str) -> str:
    """The sha256 of the MAIN database file only: the WRONG oracle, kept to show that it misses a WAL-only commit (negative control)."""
    p = os.path.join(directory, "signing.sqlite")
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else "-"
