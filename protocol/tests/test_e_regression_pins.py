"""E regression pins (agent 2, F task: Step 5; A3-0073 and communication/F_SOURCE_READY.md 'Historical E source and successor regressions'). Written BEFORE the pin values were filled in.

PAPER-DERIVED RECONSTRUCTION. The F work is allowed to change three E-listed source paths (the accepted D-4/D-6, profile-3, D50/store and exporter tasks). A3 requires that E operations, outputs, the default
worker export and the legacy worker fingerprint keep their reviewed behaviour and that this is SHOWN by running something, not inferred from a hash. These tests pin exactly that, against the HISTORICAL commit
376347d (the common F0 baseline, whose E inventory protocol/evidence/source-manifest.sha256 has SHA-256 005c8448..):
  1. the worker deployment fingerprint VALUE for the E fixture (no earlier test pinned it, only len == 64), and current code == historical code on the same fixture;
  2. the DEFAULT `worker_log` export, byte for byte, on the same synthetic state under the historical and the current code (the opt-in `--binding` must not change the default);
  3. exports/adapter.json SHA-256 and `python -m hmbc_protocol.export --check`;
  4. the three changed E-listed paths differ from the historical blobs ONLY in the definitions the plan allows (AST level, docstrings ignored), and each allowed change is the REVIEWED one;
  5. the E inventory is itself unchanged and EXACTLY those three of its 142 entries mismatch.
Corrupt input is not the point here: this file is a CHARACTERIZATION of behaviour that must stay put. Its sensitivity is shown by tools/run_e_regression_pins_mutants.py, not by a missing-feature RED.

Two guards against a vacuous pass (Fork C's first probe compared two empty outputs): every subprocess prints the directory it imported `hmbc_protocol` from and the test asserts it is the intended tree, and every
export is asserted non-empty and parsed.
"""
import ast
import copy
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tarfile
import io

import pytest

PROTO = pathlib.Path(__file__).resolve().parents[1]
REPO = PROTO.parent
HIST = "376347d9b0979d1e46824a30197b935ffe91e4fb"
INVENTORY = PROTO / "evidence" / "source-manifest.sha256"
INVENTORY_SHA = "005c8448faeb90d2dade129211a5f220635ee1c8bf421c89f17b2b7d0c2d7612"
INVENTORY_ENTRIES = 142
ADAPTER_JSON_SHA = "7146495b4dfbe351d73299223efdb853c41895ac880f9a6c13e2a525656a9220"
E_FIXTURE = PROTO / "tests" / "fixtures" / "deployment-agent1-91add8c-v1-repaired-e.json"
CHANGED_E_PATHS = ["protocol/hmbc_protocol/worker.py", "protocol/hmbc_protocol/worker_log.py", "protocol/testtools/deviating_witness.py"]
HIST_SHA = {"protocol/hmbc_protocol/worker.py": "204af36906a89521517c88b1314e596e087a303e576cff38836071532bdb8908",
            "protocol/hmbc_protocol/worker_log.py": "b443d5e8a6b62e7cded7bbece00c78a2cfbc05fd983d912e303398de2a36cd0e",
            "protocol/testtools/deviating_witness.py": "0511ba571b71d960d8ffbe4b8c811da99ed7de53a4b7515ac425c5291cc3c2d7"}

# ---- the pins -----------------------------------------------------------------------------------------------------------------------------------------------
FINGERPRINT_E_FIXTURE = "758f970ef15219817004e0a16683a0a64e1a4cbbd3c40c227bb2e9d76610f6a5"      # measured: historical == current (RED run 1 printed it); first 16 hex = fingerprint-measurement.txt of A2-0039
DEFAULT_EXPORT_SHA256 = "7a3ed500e3fbb567f1539eb481ab12613f170834e21e067d8e56d1c769d80d01"     # of the 2644-byte default export of the synthetic state (two events, two releases)
DEFAULT_EXPORT_BYTES = 2644
# The definitions the accepted plan lets F change in E-listed source (A3-0073 'D4/D6/profile3/store/exporter'; F_SOURCE_READY.md; accounting E-SOURCE-ACCOUNTING.md section 4):
ALLOWED = {
    "protocol/hmbc_protocol/worker.py": {"changed": {"Worker._recipient_for"}, "added": set(), "removed": set()},                       # 4.1 profile-3 recipient binding (be27f32)
    "protocol/hmbc_protocol/worker_log.py": {"changed": {"main"}, "added": set(), "removed": set()},                                     # 4.2 opt-in D50 binding export (eb6e299)
    "protocol/testtools/deviating_witness.py": {"changed": {"main"}, "added": {"stmt:from hmbc_protocol.adapter import AdapterError, strict_loads"}, "removed": set()},   # 4.3 D-6 strict JSON (0ec5422)
}

