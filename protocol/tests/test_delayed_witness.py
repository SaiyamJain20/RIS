"""TEST-ONLY delay injection H6 for a witness PROCESS (agent 2, F task 3; INVENTORY section 4 row F-20). Written BEFORE testtools/delayed_witness.py existed.

    python -m testtools.delayed_witness --delay-ms N [--only-kind checkpoint|decision|receipt|governance] [--when before|after] <the arguments of hmbc_protocol.witness_main>

serves the PRODUCTION witness process and holds the answer to a matching request for N milliseconds of REAL time:
  --when after   (default) the request is processed at once and the REPLY is held: the durable record exists while the caller still waits (a slow reply, a slow network back);
  --when before  the REQUEST is held and processed afterwards: nothing is recorded while it is held (a slow network out; the "delivery hold" of the pool schedules).
Without `--only-kind` every signing kind is delayed; a line that is not a well-formed request (no parsable kind) is never delayed. The production witness is unchanged: with the hook installed and the
delay applied, every reply is byte for byte the production reply (tested against an un-hooked server on the same lines).

Offline tests (no chain) drive the real `witness_main.serve` loop in a child process with a stub service that timestamps its own calls on the monotonic clock, so the hold position is MEASURED, not assumed.
LIVE tests (`test_live_*`, real Anvil + agent 1's F ledger snapshot 85c59f5, skipped when Foundry or the commit is missing): a real witness process, the deterministic signature, and a SIGKILL during the hold.
Real-time thresholds are generous on purpose (a delayed reply must take at least the delay and less than delay + 3 s; an undelayed one less than 0.5 s); a heavily loaded host can still make a fast-path check slow.
"""
import json
import os
import socket
import subprocess
import sys
import time

import pytest

from hmbc_protocol import witness_state as ws
from testtools import state_oracle

