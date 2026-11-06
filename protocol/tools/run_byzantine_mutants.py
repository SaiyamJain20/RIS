"""Mutation check of the successor adapter handlers the TEST-ONLY Byzantine variants (agent 2, F task 3 slice 7a). Standard library only. Same method as the other runners: one text replacement per mutant (it must match exactly once
and change the file), run the UNCHANGED tests/test_byzantine.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or
timeout is NOT detection; the unmutated copy runs first as a control. the carried adapter.py, wire.py, witness_service.py, witness_pool.py and witness_pool_driver.py are NOT mutated here (their own runners do that).

Usage (repository root):   python3 -B -I protocol/tools/run_byzantine_mutants.py        (needs pytest and the E dependencies: protocol/requirements.txt)
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
SRC = open(os.path.join(PROTO, "testtools", "byzantine.py")).read()

M = [
    ("Z1 a withheld witness still replies", [("ServiceEndpoint(sign, muted=True)", "ServiceEndpoint(sign)")]),
    ("Z2 a delayed reply is not delayed", [("return [(d + self.ms, r) for d, r in", "return [(d, r) for d, r in")]),
    ("Z3 a repeater repeats once", [("for d, r in self.inner.deliver(round_no, message)] * self.n", "for d, r in self.inner.deliver(round_no, message)] * 1")]),
    ("Z4 an equivocator sends no second value", [("return first + [(self.reply_delay + 1,", "return first if True else [(self.reply_delay + 1,")]),
    ("Z5 the second value is the asked one", [("other = self.alt(dict(message))", "other = dict(message)")]),
    ("Z6 the second value arrives before the first", [("self.reply_delay + 1,", "self.reply_delay - 1,")]),
    ("Z7 an equivocator mutates the caller's message", [("other = self.alt(dict(message))", "other = self.alt(message)")]),
    ("Z8 a poisoner does not poison", [("other = self.mutate(dict(message))", "other = dict(message)")]),
    ("Z9 a poisoner mutates the caller's message", [("other = self.mutate(dict(message))", "other = self.mutate(message)")]),
    ("Z10 garbage is a known reply type", [('"no-such-reply"', '"signature"')]),
    ("Z11 the view is not restored", [("    finally:\n        service._view = old", "    finally:\n        pass")]),
    ("Z12 the view is not overridden", [("    service._view = view\n    try:", "    try:")]),
    ("Z13 a wrapper loses the delivery hold", [("        return self.inner.send_delay(round_no)", "        return 0")]),
    ("Z14 the default reply delay is 200 ms", [("def __init__(self, reply_delay=100):", "def __init__(self, reply_delay=200):")]),
    ("Z15 a delayed wrapper does not record the delivery", [("        self.deliveries.append((round_no, dict(message)))\n        return [(d + self.ms, r)", "        return [(d + self.ms, r)")]),
    ("Z16 a repeater does not record the delivery", [("        self.deliveries.append((round_no, dict(message)))\n        return [(d, dict(r)) for d, r in", "        return [(d, dict(r)) for d, r in")]),
]


def validate_anchors():
    bad = [(name, SRC.count(old)) for name, edits in M for old, _ in edits if SRC.count(old) != 1]
    if bad:
        print("INVALID anchors (nothing was run):", bad)
        return False
    return True


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="byz-mutant-")
    try:
        p = os.path.join(d, "protocol")
        shutil.copytree(os.path.join(PROTO, "testtools"), os.path.join(p, "testtools"), ignore=shutil.ignore_patterns("__pycache__", "byzantine.py"))
        shutil.copytree(os.path.join(PROTO, "f0", "vectors"), os.path.join(p, "f0", "vectors"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(PROTO, "tests", "fixtures"), os.path.join(p, "tests", "fixtures"))
        shutil.copytree(os.path.join(PROTO, "abi"), os.path.join(p, "abi"))                  # the carried code reads the ABI manifest at import time
        shutil.copytree(os.path.join(PROTO, "hmbc_protocol"), os.path.join(p, "hmbc_protocol"), ignore=shutil.ignore_patterns("__pycache__"))
        for rel in ("pytest.ini",) + tuple(os.path.join("tests", n) for n in ("conftest.py", "support.py", "test_witness_service.py", "test_witness_service_decision.py", "test_witness_service_governance.py",
                                                                              "test_witness_service_receipt.py", "test_witness_pool_driver.py", "test_byzantine.py")):
            os.makedirs(os.path.dirname(os.path.join(p, rel)) or p, exist_ok=True)
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "testtools", "byzantine.py"), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_byzantine.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
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
