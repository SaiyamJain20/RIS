"""Executable reference of every TEST-ONLY hook variant command line (agent 2, F phase). Written BEFORE `protocol/evidence/af-case-hook-reference/README.md` documented them.

This file exists because agent 3's runner does not own my code: the inventory names the variants but not the exact command line that starts each one. Here each documented form is STARTED for real
(the alternate entry or a hook entry point, on a real Anvil pair with agent 1's F ledger), and the assertion is about the START, not about the behaviour (which the live hook tests already pin):
each form either runs (a hook child starts) or, for a form designed to be refused, gives ONE closed `refusing:` line and exit 2. If a documented line stops parsing, this test fails, so the reference
cannot silently rot. Live (needs Foundry), one start per form; no F case is run."""
import json
import os
import subprocess
import sys

import pytest

from test_faulty_adapter_v2 import ABI_DIR, SCHEMA, SCHEMA_SHA, base_flags, mods, run
from test_rpc_binding_view_live import f_ledger, live_f  # noqa: F401  (fixtures)

PROTO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FX = os.path.join(PROTO, "tests", "fixtures")
ENV = {"PYTHONPATH": PROTO, "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}


def mt():
    mods()
    from testtools import mutant_tree
    return mutant_tree


def launch(tmp_path, extra, dep_file):
    """Start the alternate entry with `extra` variant flags on a REAL deployment manifest; return the process (stdin open)."""
    args = ["--deployment", str(dep_file), "--abi-dir", ABI_DIR, "--schema", SCHEMA, "--schema-sha256", SCHEMA_SHA, "--schema-revision", "v2", "--state-dir", str(tmp_path / "state")]
    return subprocess.Popen([sys.executable, "-B", "-m", "testtools.faulty_adapter_v2", *extra, *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=PROTO, env=ENV, text=True)


def first_response(p, live, timeout=120):
    """One request line in, one response line out: the adapter is up and the variant is installed."""
    from test_rpc_binding_view_live import v2_line
    p.stdin.write(v2_line("collect_checkpoint", {}, live.dep) + "\n")
    p.stdin.flush()
    import selectors
    sel = selectors.DefaultSelector()
    sel.register(p.stdout, selectors.EVENT_READ)
    assert sel.select(timeout)[0], "the adapter answered nothing: " + (p.stderr.read()[-600:] if p.poll() is not None else "still running")
    return json.loads(p.stdout.readline())


def stop(p):
    try:
        p.stdin.close()
    except OSError:
        pass
    try:
        rc = p.wait(timeout=60)
    except subprocess.TimeoutExpired:
        p.kill()
        rc = p.wait(timeout=30)
    p.stdout.close()
    return rc, (p.stderr.read() if p.poll() is not None else "")


def test_reference_file_exists_and_lists_every_variant():
    path = os.path.join(PROTO, "evidence", "af-case-hook-reference", "README.md")
    text = open(path, encoding="utf-8").read()
    for token in ("--witness-variant", "I=crash:", "I=delay:", "I=mutant:", "I=byz:", "I=view:", "--mutant-tree", "--worker-variant compromised"):
        assert token in text, token
    for mid in ("M1", "M2", "M3", "M4", "M5", "M6", "M7"):
        assert mid in text, mid


@pytest.mark.parametrize("extra", [
    ["--witness-variant", "0=crash:before_commit"],
    ["--witness-variant", "0=crash:after_commit"],
    ["--witness-variant", "0=delay:3000"],
    ["--witness-variant", "0=delay:3000:checkpoint:before"],
    ["--witness-variant", "3=byz:withhold"],
    ["--witness-variant", "3=byz:garbage"],
    ["--witness-variant", "3=byz:repeat:3"],
    ["--witness-variant", "3=byz:equivocate"],
    ["--witness-variant", "3=byz:impersonate:0"],
    ["--witness-variant", "3=byz:poison:authEpoch"],
    ["--witness-variant", "1=view:authEpoch:3"],
    ["--witness-variant", "1=view:policyVersion:2"],
    ["--witness-variant", "1=view:witnessSetVersion:9"],
    ["--witness-variant", "1=view:headLag:2"],
], ids=["crash-before", "crash-after", "delay", "delay-kind-when", "byz-withhold", "byz-garbage", "byz-repeat", "byz-equivocate", "byz-impersonate", "byz-poison", "view-auth", "view-policy", "view-wset", "view-headlag"])
def test_every_documented_witness_variant_form_starts_or_answers(live_f, tmp_path, extra):
    dep_file = tmp_path / "dep.json"
    dep_file.write_text(json.dumps(live_f.dep))
    p = launch(tmp_path, extra, dep_file)
    try:
        r = first_response(p, live_f)
        assert "ok" in r and r["schemaVersion"] == "v2", r     # a well-formed adapter response: the variant is installed and the child started
    finally:
        rc, err = stop(p)
    assert rc == 0 and err == "", (extra, rc, err)


@pytest.mark.parametrize("mid,extra", [("M1", ["--witness-variant", "1=mutant:M1"]), ("M2", ["--witness-variant", "1=mutant:M2"])], ids=["M1", "M2"])
def test_documented_mutant_forms_start(live_f, tmp_path, mid, extra):
    tree = str(tmp_path / ("tree-" + mid))
    mt().build(mid, tree)
    dep_file = tmp_path / "dep.json"
    dep_file.write_text(json.dumps(live_f.dep))
    p = launch(tmp_path, extra + ["--mutant-tree", mid + "=" + tree], dep_file)
    try:
        r = first_response(p, live_f)
        assert "ok" in r, r
    finally:
        rc, err = stop(p)
    assert rc == 0 and err == "", (mid, rc, err)


def test_the_adapter_role_mutant_m5_is_refused_as_a_witness_variant(tmp_path):
    """M5 runs in the ADAPTER process and is documented as such: as a witness variant it must be refused before anything is spawned, never silently started."""
    tree = str(tmp_path / "tree-M5")
    mt().build("M5", tree)
    p = run(base_flags(tmp_path) + ["--witness-variant", "0=mutant:M5", "--mutant-tree", "M5=" + tree])
    assert p.returncode == 2 and p.stdout == "" and str(tmp_path) not in p.stderr
    err = json.loads(p.stderr.strip().splitlines()[0])
    assert err["error"]["code"] == "MALFORMED" and err["error"]["message"].startswith("refusing:")


def test_the_documented_mutant_tree_construction_command(tmp_path):
    tree = str(tmp_path / "tree")
    r = subprocess.run([sys.executable, "-B", "-m", "testtools.mutant_tree", "build", "M2", "--dest", tree], cwd=PROTO, capture_output=True, text=True, env=ENV)
    assert r.returncode == 0 and json.load(open(os.path.join(tree, "MUTANT.json")))["id"] == "M2"


def test_a_worker_variant_form_is_refused_without_claims_and_documented_as_such(tmp_path):
    p = run(base_flags(tmp_path) + ["--worker-variant", "compromised"])
    assert p.returncode == 2 and p.stdout == ""
    err = json.loads(p.stderr.strip().splitlines()[0])                          # ONE closed JSON line with the refusing text inside it, as every entry point refuses
    assert err["error"]["code"] == "MALFORMED" and err["error"]["message"].startswith("refusing: --worker-variant needs --claims FILE")