"""The successor adapter's command line (agent 2, F task 2 slice 10a). Written BEFORE hmbc_protocol/adapter_v2_main.py existed.

`python -m hmbc_protocol.adapter_v2_main --deployment F --abi-dir D --schema S --schema-sha256 H --schema-revision v2|v2.1 --state-dir D` pins ONE deployment, loads the hash-pinned ABI files and the exact
published schema, runs the startup order of `adapter_v2_start` against the REAL chains through `RpcBindingView`, and then serves JSON lines on stdin/stdout with the key-worker operations backed by the real
ledger and EVERY response checked against the published schema (check_responses stays on). The four witness operations are NOT wired here (no witness processes or transport exist yet): they answer
ADAPTER_UNAVAILABLE "not wired". Startup failures print ONE JSON object on stderr, nothing on stdout, exit 2, no traceback.
This file: the no-node cases (argument and file validation, an unreachable node, no state left behind) as real subprocesses; the live cases against a real deployment are in
test_rpc_binding_view_live.py (last tests).
"""
import json
import os
import socket
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROTO = os.path.join(ROOT, "protocol")
FX = os.path.join(PROTO, "tests", "fixtures")
ABI_DIR = os.path.join(FX, "agent1-85c59f5-abi")
SCHEMA = os.path.join(FX, "agent3-v2.1-hmbc.schema.json")
SCHEMA_SHA = "d43c3a9a4cbb10214135afb767a2adc109da462f88bd11a81a8c8955d44fd1f3"
F2 = os.path.join(FX, "agent1-85c59f5-f-base-deployment.json")


