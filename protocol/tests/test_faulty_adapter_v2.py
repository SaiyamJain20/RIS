"""The TEST-ONLY alternate successor adapter entry `testtools.faulty_adapter_v2` (agent 2, proposal P3 of A2-0074). Written BEFORE the module existed.

    python -m testtools.faulty_adapter_v2 <the six adapter flags> [--allow-governance FILE]
        [--witness-variant I=crash:before_commit|crash:after_commit|delay:MS[:kind[:before|after]]]...  [--worker-variant compromised --claims FILE]

It serves `hmbc_protocol.adapter_v2_main` (production bytes unchanged) and, IN ITS OWN PROCESS ONLY, (a) wraps `build_runtime` so the supervisor gets the keyword-only `command_for` seam that makes witness I run
`testtools.faulty_witness` (H4) or `testtools.delayed_witness` (H6) with the production witness's own arguments, and (b) makes the adapter's worker the TEST-ONLY `CompromisedWorker` (H5) with the claims of FILE.
This file: the offline part (parsing, every refusal as a real process, the exact argv per variant, the wiring with the REAL supervisor class but nothing spawned, the production-equivalence of a run with no variant,
the static production boundary). The behaviour against a real ledger with real children is in test_faulty_adapter_v2_live.py (rows F-13, F-20, F-19).
"""
import argparse
import json
import os
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
E1 = os.path.join(FX, "deployment-agent1-91add8c-v1-repaired-e.json")
ENV = {"PYTHONPATH": PROTO, "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}


def sys_path():
    if PROTO not in sys.path:
        sys.path.insert(0, PROTO)


def mods():
    sys_path()
    from hmbc_protocol import adapter_v2_main as am
    from hmbc_protocol import witness_process_transport as wpt
    from testtools import faulty_adapter_v2 as fa
    return fa, am, wpt


def base_flags(tmp_path, deployment=F2):
    return ["--deployment", deployment, "--abi-dir", ABI_DIR, "--schema", SCHEMA, "--schema-sha256", SCHEMA_SHA, "--schema-revision", "v2", "--state-dir", str(tmp_path / "state")]


def run(args, stdin=""):
    return subprocess.run([sys.executable, "-B", "-m", "testtools.faulty_adapter_v2", *args], input=stdin, capture_output=True, text=True, cwd=PROTO, env=ENV, timeout=60)


def one_refusal(p, tmp_path):
    """Exactly one JSON line on stderr, code MALFORMED, nothing on stdout, exit 2, no traceback, no path and no key in it, nothing created and nothing spawned."""
    assert p.returncode == 2 and p.stdout == "" and "Traceback" not in p.stderr, (p.returncode, p.stdout, p.stderr[-300:])
    lines = p.stderr.strip().splitlines()
    assert len(lines) == 1, lines
    obj = json.loads(lines[0])
    assert set(obj) == {"error"} and obj["error"]["code"] == "MALFORMED" and obj["error"]["message"].startswith("refusing: "), obj
    for forbidden in (str(tmp_path), ABI_DIR, FX, "0x" + "ab" * 32):
        assert forbidden not in p.stderr
    assert not os.path.exists(tmp_path / "state") and not list(tmp_path.glob("**/witness-*.pid"))
    return obj["error"]["message"]


def claim(**over):
    c = {"requestDigest": "0x" + "e1" * 32, "dataId": "0x" + "d1" * 32, "gid": "0x" + "a1" * 20, "recipientKeyRef": "keyref:user:alice"}
    c.update(over)
    return c


def write(tmp_path, name, content):
    f = tmp_path / name
    f.write_bytes(content if isinstance(content, bytes) else json.dumps(content).encode())
    return str(f)


# ---- the variant syntax ----------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("0=crash:before_commit", (0, "crash", "before_commit", None, None, None)),
    ("3=crash:after_commit", (3, "crash", "after_commit", None, None, None)),
    ("1=delay:0", (1, "delay", None, 0, None, None)),
    ("1=delay:60000", (1, "delay", None, 60000, None, None)),
    ("2=delay:6000:decision", (2, "delay", None, 6000, "decision", None)),
    ("2=delay:6000:decision:before", (2, "delay", None, 6000, "decision", "before")),
    ("2=delay:5:receipt:after", (2, "delay", None, 5, "receipt", "after")),
    ("1=delay:7:governance", (1, "delay", None, 7, "governance", None)),
])
def test_a_valid_witness_variant_parses_to_exactly_its_parts(text, expected):
    fa, _, _ = mods()
    v = fa.parse_variant(text)
    assert (v.index, v.name, v.point, v.delay_ms, v.only_kind, v.when) == expected


