"""Durable witness signing store (agent 2, F task 2): a paper-derived reconstruction of the persistent honest single-signing rule. SYMBOLIC; synthetic fixtures; NOT a measured system.

Design inputs (frozen, F0 acceptance A3-0073): SIGNING-RULES sections 1, 2 and 6, SUCCESSOR-WIRE sections 1, 4 and 5, D50 revision 5 and EXPORT-LAYOUTS revision 9 (protocol/f0).
One SQLite database per witness (`<dir>/signing.sqlite`, WAL, synchronous=FULL) plus the `INITIALIZED` marker form the committed state; `-shm` is a recreatable index, not state.

What the store does, and what it deliberately does not:
  * it records the choice for each conflict key K = (type, domain separator, witnessSetVersion, key field) BEFORE any signature leaves the process (the signature is computed inside the
    transaction but returned only after COMMIT; a crash before the commit signs nothing, a crash after it leaves a record that makes the retry idempotent);
  * a different effect for a live key is refused CONFLICT_PINNED (STALE_STATE) with the recorded value, unless every digest under the key is dead by an OBSERVED target-ledger fact
    (the observed block timestamp at or after every expiry, or a numeric overtaken fact the caller supplies and the store re-checks); the host clock is never read;
  * a regression of the observed chain (number, timestamp, or a changed hash at the same number) sets a persisted fault; every later signing refuses WITNESS_FAULTED until an explicit
    clear, which appends to `fault_log` and never rewrites signing history;
  * it validates NOTHING about the proposal itself (that is the caller's independent validation, SIGNING-RULES section 3) and it verifies no signature (the signer is injected).
Process death is the only crash mode exercised by the tests; power loss and OS crash are untested and no durability claim is made for them.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import sqlite3
import threading
from contextlib import contextmanager

SCHEMA = "2"
REASON_CODE = {"STORE_MISSING": "ADAPTER_UNAVAILABLE", "STORE_CORRUPT": "ADAPTER_UNAVAILABLE", "LEGACY_STATE": "WRONG_DESTINATION", "BINDING_MISMATCH": "WRONG_DESTINATION",
               "OWNER_MISMATCH": "WRONG_DESTINATION", "WITNESS_FAULTED": "ADAPTER_UNAVAILABLE", "CONFLICT_PINNED": "STALE_STATE"}
TYPES = ("AccessDecision", "StateCheckpoint", "GrantReceipt", "GovernanceAction")
_RANK = {t: i for i, t in enumerate(TYPES)}
TARGET = {"AccessDecision": "dbc", "StateCheckpoint": "dbc", "GrantReceipt": "pbc", "GovernanceAction": "pbc"}
HAS_EXPIRY = {"AccessDecision": True, "StateCheckpoint": True, "GrantReceipt": False, "GovernanceAction": True}
EFFECT_FIELDS = {   # V = every signed field except the key field and the liveness field (SIGNING-RULES section 1)
    "StateCheckpoint": {"authEpoch", "policyVersion", "keyEpoch", "witnessSetVersion", "sourceChainId", "psc", "sourceBlockNumber", "sourceBlockHash"},
    "AccessDecision": {"result", "credentialDigest", "stateSequence", "witnessSetVersion", "sourceBlockNumber", "sourceBlockHash"},
    "GrantReceipt": {"grantId", "gid", "dataId", "keyEpoch", "grantExpiresAt", "witnessSetVersion", "dbcChainId", "kssc", "dbcBlockNumber", "dbcBlockHash"},
    "GovernanceAction": {"action", "root", "admins", "witnessSetVersion"},
}
DEATH_TYPES = {"expiry": {"AccessDecision", "StateCheckpoint", "GovernanceAction"}, "overtaken-checkpoint": {"StateCheckpoint"}, "overtaken-governance": {"GovernanceAction"},
               "overtaken-decision-sequence": {"AccessDecision"}, "overtaken-decision-grant": {"AccessDecision"}, "executed-receipt": {"GrantReceipt"}}
NUMERIC_DEATH = {"overtaken-checkpoint", "overtaken-governance", "overtaken-decision-sequence"}
_DEC = re.compile(r"(0|[1-9][0-9]*)")
_H32 = re.compile(r"0x[0-9a-f]{64}")
_SHA = re.compile(r"[0-9a-f]{64}")
_SIG = re.compile(r"0x[0-9a-f]{130}")
_OWNER = re.compile(r"witness:0x[0-9a-f]{40}")
_KEY_DEC = {"StateCheckpoint", "GovernanceAction"}

_SCHEMA_SQL = (
    "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    "CREATE TABLE conflict (type TEXT NOT NULL, domain TEXT NOT NULL, wsv TEXT NOT NULL, key TEXT NOT NULL, effect TEXT NOT NULL, vhash TEXT NOT NULL, PRIMARY KEY (type, domain, wsv, key))",
    "CREATE TABLE digests (digest TEXT PRIMARY KEY, type TEXT NOT NULL, domain TEXT NOT NULL, wsv TEXT NOT NULL, key TEXT NOT NULL, expires_at TEXT, signature TEXT NOT NULL, "
    "observation TEXT NOT NULL, sup_seq INTEGER)",
    "CREATE TABLE superseded (seq INTEGER PRIMARY KEY, type TEXT NOT NULL, domain TEXT NOT NULL, wsv TEXT NOT NULL, key TEXT NOT NULL, effect TEXT NOT NULL, vhash TEXT NOT NULL, death TEXT NOT NULL)",
    "CREATE TABLE observed (chain TEXT PRIMARY KEY, observation TEXT NOT NULL)",
    "CREATE TABLE fault (id INTEGER PRIMARY KEY CHECK (id = 1), body TEXT NOT NULL)",
    "CREATE TABLE fault_log (seq INTEGER PRIMARY KEY, fault TEXT NOT NULL, cleared_against TEXT NOT NULL, note TEXT NOT NULL)",
)
_RECORD_TABLES = ("conflict", "digests", "superseded", "observed", "fault", "fault_log")


class StoreError(Exception):
    """A refusal with its SUCCESSOR-WIRE section 1 reason and the closed v1 code that reason maps to; `recorded` is set only for a CONFLICT_PINNED refusal of a StateCheckpoint."""

    def __init__(self, reason: str, message: str, recorded: dict | None = None):
        super().__init__(f"{reason}: {message}")
        self.reason, self.code, self.message, self.recorded = reason, REASON_CODE[reason], message, recorded


def canonical_json(x) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _fsync_dir(path: str) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _ro(db: str) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.isolation_level = None
    return con


def _paths(directory: str):
    return os.path.join(directory, "signing.sqlite"), os.path.join(directory, "INITIALIZED"), os.path.join(directory, "INITIALIZED.tmp")


def _classify(directory: str):
    """Read-only inspection of an existing directory. Returns ("fresh", None), ("interrupted", meta) or ("open", meta); raises the stage-9 refusals (SUCCESSOR-WIRE section 1) and writes nothing."""
    db, marker, _tmp = _paths(directory)
    has_db, has_marker = os.path.exists(db), os.path.exists(marker)
    if not has_db and not has_marker:
        return "fresh", None
    if has_marker and not has_db:
        raise StoreError("STORE_MISSING", "the INITIALIZED marker exists but the database does not")
    try:
        con = _ro(db)
        try:
            if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise StoreError("STORE_CORRUPT", "integrity_check failed")
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            meta = dict(con.execute("SELECT key, value FROM meta")) if "meta" in tables else {}
            if not all(k in meta for k in ("binding_v2", "binding_v2_doc", "owner", "schema")):
                if has_marker:
                    raise StoreError("STORE_CORRUPT", "the INITIALIZED marker exists but the binding rows are missing")
                if any(con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables):
                    raise StoreError("LEGACY_STATE", "a database with rows and no binding rows (an unbound legacy store)")
                return "fresh", None                                   # an empty database without binding rows: nothing was ever recorded
            rows = sum(con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in _RECORD_TABLES if t in tables)
        finally:
            con.close()
    except sqlite3.DatabaseError as e:
        raise StoreError("STORE_CORRUPT", f"the database cannot be read: {e}") from None
    if not has_marker:
        if rows:
            raise StoreError("STORE_CORRUPT", "record rows exist but the INITIALIZED marker is missing")
        return "interrupted", meta
    try:
        mk = json.loads(open(marker).read())
    except (OSError, ValueError):
        raise StoreError("STORE_CORRUPT", "the INITIALIZED marker is unreadable") from None
    if mk != {"binding_v2": meta["binding_v2"], "owner": meta["owner"], "schema": meta["schema"]} or meta["schema"] != SCHEMA:
        raise StoreError("STORE_CORRUPT", "the marker differs from the database's identity rows")
    return "open", meta


def _check_anchor(a) -> None:
    ok = isinstance(a, dict) and set(a) == {"pbc", "dbc"}
    for side in ("pbc", "dbc") if ok else ():
        r = a[side]
        ok = ok and isinstance(r, dict) and set(r) == {"number", "hash"} and isinstance(r["number"], str) and bool(_DEC.fullmatch(r["number"])) and isinstance(r["hash"], str) and bool(_H32.fullmatch(r["hash"]))
    if not ok:
        raise ValueError("anchor must be {pbc: {number, hash}, dbc: {number, hash}} with a decimal number and a 0x block hash")


def view_for_export(directory: str) -> "StoreView":
    """The read-only entry of the exporters: only a missing, corrupt or legacy store is refused (SUCCESSOR-WIRE section 1); identity is not compared, nothing is written."""
    if not os.path.isdir(directory):
        raise StoreError("STORE_MISSING", "no store directory")
    state, meta = _classify(directory)
    if state != "open":
        raise StoreError("STORE_MISSING", "the store was never initialised (no INITIALIZED marker)")
    return StoreView(directory, meta)


def _identity(meta: dict, binding_v2: str, owner: str) -> None:
    if meta["binding_v2"] != binding_v2:
        raise StoreError("BINDING_MISMATCH", "the store is bound to another deployment")
    if meta["owner"] != owner:
        raise StoreError("OWNER_MISMATCH", "the store belongs to another role or key")


def _write_marker(directory: str, binding_v2: str, owner: str, hook) -> None:
    db, marker, tmp = _paths(directory)
    with open(tmp, "w") as f:
        f.write(canonical_json({"binding_v2": binding_v2, "owner": owner, "schema": SCHEMA}))
        f.flush()
        os.fsync(f.fileno())
    hook("after_tmp_marker")
    os.rename(tmp, marker)
    _fsync_dir(directory)
    hook("after_rename")


def init_store(directory: str, binding_v2: str, document: dict, owner: str, *, anchor: dict | None = None, crash_hook=None) -> "WitnessStore":
    """Initialise a fresh (or an interrupted) store, or OPEN an existing one whose identity matches; never initialise over a store (SUCCESSOR-WIRE section 5). The caller has already
    verified the deployment and computed `binding_v2` (D50); signing is allowed only after the marker exists and the directory was fsynced."""
    hook = crash_hook or (lambda p: None)
    if not isinstance(binding_v2, str) or not _SHA.fullmatch(binding_v2) or not isinstance(owner, str) or not _OWNER.fullmatch(owner) or not isinstance(document, dict):
        raise ValueError("binding_v2, owner or document is malformed")
    if anchor is not None:
        _check_anchor(anchor)
    if os.path.isdir(directory):
        state, meta = _classify(directory)
    else:
        state, meta = "fresh", None
    if state == "open":
        _identity(meta, binding_v2, owner)
        return open_store(directory, binding_v2, owner, crash_hook=crash_hook)
    os.makedirs(directory, mode=0o700, exist_ok=True)
    os.chmod(directory, 0o700)
    lock = os.open(os.path.join(directory, ".init.lock"), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        hook("after_dir")
        db, marker, tmp = _paths(directory)
        if state == "interrupted":
            _identity(meta, binding_v2, owner)
            if os.path.exists(tmp):
                os.remove(tmp)
        else:
            con = sqlite3.connect(db)
            con.isolation_level = None
            try:
                con.execute("PRAGMA journal_mode=WAL")
                con.execute("PRAGMA synchronous=FULL")
                con.execute("BEGIN")
                for sql in _SCHEMA_SQL:
                    con.execute(sql)
                rows = [("schema", SCHEMA), ("binding_v2", binding_v2), ("binding_v2_doc", canonical_json(document)), ("owner", owner)]
                if anchor is not None:
                    rows.append(("anchor", canonical_json(anchor)))          # the pinned block per chain at which the live fields were read (EXPORT-LAYOUTS section 2)
                for k, v in rows:
                    con.execute("INSERT INTO meta (key, value) VALUES (?, ?)", (k, v))
                con.execute("COMMIT")
            finally:
                con.close()
            os.chmod(db, 0o600)
        hook("after_db_commit")
        _write_marker(directory, binding_v2, owner, hook)
    finally:
        os.close(lock)
    return open_store(directory, binding_v2, owner, crash_hook=crash_hook)


def open_store(directory: str, binding_v2: str, owner: str, *, signing: bool = True, crash_hook=None) -> "WitnessStore":
    """Open an initialised store. Refusals, in the order of SUCCESSOR-WIRE section 1 stage 9: STORE_MISSING, STORE_CORRUPT, LEGACY_STATE, BINDING_MISMATCH, OWNER_MISMATCH, then
    WITNESS_FAULTED (only when `signing`: a faulted store still opens for read-only evidence)."""
    if not os.path.isdir(directory):
        raise StoreError("STORE_MISSING", "no store directory")
    state, meta = _classify(directory)
    if state != "open":
        raise StoreError("STORE_MISSING", "the store was never initialised (no INITIALIZED marker)")
    _identity(meta, binding_v2, owner)
    st = WitnessStore(directory, meta, crash_hook)
    if signing and st._faulted():
        st.close()
        raise StoreError("WITNESS_FAULTED", "the store carries an uncleared fault")
    return st


class StoreView:
    """A READ-ONLY view of an initialised store: no write connection, no identity check, no lock. The exporters use it (they make no RPC, so they have nothing to compare the identity with):
    every read goes through one WAL-aware `mode=ro` transaction. `WitnessStore` extends it with the signing connection."""

    def __init__(self, directory: str, meta: dict):
        self.directory, self.owner, self.binding_v2 = directory, meta["owner"], meta["binding_v2"]
        self.document = json.loads(meta["binding_v2_doc"])
        self.anchor = json.loads(meta["anchor"]) if "anchor" in meta else None

    def evidence(self) -> dict:
        """The `witness_state --evidence` document (EXPORT-LAYOUTS section 3), read in ONE read transaction through a WAL-aware read-only connection."""
        con = _ro(_paths(self.directory)[0])
        try:
            con.execute("BEGIN")
            obs = sorted((json.loads(r[0]) for r in con.execute("SELECT observation FROM observed")), key=lambda o: int(o["chainId"]))
            fr = con.execute("SELECT body FROM fault WHERE id = 1").fetchone()
            log = [{"seq": str(s), "fault": json.loads(f), "clearedAgainst": json.loads(c), "note": n} for s, f, c, n in con.execute("SELECT seq, fault, cleared_against, note FROM fault_log ORDER BY seq")]

            def digests(k, live):
                out = []
                for dg, e, sg, ob in con.execute("SELECT digest, expires_at, signature, observation FROM digests WHERE type=? AND domain=? AND wsv=? AND key=? AND "
                                                 + ("sup_seq IS NULL" if live is None else "sup_seq = ?"), (*k,) if live is None else (*k, live)):
                    d = {"digest": dg, "signature": sg, "observation": json.loads(ob)}
                    if e is not None:
                        d["expiresAt"] = e
                    out.append(d)
                return sorted(out, key=lambda d: (int(d["expiresAt"]) if "expiresAt" in d else -1, d["digest"]))

            def record(k, effect, vhash, live):
                return {"type": k[0], "domainSeparator": k[1], "witnessSetVersion": k[2], "keyField": k[3], "effect": json.loads(effect), "vHash": vhash, "digests": digests(k, live)}

            conflicts = [record((t, d, w, ky), e, vh, None) for t, d, w, ky, e, vh in con.execute("SELECT type, domain, wsv, key, effect, vhash FROM conflict")]
            conflicts.sort(key=lambda r: (_RANK[r["type"]], r["domainSeparator"], int(r["witnessSetVersion"]), int(r["keyField"]) if _DEC.fullmatch(r["keyField"]) else 0, r["keyField"]))
            sup = []
            for s, t, d, w, ky, e, vh, death in con.execute("SELECT seq, type, domain, wsv, key, effect, vhash, death FROM superseded ORDER BY seq"):
                r = record((t, d, w, ky), e, vh, s)
                r["seq"], r["death"] = str(s), json.loads(death)
                sup.append(r)
            con.execute("COMMIT")
        finally:
            con.close()
        doc = {"schemaVersion": "hmbc-witness-evidence/v2", "owner": self.owner, "binding": {"binding_v2": self.binding_v2, "document": self.document},
               "marker": json.loads(open(_paths(self.directory)[1]).read()), "observations": obs, "faulted": json.loads(fr[0]) if fr else None, "faultLog": log,
               "conflicts": conflicts, "superseded": sup}
        doc["evidenceSha256"] = hashlib.sha256(canonical_json(doc).encode("ascii")).hexdigest()
        return doc

    def binding_export(self, anchor: dict) -> dict:
        """The `--binding` export (EXPORT-LAYOUTS section 2): {owner, binding_v2, document, anchor}, nothing else."""
        return {"owner": self.owner, "binding_v2": self.binding_v2, "document": self.document, "anchor": anchor}


class WitnessStore(StoreView):
    def __init__(self, directory: str, meta: dict, crash_hook=None):
        super().__init__(directory, meta)
        self._chains = {side: self.document["chains"][side]["chainId"] for side in ("pbc", "dbc")}
        self._hook = crash_hook or (lambda p: None)
        db = _paths(directory)[0]
        self._con = sqlite3.connect(db, check_same_thread=False, isolation_level=None)
        self._con.execute("PRAGMA journal_mode=WAL")
        self._con.execute("PRAGMA synchronous=FULL")
        self._con.execute("PRAGMA busy_timeout=30000")
        self._mutex = threading.Lock()
        self._lockfd = os.open(os.path.join(directory, ".lock"), os.O_CREAT | os.O_RDWR, 0o600)

    def close(self) -> None:
        try:
            self._con.close()
        finally:
            if self._lockfd is not None:
                os.close(self._lockfd)
                self._lockfd = None

    @contextmanager
    def exclusive(self):
        """TEST-ONLY support for a stopped/locked state copy (hook H7): no signing runs while this is held."""
        with self._mutex:
            fcntl.flock(self._lockfd, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(self._lockfd, fcntl.LOCK_SH)

    def _faulted(self) -> bool:
        return self._con.execute("SELECT COUNT(*) FROM fault").fetchone()[0] > 0

    # ---------------------------------------------------------------- signing --------------------------------------------------------------------
    def sign(self, *, type: str, domain: str, wsv: str, key: str, effect: dict, expires_at, digest: str, signer, observe, overtaken=None) -> str:
        """Record the choice for K and return the signature, or refuse. `observe()` returns the target ledger's latest-block observation taken for this request; `signer(digest)` returns the
        65-byte hex signature (deterministic, RFC 6979 in production); `overtaken` is ("kind", observed-or-None) evidence of a numeric/ledger death that the store re-checks."""
        if type not in TYPES or not _H32.fullmatch(str(domain)) or not _DEC.fullmatch(str(wsv)) or not _H32.fullmatch(str(digest)):
            raise ValueError("type, domain, witnessSetVersion or digest is malformed")
        if not (isinstance(key, str) and (_DEC.fullmatch(key) if type in _KEY_DEC else _H32.fullmatch(key))):
            raise ValueError("key field is malformed for this type")
        if not isinstance(effect, dict) or set(effect) != EFFECT_FIELDS[type]:
            raise ValueError("effect must carry exactly the fields of V for this type")
        if HAS_EXPIRY[type] != (expires_at is not None) or (expires_at is not None and not _DEC.fullmatch(str(expires_at))):
            raise ValueError("expiresAt is required for types with a liveness field and absent for GrantReceipt")
        with self._mutex:
            fcntl.flock(self._lockfd, fcntl.LOCK_SH)
            self._con.execute("BEGIN IMMEDIATE")
            pending = None
            try:
                try:
                    out = self._sign_in_txn(type, domain, wsv, key, effect, expires_at, digest, signer, observe, overtaken)
                except _FaultSet as fs:
                    pending, out = fs.error, None
                if out is None and pending is None:          # a pure read (idempotent re-sign): nothing to commit
                    self._con.execute("ROLLBACK")
                    return self._stored
                self._hook("before_commit")
                self._con.execute("COMMIT")
            except BaseException:
                if self._con.in_transaction:
                    self._con.execute("ROLLBACK")
                raise
            self._hook("after_commit")
            if pending is not None:
                raise pending
            return out

    _stored = None

    def _sign_in_txn(self, type, domain, wsv, key, effect, expires_at, digest, signer, observe, overtaken):
        con = self._con
        if con.execute("SELECT COUNT(*) FROM fault").fetchone()[0]:
            raise StoreError("WITNESS_FAULTED", "the store carries an uncleared fault")
        obs = observe()
        self._check_obs(obs)
        if obs["chainId"] != self._chains[TARGET[type]]:
            raise ValueError("the observation is not of the target ledger of this type")
        row = con.execute("SELECT observation FROM observed WHERE chain = ?", (obs["chainId"],)).fetchone()
        if row:
            last = json.loads(row[0])
            reason = ("number-regression" if int(obs["blockNumber"]) < int(last["blockNumber"]) else "timestamp-regression" if int(obs["timestamp"]) < int(last["timestamp"])
                      else "hash-changed" if obs["blockNumber"] == last["blockNumber"] and obs["blockHash"] != last["blockHash"] else None)
            if reason:
                con.execute("INSERT INTO fault (id, body) VALUES (1, ?)", (canonical_json({"reason": reason, "previous": last, "observed": obs}),))
                raise _FaultSet(StoreError("WITNESS_FAULTED", f"the observed chain regressed ({reason}); the store is faulted until an explicit clear"))
        k = (type, domain, wsv, key)
        vhash = hashlib.sha256(canonical_json(effect).encode("ascii")).hexdigest()
        rec = con.execute("SELECT effect, vhash FROM conflict WHERE type=? AND domain=? AND wsv=? AND key=?", k).fetchone()
        stored = con.execute("SELECT signature FROM digests WHERE digest = ?", (digest,)).fetchone()
        if stored is not None:
            if rec is None or rec[1] != vhash:
                raise StoreError("CONFLICT_PINNED", "this digest is already recorded under another effect or key")
            self._stored = stored[0]
            return None                                      # idempotent: the STORED signature, the signer is not asked
        if rec is not None and rec[1] != vhash:
            live = con.execute("SELECT digest, expires_at, signature FROM digests WHERE type=? AND domain=? AND wsv=? AND key=? AND sup_seq IS NULL", k).fetchall()
            death = self._death(type, key, json.loads(rec[0]), live, obs, overtaken)
            if death is None:
                recorded = None
                if type == "StateCheckpoint":
                    latest = max(live, key=lambda r: (int(r[1]), r[0]))
                    recorded = {"message": {"sequence": key, **json.loads(rec[0]), "expiresAt": latest[1]}, "signature": latest[2]}
                raise StoreError("CONFLICT_PINNED", "an earlier digest recorded under this key is not observed dead", recorded)
            seq = con.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM superseded").fetchone()[0]
            con.execute("INSERT INTO superseded (seq, type, domain, wsv, key, effect, vhash, death) VALUES (?,?,?,?,?,?,?,?)", (seq, *k, rec[0], rec[1], canonical_json(death)))
            con.execute("UPDATE digests SET sup_seq = ? WHERE type=? AND domain=? AND wsv=? AND key=? AND sup_seq IS NULL", (seq, *k))
            con.execute("DELETE FROM conflict WHERE type=? AND domain=? AND wsv=? AND key=?", k)
            rec = None
        if rec is None:
            con.execute("INSERT INTO conflict (type, domain, wsv, key, effect, vhash) VALUES (?,?,?,?,?,?)", (*k, canonical_json(effect), vhash))
        sig = signer(digest)
        if not isinstance(sig, str) or not _SIG.fullmatch(sig):
            raise ValueError("the signer returned a malformed signature")
        con.execute("INSERT INTO digests (digest, type, domain, wsv, key, expires_at, signature, observation, sup_seq) VALUES (?,?,?,?,?,?,?,?,NULL)",
                    (digest, *k, None if expires_at is None else str(expires_at), sig, canonical_json(obs)))
        con.execute("INSERT OR REPLACE INTO observed (chain, observation) VALUES (?, ?)", (obs["chainId"], canonical_json(obs)))
        return sig

    @staticmethod
    def _check_obs(o) -> None:
        if not (isinstance(o, dict) and set(o) == {"chainId", "blockNumber", "blockHash", "timestamp"} and all(_DEC.fullmatch(str(o[x])) for x in ("chainId", "blockNumber", "timestamp"))
                and _H32.fullmatch(str(o["blockHash"]))):
            raise ValueError("the observation must be {chainId, blockNumber, blockHash, timestamp} with decimal strings and a 0x block hash")

    @staticmethod
    def _death(type, key, old_effect, live, obs, overtaken):
        """The death evidence for the live generation of K, or None. Only OBSERVED facts count: the observed block timestamp against the expiries, or a numeric fact the caller supplies that
        this function re-checks against the key or the old effect. A grant or an executed receipt is a ledger fact the layout cannot show; the caller asserts it, the type is checked."""
        if HAS_EXPIRY[type] and live and all(r[1] is not None for r in live) and int(obs["timestamp"]) >= max(int(r[1]) for r in live):
            return {"kind": "expiry", "observation": obs}
        if overtaken is None:
            return None
        kind, observed = overtaken
        if kind not in DEATH_TYPES or type not in DEATH_TYPES[kind] or kind == "expiry":
            return None
        if kind in NUMERIC_DEATH:
            if not (isinstance(observed, str) and _DEC.fullmatch(observed)):
                return None
            ok = (int(observed) > int(old_effect["stateSequence"]) if kind == "overtaken-decision-sequence" else int(observed) >= int(key))
            return {"kind": kind, "observation": obs, "observed": observed} if ok else None
        if observed is not None:
            return None
        if kind == "overtaken-decision-grant" and old_effect.get("result") != "1":
            return None                                                  # a DENY is never dead by grant (A1-0107)
        return {"kind": kind, "observation": obs}

    # ---------------------------------------------------------------- tripwire clear -----------------------------------------------------------
    def clear_fault(self, note: str, observe) -> None:
        """An explicit operator clear: appends one `fault_log` row and adopts the chain's current latest observation as the new baseline. It never deletes or rewrites signing history."""
        if not isinstance(note, str) or not note.strip():
            raise ValueError("a clear needs a non-empty note")
        with self._mutex:
            fcntl.flock(self._lockfd, fcntl.LOCK_SH)
            self._con.execute("BEGIN IMMEDIATE")
            try:
                row = self._con.execute("SELECT body FROM fault WHERE id = 1").fetchone()
                if row is None:
                    raise ValueError("the store is not faulted: nothing to clear")
                fault = json.loads(row[0])
                obs = observe()
                self._check_obs(obs)
                if obs["chainId"] != fault["observed"]["chainId"]:
                    raise ValueError("the clearing observation must be of the faulted chain")
                seq = self._con.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM fault_log").fetchone()[0]
                self._con.execute("INSERT INTO fault_log (seq, fault, cleared_against, note) VALUES (?,?,?,?)", (seq, canonical_json(fault), canonical_json(obs), note))
                self._con.execute("DELETE FROM fault WHERE id = 1")
                self._con.execute("INSERT OR REPLACE INTO observed (chain, observation) VALUES (?, ?)", (obs["chainId"], canonical_json(obs)))
                self._hook("before_commit")
                self._con.execute("COMMIT")
            except BaseException:
                if self._con.in_transaction:
                    self._con.execute("ROLLBACK")
                raise


