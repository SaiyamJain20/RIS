"""D50 chain view over JSON-RPC (agent 2, F task 2 slice 8a). Written BEFORE hmbc_protocol/rpc_binding_view.py existed.

`RpcBindingView` is the REAL implementation of the chain view `binding_open.reconstruct` reads through (chain_id, latest, block, code, call): one JSON-RPC request per view call, ABI-encoded getters
against ABI files whose sha256 the pinned manifest names, every read after the anchor pinned to ONE block number. What is tested: against a FAKE JSON-RPC node (an in-process loopback HTTP server that
decodes the calldata with `eth_abi` and the byte-copied ABI exports of agent 1) the view returns exactly what `binding_open` expects, `reconstruct` over the view gives the SAME document and binding hash as
over the in-memory fake the 106 binding_open tests use, in exactly 55 (F) and 48 (E) requests, and every way a node can misbehave is a LedgerUnreachable (stage 1), never a wrong value. NOT tested: a real
node (no Foundry/Anvil is installed here), real block hashes, EIP-1898 pinning by hash (the view pins by block NUMBER; the anchor hash is the caller's), or a reorg between reads. The fake node shares the
ABI files and the eth_abi library with the code under test: that is a correlated check of the encoding, not an independent one; the 4-byte selectors are recomputed in the test with eth_utils.
"""
import copy
import hashlib
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from eth_abi import decode, encode
from eth_utils import function_signature_to_4byte_selector

from hmbc_protocol import binding as bd
from hmbc_protocol import binding_open as bo
from hmbc_protocol import rpc_binding_view as rv
from hmbc_protocol.chain import Chain

from test_binding_open import ADDRS, Chains, bhash, make_manifest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FX = os.path.join(ROOT, "protocol", "tests", "fixtures")
ABI_DIR = os.path.join(FX, "agent1-85c59f5-abi")
F2 = json.load(open(os.path.join(FX, "agent1-85c59f5-f-base-deployment.json")))
NAMES = ("LSC", "TMSC", "RSC", "PSC", "ACSC", "KSSC", "Governance")
ABIS = {n: json.load(open(os.path.join(ABI_DIR, n + ".json"))) for n in NAMES}


def sig(f):
    return f["name"] + "(" + ",".join(i["type"] for i in f["inputs"]) + ")"


class Node:
    """One chain's fake JSON-RPC node. `fake` is a `Chains` (the in-memory fake of the binding_open tests) it answers from; behaviours: down, error, revert, garbage, short, wrongid."""

    def __init__(self, chain, fake):
        self.chain, self.fake, self.requests, self.mode = chain, fake, [], None
        self.addr_name = {a: n for n, a in fake.m["chains"][chain]["contracts"].items()}
        node = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["content-length"])))
                node.requests.append((body["method"], body["params"]))
                try:
                    result = node.answer(body["method"], body["params"])
                    out = {"jsonrpc": "2.0", "id": body["id"], "result": result}
                except RuntimeError as e:
                    out = {"jsonrpc": "2.0", "id": body["id"], "error": {"code": -32000, "message": str(e)}}
                data = json.dumps(out).encode()
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    def block_hash(self, n):
        return self.fake.genesis[self.chain] if n == 0 else bhash("%s:%d" % (self.chain, n))

    def answer(self, method, params):
        if self.mode == "error":
            raise RuntimeError("node says no")
        if self.mode == "garbage":
            return "0xzz"
        if method == "eth_chainId":
            return hex(int(self.fake.m["chains"][self.chain]["chainId"]) + (1 if self.mode == "wrongid" else 0))
        if method == "eth_getBlockByNumber":
            tag = params[0]
            n = self.fake.head[self.chain] if tag == "latest" else int(tag, 16)
            if n > self.fake.head[self.chain] or (self.chain, n) in self.fake.missing_block:
                return None
            return {"number": hex(n), "hash": self.block_hash(n), "timestamp": hex(1000 + n)}
        if method == "eth_getCode":
            a = params[0]
            return self.fake.code_override.get(self.addr_name[a], __import__("test_binding_open").synthetic_code(self.addr_name[a]))
        if method == "eth_call":
            to, data = params[0]["to"], bytes.fromhex(params[0]["data"][2:])
            name = self.addr_name[to]
            for f in ABIS[name]:
                if f.get("type") == "function" and function_signature_to_4byte_selector(sig(f)) == data[:4]:
                    args = decode([i["type"] for i in f["inputs"]], data[4:]) if f["inputs"] else ()
                    self.fake.requests.append(("node-call", name, f["name"], tuple(args), params[1]))
                    if self.mode == "revert":
                        raise RuntimeError("execution reverted")
                    v = self.fake.values[(name, f["name"])]
                    t = f["outputs"][0]["type"]
                    if t == "bool":
                        pass
                    elif t == "address[]":
                        v = list(v)
                    elif t == "address":
                        v = v
                    else:
                        v = int(v)
                    out = encode([t], [v])
                    return "0x" + (out[:-1].hex() if self.mode == "short" else out.hex())
            raise RuntimeError("no such function")
        raise RuntimeError("unsupported " + method)


