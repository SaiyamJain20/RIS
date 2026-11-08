"""Durable witness signing store (agent 2, F task 2, slice 1). Written BEFORE hmbc_protocol/witness_state.py existed.

Covers the lifecycle of SUCCESSOR-WIRE section 5 (init order, crash points, every open refusal with the logical snapshot unchanged), the signing rule of SIGNING-RULES section 2 and 6
(commit before signature, idempotent re-sign, CONFLICT_PINNED with the recorded value, supersession only after death, A -> B -> A), the tripwire (persisted FAULTED, clear keeps history)
and the evidence/binding exports, which are cross-checked against MY OWN layout and D50 reference checkers (protocol/f0/vectors). No chain: the signer and the observation source are
injected; digests and signatures are placeholders. Process death is the only crash mode injected; power loss is not tested.
"""
import copy
import hashlib
import importlib.util
import json
import os
import sqlite3
import stat
import subprocess
import sys
import threading

import pytest

from hmbc_protocol import witness_state as ws
from testtools import state_oracle

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
V = os.path.join(ROOT, "protocol", "f0", "vectors")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(V, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


d50 = _load("d50_reference")
LAY = _load("export_layouts_reference")
B = d50.synthetic_binding_document("repaired-f")
BIND = d50.binding_v2(B)
OWNER = "witness:0x" + "11" * 20
DBC, PBC = B["chains"]["dbc"]["chainId"], B["chains"]["pbc"]["chainId"]
DOM_S, DOM_D = "0x" + "a1" * 32, "0x" + "a2" * 32
CHILD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state_child.py")


def h(label):
    return "0x" + hashlib.sha256(label.encode()).hexdigest()


def signer(digest):
    return "0x" + (hashlib.sha256(digest.encode()).hexdigest() * 3)[:130]


def obs(chain, number, ts):
    return {"chainId": chain, "blockNumber": str(number), "blockHash": h("block:%s:%d" % (chain, number)), "timestamp": str(ts)}


def cp_effect(block):
    return {"authEpoch": "3", "policyVersion": "1", "keyEpoch": "0", "witnessSetVersion": "2", "sourceChainId": PBC, "psc": "0x" + "bb" * 20,
            "sourceBlockNumber": str(block), "sourceBlockHash": h("block:%s:%d" % (PBC, block))}


def dec_effect(seq, result="1"):
    return {"result": result, "credentialDigest": h("cred"), "stateSequence": str(seq), "witnessSetVersion": "2", "sourceBlockNumber": "158", "sourceBlockHash": h("b158")}


@pytest.fixture
def store(tmp_path):
    return ws.init_store(str(tmp_path / "witness-0"), BIND, B, OWNER)


def sign_cp(st, seq, block, expires, label, o, **kw):
    return st.sign(type="StateCheckpoint", domain=DOM_S, wsv="2", key=str(seq), effect=cp_effect(block), expires_at=str(expires), digest=h(label), signer=signer, observe=lambda: o, **kw)


def refusal(fn):
    try:
        fn()
    except ws.StoreError as e:
        return e
    return None


# ---------------------------------------------------------------- lifecycle ------------------------------------------------------------------
def test_init_creates_a_private_directory_database_and_marker(tmp_path):
    d = str(tmp_path / "w0")
    st = ws.init_store(d, BIND, B, OWNER)
    assert stat.S_IMODE(os.stat(d).st_mode) == 0o700
    marker = json.loads(open(os.path.join(d, "INITIALIZED")).read())
    assert marker == {"binding_v2": BIND, "owner": OWNER, "schema": "2"}
    assert not os.path.exists(os.path.join(d, "INITIALIZED.tmp"))
    con = sqlite3.connect(os.path.join(d, "signing.sqlite"))
    assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    meta = dict(con.execute("SELECT key, value FROM meta"))
    assert meta["binding_v2"] == BIND and meta["owner"] == OWNER and meta["schema"] == "2" and json.loads(meta["binding_v2_doc"]) == B
    assert st.owner == OWNER and st.binding_v2 == BIND


def test_reopen_of_an_initialised_store_works_and_never_reinitialises(tmp_path):
    d = str(tmp_path / "w0")
    ws.init_store(d, BIND, B, OWNER)
    before = state_oracle.logical_snapshot(d)
    st = ws.open_store(d, BIND, OWNER)
    assert st.binding_v2 == BIND and state_oracle.logical_snapshot(d) == before
    again = ws.init_store(d, BIND, B, OWNER)                                       # an existing store is OPENED, never initialised over (SUCCESSOR-WIRE section 5)
    assert again.binding_v2 == BIND and state_oracle.logical_snapshot(d) == before
    e = refusal(lambda: ws.init_store(d, "f" * 64, B, OWNER))                      # ... and a different binding is refused, not overwritten
    assert e is not None and (e.reason, e.code) == ("BINDING_MISMATCH", "WRONG_DESTINATION")
    assert state_oracle.logical_snapshot(d) == before


@pytest.mark.parametrize("point,has_marker", [("after_dir", False), ("after_db_commit", False), ("after_tmp_marker", False), ("after_rename", True)])
def test_crash_during_initialisation_then_restart_completes_it(tmp_path, point, has_marker):
    d = str(tmp_path / "w0")
    cfg = json.dumps({"binding_v2": BIND, "document": B, "owner": OWNER})
    r = subprocess.run([sys.executable, "-B", CHILD, d, point, "init", cfg], capture_output=True, text=True)
    assert r.returncode == 77 and "init-complete" not in r.stdout
    assert os.path.exists(os.path.join(d, "INITIALIZED")) == has_marker
    if os.path.exists(os.path.join(d, "signing.sqlite")):          # nothing can have been signed before the marker: no record rows
        con = sqlite3.connect(os.path.join(d, "signing.sqlite"))
        assert con.execute("SELECT COUNT(*) FROM conflict").fetchone()[0] == 0 and con.execute("SELECT COUNT(*) FROM digests").fetchone()[0] == 0
    st = ws.init_store(d, BIND, B, OWNER) if not has_marker else ws.open_store(d, BIND, OWNER)           # restart completes (or simply opens)
    assert os.path.exists(os.path.join(d, "INITIALIZED")) and not os.path.exists(os.path.join(d, "INITIALIZED.tmp"))
    assert sign_cp(st, 4, 138, 1791521610, "d1", obs(DBC, 159, 1791521590)) == signer(h("d1"))


def test_signing_is_refused_without_the_marker(tmp_path):
    d = str(tmp_path / "w0")
    cfg = json.dumps({"binding_v2": BIND, "document": B, "owner": OWNER})
    subprocess.run([sys.executable, "-B", CHILD, d, "after_db_commit", "init", cfg], capture_output=True)
    e = refusal(lambda: ws.open_store(d, BIND, OWNER))
    assert e is not None and e.reason in ("STORE_MISSING", "STORE_CORRUPT")


def _refused_open_leaves_state_unchanged(d, fn, reason, code):
    before = state_oracle.logical_snapshot(d)
    e = refusal(fn)
    assert e is not None, "expected a refusal"
    assert (e.reason, e.code) == (reason, code)
    assert state_oracle.logical_snapshot(d) == before


def test_every_open_refusal_has_its_reason_and_changes_nothing(tmp_path):
    base = tmp_path / "base"
    ws.init_store(str(base), BIND, B, OWNER)
    import shutil
    # marker without a database
    d = str(tmp_path / "missing"); shutil.copytree(str(base), d); os.remove(os.path.join(d, "signing.sqlite"))
    for suffix in ("-wal", "-shm"):
        if os.path.exists(os.path.join(d, "signing.sqlite" + suffix)): os.remove(os.path.join(d, "signing.sqlite" + suffix))
    _refused_open_leaves_state_unchanged(d, lambda: ws.open_store(d, BIND, OWNER), "STORE_MISSING", "ADAPTER_UNAVAILABLE")
    # corrupt database bytes
    d = str(tmp_path / "corrupt"); shutil.copytree(str(base), d)
    for suffix in ("-wal", "-shm"):
        if os.path.exists(os.path.join(d, "signing.sqlite" + suffix)): os.remove(os.path.join(d, "signing.sqlite" + suffix))
    open(os.path.join(d, "signing.sqlite"), "r+b").write(b"\x00" * 200)
    e = refusal(lambda: ws.open_store(d, BIND, OWNER)); assert e is not None and (e.reason, e.code) == ("STORE_CORRUPT", "ADAPTER_UNAVAILABLE")
    # a marker that names another binding than the database
    d = str(tmp_path / "markerdiff"); shutil.copytree(str(base), d)
    open(os.path.join(d, "INITIALIZED"), "w").write(json.dumps({"binding_v2": "0" * 64, "owner": OWNER, "schema": "2"}))
    _refused_open_leaves_state_unchanged(d, lambda: ws.open_store(d, BIND, OWNER), "STORE_CORRUPT", "ADAPTER_UNAVAILABLE")
    # binding and owner differ
    d = str(base)
    _refused_open_leaves_state_unchanged(d, lambda: ws.open_store(d, "f" * 64, OWNER), "BINDING_MISMATCH", "WRONG_DESTINATION")
    _refused_open_leaves_state_unchanged(d, lambda: ws.open_store(d, BIND, "witness:0x" + "22" * 20), "OWNER_MISMATCH", "WRONG_DESTINATION")
    # precedence: a binding that differs is reported before an owner that differs
    _refused_open_leaves_state_unchanged(d, lambda: ws.open_store(d, "f" * 64, "witness:0x" + "22" * 20), "BINDING_MISMATCH", "WRONG_DESTINATION")


def test_a_legacy_store_with_rows_and_no_binding_is_refused(tmp_path):
    d = str(tmp_path / "legacy"); os.makedirs(d, mode=0o700)
    con = sqlite3.connect(os.path.join(d, "signing.sqlite"))
    con.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, body TEXT)"); con.execute("INSERT INTO records (body) VALUES ('x')"); con.commit(); con.close()
    _refused_open_leaves_state_unchanged(d, lambda: ws.init_store(d, BIND, B, OWNER), "LEGACY_STATE", "WRONG_DESTINATION")


