"""TEST-ONLY crash hook H4 for a witness PROCESS (agent 2, F task 3; INVENTORY section 4 row F-13). Written BEFORE testtools/faulty_witness.py existed.

    python -m testtools.faulty_witness --crash-at before_commit|after_commit <the arguments of hmbc_protocol.witness_main>

serves the PRODUCTION witness process and ends it with os._exit(86) at the first signing request that REACHES the named point of the durable store (the store's own `crash_hook` seam, injected by patching
`witness_state.init_store`/`open_store` inside the hook's own process; no existing file is edited):
  before_commit  the signing transaction is open and nothing is committed: nothing is signed, no reply, the restart finds no record;
  after_commit   the record is durable (WAL, synchronous=FULL) and no reply was written: the restart replies with the RECORDED value and never signs a second one (row F-13).
A request that does not reach the point (a malformed line, a refusal before the commit, an idempotent re-sign that is a pure read) is an ordinary reply and the process lives on.

Offline tests (no chain): the refusals, the `install()` seam through a real child process on a real store, the pass-through of the production startup refusal, the static production boundary.
LIVE tests (`test_live_*`, real Anvil + agent 1's F ledger snapshot 85c59f5, skipped when Foundry or the commit is missing): the F-13 rows with a real witness process. A simulated crash at two logical
points after or before a durable commit: process death only, never power-loss durability.
"""
import hashlib
import json
import os
import socket
import subprocess
import sys
import time

import pytest

from eth_account import Account

from hmbc_protocol import keys, witness_service as svc, witness_state as ws
from testtools import state_oracle
from testtools.byzantine import sign_message

