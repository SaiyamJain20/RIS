"""Witness-side ledger view over JSON-RPC: fast unit tests with a FAKE chain client (agent 2, F task 2 slice 9a). The live tests against real nodes and real contracts are in `test_rpc_binding_view_live.py`;
these check, without any node, exactly WHICH contract, function, arguments and block each view method asks for, the shapes it returns, and that every kind of failure is `LedgerUnreachable` (or a ValueError
for a caller bug). The contracts are the real `abi.Contract` objects of agent 1's byte-copied F ABI exports; only the client is fake."""
import json
import os

import pytest

from hmbc_protocol import rpc_witness_view as rwv
from hmbc_protocol.abi import AbiError, Contract
from hmbc_protocol.chain import ChainError, Rejected
from hmbc_protocol.witness_service import LedgerUnreachable

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FX = os.path.join(ROOT, "protocol", "tests", "fixtures")
ABI_DIR = os.path.join(FX, "agent1-85c59f5-abi")
F2 = json.load(open(os.path.join(FX, "agent1-85c59f5-f-base-deployment.json")))
ABIS = {n: json.load(open(os.path.join(ABI_DIR, n + ".json"))) for n in ("PSC", "TMSC", "Governance", "KSSC", "ACSC")}
SIDE = {"PSC": "pbc", "TMSC": "pbc", "Governance": "pbc", "KSSC": "dbc", "ACSC": "dbc"}
H = "0x" + "ab" * 32
A = "0x" + "11" * 20


def contracts(skip=()):
    out = {}
    for i, (n, abi) in enumerate(ABIS.items()):
        if n not in skip:
            out[n] = Contract(abi, "0x" + ("%02x" % (0xA0 + i)) * 20)          # letters in the hex, so a missing .lower() shows
    return out


class FakeChain:
    """Records every request and answers from `answers` ({(address, fn): value | callable | Exception}); the carried client's surface used by the view."""

    def __init__(self, chain_id, head=100, ts=5000):
        self.chain_id, self.head, self.ts = chain_id, head, ts
        self.calls, self.answers, self.fail = [], {}, None
        self.logs, self.tx, self.blocks = [], {}, {}
        self.pending_ts = None

    def _check_chain(self):
        if self.fail == "chain":
            raise ChainError("chain id mismatch")

    def call(self, contract, fn, *args, block="latest"):
        self.calls.append((contract.address, fn, args, block))
        if self.fail == "call":
            raise ChainError("transport failure")
        if self.fail == "abi":
            raise AbiError("cannot decode")
        v = self.answers[(contract.address, fn)]
        if isinstance(v, Exception):
            raise v
        return v(*args) if callable(v) else v

    def get_block(self, block="latest"):
        if self.fail == "block":
            raise ChainError("transport failure")
        n = self.head if block == "latest" else block
        return {"number": n, "hash": "0x" + "%064x" % n, "timestamp": self.ts + n}

    def rpc(self, method, params=None):
        assert method == "eth_getBlockByNumber"
        if self.fail == "block":
            raise ChainError("transport failure")
        n = int(params[0], 16)
        return self.blocks.get(n) if n in self.blocks else (None if n > self.head else {"hash": "0x" + "%064x" % n, "timestamp": hex(self.ts + n)})

    def now(self):
        if self.fail == "now":
            raise ChainError("transport failure")
        return self.pending_ts or self.ts + self.head

    def get_logs(self, address, topics, from_block=0, to_block="latest"):
        self.calls.append(("logs", address, tuple(topics)))
        if self.fail == "logs":
            raise ChainError("transport failure")
        return self.logs

    def get_transaction(self, tx_hash):
        if self.fail == "tx":
            raise ChainError("transaction not found")
        return self.tx


def make(skip=()):
    cs = contracts(skip)
    pbc, dbc = FakeChain(18545), FakeChain(28545, head=50, ts=9000)
    return rwv.RpcWitnessView(chains={"pbc": pbc, "dbc": dbc}, contracts=cs), pbc, dbc, cs


def answer(chain, contract, fn, value):
    chain.answers[(contract.address, fn)] = value


# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_observe_reports_the_latest_block_of_the_named_chain_with_string_fields():
    v, pbc, dbc, _ = make()
    assert v.observe("pbc") == {"chainId": "18545", "blockNumber": "100", "blockHash": "0x" + "%064x" % 100, "timestamp": "5100"}
    assert v.observe("dbc") == {"chainId": "28545", "blockNumber": "50", "blockHash": "0x" + "%064x" % 50, "timestamp": "9050"}


def test_pbc_block_is_none_for_a_missing_block_and_has_string_fields_otherwise():
    v, pbc, dbc, _ = make()
    assert v.pbc_block(7) == {"number": "7", "hash": "0x" + "%064x" % 7, "timestamp": str(5007)}
    assert v.pbc_block(101) is None and v.pbc_block(0)["number"] == "0"


def test_now_is_the_carried_clients_now_for_the_named_chain():
    v, pbc, dbc, _ = make()
    pbc.pending_ts = 77777
    assert v.now("pbc") == 77777 and v.now("dbc") == 9050


def test_reads_at_asks_the_right_contract_function_and_block_for_each_epoch_value():
    v, pbc, dbc, cs = make()
    answer(pbc, cs["TMSC"], "authEpoch", "3")
    answer(pbc, cs["PSC"], "policyVersion", "1")
    answer(pbc, cs["PSC"], "witnessSetVersion", "2")
    assert v.reads_at(42) == {"authEpoch": "3", "policyVersion": "1", "witnessSetVersion": "2"}
    assert sorted(pbc.calls) == sorted([(cs["TMSC"].address, "authEpoch", (), 42), (cs["PSC"].address, "policyVersion", (), 42), (cs["PSC"].address, "witnessSetVersion", (), 42)])


def test_the_pbc_state_reads_go_to_the_pbc_contracts_with_their_arguments():
    v, pbc, dbc, cs = make()
    answer(pbc, cs["Governance"], "governanceNonce", "4")
    answer(pbc, cs["TMSC"], "isAuthority", True)
    answer(pbc, cs["TMSC"], "removedAuthority", False)
    answer(pbc, cs["PSC"], "getRequest", {"status": "1"})
    answer(pbc, cs["TMSC"], "checkCredentials", ["0", [{"validUntil": "9"}]])
    assert v.governance_nonce() == "4" and v.is_authority(A) is True and v.removed_authority(A) is False and v.psc_request(H) == {"status": "1"}
    assert v.credentials(A, {"claims": []}, 123, 99) == ("0", [{"validUntil": "9"}])
    assert pbc.calls[:4] == [(cs["Governance"].address, "governanceNonce", (), "latest"), (cs["TMSC"].address, "isAuthority", (A,), "latest"), (cs["TMSC"].address, "removedAuthority", (A,), "latest"),
                             (cs["PSC"].address, "getRequest", (H,), "latest")]
    assert pbc.calls[-1] == (cs["TMSC"].address, "checkCredentials", (A, {"claims": []}, "123"), 99)       # the timestamp goes as a decimal string, the block pins the read
    assert dbc.calls == []


def test_the_dbc_state_reads_go_to_the_dbc_contracts_with_their_arguments():
    v, pbc, dbc, cs = make()
    answer(dbc, cs["KSSC"], "currentCheckpoint", [True, {"sequence": "5", "expiresAt": "9"}])
    answer(dbc, cs["KSSC"], "nonceConsumed", True)
    answer(dbc, cs["ACSC"], "evaluate", True)
    answer(dbc, cs["KSSC"], "getGrant", ["0x" + "01" * 32, "0x" + "02" * 32, A, "0", "20", True])
    assert v.dbc_current_checkpoint() == {"sequence": "5", "expiresAt": "9"} and v.nonce_consumed(A, 7) is True and v.policy_satisfied(H, [{"r": 1}]) is True
    assert v.grant(H) == {"digest": "0x" + "01" * 32, "dataId": "0x" + "02" * 32, "gid": A, "keyEpoch": "0", "expiresAt": "20", "allowed": True}
    assert dbc.calls == [(cs["KSSC"].address, "currentCheckpoint", (), "latest"), (cs["KSSC"].address, "nonceConsumed", (A, "7"), "latest"), (cs["ACSC"].address, "evaluate", (H, [{"r": 1}]), "latest"),
                         (cs["KSSC"].address, "getGrant", (H,), "latest")]
    assert pbc.calls == []