@pytest.mark.parametrize("text", ["4=crash:after_commit", "-1=crash:after_commit", "01=crash:after_commit", "a=crash:after_commit", "١=crash:after_commit", "=crash:after_commit", "1=crash:", "1=crash:during",
                                  "1=crash:after_commit:x", "1=delay:60001", "1=delay:-1", "1=delay:007", "1=delay:1e3", "1=delay:", "1=delay:5:nope", "1=delay:5:decision:nope", "1=delay:5:before",
                                  "1=delay:5:decision:before:extra", "1=teleport:5", "1 = delay:5", "1=Delay:5", "", "crash:after_commit", "1", "1=", "1=delay:٥"])
def test_every_malformed_witness_variant_is_refused(text):
    fa, _, _ = mods()
    with pytest.raises(ValueError):
        fa.parse_variant(text)


def test_the_delay_bound_is_the_delayed_witness_bound():
    sys_path()
    fa, _, _ = mods()
    from testtools import delayed_witness as dw
    assert fa.MAX_DELAY_MS == dw.MAX_DELAY_MS == 60000
    assert fa.parse_variant(f"0=delay:{dw.MAX_DELAY_MS}").delay_ms == 60000
    with pytest.raises(ValueError):
        fa.parse_variant(f"0=delay:{dw.MAX_DELAY_MS + 1}")


# ---- the command seam ------------------------------------------------------------------------------------------------------------------------------------

def default_command(wpt, index, allow=None):
    return wpt.witness_main_argv(deployment="/d/dep.json", abi_dir="/d/abi", state_dir="/d/state", index=index, key_label=f"witness-{index + 1}", allow_governance=allow, python="/py")


def test_command_for_substitutes_exactly_the_named_witnesses_and_keeps_the_production_command_for_the_others():
    fa, _, wpt = mods()
    variants = {1: fa.parse_variant("1=crash:after_commit"), 2: fa.parse_variant("2=delay:6000:decision:before")}
    cf = fa.command_for_variants(variants)
    d0, d1, d2, d3 = (default_command(wpt, i, allow="/d/allow.json") for i in range(4))
    assert cf(0, d0) == d0 and cf(3, d3) == d3
    assert d1[:4] == ["/py", "-B", "-m", "hmbc_protocol.witness_main"]
    assert cf(1, d1) == ["/py", "-B", "-m", "testtools.faulty_witness", "--crash-at", "after_commit", *d1[4:]]
    assert cf(2, d2) == ["/py", "-B", "-m", "testtools.delayed_witness", "--delay-ms", "6000", "--only-kind", "decision", "--when", "before", *d2[4:]]
    assert "--allow-governance" in cf(1, d1) and cf(1, d1)[-2:] == ["--allow-governance", "/d/allow.json"]        # the production arguments, the approval list included, are carried over verbatim


@pytest.mark.parametrize("text,flags", [("1=crash:before_commit", ["--crash-at", "before_commit"]), ("1=delay:5", ["--delay-ms", "5"]), ("1=delay:5:receipt", ["--delay-ms", "5", "--only-kind", "receipt"]),
                                         ("1=delay:5:receipt:after", ["--delay-ms", "5", "--only-kind", "receipt", "--when", "after"])])
def test_the_variant_flags_are_exactly_the_hook_commands_documented_flags(text, flags):
    fa, _, wpt = mods()
    d1 = default_command(wpt, 1)
    out = fa.command_for_variants({1: fa.parse_variant(text)})(1, d1)
    assert out[4:4 + len(flags)] == flags and out[4 + len(flags):] == d1[4:]


