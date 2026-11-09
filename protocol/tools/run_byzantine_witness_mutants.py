"""Mutation check of the TEST-ONLY real-process Byzantine witness testtools/byzantine_witness.py (agent 2, F phase; gap G1). Standard library only. Same method as the other runners: one text edit set per mutant
(each anchor must match exactly once and the text must change), run the UNCHANGED tests/test_byzantine_witness.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests
ran and failed (a crash or a timeout is not detection); the unmutated copy runs first as a control with no skip. Mutants in E are ARGUED EQUIVALENTS and are RUN: they must SURVIVE.

OFFLINE ONLY: the live behaviour against a real pool and ledger is tests/test_byzantine_witness_live.py and is not mutated here.

Usage (repository root):   python3 -B -I protocol/tools/run_byzantine_witness_mutants.py        (needs pytest: protocol/requirements.txt)        Exit 0 only when the control passes, every M mutant is detected and every E mutant survives.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.abspath(os.path.join(HERE, ".."))
TARGET = "testtools/byzantine_witness.py"
TESTS = ["tests/test_byzantine_witness.py"]
SRC = open(os.path.join(PROTO, TARGET)).read()

M = [
    ("B1 the decimal poison does nothing", [("        return str(int(value) + 1)", "        return value")]),
    ("B2 the hex poison does nothing", [("        return value[:-1] + _NIBBLES[(int(value[-1], 16) + 1) % 16]", "        return value")]),
    ("B3 impersonate signs with the witness's own key", [('bz.sign_message(impersonated_key, typ, message, deployment)', 'bz.sign_message(key, typ, message, deployment)')]),
    ("B4 repeat writes one time too few", [("            for _ in range(int(arg)):", "            for _ in range(int(arg) - 1):")]),
    ("B5 withhold answers", [('        if name == "withhold":\n            return len(text)\n', "")]),
    ("B6 equivocate never writes the second value", [('        if name == "equivocate" and ctx is not None and ctx[1] is not None:', "        if False:")]),
    ("B7 the second value is signed by an outsider key", [("sig = bz.sign_message(self._key, TYPE_OF[kind], alt, self._deployment)", 'sig = bz.sign_message(keys.synthetic_private_key("outsider"), TYPE_OF[kind], alt, self._deployment)')]),
    ("B8 garbage answers with a signature reply", [('            return wm._answer(ident, {"type": "bogus"})', '            return wm._answer(ident, {"type": "signature", "message": message, "signature": "0x" + "00" * 65})')]),
    ("B9 the label is not checked against the witness at the index", [("    if witnesses[index] != Account.from_key(key).address.lower():", "    if False:")]),
    ("B10 a deployment without a TEST-ONLY derivation is accepted", [('or not derivation.startswith("TEST-ONLY") or len(witnesses) != 4', " or len(witnesses) != 4")]),
    ("B11 the light behaviours start the production service", [('    if name in ("repeat", "equivocate"):\n        try:', "    if True:\n        try:")]),
    ("B12 poison of an absent field raises", [("            if arg in poisoned:\n                poisoned[arg] = mutate(poisoned[arg])", "            poisoned[arg] = mutate(poisoned[arg])")]),
    ("B13 repeat accepts N = 1", [('_REPEAT = re.compile(r"repeat:([2-8])")', '_REPEAT = re.compile(r"repeat:([1-8])")')]),
    ("B14 repeat accepts N = 9", [('_REPEAT = re.compile(r"repeat:([2-8])")', '_REPEAT = re.compile(r"repeat:([2-9])")')]),
    ("B15 impersonate accepts J = 4", [('_IMPERSONATE = re.compile(r"impersonate:([0-3])")', '_IMPERSONATE = re.compile(r"impersonate:([0-4])")')]),
    ("B16 the poison field list is open (any name)", [('_POISON = re.compile(r"poison:(" + "|".join(FIELDS) + ")")', '_POISON = re.compile(r"poison:([A-Za-z]+)")')]),
    ("B17 a malformed request is answered as a garbage reply", [("        if kind is None:\n            return wm._answer(ident, dict(wm.MALFORMED))", "        if kind is None:\n            return wm._answer(ident, {\"type\": \"bogus\"})")]),
    ("B18 the equivocation field of a checkpoint is the sequence", [('EQUIVOCATE_FIELD = {"checkpoint": "sourceBlockNumber",', 'EQUIVOCATE_FIELD = {"checkpoint": "sequence",')]),
    ("B19 a start-up failure prints a usage text instead of the closed line", [("    def _error(message):                                                             # never print a usage text or exit: the caller turns it into the one closed refusal\n        raise ValueError(\"malformed arguments\")", "    def _error(message):\n        sys.stderr.write(message)\n        raise ValueError(\"malformed arguments\")")]),
]

E = []                                                                       # no mutant of this module was argued equivalent: every one changes a behaviour the tests pin


def build_tree():
    d = tempfile.mkdtemp(prefix="bw-mutant-")
    p = os.path.join(d, "protocol")
    for sub in ("testtools", "hmbc_protocol", "abi", "exports"):
        shutil.copytree(os.path.join(PROTO, sub), os.path.join(p, sub), ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(PROTO, "f0", "vectors"), os.path.join(p, "f0", "vectors"), ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(PROTO, "tests", "fixtures"), os.path.join(p, "tests", "fixtures"))
    for rel in ["pytest.ini"] + TESTS:
        os.makedirs(os.path.dirname(os.path.join(p, rel)) or p, exist_ok=True)
        shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
    return d, p


def run_tests(p):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rs", *TESTS], cwd=p, capture_output=True, text=True, timeout=300, env=env)
    except subprocess.TimeoutExpired:
        return "timeout", None
    skipped = re.search(r"(\d+) skipped", r.stdout)
    if r.returncode == 0:
        return ("pass-with-skips" if skipped else "pass"), 0
    m = re.search(r"(\d+) failed", r.stdout)
    if r.returncode == 1 and m:
        return "fail", int(m.group(1))
    return "crash", None


def mutate(name, edits):
    text = SRC
    for old, new in edits:
        if text.count(old) != 1:
            print("INVALID %s | anchor matches %d times: %r" % (name, text.count(old), old[:70]))
            return None
        text = text.replace(old, new)
    if text == SRC and name[0] != "E":
        print("INVALID %s | the mutation changed nothing" % name)
        return None
    return text


def main():
    d, p = build_tree()
    try:
        status, _ = run_tests(p)
        if status != "pass":
            print("CONTROL FAILED: the unmutated module does not pass its own tests (%s); nothing reported" % status)
            return 2
        print("control: the unmutated module passes all tests with no skip")
        detected, ok = 0, True
        for name, edits in M:
            text = mutate(name, edits)
            if text is None:
                return 2
            with open(os.path.join(p, TARGET), "w") as f:
                f.write(text)
            status, n = run_tests(p)
            if status == "fail":
                detected += 1
                print("DETECTED %s | failed tests: %d" % (name, n))
            else:
                ok = False
                print("NOT-DETECTED(%s) %s" % (status, name))
        survived = 0
        for name, why, edits in E:
            text = mutate(name, edits)
            if text is None:
                return 2
            with open(os.path.join(p, TARGET), "w") as f:
                f.write(text)
            status, _ = run_tests(p)
            print("EQUIVALENT %s | %s | survived: %s (status %s)" % (name, why, status == "pass", status))
            survived += status == "pass"
            ok = ok and status == "pass"
        print("detected %d of %d; equivalent survivors %d of %d" % (detected, len(M), survived, len(E)))
        return 0 if ok else 1
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