def test_no_checkpoint_is_none_and_the_returned_dict_is_a_copy():
    v, pbc, dbc, cs = make()
    cp = {"sequence": "1"}
    answer(dbc, cs["KSSC"], "currentCheckpoint", [True, cp])
    got = v.dbc_current_checkpoint()
    got["sequence"] = "9"
    assert cp["sequence"] == "1"
    answer(dbc, cs["KSSC"], "currentCheckpoint", [False, {"sequence": "0"}])
    assert v.dbc_current_checkpoint() is None


def test_the_forwarded_logs_are_the_pscs_accessforwarded_events_filtered_by_the_digest():
    v, pbc, dbc, cs = make()
    pbc.logs = [{"transactionHash": H, "blockNumber": "0x1f", "blockHash": "0x" + "cc" * 32}]
    assert v.forwarded_logs(H) == [{"txHash": H, "block": 31}]
    from eth_utils import keccak
    kind, address, topics = pbc.calls[-1]
    assert (kind, address) == ("logs", cs["PSC"].address) and topics == ("0x" + keccak(text=cs["PSC"].event_signature("AccessForwarded")).hex(), H)


def test_the_grant_issued_logs_are_the_ksscs_events_filtered_by_the_grant_id_with_their_block_hash():
    v, pbc, dbc, cs = make()
    dbc.logs = [{"transactionHash": H, "blockNumber": "0x50", "blockHash": "0x" + "dd" * 32}]
    assert v.grant_issued_logs(H) == [{"block": 80, "hash": "0x" + "dd" * 32}]
    from eth_utils import keccak
    kind, address, topics = dbc.calls[-1]
    assert (kind, address) == ("logs", cs["KSSC"].address) and topics == ("0x" + keccak(text=cs["KSSC"].event_signature("GrantIssued")).hex(), H)


def zero(t):
    ty = t["type"]
    if ty == "tuple":
        return {c["name"]: zero(c) for c in t["components"]}
    if ty.endswith("[]"):
        return []
    if ty == "address":
        return "0x" + "00" * 20
    if ty == "bool":
        return False
    if ty == "bytes":
        return "0x"
    if ty.startswith("bytes"):
        return "0x" + "00" * int(ty[5:])
    return "0"


def calldata_of(contract, fn, **over):
    f = contract._fn[fn]
    args = [zero(i) for i in f["inputs"]]
    return "0x" + contract.calldata(fn, *args).hex()


def test_forwarding_call_decodes_a_direct_requestaccess_and_returns_its_parts():
    v, pbc, dbc, cs = make()
    pbc.tx = {"to": cs["PSC"].address.upper().replace("0X", "0x"), "input": calldata_of(cs["PSC"], "requestAccess")}
    c = v.forwarding_call(H)
    assert c["to"] == cs["PSC"].address and c["method"] == "requestAccess" and set(c) == {"to", "method", "request", "signature", "bundle"}
    assert isinstance(c["request"], dict) and "gid" in c["request"] and c["bundle"] is not None


def test_forwarding_call_reports_another_method_without_a_request_and_garbage_as_none():
    v, pbc, dbc, cs = make()
    pbc.tx = {"to": cs["PSC"].address, "input": "0x" + cs["PSC"].selector("seal").hex()}
    assert v.forwarding_call(H) == {"to": cs["PSC"].address, "method": "seal", "request": None, "signature": None, "bundle": None}
    for tx in ({"to": cs["PSC"].address, "input": "0x1234"}, {"to": cs["PSC"].address, "input": "0xdeadbeef00"}, {"to": cs["PSC"].address}, {"to": cs["PSC"].address, "input": 5},
               {"to": None, "input": "0x"}):
        pbc.tx = tx
        assert v.forwarding_call(H) is None


