"""Mutation check of the TEST-ONLY real-process Byzantine witness testtools/divergent_witness.py (agent 2, F phase; gap G2). Standard library only. Same method as the other runners: one text edit set per mutant
(each anchor must match exactly once and the text must change), run the UNCHANGED tests/test_divergent_witness.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests
ran and failed (a crash or a timeout is not detection); the unmutated copy runs first as a control with no skip. Mutants in E are ARGUED EQUIVALENTS and are RUN: they must SURVIVE.

OFFLINE ONLY: the live behaviour against a real pool and ledger is tests/test_divergent_witness_live.py and is not mutated here.

Usage (repository root):   python3 -B -I protocol/tools/run_divergent_witness_mutants.py        (needs pytest: protocol/requirements.txt)        Exit 0 only when the control passes, every M mutant is detected and every E mutant survives.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.abspath(os.path.join(HERE, ".."))
TARGET = "testtools/divergent_witness.py"
TESTS = ["tests/test_divergent_witness.py"]
SRC = open(os.path.join(PROTO, TARGET)).read()

M = [
    ("D1 the read divergence adds nothing", [("            out[self.field] = str(int(out[self.field]) + self.n)", "            out[self.field] = out[self.field]")]),
    ("D2 the read divergence adds one", [("            out[self.field] = str(int(out[self.field]) + self.n)", "            out[self.field] = str(int(out[self.field]) + 1)")]),
    ("D3 the read divergence subtracts", [("            out[self.field] = str(int(out[self.field]) + self.n)", "            out[self.field] = str(int(out[self.field]) - self.n)")]),
    ("D4 every read field diverges", [("        if self.field in READ_FIELDS and isinstance(out.get(self.field), str) and _DEC.fullmatch(out[self.field]):\n            out[self.field] = str(int(out[self.field]) + self.n)", "        for k in READ_FIELDS:\n            if isinstance(out.get(k), str) and _DEC.fullmatch(out[k]):\n                out[k] = str(int(out[k]) + self.n)")]),
    ("D5 a non-decimal real read is guessed at", [("isinstance(out.get(self.field), str) and _DEC.fullmatch(out[self.field])", "isinstance(out.get(self.field), str)")]),
    ("D6 the head lag subtracts nothing", [("        return max(head - self.n, 0)", "        return head")]),
    ("D7 the head lag may go below genesis", [("        return max(head - self.n, 0)", "        return head - self.n")]),
    ("D8 the lagged head is not reported by observe", [('        if self.field != "headLag" or chain != "pbc":\n            return real', "        if True:\n            return real")]),
    ("D9 the lag applies to the DBC too", [('        if self.field != "headLag" or chain != "pbc":', '        if self.field != "headLag":')]),
    ("D10 the lagged block reports the real chain id of the other chain", [('"chainId": real["chainId"], "blockNumber": str(n)', '"chainId": "0", "blockNumber": str(n)')]),
    ("D11 newer blocks stay visible under a lag", [('        if self.field == "headLag" and number > self._lagged_head():\n            return None\n', "")]),
    ("D12 the lagged head itself is hidden", [("number > self._lagged_head()", "number >= self._lagged_head()")]),
    ("D13 a read-divergence view also hides blocks", [('        if self.field == "headLag" and number > self._lagged_head():', "        if number > self._lagged_head():")]),
    ("D14 a read lag changes no read (lag affects reads_at)", [("    def reads_at(self, number):\n        out = dict(self._inner.reads_at(number))", "    def reads_at(self, number):\n        out = dict(self._inner.reads_at(number)) if self.field != 'headLag' else dict(self._inner.reads_at(max(number - 1, 0)))")]),
    ("D15 other methods are not delegated", [("        return getattr(self._inner, name)", "        raise AttributeError(name)")]),
    ("D16 the spec accepts N = 0", [('_SPEC = re.compile(r"(authEpoch|policyVersion|witnessSetVersion|headLag):([1-9][0-9]?)")', '_SPEC = re.compile(r"(authEpoch|policyVersion|witnessSetVersion|headLag):([0-9][0-9]?)")')]),
    ("D17 the spec accepts a leading zero", [('([1-9][0-9]?)")', '(0?[1-9][0-9]?)")')]),
    ("D18 the spec accepts N above the maximum", [("or not 1 <= int(m.group(2)) <= MAX_N", "")]),
    ("D19 the spec accepts keyEpoch", [('(authEpoch|policyVersion|witnessSetVersion|headLag)', '(authEpoch|policyVersion|witnessSetVersion|headLag|keyEpoch)')]),
    ("D20 the spec is matched by prefix only", [("_SPEC.fullmatch(text)", "_SPEC.match(text)")]),
    ("D21 install wraps nothing", [("        return DivergentView(original(cls, *args, **kwargs), spec)", "        return original(cls, *args, **kwargs)")]),
    ("D22 install accepts a malformed spec", [("    parse_spec(spec)\n    original = ", "    original = ")]),
    ("D23 a missing --view is accepted", [("    try:\n        parse_spec(args.view)\n    except ValueError:", "    try:\n        args.view and parse_spec(args.view)\n    except ValueError:")]),
    ("D24 a deployment without a TEST-ONLY derivation is accepted", [("        require_test_only(deployment)\n", "        pass\n")]),
    ("D25 a missing deployment is accepted", [('    if args.deployment is None:\n        raise SystemExit("refusing: --deployment is required")\n', "")]),
    ("D26 the deployment argument is not passed on", [('    return witness_main.main(["--deployment", args.deployment, *rest])', "    return witness_main.main(rest)")]),
    ("D27 the view is installed after the witness started", [("    install(args.view)\n    return witness_main.main(", "    rc = witness_main.main(")]),
]

E = []                                                                       # no mutant of this module was argued equivalent: every one changes a behaviour the tests pin


def build_tree():
    d = tempfile.mkdtemp(prefix="dv-mutant-")
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