def test_records_without_the_marker_are_corrupt_not_initialised(tmp_path):
    d = str(tmp_path / "w0"); ws.init_store(d, BIND, B, OWNER)
    st = ws.open_store(d, BIND, OWNER); sign_cp(st, 4, 138, 1791521610, "d1", obs(DBC, 159, 1791521590)); st.close()
    os.remove(os.path.join(d, "INITIALIZED"))
    _refused_open_leaves_state_unchanged(d, lambda: ws.open_store(d, BIND, OWNER), "STORE_CORRUPT", "ADAPTER_UNAVAILABLE")


def test_a_database_that_opens_but_fails_integrity_check_is_corrupt(tmp_path):
    """A corruption that leaves the identity rows readable: only PRAGMA integrity_check can find it (the test searches the pages for one, and asserts it found one)."""
    d = str(tmp_path / "w0"); st = ws.init_store(d, BIND, B, OWNER)
    for i in range(1, 40):
        sign_cp(st, i, 100 + i, 1791521610, "d%d" % i, obs(DBC, 100 + i, 1791521000 + i))
    st.close()
    db = os.path.join(d, "signing.sqlite")
    con = sqlite3.connect(db); con.execute("PRAGMA wal_checkpoint(TRUNCATE)"); ps = con.execute("PRAGMA page_size").fetchone()[0]; pc = con.execute("PRAGMA page_count").fetchone()[0]; con.close()
    found = False
    for page in range(2, pc + 1):
        good = open(db, "rb").read()
        with open(db, "r+b") as f:
            f.seek((page - 1) * ps + ps // 2); f.write(b"\xff" * 16)
        try:
            ro = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
            ok = ro.execute("PRAGMA integrity_check").fetchone()[0] != "ok" and ro.execute("SELECT COUNT(*) FROM meta").fetchone()[0] == 4
            ro.close()
        except sqlite3.DatabaseError:
            ok = False
        if ok:
            found = True
            break
        open(db, "wb").write(good)
    assert found, "no page corruption left the identity rows readable while failing integrity_check"
    before = state_oracle.main_file_sha256(d)
    e = refusal(lambda: ws.open_store(d, BIND, OWNER))
    assert e is not None and (e.reason, e.code) == ("STORE_CORRUPT", "ADAPTER_UNAVAILABLE") and state_oracle.main_file_sha256(d) == before


def test_init_makes_an_existing_directory_private(tmp_path):
    d = str(tmp_path / "w0"); os.makedirs(d, mode=0o755); os.chmod(d, 0o755)
    ws.init_store(d, BIND, B, OWNER)
    assert stat.S_IMODE(os.stat(d).st_mode) == 0o700


def test_oracle_sees_a_wal_only_commit_while_the_main_file_hash_does_not(tmp_path):
    """Negative control of the ORACLE itself (not of the store): a committed row that lives only in the -wal file."""
    d = str(tmp_path / "w0"); ws.init_store(d, BIND, B, OWNER)
    main_before, snap_before = state_oracle.main_file_sha256(d), state_oracle.logical_snapshot(d)
    con = sqlite3.connect(os.path.join(d, "signing.sqlite")); con.execute("PRAGMA wal_autocheckpoint=0")
    con.execute("INSERT INTO meta (key, value) VALUES ('wal-only', 'x')"); con.commit()
    assert state_oracle.main_file_sha256(d) == main_before          # the WRONG oracle misses it
    assert state_oracle.logical_snapshot(d) != snap_before          # the logical snapshot sees it
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)"); con.close()      # a checkpoint alone preserves the logical snapshot
    snap_after = state_oracle.logical_snapshot(d)
    con = sqlite3.connect(os.path.join(d, "signing.sqlite")); con.execute("PRAGMA wal_checkpoint(TRUNCATE)"); con.close()
    assert state_oracle.logical_snapshot(d) == snap_after


