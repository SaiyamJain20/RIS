"""Startup refusal boundary at BOTH command-line entry points (agent 2; answer to A3-0096 and A3-0097). Written BEFORE the fix.

A3 reproduced two escapes: a PBC/DBC chainId written as the JSON number 1e999 (uncaught OverflowError traceback, exit 1) and a schema file that hashes correctly but parses to a non-object
(AttributeError traceback; for `null` the CLI would even start WITHOUT response checking). The same lenient `int()` and bare `json.loads` appear at more sites (rpc_binding_view, rpc_witness_view,
binding_open, the allow-list reader), so this file tests the CLASS instead of the two lines: every corrupt LOCAL input must end in ONE closed refusal (code MALFORMED), before any chain is asked and with no
state created, at both entry points. Corrupt local configuration only: nothing here is a remote attack or an authorization bypass.

Method: the builders (`adapter_v2_main.build_context`, `witness_main.build_service`) are called in-process with the chain-opening step replaced by a function that fails the test if it is reached, so an
escaping OverflowError/AttributeError/RecursionError is a test error and a lenient accept (the process would go on and ask the chain) is a test failure. A few real subprocess runs pin the exit code,
the single JSON line on stderr and the absence of a traceback.
"""
import argparse
import hashlib
import io
import json
import os
import shutil
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
RAW = "@@RAW@@"
NEST = 200000

# JSON tokens that are NOT a canonical unsigned decimal string. `1e999` and `1.5` become float; "1_0", " 5", "+5" and the Arabic-Indic digit are all accepted by Python's int(); 18545 as a bare number is
# not the interface's decimal-string encoding.
UINT_RAW = ["1e999", "-1", "true", "null", "[]", "{}", "1.5", "18545", '"1_0"', '" 5"', '"+5"', '"0x10"', '"007"', '"\\u0663"', '""', '"' + "9" * 79 + '"']
DEPTH = (b"[" * NEST) + (b"]" * NEST)


def sys_path():
    if PROTO not in sys.path:
        sys.path.insert(0, PROTO)


def manifest_file(tmp_path, path, raw, name="dep.json"):
    """F2 with the JSON token at `path` replaced by `raw` (text level, so a token like 1e999 survives)."""
    m = json.load(open(F2))
    node = m
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = RAW
    f = tmp_path / name
    f.write_text(json.dumps(m).replace(json.dumps(RAW), raw))
    return str(f)


def adapter_args(tmp_path, **over):
    a = dict(deployment=F2, abi_dir=ABI_DIR, schema=SCHEMA, schema_sha256=SCHEMA_SHA, schema_revision="v2", state_dir=str(tmp_path / "state"))
    a.update(over)
    return argparse.Namespace(**a)


def witness_args(tmp_path, **over):
    a = dict(deployment=F2, abi_dir=ABI_DIR, index="0", key_label="witness-1", state_dir=str(tmp_path / "state"), allow_governance=None)
    a.update(over)
    return argparse.Namespace(**a)


def never_reached(*_args, **_kwargs):
    raise AssertionError("startup went on to ask the chain although its configuration is corrupt")


def build(entry, args, monkeypatch):
    """The entry point's builder with the first step that talks to a chain replaced by a failing stub."""
    sys_path()
    from hmbc_protocol import adapter_v2_main as am
    from hmbc_protocol import binding_open as bo
    from hmbc_protocol import witness_main as wm
    if entry == "adapter_v2_main":
        return am.build_context(args, start=never_reached)
    monkeypatch.setattr(bo, "open_witness_store", never_reached)
    return wm.build_service(args)


def assert_closed_malformed(entry, args, monkeypatch, tmp_path):
    sys_path()
    from hmbc_protocol import adapter_v2_main as am
    with pytest.raises(am.Refusal) as e:
        build(entry, args, monkeypatch)
    assert e.value.code == "MALFORMED", (e.value.code, str(e.value))
    assert not os.path.exists(tmp_path / "state"), "a refused startup must leave no state behind"


ENTRIES = ["adapter_v2_main", "witness_main"]


def make_args(entry, tmp_path, **over):
    return adapter_args(tmp_path, **over) if entry == "adapter_v2_main" else witness_args(tmp_path, **over)


