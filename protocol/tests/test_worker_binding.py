"""Worker store D50 rows and `worker_log --binding` (agent 2, F task 2, slice 5b). Written BEFORE hmbc_protocol/worker_binding.py existed and before `worker_log.py` knew `--binding`.

D50 section 5 and SUCCESSOR-WIRE section 5 give the key worker (`<state-dir>/worker/`, `owner = "worker"`, NO key and NO membership check) the same store identity as a witness: `meta` rows `binding_v2`,
`binding_v2_doc`, `owner`, `schema`, the `INITIALIZED` marker, an initialisation order with defined crash points, refusal reasons, and an opt-in read-only export
`python -m hmbc_protocol.worker_log --state-dir D --binding` printing `{owner, binding_v2, document, anchor}`. The carried E code is untouched except for ONE opt-in flag in `worker_log.py`; the E `Worker`
class, its schema, its `deployment` fingerprint row and the default export stay as they were (tested, and the default export is compared with the E-era file when git can show it).

What is established: the lifecycle (fresh, interrupted at every injected crash point, open, every refusal with the logical snapshot unchanged), that the E `Worker` runs unchanged on a bound directory, that an
E-created EMPTY store is bound on first open while one with rows is refused LEGACY_STATE, and the exporter contract. NOT established: anything about a running adapter (none exists yet), a real chain, or power loss
(only process death is modelled, here by an exception at the hook point; slice 1 tests real process death for the witness store).
"""
import hashlib
import importlib.util
import json
import os
import sqlite3
import stat
import subprocess
import sys

import pytest