# ---------------------------------------------------------------- the signing rule -----------------------------------------------------------
def test_first_signature_is_recorded_and_returned(store):
    sig = sign_cp(store, 4, 138, 1791521610, "d1", obs(DBC, 159, 1791521590))
    assert sig == signer(h("d1"))
    ev = store.evidence()
    assert len(ev["conflicts"]) == 1 and ev["conflicts"][0]["digests"][0]["signature"] == sig and ev["superseded"] == []


def test_same_digest_returns_the_stored_signature_and_adds_no_row(store):
    o = obs(DBC, 159, 1791521590)
    first = sign_cp(store, 4, 138, 1791521610, "d1", o)
    before = state_oracle.logical_snapshot(store.directory)
    calls = []
    again = store.sign(type="StateCheckpoint", domain=DOM_S, wsv="2", key="4", effect=cp_effect(138), expires_at="1791521610", digest=h("d1"), signer=lambda d: calls.append(d) or "0x" + "00" * 65, observe=lambda: o)
    assert again == first and calls == []              # the STORED signature, the signer is not even asked
    assert state_oracle.logical_snapshot(store.directory) == before


def test_same_effect_with_a_later_expiry_adds_a_digest_to_the_same_record(store):
    sign_cp(store, 4, 138, 1791521610, "d1", obs(DBC, 159, 1791521590))
    sign_cp(store, 4, 138, 1791521640, "d2", obs(DBC, 160, 1791521600))
    ev = store.evidence()
    assert len(ev["conflicts"]) == 1 and [d["expiresAt"] for d in ev["conflicts"][0]["digests"]] == ["1791521610", "1791521640"] and ev["superseded"] == []


