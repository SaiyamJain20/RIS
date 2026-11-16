"""TEST-ONLY real-PROCESS divergent ledger view (H3; F-plan gap G2). Written BEFORE `testtools/divergent_witness.py` existed. PAPER-DERIVED RECONSTRUCTION; synthetic TEST-ONLY keys.

    python -m testtools.divergent_witness --view SPEC <the production witness's own arguments>
    SPEC  authEpoch:N | policyVersion:N | witnessSetVersion:N | headLag:N        (N a canonical decimal 1..50)

The witness process is the PRODUCTION one (`hmbc_protocol.witness_main`: same arguments, wire, start-up, store, exit codes) with ONE difference inside this process: the `RpcWitnessView` it reads the real
chains through is wrapped so that its reads DIVERGE from the real ledger:
  authEpoch:N, policyVersion:N, witnessSetVersion:N   `reads_at(n)` returns the real value + N for that field;
  headLag:N                                           the PBC the witness sees is N blocks behind: `observe("pbc")` reports block head-N and `pbc_block(n)` is None for n above it.
Everything else is delegated to the real view unchanged. D50 start-up uses the real, unwrapped binding view, so the process starts normally. This breaks the safe-ledger assumption BY DESIGN (INVENTORY H3) and
is for the conditional rows only. The unit tests use a fake inner view; the live process tests are in test_rpc_binding_view_live.py.
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROTO = os.path.join(ROOT, "protocol")
FX = os.path.join(PROTO, "tests", "fixtures")
F2 = os.path.join(FX, "agent1-85c59f5-f-base-deployment.json")
E21 = os.path.join(FX, "agent1-85c59f5-e-successor-v2.1-deployment.json")
sys.path.insert(0, PROTO)


def dw():
    from testtools import divergent_witness
    return divergent_witness


class Inner:
    def __init__(self):
        self.calls = []
        self.head = 100

    def reads_at(self, n):
        self.calls.append(("reads_at", n))
        return {"authEpoch": str(3 + n), "policyVersion": "1", "witnessSetVersion": "2"}          # depends on the block, so a wrongly shifted block shows

    def observe(self, chain):
        self.calls.append(("observe", chain))
        n = self.head if chain == "pbc" else 50
        return {"chainId": "18545" if chain == "pbc" else "28545", "blockNumber": str(n), "blockHash": "0x" + "%064x" % n, "timestamp": str(5000 + n)}

    def pbc_block(self, n):
        self.calls.append(("pbc_block", n))
        return None if n > self.head else {"number": str(n), "hash": "0x" + "%064x" % n, "timestamp": str(5000 + n)}

    def governance_nonce(self):
        return "7"


@pytest.mark.parametrize("spec", ["authEpoch:1", "policyVersion:50", "witnessSetVersion:9", "headLag:7"])
def test_a_view_spec_parses_to_itself(spec):
    assert dw().parse_spec(spec) == spec


@pytest.mark.parametrize("spec", ["", "authEpoch", "authEpoch:", "authEpoch:0", "authEpoch:51", "authEpoch:01", "authEpoch:-1", "authEpoch:+1", "authEpoch:1:2", "AuthEpoch:1", "authEpoch: 1", "keyEpoch:1",
                                  "headLag", "headLag:0", "headLag:x", None, 5])
def test_every_malformed_spec_is_refused(spec):
    with pytest.raises(ValueError):
        dw().parse_spec(spec)


@pytest.mark.parametrize("field", ["authEpoch", "policyVersion", "witnessSetVersion"])
def test_a_read_divergence_adds_n_to_exactly_that_field(field):
    inner = Inner()
    v = dw().DivergentView(inner, f"{field}:4")
    real = inner.reads_at(10)
    got = v.reads_at(10)
    assert got[field] == str(int(real[field]) + 4) and {k: got[k] for k in got if k != field} == {k: real[k] for k in real if k != field}
    assert ("reads_at", 10) in inner.calls and v.observe("pbc") == inner.observe("pbc") and v.pbc_block(100) == inner.pbc_block(100)


def test_a_head_lag_reports_an_older_pbc_head_and_hides_newer_blocks_but_not_the_dbc():
    inner = Inner()
    v = dw().DivergentView(inner, "headLag:3")
    assert v.observe("pbc") == {"chainId": "18545", "blockNumber": "97", "blockHash": "0x" + "%064x" % 97, "timestamp": "5097"}
    assert v.pbc_block(97) == inner.pbc_block(97) and v.pbc_block(98) is None and v.pbc_block(100) is None and v.pbc_block(0) == inner.pbc_block(0)
    assert v.observe("dbc") == inner.observe("dbc")
    assert v.reads_at(5) == inner.reads_at(5)                                         # a head lag changes no read at a given block


def test_a_head_lag_larger_than_the_chain_clamps_at_genesis():
    inner = Inner()
    inner.head = 2
    v = dw().DivergentView(inner, "headLag:50")
    assert v.observe("pbc")["blockNumber"] == "0" and v.pbc_block(0) is not None and v.pbc_block(1) is None


def test_every_other_method_is_delegated_unchanged_and_an_unknown_one_still_raises():
    v = dw().DivergentView(Inner(), "authEpoch:1")
    assert v.governance_nonce() == "7"
    with pytest.raises(AttributeError):
        v.no_such_method()


def test_a_non_decimal_real_read_is_left_alone_not_guessed():
    class Odd(Inner):
        def reads_at(self, n):
            return {"authEpoch": "not a number", "policyVersion": "1", "witnessSetVersion": "2"}
    assert dw().DivergentView(Odd(), "authEpoch:1").reads_at(1)["authEpoch"] == "not a number"


def test_install_makes_from_manifest_return_a_divergent_view_of_what_the_original_builds_and_passes_its_arguments_on():
    from hmbc_protocol import rpc_witness_view as rwv
    original = rwv.RpcWitnessView.__dict__["from_manifest"]
    seen = {}
    inner = Inner()

    def fake(cls, *args, **kwargs):
        seen.update(cls=cls, args=args, kwargs=kwargs)
        return inner
    try:
        rwv.RpcWitnessView.from_manifest = classmethod(fake)
        dw().install("authEpoch:2")
        view = rwv.RpcWitnessView.from_manifest({"m": 1}, "chains", "abi", extra=5)
    finally:
        rwv.RpcWitnessView.from_manifest = original
    assert isinstance(view, dw().DivergentView) and view._inner is inner and (view.field, view.n) == ("authEpoch", 2)
    assert seen["cls"] is rwv.RpcWitnessView and seen["args"] == ({"m": 1}, "chains", "abi") and seen["kwargs"] == {"extra": 5}
    assert view.reads_at(4)["authEpoch"] == str(3 + 4 + 2)


def test_install_refuses_a_malformed_spec_and_leaves_from_manifest_alone():
    from hmbc_protocol import rpc_witness_view as rwv
    before = rwv.RpcWitnessView.__dict__["from_manifest"]
    for bad in ("", "authEpoch:0", "nonsense", None):
        with pytest.raises(ValueError):
            dw().install(bad)
    assert rwv.RpcWitnessView.__dict__["from_manifest"] is before


def test_a_missing_deployment_argument_is_refused(tmp_path):
    p = run(["--view", "headLag:2"])
    assert p.returncode != 0 and p.stdout == "" and "refusing: --deployment is required" in p.stderr


def run(args):
    return subprocess.run([sys.executable, "-B", "-m", "testtools.divergent_witness", *args], capture_output=True, text=True, cwd=PROTO,
                          env={"PYTHONPATH": PROTO, "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}, timeout=60)


def witness_args(tmp_path, **over):
    a = {"--deployment": F2, "--abi-dir": os.path.join(FX, "agent1-85c59f5-abi"), "--index": "0", "--key-label": "witness-1", "--state-dir": str(tmp_path / "state")}
    a.update(over)
    return [x for kv in a.items() for x in kv]


def test_a_missing_or_malformed_view_is_refused_before_anything_is_created(tmp_path):
    for extra in ([], ["--view", "authEpoch:0"], ["--view", "nonsense"], ["--view", ""]):
        p = run(extra + witness_args(tmp_path))
        assert p.returncode != 0 and p.stdout == "" and "refusing:" in p.stderr and "Traceback" not in p.stderr, (extra, p.stderr)
        assert not os.path.exists(tmp_path / "state")


def test_a_deployment_without_a_test_only_key_derivation_is_refused(tmp_path):
    m = json.load(open(F2))
    m["fixture"]["keyDerivation"] = "production HSM"
    f = tmp_path / "dep.json"
    f.write_text(json.dumps(m))
    p = run(["--view", "headLag:2"] + witness_args(tmp_path, **{"--deployment": str(f)}))
    assert p.returncode != 0 and p.stdout == "" and "refusing:" in p.stderr and not os.path.exists(tmp_path / "state")


def test_a_valid_request_reaches_the_production_witness_which_then_refuses_an_unreachable_node_cleanly(tmp_path):
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    m = json.load(open(F2))
    m["chains"]["pbc"]["rpcUrl"] = m["chains"]["dbc"]["rpcUrl"] = f"http://127.0.0.1:{port}"
    f = tmp_path / "dep.json"
    f.write_text(json.dumps(m))
    p = run(["--view", "headLag:2"] + witness_args(tmp_path, **{"--deployment": str(f)}))
    assert p.returncode == 2 and p.stdout == "" and json.loads(p.stderr.strip().splitlines()[-1])["error"]["reason"] == "LEDGER_UNREACHABLE"      # the production witness's own closed refusal


def test_the_module_reads_no_environment_clock_thread_or_socket():
    src = open(os.path.join(PROTO, "testtools", "divergent_witness.py")).read()
    for banned in ("os.environ", "import time", "datetime", "import threading", "import socket", "import random", "subprocess"):
        assert banned not in src, banned