from hmbc_protocol import worker_binding as wb
from hmbc_protocol import witness_state as ws
from hmbc_protocol.worker import Worker
from testtools import state_oracle

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
V = os.path.join(ROOT, "protocol", "f0", "vectors")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(V, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


d50, LAY = _load("d50_reference"), _load("export_layouts_reference")
B = d50.synthetic_binding_document("repaired-f")
BIND = d50.binding_v2(B)
ANCHOR = {"pbc": {"number": "300", "hash": "0x" + "ab" * 32}, "dbc": {"number": "400", "hash": "0x" + "cd" * 32}}
DEPLOY = json.load(open(os.path.join(ROOT, "protocol", "tests", "fixtures", "deployment-agent1-91add8c-v1-repaired-e.json")))


class StubLed:
    """All the E Worker reads from its ledger when it opens its database is `led.deployment`."""
    deployment = DEPLOY


def e_worker(directory):
    return Worker(StubLed(), directory, lambda: 0)


def snap(d):
    return state_oracle.logical_snapshot(d, db_name="worker.sqlite")


class Crash(Exception):
    pass


def crash_at(point):
    def hook(p):
        if p == point:
            raise Crash(p)
    return hook


def meta(d):
    con = sqlite3.connect("file:%s?mode=ro" % os.path.join(d, "worker.sqlite"), uri=True)
    try:
        return dict(con.execute("select key, value from meta"))
    finally:
        con.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the lifecycle
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_a_fresh_directory_is_bound_with_the_identity_rows_the_marker_and_the_private_modes(tmp_path):
    d = str(tmp_path / "worker")
    wb.bind_worker_dir(d, BIND, B, ANCHOR)
    assert stat.S_IMODE(os.stat(d).st_mode) == 0o700 and stat.S_IMODE(os.stat(os.path.join(d, "worker.sqlite")).st_mode) == 0o600
    m = meta(d)
    assert (m["binding_v2"], m["owner"], m["schema"]) == (BIND, "worker", "2") and json.loads(m["binding_v2_doc"]) == B and json.loads(m["anchor"]) == ANCHOR
    assert m["binding_v2_doc"] == ws.canonical_json(B) and m["anchor"] == ws.canonical_json(ANCHOR)                 # canonical_json text, as D50 section 2 says
    assert json.loads(open(os.path.join(d, "INITIALIZED")).read()) == {"binding_v2": BIND, "owner": "worker", "schema": "2"}
    assert open(os.path.join(d, "INITIALIZED")).read() == ws.canonical_json({"binding_v2": BIND, "owner": "worker", "schema": "2"})
    assert not os.path.exists(os.path.join(d, "INITIALIZED.tmp")) and os.path.exists(os.path.join(d, ".init.lock"))
    con = sqlite3.connect(os.path.join(d, "worker.sqlite"))
    try:
        assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert {r[0] for r in con.execute("select name from sqlite_master where type='table'")} >= {"records", "releases", "events", "meta"}     # the E schema, unchanged
    finally:
        con.close()


def test_the_carried_e_worker_runs_unchanged_on_a_bound_directory_and_keeps_its_v1_fingerprint(tmp_path):
    d = str(tmp_path / "worker")
    wb.bind_worker_dir(d, BIND, B, ANCHOR)
    w = e_worker(d)
    fp = w.db.execute("select value from meta where key='deployment'").fetchone()[0]
    dep = DEPLOY["chains"]
    want = hashlib.sha256(json.dumps({"pbc": [dep["pbc"]["chainId"], dep["pbc"]["contracts"]["PSC"], dep["pbc"]["contracts"]["RSC"]],
                                      "dbc": [dep["dbc"]["chainId"], dep["dbc"]["contracts"]["KSSC"], dep["dbc"]["contracts"]["ACSC"]]}, sort_keys=True).encode()).hexdigest()
    assert fp == want                                                                             # the same formula, the same bytes
    assert meta(d)["binding_v2"] == BIND
    w.db.close()
    wb.bind_worker_dir(d, BIND, B, ANCHOR)                                                        # and the directory still opens as bound after the E worker used it


def test_binding_an_already_bound_directory_is_an_open_that_writes_nothing(tmp_path):
    d = str(tmp_path / "worker")
    wb.bind_worker_dir(d, BIND, B, ANCHOR)
    before = snap(d)
    wb.bind_worker_dir(d, BIND, B, ANCHOR)
    wb.bind_worker_dir(d, BIND, B, ANCHOR)
    assert snap(d) == before


def test_an_e_created_empty_store_is_bound_on_first_open_and_keeps_its_deployment_row(tmp_path):
    d = str(tmp_path / "worker")
    w = e_worker(d)                                                                               # what an E run leaves: schema and the v1 fingerprint, no records
    fp = w.db.execute("select value from meta where key='deployment'").fetchone()[0]
    w.db.close()
    wb.bind_worker_dir(d, BIND, B, ANCHOR)
    m = meta(d)
    assert m["deployment"] == fp and m["binding_v2"] == BIND and m["owner"] == "worker"
    assert os.path.exists(os.path.join(d, "INITIALIZED"))


@pytest.mark.parametrize("table_sql", [
    "insert into events(type, request_digest, grant_id, gid, data_id, timestamp) values('RELEASE_INTENT','0x1','0x2','0x3','0x4',5)",
    "insert into records values('0x1','0x2','0x3','{}','0x4','0x5')",
    "insert into releases values('0x1','0x2','0x3','0x4','0x5','0','0x6','0x7',9,8,'unknown',0,0)",
], ids=["events", "records", "releases"])
def test_an_e_created_store_with_rows_is_refused_as_unbound_legacy_state_and_nothing_changes(tmp_path, table_sql):
    d = str(tmp_path / "worker")
    w = e_worker(d)
    w.db.execute(table_sql)
    w.db.close()
    before = snap(d)
    with pytest.raises(ws.StoreError) as e:
        wb.bind_worker_dir(d, BIND, B, ANCHOR)
    assert (e.value.reason, e.value.code) == ("LEGACY_STATE", "WRONG_DESTINATION") and snap(d) == before and not os.path.exists(os.path.join(d, "INITIALIZED"))
    assert "binding_v2" not in meta(d)


@pytest.mark.parametrize("point", ["after_dir", "after_db_commit", "after_tmp_marker", "after_rename"])
def test_every_injected_crash_point_leaves_a_directory_a_restart_completes_to_the_same_state(tmp_path, point):
    clean = str(tmp_path / "clean")
    wb.bind_worker_dir(clean, BIND, B, ANCHOR)
    d = str(tmp_path / "crashed")
    with pytest.raises(Crash):
        wb.bind_worker_dir(d, BIND, B, ANCHOR, crash_hook=crash_at(point))
    wb.bind_worker_dir(d, BIND, B, ANCHOR)                                                        # the restart
    assert meta(d) == meta(clean) and open(os.path.join(d, "INITIALIZED")).read() == open(os.path.join(clean, "INITIALIZED")).read()
    assert not os.path.exists(os.path.join(d, "INITIALIZED.tmp"))
    e_worker(d).db.close()                                                                        # and the E worker opens it


def test_a_crash_after_the_database_commit_leaves_binding_rows_and_no_marker_and_the_export_calls_it_never_initialised(tmp_path):
    d = str(tmp_path / "worker")
    with pytest.raises(Crash):
        wb.bind_worker_dir(d, BIND, B, ANCHOR, crash_hook=crash_at("after_db_commit"))
    assert "binding_v2" in meta(d) and not os.path.exists(os.path.join(d, "INITIALIZED"))
    with pytest.raises(ws.StoreError) as e:
        wb.view_for_export(d)
    assert e.value.reason == "STORE_MISSING"


def test_an_interrupted_initialisation_of_another_identity_is_refused_not_completed(tmp_path):
    d = str(tmp_path / "worker")
    with pytest.raises(Crash):
        wb.bind_worker_dir(d, BIND, B, ANCHOR, crash_hook=crash_at("after_db_commit"))
    before = snap(d)
    with pytest.raises(ws.StoreError) as e:
        wb.bind_worker_dir(d, "ab" * 32, B, ANCHOR)
    assert e.value.reason == "BINDING_MISMATCH" and snap(d) == before and not os.path.exists(os.path.join(d, "INITIALIZED"))


def test_a_store_bound_to_another_deployment_is_refused_and_nothing_changes(tmp_path):
    d = str(tmp_path / "worker")
    wb.bind_worker_dir(d, BIND, B, ANCHOR)
    before = snap(d)
    with pytest.raises(ws.StoreError) as e:
        wb.bind_worker_dir(d, d50.binding_v2(d50.synthetic_binding_document("repaired-e")), d50.synthetic_binding_document("repaired-e"), ANCHOR)
    assert (e.value.reason, e.value.code) == ("BINDING_MISMATCH", "WRONG_DESTINATION") and snap(d) == before


def _retarget_owner(d, owner):
    con = sqlite3.connect(os.path.join(d, "worker.sqlite"))
    con.execute("update meta set value=? where key='owner'", (owner,))
    con.commit()
    con.close()
    open(os.path.join(d, "INITIALIZED"), "w").write(ws.canonical_json({"binding_v2": BIND, "owner": owner, "schema": "2"}))


def test_a_store_of_another_role_is_refused_owner_mismatch(tmp_path):
    d = str(tmp_path / "worker")
    wb.bind_worker_dir(d, BIND, B, ANCHOR)
    _retarget_owner(d, "witness:0x" + "11" * 20)
    before = snap(d)
    with pytest.raises(ws.StoreError) as e:
        wb.bind_worker_dir(d, BIND, B, ANCHOR)
    assert e.value.reason == "OWNER_MISMATCH" and snap(d) == before


def test_a_marker_without_a_database_is_store_missing(tmp_path):
    d = str(tmp_path / "worker")
    os.makedirs(d, mode=0o700)
    open(os.path.join(d, "INITIALIZED"), "w").write("{}")
    with pytest.raises(ws.StoreError) as e:
        wb.bind_worker_dir(d, BIND, B, ANCHOR)
    assert (e.value.reason, e.value.code) == ("STORE_MISSING", "ADAPTER_UNAVAILABLE")


@pytest.mark.parametrize("damage", ["garbage database", "marker differs", "rows without marker", "marker unreadable"])
def test_a_corrupt_store_is_refused_store_corrupt_and_a_replacement_is_never_created(tmp_path, damage):
    d = str(tmp_path / "worker")
    wb.bind_worker_dir(d, BIND, B, ANCHOR)
    if damage == "garbage database":
        for suffix in ("", "-wal", "-shm"):
            p = os.path.join(d, "worker.sqlite" + suffix)
            if os.path.exists(p):
                os.remove(p)
        open(os.path.join(d, "worker.sqlite"), "wb").write(b"this is not a database" * 50)
    elif damage == "marker differs":
        open(os.path.join(d, "INITIALIZED"), "w").write(ws.canonical_json({"binding_v2": "00" * 32, "owner": "worker", "schema": "2"}))
    elif damage == "rows without marker":
        e_worker(d).db.execute("insert into events(type, request_digest, grant_id, gid, data_id, timestamp) values('RELEASE_INTENT','0x1','0x2','0x3','0x4',5)")
        os.remove(os.path.join(d, "INITIALIZED"))
    else:
        open(os.path.join(d, "INITIALIZED"), "w").write("not json")
    before = open(os.path.join(d, "worker.sqlite"), "rb").read()
    with pytest.raises(ws.StoreError) as e:
        wb.bind_worker_dir(d, BIND, B, ANCHOR)
    assert e.value.reason == "STORE_CORRUPT" and open(os.path.join(d, "worker.sqlite"), "rb").read() == before


@pytest.mark.parametrize("sql", ["delete from meta", "delete from meta where key in ('binding_v2','binding_v2_doc','owner')"], ids=["all meta rows", "binding rows only"])
@pytest.mark.parametrize("entry", ["bind", "export"])
def test_a_marker_next_to_missing_binding_rows_is_store_corrupt_and_nothing_is_initialised_over_it(tmp_path, sql, entry):
    """EXPORT-LAYOUTS section 1: 'missing binding rows next to a marker' is STORE_CORRUPT (the same gap my slice-1 witness classifier had, fixed there in this slice)."""
    d = str(tmp_path / "state" / "worker")
    wb.bind_worker_dir(d, BIND, B, ANCHOR)
    con = sqlite3.connect(os.path.join(d, "worker.sqlite"))
    con.execute(sql)
    con.commit()
    con.close()
    before = snap(d)
    with pytest.raises(ws.StoreError) as e:
        (wb.bind_worker_dir(d, BIND, B, ANCHOR) if entry == "bind" else wb.view_for_export(d))
    assert (e.value.reason, e.value.code) == ("STORE_CORRUPT", "ADAPTER_UNAVAILABLE") and snap(d) == before


def test_a_database_that_opens_but_fails_integrity_check_is_corrupt(tmp_path):
    """A corruption that leaves the identity rows readable: only PRAGMA integrity_check can find it (the test searches the pages for one and asserts it found one)."""
    d = str(tmp_path / "worker")
    wb.bind_worker_dir(d, BIND, B, ANCHOR)
    w = e_worker(d)
    for i in range(400):
        w.db.execute("insert into events(type, request_digest, grant_id, gid, data_id, timestamp) values('RELEASE_INTENT',?,?,?,?,?)", ("0x%064x" % i, "0x%064x" % (i + 1), "0x%040x" % i, "0x%064x" % (i + 2), i))
    w.db.execute("pragma wal_checkpoint(TRUNCATE)")
    w.db.close()
    db = os.path.join(d, "worker.sqlite")
    con = sqlite3.connect(db)
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    ps, pc = con.execute("PRAGMA page_size").fetchone()[0], con.execute("PRAGMA page_count").fetchone()[0]
    con.close()
    found = False
    for page, off in [(pg, o) for pg in range(2, pc + 1) for o in (0, 1, 3, 5, 8, 12, ps // 2, ps - 8)]:        # structure (the page header, cell pointers) is what integrity_check sees
        good = open(db, "rb").read()
        with open(db, "r+b") as f:
            f.seek((page - 1) * ps + off)
            f.write(b"\xff" * 8)
        try:
            ro = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
            ok = ro.execute("PRAGMA integrity_check").fetchone()[0] != "ok" and {"binding_v2", "owner"} <= {r[0] for r in ro.execute("SELECT key FROM meta")}
            ro.close()
        except sqlite3.DatabaseError:
            ok = False
        if ok:
            found = True
            break
        open(db, "wb").write(good)
    assert found, "no page corruption left the identity rows readable while failing integrity_check"
    before = open(db, "rb").read()
    with pytest.raises(ws.StoreError) as e:
        wb.bind_worker_dir(d, BIND, B, ANCHOR)
    assert (e.value.reason, e.value.code) == ("STORE_CORRUPT", "ADAPTER_UNAVAILABLE") and open(db, "rb").read() == before


def test_malformed_arguments_are_a_value_error_and_create_nothing(tmp_path):
    d = str(tmp_path / "worker")
    for bad in (dict(binding_v2="xyz", document=B, anchor=ANCHOR), dict(binding_v2=BIND, document="x", anchor=ANCHOR), dict(binding_v2=BIND, document=B, anchor={"pbc": {}}),
                dict(binding_v2=BIND, document=B, anchor=None)):
        with pytest.raises(ValueError):
            wb.bind_worker_dir(d, **bad)
    assert not os.path.exists(d)


def test_a_preexisting_directory_is_made_private_by_binding_it(tmp_path):
    d = str(tmp_path / "worker")
    os.makedirs(d, mode=0o755)
    os.chmod(d, 0o755)
    wb.bind_worker_dir(d, BIND, B, ANCHOR)
    assert stat.S_IMODE(os.stat(d).st_mode) == 0o700
    e_worker(d).db.close()                                                                         # the E worker refuses a directory open to group or other: it accepts this one


def test_concurrent_first_binds_of_one_directory_all_succeed_and_leave_one_identity(tmp_path):
    d = str(tmp_path / "worker")
    code = ("import sys, json\nfrom hmbc_protocol import worker_binding as wb\nB = json.loads(sys.argv[2]); A = json.loads(sys.argv[3])\nwb.bind_worker_dir(sys.argv[1], sys.argv[4], B, A)\n")
    procs = [subprocess.Popen([sys.executable, "-B", "-c", code, d, json.dumps(B), json.dumps(ANCHOR), BIND], cwd=os.path.join(ROOT, "protocol"), env=dict(os.environ, PYTHONPATH=os.path.join(ROOT, "protocol")),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(6)]
    outs = [p.communicate(timeout=120) for p in procs]
    assert [p.returncode for p in procs] == [0] * 6, [o[1].decode()[-300:] for o in outs]
    assert meta(d)["binding_v2"] == BIND and os.path.exists(os.path.join(d, "INITIALIZED"))


@pytest.mark.parametrize("what", ["anchor row missing", "document row tampered", "document row not json"])
def test_the_export_refuses_binding_rows_that_do_not_fit_together(tmp_path, what):
    sd = str(tmp_path / "state")
    d = os.path.join(sd, "worker")
    wb.bind_worker_dir(d, BIND, B, ANCHOR)
    con = sqlite3.connect(os.path.join(d, "worker.sqlite"))
    if what == "anchor row missing":
        con.execute("delete from meta where key='anchor'")
    elif what == "document row tampered":
        other = json.loads(ws.canonical_json(B))
        other["interfaceVersion"] = "v9"
        con.execute("update meta set value=? where key='binding_v2_doc'", (ws.canonical_json(other),))
    else:
        con.execute("update meta set value='not json' where key='binding_v2_doc'")
    con.commit()
    con.close()
    r = run_cli(sd, "--binding")
    assert r.returncode == 3 and r.stdout == "" and json.loads(r.stderr)["reason"] == "STORE_CORRUPT"


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the opt-in exporter
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def run_cli(state_dir, *extra):
    return subprocess.run([sys.executable, "-B", "-m", "hmbc_protocol.worker_log", "--state-dir", state_dir, *extra], capture_output=True, text=True, cwd=os.path.join(ROOT, "protocol"),
                          env=dict(os.environ, PYTHONPATH=os.path.join(ROOT, "protocol")), timeout=60)


def test_the_binding_export_prints_exactly_the_four_members_on_one_canonical_line(tmp_path):
    sd = str(tmp_path / "state")
    wb.bind_worker_dir(os.path.join(sd, "worker"), BIND, B, ANCHOR)
    r = run_cli(sd, "--binding")
    assert r.returncode == 0 and r.stderr == ""
    doc = json.loads(r.stdout)
    assert set(doc) == {"owner", "binding_v2", "document", "anchor"} and doc["owner"] == "worker" and doc["binding_v2"] == BIND and doc["document"] == B and doc["anchor"] == ANCHOR
    assert r.stdout == LAY.render(doc) and r.stdout.endswith("\n") and r.stdout.count("\n") == 1 and ": " not in r.stdout and ", " not in r.stdout
    LAY.validate_binding_export(doc)                                                              # my layout checker
    assert doc["binding_v2"] == d50.binding_v2(doc["document"])


def test_the_export_is_read_only_and_creates_nothing_and_prints_no_token_or_row(tmp_path):
    sd = str(tmp_path / "state")
    d = os.path.join(sd, "worker")
    wb.bind_worker_dir(d, BIND, B, ANCHOR)
    before_files, before_snap = sorted(f for f in os.listdir(d) if not f.endswith(("-shm", "-wal"))), snap(d)
    for _ in range(2):
        assert run_cli(sd, "--binding").returncode == 0
    assert sorted(f for f in os.listdir(d) if not f.endswith(("-shm", "-wal"))) == before_files and snap(d) == before_snap


@pytest.mark.parametrize("case", ["missing directory", "never initialised", "legacy store", "corrupt database", "marker differs"])
def test_every_exporter_refusal_is_one_canonical_stderr_line_and_exit_3(tmp_path, case):
    sd = str(tmp_path / "state")
    d = os.path.join(sd, "worker")
    expect = None
    if case == "missing directory":
        os.makedirs(sd)
        expect = ("STORE_MISSING", "ADAPTER_UNAVAILABLE")
    elif case == "never initialised":
        with pytest.raises(Crash):
            wb.bind_worker_dir(d, BIND, B, ANCHOR, crash_hook=crash_at("after_db_commit"))
        expect = ("STORE_MISSING", "ADAPTER_UNAVAILABLE")
    elif case == "legacy store":
        w = e_worker(d)
        w.db.execute("insert into events(type, request_digest, grant_id, gid, data_id, timestamp) values('RELEASE_INTENT','0x1','0x2','0x3','0x4',5)")
        w.db.close()
        expect = ("LEGACY_STATE", "WRONG_DESTINATION")
    elif case == "corrupt database":
        wb.bind_worker_dir(d, BIND, B, ANCHOR)
        for suffix in ("", "-wal", "-shm"):
            p = os.path.join(d, "worker.sqlite" + suffix)
            if os.path.exists(p):
                os.remove(p)
        open(os.path.join(d, "worker.sqlite"), "wb").write(b"garbage" * 100)
        expect = ("STORE_CORRUPT", "ADAPTER_UNAVAILABLE")
    else:
        wb.bind_worker_dir(d, BIND, B, ANCHOR)
        open(os.path.join(d, "INITIALIZED"), "w").write(ws.canonical_json({"binding_v2": "00" * 32, "owner": "worker", "schema": "2"}))
        expect = ("STORE_CORRUPT", "ADAPTER_UNAVAILABLE")
    r = run_cli(sd, "--binding")
    assert r.returncode == 3 and r.stdout == ""
    line = json.loads(r.stderr)
    assert set(line) == {"code", "message", "reason"} and (line["reason"], line["code"]) == expect and r.stderr == LAY.error_line(line["reason"], line["message"])


def test_the_export_reads_only_the_worker_subdirectory_of_the_named_state_directory(tmp_path):
    sd = str(tmp_path / "state")
    os.makedirs(sd)
    wb.bind_worker_dir(sd, BIND, B, ANCHOR)                                                       # a bound store in the directory ITSELF (the E direct layout) is not what --binding reads
    r = run_cli(sd, "--binding")
    assert r.returncode == 3 and json.loads(r.stderr)["reason"] == "STORE_MISSING"


def test_the_default_export_without_the_flag_is_unchanged_byte_for_byte(tmp_path):
    """The default output of the CARRIED E exporter is compared with the E-era file at the commit before this slice (when git can show it) on the same directory."""
    d = str(tmp_path / "state" / "worker")
    w = e_worker(d)
    w.db.execute("insert into events(type, request_digest, grant_id, gid, data_id, timestamp) values('RELEASE_INTENT','0x1','0x2','0x3','0x4',5)")
    w.db.close()
    new = run_cli(str(tmp_path / "state"))
    assert new.returncode == 0 and json.loads(new.stdout)["schemaVersion"] == "hmbc-worker-log/v0" and new.stdout.startswith("{\n \"schemaVersion\"")
    try:
        old_src = subprocess.check_output(["git", "-C", ROOT, "show", "b7c86b6:protocol/hmbc_protocol/worker_log.py"], stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pytest.skip("the E-era worker_log.py is not reachable from here (a disposable copy has no repository)")
    scratch = tmp_path / "old"
    (scratch / "hmbc_protocol").mkdir(parents=True)
    (scratch / "hmbc_protocol" / "__init__.py").write_text("")
    (scratch / "hmbc_protocol" / "worker_log.py").write_bytes(old_src)
    old = subprocess.run([sys.executable, "-B", "-m", "hmbc_protocol.worker_log", "--state-dir", str(tmp_path / "state")], capture_output=True, text=True, cwd=str(scratch),
                         env=dict(os.environ, PYTHONPATH=str(scratch)), timeout=60)
    assert old.returncode == 0 and old.stdout == new.stdout and old.stderr == new.stderr


def test_the_flag_is_not_accepted_with_unknown_company_and_usage_errors_are_exit_2(tmp_path):
    assert run_cli(str(tmp_path), "--binding", "--nonsense").returncode == 2


def test_the_module_reads_no_clock_no_network_and_no_key():
    import ast
    src = open(os.path.join(ROOT, "protocol", "hmbc_protocol", "worker_binding.py")).read()
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            mods.add((node.module or "").split(".")[0])
    assert not mods & {"time", "datetime", "random", "socket", "urllib", "http", "subprocess", "eth_account", "eth_keys"}, mods
