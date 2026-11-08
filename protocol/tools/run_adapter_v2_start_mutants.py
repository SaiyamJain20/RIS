"""Mutation check of the successor adapter handlers the startup order (agent 2, F task 2 slice 6c). Standard library only. Same method as the other runners: one text replacement per mutant (it must match exactly once
and change the file), run the UNCHANGED tests/test_adapter_v2_start.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or
timeout is NOT detection; the unmutated copy runs first as a control. the carried adapter.py, wire.py, witness_service.py, witness_pool.py and witness_pool_driver.py are NOT mutated here (their own runners do that).

Usage (repository root):   python3 -B -I protocol/tools/run_adapter_v2_start_mutants.py        (needs pytest and the E dependencies: protocol/requirements.txt)
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
SRC = open(os.path.join(PROTO, "hmbc_protocol", "adapter_v2_start.py")).read()

# EQUIVALENT MUTANT found in run 1 and dropped (run 1: 15 of 16): T16 the reconstruction run as the witness role with the manifest's own first witness key. That key is in the live set by
# construction, so the extra witness-only check (UNKNOWN_AUTHORITY) cannot fire and the document, binding and request count are identical to the worker role's.
M = [
    ("T1 the revision is not checked against the manifest before the chain is read", [("handlers={}, schema=schema)", "handlers={}, schema=schema) if False else None")]),
    ("T2 the schema is not applied in the dry check", [("handlers={}, schema=schema)", "handlers={})")]),
    ("T3 a worker factory that cannot be called is accepted", [("if not callable(worker_factory):", "if False:")]),
    ("T4 any state directory is accepted", [("if not isinstance(state_dir, str) or not state_dir:", "if False:")]),
    ("T5 a partial witness wiring is accepted", [("if any(x is not None for x in wiring) and any(x is None for x in wiring):", "if False:")]),
    ("T6 the witness wiring is validated after the chain is read", [("    witness_ops = {} if witness_view is None else aw.witness_handlers(view=witness_view, witnesses=witnesses, transport_factory=transport_factory)\n", ""),
                                                                    ("    handlers = {", "    witness_ops = {} if witness_view is None else aw.witness_handlers(view=witness_view, witnesses=witnesses, transport_factory=transport_factory)\n    handlers = {")]),
    ("T7 the worker directory is never bound", [("    wb.bind_worker_dir(os.path.join(state_dir, WORKER_SUBDIR), r[\"binding_v2\"], r[\"document\"], r[\"anchor\"])", "    pass")]),
    ("T8 the directory is created before the deployment is verified", [("    r = bo.reconstruct(", "    os.makedirs(os.path.join(state_dir, WORKER_SUBDIR), exist_ok=True)\n    r = bo.reconstruct(")]),
    ("T9 the worker directory has another name", [('WORKER_SUBDIR = "worker"', 'WORKER_SUBDIR = "workers"')]),
    ("T10 prepare_request is not installed", [('handlers = {"prepare_request": ops.prepare_request, ', "handlers = {")]),
    ("T11 the key worker operations are not installed", [("**ops.worker_handlers(worker_factory), ", "")]),
    ("T12 the witness operations are not installed", [(", **witness_ops}", "}")]),
    ("T13 the worker is made at startup", [("    handlers = {", "    worker_factory(None)\n    handlers = {")]),
    ("T14 the bound anchor is the PBC anchor twice", [('r["document"], r["anchor"])', 'r["document"], {"pbc": r["anchor"]["pbc"], "dbc": r["anchor"]["pbc"]})')]),
    ("T15 the binding is the hash of another value", [('r["binding_v2"], r["document"]', '"0" * 64, r["document"]')]),
]


def validate_anchors():
    bad = [(name, SRC.count(old)) for name, edits in M for old, _ in edits if SRC.count(old) != 1]
    if bad:
        print("INVALID anchors (nothing was run):", bad)
        return False
    return True


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="adv2start-mutant-")
    try:
        p = os.path.join(d, "protocol")
        shutil.copytree(os.path.join(PROTO, "testtools"), os.path.join(p, "testtools"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(PROTO, "f0", "vectors"), os.path.join(p, "f0", "vectors"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(PROTO, "tests", "fixtures"), os.path.join(p, "tests", "fixtures"))
        shutil.copytree(os.path.join(PROTO, "abi"), os.path.join(p, "abi"))                  # the carried code reads the ABI manifest at import time
        shutil.copytree(os.path.join(PROTO, "hmbc_protocol"), os.path.join(p, "hmbc_protocol"), ignore=shutil.ignore_patterns("__pycache__", "adapter_v2_start.py"))
        for rel in ("pytest.ini",) + tuple(os.path.join("tests", n) for n in ("conftest.py", "support.py", "test_witness_service.py", "test_witness_service_decision.py", "test_witness_service_governance.py",
                                                                              "test_witness_service_receipt.py", "test_binding_open.py", "test_adapter_v2_start.py")):
            os.makedirs(os.path.dirname(os.path.join(p, rel)) or p, exist_ok=True)
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "hmbc_protocol", "adapter_v2_start.py"), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_adapter_v2_start.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
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
    status, _ = run_in_copy(SRC)
    if status != "pass":
        print("CONTROL FAILED: the unmutated module does not pass its own tests (%s); nothing reported" % status)
        return 2
    print("control: unmutated module passes all tests")
    detected = 0
    for name, edits in M:
        text = SRC
        for old, new in edits:
            if text.count(old) != 1:
                print("INVALID %s | anchor matches %d times: %r" % (name, text.count(old), old[:70]))
                return 2
            text = text.replace(old, new)
        if text == SRC:
            print("INVALID %s | the mutation changed nothing" % name)
            return 2
        status, n = run_in_copy(text)
        if status == "fail":
            detected += 1
            print("DETECTED %s | failed tests: %d" % (name, n))
        else:
            print("NOT-DETECTED(%s) %s" % (status, name))
    print("detected %d of %d" % (detected, len(M)))
    return 0 if detected == len(M) else 1


if __name__ == "__main__":
    sys.exit(main())
