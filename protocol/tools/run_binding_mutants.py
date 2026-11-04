"""Mutation check of the D50 binding module (agent 2, F task 2 slice 2). Standard library only. Same method as the F0 runners: one text replacement per mutant (it must match exactly once and
change the file), run the UNCHANGED tests/test_binding.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or
timeout is NOT detection; the unmutated copy runs first as a control.

Usage (repository root):   python3 -B -I protocol/tools/run_binding_mutants.py        (needs pytest: protocol/requirements.txt)
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
SRC = open(os.path.join(PROTO, "hmbc_protocol", "binding.py")).read()

M = [
    ("B1 the table mask of mutant-no-nonce is wrong (16)", [('"mutant-no-nonce": (2, 8)', '"mutant-no-nonce": (2, 16)')]),
    ("B2 repaired-f admits masks up to 1023", [("\nMUT_ALL = (1 << 9) - 1\n", "\nMUT_ALL = (1 << 10) - 1\n")]),
    ("B3 the manifest mask is not compared with the table mask", [("    if (row[1] is None and not 0 <= mask <= MUT_ALL) or (row[1] is not None and mask != row[1]):", "    if (row[1] is None and not 0 <= mask <= MUT_ALL):")]),
    ("B4 the live profile() is not compared", [("    if not _is_dec(live_enum) or int(live_enum) != row[0]:\n        raise OpenRefusal(\"PROFILE_MISMATCH\", \"live profile() differs from the manifest\")\n", "")]),
    ("B5 B.profile.name is copied from the manifest instead of BASE[enum]", [('return {"name": BASE_NAME[row[0]], "enum": str(row[0])}', 'return {"name": name, "enum": str(row[0])}')]),
    ("B6 the name/enum agreement of B.profile is not checked", [("    if e > 3 or BASE_NAME[e] != p[\"name\"]:", "    if e > 3:")]),
    ("B7 repaired-f no longer requires interfaceVersion v2", [('    if f and d["interfaceVersion"] != "v2":', "    if False:")]),
    ("B8 a duplicate witness is accepted", [("        if len(set(r[\"witnesses\"])) != len(r[\"witnesses\"]):", "        if False:")]),
    ("B9 the threshold bound is not checked", [("        if not 1 <= int(r[\"threshold\"]) <= len(r[\"witnesses\"]):", "        if False:")]),
    ("B10 the canonical JSON does not sort keys", [("json.dumps(doc, sort_keys=True, separators=(\",\", \":\"), ensure_ascii=True)", "json.dumps(doc, sort_keys=False, separators=(\",\", \":\"), ensure_ascii=True)")]),
    ("B11 the hash prefix has no line feed", [('PREFIX = b"hmbc-deployment-binding/v2\\n"', 'PREFIX = b"hmbc-deployment-binding/v2"')]),
    ("B12 a range of another length than 32 is accepted", [("        if length != IMMUTABLE_SLOT_BYTES:\n            raise ValueError(f\"range {i}: length must be {IMMUTABLE_SLOT_BYTES}, got {length}\")\n", "")]),
    ("B13 overlapping or unsorted ranges are accepted", [("        if start < prev_end:\n            raise ValueError(f\"range {i}: unsorted or overlapping (start {start} < previous end {prev_end})\")\n", "")]),
    ("B14 a range past the runtime is accepted", [("        if start + length > n:\n            raise ValueError(f\"range {i}: ends at {start + length}, past the {n}-byte runtime\")\n", "")]),
    ("B15 a live runtime of another length than the pin is accepted", [("    if len(code) != n:\n        raise ValueError(f\"live runtime is {len(code)} bytes, the pin says {n}\")\n", "")]),
    ("B16 the object list may carry extra keys", [("        if set(r) != {\"start\", \"length\"}:", "        if not {\"start\", \"length\"} <= set(r):")]),
    ("B17 an unknown key in B is ignored", [("    if not set(required) <= keys or not keys <= set(required) | set(optional):", "    if not set(required) <= keys:")]),
    ("B18 immutableRefsSha256 may be present on some contracts only", [("    if any(pins) and not all(pins):\n        raise ValueError(\"immutableRefsSha256 must be present on every contract or on none\")\n", "")]),
    ("B19 repaired-f does not require immutableRefsSha256", [("    if f and not all(pins):\n        raise ValueError(\"repaired-f requires immutableRefsSha256 on every contract\")\n", "")]),
    ("B20 decimal strings may have leading zeros", [('_DEC = re.compile(r"(0|[1-9][0-9]*)")', '_DEC = re.compile(r"[0-9]+")')]),
    ("B21 the owner of the mask check order is swapped: mutations before the profile enum", [('    if not _is_dec(enum) or int(enum) != row[0]:\n        raise OpenRefusal("PROFILE_MISMATCH", "manifest profileEnum differs from the table entry for this name")\n', "")]),
    ("B22 Governance is not required under repaired-f", [('    want = {"pbc": PBC_E + (("Governance",) if f else ()), "dbc": DBC_E}', '    want = {"pbc": PBC_E, "dbc": DBC_E}')]),
    ("B23 the E mutant name accepted into B.profile.name", [('PROFILES = {"paper-strict", "paper-minimal", "repaired-e", "repaired-f"}', 'PROFILES = {"paper-strict", "paper-minimal", "repaired-e", "repaired-f", "mutant-no-nonce"}')]),
]


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="state-mutant-")
    try:
        p = os.path.join(d, "protocol")
        for sub in ("hmbc_protocol", "tests", "testtools", os.path.join("f0", "vectors"), os.path.join("tests", "fixtures")):
            os.makedirs(os.path.join(p, sub), exist_ok=True)
        for rel in ("pytest.ini", os.path.join("hmbc_protocol", "__init__.py"), os.path.join("tests", "test_binding.py"),
                    os.path.join("f0", "vectors", "d50_reference.py"), os.path.join("f0", "vectors", "d50_binding_vector.json"), os.path.join("tests", "fixtures", "deployment-agent1-91add8c-v1-repaired-e.json")):
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "hmbc_protocol", "binding.py"), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_binding.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
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