# ---- the manifest's numbers -----------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("side", ["pbc", "dbc"])
@pytest.mark.parametrize("field", ["chainId", "deployBlock"])
@pytest.mark.parametrize("raw", UINT_RAW)
def test_a_manifest_number_that_is_not_a_canonical_decimal_string_is_one_closed_refusal(tmp_path, monkeypatch, entry, side, field, raw):
    f = manifest_file(tmp_path, ("chains", side, field), raw)
    assert_closed_malformed(entry, make_args(entry, tmp_path, deployment=f), monkeypatch, tmp_path)


# ---- the schema file (the adapter only) -----------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("content", [b"null", b"[]", b"1", b'"x"', b"true", b"{}", b'{"$defs": null}', b'{"$defs": []}', b'{"$defs": {}}', DEPTH], ids=lambda c: c[:24].decode("latin-1") if len(c) < 60 else "deeply-nested")
def test_a_schema_file_that_hashes_correctly_but_is_not_the_published_shape_is_one_closed_refusal(tmp_path, monkeypatch, content):
    f = tmp_path / "schema.json"
    f.write_bytes(content)
    args = adapter_args(tmp_path, schema=str(f), schema_sha256=hashlib.sha256(content).hexdigest())
    assert_closed_malformed("adapter_v2_main", args, monkeypatch, tmp_path)


# ---- the pinned ABI files -------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("content", [DEPTH, b"{}", b"null", b"[1"], ids=["deeply-nested", "object", "null", "truncated"])
def test_a_pinned_abi_file_that_hashes_correctly_but_is_not_an_abi_is_one_closed_refusal(tmp_path, monkeypatch, entry, content):
    d = tmp_path / "abi"
    shutil.copytree(ABI_DIR, d)
    (d / "PSC.json").write_bytes(content)
    m = json.load(open(F2))
    m["abi"]["PSC"]["abiSha256"] = hashlib.sha256(content).hexdigest()
    f = tmp_path / "dep.json"
    f.write_text(json.dumps(m))
    assert_closed_malformed(entry, make_args(entry, tmp_path, deployment=str(f), abi_dir=str(d)), monkeypatch, tmp_path)


# ---- the allow-list (the witness only) ------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("content", [DEPTH, b"null", b'"x"', b"1", b"{}", b'""', b"true", b'[["1", "0xabc", []]]', b'[["9", "0x' + b"0" * 40 + b'", []]]'],
                         ids=["deeply-nested", "null", "string", "number", "object", "empty-string", "bool", "short-address", "bad-action"])
def test_an_allow_governance_file_that_is_not_an_array_of_approval_tuples_is_one_closed_refusal(tmp_path, monkeypatch, content):
    f = tmp_path / "allow.json"
    f.write_bytes(content)
    assert_closed_malformed("witness_main", witness_args(tmp_path, allow_governance=str(f)), monkeypatch, tmp_path)


# ---- the carried library entry points reached by the same corrupt input ------------------------------------------------------------------------------------------

def test_the_rpc_views_refuse_a_non_integral_chain_id_with_value_error_not_overflow_error(tmp_path):
    sys_path()
    from hmbc_protocol import rpc_binding_view as rv
    from hmbc_protocol import rpc_witness_view as rwv
    from hmbc_protocol.chain import Chain
    m = json.load(open(F2))
    chains = {s: Chain(m["chains"][s]["rpcUrl"], int(m["chains"][s]["chainId"])) for s in ("pbc", "dbc")}
    for bad in (float("inf"), 1.5, True, "1_0", " 5", 18545):
        m2 = json.loads(json.dumps(m))
        m2["chains"]["pbc"]["chainId"] = bad
        with pytest.raises(ValueError):
            rv.RpcBindingView.from_manifest(m2, chains, ABI_DIR)
        with pytest.raises(ValueError):
            rwv.RpcWitnessView.from_manifest(m2, chains, ABI_DIR)


def test_load_pinned_abis_refuses_a_deeply_nested_abi_with_value_error(tmp_path):
    sys_path()
    from hmbc_protocol import rpc_binding_view as rv
    d = tmp_path / "abi"
    shutil.copytree(ABI_DIR, d)
    (d / "PSC.json").write_bytes(DEPTH)
    m = json.load(open(F2))
    m["abi"]["PSC"]["abiSha256"] = hashlib.sha256(DEPTH).hexdigest()
    with pytest.raises(ValueError):
        rv.load_pinned_abis(m, str(d))