def test_a_different_effect_for_a_live_key_is_pinned_with_the_recorded_value_and_changes_nothing(store):
    sign_cp(store, 4, 138, 1791521610, "d1", obs(DBC, 159, 1791521590))
    late = sign_cp(store, 4, 138, 1791521640, "d2", obs(DBC, 160, 1791521600))
    before = state_oracle.logical_snapshot(store.directory)
    e = refusal(lambda: store.sign(type="StateCheckpoint", domain=DOM_S, wsv="2", key="4", effect=cp_effect(139), expires_at="1791521650", digest=h("d3"), signer=signer, observe=lambda: obs(DBC, 160, 1791521600)))
    assert e is not None and (e.reason, e.code) == ("CONFLICT_PINNED", "STALE_STATE")
    assert e.recorded == {"message": {"sequence": "4", **cp_effect(138), "expiresAt": "1791521640"}, "signature": late}      # the latest-expiry digest, nothing new signed
    assert state_oracle.logical_snapshot(store.directory) == before


def test_supersession_needs_every_digest_dead_by_an_observed_expiry(store):
    sign_cp(store, 4, 138, 1791521610, "d1", obs(DBC, 159, 1791521590))
    sign_cp(store, 4, 138, 1791521640, "d2", obs(DBC, 160, 1791521600))
    new = lambda o, lab="d3": store.sign(type="StateCheckpoint", domain=DOM_S, wsv="2", key="4", effect=cp_effect(139), expires_at=str(1791521700), digest=h(lab), signer=signer, observe=lambda: o)
    e = refusal(lambda: new(obs(DBC, 170, 1791521639)))                 # one tick before the LATEST expiry: not dead
    assert e is not None and e.reason == "CONFLICT_PINNED"
    sig = new(obs(DBC, 171, 1791521640))                                # observed timestamp >= every expiry: dead
    assert sig == signer(h("d3"))
    ev = store.evidence()
    assert len(ev["superseded"]) == 1 and ev["superseded"][0]["death"]["kind"] == "expiry" and ev["superseded"][0]["seq"] == "1"
    assert ev["conflicts"][0]["effect"]["sourceBlockNumber"] == "139" and len(ev["superseded"][0]["digests"]) == 2


