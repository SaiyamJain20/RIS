"""Wiring the four witness operations into the successor command line (agent 2, F task 2/3, proposals P1 and P2 of A2-0074). Written BEFORE the wiring existed.

`adapter_v2_main.build_runtime(args)` returns `(context, supervisor_or_None)`. For a `repaired-f` deployment the context is started with the witness wiring (the proposer's own `RpcWitnessView`, the four witness addresses of the pinned manifest, and
the supervisor's `transport_factory`) and the supervisor is returned UNSTARTED: it is spawned by `main` only after every startup validation has passed, so a refused startup spawns nothing and writes no pid file. For any other profile
(the carried E successor deployment) there is no supervisor and no witness wiring: the four operations stay "not wired" for that profile, exactly as before. `build_context` itself is unchanged. The optional TEST-ONLY
`--allow-governance FILE` is validated before anything is created and handed to every witness unchanged.
No chain, no process and no clock is used here: the supervisor and the start function are replaced by recorders. The real processes against a real ledger are in test_adapter_v2_main_wiring_live.py.
"""
import argparse
import io
import json
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROTO = os.path.join(ROOT, "protocol")
FX = os.path.join(PROTO, "tests", "fixtures")
ABI_DIR = os.path.join(FX, "agent1-85c59f5-abi")
SCHEMA = os.path.join(FX, "agent3-v2.1-hmbc.schema.json")
SCHEMA_SHA = "d43c3a9a4cbb10214135afb767a2adc109da462f88bd11a81a8c8955d44fd1f3"
F2 = os.path.join(FX, "agent1-85c59f5-f-base-deployment.json")
E21 = os.path.join(FX, "agent1-85c59f5-e-successor-v2.1-deployment.json")


def mods():
    if PROTO not in sys.path:
        sys.path.insert(0, PROTO)
    from hmbc_protocol import adapter_v2_main as am
    from hmbc_protocol import rpc_witness_view as rwv
    from hmbc_protocol import witness_process_transport as wpt
    return am, rwv, wpt


def args_for(tmp_path, deployment=F2, revision="v2", **over):
    a = dict(deployment=deployment, abi_dir=ABI_DIR, schema=SCHEMA, schema_sha256=SCHEMA_SHA, schema_revision=revision, state_dir=str(tmp_path / "state"), allow_governance=None)
    a.update(over)
    return argparse.Namespace(**a)


class FakeSupervisor:
    def __init__(self, events=None, start_error=None):
        self.events = events if events is not None else []
        self.start_error = start_error
        self.started = self.closed = False

    def transport_factory(self, kind):
        return ("transport", kind)

    def start(self):
        self.events.append("start")
        if self.start_error is not None:
            raise self.start_error
        self.started = True

    def close(self, grace_s=3.0):
        self.events.append("close")
        self.closed = True


class Recorder:
    def __init__(self, supervisor=None):
        self.calls, self.supervisor = [], supervisor or FakeSupervisor()

    def __call__(self, **kw):
        self.calls.append(kw)
        return self.supervisor


def capture_start():
    seen = []

    def fake_start(**kw):
        seen.append(kw)
        return "CONTEXT"
    return seen, fake_start


# ---- build_runtime ------------------------------------------------------------------------------------------------------------------------------------------

def test_a_repaired_f_deployment_gets_the_witness_wiring_and_an_unstarted_supervisor(tmp_path):
    am, rwv, _ = mods()
    seen, fake_start = capture_start()
    rec = Recorder()
    ctx, sup = am.build_runtime(args_for(tmp_path), start=fake_start, supervisor_factory=rec)
    assert ctx == "CONTEXT" and sup is rec.supervisor and not sup.started and not sup.closed          # spawned later, by main, after startup validation
    kw = seen[0]
    assert set(kw) == {"manifest", "schema_revision", "chain_view", "state_dir", "worker_factory", "schema", "witness_view", "witnesses", "transport_factory"}
    manifest = json.load(open(F2))
    assert kw["witnesses"] == manifest["fixture"]["witnessSet"]["witnesses"] and len(kw["witnesses"]) == 4
    assert isinstance(kw["witness_view"], rwv.RpcWitnessView)
    assert kw["transport_factory"]("checkpoint") == ("transport", "checkpoint")                        # it IS the supervisor's factory
    assert len(rec.calls) == 1
    c = rec.calls[0]
    assert set(c) == {"manifest", "deployment_path", "abi_dir", "state_dir", "allow_governance"}
    assert c["manifest"] == manifest and c["deployment_path"] == F2 and c["abi_dir"] == ABI_DIR and c["state_dir"] == str(tmp_path / "state") and c["allow_governance"] is None


