"""Durable key worker (symbolic mode): record registration, grant-bound release, crash-safe retry, completion.

A grant is authorisation, a send is an attempted delivery, and an acknowledged transmission is yet another fact; they are three
separate durable records. Intent (and the response token) is committed to disk BEFORE anything is transmitted; a retry returns the same
cached response only while the original grant is unexpired and never mints a new capability. Nothing here is real ABE: the token is a
TEST-ONLY random handle with no cryptographic confidentiality (A33).
"""
from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import sqlite3
import stat
from typing import Callable

from . import eip712, keys, symbolic, wire
from .ledger import Ledger


class WorkerError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code, self.message = code, message


class SimulatedCrash(Exception):
    """Fault-injection stand-in for a process crash at a named point; the on-disk state is whatever was durable at that moment."""


_SCHEMA = """
create table if not exists records(data_id text primary key, owner text not null, payload_digest text not null,
  policy_json text not null, policy_digest text not null, ciphertext_digest text not null);
create table if not exists releases(grant_id text primary key, request_digest text not null, data_id text not null, gid text not null,
  recipient_key_hash text not null, key_epoch text not null, ciphertext_digest text not null, token text not null,
  grant_expires_at integer not null, created_at integer not null, delivery text not null, sent_count integer not null default 0,
  completed_count integer not null default 0);
create table if not exists meta(key text primary key, value text not null);
create table if not exists events(id integer primary key autoincrement, type text not null, request_digest text not null,
  grant_id text not null, gid text not null, data_id text not null, timestamp integer not null);
"""