PROBE = r'''
import json, os, sys
import hmbc_protocol
from hmbc_protocol.ledger import Ledger
from hmbc_protocol.worker import Worker

dep = json.load(open(sys.argv[1]))
state = sys.argv[2]
w = Worker(Ledger.from_deployment(dep), state, clock=lambda: 0)
fp = w.db.execute("select value from meta where key='deployment'").fetchone()[0]
if len(sys.argv) > 3 and sys.argv[3] == "rows":
    req, grant, data, rk, cd, token = ("0x" + c * 32 for c in ("11", "22", "44", "55", "66", "77"))
    gid = "0x" + "33" * 20
    ins = "insert into events(type,request_digest,grant_id,gid,data_id,timestamp) values(?,?,?,?,?,?)"
    w.db.execute(ins, ("RELEASE_INTENT", req, grant, gid, data, 5))
    w.db.execute(ins, ("RELEASE_SENT", req, grant, gid, data, 6))
    ins_r = "insert into releases values(?,?,?,?,?,?,?,?,?,?,?,?,?)"
    w.db.execute(ins_r, (grant, req, data, gid, rk, "0", cd, token, 1000, 5, "unknown", 1, 1))
    # a SECOND release that sorts first by created_at but last by grant_id: only then can a change of the export's release ordering be seen
    w.db.execute(ins_r, ("0x" + "23" * 32, req, data, gid, rk, "0", cd, "0x" + "88" * 32, 1000, 4, "unknown", 2, 2))
w.db.close()
print(json.dumps({"fingerprint": fp, "package": os.path.dirname(os.path.realpath(hmbc_protocol.__file__))}))
'''


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def git(*args, check=True):
    p = subprocess.run(["git", *args], cwd=REPO, capture_output=True)
    if check and p.returncode != 0:
        pytest.fail(f"git {' '.join(args)} failed ({p.returncode}): {p.stderr.decode(errors='replace')[:300]}. The historical commit {HIST} must be in the local object store (git fetch origin): a pin test must FAIL, not skip, when its reference is missing.")
    return p.stdout


def hist_blob(path):
    return git("show", f"{HIST}:{path}")


@pytest.fixture(scope="module")
def hist(tmp_path_factory):
    """The historical protocol code (git archive of the common F0 baseline), extracted to a temporary directory: nothing in the repository is touched."""
    git("cat-file", "-e", f"{HIST}^{{commit}}")
    tar = git("archive", HIST, "protocol/hmbc_protocol", "protocol/abi", "protocol/testtools", "protocol/exports")
    root = tmp_path_factory.mktemp("hist")
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        t.extractall(root, filter="data")
    for path, want in HIST_SHA.items():
        assert sha256_bytes((root / path).read_bytes()) == want, f"the extracted historical {path} is not the inventory's blob"
    return root / "protocol"


@pytest.fixture(scope="module")
def probe_script(tmp_path_factory):
    f = tmp_path_factory.mktemp("probe") / "probe_state.py"
    f.write_text(PROBE)
    return f


