"""Read-only exporter CLI of the witness store: `python -m hmbc_protocol.witness_state --state-dir D --witness-index I (--binding | --evidence)` (EXPORT-LAYOUTS section 1). Written BEFORE the CLI
existed. Success: exit 0, stdout one canonical-JSON line plus one LF, stderr empty. Refusal: exit 3, stdout empty, stderr one canonical ExporterError line. Usage: exit 2. No RPC, no write, no key."""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

import pytest

from hmbc_protocol import witness_state as ws
from testtools import state_oracle

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROTO = os.path.join(ROOT, "protocol")
V = os.path.join(PROTO, "f0", "vectors")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(V, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


d50, LAY = _load("d50_reference"), _load("export_layouts_reference")
B = d50.synthetic_binding_document("repaired-f")
BIND = d50.binding_v2(B)
OWNER = "witness:0x" + "11" * 20
DBC = B["chains"]["dbc"]["chainId"]
ANCHOR = {"pbc": {"number": "141", "hash": "0x" + "ab" * 32}, "dbc": {"number": "161", "hash": "0x" + "cd" * 32}}


def h(label):
    return "0x" + hashlib.sha256(label.encode()).hexdigest()


def run_cli(state_dir, *args):
    env = dict(os.environ, PYTHONPATH=PROTO, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-B", "-m", "hmbc_protocol.witness_state", "--state-dir", state_dir, *args], capture_output=True, text=True, env=env)


@pytest.fixture
def sdir(tmp_path):
    st = ws.init_store(str(tmp_path / "witness-2"), BIND, B, OWNER, anchor=ANCHOR)
    st.sign(type="StateCheckpoint", domain="0x" + "a1" * 32, wsv="2", key="4", effect={"authEpoch": "3", "policyVersion": "1", "keyEpoch": "0", "witnessSetVersion": "2", "sourceChainId": "1", "psc": "0x" + "bb" * 20,
            "sourceBlockNumber": "138", "sourceBlockHash": h("b138")}, expires_at="1791521610", digest=h("d1"), signer=lambda d: "0x" + (hashlib.sha256(d.encode()).hexdigest() * 3)[:130],
            observe=lambda: {"chainId": DBC, "blockNumber": "159", "blockHash": h("blk159"), "timestamp": "1791521590"})
    st.close()
    return str(tmp_path)


def test_evidence_success_is_one_canonical_line_equal_to_the_library_output(sdir):
    r = run_cli(sdir, "--witness-index", "2", "--evidence")
    assert r.returncode == 0 and r.stderr == "" and r.stdout.endswith("\n") and r.stdout.count("\n") == 1
    doc = json.loads(r.stdout)
    assert r.stdout == LAY.render(doc) and ": " not in r.stdout and ", " not in r.stdout
    LAY.validate_evidence(doc)
    assert doc == ws.open_store(os.path.join(sdir, "witness-2"), BIND, OWNER, signing=False).evidence()


def test_binding_success_prints_exactly_the_four_members_with_the_stored_anchor(sdir):
    r = run_cli(sdir, "--witness-index", "2", "--binding")
    assert r.returncode == 0 and r.stderr == "" and r.stdout.count("\n") == 1
    doc = json.loads(r.stdout)
    assert set(doc) == {"owner", "binding_v2", "document", "anchor"} and doc["anchor"] == ANCHOR and doc["binding_v2"] == BIND and doc["owner"] == OWNER
    LAY.validate_binding_export(doc)
    assert r.stdout == LAY.render(doc)


def test_the_exporters_write_nothing_and_make_no_rpc(sdir):
    d = os.path.join(sdir, "witness-2")
    before = state_oracle.logical_snapshot(d)
    for flag in ("--evidence", "--binding"):
        assert run_cli(sdir, "--witness-index", "2", flag).returncode == 0
    assert state_oracle.logical_snapshot(d) == before
    src = open(ws.__file__).read()
    assert not any(("import " + m) in src or ("from " + m) in src for m in ("urllib", "socket", "http", "requests", "web3", "hmbc_protocol.chain"))      # the store module has no network client at all


@pytest.mark.parametrize("setup,reason,code", [("missing", "STORE_MISSING", "ADAPTER_UNAVAILABLE"), ("corrupt", "STORE_CORRUPT", "ADAPTER_UNAVAILABLE"), ("legacy", "LEGACY_STATE", "WRONG_DESTINATION")])
def test_refusals_are_one_canonical_error_line_on_stderr_with_exit_3(tmp_path, setup, reason, code):
    import sqlite3
    d = tmp_path / "witness-0"
    if setup == "missing":
        os.makedirs(d); open(d / "INITIALIZED", "w").write("{}")
    elif setup == "corrupt":
        os.makedirs(d); open(d / "signing.sqlite", "wb").write(b"\x00" * 200)
    else:
        os.makedirs(d); con = sqlite3.connect(d / "signing.sqlite"); con.execute("CREATE TABLE records (b TEXT)"); con.execute("INSERT INTO records VALUES ('x')"); con.commit(); con.close()
    for flag in ("--evidence", "--binding"):
        r = run_cli(str(tmp_path), "--witness-index", "0", flag)
        assert r.returncode == 3 and r.stdout == "" and r.stderr.count("\n") == 1
        err = json.loads(r.stderr)
        assert err["reason"] == reason and err["code"] == code and err["message"] and set(err) == {"code", "message", "reason"}
        assert r.stderr == ws.canonical_json(err) + "\n"


def test_a_missing_store_directory_and_a_binding_export_without_an_anchor_are_refused(tmp_path):
    r = run_cli(str(tmp_path), "--witness-index", "1", "--evidence")
    assert r.returncode == 3 and json.loads(r.stderr)["reason"] == "STORE_MISSING"
    ws.init_store(str(tmp_path / "witness-0"), BIND, B, OWNER)                      # initialised without an anchor
    r = run_cli(str(tmp_path), "--witness-index", "0", "--binding")
    assert r.returncode == 3 and json.loads(r.stderr)["reason"] == "STORE_CORRUPT" and r.stdout == ""
    assert run_cli(str(tmp_path), "--witness-index", "0", "--evidence").returncode == 0          # the evidence export does not need an anchor


@pytest.mark.parametrize("args", [[], ["--witness-index", "0"], ["--witness-index", "4", "--evidence"], ["--witness-index", "-1", "--evidence"], ["--witness-index", "x", "--evidence"],
                                  ["--witness-index", "0", "--evidence", "--binding"], ["--evidence"]])
def test_usage_errors_exit_2_and_print_nothing_on_stdout(tmp_path, args):
    r = run_cli(str(tmp_path), *args)
    assert r.returncode == 2 and r.stdout == ""


def test_a_faulted_store_still_exports_evidence(tmp_path):
    st = ws.init_store(str(tmp_path / "witness-0"), BIND, B, OWNER, anchor=ANCHOR)
    eff = {"authEpoch": "3", "policyVersion": "1", "keyEpoch": "0", "witnessSetVersion": "2", "sourceChainId": "1", "psc": "0x" + "bb" * 20, "sourceBlockNumber": "138", "sourceBlockHash": h("b138")}
    sg = lambda d: "0x" + (hashlib.sha256(d.encode()).hexdigest() * 3)[:130]
    st.sign(type="StateCheckpoint", domain="0x" + "a1" * 32, wsv="2", key="4", effect=eff, expires_at="1791521610", digest=h("d1"), signer=sg, observe=lambda: {"chainId": DBC, "blockNumber": "160", "blockHash": h("blk160"), "timestamp": "1791521600"})
    with pytest.raises(ws.StoreError):
        st.sign(type="StateCheckpoint", domain="0x" + "a1" * 32, wsv="2", key="5", effect=eff, expires_at="1791521650", digest=h("d2"), signer=sg, observe=lambda: {"chainId": DBC, "blockNumber": "158", "blockHash": h("blk158"), "timestamp": "1791521600"})
    st.close()
    r = run_cli(str(tmp_path), "--witness-index", "0", "--evidence")
    assert r.returncode == 0 and json.loads(r.stdout)["faulted"] is not None


@pytest.mark.parametrize("bad", [{"pbc": ANCHOR["pbc"]}, {**ANCHOR, "x": ANCHOR["pbc"]}, {**ANCHOR, "pbc": {"number": 141, "hash": ANCHOR["pbc"]["hash"]}}, {**ANCHOR, "dbc": {"number": "161", "hash": "0x" + "CD" * 32}},
                                {**ANCHOR, "dbc": {"number": "161"}}, {**ANCHOR, "dbc": {"number": "0161", "hash": ANCHOR["dbc"]["hash"]}}, "anchor", []])
def test_a_malformed_anchor_is_refused_at_init_and_nothing_is_created(tmp_path, bad):
    d = tmp_path / "witness-0"
    with pytest.raises(ValueError):
        ws.init_store(str(d), BIND, B, OWNER, anchor=bad)
    assert not os.path.exists(d)