def test_command_for_does_not_touch_an_index_without_a_variant_even_for_an_empty_table():
    fa, _, wpt = mods()
    cf = fa.command_for_variants({})
    for i in range(4):
        d = default_command(wpt, i)
        assert cf(i, d) == d


# ---- splitting the command line ---------------------------------------------------------------------------------------------------------------------------

def test_split_arguments_keeps_the_adapter_flags_verbatim_and_in_order(tmp_path):
    fa, _, _ = mods()
    base = base_flags(tmp_path) + ["--allow-governance", "/x/allow.json"]
    argv = base[:4] + ["--witness-variant", "1=crash:after_commit"] + base[4:8] + ["--worker-variant", "compromised", "--claims", "/x/c.json"] + base[8:] + ["--witness-variant=2=delay:9"]
    parsed = fa.split_arguments(argv)
    assert parsed.base == base
    assert [v.index for v in parsed.variants] == [1, 2] and parsed.worker == "compromised" and parsed.claims == "/x/c.json"


def test_split_arguments_without_any_variant_returns_the_arguments_untouched(tmp_path):
    fa, _, _ = mods()
    base = base_flags(tmp_path)
    parsed = fa.split_arguments(base)
    assert parsed.base == base and parsed.variants == [] and parsed.worker is None and parsed.claims is None


# ---- every refusal, as a real process ---------------------------------------------------------------------------------------------------------------------

def non_test_only(tmp_path):
    m = json.load(open(F2))
    m["fixture"]["keyDerivation"] = "production HSM"
    return write(tmp_path, "prod.json", m)


REFUSALS = {
    "unknown-variant-name": lambda t: ["--witness-variant", "1=teleport:5"],
    "bad-variant-syntax": lambda t: ["--witness-variant", "crash:after_commit"],
    "index-above-range": lambda t: ["--witness-variant", "4=crash:after_commit"],
    "index-negative": lambda t: ["--witness-variant=-1=crash:after_commit"],
    "index-negative-separate-value": lambda t: ["--witness-variant", "-1=crash:after_commit"],
    "variant-flag-without-value": lambda t: ["--witness-variant"],
    "claims-flag-without-value": lambda t: ["--claims"],
    "delay-above-bound": lambda t: ["--witness-variant", "1=delay:60001"],
    "repeated-index": lambda t: ["--witness-variant", "1=crash:after_commit", "--witness-variant", "1=delay:5"],
    "worker-variant-without-claims": lambda t: ["--worker-variant", "compromised"],
    "claims-without-worker-variant": lambda t: ["--claims", write(t, "c.json", [claim()])],
    "unknown-worker-variant": lambda t: ["--worker-variant", "evil", "--claims", write(t, "c.json", [claim()])],
    "claims-not-json": lambda t: ["--worker-variant", "compromised", "--claims", write(t, "c.json", b"not json")],
    "claims-not-a-list": lambda t: ["--worker-variant", "compromised", "--claims", write(t, "c.json", {})],
    "claims-not-utf8": lambda t: ["--worker-variant", "compromised", "--claims", write(t, "c.json", b"\xff\xfe")],
    "claims-nested": lambda t: ["--worker-variant", "compromised", "--claims", write(t, "c.json", b"[" * 5000 + b"]" * 5000)],
    "claims-missing-file": lambda t: ["--worker-variant", "compromised", "--claims", str(t / "nope.json")],
    "claim-missing-field": lambda t: ["--worker-variant", "compromised", "--claims", write(t, "c.json", [{k: v for k, v in claim().items() if k != "gid"}])],
    "claim-extra-field": lambda t: ["--worker-variant", "compromised", "--claims", write(t, "c.json", [claim(extra="x")])],
    "claim-bad-address": lambda t: ["--worker-variant", "compromised", "--claims", write(t, "c.json", [claim(gid="0xabc")])],
    "claim-bad-digest": lambda t: ["--worker-variant", "compromised", "--claims", write(t, "c.json", [claim(requestDigest="0x12")])],
    "claim-bad-key-ref": lambda t: ["--worker-variant", "compromised", "--claims", write(t, "c.json", [claim(recipientKeyRef="alice")])],
    "claims-duplicate-json-key": lambda t: ["--worker-variant", "compromised", "--claims", write(t, "c.json", ('[{"requestDigest": "0x' + "e1" * 32 + '", "requestDigest": "0x' + "e2" * 32 + '", "dataId": "0x' + "d1" * 32
                                                                                                          + '", "gid": "0x' + "a1" * 20 + '", "recipientKeyRef": "keyref:user:alice"}]').encode())],
    "claim-duplicate-digest": lambda t: ["--worker-variant", "compromised", "--claims", write(t, "c.json", [claim(), claim()])],
}