def test_a_context_refuses_a_supplied_schema_that_is_not_an_object_with_an_object_defs():
    sys_path()
    from hmbc_protocol import adapter_v2 as av2
    m = json.load(open(F2))
    for bad in ([], 1, "x", True, {"$defs": None}, {"$defs": []}):
        with pytest.raises(ValueError):
            av2.Context(manifest=m, schema_revision="v2", handlers={}, schema=bad)


# ---- the last resort and the real processes -------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("entry", ENTRIES)
def test_main_turns_an_unexpected_startup_exception_into_one_closed_refusal_that_leaks_nothing(tmp_path, monkeypatch, entry):
    sys_path()
    from hmbc_protocol import adapter_v2_main as am
    from hmbc_protocol import witness_main as wm
    secret = "/home/someone/private-key-path"
    mod, name, argv = (am, "build_context", ["--deployment", F2, "--abi-dir", ABI_DIR, "--schema", SCHEMA, "--schema-sha256", SCHEMA_SHA, "--schema-revision", "v2", "--state-dir", str(tmp_path / "s")]) \
        if entry == "adapter_v2_main" else (wm, "build_service", ["--deployment", F2, "--abi-dir", ABI_DIR, "--index", "0", "--key-label", "witness-1", "--state-dir", str(tmp_path / "s")])

    def boom(*a, **k):
        raise RuntimeError(secret)
    monkeypatch.setattr(mod, name, boom)
    old = os.umask(0o022)
    try:
        out, err = io.StringIO(), io.StringIO()
        rc = mod.main(argv, stdin=io.BytesIO(b""), stdout=out, stderr=err)
    finally:
        os.umask(old)
    assert rc == 2 and out.getvalue() == ""
    lines = err.getvalue().strip().splitlines()
    assert len(lines) == 1 and secret not in lines[0] and "Traceback" not in lines[0]
    obj = json.loads(lines[0])
    assert set(obj) == {"error"} and obj["error"]["code"] == "ADAPTER_UNAVAILABLE"
    assert not os.path.exists(tmp_path / "s")