def test_forwarding_call_of_a_contract_creation_has_an_empty_target():
    v, pbc, dbc, cs = make()
    pbc.tx = {"to": None, "input": "0x" + cs["PSC"].selector("seal").hex()}
    assert v.forwarding_call(H)["to"] == ""


# --------------------------------------------------------------------------------------------------------------------------------------------------------
CALLS = [("observe", lambda v: v.observe("pbc")), ("pbc_block", lambda v: v.pbc_block(1)), ("now", lambda v: v.now("pbc")), ("reads_at", lambda v: v.reads_at(1)),
         ("governance_nonce", lambda v: v.governance_nonce()), ("is_authority", lambda v: v.is_authority(A)), ("removed_authority", lambda v: v.removed_authority(A)),
         ("psc_request", lambda v: v.psc_request(H)), ("credentials", lambda v: v.credentials(A, {}, 1, 1)), ("forwarded_logs", lambda v: v.forwarded_logs(H)),
         ("grant_issued_logs", lambda v: v.grant_issued_logs(H)), ("dbc_current_checkpoint", lambda v: v.dbc_current_checkpoint()), ("nonce_consumed", lambda v: v.nonce_consumed(A, 1)),
         ("policy_satisfied", lambda v: v.policy_satisfied(H, [])), ("grant", lambda v: v.grant(H)), ("forwarding_call", lambda v: v.forwarding_call(H))]


@pytest.mark.parametrize("mode", ["call", "abi", "block", "now", "logs", "tx", "chain"])
def test_every_failure_mode_of_the_client_is_ledger_unreachable_for_the_methods_that_use_it(mode):
    uses = {"call": {"reads_at", "governance_nonce", "is_authority", "removed_authority", "psc_request", "credentials", "dbc_current_checkpoint", "nonce_consumed", "policy_satisfied", "grant"},
            "abi": {"reads_at", "governance_nonce", "is_authority", "removed_authority", "psc_request", "credentials", "dbc_current_checkpoint", "nonce_consumed", "policy_satisfied", "grant"},
            "block": {"observe", "pbc_block"}, "now": {"now"}, "logs": {"forwarded_logs", "grant_issued_logs"}, "tx": {"forwarding_call"}, "chain": {"pbc_block"}}[mode]
    for name, fn in CALLS:
        if name not in uses:
            continue
        v, pbc, dbc, cs = make()
        for c in (pbc, dbc):
            c.fail = mode
        with pytest.raises(LedgerUnreachable):
            fn(v)


def test_a_revert_and_an_unusable_answer_are_ledger_unreachable():
    v, pbc, dbc, cs = make()
    answer(pbc, cs["TMSC"], "isAuthority", Rejected("EXPIRED"))
    with pytest.raises(LedgerUnreachable):
        v.is_authority(A)
    answer(dbc, cs["KSSC"], "getGrant", ["only", "three", "values"])
    with pytest.raises(LedgerUnreachable):
        v.grant(H)
    answer(dbc, cs["KSSC"], "currentCheckpoint", "not a pair")
    with pytest.raises(LedgerUnreachable):
        v.dbc_current_checkpoint()
    pbc.blocks[5] = {"timestamp": "0x10"}                                    # a block without a hash
    with pytest.raises(LedgerUnreachable):
        v.pbc_block(5)
    pbc.logs = [{"transactionHash": H, "blockNumber": "not hex"}]
    with pytest.raises(LedgerUnreachable):
        v.forwarded_logs(H)
    dbc.logs = [{"blockNumber": "0x1"}]                                      # no blockHash
    with pytest.raises(LedgerUnreachable):
        v.grant_issued_logs(H)
    answer(pbc, cs["TMSC"], "checkCredentials", "code and records")
    with pytest.raises(LedgerUnreachable):
        v.credentials(A, {}, 1, 1)


