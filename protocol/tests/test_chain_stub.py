"""Chain client against a stub JSON-RPC node that lies: it answers eth_call for ANY block tag, so only the client's own guard can notice."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from hmbc_protocol import abi, chain

CONTRACT = abi.Contract([{"type": "function", "name": "v", "stateMutability": "view", "inputs": [], "outputs": [{"name": "", "type": "uint64"}]}], "0x" + "11" * 20)


@pytest.fixture
def stub():
    seen = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            req = json.loads(self.rfile.read(int(self.headers["content-length"])))
            seen.append((req["method"], req["params"]))
            result = {"eth_chainId": "0x1", "eth_blockNumber": "0x5", "eth_call": "0x" + format(42, "064x")}[req["method"]]
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "result": result}).encode()
            self.send_response(200)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", seen
    srv.shutdown()


def test_a_block_beyond_the_head_is_an_error_even_if_the_node_would_answer(stub):
    url, seen = stub
    c = chain.Chain(url, 1)
    assert c.call(CONTRACT, "v", block=5) == "42"
    with pytest.raises(chain.ChainError, match="does not exist"):
        c.call(CONTRACT, "v", block=6)
    assert [m for m, _ in seen].count("eth_call") == 1                       # the lying node was never even asked about block 6


def test_a_wrong_chain_id_is_refused_before_any_read(stub):
    url, seen = stub
    with pytest.raises(chain.ChainError, match="chain id"):
        chain.Chain(url, 2).call(CONTRACT, "v")
    assert [m for m, _ in seen] == ["eth_chainId"]