def expected_message(name):
    fa, _, _ = mods()
    if name in ("repeated-index",):
        return fa.MSG_REPEATED
    if name == "unknown-worker-variant":
        return fa.MSG_WORKER
    if name == "worker-variant-without-claims":
        return fa.MSG_NEEDS_CLAIMS
    if name == "claims-without-worker-variant":
        return fa.MSG_NEEDS_WORKER
    if name in ("index-negative-separate-value", "variant-flag-without-value", "claims-flag-without-value"):
        return fa.MSG_FLAGS
    if name.startswith("claim"):
        return fa.MSG_CLAIMS
    return fa.MSG_VARIANT


@pytest.mark.parametrize("name", sorted(REFUSALS))
def test_a_bad_hook_request_is_one_closed_refusal_for_the_right_reason_before_anything_is_created_or_spawned(tmp_path, name):
    p = run(base_flags(tmp_path) + REFUSALS[name](tmp_path))
    assert one_refusal(p, tmp_path) == expected_message(name)


def test_a_deployment_that_does_not_declare_test_only_keys_is_refused_whatever_the_variants(tmp_path):
    for extra in ([], ["--witness-variant", "1=crash:after_commit"]):
        p = run(base_flags(tmp_path, deployment=non_test_only(tmp_path)) + extra)
        assert one_refusal(p, tmp_path) == mods()[0].MSG_DEPLOYMENT and "TEST-ONLY" in mods()[0].MSG_DEPLOYMENT


@pytest.mark.parametrize("content", [b"not json", b"[]", b"\xff", b'{"a": 1, "a": 2}'], ids=["not-json", "array", "not-utf8", "duplicate-key"])
def test_an_unusable_deployment_file_is_one_closed_refusal(tmp_path, content):
    assert one_refusal(run(base_flags(tmp_path, deployment=write(tmp_path, "dep.json", content)) + ["--witness-variant", "1=crash:after_commit"]), tmp_path) == mods()[0].MSG_DEPLOYMENT


def test_a_missing_deployment_file_is_one_closed_refusal(tmp_path):
    assert one_refusal(run(base_flags(tmp_path, deployment=str(tmp_path / "nope.json"))), tmp_path) == mods()[0].MSG_DEPLOYMENT


def test_a_missing_adapter_flag_is_refused_exactly_as_the_production_command_refuses_it(tmp_path):
    base = base_flags(tmp_path)
    i = base.index("--schema-sha256")
    p = run(base[:i] + base[i + 2:] + ["--witness-variant", "1=crash:after_commit"])
    q = subprocess.run([sys.executable, "-B", "-m", "hmbc_protocol.adapter_v2_main", *(base[:i] + base[i + 2:])], capture_output=True, text=True, cwd=PROTO, env=ENV, timeout=60)
    assert p.returncode == q.returncode == 2 and p.stdout == q.stdout == "" and "the following arguments are required: --schema-sha256" in p.stderr
    assert p.stderr.splitlines()[-1].split(": error: ", 1)[1] == q.stderr.splitlines()[-1].split(": error: ", 1)[1]


def test_an_abbreviated_hook_flag_is_not_a_hook_flag_so_a_typo_can_never_silently_arm_a_fault(tmp_path):
    p = run(base_flags(tmp_path) + ["--witness-var", "1=crash:after_commit"])
    assert p.returncode == 2 and p.stdout == "" and "unrecognized arguments" in p.stderr and not os.path.exists(tmp_path / "state")


# ---- the wiring: the REAL supervisor class, nothing spawned ------------------------------------------------------------------------------------------------