def run_module(module, args):
    return subprocess.run([sys.executable, "-B", "-m", f"hmbc_protocol.{module}", *args], capture_output=True, text=True, cwd=PROTO,
                          env={"PYTHONPATH": PROTO, "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}, timeout=60)


def refused(p):
    assert p.returncode == 2 and p.stdout == "" and "Traceback" not in p.stderr, (p.returncode, p.stdout, p.stderr[-400:])
    lines = p.stderr.strip().splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert set(obj) == {"error"} and set(obj["error"]) >= {"code", "message"}
    return obj["error"]


def test_a3_0096_case_1_chain_id_1e999_is_a_closed_refusal_in_both_real_processes(tmp_path):
    f = manifest_file(tmp_path, ("chains", "pbc", "chainId"), "1e999")
    a = run_module("adapter_v2_main", ["--deployment", f, "--abi-dir", ABI_DIR, "--schema", SCHEMA, "--schema-sha256", SCHEMA_SHA, "--schema-revision", "v2", "--state-dir", str(tmp_path / "a")])
    assert refused(a)["code"] == "MALFORMED" and not os.path.exists(tmp_path / "a")
    w = run_module("witness_main", ["--deployment", f, "--abi-dir", ABI_DIR, "--index", "0", "--key-label", "witness-1", "--state-dir", str(tmp_path / "w")])
    assert refused(w)["code"] == "MALFORMED" and not os.path.exists(tmp_path / "w")


@pytest.mark.parametrize("content", [b"[]", b"null"])
def test_a3_0096_case_2_a_non_object_schema_is_a_closed_refusal_in_the_real_process(tmp_path, content):
    f = tmp_path / "schema.json"
    f.write_bytes(content)
    p = run_module("adapter_v2_main", ["--deployment", F2, "--abi-dir", ABI_DIR, "--schema", str(f), "--schema-sha256", hashlib.sha256(content).hexdigest(), "--schema-revision", "v2",
                                       "--state-dir", str(tmp_path / "a")])
    assert refused(p)["code"] == "MALFORMED" and not os.path.exists(tmp_path / "a")


def test_the_real_published_schema_and_a_valid_manifest_are_not_refused_by_the_new_checks(tmp_path, monkeypatch):
    """The control: the fixture the other tests use passes every new check and reaches the (stubbed) chain-opening step."""
    sys_path()
    from hmbc_protocol import adapter_v2_main as am
    with pytest.raises(AssertionError, match="went on to ask the chain"):
        am.build_context(adapter_args(tmp_path), start=never_reached)


# ---- gaps found by the mutation runners (fork D evidence: each kills one survivor; see evidence/af2-startup-fix) ------------------------------------------------


def schema_without(tmp_path, *dropped):
    """The published schema with the named $defs removed, as a file, with its SHA-256 (corrupt local config: the pinned hash matches the corrupt file)."""
    schema = json.load(open(SCHEMA))
    for name in dropped:
        del schema["$defs"][name]
    raw = json.dumps(schema).encode()
    f = tmp_path / "schema.json"
    f.write_bytes(raw)
    return str(f), hashlib.sha256(raw).hexdigest()


def test_the_schema_shape_check_uses_the_selected_revision(tmp_path, monkeypatch):
    """v2.1 needs LedgerDeploymentEComplete, v2 does not: the same file is refused for one revision and not for the other (C27, A8)."""
    f, h = schema_without(tmp_path, "LedgerDeploymentEComplete")
    assert_closed_malformed("adapter_v2_main", adapter_args(tmp_path, schema=f, schema_sha256=h, schema_revision="v2.1"), monkeypatch, tmp_path)
    with pytest.raises(AssertionError, match="went on to ask the chain"):                 # control: it serves revision v2, so startup goes on to the (stubbed) chain step
        build("adapter_v2_main", adapter_args(tmp_path / "ok", schema=f, schema_sha256=h, schema_revision="v2"), monkeypatch)


def test_a_schema_that_lacks_a_response_type_is_refused_before_startup_begins(tmp_path, monkeypatch):
    """A3: every carrier branch is present, one published response type is not."""
    f, h = schema_without(tmp_path, "CollectDecisionResponse")
    assert_closed_malformed("adapter_v2_main", adapter_args(tmp_path, schema=f, schema_sha256=h), monkeypatch, tmp_path)


def test_context_requires_the_response_types_only_when_it_checks_responses(tmp_path):
    """A7: with response checking on, a schema that cannot validate a response is refused; with it off no response validator is built, so only the carrier branches are needed."""
    sys_path()
    from hmbc_protocol import adapter_v2 as av2
    schema = json.load(open(SCHEMA))
    del schema["$defs"]["CollectDecisionResponse"]
    manifest = json.load(open(F2))
    with pytest.raises(ValueError):
        av2.Context(manifest=manifest, schema_revision="v2", handlers={}, schema=schema)
    av2.Context(manifest=manifest, schema_revision="v2", handlers={}, schema=schema, check_responses=False)


def test_the_manifest_number_widths_are_256_bits_for_chain_ids_and_64_bits_for_deploy_blocks():
    """S5, S6: the boundaries, not only the far-out-of-range 79-digit string."""
    sys_path()
    from hmbc_protocol import startup_config as sc

    def numbers(chain_id, deploy_block):
        m = json.load(open(F2))
        m["chains"]["pbc"]["chainId"], m["chains"]["pbc"]["deployBlock"] = chain_id, deploy_block
        return sc.manifest_numbers(m)["pbc"]
    assert numbers(str(2 ** 255), str(2 ** 64 - 1)) == {"chainId": 2 ** 255, "deployBlock": 2 ** 64 - 1}
    with pytest.raises(sc.ConfigError):
        numbers(str(2 ** 256), "1")
    with pytest.raises(sc.ConfigError):
        numbers("1", str(2 ** 64))


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("chains", [None, [], "x", 1, {"pbc": None, "dbc": {}}, {"pbc": [], "dbc": {}}, {"pbc": {"chainId": "1", "deployBlock": "1"}, "dbc": 7}], ids=["null", "array", "string", "number", "pbc-null", "pbc-array", "dbc-number"])
def test_chains_that_are_not_objects_are_one_closed_refusal(tmp_path, monkeypatch, entry, chains):
    """S10: TypeError is the failure of a `chains` or chain value that cannot be subscripted by name."""
    m = json.load(open(F2))
    m["chains"] = chains
    f = tmp_path / "dep.json"
    f.write_text(json.dumps(m))
    assert_closed_malformed(entry, make_args(entry, tmp_path, deployment=str(f)), monkeypatch, tmp_path)