def run(args, stdin="", env=None):
    e = {"PYTHONPATH": PROTO, "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}
    e.update(env or {})
    return subprocess.run([sys.executable, "-B", "-m", "hmbc_protocol.adapter_v2_main", *args], input=stdin, capture_output=True, text=True, cwd=PROTO, env=e, timeout=60)


def good(tmp_path, **over):
    a = {"--deployment": F2, "--abi-dir": ABI_DIR, "--schema": SCHEMA, "--schema-sha256": SCHEMA_SHA, "--schema-revision": "v2", "--state-dir": str(tmp_path / "state")}
    a.update(over)
    return [x for kv in a.items() if kv[1] is not None for x in kv]


def refused(p):
    """Exactly one JSON object on stderr, an `error` with a code and a message, nothing on stdout, exit 2, no traceback."""
    assert p.returncode == 2 and p.stdout == "" and "Traceback" not in p.stderr, (p.returncode, p.stdout, p.stderr)
    lines = p.stderr.strip().splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert set(obj) == {"error"} and set(obj["error"]) >= {"code", "message"}
    return obj["error"]


@pytest.mark.parametrize("drop", ["--deployment", "--abi-dir", "--schema", "--schema-sha256", "--schema-revision", "--state-dir"])
def test_every_argument_is_required_and_nothing_is_defaulted(tmp_path, drop):
    args = good(tmp_path, **{drop: None})
    p = run(args)
    assert p.returncode == 2 and p.stdout == "" and "Traceback" not in p.stderr
    assert "the following arguments are required" in p.stderr and drop in p.stderr          # argparse refused it: it was not defaulted and then failed for another reason
    assert not os.path.exists(tmp_path / "state")


def test_a_schema_revision_other_than_v2_or_v2_1_is_refused(tmp_path):
    for bad in ("v1", "v3", "latest", ""):
        p = run(good(tmp_path, **{"--schema-revision": bad}))
        assert p.returncode == 2 and p.stdout == "" and "Traceback" not in p.stderr, bad


def test_a_schema_file_that_does_not_hash_to_the_pinned_value_is_refused_before_anything_else(tmp_path):
    err = refused(run(good(tmp_path, **{"--schema-sha256": "0" * 64})))
    assert err["code"] == "MALFORMED" and "schema" in err["message"]
    assert not os.path.exists(tmp_path / "state")
    changed = tmp_path / "schema.json"
    changed.write_bytes(open(SCHEMA, "rb").read() + b" ")
    assert refused(run(good(tmp_path, **{"--schema": str(changed)})))["code"] == "MALFORMED"


def test_a_malformed_schema_hash_argument_is_refused(tmp_path):
    for bad in ("zz", "D43C3A9A" + "0" * 56, "0" * 63):
        p = run(good(tmp_path, **{"--schema-sha256": bad}))
        assert p.returncode == 2 and p.stdout == "" and "Traceback" not in p.stderr


@pytest.mark.parametrize("content,why", [(b'{"a": 1, "a": 2}', "duplicate key"), (b'{"a": NaN}', "NaN"), (b"\xff\xfe", "not UTF-8"), (b"{", "truncated"), (b"[]", "not an object"), (b"{}", "not a deployment")])
def test_a_deployment_file_that_is_not_strict_json_or_not_a_deployment_is_refused_cleanly(tmp_path, content, why):
    f = tmp_path / "dep.json"
    f.write_bytes(content)
    err = refused(run(good(tmp_path, **{"--deployment": str(f)})))
    assert err["code"] == "MALFORMED", why
    assert not os.path.exists(tmp_path / "state")


def test_a_missing_deployment_schema_or_abi_directory_is_refused_cleanly(tmp_path):
    for flag, value in (("--deployment", str(tmp_path / "nope.json")), ("--schema", str(tmp_path / "nope.json")), ("--abi-dir", str(tmp_path / "nope"))):
        assert refused(run(good(tmp_path, **{flag: value})))["code"] == "MALFORMED", flag


def test_an_abi_directory_whose_files_do_not_hash_to_the_manifest_is_refused(tmp_path):
    d = tmp_path / "abi"
    d.mkdir()
    for n in os.listdir(ABI_DIR):
        (d / n).write_bytes(open(os.path.join(ABI_DIR, n), "rb").read())
    (d / "PSC.json").write_bytes((d / "PSC.json").read_bytes() + b" ")
    assert refused(run(good(tmp_path, **{"--abi-dir": str(d)})))["code"] == "MALFORMED"
    assert not os.path.exists(tmp_path / "state")


def test_the_manifest_marker_must_agree_with_the_explicit_schema_revision(tmp_path):
    m = json.load(open(F2))
    m["schemaVersion"] = "hmbc-ledger-deployment/v2.1"
    f = tmp_path / "dep.json"
    f.write_text(json.dumps(m))
    assert refused(run(good(tmp_path, **{"--deployment": str(f), "--schema-revision": "v2"})))["code"] == "MALFORMED"


def test_an_unreachable_node_is_ledger_unreachable_and_leaves_no_state_behind(tmp_path):
    with socket.socket() as s:                                            # a port nothing listens on
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    m = json.load(open(F2))
    m["chains"]["pbc"]["rpcUrl"] = f"http://127.0.0.1:{port}"
    m["chains"]["dbc"]["rpcUrl"] = f"http://127.0.0.1:{port}"
    f = tmp_path / "dep.json"
    f.write_text(json.dumps(m))
    err = refused(run(good(tmp_path, **{"--deployment": str(f)})))
    assert err["code"] == "ADAPTER_UNAVAILABLE" and err.get("reason") == "LEDGER_UNREACHABLE"
    assert not os.path.exists(tmp_path / "state" / "worker")


def test_a_non_loopback_rpc_url_is_refused_before_any_connection(tmp_path):
    m = json.load(open(F2))
    m["chains"]["pbc"]["rpcUrl"] = "http://192.0.2.1:8545"
    f = tmp_path / "dep.json"
    f.write_text(json.dumps(m))
    err = refused(run(good(tmp_path, **{"--deployment": str(f)})))
    assert err["code"] == "MALFORMED"


def test_a_state_directory_that_group_or_other_can_reach_is_refused(tmp_path):
    d = tmp_path / "state"
    d.mkdir(mode=0o755)
    os.chmod(d, 0o755)
    err = refused(run(good(tmp_path)))
    assert err["code"] == "MALFORMED" and "state" in err["message"]


def test_the_module_reads_no_environment_and_has_no_clock_thread_or_socket_of_its_own():
    src = open(os.path.join(PROTO, "hmbc_protocol", "adapter_v2_main.py")).read()
    for banned in ("os.environ", "import time", "datetime", "import threading", "import socket", "import random"):
        assert banned not in src, banned


def test_a_schema_file_that_hashes_correctly_but_is_not_json_is_refused(tmp_path):
    import hashlib
    f = tmp_path / "schema.json"
    f.write_bytes(b"not json")
    err = refused(run(good(tmp_path, **{"--schema": str(f), "--schema-sha256": hashlib.sha256(b"not json").hexdigest()})))
    assert err["code"] == "MALFORMED" and "not JSON" in err["message"]


def test_a_state_path_that_is_a_file_is_refused(tmp_path):
    f = tmp_path / "state"
    f.write_text("x")
    err = refused(run(good(tmp_path)))
    assert err["code"] == "MALFORMED" and "not a directory" in err["message"]


def test_the_refusal_names_a_reason_for_a_stage_refusal_and_the_closed_code_of_that_reason(tmp_path):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    m = json.load(open(F2))
    m["chains"]["pbc"]["rpcUrl"] = m["chains"]["dbc"]["rpcUrl"] = f"http://127.0.0.1:{port}"
    f = tmp_path / "dep.json"
    f.write_text(json.dumps(m))
    p = run(good(tmp_path, **{"--deployment": str(f)}))
    assert p.returncode == 2
    assert json.loads(p.stderr)["error"] == {"code": "ADAPTER_UNAVAILABLE", "message": json.loads(p.stderr)["error"]["message"], "reason": "LEDGER_UNREACHABLE"}


def test_build_context_passes_the_pinned_manifest_the_explicit_revision_the_schema_and_a_worker_factory_to_the_startup_order(tmp_path):
    import argparse
    sys.path.insert(0, PROTO)
    from hmbc_protocol import adapter_v2_main as main

    seen = {}

    def fake_start(**kw):
        seen.update(kw)
        return "CONTEXT"
    for rev in ("v2", "v2.1"):
        args = argparse.Namespace(deployment=F2, abi_dir=ABI_DIR, schema=SCHEMA, schema_sha256=SCHEMA_SHA, schema_revision=rev, state_dir=str(tmp_path / "state"))
        assert main.build_context(args, start=fake_start) == "CONTEXT"
        assert seen["schema_revision"] == rev and seen["manifest"] == json.load(open(F2)) and seen["state_dir"] == str(tmp_path / "state")
        assert seen["schema"] == json.load(open(SCHEMA)) and callable(seen["worker_factory"]) and set(seen) == {"manifest", "schema_revision", "chain_view", "state_dir", "worker_factory", "schema"}
    assert "check_responses" not in seen                                  # the default (on) is kept: nothing in the command line can switch response checking off
