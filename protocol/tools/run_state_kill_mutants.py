"""Mutation check of the RANDOM-SIGKILL durability tests of the witness store (agent 2, F phase). Standard library only. Same method as the other runners: one text edit set per mutant (each anchor
must match exactly once and the text must change), run the UNCHANGED tests/test_witness_state_kill.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the
tests ran and failed (a crash or timeout is NOT detection); the unmutated copy runs first as a control. Mutants in E are ARGUED EQUIVALENTS and are RUN: they must SURVIVE.

  K1 the signing transaction is removed (BEGIN, COMMIT and the read-only ROLLBACK become no-ops), so each statement of one signing autocommits separately: a kill between them leaves a pin without
     a digest or a digest without its observation. Detected only if the kill lands between two of those commits.
  K2 initialisation writes the INITIALIZED marker BEFORE the database is committed: a kill in between leaves a marker without a database, which the next init_store refuses.
  E1 `synchronous=FULL` becomes OFF at both sites. A SIGKILL does not discard the kernel's page cache, so this cannot be seen by killing a process: it needs power loss or an OS crash. This
     mutant is RUN and must SURVIVE: that is the honest statement of what this test file does not measure.
Usage (repository root):   python3 -B -I protocol/tools/run_state_kill_mutants.py        (needs pytest: protocol/requirements.txt)     Exit 0 only when every M mutant is detected and every E mutant survives.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.abspath(os.path.join(HERE, ".."))
SRC = open(os.path.join(PROTO, "hmbc_protocol", "witness_state.py")).read()

M = [
    ("K1 the signing transaction is removed: every statement autocommits on its own",
     [('            self._con.execute("BEGIN IMMEDIATE")\n            pending = None', "            pending = None"),
      ('                self._hook("before_commit")\n                self._con.execute("COMMIT")', '                self._hook("before_commit")'),
      ('                    self._con.execute("ROLLBACK")\n                    return self._stored', "                    return self._stored")]),
    ("K2 the INITIALIZED marker is written before the database exists",
     [("        db, marker, tmp = _paths(directory)\n        if state == \"interrupted\":", "        db, marker, tmp = _paths(directory)\n        _write_marker(directory, binding_v2, owner, hook)\n        if state == \"interrupted\":"),
      ("        hook(\"after_db_commit\")\n        _write_marker(directory, binding_v2, owner, hook)\n", "        hook(\"after_db_commit\")\n")]),
]
E = [
    ("E1 synchronous=FULL becomes OFF (only power loss can show it; SIGKILL cannot)",
     [('                con.execute("PRAGMA synchronous=FULL")\n                con.execute("BEGIN")', '                con.execute("PRAGMA synchronous=OFF")\n                con.execute("BEGIN")'),
      ('        self._con.execute("PRAGMA synchronous=FULL")\n        self._con.execute("PRAGMA busy_timeout=30000")', '        self._con.execute("PRAGMA synchronous=OFF")\n        self._con.execute("PRAGMA busy_timeout=30000")')]),
]
FILES = ("pytest.ini", os.path.join("hmbc_protocol", "__init__.py"), os.path.join("tests", "test_witness_state.py"), os.path.join("tests", "test_witness_state_kill.py"),
         os.path.join("tests", "state_kill_child.py"), os.path.join("testtools", "__init__.py"), os.path.join("testtools", "state_oracle.py"), os.path.join("f0", "vectors", "d50_reference.py"),
         os.path.join("f0", "vectors", "export_layouts_reference.py"), os.path.join("tests", "fixtures", "deployment-agent1-91add8c-v1-repaired-e.json"))


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="state-kill-mutant-")
    try:
        p = os.path.join(d, "protocol")
        for sub in ("hmbc_protocol", "tests", "testtools", os.path.join("f0", "vectors"), os.path.join("tests", "fixtures")):
            os.makedirs(os.path.join(p, sub), exist_ok=True)
        for rel in FILES:
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "hmbc_protocol", "witness_state.py"), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", HMBC_KILL_TRIALS=os.environ.get("HMBC_KILL_TRIALS", "40"))
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_witness_state_kill.py"], cwd=p, capture_output=True, text=True, timeout=900, env=env)
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


def mutate(name, edits):
    text = SRC
    for old, new in edits:
        if text.count(old) != 1:
            print("INVALID %s | anchor matches %d times: %r" % (name, text.count(old), old[:70]))
            return None
        text = text.replace(old, new)
    if text == SRC:
        print("INVALID %s | the mutation changed nothing" % name)
        return None
    return text


def main():
    status, _ = run_in_copy(SRC)
    if status != "pass":
        print("CONTROL FAILED: the unmutated store does not pass its own kill tests (%s); nothing reported" % status)
        return 2
    print("control: unmutated store passes all kill tests")
    detected, ok = 0, True
    for name, edits in M:
        text = mutate(name, edits)
        if text is None:
            return 2
        status, n = run_in_copy(text)
        if status == "fail":
            detected += 1
            print("DETECTED %s | failed tests: %d" % (name, n))
        else:
            ok = False
            print("NOT-DETECTED(%s) %s" % (status, name))
    survived = 0
    for name, edits in E:
        text = mutate(name, edits)
        if text is None:
            return 2
        status, n = run_in_copy(text)
        print("EQUIVALENT %s | survived: %s (status %s)" % (name, status == "pass", status))
        if status == "pass":
            survived += 1
        else:
            ok = False
    print("detected %d of %d; equivalent survivors %d of %d" % (detected, len(M), survived, len(E)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