def args_for(tmp_path, **over):
    a = dict(deployment=F2, abi_dir=ABI_DIR, schema=SCHEMA, schema_sha256=SCHEMA_SHA, schema_revision="v2", state_dir=str(tmp_path / "state"), allow_governance=None)
    a.update(over)
    return argparse.Namespace(**a)


def restoring(monkeypatch, am):
    """Record the module attributes the entry patches so pytest restores them whatever the test does."""
    monkeypatch.setattr(am, "build_runtime", am.build_runtime)
    monkeypatch.setattr(am, "Worker", am.Worker)


def test_installed_witness_variants_reach_the_real_supervisors_effective_commands(tmp_path, monkeypatch):
    fa, am, wpt = mods()
    restoring(monkeypatch, am)
    fa.install({1: fa.parse_variant("1=crash:after_commit"), 3: fa.parse_variant("3=delay:6000")}, None)
    ctx, sup = am.build_runtime(args_for(tmp_path), start=lambda **kw: "CONTEXT")
    assert ctx == "CONTEXT" and isinstance(sup, wpt.WitnessSupervisor) and not sup.children and callable(sup.command_for)
    cmds = sup._effective_commands()
    modules = [c[c.index("-m") + 1] for c in cmds]
    assert modules == ["hmbc_protocol.witness_main", "testtools.faulty_witness", "hmbc_protocol.witness_main", "testtools.delayed_witness"]
    assert cmds[1][4:6] == ["--crash-at", "after_commit"] and cmds[3][4:6] == ["--delay-ms", "6000"]
    assert cmds[0] == sup.commands[0] and cmds[2] == sup.commands[2]                                              # the other two are the production commands, byte for byte
    for i, c in enumerate(cmds):
        assert c[c.index("--index") + 1] == str(i) and c[c.index("--key-label") + 1] == f"witness-{i + 1}" and c[c.index("--deployment") + 1] == F2


def test_an_explicit_supervisor_factory_still_wins_over_the_installed_one(tmp_path, monkeypatch):
    fa, am, _ = mods()
    restoring(monkeypatch, am)
    fa.install({1: fa.parse_variant("1=crash:after_commit")}, None)
    import types
    sentinel = types.SimpleNamespace(transport_factory=lambda kind: None)
    ctx, sup = am.build_runtime(args_for(tmp_path), start=lambda **kw: "CONTEXT", supervisor_factory=lambda **kw: sentinel)
    assert sup is sentinel


def test_the_installed_worker_variant_makes_the_adapters_worker_a_compromised_worker_with_the_claims(tmp_path, monkeypatch):
    fa, am, _ = mods()
    sys_path()
    from hmbc_protocol import eip712
    from hmbc_protocol.ledger import Ledger
    from hmbc_protocol.worker import Worker
    from testtools.compromised_worker import CompromisedWorker
    restoring(monkeypatch, am)
    fa.install({}, [claim()])
    assert am.Worker is not Worker
    led = Ledger.from_deployment(json.load(open(E1)))           # the E fixture: the carried Ledger loads the bundled E ABIs, which the F fixture does not match
    w = am.Worker(led, str(tmp_path / "w"), clock=lambda: 0)
    assert isinstance(w, CompromisedWorker)
    gid = "0x" + eip712.grant_id(bytes.fromhex(claim()["requestDigest"][2:]), led.KSSC.address, led.dbc.chain_id).hex()
    assert list(w.claims) == [gid]


def test_install_without_a_witness_variant_leaves_build_runtime_alone_and_without_claims_leaves_the_worker_alone(tmp_path, monkeypatch):
    fa, am, _ = mods()
    restoring(monkeypatch, am)
    runtime, worker = am.build_runtime, am.Worker
    fa.install({}, None)
    assert am.build_runtime is runtime and am.Worker is worker


# ---- a run with no variant is the production entry ----------------------------------------------------------------------------------------------------------

def test_main_without_any_variant_hands_the_adapter_flags_to_the_production_main_untouched_and_patches_nothing(tmp_path, monkeypatch):
    fa, am, _ = mods()
    restoring(monkeypatch, am)
    runtime, worker = am.build_runtime, am.Worker
    seen = {}

    def fake_main(argv=None, stdin=None, stdout=None, stderr=None):
        seen.update(argv=argv, patched=(am.build_runtime is not runtime, am.Worker is not worker))
        return 7
    monkeypatch.setattr(am, "main", fake_main)
    base = base_flags(tmp_path) + ["--allow-governance", str(tmp_path / "a.json")]
    assert fa.main(base) == 7 and seen["argv"] == base and seen["patched"] == (False, False)


