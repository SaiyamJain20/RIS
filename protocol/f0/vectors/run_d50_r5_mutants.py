"""Mutation check of the D50 REVISION-5 rules in the reference (agent 2). Standard library only.

Copies `d50_reference.py`, `test_d50_reference.py` and the E fixture the reference reads into a fresh temporary directory that keeps the repository layout
(protocol/f0/vectors and protocol/tests/fixtures), applies ONE text replacement to the copy of the reference (it must match exactly once and change the file), runs the unchanged
expectations there and counts a mutant as DETECTED only when they ran and reported failures ("FAILED: n", exit 1). A crash or timeout is NOT counted as detected. The unmutated
copy runs first as a control and must pass. This covers the revision-5 rules only; the revision-4 mutant record (evidence/d50-mutants.txt) is retained as it was.

Usage (repository root):   python3 -B -I protocol/f0/vectors/run_d50_r5_mutants.py > protocol/f0/evidence/d50-revision5-mutants.txt
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FIXTURE = os.path.join(ROOT, "protocol", "tests", "fixtures", "deployment-agent1-91add8c-v1-repaired-e.json")
REF = open(os.path.join(HERE, "d50_reference.py")).read()

MUTANTS = [
    ("D1 B.profile.name copied from the manifest instead of BASE[enum] (the revision-4 behaviour)", [('return {"name": BASE_NAME[row[0]], "enum": str(row[0])}', 'return {"name": name, "enum": str(row[0])}')]),
    ("D2 the live profile() is not compared with the table", [("    if not _is_dec(live_enum) or int(live_enum) != row[0]:\n        raise OpenRefusal(\"PROFILE_MISMATCH\", \"live profile() differs from the manifest\")\n", "")]),
    ("D3 the manifest profileEnum is not compared with the table", [("    if not _is_dec(enum) or int(enum) != row[0]:\n        raise OpenRefusal(\"PROFILE_MISMATCH\", \"manifest profileEnum differs from the table entry for this name\")\n", "")]),
    ("D4 the manifest mask is not compared with the table mask", [("    if (row[1] is None and not 0 <= mask <= MUT_ALL) or (row[1] is not None and mask != row[1]):", "    if (row[1] is None and not 0 <= mask <= MUT_ALL):")]),
    ("D5 the live per-contract mutations are not compared with the manifest", [("        if not _is_dec(v) or int(v) != mask:\n            raise OpenRefusal(\"MUTATIONS_MISMATCH\", f\"live mutations of {n} differ from the manifest\")", "        if False:\n            raise OpenRefusal(\"MUTATIONS_MISMATCH\", f\"live mutations of {n} differ from the manifest\")")]),
    ("D6 an F deployment may omit the Governance live mask", [('want = set(MASK_HOLDERS_E) | ({"Governance"} if row[0] == 3 else set())', "want = set(live_mutations) if isinstance(live_mutations, dict) else set()")]),
    ("D7 an unknown manifest name is reported as MUTATIONS_MISMATCH", [('raise OpenRefusal("PROFILE_MISMATCH", "manifest profile name is not in the closed table")', 'raise OpenRefusal("MUTATIONS_MISMATCH", "manifest profile name is not in the closed table")')]),
    ("D8 the name/enum agreement of B.profile is not checked", [("    if e > 3 or BASE_NAME[e] != p[\"name\"]:", "    if e > 3:")]),
    ("D9 repaired-f no longer requires interfaceVersion v2", [('    if f and d["interfaceVersion"] != "v2":', "    if False:")]),
    ("D10 a duplicate witness member is accepted", [("        if len(set(r[\"witnesses\"])) != len(r[\"witnesses\"]):", "        if False:")]),
    ("D11 the threshold bound is not checked", [("        if not 1 <= int(r[\"threshold\"]) <= len(r[\"witnesses\"]):", "        if False:")]),
    ("D12 repaired-f admits masks up to 1023", [("\nMUT_ALL = (1 << 9) - 1\n", "\nMUT_ALL = (1 << 10) - 1\n")]),
    ("D13 the table mask of mutant-no-nonce is wrong (16)", [('"mutant-no-nonce": (2, 8)', '"mutant-no-nonce": (2, 16)')]),
    ("D14 paper-minimal has the wrong table enum (2)", [('"paper-minimal": (1, 0)', '"paper-minimal": (2, 0)')]),
    ("D15 a non-string live mask is accepted as the integer value", [("def _is_dec(v):\n    return isinstance(v, str) and _DEC.fullmatch(v) is not None", "def _is_dec(v):\n    return _DEC.fullmatch(str(v)) is not None")]),
]


def run_in_copy(ref_text):
    d = tempfile.mkdtemp(prefix="d50-r5-mutant-")
    try:
        vec = os.path.join(d, "protocol", "f0", "vectors")
        fix = os.path.join(d, "protocol", "tests", "fixtures")
        os.makedirs(vec)
        os.makedirs(fix)
        with open(os.path.join(vec, "d50_reference.py"), "w") as f:
            f.write(ref_text)
        shutil.copy(os.path.join(HERE, "test_d50_reference.py"), os.path.join(vec, "test_d50_reference.py"))
        shutil.copy(FIXTURE, fix)
        try:
            p = subprocess.run([sys.executable, "-B", "-I", os.path.join(vec, "test_d50_reference.py")], capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            return "timeout", None
        m = re.search(r"^FAILED: (\d+)$", p.stdout, re.M)
        if p.returncode == 0 and "all expectations hold" in p.stdout:
            return "pass", 0
        if p.returncode == 1 and m:
            return "fail", int(m.group(1))
        return "crash", None
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    status, _ = run_in_copy(REF)
    if status != "pass":
        print("CONTROL FAILED: the unmutated reference does not pass its own expectations (%s); nothing reported" % status)
        return 2
    print("control: unmutated reference passes all expectations")
    detected = 0
    for name, edits in MUTANTS:
        text = REF
        for old, new in edits:
            if text.count(old) != 1:
                print("INVALID %s | anchor matches %d times: %r" % (name, text.count(old), old[:70]))
                return 2
            text = text.replace(old, new)
        if text == REF:
            print("INVALID %s | the mutation changed nothing" % name)
            return 2
        status, n = run_in_copy(text)
        if status == "fail":
            detected += 1
            print("DETECTED %s | failed expectations: %d" % (name, n))
        else:
            print("NOT-DETECTED(%s) %s" % (status, name))
    print("detected %d of %d" % (detected, len(MUTANTS)))
    return 0 if detected == len(MUTANTS) else 1


if __name__ == "__main__":
    sys.exit(main())
