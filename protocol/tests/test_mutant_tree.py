"""TEST-ONLY real source mutants M1..M7 of the F plan, as separate-process source trees (agent 2, F phase; gap G3 of protocol/evidence/af-case-hook-inventory). Written BEFORE testtools/mutant_tree.py and
testtools/mutant_run.py existed. PAPER-DERIVED RECONSTRUCTION; deliberate source mutants, not observed vulnerabilities.

The F plan (SOURCE-INTERFACE-PLAN, "experiment coverage") defines seven DELIBERATE source mutants M1..M7 and maps them to F rows (M1/M2 F-12, M2 F-13, M3 F-29, M4 FL-7, M5 FL-5, M6/M7 FL-1). Until now they existed only
as single-site text edits inside my mutation runners (unit level): no supervised witness or adapter PROCESS could be started as a mutant. This file pins the contract of the two TEST-ONLY tools that close that gap:
  * `testtools.mutant_tree` builds a copy of `hmbc_protocol` and `testtools` in which exactly ONE registered mutant is applied (each anchor must match exactly once; the edit must change the file), with a marker file;
  * `testtools.mutant_run` starts one of THREE allowed modules from such a tree by EXEC (same pid as the launcher, so a supervisor's pid file and a kill still name the real process), with the tree as the working directory;
    it refuses a missing or tampered tree, a marker for another mutant, a relative path argument, and any module other than the allow-list.
Not claimed: that any F case passes; that a mutant is exploitable; anything about a real transport beyond the processes started here."""
import ast
import hashlib
import json
import os
import subprocess
import sys

import pytest

PROTO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IDS = ["M1", "M2", "M3", "M4", "M5", "M6", "M7"]


def mt():
    from testtools import mutant_tree
    return mutant_tree


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def tree_files(root):
    out = {}
    for base in ("hmbc_protocol", "testtools"):
        for dp, dn, fn in os.walk(os.path.join(root, base)):
            dn[:] = [d for d in dn if d != "__pycache__"]
            for f in fn:
                p = os.path.join(dp, f)
                out[os.path.relpath(p, root)] = sha(p)
    return out


def run_launcher(*argv, cwd=None):
    return subprocess.run([sys.executable, "-B", "-m", "testtools.mutant_run", *argv], cwd=cwd or PROTO, capture_output=True, text=True, timeout=60)


# ---- the registry ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def test_the_registry_holds_exactly_m1_to_m7_each_with_a_plan_row():
    m = mt()
    assert sorted(m.MUTANTS) == IDS
    for mid, mu in m.MUTANTS.items():
        assert mu.id == mid and mu.rows and mu.role in ("witness", "adapter") and mu.what and mu.edits


@pytest.mark.parametrize("mid", IDS)
def test_every_anchor_matches_the_production_source_exactly_once_and_changes_it(mid):
    mu = mt().MUTANTS[mid]
    for rel, old, new in mu.edits:
        text = open(os.path.join(PROTO, rel)).read()
        assert text.count(old) == 1, (mid, rel, old[:60])
        assert old != new


# ---- the builder -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("mid", IDS)
def test_a_built_tree_differs_from_production_in_exactly_the_edited_files(tmp_path, mid):
    m = mt()
    dest = str(tmp_path / "tree")
    m.build(mid, dest)
    prod, tree = tree_files(PROTO), tree_files(dest)
    edited = {rel for rel, _, _ in m.MUTANTS[mid].edits}
    assert set(tree) == set(prod)
    assert {k for k in tree if tree[k] != prod[k]} == edited
    for k in tree:
        if k.endswith(".py"):
            ast.parse(open(os.path.join(dest, k)).read())                               # the mutated source still compiles
    marker = json.load(open(os.path.join(dest, "MUTANT.json")))
    assert marker["id"] == mid and set(marker["files"]) == edited
    assert all(marker["files"][k] == tree[k] for k in edited)
    m.verify_tree(dest, mid)


def test_a_built_tree_carries_the_data_directories_unchanged(tmp_path):
    m = mt()
    dest = str(tmp_path / "tree")
    m.build("M1", dest)
    for d in ("abi", "exports"):
        prod = {os.path.relpath(os.path.join(dp, f), os.path.join(PROTO, d)): sha(os.path.join(dp, f)) for dp, _, fn in os.walk(os.path.join(PROTO, d)) for f in fn if "__pycache__" not in dp}
        tree = {os.path.relpath(os.path.join(dp, f), os.path.join(dest, d)): sha(os.path.join(dp, f)) for dp, _, fn in os.walk(os.path.join(dest, d)) for f in fn}
        assert prod and tree == prod, d                                                  # the package reads them relative to itself (ledger.ABI_DIR, export.ROOT)


def test_build_refuses_an_unknown_id_a_relative_destination_and_a_non_empty_one(tmp_path):
    m = mt()
    for bad in (lambda: m.build("M8", str(tmp_path / "a")), lambda: m.build("M1", "relative/dir"), lambda: m.build("m1", str(tmp_path / "b"))):
        with pytest.raises(m.MutantError):
            bad()
    (tmp_path / "full").mkdir()
    (tmp_path / "full" / "x").write_text("x")
    with pytest.raises(m.MutantError):
        m.build("M1", str(tmp_path / "full"))
    assert os.listdir(tmp_path / "full") == ["x"]                                       # nothing was written into the refused directory