class Worker:
    def __init__(self, led: Ledger, state_dir, clock: Callable[[], int], faults=frozenset()):
        self.led, self.clock, self.faults = led, clock, set(faults)
        os.makedirs(state_dir, mode=0o700, exist_ok=True)
        if stat.S_IMODE(os.stat(state_dir).st_mode) & 0o077:
            raise WorkerError("MALFORMED", "worker state directory must not be accessible to group/other (chmod 700)")
        old = os.umask(0o077)
        try:
            # Serialise first-time initialisation (WAL switch + schema + deployment fingerprint) across threads/processes sharing a state dir:
            # SQLite does not apply the busy timeout to the journal-mode switch, so concurrent first opens could fail "database is locked".
            with open(os.path.join(state_dir, ".init.lock"), "a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                self.db = sqlite3.connect(os.path.join(state_dir, "worker.sqlite"), isolation_level=None, timeout=15)
                self.db.execute("pragma journal_mode=wal")
                self.db.execute("pragma synchronous=full")                           # a commit is on disk when it returns
                self.db.executescript(_SCHEMA)
                # State belongs to ONE deployment: a worker pointed at another (e.g. fake) ledger must not mint capabilities from this DB.
                dep = led.deployment["chains"]
                fp = hashlib.sha256(json.dumps({"pbc": [dep["pbc"]["chainId"], dep["pbc"]["contracts"]["PSC"], dep["pbc"]["contracts"]["RSC"]],
                                                "dbc": [dep["dbc"]["chainId"], dep["dbc"]["contracts"]["KSSC"], dep["dbc"]["contracts"]["ACSC"]]},
                                               sort_keys=True).encode()).hexdigest()
                self.db.execute("insert or ignore into meta values('deployment', ?)", (fp,))
                stored = self.db.execute("select value from meta where key='deployment'").fetchone()[0]
        finally:
            os.umask(old)
        if stored != fp:
            raise WorkerError("WRONG_DESTINATION", "this worker state belongs to a different ledger deployment")
        self.db.execute("pragma synchronous=full")

    # -- encrypt_record -----------------------------------------------------------------------------------------------------
    def encrypt_record(self, record: dict, policy: dict, key_epoch: str) -> dict:
        try:
            wire.encrypt_record_input({"record": record, "policy": policy, "keyEpoch": key_epoch})
        except wire.WireError as e:
            raise WorkerError("MALFORMED", str(e)) from None
        led = self.led
        entry = led.dbc.call(led.ACSC, "dataEntry", record["dataId"])
        if not entry["exists"] or entry["owner"] != record["owner"]:
            raise WorkerError("WRONG_SUBJECT", "the ACSC has no such record or a different owner")
        registered = symbolic.policy_digest({"clauses": led.dbc.call(led.ACSC, "policy", entry["policyId"])})
        pd = symbolic.policy_digest(policy)
        if pd != registered:
            raise WorkerError("WRONG_SUBJECT", "policy differs from the policy registered for this record on the ACSC")
        cd = symbolic.ciphertext_digest(record, policy)
        self.db.execute("begin immediate")                       # select-then-insert must be atomic across threads/processes
        try:
            row = self.db.execute("select payload_digest, policy_digest from records where data_id=?", (record["dataId"],)).fetchone()
            if row is None:
                self.db.execute("insert into records values(?,?,?,?,?,?)",
                                (record["dataId"], record["owner"], record["payloadDigest"], repr(sorted(policy.items())), pd, cd))
            self.db.execute("commit")
        except BaseException:
            self.db.execute("rollback")
            raise
        if row is not None and row != (record["payloadDigest"], pd):
            raise WorkerError("WRONG_SUBJECT", "dataId is already registered with different content")
        return {"schemaVersion": "v1", "adapterMode": "symbolic", "dataId": record["dataId"], "keyEpoch": "0",
                "ciphertextDigest": cd, "policyDigest": pd}

    # -- release ------------------------------------------------------------------------------------------------------------
    def _recipient_for(self, g: dict) -> str:
        """The recipient commitment a release is bound to.

        repaired-e: the grant's own recipientKeyHash, which must be non-zero and equal the GID's registered key (the PSC enforced that at request time).
        paper profiles (decision D35 / assumption A38, option (c)): the DBC grant carries NO recipient (zero, A24), so the response is bound to the key the grant's
        GID registered on the PBC, RSC.recipientKeyHash(grant.gid): a symbolic reconstruction of HMBC III-D3 (the PSC returns the response encrypted to the user's key),
        NOT real encryption. The GID is relay-asserted in the paper tuple, so subject substitution binds the response to the substituted subject (a visible SPEC_GAP); a GID
        with no registered key gets NO release (WRONG_SUBJECT, before any intent). The grant's native zero is never rewritten: only the response/worker record carry the key."""
        led = self.led
        registered = led.pbc.call(led.RSC, "recipientKeyHash", g["gid"])
        if led.pbc.call(led.PSC, "profile") == "2":
            if int(g["recipientKeyHash"], 16) == 0 or g["recipientKeyHash"] != registered:
                raise WorkerError("WRONG_SUBJECT", "the grant's recipient key is unbound or differs from the registered one")
            return g["recipientKeyHash"]
        if int(registered, 16) == 0:
            raise WorkerError("WRONG_SUBJECT", "the grant's GID has no registered recipient key, so a paper-mode response has no recipient to bind to")
        if int(g["recipientKeyHash"], 16) != 0:
            raise WorkerError("WRONG_SUBJECT", "a paper-profile grant is expected to carry no recipient commitment")
        return registered

    def _event(self, kind: str, row: tuple, ts: int) -> None:
        self.db.execute("insert into events(type,request_digest,grant_id,gid,data_id,timestamp) values(?,?,?,?,?,?)",
                        (kind, row[0], row[1], row[2], row[3], ts))

    def release(self, grant_id: str, transmit: Callable[[dict], None] | None = None) -> dict:
        try:
            wire.hash32(grant_id)
        except wire.WireError as e:
            raise WorkerError("MALFORMED", str(e)) from None
        led = self.led
        g = led.dbc.call(led.KSSC, "grantDetails", grant_id)
        bound = "0x" + eip712.grant_id(bytes.fromhex(g["requestDigest"][2:]), led.KSSC.address, led.dbc.chain_id).hex()
        if not g["exists"] or not g["allowed"] or bound != grant_id:
            raise WorkerError("NOT_COMMITTED", "no allowed grant with this id is committed on the DBC")
        now = self.clock()
        if now >= int(g["expiresAt"]):
            raise WorkerError("EXPIRED", "the grant has expired; a retry never extends its lifetime")
        if g["keyEpoch"] != "0":
            raise WorkerError("WRONG_EPOCH", "E supports keyEpoch 0 only")
        recipient = self._recipient_for(g)
        rec = self.db.execute("select ciphertext_digest from records where data_id=?", (g["dataId"],)).fetchone()
        if rec is None:
            raise WorkerError("WRONG_SUBJECT", "no record is registered with this worker for the granted dataId")
        ident = (g["requestDigest"], grant_id, g["gid"], g["dataId"])
        self.db.execute("begin immediate")
        try:
            row = self.db.execute("select token from releases where grant_id=?", (grant_id,)).fetchone()
            created = row is None
            if created:
                token = "0x" + os.urandom(32).hex()
                self.db.execute("insert into releases values(?,?,?,?,?,?,?,?,?,?,?,0,0)",
                                (grant_id, g["requestDigest"], g["dataId"], g["gid"], recipient, g["keyEpoch"], rec[0],
                                 token, int(g["expiresAt"]), now, "unknown"))
                self._event("RELEASE_INTENT", ident, now)
            else:
                token = row[0]
            self.db.execute("commit")
        except BaseException:
            self.db.execute("rollback")
            raise
        if "crash_after_intent" in self.faults:
            self.faults.discard("crash_after_intent")
            raise SimulatedCrash("crash after durable intent, before send")
        response = {"schemaVersion": "v1", "adapterMode": "symbolic", "requestDigest": g["requestDigest"], "grantId": grant_id,
                    "dataId": g["dataId"], "ciphertextDigest": rec[0], "recipientKeyHash": recipient, "keyEpoch": "0",
                    "responseEnvelope": {"kind": "symbolic-partial/v1", "token": token}}
        # Write-ahead: the ATTEMPT is durable before the response can leave, exactly like the intent, so the audit log can never lack a send that happened.
        # RELEASE_SENT therefore means "a send was attempted", never "delivered": the protocol has no recipient acknowledgement, so delivery stays "unknown".
        self.db.execute("begin immediate")
        try:
            self.db.execute("update releases set sent_count=sent_count+1 where grant_id=?", (grant_id,))
            self._event("RELEASE_SENT", ident, self.clock())
            self.db.execute("commit")
        except BaseException:
            self.db.execute("rollback")
            raise
        if transmit is not None:
            transmit(response)
        if "crash_after_send" in self.faults:
            self.faults.discard("crash_after_send")
            raise SimulatedCrash("crash after the send, before it was recorded as completed")
        self.db.execute("update releases set completed_count=completed_count+1 where grant_id=?", (grant_id,))
        return response

    # -- completion ---------------------------------------------------------------------------------------------------------
    def finish_decryption(self, response: dict, user_key_ref: str) -> dict:
        try:
            wire.finish_decryption_input({"response": response, "userKeyRef": user_key_ref})
        except wire.WireError as e:
            raise WorkerError("MALFORMED", str(e)) from None
        row = self.db.execute("select request_digest,data_id,ciphertext_digest,recipient_key_hash,key_epoch,token from releases where grant_id=?",
                              (response["grantId"],)).fetchone()
        issued = None if row is None else (row[0], row[1], row[2], row[3], row[4], row[5])
        offered = (response["requestDigest"], response["dataId"], response["ciphertextDigest"], response["recipientKeyHash"],
                   response["keyEpoch"], response["responseEnvelope"]["token"])
        if issued is None or not all(hmac.compare_digest(a.encode(), b.encode()) for a, b in zip(issued, offered)):
            raise WorkerError("WRONG_SUBJECT", "this response was not issued by this worker for this grant")
        if keys.recipient_key_hash(user_key_ref) != issued[3]:
            raise WorkerError("WRONG_SUBJECT", "the user key reference does not match the recipient the response is bound to")
        return {"schemaVersion": "v1", "adapterMode": "symbolic", "decryptable": True, "dataId": issued[1], "ciphertextDigest": issued[2]}

    # -- observation --------------------------------------------------------------------------------------------------------
    def status(self, grant_id: str) -> dict | None:
        r = self.db.execute("select delivery, sent_count, completed_count, grant_expires_at from releases where grant_id=?", (grant_id,)).fetchone()
        return None if r is None else {"delivery": r[0], "sendAttempts": r[1], "completedAttempts": r[2], "grantExpiresAt": str(r[3])}

    def events(self) -> list[dict]:
        return [{"type": t, "requestDigest": rd, "timestamp": str(ts), "grantId": gi, "gid": gid, "dataId": did}
                for t, rd, gi, gid, did, ts in self.db.execute(
                    "select type,request_digest,grant_id,gid,data_id,timestamp from events order by id")]