def test_a_to_b_to_a_is_legal_and_the_evidence_validates(store):
    t = 1791521500
    def put(effect_block, label, exp, n, ts):
        return store.sign(type="StateCheckpoint", domain=DOM_S, wsv="2", key="4", effect=cp_effect(effect_block), expires_at=str(exp), digest=h(label), signer=signer, observe=lambda: obs(DBC, n, ts))
    put(136, "A1", t + 60, 150, t)
    put(137, "B", t + 121, 160, t + 61)
    put(136, "A2", t + 182, 170, t + 122)
    ev = store.evidence()
    assert [s["death"]["kind"] for s in ev["superseded"]] == ["expiry", "expiry"] and ev["conflicts"][0]["effect"]["sourceBlockNumber"] == "136"
    LAY.validate_evidence(ev)


def test_a_decision_dies_when_the_checkpoint_sequence_overtakes_it(store):
    o1 = obs(DBC, 154, 1791521530)
    store.sign(type="AccessDecision", domain=DOM_D, wsv="2", key=h("req"), effect=dec_effect(5), expires_at="1791521600", digest=h("dec1"), signer=signer, observe=lambda: o1)    # unexpired at the later observations: only the overtaken fact can kill it
    new = lambda o, over: store.sign(type="AccessDecision", domain=DOM_D, wsv="2", key=h("req"), effect=dec_effect(6), expires_at="1791521620", digest=h("dec2"), signer=signer, observe=lambda: o, overtaken=over)
    e = refusal(lambda: new(obs(DBC, 155, 1791521540), ("overtaken-decision-sequence", "5")))      # observed == stateSequence is NOT overtaken
    assert e is not None and e.reason == "CONFLICT_PINNED"
    e = refusal(lambda: new(obs(DBC, 155, 1791521540), None))
    assert e is not None and e.reason == "CONFLICT_PINNED"
    new(obs(DBC, 158, 1791521570), ("overtaken-decision-sequence", "6"))
    assert store.evidence()["superseded"][0]["death"] == {"kind": "overtaken-decision-sequence", "observation": obs(DBC, 158, 1791521570), "observed": "6"}


def test_only_an_allow_decision_can_die_by_grant_and_the_effect_fields_are_enforced(store):
    o = obs(DBC, 155, 1791521540)
    kw = dict(type="AccessDecision", domain=DOM_D, wsv="2", signer=signer)
    store.sign(key=h("deny-req"), effect=dec_effect(5, "0"), expires_at="1791521600", digest=h("deny1"), observe=lambda: obs(DBC, 154, 1791521530), **kw)
    e = refusal(lambda: store.sign(key=h("deny-req"), effect=dec_effect(6, "0"), expires_at="1791521650", digest=h("deny2"), observe=lambda: o, overtaken=("overtaken-decision-grant", None), **kw))
    assert e is not None and e.reason == "CONFLICT_PINNED"                       # a DENY is never dead by grant: the ledger still accepts it (A1-0107)
    store.sign(key=h("allow-req"), effect=dec_effect(5, "1"), expires_at="1791521600", digest=h("allow1"), observe=lambda: obs(DBC, 154, 1791521531), **kw)
    store.sign(key=h("allow-req"), effect=dec_effect(6, "0"), expires_at="1791521650", digest=h("allow2"), observe=lambda: o, overtaken=("overtaken-decision-grant", None), **kw)
    kinds = [s_["death"]["kind"] for s_ in store.evidence()["superseded"]]
    assert kinds == ["overtaken-decision-grant"]                                 # an ALLOW dead by grant, then a live DENY for the same request
    LAY.validate_evidence(store.evidence())
    with pytest.raises(ValueError):
        store.sign(key=h("x"), effect={k: v for k, v in dec_effect(5).items() if k != "result"}, expires_at="1791521600", digest=h("bad1"), observe=lambda: o, **kw)
    with pytest.raises(ValueError):
        store.sign(key=h("x"), effect={**dec_effect(5), "extra": "1"}, expires_at="1791521600", digest=h("bad2"), observe=lambda: o, **kw)


