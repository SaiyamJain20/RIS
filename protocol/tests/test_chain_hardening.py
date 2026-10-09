"""Findings 2/3/7/8 of the independent review: idle-chain clock, loopback pinning, redirects/proxies, error classes."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from hmbc_protocol import abi, chain
from support import rpc

CONTRACT = abi.Contract([{"type": "function", "name": "v", "stateMutability": "view", "inputs": [], "outputs": [{"name": "", "type": "uint64"}]}], "0x" + "11" * 20)


def serve(handler_cls):
    srv = HTTPServer(("127.0.0.1", 0), handler_cls)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def reply(h, result=None, raw=None):
    body = json.dumps(raw if raw is not None else {"jsonrpc": "2.0", "id": 1, "result": result}).encode()
    h.send_response(200)
    h.send_header("content-length", str(len(body)))
    h.end_headers()
    h.wfile.write(body)


# --- finding 2/3: "now" must not freeze on an idle chain ---------------------------------------------------------------------

def test_now_follows_the_clock_of_an_idle_chain_not_the_last_mined_block(ledger):
    from hmbc_protocol import ledger as ledger_mod
    led = ledger_mod.Ledger.from_deployment(ledger.deployment)
    head = led.dbc.get_block()["timestamp"]
    rpc(ledger.dbc_url, "evm_increaseTime", [300])                          # five idle minutes, no block mined
    assert led.dbc.get_block()["timestamp"] == head
    assert led.dbc.now() >= head + 300


def test_checkpoint_after_an_idle_period_is_still_acceptable(world):
    from hmbc_protocol.relay import Relay
    from hmbc_protocol.witness import Witness
    led, ctx = world
    rpc(led.dbc.url, "evm_increaseTime", [120])                              # > the 60 s checkpoint TTL since the last DBC block
    Relay(led, "relay").accept_state(Witness(led).checkpoint())             # would fail EXPIRED if "now" were the stale head
    assert led.dbc.call(led.KSSC, "currentCheckpoint")[0] is True


class _Pending(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["content-length"])))
        if req["method"] == "eth_chainId":
            return reply(self, "0x1")
        if req["method"] == "eth_getBlockByNumber" and req["params"][0] == "pending":
            return reply(self, raw={"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "pending not supported"}})
        if req["method"] == "eth_getBlockByNumber":
            return reply(self, {"number": "0x5", "hash": "0x" + "ab" * 32, "timestamp": "0x64"})


def test_now_falls_back_to_the_latest_block_when_the_node_has_no_pending_block():
    srv, url = serve(_Pending)
    try:
        assert chain.Chain(url, 1).now() == 100
    finally:
        srv.shutdown()


# --- finding 7: loopback pinning, redirects, proxies ----------------------------------------------------------------------------

@pytest.mark.parametrize("url", ["http://169.254.169.254:80", "http://example.com:8545", "http://127.0.0.1", "file:///etc/passwd", "http://127.0.0.1:99999", None, 7])
def test_chain_itself_refuses_non_loopback_or_malformed_urls(url):
    with pytest.raises(chain.ChainError):
        chain.Chain(url, 1)


def test_redirects_are_not_followed():
    hits = []

    class Target(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            hits.append(("POST", self.path))
            reply(self, "0x1")

        def do_GET(self):                                                       # urllib turns a redirected POST into a GET
            hits.append(("GET", self.path))
            reply(self, "0x1")

    tsrv, turl = serve(Target)

    class Redirector(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["content-length"]))
            self.send_response(302)
            self.send_header("location", turl + "/stolen")
            self.send_header("content-length", "0")
            self.end_headers()

    rsrv, rurl = serve(Redirector)
    try:
        with pytest.raises(chain.ChainError):
            chain.Chain(rurl, 1).block_number()
        assert hits == [], "the client followed a redirect away from the pinned node"
    finally:
        tsrv.shutdown(); rsrv.shutdown()


def test_proxy_environment_variables_are_ignored(monkeypatch):
    seen = []

    class Proxy(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            seen.append(self.path)
            reply(self, "0x1")

    class Node(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["content-length"]))
            reply(self, "0x1")

    psrv, purl = serve(Proxy)
    nsrv, nurl = serve(Node)
    monkeypatch.setenv("http_proxy", purl)
    monkeypatch.setenv("HTTP_PROXY", purl)
    try:
        assert chain.Chain(nurl, 1).block_number() == 1
        assert seen == []
    finally:
        psrv.shutdown(); nsrv.shutdown()


# --- finding 8: failures map to ChainError, never a raw exception ---------------------------------------------------------------

@pytest.mark.parametrize("raw", [{"jsonrpc": "2.0", "id": 1}, {"jsonrpc": "2.0", "id": 1, "result": None}, ["not", "an", "object"], "just a string",
                                 "an error occurred", ["error", "result"]])      # the last two CONTAIN the keys: only an explicit object check stops out["error"] raising TypeError
def test_malformed_node_replies_are_chain_errors(raw):
    class Bad(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["content-length"]))
            reply(self, raw=raw)

    srv, url = serve(Bad)
    try:
        with pytest.raises(chain.ChainError):
            chain.Chain(url, 1).block_number()
    finally:
        srv.shutdown()