from test_faulty_witness import HookProc, expected_signature, imported_modules, production, two_checkpoints  # noqa: F401
from test_rpc_binding_view_live import live_f  # noqa: F401  (a fixture)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROTO = os.path.join(ROOT, "protocol")
FX = os.path.join(PROTO, "tests", "fixtures")
ABI_DIR = os.path.join(FX, "agent1-85c59f5-abi")
F2 = os.path.join(FX, "agent1-85c59f5-f-base-deployment.json")
MODULE = "testtools.delayed_witness"
ENV = {"PYTHONPATH": PROTO, "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}
KINDS = ("checkpoint", "decision", "receipt", "governance")
DELAY = 800                                   # ms
FAST = 0.5                                    # s: an undelayed stub reply
SLACK = 3.0                                   # s: allowed overshoot of a delayed reply


def run(args, timeout=60):
    return subprocess.run([sys.executable, "-B", "-m", MODULE, *args], capture_output=True, text=True, cwd=PROTO, env=ENV, timeout=timeout)


def wm_args(tmp_path, **over):
    a = {"--deployment": F2, "--abi-dir": ABI_DIR, "--index": "0", "--key-label": "witness-1", "--state-dir": str(tmp_path / "state")}
    a.update(over)
    return [x for kv in a.items() if kv[1] is not None for x in kv]


def refused_with(p, text):
    assert p.returncode != 0 and p.stdout == "" and "Traceback" not in p.stderr, (p.returncode, p.stdout, p.stderr)
    assert p.stderr.startswith("refusing:") and text in p.stderr, p.stderr


# ---- offline: refusals ----------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("value", [None, "", "-1", "1.5", "1e3", "1_0", " 5", "+5", "007", "60001", "abc", "٣"])
def test_the_hook_refuses_a_missing_or_non_canonical_or_excessive_delay_and_creates_nothing(tmp_path, value):
    args = ["--delay-ms", value] if value is not None else []
    refused_with(run(args + wm_args(tmp_path)), "--delay-ms")
    assert not os.path.exists(tmp_path / "state")


@pytest.mark.parametrize("value", ["0", "1", "800", "60000"])
def test_the_hook_accepts_a_canonical_delay_up_to_sixty_seconds(tmp_path, value):
    """Accepted means: it gets as far as the PRODUCTION startup, which (no node) refuses closed with exit 2 and ONE JSON line."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    m = json.load(open(F2))
    m["chains"]["pbc"]["rpcUrl"] = m["chains"]["dbc"]["rpcUrl"] = f"http://127.0.0.1:{port}"
    f = tmp_path / "dep.json"
    f.write_text(json.dumps(m))
    hooked = run(["--delay-ms", value] + wm_args(tmp_path, **{"--deployment": str(f), "--state-dir": str(tmp_path / "h")}))
    prod = subprocess.run([sys.executable, "-B", "-m", "hmbc_protocol.witness_main", *wm_args(tmp_path, **{"--deployment": str(f), "--state-dir": str(tmp_path / "p")})], capture_output=True, text=True,
                          cwd=PROTO, env=ENV, timeout=60)
    assert hooked.returncode == prod.returncode == 2 and hooked.stdout == ""
    assert json.loads(hooked.stderr) == json.loads(prod.stderr) and json.loads(hooked.stderr)["error"]["reason"] == "LEDGER_UNREACHABLE"
    assert not os.path.exists(tmp_path / "h")


@pytest.mark.parametrize("flag,value", [("--only-kind", "nonsense"), ("--only-kind", ""), ("--only-kind", "CHECKPOINT"), ("--only-kind", "checkpoint,decision"), ("--when", "during"), ("--when", ""), ("--when", "AFTER")])
def test_the_hook_refuses_an_unknown_kind_or_hold_position(tmp_path, flag, value):
    refused_with(run(["--delay-ms", "10", flag, value] + wm_args(tmp_path)), flag)
    assert not os.path.exists(tmp_path / "state")


def test_the_hook_refuses_a_non_test_only_deployment_and_an_unreadable_one(tmp_path):
    m = json.load(open(F2))
    m["fixture"]["keyDerivation"] = "production HSM"
    f = tmp_path / "dep.json"
    f.write_text(json.dumps(m))
    refused_with(run(["--delay-ms", "10"] + wm_args(tmp_path, **{"--deployment": str(f)})), "TEST-ONLY")
    for content in (b"{", b"[]", b"\xff\xfe", b'{"a": 1, "a": 2}'):
        g = tmp_path / "bad.json"
        g.write_bytes(content)
        refused_with(run(["--delay-ms", "10"] + wm_args(tmp_path, **{"--deployment": str(g)})), "")
    refused_with(run(["--delay-ms", "10"] + wm_args(tmp_path, **{"--deployment": None})), "--deployment")
    assert not os.path.exists(tmp_path / "state")


# ---- offline: what main() hands to install() ------------------------------------------------------------------------------------------------------------------

def test_main_passes_the_delay_the_kind_and_the_default_hold_position_to_install_and_the_rest_to_the_production_process(tmp_path, monkeypatch):
    sys.path.insert(0, PROTO)
    from testtools import delayed_witness as dw
    seen = {}
    monkeypatch.setattr(dw, "install", lambda *a, **k: seen.update(install=(a, k)))
    monkeypatch.setattr(dw.witness_main, "main", lambda argv: seen.update(argv=list(argv)) or 0)
    base = wm_args(tmp_path)
    assert dw.main(["--delay-ms", "250"] + base) == 0
    assert seen["install"] == ((250, None, "after"), {})                         # the default hold position is AFTER, the default kind is every kind
    assert seen["argv"][:2] == ["--deployment", F2] and "--delay-ms" not in seen["argv"] and "--when" not in seen["argv"]      # the production process never sees the hook's own flags
    assert dw.main(["--delay-ms", "7", "--only-kind", "receipt", "--when", "before"] + base) == 0
    assert seen["install"] == ((7, "receipt", "before"), {})


# ---- offline: the hold, measured on the real serve loop with a stub service ----------------------------------------------------------------------------------

CHILD = r'''
import sys, time
sys.dont_write_bytecode = True
from hmbc_protocol import witness_main as wm
mode = sys.argv[1]
if mode != "plain":
    from testtools import delayed_witness as dw
    delay, kind, when = int(sys.argv[2]), (sys.argv[3] or None), sys.argv[4]
    dw.install(delay, kind, when)

class Stub:
    def _s(self, name, message):
        sys.stderr.write("called %s %.6f\n" % (name, time.monotonic()))
        sys.stderr.flush()
        return "0x" + "11" * 65
    def sign_checkpoint(self, m): return self._s("checkpoint", m)
    def sign_decision(self, m): return self._s("decision", m)
    def sign_receipt(self, m): return self._s("receipt", m)
    def sign_governance(self, m): return self._s("governance", m)

raise SystemExit(wm.serve(sys.stdin.buffer, sys.stdout, Stub()))
'''


class Child:
    def __init__(self, mode="hooked", delay=DELAY, kind="", when="after"):
        self.p = subprocess.Popen([sys.executable, "-B", "-c", CHILD, mode, str(delay), kind, when], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=PROTO, env=ENV)
        self.n = 0
        self.lines = []
        self.warm()

    def warm(self):
        """One unparsable line: the serve loop is running (and, by design, an unparsable line is never delayed)."""
        self.p.stdin.write("warm-up\n")
        self.p.stdin.flush()
        assert json.loads(self.p.stdout.readline())["reply"]["code"] == "MALFORMED"

    def raw(self, text):
        self.p.stdin.write(text + "\n")
        self.p.stdin.flush()

    def ask(self, kind, round_no=1):
        """(reply object, seconds until the reply, seconds until the stub service was called or None)."""
        self.n += 1
        line = json.dumps({"schemaVersion": "hmbc-witness-rpc/v1", "id": self.n, "round": round_no, "kind": kind, "message": {"k": kind}})
        t0 = time.monotonic()
        self.raw(line)
        out = self.p.stdout.readline()
        t1 = time.monotonic()
        self.lines.append(out)
        reply = json.loads(out)
        called = None
        if reply["reply"]["type"] == "signature":
            c = self.p.stderr.readline().split()
            assert c[0] == "called" and c[1] == kind
            called = float(c[2]) - t0
        return reply, t1 - t0, called

    def close(self):
        self.p.stdin.close()
        rc = self.p.wait(timeout=30)
        self.p.stdout.close()
        self.p.stderr.close()
        return rc


def test_a_matching_reply_is_held_for_the_delay_while_the_service_ran_at_once_by_default():
    c = Child(kind="checkpoint")
    try:
        reply, took, called = c.ask("checkpoint")
        assert reply["reply"]["type"] == "signature" and DELAY / 1000 <= took < DELAY / 1000 + SLACK, took
        assert called is not None and called < FAST, called                    # `after`: the state changed at once, only the reply was held
    finally:
        assert c.close() == 0


def test_when_before_the_request_is_held_and_the_service_runs_only_after_the_hold():
    c = Child(kind="checkpoint", when="before")
    try:
        reply, took, called = c.ask("checkpoint")
        assert reply["reply"]["type"] == "signature" and DELAY / 1000 <= took < DELAY / 1000 + SLACK, took
        assert called is not None and called >= DELAY / 1000 - 0.01, called    # `before`: nothing happened while the request was held
    finally:
        assert c.close() == 0


def test_only_the_selected_kind_is_delayed():
    c = Child(kind="decision")
    try:
        _r, took_other, _c = c.ask("checkpoint")
        assert took_other < FAST, took_other
        _r, took, _c = c.ask("decision")
        assert DELAY / 1000 <= took < DELAY / 1000 + SLACK, took
    finally:
        assert c.close() == 0


def test_without_only_kind_every_signing_kind_is_delayed():
    c = Child(delay=300)
    try:
        for kind in KINDS:
            _r, took, _c = c.ask(kind)
            assert 0.3 <= took < 0.3 + SLACK, (kind, took)
    finally:
        assert c.close() == 0


def test_a_line_without_a_parsable_kind_and_an_unknown_kind_are_never_delayed():
    c = Child(delay=3000)
    try:
        for text in ("not json", "[]", '{"kind": 3}', '{"id": 1}', json.dumps({"schemaVersion": "hmbc-witness-rpc/v1", "id": 9, "round": 1, "kind": "nonsense", "message": {}})):
            t0 = time.monotonic()
            c.raw(text)
            reply = json.loads(c.p.stdout.readline())
            assert reply["reply"]["code"] == "MALFORMED" and time.monotonic() - t0 < FAST, text
    finally:
        assert c.close() == 0


def test_a_zero_delay_is_a_plain_pass_through():
    c = Child(delay=0)
    try:
        for kind in KINDS:
            _r, took, _c = c.ask(kind)
            assert took < FAST, (kind, took)
    finally:
        assert c.close() == 0


@pytest.mark.parametrize("when", ["after", "before"])
def test_the_production_reply_is_unchanged_byte_for_byte(when):
    """The same request lines to an un-hooked server and to the delayed one give identical reply lines."""
    plain, hooked = Child("plain"), Child(delay=100, when=when)
    try:
        for kind in KINDS:
            plain.ask(kind)
            hooked.ask(kind)
        assert plain.lines == hooked.lines and len(plain.lines) == 4
    finally:
        assert plain.close() == 0 and hooked.close() == 0


# ---- offline: the static production boundary ----------------------------------------------------------------------------------------------------------------

def test_the_hook_is_not_part_of_the_production_boundary():
    pkg = os.path.join(PROTO, "hmbc_protocol")
    for name in sorted(os.listdir(pkg)):
        if name.endswith(".py"):
            src = open(os.path.join(pkg, name)).read()
            assert not any(m == "testtools" or m.startswith("testtools.") for m in imported_modules(src)), name
            assert "delayed_witness" not in src, name
    for dirpath, _dirs, files in os.walk(os.path.join(PROTO, "exports")):
        for fn in files:
            text = open(os.path.join(dirpath, fn)).read()
            assert "delayed_witness" not in text and "delay-ms" not in text and "testtools" not in text, fn


def test_the_hook_module_is_loudly_test_only_and_never_prints_a_key():
    src = open(os.path.join(PROTO, "testtools", "delayed_witness.py")).read()
    assert "TEST-ONLY" in src.split('"""')[1]
    assert "synthetic_private_key" not in src and "print(" not in src


# ---- LIVE: a real witness process, the real chains --------------------------------------------------------------------------------------------------------

def wait_for(pred, timeout=60.0, step=0.05):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(step)
    return False


def test_live_f20_a_real_witness_process_answers_after_the_delay_with_the_deterministic_signature(live_f, tmp_path):
    a, _b = two_checkpoints(live_f)
    p = HookProc(live_f, tmp_path, 1, module=MODULE, extra=["--delay-ms", "1200", "--only-kind", "checkpoint"])
    try:
        assert wait_for(lambda: os.path.exists(os.path.join(p.state_dir, "witness-1", "INITIALIZED")))      # started: from here the request is read at once
        t0 = time.monotonic()
        reply = p.ask("checkpoint", a)
        took = time.monotonic() - t0
        assert reply["type"] == "signature" and reply["message"] == a and reply["signature"] == expected_signature(live_f, 1, a)
        assert 1.2 <= took < 1.2 + SLACK + 3, took
    finally:
        assert p.finish() == (0, "")


def test_live_a_kill_during_an_after_hold_leaves_the_record_and_during_a_before_hold_leaves_nothing(live_f, tmp_path):
    a, b = two_checkpoints(live_f)
    # --when after: the record is committed while the reply is held; the kill finds it durable and the restart is pinned to it
    held = HookProc(live_f, tmp_path, 3, module=MODULE, extra=["--delay-ms", "6000", "--when", "after"])
    store_dir = os.path.join(held.state_dir, "witness-3")
    held.send_line(json.dumps({"schemaVersion": "hmbc-witness-rpc/v1", "id": 1, "round": 1, "kind": "checkpoint", "message": a}))
    def recorded():
        try:
            return len(ws.view_for_export(store_dir).evidence()["conflicts"]) == 1
        except ws.StoreError:
            return False
    assert wait_for(recorded), "the record never appeared while the reply was held"
    held.p.kill()
    held.finish()
    restart = production(live_f, tmp_path, 3)
    try:
        r = restart.ask("checkpoint", b)
        assert r["type"] == "error" and r["reason"] == "CONFLICT_PINNED" and r["recorded"]["message"] == a, r
    finally:
        assert restart.close() == (0, "")
    # --when before: the request is held, nothing is recorded, the kill leaves the store untouched and a different value signs after the restart
    first = production(live_f, tmp_path, 2)
    assert first.close() == (0, "")
    store2 = os.path.join(str(tmp_path / "wstate"), "witness-2")
    baseline = state_oracle.logical_snapshot(store2)
    held2 = HookProc(live_f, tmp_path, 2, module=MODULE, extra=["--delay-ms", "6000", "--when", "before"])
    held2.send_line(json.dumps({"schemaVersion": "hmbc-witness-rpc/v1", "id": 1, "round": 1, "kind": "checkpoint", "message": a}))
    time.sleep(1.5)                                                                                         # long after startup, well inside the 6 s hold
    assert state_oracle.logical_snapshot(store2) == baseline                                                 # nothing recorded while the request is held
    held2.p.kill()
    held2.finish()
    restart2 = production(live_f, tmp_path, 2)
    try:
        r = restart2.ask("checkpoint", b)
        assert r["type"] == "signature" and r["message"] == b and r["signature"] == expected_signature(live_f, 2, b), r
    finally:
        assert restart2.close() == (0, "")
