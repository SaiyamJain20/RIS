"""Findings 1, 5, 8 and 11 of the independent review (adapter): pinned deployment, stdin robustness, huge integers, no strippable asserts."""
import copy
import json
import pathlib
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from hmbc_protocol import adapter, client, eip712, wire

ROOT = pathlib.Path(__file__).resolve().parents[1]
GRANT = {"grantId": "0x" + "55" * 32}


def call(op, inp, dep):
    resp = adapter.handle_line(json.dumps({"schemaVersion": "v1", "operation": op, "input": inp, "deploymentManifest": dep}))
    wire.adapter_response(resp, op)
    return resp


@pytest.fixture(autouse=True)
def _reset():
    yield
    adapter.configure(None)


def test_ledger_operations_need_a_pinned_deployment(world, tmp_path):
    led, ctx = world
    adapter.configure(str(tmp_path / "s"))                                        # state dir but NO pinned deployment
    r = call("release", GRANT, led.deployment)
    assert not r["ok"] and r["error"]["code"] == "ADAPTER_UNAVAILABLE" and "pinned" in r["error"]["message"]


def test_a_manifest_that_differs_from_the_pinned_one_is_wrong_destination_and_never_contacted(world, tmp_path):
    """A deviating runner points rpcUrl at its own mock node. The adapter must refuse BEFORE any connection, whatever the mock would answer."""
    led, ctx = world
    hits = []

    class Mock(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            hits.append(self.path)
            self.send_response(500)
            self.send_header("content-length", "0")
            self.end_headers()

    srv = HTTPServer(("127.0.0.1", 0), Mock)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    adapter.configure(str(tmp_path / "s"), led.deployment)
    try:
        for mutate in (lambda d: d["chains"]["dbc"].__setitem__("rpcUrl", f"http://127.0.0.1:{srv.server_address[1]}"),
                       lambda d: d["chains"]["pbc"]["contracts"].__setitem__("PSC", "0x" + "99" * 20),
                       lambda d: d["fixture"]["witnessSet"]["keyLabels"].__setitem__(0, "attacker")):
            dep = copy.deepcopy(led.deployment)
            mutate(dep)
            for op, inp in (("release", GRANT), ("collect_decision", {"requestDigest": "0x" + "99" * 32})):
                r = call(op, inp, dep)
                assert not r["ok"] and r["error"]["code"] == "WRONG_DESTINATION", (op, r)
        assert hits == []
    finally:
        srv.shutdown()


def test_prepare_request_also_refuses_a_manifest_other_than_the_pinned_one(world, tmp_path):
    led, ctx = world
    adapter.configure(str(tmp_path / "s"), led.deployment)
    dep = copy.deepcopy(led.deployment)
    dep["chains"]["dbc"]["contracts"]["KSSC"] = "0x" + "99" * 20
    r = call("prepare_request", {"request": {"nothing": "relevant"}, "signingKeyRef": "keyref:user:alice"}, dep)
    assert not r["ok"] and r["error"]["code"] in ("WRONG_DESTINATION", "MALFORMED")


def test_the_pinned_deployment_itself_works(world, tmp_path):
    led, ctx = world
    adapter.configure(str(tmp_path / "s"), led.deployment)
    r = call("release", GRANT, led.deployment)
    assert not r["ok"] and r["error"]["code"] == "NOT_COMMITTED"                  # reached the real ledger and found no such grant


def test_a_pinned_deployment_must_itself_be_valid(world, tmp_path):
    led, ctx = world
    bad = copy.deepcopy(led.deployment)
    bad["abi"]["PSC"]["abiSha256"] = "0" * 64
    with pytest.raises(ValueError):
        adapter.configure(str(tmp_path / "s"), bad)


# --- finding 5: stdin robustness -----------------------------------------------------------------------------------------------

def run_adapter(stdin_bytes, tmp_path, extra=()):
    p = subprocess.run([sys.executable, "-m", "hmbc_protocol.adapter", "--state-dir", str(tmp_path / "state"), *extra], cwd=ROOT,
                       env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin", "PYTHONIOENCODING": "utf-8:strict"}, input=stdin_bytes, capture_output=True, timeout=60)
    return p


def test_invalid_utf8_gets_a_malformed_response_and_the_process_keeps_serving(tmp_path):
    good = json.dumps({"schemaVersion": "v1", "operation": "rotate_epoch", "input": {"targetEpoch": "1"}, "deploymentManifest": {}}).encode()
    p = run_adapter(b"\xff\xfe not utf8\n" + good + b"\n", tmp_path)
    assert p.returncode == 0 and p.stderr == b"", p.stderr
    lines = [json.loads(x) for x in p.stdout.splitlines()]
    assert len(lines) == 2 and lines[0]["error"]["code"] == "MALFORMED" and lines[1]["error"]["code"] == "MALFORMED"   # second: manifest {} is invalid


def test_an_oversized_line_is_answered_once_and_the_stream_resynchronises(tmp_path):
    big = b"x" * (adapter.MAX_LINE_BYTES * 2 + 17)
    good = json.dumps({"schemaVersion": "v1", "operation": "rotate_epoch", "input": {"targetEpoch": "1"}, "deploymentManifest": {}}).encode()
    p = run_adapter(big + b"\n" + good + b"\n", tmp_path)
    assert p.returncode == 0 and p.stderr == b""
    lines = [json.loads(x) for x in p.stdout.splitlines()]
    assert len(lines) == 2 and "1 MiB" in lines[0]["error"]["message"]            # exactly one response for the giant line, then back in step


# --- finding 8 / 11 --------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("n", [4301, 5000, 100000])
def test_huge_decimal_strings_are_malformed_not_a_raw_value_error(n):
    with pytest.raises(wire.WireError):
        wire.uint("9" * n, 64)
    with pytest.raises(eip712.EncodingError):
        eip712._uint("9" * n, 64)


def test_prepare_request_with_a_huge_nonce_is_malformed(world, tmp_path):
    led, ctx = world
    from hmbc_protocol.client import UserClient
    adapter.configure(str(tmp_path / "s"), led.deployment)
    req = UserClient("alice", led.deployment).build_request(data_id="0x" + "ab" * 32, nonce="9" * 5000, auth_epoch="3", expires_at="1800000030")
    r = call("prepare_request", {"request": req, "signingKeyRef": "keyref:user:alice"}, led.deployment)
    assert not r["ok"] and r["error"]["code"] == "MALFORMED"


def test_signature_self_check_is_an_error_not_an_assert(world, tmp_path, monkeypatch):
    led, ctx = world
    from hmbc_protocol.client import UserClient
    adapter.configure(str(tmp_path / "s"), led.deployment)
    monkeypatch.setattr(eip712, "recover", lambda d, s: "0x" + "00" * 20)
    c = UserClient("alice", led.deployment)
    req = c.build_request(data_id="0x" + "ab" * 32, nonce="1", auth_epoch="3", expires_at="1800000030")
    with pytest.raises(client.ClientError) as e:
        c.sign_request(req)
    assert e.value.code == "BAD_SIGNATURE"
    r = call("prepare_request", {"request": req, "signingKeyRef": "keyref:user:alice"}, led.deployment)
    assert not r["ok"] and r["error"]["code"] == "ADAPTER_UNAVAILABLE"