def run_py(tree, args, script=None):
    """Run python against the package at `tree` (a `protocol/` directory), a minimal environment, cwd = that directory."""
    cmd = [sys.executable, "-B", *( [str(script)] if script else [] ), *args]
    return subprocess.run(cmd, cwd=tree, capture_output=True, env={"PYTHONPATH": str(tree), "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}, timeout=120)


def probe(tree, script, deployment, state, rows=False):
    p = run_py(tree, [str(deployment), str(state)] + (["rows"] if rows else []), script=script)
    assert p.returncode == 0, p.stderr.decode(errors="replace")[-600:]
    out = json.loads(p.stdout)
    assert pathlib.Path(out["package"]) == pathlib.Path(tree).resolve() / "hmbc_protocol", f"imported {out['package']}, expected the package under {tree}"
    return out["fingerprint"]


def export_default(tree, state):
    p = run_py(tree, ["-m", "hmbc_protocol.worker_log", "--state-dir", str(state)])
    assert p.returncode == 0 and p.stderr == b"", (p.returncode, p.stderr[-300:])
    assert len(p.stdout) > 100, "an empty export would make every equality vacuous"
    doc = json.loads(p.stdout)
    assert [e["type"] for e in doc["events"]] == ["RELEASE_INTENT", "RELEASE_SENT"] and [r["createdAt"] for r in doc["releases"]] == ["4", "5"]
    return p.stdout


# ---- 1 and 2: fingerprint value and default export ------------------------------------------------------------------------------------------------------------

def test_the_worker_fingerprint_of_the_e_fixture_is_pinned_and_equal_under_the_historical_and_the_current_code(tmp_path, hist, probe_script):
    historical = probe(hist, probe_script, E_FIXTURE, tmp_path / "hist-state")
    current = probe(PROTO, probe_script, E_FIXTURE, tmp_path / "cur-state")
    assert historical == current
    assert current == FINGERPRINT_E_FIXTURE


def test_the_default_worker_export_is_byte_identical_under_the_historical_and_the_current_code_on_both_states(tmp_path, hist, probe_script):
    """A 2 x 2 cross: the state written by the historical Worker and by the current Worker, each exported by the historical and the current worker_log. Four equal, non-empty, pinned byte strings."""
    states = {}
    for name, tree in (("hist", hist), ("cur", PROTO)):
        states[name] = tmp_path / f"{name}-state"
        probe(tree, probe_script, E_FIXTURE, states[name], rows=True)
    outs = {(s, c): export_default(tree, states[s]) for s in states for c, tree in (("hist", hist), ("cur", PROTO))}
    assert len(set(outs.values())) == 1, {k: sha256_bytes(v)[:16] for k, v in outs.items()}
    out = next(iter(outs.values()))
    assert (len(out), sha256_bytes(out)) == (DEFAULT_EXPORT_BYTES, DEFAULT_EXPORT_SHA256)
    assert b"77" * 32 not in out and b"88" * 32 not in out                  # no raw token appears: only keccak digests


# ---- 3: the default export of the adapter ---------------------------------------------------------------------------------------------------------------------

def test_the_default_adapter_export_is_unchanged_and_matches_its_regeneration():
    assert sha256_bytes((PROTO / "exports" / "adapter.json").read_bytes()) == ADAPTER_JSON_SHA
    p = run_py(PROTO, ["-m", "hmbc_protocol.export", "--check"])
    assert p.returncode == 0, (p.stdout[-300:], p.stderr[-300:])
    assert b"exports match 9 files" in p.stdout


# ---- 4: the changed definitions of the three E-listed paths ---------------------------------------------------------------------------------------------------

def _strip_doc(node):
    body = list(node.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    return body


def _dump(node):
    c = copy.copy(node)
    c.body = _strip_doc(node)
    return ast.dump(c)


def definitions(src):
    """{name: dump} for every function, every class header and method, and a `stmt:` key for every other module-level statement; docstrings are ignored."""
    out = {}
    for n in ast.parse(src).body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[n.name] = _dump(n)
        elif isinstance(n, ast.ClassDef):
            head = copy.copy(n)
            head.body = [m for m in _strip_doc(n) if not isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
            out[n.name] = ast.dump(head)
            for m in n.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out[f"{n.name}.{m.name}"] = _dump(m)
        elif isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None), ast.Constant) and isinstance(n.value.value, str):
            continue                                                   # the module docstring
        else:
            out["stmt:" + ast.unparse(n)] = ""
    return out


def _delta(path):
    old, new = definitions(hist_blob(path).decode()), definitions((REPO / path).read_text())
    return {"changed": {k for k in set(old) & set(new) if old[k] != new[k]}, "added": set(new) - set(old), "removed": set(old) - set(new)}


@pytest.mark.parametrize("path", CHANGED_E_PATHS)
def test_each_changed_e_listed_path_differs_from_the_historical_blob_only_in_the_allowed_definitions(path):
    assert sha256_bytes((REPO / path).read_bytes()) != HIST_SHA[path], "the path is no longer changed: update the pin and the accounting"
    assert _delta(path) == ALLOWED[path]


def test_worker_recipient_for_differs_from_the_historical_function_only_by_the_profile_test():
    """The historical `profile == "2"` becomes `profile in ("2", "3")`; nothing else in the function changes (docstrings are ignored)."""
    class Rewrite(ast.NodeTransformer):
        hits = 0

        def visit_Compare(self, node):
            self.generic_visit(node)
            if (len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq) and isinstance(node.comparators[0], ast.Constant) and node.comparators[0].value == "2"
                    and "profile" in ast.unparse(node.left)):
                Rewrite.hits += 1
                return ast.Compare(left=node.left, ops=[ast.In()], comparators=[ast.Tuple(elts=[ast.Constant("2"), ast.Constant("3")], ctx=ast.Load())])
            return node

    def method(src):
        for n in ast.parse(src).body:
            if isinstance(n, ast.ClassDef) and n.name == "Worker":
                return next(m for m in n.body if isinstance(m, ast.FunctionDef) and m.name == "_recipient_for")
    old = copy.deepcopy(method(hist_blob("protocol/hmbc_protocol/worker.py").decode()))
    old.body = _strip_doc(old)
    rewritten = Rewrite().visit(old)
    cur = method((REPO / "protocol/hmbc_protocol/worker.py").read_text())
    cur_c = copy.copy(cur)
    cur_c.body = _strip_doc(cur)
    assert Rewrite.hits == 1
    assert ast.dump(rewritten) == ast.dump(cur_c)


REVIEWED_WORKER_LOG_MAIN = """
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--binding", action="store_true", help="opt-in (F successor): print the D50 binding export of <state-dir>/worker instead of the log; read-only, no RPC")
    ns = ap.parse_args(argv)
    if ns.binding:
        from . import worker_binding
        return worker_binding.binding_main(ns.state_dir)
    print(json.dumps(export(ns.state_dir), indent=1))
    return 0
"""

REVIEWED_DEVIATING_WITNESS_MAIN = """
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deployment", required=True, help="the deployment JSON the runner pinned the adapter with")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("receipt")
    r.add_argument("--grant-id", required=True)
    r.add_argument("--field", required=True)
    r.add_argument("--value")
    r.add_argument("--at-block")
    args = ap.parse_args(argv)
    with open(args.deployment, "rb") as f:
        raw = f.read()
    try:
        dep = strict_loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        raise SystemExit("refusing: the deployment file is not valid UTF-8") from None
    except AdapterError as e:
        raise SystemExit(f"refusing: {e.message}") from None
    try:
        led = Ledger.from_deployment(dep)
        out = deviating_receipt(led, args.grant_id, args.field, args.value, args.at_block)
    except (wire.WireError, ValueError, KeyError) as e:
        raise SystemExit(f"refusing: {type(e).__name__}: {e}") from None
    sys.stdout.write(json.dumps(out) + "\\n")
    return 0
"""


def _function(src, name):
    return next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == name)