def test_the_e_successor_deployment_gets_no_witness_wiring_and_no_supervisor(tmp_path):
    am, _, _ = mods()
    seen, fake_start = capture_start()
    rec = Recorder()
    ctx, sup = am.build_runtime(args_for(tmp_path, deployment=E21, revision="v2.1"), start=fake_start, supervisor_factory=rec)
    assert ctx == "CONTEXT" and sup is None and rec.calls == []
    assert set(seen[0]) == {"manifest", "schema_revision", "chain_view", "state_dir", "worker_factory", "schema"}


def test_build_context_is_unchanged_and_never_wires_witnesses(tmp_path):
    am, _, _ = mods()
    seen, fake_start = capture_start()
    assert am.build_context(args_for(tmp_path), start=fake_start) == "CONTEXT"
    assert set(seen[0]) == {"manifest", "schema_revision", "chain_view", "state_dir", "worker_factory", "schema"}


def test_a_valid_allow_governance_file_is_validated_and_passed_to_the_supervisor_unchanged(tmp_path):
    am, _, _ = mods()
    f = tmp_path / "allow.json"
    f.write_text(json.dumps([["1", "0x" + "ab" * 20, ["0x" + "cd" * 20]]]))
    rec = Recorder()
    am.build_runtime(args_for(tmp_path, allow_governance=str(f)), start=capture_start()[1], supervisor_factory=rec)
    assert rec.calls[0]["allow_governance"] == str(f)


@pytest.mark.parametrize("content", [b"{}", b'""', b"null", b"[1]", b'[["9", "0x' + b"00" * 20 + b'", []]]', b"[" * 5000 + b"]" * 5000, b"\xff"], ids=["object", "string", "null", "not-a-tuple", "bad-action", "deeply-nested", "not-utf8"])
def test_a_bad_allow_governance_file_is_refused_before_any_supervisor_or_state(tmp_path, content):
    am, _, _ = mods()
    f = tmp_path / "allow.json"
    f.write_bytes(content)
    seen, fake_start = capture_start()
    rec = Recorder()
    with pytest.raises(am.Refusal) as e:
        am.build_runtime(args_for(tmp_path, allow_governance=str(f)), start=fake_start, supervisor_factory=rec)
    assert e.value.code == "MALFORMED"
    assert rec.calls == [] and seen == [] and not os.path.exists(tmp_path / "state")


def test_allow_governance_on_a_non_f_deployment_is_refused_not_silently_ignored(tmp_path):
    am, _, _ = mods()
    f = tmp_path / "allow.json"
    f.write_text("[]")
    rec = Recorder()
    with pytest.raises(am.Refusal) as e:
        am.build_runtime(args_for(tmp_path, deployment=E21, revision="v2.1", allow_governance=str(f)), start=capture_start()[1], supervisor_factory=rec)
    assert e.value.code == "MALFORMED" and "repaired-f" in e.value.message and rec.calls == [] and not os.path.exists(tmp_path / "state")


def test_a_missing_allow_governance_file_is_a_closed_refusal(tmp_path):
    am, _, _ = mods()
    with pytest.raises(am.Refusal) as e:
        am.build_runtime(args_for(tmp_path, allow_governance=str(tmp_path / "nope.json")), start=capture_start()[1], supervisor_factory=Recorder())
    assert e.value.code == "MALFORMED"


def test_a_manifest_without_four_witness_labels_is_a_closed_refusal_and_spawns_nothing(tmp_path):
    am, _, wpt = mods()
    m = json.load(open(F2))
    m["fixture"]["witnessSet"]["keyLabels"] = ["witness-1"]
    f = tmp_path / "dep.json"
    f.write_text(json.dumps(m))
    with pytest.raises(am.Refusal) as e:
        am.build_runtime(args_for(tmp_path, deployment=str(f)), start=capture_start()[1])                # the REAL supervisor factory refuses
    assert e.value.code == "MALFORMED" and not os.path.exists(tmp_path / "state")