def test_the_target_ledger_is_checked_and_wall_clock_is_never_read(store, monkeypatch):
    with pytest.raises(ValueError):                       # a checkpoint observed on the PBC is a caller bug, not a refusal
        sign_cp(store, 4, 138, 1791521610, "d1", obs(PBC, 140, 1791521590))
    import time
    monkeypatch.setattr(time, "time", lambda: (_ for _ in ()).throw(AssertionError("wall clock read")))
    monkeypatch.setattr(time, "monotonic", lambda: (_ for _ in ()).throw(AssertionError("clock read")))
    sign_cp(store, 4, 138, 1791521610, "d1", obs(DBC, 159, 1791521590))


def test_keys_are_independent_across_types_domains_and_sequences(store):
    o = obs(DBC, 159, 1791521590)
    sign_cp(store, 4, 138, 1791521610, "d1", o)
    sign_cp(store, 5, 139, 1791521610, "d2", o)                                  # another sequence: another key, no conflict
    store.sign(type="StateCheckpoint", domain="0x" + "c3" * 32, wsv="2", key="4", effect=cp_effect(139), expires_at="1791521610", digest=h("d3"), signer=signer, observe=lambda: o)
    assert len(store.evidence()["conflicts"]) == 3


def test_concurrent_signers_for_one_key_produce_exactly_one_effect(tmp_path):
    d = str(tmp_path / "w0"); ws.init_store(d, BIND, B, OWNER)
    results = []
    def worker(block, label):
        st = ws.open_store(d, BIND, OWNER)
        try:
            st.sign(type="StateCheckpoint", domain=DOM_S, wsv="2", key="4", effect=cp_effect(block), expires_at="1791521610", digest=h(label), signer=signer, observe=lambda: obs(DBC, 159, 1791521590))
            results.append("signed")
        except ws.StoreError as e:
            results.append(e.reason)
    ts = [threading.Thread(target=worker, args=(130 + i, "c%d" % i)) for i in range(6)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert sorted(results) == ["CONFLICT_PINNED"] * 5 + ["signed"]
    assert len(ws.open_store(d, BIND, OWNER).evidence()["conflicts"]) == 1


# ---------------------------------------------------------------- commit before signature -------------------------------------------------------
def _child_sign(d, point, label="d1", expires="1791521610", block=138):
    cfg = json.dumps({"binding_v2": BIND, "owner": OWNER, "type": "StateCheckpoint", "domain": DOM_S, "key": "4", "effect": cp_effect(block), "expires_at": expires, "digest": h(label), "obs": obs(DBC, 159, 1791521590)})
    return subprocess.run([sys.executable, "-B", CHILD, d, point, "sign", cfg], capture_output=True, text=True)


def test_a_crash_before_the_commit_signs_nothing(tmp_path):
    d = str(tmp_path / "w0"); ws.init_store(d, BIND, B, OWNER)
    before = state_oracle.logical_snapshot(d)
    r = _child_sign(d, "before_commit")
    assert r.returncode == 77 and "signature-returned" not in r.stdout          # no signature left the process
    assert state_oracle.logical_snapshot(d) == before


def test_a_crash_after_the_commit_and_before_the_reply_keeps_the_record_and_the_retry_is_idempotent(tmp_path):
    d = str(tmp_path / "w0"); ws.init_store(d, BIND, B, OWNER)
    r = _child_sign(d, "after_commit")
    assert r.returncode == 77 and "signature-returned" not in r.stdout
    st = ws.open_store(d, BIND, OWNER)
    assert len(st.evidence()["conflicts"]) == 1                                  # the choice is durable although the caller never saw a signature
    other = refusal(lambda: st.sign(type="StateCheckpoint", domain=DOM_S, wsv="2", key="4", effect=cp_effect(139), expires_at="1791521610", digest=h("x"), signer=signer, observe=lambda: obs(DBC, 160, 1791521591)))
    assert other is not None and other.reason == "CONFLICT_PINNED"
    assert sign_cp(st, 4, 138, 1791521610, "d1", obs(DBC, 160, 1791521591)) == signer(h("d1"))       # the retry of the same digest returns the same signature


# ---------------------------------------------------------------- tripwire -------------------------------------------------------------------
@pytest.mark.parametrize("bad,why", [(lambda: obs(DBC, 158, 1791521600), "number"), (lambda: {**obs(DBC, 160, 1791521599)}, "timestamp"), (lambda: {**obs(DBC, 160, 1791521600), "blockHash": h("other")}, "hash")])
def test_a_regression_sets_a_persisted_fault_and_every_later_signing_refuses(tmp_path, bad, why):
    d = str(tmp_path / "w0"); st = ws.init_store(d, BIND, B, OWNER)
    sign_cp(st, 4, 138, 1791521610, "d1", obs(DBC, 160, 1791521600))
    e = refusal(lambda: sign_cp(st, 5, 139, 1791521650, "d2", bad()))
    assert e is not None and (e.reason, e.code) == ("WITNESS_FAULTED", "ADAPTER_UNAVAILABLE")
    st.close()
    st2 = ws.open_store(d, BIND, OWNER, signing=False)                          # evidence export keeps working while faulted
    ev = st2.evidence(); assert ev["faulted"] is not None and ev["faultLog"] == [] and ev["faulted"]["reason"] in ("number-regression", "timestamp-regression", "hash-changed")
    LAY.validate_evidence(ev)
    e = refusal(lambda: ws.open_store(d, BIND, OWNER))                           # a restart stays FAULTED (stage 9, after every identity check)
    assert e is not None and e.reason == "WITNESS_FAULTED"
    e = refusal(lambda: st2.sign(type="StateCheckpoint", domain=DOM_S, wsv="2", key="6", effect=cp_effect(140), expires_at="1791521700", digest=h("d3"), signer=signer, observe=lambda: obs(DBC, 170, 1791521700)))
    assert e is not None and e.reason == "WITNESS_FAULTED"


def test_clear_fault_keeps_all_signing_history_and_appends_one_log_row(tmp_path):
    d = str(tmp_path / "w0"); st = ws.init_store(d, BIND, B, OWNER)
    sign_cp(st, 4, 138, 1791521610, "d1", obs(DBC, 160, 1791521600))
    refusal(lambda: sign_cp(st, 5, 139, 1791521650, "d2", obs(DBC, 158, 1791521600)))
    history = json.dumps([st.evidence()["conflicts"], st.evidence()["superseded"]], sort_keys=True)
    with pytest.raises(ValueError):
        st.clear_fault("", lambda: obs(DBC, 158, 1791521605))                    # a note is required
    st.clear_fault("operator clear after a test restart of the DBC", lambda: obs(DBC, 158, 1791521605))
    ev = st.evidence()
    assert ev["faulted"] is None and len(ev["faultLog"]) == 1 and ev["faultLog"][0]["note"].startswith("operator clear")
    assert json.dumps([ev["conflicts"], ev["superseded"]], sort_keys=True) == history          # history untouched
    assert {o["chainId"]: o for o in ev["observations"]}[DBC]["blockNumber"] == "158"          # the new baseline
    LAY.validate_evidence(ev)
    assert sign_cp(st, 5, 139, 1791521650, "d2", obs(DBC, 159, 1791521610)) == signer(h("d2"))
    with pytest.raises(ValueError):
        st.clear_fault("nothing to clear", lambda: obs(DBC, 160, 1791521620))   # not faulted: refused


# ---------------------------------------------------------------- exports (cross-checked against my layout and D50 checkers) ------------------
def test_evidence_validates_against_the_layout_reference_for_a_mixed_history(store):
    t = 1791521500
    for i, (block, lab, exp, n, ts) in enumerate([(136, "A1", t + 60, 150, t), (137, "B", t + 121, 160, t + 61)]):
        store.sign(type="StateCheckpoint", domain=DOM_S, wsv="2", key="4", effect=cp_effect(block), expires_at=str(exp), digest=h(lab), signer=signer, observe=lambda n=n, ts=ts: obs(DBC, n, ts))
    store.sign(type="AccessDecision", domain=DOM_D, wsv="2", key=h("req"), effect=dec_effect(6), expires_at=str(t + 200), digest=h("dec"), signer=signer, observe=lambda: obs(DBC, 170, t + 130))
    store.sign(type="GrantReceipt", domain="0x" + "d4" * 32, wsv="2", key=h("req"), effect={"grantId": h("g"), "gid": "0x" + "cc" * 20, "dataId": h("data"), "keyEpoch": "0", "grantExpiresAt": str(t + 400), "witnessSetVersion": "2",
              "dbcChainId": DBC, "kssc": "0x" + "dd" * 20, "dbcBlockNumber": "159", "dbcBlockHash": h("b159")}, expires_at=None, digest=h("rcpt"), signer=signer, observe=lambda: obs(PBC, 140, t + 100))
    ev = store.evidence()
    LAY.validate_evidence(ev)
    assert ev["owner"] == OWNER and ev["marker"] == {"binding_v2": BIND, "owner": OWNER, "schema": "2"} and ev["binding"] == {"binding_v2": BIND, "document": B}
    assert ev["evidenceSha256"] == LAY.evidence_sha256(ev)


def test_evidence_is_read_only_and_repeatable(store):
    sign_cp(store, 4, 138, 1791521610, "d1", obs(DBC, 159, 1791521590))
    before = state_oracle.logical_snapshot(store.directory)
    a, b = store.evidence(), store.evidence()
    assert a == b and state_oracle.logical_snapshot(store.directory) == before


def test_the_binding_export_validates_and_renders_one_canonical_line(store):
    anchor = {"pbc": {"number": "141", "hash": h("anchor:pbc")}, "dbc": {"number": "161", "hash": h("anchor:dbc")}}
    exp = store.binding_export(anchor)
    LAY.validate_binding_export(exp)
    assert exp["owner"] == OWNER and exp["binding_v2"] == BIND and LAY.render(exp).count("\n") == 1


def test_a_store_with_no_signing_history_exports_empty_evidence(store):
    ev = store.evidence(); LAY.validate_evidence(ev)
    assert ev["conflicts"] == [] and ev["superseded"] == [] and ev["observations"] == [] and ev["faulted"] is None and ev["faultLog"] == []


# ---- found by the worker-store slice (5b): a marker next to MISSING binding rows ---------------------------------------------------------------------
@pytest.mark.parametrize("sql", ["delete from meta", "delete from meta where key in ('binding_v2','binding_v2_doc','owner')"], ids=["all meta rows", "binding rows only"])
@pytest.mark.parametrize("entry", ["open_store", "view_for_export", "init_store"])
def test_a_marker_next_to_missing_binding_rows_is_store_corrupt_and_nothing_is_initialised_over_it(tmp_path, sql, entry):
    """EXPORT-LAYOUTS section 1: `STORE_CORRUPT` includes 'missing binding rows next to a marker'; SUCCESSOR-WIRE section 5: an existing store is opened, never silently initialised. My slice-1 classifier
    called the first variant LEGACY_STATE and the second STORE_MISSING, and `init_store` died with a raw sqlite error; found while writing the worker store's lifecycle."""
    d = str(tmp_path / "w0")
    ws.init_store(d, BIND, B, OWNER).close()
    con = sqlite3.connect(os.path.join(d, "signing.sqlite"))
    con.execute(sql)
    con.commit()
    con.close()
    before = state_oracle.logical_snapshot(d)
    call = {"open_store": lambda: ws.open_store(d, BIND, OWNER), "view_for_export": lambda: ws.view_for_export(d), "init_store": lambda: ws.init_store(d, BIND, B, OWNER)}[entry]
    with pytest.raises(ws.StoreError) as e:
        call()
    assert (e.value.reason, e.value.code) == ("STORE_CORRUPT", "ADAPTER_UNAVAILABLE") and state_oracle.logical_snapshot(d) == before