from test_rpc_binding_view_live import live_f, mine, witness_view  # noqa: F401  (live_f is a fixture)
from test_witness_state import B, BIND, DBC, DOM_S, OWNER, cp_effect, h, obs, signer

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROTO = os.path.join(ROOT, "protocol")
FX = os.path.join(PROTO, "tests", "fixtures")
ABI_DIR = os.path.join(FX, "agent1-85c59f5-abi")
F2 = os.path.join(FX, "agent1-85c59f5-f-base-deployment.json")
MODULE = "testtools.faulty_witness"
CRASH_EXIT = 86
ENV = {"PYTHONPATH": PROTO, "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}


def run(args, cwd=PROTO, timeout=60):
    return subprocess.run([sys.executable, "-B", "-m", MODULE, *args], capture_output=True, text=True, cwd=cwd, env=ENV, timeout=timeout)


def wm_args(tmp_path, **over):
    a = {"--deployment": F2, "--abi-dir": ABI_DIR, "--index": "0", "--key-label": "witness-1", "--state-dir": str(tmp_path / "state")}
    a.update(over)
    return [x for kv in a.items() if kv[1] is not None for x in kv]


def refused_with(p, text):
    """The hook's own refusal: non-zero exit, nothing on stdout, `refusing:` on stderr, no traceback."""
    assert p.returncode != 0 and p.stdout == "" and "Traceback" not in p.stderr, (p.returncode, p.stdout, p.stderr)
    assert p.stderr.startswith("refusing:") and text in p.stderr, p.stderr


# ---- offline: the hook refuses before it touches anything --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("point", [None, "", "after_intent", "after_send", "BEFORE_COMMIT", "before_commit,after_commit", "commit"])
def test_the_hook_refuses_a_missing_or_unknown_crash_point_and_creates_nothing(tmp_path, point):
    args = ["--crash-at", point] if point is not None else []
    p = run(args + wm_args(tmp_path))
    refused_with(p, "--crash-at")
    assert not os.path.exists(tmp_path / "state")


def test_the_hook_refuses_a_deployment_that_does_not_declare_test_only_keys_before_any_io(tmp_path):
    m = json.load(open(F2))
    m["fixture"]["keyDerivation"] = "production HSM"
    f = tmp_path / "dep.json"
    f.write_text(json.dumps(m))
    refused_with(run(["--crash-at", "after_commit"] + wm_args(tmp_path, **{"--deployment": str(f)})), "TEST-ONLY")
    assert not os.path.exists(tmp_path / "state")


@pytest.mark.parametrize("content", [b"{", b"[]", b"null", b'{"a": 1, "a": 2}', b"\xff\xfe", b"{}"], ids=["truncated", "array", "null", "duplicate-key", "not-utf8", "no-fixture"])
def test_the_hook_refuses_an_unreadable_or_non_manifest_deployment_cleanly(tmp_path, content):
    f = tmp_path / "dep.json"
    f.write_bytes(content)
    p = run(["--crash-at", "after_commit"] + wm_args(tmp_path, **{"--deployment": str(f)}))
    refused_with(p, "")
    assert not os.path.exists(tmp_path / "state")


def test_the_hook_refuses_a_missing_deployment_argument_and_a_missing_file(tmp_path):
    refused_with(run(["--crash-at", "after_commit"] + wm_args(tmp_path, **{"--deployment": None})), "--deployment")
    refused_with(run(["--crash-at", "after_commit"] + wm_args(tmp_path, **{"--deployment": str(tmp_path / "nope.json")})), "")
    assert not os.path.exists(tmp_path / "state")


# ---- offline: the pass-through of the production startup ----------------------------------------------------------------------------------------------------

def test_with_valid_arguments_and_no_node_the_hook_ends_exactly_like_the_production_process(tmp_path):
    """The hook is never reached before the first signing request: with nothing listening, startup is refused by the PRODUCTION code (LEDGER_UNREACHABLE, exit 2, ONE JSON line), identically."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    m = json.load(open(F2))
    m["chains"]["pbc"]["rpcUrl"] = m["chains"]["dbc"]["rpcUrl"] = f"http://127.0.0.1:{port}"
    f = tmp_path / "dep.json"
    f.write_text(json.dumps(m))
    hooked = run(["--crash-at", "after_commit"] + wm_args(tmp_path, **{"--deployment": str(f), "--state-dir": str(tmp_path / "h")}))
    prod = subprocess.run([sys.executable, "-B", "-m", "hmbc_protocol.witness_main", *wm_args(tmp_path, **{"--deployment": str(f), "--state-dir": str(tmp_path / "p")})], capture_output=True, text=True,
                          cwd=PROTO, env=ENV, timeout=60)
    assert hooked.returncode == prod.returncode == 2 and hooked.stdout == prod.stdout == ""
    assert json.loads(hooked.stderr) == json.loads(prod.stderr) and json.loads(hooked.stderr)["error"]["reason"] == "LEDGER_UNREACHABLE"
    assert not os.path.exists(tmp_path / "h") and not os.path.exists(tmp_path / "p")


# ---- offline: the install() seam on a real store, through a real child process --------------------------------------------------------------------------------

CHILD = r'''
import hashlib, json, os, sys
sys.dont_write_bytecode = True
from testtools import faulty_witness as fw
from hmbc_protocol import witness_state as ws
point, action, cfg = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
fw.install(point)
def signer(d):
    return "0x" + (hashlib.sha256(d.encode()).hexdigest() * 3)[:130]
st = ws.init_store(cfg["dir"], cfg["binding_v2"], cfg["document"], cfg["owner"])
if action == "init":
    print("init-complete")
    raise SystemExit(0)
sig = st.sign(type="StateCheckpoint", domain=cfg["domain"], wsv="2", key="4", effect=cfg["effect"], expires_at=cfg["expires_at"], digest=cfg["digest"], signer=signer, observe=lambda: cfg["obs"])
print("signature-returned " + sig)
'''


def child(d, point, action="sign", label="d1", block=138):
    cfg = json.dumps({"dir": d, "binding_v2": BIND, "document": B, "owner": OWNER, "domain": DOM_S, "effect": cp_effect(block), "expires_at": "1791521610", "digest": h(label), "obs": obs(DBC, 159, 1791521590)})
    return subprocess.run([sys.executable, "-B", "-c", CHILD, point, action, cfg], capture_output=True, text=True, cwd=PROTO, env=ENV, timeout=60)


def other_effect(st):
    """A different valid effect for the same live key 4."""
    return st.sign(type="StateCheckpoint", domain=DOM_S, wsv="2", key="4", effect=cp_effect(139), expires_at="1791521610", digest=h("x"), signer=signer, observe=lambda: obs(DBC, 160, 1791521591))


def test_install_after_commit_kills_with_86_after_the_durable_record_and_the_restart_is_pinned_to_it(tmp_path):
    d = str(tmp_path / "w0")
    ws.init_store(d, BIND, B, OWNER)
    r = child(d, "after_commit")
    assert r.returncode == CRASH_EXIT and "signature-returned" not in r.stdout and r.stdout == ""
    st = ws.open_store(d, BIND, OWNER)
    assert len(st.evidence()["conflicts"]) == 1                                           # durable although no reply ever left the process
    with pytest.raises(ws.StoreError) as e:
        other_effect(st)
    assert e.value.reason == "CONFLICT_PINNED" and e.value.recorded["signature"] == signer(h("d1"))
    assert st.sign(type="StateCheckpoint", domain=DOM_S, wsv="2", key="4", effect=cp_effect(138), expires_at="1791521610", digest=h("d1"), signer=signer, observe=lambda: obs(DBC, 160, 1791521591)) == signer(h("d1"))


def test_install_before_commit_kills_with_86_and_signs_nothing(tmp_path):
    d = str(tmp_path / "w0")
    ws.init_store(d, BIND, B, OWNER)
    before = state_oracle.logical_snapshot(d)
    r = child(d, "before_commit")
    assert r.returncode == CRASH_EXIT and r.stdout == ""
    assert state_oracle.logical_snapshot(d) == before                                     # the open transaction died with the process
    st = ws.open_store(d, BIND, OWNER)
    assert other_effect(st) == signer(h("x"))                                             # nothing was pinned: a different value signs


def test_a_pure_read_re_sign_never_reaches_the_point_so_the_process_is_not_killed(tmp_path):
    """The hook fires only for a request that REACHES the point: an idempotent re-sign of an already recorded value commits nothing, so it passes under both points."""
    d = str(tmp_path / "w0")
    st = ws.init_store(d, BIND, B, OWNER)
    st.sign(type="StateCheckpoint", domain=DOM_S, wsv="2", key="4", effect=cp_effect(138), expires_at="1791521610", digest=h("d1"), signer=signer, observe=lambda: obs(DBC, 159, 1791521590))
    st.close()
    for point in ("before_commit", "after_commit"):
        r = child(d, point)
        assert r.returncode == 0 and r.stdout.strip() == "signature-returned " + signer(h("d1")), (point, r.stdout, r.stderr[-300:])


@pytest.mark.parametrize("point", ["before_commit", "after_commit"])
def test_the_stores_other_hook_points_do_not_fire_during_initialisation(tmp_path, point):
    r = child(str(tmp_path / "fresh"), point, action="init")
    assert r.returncode == 0 and r.stdout.strip() == "init-complete", (r.returncode, r.stdout, r.stderr[-300:])


# ---- offline: the static production boundary ----------------------------------------------------------------------------------------------------------------

def imported_modules(src):
    import ast
    out = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            out.add(("." * node.level) + (node.module or ""))
            out.update(("." * node.level) + (node.module or "") + "." + a.name for a in node.names)
    return out


def test_the_hook_is_not_part_of_the_production_boundary():
    pkg = os.path.join(PROTO, "hmbc_protocol")
    for name in sorted(os.listdir(pkg)):
        if name.endswith(".py"):
            src = open(os.path.join(pkg, name)).read()
            assert not any(m == "testtools" or m.startswith("testtools.") for m in imported_modules(src)), name       # no production module imports a test tool
            assert "faulty_witness" not in src, name
    for dirpath, _dirs, files in os.walk(os.path.join(PROTO, "exports")):
        for fn in files:
            text = open(os.path.join(dirpath, fn)).read()
            assert "faulty_witness" not in text and "crash-at" not in text and "testtools" not in text, fn
    code = "import sys, hmbc_protocol.adapter_v2_main, hmbc_protocol.witness_main; print(any('testtools' in m for m in sys.modules))"
    p = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, cwd=PROTO, env=ENV, timeout=60)
    assert p.stdout.strip() == "False", p.stderr


def test_the_hook_module_is_loudly_test_only_and_never_prints_a_key():
    src = open(os.path.join(PROTO, "testtools", "faulty_witness.py")).read()
    assert "TEST-ONLY" in src.split('"""')[1] and "os._exit" in src
    assert "synthetic_private_key" not in src and "print(" not in src


# ---- LIVE: a real witness process, the real chains --------------------------------------------------------------------------------------------------------

class HookProc:
    """A witness process started with `python -m <module> <extra> --deployment ...`, speaking the witness RPC. EOF is a legal answer: the hook kills the process by design."""

    def __init__(self, live, tmp_path, index, module=MODULE, extra=(), state="wstate"):
        dep_file = tmp_path / "dep.json"
        dep_file.write_text(json.dumps(live.dep))
        self.state_dir = str(tmp_path / state)
        args = ["--deployment", str(dep_file), "--abi-dir", live.abi_dir, "--index", str(index), "--key-label", "witness-%d" % (index + 1), "--state-dir", self.state_dir]
        self.p = subprocess.Popen([sys.executable, "-B", "-m", module, *extra, *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=PROTO, env=ENV)
        self.n = 0

    def send_line(self, text):
        self.p.stdin.write(text + "\n")
        self.p.stdin.flush()

    def ask_raw(self, kind, message, round_no=1):
        """The raw answer line, or '' at EOF."""
        self.n += 1
        self.send_line(json.dumps({"schemaVersion": "hmbc-witness-rpc/v1", "id": self.n, "round": round_no, "kind": kind, "message": message}))
        return self.p.stdout.readline()

    def ask(self, kind, message, round_no=1):
        line = self.ask_raw(kind, message, round_no)
        assert line, "the witness process died: " + self.p.stderr.read()
        out = json.loads(line)
        assert out["id"] == self.n
        return out["reply"]

    def alive(self):
        return self.p.poll() is None

    def finish(self, timeout=30):
        try:
            self.p.stdin.close()
        except OSError:
            pass
        rc = self.p.wait(timeout=timeout)
        err = self.p.stderr.read()
        self.p.stdout.close()
        self.p.stderr.close()
        return rc, err


def two_checkpoints(live):
    """A valid checkpoint A and a different valid checkpoint B for the same sequence (the older source block), as the carried live restart test builds them."""
    wview, chains = witness_view(live)
    mine(live, "pbc")
    mine(live, "pbc")
    mine(live, "dbc")
    a = svc.derive_checkpoint(wview, live.dep)
    n = int(a["sourceBlockNumber"])
    b = dict(a, sourceBlockNumber=str(n - 1), sourceBlockHash=chains["pbc"].get_block(n - 1)["hash"])
    return a, b


def expected_signature(live, index, message):
    key = keys.synthetic_private_key("witness-%d" % (index + 1))
    assert Account.from_key(key).address.lower() == live.dep["fixture"]["witnessSet"]["witnesses"][index]
    return sign_message(key, "StateCheckpoint", message, live.dep)


def production(live, tmp_path, index):
    from test_rpc_binding_view_live import WitnessProc
    return WitnessProc(live, tmp_path, index)


def test_live_f13_a_kill_after_the_commit_leaves_the_pin_and_the_restart_replies_with_the_recorded_value(live_f, tmp_path):
    a, b = two_checkpoints(live_f)
    dying = HookProc(live_f, tmp_path, 3, extra=["--crash-at", "after_commit"])
    assert dying.ask_raw("checkpoint", a) == ""                                           # no reply line: the process died after the commit and before answering
    rc, err = dying.finish()
    assert rc == CRASH_EXIT and err == "", (rc, err)
    restart = production(live_f, tmp_path, 3)                                             # the PRODUCTION command on the same state directory
    try:
        same = restart.ask("checkpoint", a)
        assert same["type"] == "signature" and same["message"] == a
        assert same["signature"] == expected_signature(live_f, 3, a)                      # the recorded value is exactly what an honest witness would have signed (RFC 6979)
        other = restart.ask("checkpoint", b)
        assert other["type"] == "error" and other["code"] == "STALE_STATE" and other["reason"] == "CONFLICT_PINNED", other
        assert other["recorded"] == {"message": a, "signature": same["signature"]}        # never a second value
    finally:
        assert restart.close() == (0, "")


def test_live_f13_a_kill_before_the_commit_signs_nothing_and_a_different_value_signs_after_the_restart(live_f, tmp_path):
    a, b = two_checkpoints(live_f)
    first = production(live_f, tmp_path, 2)                                               # initialise the store, ask nothing, stop: the baseline snapshot
    assert first.close() == (0, "")
    store_dir = os.path.join(str(tmp_path / "wstate"), "witness-2")
    baseline = state_oracle.logical_snapshot(store_dir)
    dying = HookProc(live_f, tmp_path, 2, extra=["--crash-at", "before_commit"])
    assert dying.ask_raw("checkpoint", a) == ""
    rc, err = dying.finish()
    assert rc == CRASH_EXIT and err == ""
    assert state_oracle.logical_snapshot(store_dir) == baseline                           # nothing durable
    restart = production(live_f, tmp_path, 2)
    try:
        r = restart.ask("checkpoint", b)
        assert r["type"] == "signature" and r["message"] == b and r["signature"] == expected_signature(live_f, 2, b), r      # no pin: B signs
    finally:
        assert restart.close() == (0, "")


def test_live_a_request_that_does_not_reach_the_point_gets_an_ordinary_reply_and_the_process_lives_until_one_does(live_f, tmp_path):
    a, _b = two_checkpoints(live_f)
    p = HookProc(live_f, tmp_path, 1, extra=["--crash-at", "after_commit"])
    p.send_line("this is not json")
    out = json.loads(p.p.stdout.readline())
    assert out["id"] is None and out["reply"]["type"] == "error" and out["reply"]["code"] == "MALFORMED"
    assert p.alive()
    bad_kind = json.loads(p.ask_raw("nonsense", a))
    assert bad_kind["reply"]["code"] == "MALFORMED" and p.alive()
    assert p.ask_raw("checkpoint", a) == ""                                               # now a request reaches the point
    rc, err = p.finish()
    assert rc == CRASH_EXIT and err == ""