class _FaultSet(Exception):
    """Internal: a regression was recorded inside the transaction; the fault row must be COMMITTED before the refusal is raised."""

    def __init__(self, error: StoreError):
        super().__init__(str(error))
        self.error = error


# ---------------------------------------------------------------- the read-only exporter CLI ----------------------------------------------------------
def _witness_index(v: str) -> int:
    import argparse
    try:
        i = int(v)
    except ValueError:
        raise argparse.ArgumentTypeError("--witness-index must be an integer 0..3") from None
    if not 0 <= i <= 3:
        raise argparse.ArgumentTypeError("--witness-index must be 0..3")
    return i


def main(argv=None) -> int:
    """`python -m hmbc_protocol.witness_state --state-dir D --witness-index I (--binding | --evidence)` (EXPORT-LAYOUTS section 1). Success: exit 0, stdout ONE canonical JSON line plus one LF,
    stderr empty. Refusal: exit 3, stdout empty, stderr one canonical {code, message, reason} line. Usage errors: exit 2 (argparse). Read-only, no RPC, no key material."""
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog="hmbc_protocol.witness_state", description=main.__doc__)
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--witness-index", required=True, type=_witness_index)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--evidence", action="store_true")
    g.add_argument("--binding", action="store_true")
    ns = ap.parse_args(argv)
    try:
        try:
            view = view_for_export(os.path.join(ns.state_dir, f"witness-{ns.witness_index}"))
            if ns.binding:
                if view.anchor is None:
                    raise StoreError("STORE_CORRUPT", "the binding rows carry no anchor")
                doc = view.binding_export(view.anchor)
            else:
                doc = view.evidence()
        except sqlite3.DatabaseError as e:
            raise StoreError("STORE_CORRUPT", f"the database cannot be read: {e}") from None
    except StoreError as e:
        sys.stderr.write(canonical_json({"code": e.code, "message": e.message, "reason": e.reason}) + "\n")
        return 3
    sys.stdout.write(canonical_json(doc) + "\n")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