class Rig:
    def __init__(self, family="F"):
        self.m = make_manifest(family)
        self.fake = Chains(self.m)
        self.nodes = {s: Node(s, self.fake) for s in ("pbc", "dbc")}
        self.m["chains"]["pbc"]["rpcUrl"], self.m["chains"]["dbc"]["rpcUrl"] = self.nodes["pbc"].url, self.nodes["dbc"].url
        chains = {s: Chain(self.nodes[s].url, int(self.m["chains"][s]["chainId"])) for s in ("pbc", "dbc")}
        contracts = {s: dict(self.m["chains"][s]["contracts"]) for s in ("pbc", "dbc")}
        self.view = rv.RpcBindingView(chains=chains, contracts=contracts, abis=ABIS)

    def requests(self):
        return sum(len(n.requests) for n in self.nodes.values())

    def close(self):
        for n in self.nodes.values():
            n.close()


@pytest.fixture(params=["E", "F"])
def rig(request):
    r = Rig(request.param)
    r.family = request.param
    yield r
    r.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_reconstruct_over_the_rpc_view_equals_reconstruct_over_the_in_memory_fake_in_exactly_the_scheduled_requests(rig):
    got = bo.reconstruct(rig.m, rig.view, role="worker")
    ref = bo.reconstruct(rig.m, Chains(rig.m), role="worker")
    assert got["document"] == ref["document"] and got["binding_v2"] == ref["binding_v2"] and got["anchor"] == ref["anchor"] and got["buildChecked"] == ref["buildChecked"]
    assert rig.requests() == (55 if rig.family == "F" else 48)


def test_the_view_methods_return_the_shapes_binding_open_expects(rig):
    v = rig.view
    assert v.chain_id("pbc") == rig.m["chains"]["pbc"]["chainId"] and isinstance(v.chain_id("dbc"), str)
    latest = v.latest("dbc")
    assert latest == {"number": str(rig.fake.head["dbc"]), "hash": bhash("dbc:%d" % rig.fake.head["dbc"])}
    assert v.block("pbc", 0) == {"number": "0", "hash": rig.fake.genesis["pbc"]}
    assert v.block("pbc", rig.fake.head["pbc"] + 1) is None
    psc = rig.m["chains"]["pbc"]["contracts"]["PSC"]
    assert v.code("pbc", psc, 300).startswith("0x") and v.code("pbc", psc, 300) == v.code("pbc", psc, 300).lower()
    assert v.call("pbc", psc, "configured", [], 300) is True
    assert v.call("pbc", psc, "profile", [], 300) == rig.fake.values[("PSC", "profile")] and isinstance(v.call("pbc", psc, "profile", [], 300), str)
    assert v.call("pbc", psc, "witnesses", [], 300) == rig.fake.values[("PSC", "witnesses")]
    assert v.call("pbc", psc, "ksscForChain", [rig.m["chains"]["dbc"]["chainId"]], 300) == rig.fake.values[("PSC", "ksscForChain")]


def test_a_call_is_pinned_to_the_given_block_number_and_carries_its_encoded_arguments():
    r = Rig("F")
    try:
        psc = r.m["chains"]["pbc"]["contracts"]["PSC"]
        r.view.call("pbc", psc, "ksscForChain", ["28545"], 299)
        method, params = r.nodes["pbc"].requests[-1]
        assert method == "eth_call" and params[1] == hex(299) and params[0]["to"] == psc
        assert params[0]["data"] == "0x" + function_signature_to_4byte_selector("ksscForChain(uint256)").hex() + encode(["uint256"], [28545]).hex()
        assert r.fake.requests[-1][-2:] == ((28545,), hex(299)) or r.fake.requests[-1][3] == (28545,)
        r.view.code("pbc", psc, 298)
        assert r.nodes["pbc"].requests[-1] == ("eth_getCode", [psc, hex(298)])
        r.view.block("pbc", 7)
        assert r.nodes["pbc"].requests[-1] == ("eth_getBlockByNumber", [hex(7), False])
    finally:
        r.close()


