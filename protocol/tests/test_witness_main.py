"""The witness process (agent 2, F task 3 slice 11a). Written BEFORE hmbc_protocol/witness_main.py existed.

`python -m hmbc_protocol.witness_main --deployment F --abi-dir D --index I --key-label witness-N --state-dir D [--allow-governance FILE]` is ONE witness as ONE OS process: D50 stages 1 to 8 as the witness role
against the real chains, its own durable store `<state>/witness-<I>/`, the real `RpcWitnessView`, and a JSON-lines server on stdin/stdout:
  request   {"schemaVersion": "hmbc-witness-rpc/v1", "id": int, "round": 1|2, "kind": "checkpoint|decision|receipt|governance", "message": {...}}
  response  {"schemaVersion": "hmbc-witness-rpc/v1", "id": int|null, "reply": {"type": "signature", "message", "signature"} | {"type": "error", "code", "reason", "recorded"}}
The reply is exactly the pool's reply shape. KEY CUSTODY IS TEST-ONLY: the key is derived from `--key-label` (the manifest must declare a TEST-ONLY synthetic key derivation, and the derived address must be the
manifest's witness `--index`). This file: the no-node cases as real subprocesses (arguments, files, an unreachable node, no state left behind); the live cases against a real deployment are in
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
F2 = os.path.join(FX, "agent1-85c59f5-f-base-deployment.json")


def run(args, stdin=""):
    return subprocess.run([sys.executable, "-B", "-m", "hmbc_protocol.witness_main", *args], input=stdin, capture_output=True, text=True, cwd=PROTO,
                          env={"PYTHONPATH": PROTO, "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}, timeout=60)


def good(tmp_path, **over):
    a = {"--deployment": F2, "--abi-dir": ABI_DIR, "--index": "0", "--key-label": "witness-1", "--state-dir": str(tmp_path / "state")}
    a.update(over)
    return [x for kv in a.items() if kv[1] is not None for x in kv]


def refused(p):
    assert p.returncode == 2 and p.stdout == "" and "Traceback" not in p.stderr, (p.returncode, p.stdout, p.stderr)
    lines = p.stderr.strip().splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert set(obj) == {"error"} and set(obj["error"]) >= {"code", "message"}
    return obj["error"]


@pytest.mark.parametrize("drop", ["--deployment", "--abi-dir", "--index", "--key-label", "--state-dir"])
def test_every_argument_is_required(tmp_path, drop):
    p = run(good(tmp_path, **{drop: None}))
    assert p.returncode == 2 and p.stdout == "" and "Traceback" not in p.stderr and "the following arguments are required" in p.stderr and drop in p.stderr
    assert not os.path.exists(tmp_path / "state")


def test_the_index_must_be_0_to_3(tmp_path):
    for bad in ("4", "-1", "x", "01"):
        p = run(good(tmp_path, **{"--index": bad}))
        assert p.returncode == 2 and p.stdout == "" and "Traceback" not in p.stderr and "must be 0, 1, 2 or 3" in p.stderr, bad


@pytest.mark.parametrize("content", [b'{"a": 1, "a": 2}', b'{"a": NaN}', b"\xff\xfe", b"{", b"[]", b"{}"])
def test_a_deployment_file_that_is_not_strict_json_or_not_a_deployment_is_refused_cleanly(tmp_path, content):
    f = tmp_path / "dep.json"
    f.write_bytes(content)
    assert refused(run(good(tmp_path, **{"--deployment": str(f)})))["code"] == "MALFORMED"
    assert not os.path.exists(tmp_path / "state")


def test_a_manifest_that_does_not_declare_a_test_only_key_derivation_is_refused(tmp_path):
    m = json.load(open(F2))
    m["fixture"]["keyDerivation"] = "production HSM"
    f = tmp_path / "dep.json"
    f.write_text(json.dumps(m))
    err = refused(run(good(tmp_path, **{"--deployment": str(f)})))
    assert err["code"] == "MALFORMED" and "TEST-ONLY" in err["message"]


def test_a_key_label_whose_address_is_not_the_witness_at_that_index_is_refused_before_any_connection(tmp_path):
    err = refused(run(good(tmp_path, **{"--key-label": "witness-2"})))                 # witness-2 is index 1, not 0
    assert err["code"] == "UNKNOWN_AUTHORITY" and "index" in err["message"]
    assert not os.path.exists(tmp_path / "state")
    err = refused(run(good(tmp_path, **{"--key-label": "not-a-witness"})))
    assert err["code"] == "UNKNOWN_AUTHORITY"


def test_a_missing_abi_dir_or_allow_file_is_refused(tmp_path):
    assert refused(run(good(tmp_path, **{"--abi-dir": str(tmp_path / "nope")})))["code"] == "MALFORMED"
    assert refused(run(good(tmp_path) + ["--allow-governance", str(tmp_path / "nope.json")]))["code"] == "MALFORMED"
    bad = tmp_path / "allow.json"
    bad.write_text('[["1", "0xZZ", []]]')
    assert refused(run(good(tmp_path) + ["--allow-governance", str(bad)]))["code"] == "MALFORMED"


def test_an_unreachable_node_is_ledger_unreachable_and_leaves_no_state_behind(tmp_path):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    m = json.load(open(F2))
    m["chains"]["pbc"]["rpcUrl"] = m["chains"]["dbc"]["rpcUrl"] = f"http://127.0.0.1:{port}"
    f = tmp_path / "dep.json"
    f.write_text(json.dumps(m))
    err = refused(run(good(tmp_path, **{"--deployment": str(f)})))
    assert err["code"] == "ADAPTER_UNAVAILABLE" and err.get("reason") == "LEDGER_UNREACHABLE"
    assert not os.path.exists(tmp_path / "state" / "witness-0")


def test_a_state_directory_reachable_by_group_or_other_is_refused(tmp_path):
    d = tmp_path / "state"
    d.mkdir(mode=0o755)
    os.chmod(d, 0o755)
    assert refused(run(good(tmp_path)))["code"] == "MALFORMED"


def test_the_module_reads_no_environment_and_has_no_clock_thread_or_socket_of_its_own():
    src = open(os.path.join(PROTO, "hmbc_protocol", "witness_main.py")).read()
    for banned in ("os.environ", "import time", "datetime", "import threading", "import socket", "import random", "subprocess"):
        assert banned not in src, banned


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the request/response layer, with an injected service (no node): `handle_line(line, service)`
# --------------------------------------------------------------------------------------------------------------------------------------------------------
class Svc:
    def __init__(self):
        self.calls = []

    def sign_checkpoint(self, m):
        self.calls.append(("checkpoint", m))
        return "0x" + "ab" * 65

    def sign_decision(self, m):
        from hmbc_protocol.witness_service import WitnessRefusal
        raise WitnessRefusal("STALE_STATE", "CONFLICT_PINNED", "pinned", recorded={"message": {"a": "b"}, "signature": "0x" + "cd" * 65})

    def sign_receipt(self, m):
        raise RuntimeError("secret /home/x")

    def sign_governance(self, m):
        return "0x" + "ef" * 65


def req(**over):
    r = {"schemaVersion": "hmbc-witness-rpc/v1", "id": 7, "round": 1, "kind": "checkpoint", "message": {"sequence": "1"}}
    r.update(over)
    return json.dumps(r)


def test_a_signature_reply_echoes_the_id_and_the_message_in_the_pool_shape():
    sys.path.insert(0, PROTO)
    from hmbc_protocol import witness_main as wm
    svc = Svc()
    out = wm.handle_line(req(), svc)
    assert out == {"schemaVersion": "hmbc-witness-rpc/v1", "id": 7, "reply": {"type": "signature", "message": {"sequence": "1"}, "signature": "0x" + "ab" * 65}}
    assert svc.calls == [("checkpoint", {"sequence": "1"})]
    assert wm.handle_line(req(kind="governance", message={"action": "1", "admins": ["0x" + "11" * 20]}), svc)["reply"]["message"]["admins"] == ["0x" + "11" * 20]


def test_a_refusal_carries_code_reason_and_recorded_and_nothing_else():
    sys.path.insert(0, PROTO)
    from hmbc_protocol import witness_main as wm
    out = wm.handle_line(req(kind="decision"), Svc())
    assert out["reply"] == {"type": "error", "code": "STALE_STATE", "reason": "CONFLICT_PINNED", "recorded": {"message": {"a": "b"}, "signature": "0x" + "cd" * 65}}


def test_an_unexpected_exception_is_a_generic_error_that_leaks_nothing():
    sys.path.insert(0, PROTO)
    from hmbc_protocol import witness_main as wm
    out = wm.handle_line(req(kind="receipt"), Svc())
    assert out["id"] == 7 and out["reply"] == {"type": "error", "code": "ADAPTER_UNAVAILABLE", "reason": None, "recorded": None} and "secret" not in json.dumps(out)


@pytest.mark.parametrize("bad", ["not json", "[]", '{"a": 1, "a": 2}', '{"a": NaN}', req(schemaVersion="other"), req(id="7"), req(id=True), req(id=-1), req(round=3), req(round=0), req(round="1"),
                                 req(kind="nope"), req(kind=5), req(message=[]), req(message="x"), json.dumps({"schemaVersion": "hmbc-witness-rpc/v1", "id": 1, "round": 1, "kind": "checkpoint"}),
                                 json.dumps({"schemaVersion": "hmbc-witness-rpc/v1", "id": 1, "round": 1, "kind": "checkpoint", "message": {}, "extra": 1})])
def test_a_malformed_request_is_a_malformed_error_and_the_service_is_not_called(bad):
    sys.path.insert(0, PROTO)
    from hmbc_protocol import witness_main as wm
    svc = Svc()
    out = wm.handle_line(bad, svc)
    assert out["reply"] == {"type": "error", "code": "MALFORMED", "reason": None, "recorded": None} and svc.calls == []
    assert out["id"] is None or isinstance(out["id"], int)
    try:
        sent = json.loads(bad)
    except ValueError:
        sent = None
    if isinstance(sent, dict) and type(sent.get("id")) is int and sent["id"] >= 0:
        assert out["id"] == sent["id"]                                        # a readable id of a refused envelope is echoed so the caller can match the reply


def test_the_id_of_a_well_formed_envelope_is_echoed_even_when_the_message_is_refused():
    sys.path.insert(0, PROTO)
    from hmbc_protocol import witness_main as wm
    assert wm.handle_line(req(id=42, kind="decision"), Svc())["id"] == 42


def test_the_server_answers_one_line_per_line_and_survives_oversized_and_invalid_utf8_lines():
    import io
    sys.path.insert(0, PROTO)
    from hmbc_protocol import witness_main as wm
    stdin = io.BytesIO((req() + "\n").encode() + b"\xff\xfe\n" + b"x" * ((1 << 20) + 4) + b"\n" + (req(id=9) + "\n").encode() + req(id=10).encode())      # the last line has no newline
    out = io.StringIO()
    assert wm.serve(stdin, out, Svc()) == 0
    replies = [json.loads(l) for l in out.getvalue().splitlines()]
    assert [r["id"] for r in replies] == [7, None, None, 9, 10] and [r["reply"]["type"] for r in replies] == ["signature", "error", "error", "signature", "signature"]


def test_a_manifest_with_a_missing_or_wrongly_shaped_fixture_is_refused_cleanly(tmp_path):
    for fixture in (5, {}, {"keyDerivation": "TEST-ONLY"}, {"keyDerivation": "TEST-ONLY", "witnessSet": 3}, {"keyDerivation": "TEST-ONLY", "witnessSet": {"witnesses": 1, "version": "2"}}):
        m = json.load(open(F2))
        m["fixture"] = fixture
        f = tmp_path / "dep.json"
        f.write_text(json.dumps(m))
        assert refused(run(good(tmp_path, **{"--deployment": str(f)})))["code"] == "MALFORMED", fixture


def test_an_index_beyond_a_single_witness_deployment_is_refused_cleanly(tmp_path):
    e21 = os.path.join(FX, "agent1-85c59f5-e-successor-v2.1-deployment.json")
    err = refused(run(good(tmp_path, **{"--deployment": e21, "--index": "1", "--key-label": "witness-2"})))
    assert err["code"] == "UNKNOWN_AUTHORITY"


@pytest.mark.parametrize("entry", ['["9", "0x' + "11" * 20 + '", []]', '["1", "0x' + "11" * 20 + '", ["0xZZ"]]', '["1", "0x' + "11" * 20 + '", "not a list"]', '["1", 5, []]', '["1", "0x' + "AA" * 20 + '", []]',
                                   '["1", "0x' + "11" * 20 + '"]'])
def test_every_malformed_allow_list_entry_is_refused(tmp_path, entry):
    f = tmp_path / "allow.json"
    f.write_text("[" + entry + "]")
    assert refused(run(good(tmp_path) + ["--allow-governance", str(f)]))["code"] == "MALFORMED"
