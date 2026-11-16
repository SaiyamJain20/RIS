"""Mutation check of the worker store's D50 rows and the opt-in `worker_log --binding` flag (agent 2, F task 2 slice 5b). Standard library only. Same method as the other runners: one text replacement per
mutant in the file the mutant names (it must match exactly once and change the file), run the UNCHANGED tests/test_worker_binding.py in a temporary copy that keeps the repository layout, count a mutant
DETECTED only when the tests ran and failed; a crash or timeout is NOT detection; the unmutated copy runs first as a control; every anchor is validated before any run. witness_state.py is NOT mutated here
(run_state_mutants.py does that).

Usage (repository root):   python3 -B -I protocol/tools/run_worker_binding_mutants.py        (needs pytest and the E dependencies: protocol/requirements.txt)
Exit 0 only when every mutant is detected.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.abspath(os.path.join(HERE, ".."))
FILES = {n: open(os.path.join(PROTO, "hmbc_protocol", n)).read() for n in ("worker_binding.py", "worker_log.py")}

M = [
    ("W1 a worker store with rows and no binding rows is not refused", ("worker_binding.py", '        if rows:\n            raise ws.StoreError("LEGACY_STATE"', '        if False:\n            raise ws.StoreError("LEGACY_STATE"')),
    ("W2 only the events table counts as rows", ("worker_binding.py", 'RECORD_TABLES = ("records", "releases", "events")', 'RECORD_TABLES = ("events",)')),
    ("W3 a marker next to missing binding rows is not corrupt", ("worker_binding.py", '        if has_marker:\n            raise ws.StoreError("STORE_CORRUPT", "the INITIALIZED marker exists but the binding rows are missing")', '        if False:\n            raise ws.StoreError("STORE_CORRUPT", "the INITIALIZED marker exists but the binding rows are missing")')),
    ("W4 a marker without a database is not refused", ("worker_binding.py", "    if has_marker and not has_db:", "    if False:")),
    ("W5 the integrity check is skipped", ("worker_binding.py", 'if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":', "if False:")),
    ("W6 record rows without a marker are accepted", ("worker_binding.py", '        if rows:\n            raise ws.StoreError("STORE_CORRUPT", "record rows exist but', '        if False:\n            raise ws.StoreError("STORE_CORRUPT", "record rows exist but')),
    ("W7 the marker is not compared with the identity rows", ("worker_binding.py", 'if mk != {"binding_v2": meta["binding_v2"], "owner": meta["owner"], "schema": meta["schema"]} or meta["schema"] != SCHEMA:', "if False:")),
    ("W8 an interrupted initialisation of another identity is completed", ("worker_binding.py", "            ws._identity(meta, binding_v2, OWNER)\n            if os.path.exists(tmp):", "            if os.path.exists(tmp):")),
    ("W9 an open store is not compared with the binding", ("worker_binding.py", '    if state == "open":\n        ws._identity(meta, binding_v2, OWNER)\n        return\n    os.makedirs', '    if state == "open":\n        return\n    os.makedirs')),
    ("W10 the owner constant is not worker", ("worker_binding.py", 'OWNER = "worker"', 'OWNER = "worker2"')),
    ("W11 the anchor is not stored", ("worker_binding.py", '("owner", OWNER), ("anchor", ws.canonical_json(anchor))]', '("owner", OWNER)]')),
    ("W12 the binding document is stored as non-canonical JSON", ("worker_binding.py", '("binding_v2_doc", ws.canonical_json(document))', '("binding_v2_doc", json.dumps(document))')),
    ("W13 the directory is not made private", ("worker_binding.py", "    os.chmod(directory, 0o700)\n", "")),
    ("W14 the database is not made private", ("worker_binding.py", "            os.chmod(db, 0o600)\n", "")),
    ("W15 the init lock is not taken", ("worker_binding.py", "        fcntl.flock(lock, fcntl.LOCK_EX)\n", "")),
    ("W16 the state is not re-read under the lock", ("worker_binding.py", '        state, meta = _classify(directory)                         # again, under the lock: another initialiser may have finished\n        if state == "open":\n            ws._identity(meta, binding_v2, OWNER)\n            return\n', "")),
    ("W17 no crash point after the directory", ("worker_binding.py", '        hook("after_dir")\n', "")),
    ("W18 no crash point after the database commit", ("worker_binding.py", '        hook("after_db_commit")\n', "")),
    ("W19 the marker is never written", ("worker_binding.py", "        ws._write_marker(directory, binding_v2, OWNER, hook)\n", "")),
    ("W20 the E schema is not created", ("worker_binding.py", "                for stmt in (s.strip() for s in _SCHEMA.split(\";\") if s.strip()):\n                    con.execute(stmt)\n", "")),
    ("W21 the export accepts rows without an anchor", ("worker_binding.py", '    if anchor is None:\n        raise ws.StoreError("STORE_CORRUPT", "the binding rows carry no anchor")', '    if False:\n        raise ws.StoreError("STORE_CORRUPT", "the binding rows carry no anchor")')),
    ("W22 the export does not hash the stored document", ("worker_binding.py", '        if bd.binding_v2(document) != meta["binding_v2"]:', "        if False:")),
    ("W23 the export of a store that was never initialised succeeds", ("worker_binding.py", '    if state != "open":\n        raise ws.StoreError("STORE_MISSING", "the store was never initialised', '    if False:\n        raise ws.StoreError("STORE_MISSING", "the store was never initialised')),
    ("W24 a refused export exits 1", ("worker_binding.py", "        return 3\n    sys.stdout", "        return 1\n    sys.stdout")),
    ("W25 the export reads the state directory itself, not its worker subdirectory", ("worker_binding.py", 'doc = view_for_export(os.path.join(state_dir, "worker"))', "doc = view_for_export(state_dir)")),
    ("W26 the binding is not validated", ("worker_binding.py", "    if not isinstance(binding_v2, str) or not ws._SHA.fullmatch(binding_v2) or not isinstance(document, dict):", "    if False:")),
    ("W27 the anchor is not validated", ("worker_binding.py", "    ws._check_anchor(anchor)\n", "")),
    ("W28 the export is not one canonical line", ("worker_binding.py", 'sys.stdout.write(ws.canonical_json(doc) + "\\n")', 'sys.stdout.write(json.dumps(doc, indent=1) + "\\n")')),
    ("W29 the error line is not canonical", ("worker_binding.py", 'sys.stderr.write(ws.canonical_json({"code": e.code, "message": e.message, "reason": e.reason}) + "\\n")', 'sys.stderr.write(json.dumps({"code": e.code, "message": e.message, "reason": e.reason}, indent=1) + "\\n")')),
    ("L1 the --binding flag is ignored", ("worker_log.py", "    if ns.binding:", "    if False:")),
    ("L2 the flag takes a value", ("worker_log.py", 'ap.add_argument("--binding", action="store_true",', 'ap.add_argument("--binding", action="store",')),
    ("L3 the default export changes its indent", ("worker_log.py", "print(json.dumps(export(ns.state_dir), indent=1))", "print(json.dumps(export(ns.state_dir), indent=2))")),
]


def validate_anchors():
    bad = [(name, FILES[f].count(old)) for name, (f, old, _new) in M if FILES[f].count(old) != 1]
    if bad:
        print("INVALID anchors (nothing was run):", bad)
        return False
    return True


def run_in_copy(overrides):
    d = tempfile.mkdtemp(prefix="wbind-mutant-")
    try:
        p = os.path.join(d, "protocol")
        for sub in ("hmbc_protocol", "tests", "testtools", os.path.join("tests", "fixtures"), os.path.join("f0", "vectors")):
            os.makedirs(os.path.join(p, sub), exist_ok=True)
        tt = os.path.join(PROTO, "testtools")
        for name in os.listdir(tt):
            if name.endswith(".py"):
                shutil.copy(os.path.join(tt, name), os.path.join(p, "testtools", name))
        pkg = os.path.join(PROTO, "hmbc_protocol")
        for name in os.listdir(pkg):
            if name.endswith(".py"):
                shutil.copy(os.path.join(pkg, name), os.path.join(p, "hmbc_protocol", name))
        for rel in ("pytest.ini", os.path.join("tests", "test_worker_binding.py"), os.path.join("tests", "fixtures", "deployment-agent1-91add8c-v1-repaired-e.json"),
                    os.path.join("f0", "vectors", "d50_reference.py"), os.path.join("f0", "vectors", "export_layouts_reference.py")):
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        for name, text in overrides.items():
            with open(os.path.join(p, "hmbc_protocol", name), "w") as f:
                f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_worker_binding.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
        except subprocess.TimeoutExpired:
            return "timeout", None
        m = re.search(r"(\d+) failed", r.stdout)
        if r.returncode == 0:
            return "pass", 0
        if r.returncode == 1 and m:
            return "fail", int(m.group(1))
        return "crash", None
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    if not validate_anchors():
        return 2
    status, _ = run_in_copy({})
    if status != "pass":
        print("CONTROL FAILED: the unmutated modules do not pass their own tests (%s); nothing reported" % status)
        return 2
    print("control: unmutated modules pass all tests")
    detected = 0
    for name, (fname, old, new) in M:
        text = FILES[fname].replace(old, new)
        if text == FILES[fname]:
            print("INVALID %s | the mutation changed nothing" % name)
            return 2
        status, n = run_in_copy({fname: text})
        if status == "fail":
            detected += 1
            print("DETECTED %s | failed tests: %d" % (name, n))
        else:
            print("NOT-DETECTED(%s) %s" % (status, name))
    print("detected %d of %d" % (detected, len(M)))
    return 0 if detected == len(M) else 1


if __name__ == "__main__":
    sys.exit(main())