@pytest.mark.parametrize("mode", ["error", "garbage"])
def test_a_misbehaving_node_is_ledger_unreachable_on_every_view_method(mode):
    r = Rig("F")
    try:
        psc = r.m["chains"]["pbc"]["contracts"]["PSC"]
        r.nodes["pbc"].mode = mode
        for fn in (lambda: r.view.call("pbc", psc, "threshold", [], 300), lambda: r.view.latest("pbc"), lambda: r.view.block("pbc", 1), lambda: r.view.code("pbc", psc, 300),
                   lambda: r.view.chain_id("pbc")):
            with pytest.raises(bo.LedgerUnreachable):
                fn()
    finally:
        r.close()


@pytest.mark.parametrize("mode", ["revert", "short"])
def test_a_reverting_or_short_eth_call_is_ledger_unreachable(mode):
    r = Rig("F")
    try:
        r.nodes["pbc"].mode = mode
        with pytest.raises(bo.LedgerUnreachable):
            r.view.call("pbc", r.m["chains"]["pbc"]["contracts"]["PSC"], "threshold", [], 300)
    finally:
        r.close()


class Canned:
    """A chain client that answers every request with one fixed value (for replies a node should never send)."""
    chain_id = 1

    def __init__(self, value):
        self.value = value

    def rpc(self, method, params=None):
        return self.value


def canned_view(value):
    return rv.RpcBindingView(chains={"pbc": Canned(value), "dbc": Canned(value)}, contracts={"pbc": {"PSC": "0x" + "11" * 20}, "dbc": {}}, abis={"PSC": ABIS["PSC"]})


A11 = "0x" + "11" * 20


COMMON_BAD = [None, 5, "ff", "0xZZ", {"number": "0x1"}, [], True]


def test_replies_a_node_should_never_send_are_ledger_unreachable():
    # per method: the generic junk plus what is junk for THAT method ("0x" is a legitimate empty code, "0x123" a legitimate odd-length quantity)
    cases = {"chain_id": (lambda v: v.chain_id("pbc"), COMMON_BAD + ["0x"]),
             "latest": (lambda v: v.latest("pbc"), COMMON_BAD + ["0x", "0x123"]),
             "code": (lambda v: v.code("pbc", A11, 1), COMMON_BAD + ["0xABCD", "0x123"]),
             "call": (lambda v: v.call("pbc", A11, "threshold", [], 1), COMMON_BAD + ["0x", "0xABCD", "0x123"])}
    for name, (fn, bad) in cases.items():
        for value in bad:
            with pytest.raises(bo.LedgerUnreachable):
                fn(canned_view(value))
    assert canned_view("0x").code("pbc", A11, 1) == "0x"                 # an address without code is a legitimate answer: the code stage decides
    assert canned_view("0x123").chain_id("pbc") == str(0x123)


def test_a_block_reply_with_a_bad_hash_number_or_wrong_height_is_ledger_unreachable():
    good = "0x" + "ab" * 32
    for blk in ({"number": "0x5", "hash": good.upper().replace("0X", "0x")}, {"number": "0x5", "hash": "0x12"}, {"number": "5", "hash": good}, {"number": "0x5"}, {"hash": good},
                {"number": "0x6", "hash": good}):
        v = canned_view(blk)
        with pytest.raises(bo.LedgerUnreachable):
            v.block("pbc", 5)
    assert canned_view({"number": "0x5", "hash": good}).block("pbc", 5) == {"number": "5", "hash": good}
    assert canned_view({"number": "0x5", "hash": good}).latest("pbc") == {"number": "5", "hash": good}


def test_the_argument_encoder_accepts_only_canonical_in_range_values():
    arg = rv.RpcBindingView._arg
    assert arg("uint256", "0") == 0 and arg("uint8", "255") == 255 and arg("address", A11) == A11 and arg("bool", True) is True
    for t, v in (("uint8", "256"), ("uint256", str(1 << 256)), ("uint64", "01"), ("uint64", "-1"), ("uint64", 5), ("uint64", ""), ("address", "0x" + "AB" * 20), ("address", "0x12"), ("address", 5),
                 ("bool", 1), ("bool", "true")):
        with pytest.raises(ValueError):
            arg(t, v)