def test_verify_tree_detects_tampering_and_a_marker_for_another_mutant(tmp_path):
    m = mt()
    dest = str(tmp_path / "t")
    m.build("M1", dest)
    with pytest.raises(m.MutantError):
        m.verify_tree(dest, "M2")                                                       # a marker for another mutant
    path = os.path.join(dest, "hmbc_protocol", "witness_state.py")
    open(path, "a").write("\n# tampered\n")
    with pytest.raises(m.MutantError):
        m.verify_tree(dest, "M1")
    with pytest.raises(m.MutantError):
        m.verify_tree(str(tmp_path / "missing"), "M1")


def test_the_cli_builds_and_lists(tmp_path):
    r = subprocess.run([sys.executable, "-B", "-m", "testtools.mutant_tree", "list"], cwd=PROTO, capture_output=True, text=True)
    assert r.returncode == 0 and [json.loads(ln)["id"] for ln in r.stdout.splitlines()] == IDS
    dest = str(tmp_path / "cli")
    r = subprocess.run([sys.executable, "-B", "-m", "testtools.mutant_tree", "build", "M6", "--dest", dest], cwd=PROTO, capture_output=True, text=True)
    assert r.returncode == 0 and json.load(open(os.path.join(dest, "MUTANT.json")))["id"] == "M6"
    r = subprocess.run([sys.executable, "-B", "-m", "testtools.mutant_tree", "build", "M9", "--dest", str(tmp_path / "x")], cwd=PROTO, capture_output=True, text=True)
    assert r.returncode == 2 and r.stdout == "" and r.stderr.startswith("refusing:")


# ---- the launcher ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def test_the_launcher_execs_the_module_from_the_tree_and_keeps_the_pid(tmp_path):
    m = mt()
    dest = str(tmp_path / "tree")
    m.build("M1", dest)
    p = subprocess.Popen([sys.executable, "-B", "-m", "testtools.mutant_run", "--tree", dest, "--mutant", "M1", "--module", "testtools.mutant_probe"], cwd=PROTO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate(timeout=60)
    assert p.returncode == 0 and err == ""
    probe = json.loads(out)
    assert probe["pid"] == p.pid                                                        # exec: a supervisor's pid file and a kill name the real process
    assert os.path.realpath(probe["cwd"]) == os.path.realpath(dest)
    assert os.path.realpath(probe["hmbc_protocol"]).startswith(os.path.realpath(dest) + os.sep)
    assert os.path.realpath(probe["testtools"]).startswith(os.path.realpath(dest) + os.sep)
    assert probe["mutant"] == "M1"


def test_the_launcher_passes_the_module_arguments_through(tmp_path):
    m = mt()
    dest = str(tmp_path / "tree")
    m.build("M2", dest)
    r = run_launcher("--tree", dest, "--mutant", "M2", "--module", "testtools.mutant_probe", "--", "--echo", "a b", "--flag")
    assert r.returncode == 0 and json.loads(r.stdout)["argv"] == ["--echo", "a b", "--flag"]


@pytest.mark.parametrize("argv_builder,why", [
    (lambda d: ["--tree", "relative/tree", "--mutant", "M1", "--module", "testtools.mutant_probe"], "relative tree"),
    (lambda d: ["--tree", d + "-missing", "--mutant", "M1", "--module", "testtools.mutant_probe"], "missing tree"),
    (lambda d: ["--tree", d, "--mutant", "M2", "--module", "testtools.mutant_probe"], "marker is for another mutant"),
    (lambda d: ["--tree", d, "--mutant", "M1", "--module", "hmbc_protocol.adapter_v2_main"], "a module outside the allow-list"),
    (lambda d: ["--tree", d, "--mutant", "M1", "--module", "os"], "an arbitrary module"),
    (lambda d: ["--tree", d, "--mutant", "M1", "--module", "testtools.mutant_probe", "--", "--deployment", "rel/path.json"], "a relative path argument"),
    (lambda d: ["--tree", d, "--mutant", "M1"], "no module"),
    (lambda d: ["--mutant", "M1", "--module", "testtools.mutant_probe"], "no tree"),
])
def test_the_launcher_refuses_with_one_closed_line_and_starts_nothing(tmp_path, argv_builder, why):
    d = str(tmp_path / "tree")
    mt().build("M1", d)
    r = run_launcher(*argv_builder(d))
    assert r.returncode == 2, why
    assert r.stdout == "" and r.stderr.startswith("refusing:") and r.stderr.count("\n") == 1, (why, r.stderr)
    assert str(tmp_path) not in r.stderr                                                # no path is echoed


def test_the_launcher_refuses_a_tampered_tree(tmp_path):
    d = str(tmp_path / "tree")
    mt().build("M3", d)
    open(os.path.join(d, "hmbc_protocol", "witness_state.py"), "a").write("\n# tampered\n")
    r = run_launcher("--tree", d, "--mutant", "M3", "--module", "testtools.mutant_probe")
    assert r.returncode == 2 and r.stdout == "" and r.stderr.startswith("refusing:")


def test_no_production_module_imports_the_mutant_tools():
    for f in os.listdir(os.path.join(PROTO, "hmbc_protocol")):
        if f.endswith(".py"):
            src = open(os.path.join(PROTO, "hmbc_protocol", f)).read()
            assert "mutant_tree" not in src and "mutant_run" not in src and "mutant_probe" not in src, f
