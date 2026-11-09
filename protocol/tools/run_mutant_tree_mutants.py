"""Check that the seven REGISTERED source mutants M1..M7 (testtools/mutant_tree.py) are REAL behaviour changes, not no-ops (agent 2, F phase; gap G3). Standard library only. For each mutant: build its tree with the
registry's own `build` (the same code the F runner will use), place the UNCHANGED existing unit tests of the mutated module next to it in a temporary `protocol/` layout, run them, and count the mutant DETECTED
only when the tests ran and failed (a crash or a timeout is not detection). A control tree (a plain copy of the production packages) runs the same tests first and must pass with no skip other than the one argued in KNOWN_SKIP.

This shows that the baseline tests REJECT each weakened behaviour. It does NOT show what the F oracles will see: the integrated runs with a mutant started as a process are separate (tests/test_mutant_tree_live.py).

Usage (repository root):   python3 -B -I protocol/tools/run_mutant_tree_mutants.py        (needs pytest: protocol/requirements.txt)        Exit 0 only when the control passes and every mutant is detected.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PROTO)
from testtools import mutant_tree as mt  # noqa: E402

STATE = ["tests/test_witness_state.py", "tests/test_witness_state_cli.py", "tests/test_witness_state_lock.py"]
KNOWN_SKIP = "a disposable copy has no repository"        # test_witness_service_governance.py: a published blob is read from git, and a temporary copy has no repository (also skipped in the service runner's copy)
SERVICE = ["tests/test_witness_service.py", "tests/test_witness_service_decision.py", "tests/test_witness_service_receipt.py", "tests/test_witness_service_governance.py"]
POOL = ["tests/test_witness_pool.py", "tests/test_witness_pool_driver.py", "tests/test_pool_core.py"]
HELPERS = {"M5": ["tests/test_witness_service.py"]}               # test_witness_pool_driver.py imports its fixtures from test_witness_service.py (imported, not run)
TESTS = {"M1": STATE, "M2": STATE, "M3": STATE, "M4": SERVICE, "M5": POOL, "M6": SERVICE, "M7": SERVICE}


def layout(tree, tests, helpers=()):
    """Make `tree` (hmbc_protocol + testtools already in place) a `protocol/` root the tests can run in."""
    for sub in ("tests", os.path.join("tests", "fixtures"), os.path.join("f0", "vectors")):
        os.makedirs(os.path.join(tree, sub), exist_ok=True)
    shutil.copy(os.path.join(PROTO, "pytest.ini"), os.path.join(tree, "pytest.ini"))
    for name in os.listdir(os.path.join(PROTO, "tests")):
        src = os.path.join(PROTO, "tests", name)
        if os.path.isfile(src) and name != "conftest.py" and (name in {os.path.basename(t) for t in (*tests, *helpers)} or not name.startswith("test_")):          # conftest.py reads abi/manifest.json: the unit tests do not need it
            shutil.copy(src, os.path.join(tree, "tests", name))
    for sub in (os.path.join("tests", "fixtures"), os.path.join("f0", "vectors"), "f0"):          # f0/ holds the design documents some pool tests read (SUCCESSOR-WIRE.md)
        os.makedirs(os.path.join(tree, sub), exist_ok=True)
        for name in os.listdir(os.path.join(PROTO, sub)):
            if os.path.isfile(os.path.join(PROTO, sub, name)):
                shutil.copy(os.path.join(PROTO, sub, name), os.path.join(tree, sub, name))


def run(tree, tests):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rs", *tests], cwd=tree, capture_output=True, text=True, timeout=900, env=env)
    except subprocess.TimeoutExpired:
        return "timeout", None
    m = re.search(r"(\d+) failed", r.stdout)
    if r.returncode == 0:
        skips = [ln for ln in r.stdout.splitlines() if ln.startswith("SKIPPED")]
        unknown = [ln for ln in skips if KNOWN_SKIP not in ln]                       # a skip nobody argued for is not a pass: read the skip count, not only "passed"
        return ("skip" if unknown else "pass"), len(skips)
    if r.returncode == 1 and m:
        return "fail", int(m.group(1))
    return "crash", None


def main():
    d = tempfile.mkdtemp(prefix="mutant-tree-check-")
    try:
        control = os.path.join(d, "control")
        os.makedirs(control)
        for pkg in mt.PACKAGES:
            shutil.copytree(os.path.join(PROTO, pkg), os.path.join(control, pkg), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        results = {}
        for mid, tests in TESTS.items():
            ctl = os.path.join(d, "ctl-" + mid, "protocol")                       # the tests locate `protocol/f0/vectors` from the repository root: the tree must sit under a `protocol` directory
            os.makedirs(os.path.dirname(ctl))
            shutil.copytree(control, ctl)
            layout(ctl, tests, HELPERS.get(mid, ()))
            status, skips = run(ctl, tests)
            if status != "pass":
                print("CONTROL FAILED for %s: the unmutated tree does not pass its own tests (%s); nothing reported" % (mid, status))
                return 2
            print("control %s: the unmutated tree passes %s (%d argued skip)" % (mid, ",".join(os.path.basename(t) for t in tests), skips))
        detected = 0
        for mid, tests in TESTS.items():
            tree = os.path.join(d, "mut-" + mid, "protocol")
            mt.build(mid, tree)
            layout(tree, tests, HELPERS.get(mid, ()))
            status, n = run(tree, tests)
            mu = mt.MUTANTS[mid]
            if status == "fail":
                detected += 1
                print("DETECTED %s (%s) %s | failed tests: %d" % (mid, ",".join(mu.rows), mu.what, n))
            else:
                print("NOT-DETECTED(%s) %s (%s) %s" % (status, mid, ",".join(mu.rows), mu.what))
        print("detected %d of %d" % (detected, len(TESTS)))
        return 0 if detected == len(TESTS) else 1
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