def test_an_unsupported_input_type_is_refused_before_anything_is_sent():
    abi = [{"type": "function", "name": "f", "inputs": [{"type": "bytes32"}], "outputs": [{"type": "uint256"}], "stateMutability": "view"}]
    v = rv.RpcBindingView(chains={"pbc": object(), "dbc": object()}, contracts={"pbc": {"X": A11}, "dbc": {}}, abis={"X": abi})
    with pytest.raises(ValueError):
        v.call("pbc", A11, "f", ["0x" + "00" * 32], 1)


def test_code_of_an_address_that_is_not_a_contract_of_that_chain_is_a_value_error():
    r = Rig("F")
    try:
        with pytest.raises(ValueError):
            r.view.code("pbc", "0x" + "99" * 20, 1)
        assert r.requests() == 0
    finally:
        r.close()


def test_a_node_that_is_down_is_ledger_unreachable():
    r = Rig("F")
    psc = r.m["chains"]["pbc"]["contracts"]["PSC"]
    r.close()
    with pytest.raises(bo.LedgerUnreachable):
        r.view.call("pbc", psc, "threshold", [], 300)
    with pytest.raises(bo.LedgerUnreachable):
        r.view.latest("dbc")


def test_a_chain_id_the_node_reports_is_returned_as_is_so_the_stage_check_can_refuse_it():
    r = Rig("F")
    try:
        r.nodes["pbc"].mode = "wrongid"
        assert r.view.chain_id("pbc") == str(int(r.m["chains"]["pbc"]["chainId"]) + 1)
        with pytest.raises(bd.OpenRefusal) as e:
            bo.reconstruct(r.m, r.view, role="worker")
        assert e.value.reason == "GENESIS_MISMATCH"
    finally:
        r.close()


def test_an_unreachable_node_during_reconstruct_is_stage_one():
    r = Rig("F")
    try:
        r.nodes["dbc"].mode = "error"
        with pytest.raises(bd.OpenRefusal) as e:
            bo.reconstruct(r.m, r.view, role="worker")
        assert e.value.reason == "LEDGER_UNREACHABLE"
    finally:
        r.close()


def test_caller_bugs_are_value_errors_not_ledger_faults():
    r = Rig("F")
    try:
        psc, kssc = r.m["chains"]["pbc"]["contracts"]["PSC"], r.m["chains"]["dbc"]["contracts"]["KSSC"]
        for bad in (lambda: r.view.call("pbc", "0x" + "99" * 20, "threshold", [], 1),             # an address that is not a contract of that chain
                    lambda: r.view.call("pbc", kssc, "threshold", [], 1),                             # a contract of the OTHER chain
                    lambda: r.view.call("pbc", psc, "noSuchFunction", [], 1),
                    lambda: r.view.call("pbc", psc, "ksscForChain", [], 1),                            # arity
                    lambda: r.view.call("pbc", psc, "threshold", ["1"], 1),
                    lambda: r.view.call("pbc", psc, "ksscForChain", ["not-a-number"], 1),
                    lambda: r.view.call("nowhere", psc, "threshold", [], 1),
                    lambda: r.view.call("pbc", psc, "threshold", [], -1), lambda: r.view.call("pbc", psc, "threshold", [], True),
                    lambda: r.view.block("pbc", -1), lambda: r.view.code("pbc", psc, "latest")):
            with pytest.raises(ValueError):
                bad()
    finally:
        r.close()


def test_only_view_functions_with_one_supported_output_can_be_called():
    abi = [{"type": "function", "name": "poke", "inputs": [], "outputs": [], "stateMutability": "nonpayable"},
           {"type": "function", "name": "pair", "inputs": [], "outputs": [{"type": "uint256"}, {"type": "uint256"}], "stateMutability": "view"},
           {"type": "function", "name": "bump", "inputs": [], "outputs": [{"type": "uint256"}], "stateMutability": "nonpayable"},
           {"type": "function", "name": "pay", "inputs": [], "outputs": [{"type": "uint256"}], "stateMutability": "payable"},
           {"type": "function", "name": "blob", "inputs": [], "outputs": [{"type": "bytes"}], "stateMutability": "view"},
           {"type": "function", "name": "twice", "inputs": [], "outputs": [{"type": "uint8"}], "stateMutability": "view"},
           {"type": "function", "name": "twice", "inputs": [], "outputs": [{"type": "uint16"}], "stateMutability": "view"}]
    v = rv.RpcBindingView(chains={"pbc": object(), "dbc": object()}, contracts={"pbc": {"X": "0x" + "11" * 20}, "dbc": {}}, abis={"X": abi})
    for fn in ("poke", "pair", "bump", "pay", "blob", "twice", "missing"):
        with pytest.raises(ValueError):
            v.call("pbc", "0x" + "11" * 20, fn, [], 1)