@pytest.mark.parametrize("path,reviewed", [("protocol/hmbc_protocol/worker_log.py", REVIEWED_WORKER_LOG_MAIN), ("protocol/testtools/deviating_witness.py", REVIEWED_DEVIATING_WITNESS_MAIN)],
                         ids=["worker_log.main", "deviating_witness.main"])
def test_the_allowed_change_of_main_is_the_reviewed_one(path, reviewed):
    """D-6 (strict parse of the deployment) and the opt-in `--binding` are the ONLY edits of these two `main` functions; any further edit makes this fail and forces a new accounting entry."""
    cur = _function((REPO / path).read_text(), "main")
    assert _dump(cur) == _dump(_function(reviewed, "main"))


# ---- 5: the E inventory ---------------------------------------------------------------------------------------------------------------------------------------

def test_the_e_inventory_is_unchanged_and_exactly_the_three_allowed_entries_mismatch():
    assert sha256_bytes(INVENTORY.read_bytes()) == INVENTORY_SHA
    assert hist_blob("protocol/evidence/source-manifest.sha256") == INVENTORY.read_bytes()
    entries = [line.split("  ", 1) for line in INVENTORY.read_text().splitlines()]
    assert len(entries) == INVENTORY_ENTRIES
    mismatched = sorted(path for want, path in entries if not (REPO / path).is_file() or sha256_bytes((REPO / path).read_bytes()) != want)
    assert mismatched == sorted(CHANGED_E_PATHS)
    for path in CHANGED_E_PATHS:
        assert any(p == path for _, p in entries)