def test_main_with_variants_patches_then_delegates_with_only_the_adapter_flags(tmp_path, monkeypatch):
    fa, am, _ = mods()
    restoring(monkeypatch, am)
    seen = {}
    runtime, worker = am.build_runtime, am.Worker
    monkeypatch.setattr(am, "main", lambda argv=None, stdin=None, stdout=None, stderr=None: seen.update(argv=argv, patched=(am.build_runtime is not runtime, am.Worker is not worker)) or 0)
    base = base_flags(tmp_path)
    assert fa.main(["--witness-variant", "2=delay:5"] + base) == 0 and seen["argv"] == base and seen["patched"] == (True, False)    # the supervisor seam is installed, the worker is untouched


def test_main_with_a_worker_variant_installs_the_compromised_worker_and_not_the_supervisor_seam(tmp_path, monkeypatch):
    fa, am, _ = mods()
    restoring(monkeypatch, am)
    runtime, worker = am.build_runtime, am.Worker
    seen = {}
    monkeypatch.setattr(am, "main", lambda argv=None, stdin=None, stdout=None, stderr=None: seen.update(argv=argv, patched=(am.build_runtime is not runtime, am.Worker is not worker)) or 0)
    base = base_flags(tmp_path)
    assert fa.main(base + ["--worker-variant", "compromised", "--claims", write(tmp_path, "c.json", [claim()])]) == 0
    assert seen["argv"] == base and seen["patched"] == (False, True)


def test_a_run_with_no_variant_ends_exactly_as_the_production_entry_does_on_an_unreachable_node(tmp_path):
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    m = json.load(open(F2))
    m["chains"]["pbc"]["rpcUrl"] = m["chains"]["dbc"]["rpcUrl"] = f"http://127.0.0.1:{port}"
    dep = write(tmp_path, "dep.json", m)
    mine_ = run(base_flags(tmp_path, deployment=dep))
    prod = subprocess.run([sys.executable, "-B", "-m", "hmbc_protocol.adapter_v2_main", *base_flags(tmp_path, deployment=dep)], capture_output=True, text=True, cwd=PROTO, env=ENV, timeout=60)
    assert mine_.returncode == prod.returncode == 2 and mine_.stdout == prod.stdout == "" and mine_.stderr == prod.stderr
    assert json.loads(mine_.stderr)["error"]["reason"] == "LEDGER_UNREACHABLE"                                   # it really went through the production startup


# ---- the production boundary --------------------------------------------------------------------------------------------------------------------------------

def test_the_entry_is_not_part_of_the_production_adapter_boundary():
    for name in sorted(os.listdir(os.path.join(PROTO, "hmbc_protocol"))):
        if name.endswith(".py"):
            text = open(os.path.join(PROTO, "hmbc_protocol", name)).read()
            assert "faulty_adapter_v2" not in text and "testtools" not in text, name
    manifest = open(os.path.join(PROTO, "exports", "adapter.json")).read()
    for word in ("faulty_adapter_v2", "compromised", "delayed_witness", "faulty_witness", "testtools", "witness-variant", "worker-variant"):
        assert word not in manifest, word
    code = "import sys, hmbc_protocol.adapter_v2_main, hmbc_protocol.witness_main, hmbc_protocol.witness_process_transport; print(any(m.startswith('testtools') for m in sys.modules))"
    p = subprocess.run([sys.executable, "-c", code], cwd=PROTO, env=ENV, capture_output=True, text=True, timeout=60)
    assert p.stdout.strip() == "False", p.stderr


def test_the_entry_module_imports_no_clock_thread_socket_or_environment_of_its_own():
    src = open(os.path.join(PROTO, "testtools", "faulty_adapter_v2.py")).read()
    for banned in ("os.environ", "import socket", "import threading", "import random", "datetime"):
        assert banned not in src, banned