def test_the_default_supervisor_factory_is_the_real_one_and_builds_four_production_commands(tmp_path):
    am, _, wpt = mods()
    seen, fake_start = capture_start()
    ctx, sup = am.build_runtime(args_for(tmp_path), start=fake_start)
    assert isinstance(sup, wpt.WitnessSupervisor) and len(sup.commands) == 4 and not sup.children          # built, not started
    for i, cmd in enumerate(sup.commands):
        assert "hmbc_protocol.witness_main" in cmd and cmd[cmd.index("--index") + 1] == str(i) and cmd[cmd.index("--key-label") + 1] == f"witness-{i + 1}"
        assert cmd[cmd.index("--deployment") + 1] == F2 and cmd[cmd.index("--state-dir") + 1] == str(tmp_path / "state")


def test_the_parser_accepts_an_optional_allow_governance_and_still_requires_the_six_flags():
    am, _, _ = mods()
    p = am._parser()
    base = ["--deployment", "d", "--abi-dir", "a", "--schema", "s", "--schema-sha256", "0" * 64, "--schema-revision", "v2", "--state-dir", "x"]
    assert p.parse_args(base).allow_governance is None
    assert p.parse_args(base + ["--allow-governance", "f.json"]).allow_governance == "f.json"
    for drop in ("--deployment", "--abi-dir", "--schema", "--schema-sha256", "--schema-revision", "--state-dir"):
        i = base.index(drop)
        with pytest.raises(SystemExit):
            p.parse_args(base[:i] + base[i + 2:])


# ---- main -----------------------------------------------------------------------------------------------------------------------------------------------------

def run_main(am, monkeypatch, tmp_path, sup, serve=None):
    events = sup.events if sup is not None else []
    monkeypatch.setattr(am, "build_runtime", lambda args: ("CTX", sup))
    monkeypatch.setattr(am.av2, "serve", serve or (lambda stdin, stdout, ctx: events.append("serve") or 0))
    old = os.umask(0o022)
    try:
        out, err = io.StringIO(), io.StringIO()
        rc = am.main(["--deployment", F2, "--abi-dir", ABI_DIR, "--schema", SCHEMA, "--schema-sha256", SCHEMA_SHA, "--schema-revision", "v2", "--state-dir", str(tmp_path / "s")],
                     stdin=io.BytesIO(b""), stdout=out, stderr=err)
    finally:
        os.umask(old)
    return rc, out.getvalue(), err.getvalue(), events


def test_main_starts_the_supervisor_before_serving_and_always_closes_it(tmp_path, monkeypatch):
    am, _, _ = mods()
    rc, out, err, events = run_main(am, monkeypatch, tmp_path, FakeSupervisor())
    assert rc == 0 and out == "" and err == "" and events == ["start", "serve", "close"]


def test_main_closes_the_supervisor_even_when_serving_raises(tmp_path, monkeypatch):
    am, _, _ = mods()
    sup = FakeSupervisor()

    def boom(stdin, stdout, ctx):
        sup.events.append("serve")
        raise RuntimeError("serve failed")
    with pytest.raises(RuntimeError):
        run_main(am, monkeypatch, tmp_path, sup, serve=boom)
    assert sup.events == ["start", "serve", "close"]


def test_a_supervisor_that_cannot_start_is_one_closed_refusal_that_leaks_nothing_and_never_serves(tmp_path, monkeypatch):
    am, _, wpt = mods()
    sup = FakeSupervisor(start_error=wpt.SupervisorError("cannot write the pid file /home/someone/secret"))
    rc, out, err, events = run_main(am, monkeypatch, tmp_path, sup)
    assert rc == 2 and out == "" and events == ["start", "close"]                                          # no "serve"
    lines = err.strip().splitlines()
    assert len(lines) == 1 and "/home/someone" not in lines[0] and "Traceback" not in lines[0]
    obj = json.loads(lines[0])
    assert set(obj) == {"error"} and obj["error"]["code"] == "ADAPTER_UNAVAILABLE"


def test_main_without_a_supervisor_serves_exactly_as_before(tmp_path, monkeypatch):
    am, _, _ = mods()
    rc, out, err, events = run_main(am, monkeypatch, tmp_path, None)
    assert rc == 0 and err == "" and events == ["serve"]
