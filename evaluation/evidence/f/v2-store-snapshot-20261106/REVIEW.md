# Separate author review

Correlated self-review under the user's no-extra-agents instruction; weaker than
an independent reviewer. Exact source is frozen separately before root tests.

Reviewed the internal API against BOUNDARY read-only exporter requirements:
one mode=ro transaction, no immutable flag, schema/all-table/rowid completeness,
typed values, separate exact marker bytes, supplemental main/WAL hashes,
existing exclusive lock spanning caller actions, closed reader, refusal cleanup.
No peer private imports or source adoption; no existing consumer is switched.

Found a real marker race: two equal-content reads could miss file replacement
between them. New test produced 1FAIL/39PASS. Holding the marker descriptor
through the transaction now checks its original inode on context exit as well
as its final bytes. Fixed with no weakened guards. Earlier 2FAIL/28PASS were
test harness mistakes: a monkeypatch's `uri` positional parameter collided with
the keyword, and the replaced-lock test failed to expect the context-exit refusal.
Both original logs retained. Final focused file 40PASS.

Review controls cover nonregular files, URI punctuation, quoted identifiers,
hidden rowid aliases, generated columns, SQLite sequence tables, zero-row schema
changes, header pragmas, corrupt/missing/symlink paths, and a noncooperative
writer commit demonstrating a consistent read transaction. Six deliberate
in-memory bypasses target WAL visibility, row completeness, logical comparison,
marker bytes, lock exclusivity and physical-only comparison; evidence retained.

Ruling: the exclusive lock only constrains participants honoring that lock.
Physical fingerprints are supplemental and may not describe the read transaction
under a noncooperative writer. No claim of hostile-filesystem protection, export
authentication, persistence or owner compatibility is made. Future use requires
reviewed exact owner READY/path/locking choreography and exporter/native joins.
Unsupported virtual/WITHOUT ROWID/fully-shadowed-rowid tables fail closed; this
is an internal evaluator choice, to revisit with tests if a reviewed READY needs
those features. Raw real snapshots remain private because they can include data
that a public exporter would redact. No deferred correctness finding remains in
this bounded synthetic slice; broader C-F1 remains WORKING.