def test_caller_bugs_are_value_errors():
    v, pbc, dbc, cs = make()
    for bad in (lambda: v.observe("nowhere"), lambda: v.now(None), lambda: v.pbc_block(-1), lambda: v.pbc_block(True), lambda: v.pbc_block("1"), lambda: v.reads_at(-1), lambda: v.reads_at(1.5),
                lambda: v.psc_request("0x12"), lambda: v.psc_request(H.upper().replace("0X", "0x")), lambda: v.forwarded_logs("abc"), lambda: v.grant_issued_logs(5),
                lambda: v.forwarding_call("0x12"), lambda: v.grant("0x12"), lambda: v.policy_satisfied("0x12", []), lambda: v.credentials(A, {}, 1, -1)):
        with pytest.raises(ValueError):
            bad()
    assert pbc.calls == [] and dbc.calls == []                               # refused before anything was asked


def test_without_a_governance_contract_the_governance_read_is_a_value_error():
    v, pbc, dbc, cs = make(skip=("Governance",))
    with pytest.raises(ValueError):
        v.governance_nonce()
    assert v.observe("pbc")["chainId"] == "18545"


def test_constructor_validation():
    cs = contracts()
    ok = dict(chains={"pbc": FakeChain(1), "dbc": FakeChain(2)}, contracts=cs)
    rwv.RpcWitnessView(**ok)
    rwv.RpcWitnessView(**dict(ok, contracts=contracts(skip=("Governance",))))
    for bad in (dict(ok, chains={"pbc": FakeChain(1)}), dict(ok, contracts={k: v for k, v in cs.items() if k != "KSSC"}), dict(ok, contracts=dict(cs, Extra=cs["PSC"])),
                dict(ok, contracts=dict(cs, PSC="not a contract")), dict(ok, contracts=dict(cs, PSC=Contract(ABIS["PSC"], "0xABC"))), dict(ok, contracts=dict(cs, PSC=Contract(ABIS["PSC"], None)))):
        with pytest.raises(ValueError):
            rwv.RpcWitnessView(**bad)


class Client:
    def __init__(self, chain_id):
        self.chain_id = chain_id


def clients():
    return {s: Client(int(F2["chains"][s]["chainId"])) for s in ("pbc", "dbc")}


def test_from_manifest_loads_every_contract_of_the_manifest_with_its_pinned_abi():
    v = rwv.RpcWitnessView.from_manifest(F2, clients(), ABI_DIR)
    assert set(v._c) == {"PSC", "TMSC", "Governance", "KSSC", "ACSC"}
    assert v._c["KSSC"].address == F2["chains"]["dbc"]["contracts"]["KSSC"] and v._c["Governance"].address == F2["chains"]["pbc"]["contracts"]["Governance"]


def test_from_manifest_refuses_a_wrong_chain_client_a_changed_or_missing_abi_and_a_manifest_without_pins(tmp_path):
    bad_clients = clients()
    bad_clients["dbc"] = Client(1)
    with pytest.raises(ValueError):
        rwv.RpcWitnessView.from_manifest(F2, bad_clients, ABI_DIR)
    with pytest.raises(ValueError):
        rwv.RpcWitnessView.from_manifest(F2, {"pbc": Client(18545)}, ABI_DIR)
    d = tmp_path / "abi"
    d.mkdir()
    for n in ABIS:
        (d / (n + ".json")).write_bytes(open(os.path.join(ABI_DIR, n + ".json"), "rb").read())
    (d / "PSC.json").write_bytes((d / "PSC.json").read_bytes() + b" ")
    with pytest.raises(ValueError):
        rwv.RpcWitnessView.from_manifest(F2, clients(), str(d))
    (d / "PSC.json").unlink()
    with pytest.raises(ValueError):
        rwv.RpcWitnessView.from_manifest(F2, clients(), str(d))
    import copy
    m = copy.deepcopy(F2)
    del m["abi"]["TMSC"]["abiSha256"]
    with pytest.raises(ValueError):
        rwv.RpcWitnessView.from_manifest(m, clients(), ABI_DIR)


def test_the_module_reads_no_clock_no_thread_no_socket_and_no_environment():
    src = open(os.path.join(ROOT, "protocol", "hmbc_protocol", "rpc_witness_view.py")).read()
    for banned in ("import time", "datetime", "import threading", "import socket", "import random", "subprocess", "os.environ", "import urllib"):
        assert banned not in src, banned