def test_the_same_address_on_both_chains_is_two_different_contracts():
    r = Rig("F")
    try:
        same = "0x" + "77" * 20
        v = rv.RpcBindingView(chains={"pbc": object(), "dbc": object()}, contracts={"pbc": {"PSC": same}, "dbc": {"KSSC": same}}, abis={"PSC": ABIS["PSC"], "KSSC": ABIS["KSSC"]})
        assert v._function("pbc", same, "ksscForChain", ["1"])[0]["name"] == "ksscForChain"
        with pytest.raises(ValueError):
            v._function("dbc", same, "ksscForChain", ["1"])                 # KSSC has no such function
    finally:
        r.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# from_manifest: the ABI files are pinned by the manifest's abiSha256
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def chains_for(m):
    return {s: Chain("http://127.0.0.1:%d" % (9000 + i), int(m["chains"][s]["chainId"])) for i, s in enumerate(("pbc", "dbc"))}


def test_from_manifest_loads_the_abi_files_whose_hash_the_manifest_names():
    v = rv.RpcBindingView.from_manifest(F2, chains_for(F2), ABI_DIR)
    assert set(v._abis) == set(NAMES) and v._abis["PSC"] == ABIS["PSC"]


def test_from_manifest_refuses_a_changed_a_missing_or_foreign_abi_file(tmp_path):
    for name in ("changed", "missing", "extra-bytes"):
        d = tmp_path / name
        d.mkdir()
        for n in NAMES:
            if not (name == "missing" and n == "PSC"):
                raw = open(os.path.join(ABI_DIR, n + ".json"), "rb").read()
                (d / (n + ".json")).write_bytes(raw + (b" " if name == "extra-bytes" and n == "PSC" else b""))
        if name == "changed":
            j = json.loads((d / "PSC.json").read_text())
            j[0]["name"] = "evil"
            (d / "PSC.json").write_text(json.dumps(j))
        with pytest.raises(ValueError):
            rv.RpcBindingView.from_manifest(F2, chains_for(F2), str(d))


def test_from_manifest_checks_the_chain_clients_against_the_manifest():
    ch = chains_for(F2)
    ch["pbc"].chain_id += 1
    with pytest.raises(ValueError):
        rv.RpcBindingView.from_manifest(F2, ch, ABI_DIR)
    with pytest.raises(ValueError):
        rv.RpcBindingView.from_manifest(F2, {"pbc": ch["pbc"]}, ABI_DIR)


def test_constructor_validation():
    ok = dict(chains={"pbc": object(), "dbc": object()}, contracts={"pbc": {"PSC": "0x" + "11" * 20}, "dbc": {}}, abis={"PSC": ABIS["PSC"]})
    rv.RpcBindingView(**ok)
    for bad in (dict(ok, chains={"pbc": object()}), dict(ok, contracts={"pbc": {"PSC": "0xABC"}, "dbc": {}}), dict(ok, contracts={"pbc": {"PSC": "0x" + "11" * 20}, "dbc": {}}, abis={}),
                dict(ok, abis={"PSC": "not a list"}), dict(ok, contracts={"pbc": {"PSC": "0x" + "AA" * 20}, "dbc": {}})):
        with pytest.raises(ValueError):
            rv.RpcBindingView(**bad)


def test_the_module_reads_no_clock_no_thread_no_socket_and_no_environment():
    src = open(os.path.join(ROOT, "protocol", "hmbc_protocol", "rpc_binding_view.py")).read()
    for banned in ("import time", "datetime", "import threading", "import socket", "import random", "subprocess", "os.environ", "import urllib"):
        assert banned not in src, banned


def test_an_unknown_chain_name_is_a_value_error_on_every_view_method():
    r = Rig("F")
    try:
        for fn in (lambda: r.view.chain_id("nowhere"), lambda: r.view.latest("nowhere"), lambda: r.view.block("nowhere", 1), lambda: r.view.latest(None), lambda: r.view.chain_id(["pbc"])):
            with pytest.raises(ValueError):
                fn()
        assert r.requests() == 0
    finally:
        r.close()
