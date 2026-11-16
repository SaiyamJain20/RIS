"""Mutation check of the pool adoption reference (agent 2, F0 revision 7). Standard library only.

For each mutant it copies `pool_adoption.py` and `test_pool_adoption.py` into a fresh temporary directory, applies ONE text replacement to the copy of the reference (the
replacement must match exactly once, and must change the file), runs the unchanged expectations there and records whether they fail. A mutant counts as DETECTED only if the
expectations ran and reported failures ("FAILED: n", exit 1). A crash or timeout is reported separately and is NOT counted as detected. The unmutated copy is run first as a control and
must pass, otherwise nothing is reported.

Usage (repository root):   python3 -B -I protocol/f0/vectors/run_pool_adoption_mutants.py > protocol/f0/evidence/pool-adoption-mutants.txt
Exit 0 only when every mutant is detected.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REF = open(os.path.join(HERE, "pool_adoption.py")).read()

MUTANTS = [
    ("Q1 first-report projection: an equivocator counts with its smallest value (revision-5-like)",
     [("consistent = {w: next(iter(ms)) for w, ms in kinds.items() if len(ms) == 1}", "consistent = {w: sorted(ms)[0] for w, ms in kinds.items()}")]),
    ("Q2 adopt on a single report", [("candidates = [m for m, ws in seen_by.items() if len(ws) >= 2]", "candidates = [m for m, ws in seen_by.items() if len(ws) >= 1]")]),
    ("Q3 threshold three instead of two (liveness mutant)", [("candidates = [m for m, ws in seen_by.items() if len(ws) >= 2]", "candidates = [m for m, ws in seen_by.items() if len(ws) >= 3]")]),
    ("Q4 no ambiguity check: take the first candidate", [("return candidates[0] if len(candidates) == 1 else None", "return candidates[0] if candidates else None")]),
    ("Q5 ignore the sequence filter", [("if msg[0] != str(sequence):\n            continue", "if False:\n            continue")]),
    ("Q6 count reports whose signature did not verify", [('if not r["validSignature"]:\n            continue', "if False:\n            continue")]),
    ("Q7 accept any witness index", [("if isinstance(w, bool) or not isinstance(w, int) or not 0 <= w <= 3:", "if isinstance(w, bool) or not isinstance(w, int):")]),
    ("Q8 decide() counts late reports in the decision", [("return adopt_recorded(snapshot, sequence)", "return adopt_recorded(list(snapshot) + list(late), sequence)")]),
    ("Q9 decide() cancels an adoption when late reports make the union ambiguous",
     [("return adopt_recorded(snapshot, sequence)",
       "got = adopt_recorded(snapshot, sequence)\n    if got is not None and adopt_recorded(list(snapshot) + list(late), sequence) is None:\n        return None\n    return got")]),
    ("Q10 identical repeats treated as equivocation", [("kinds.setdefault(w, set()).add(msg)", "kinds.setdefault(w, []).append(msg)")]),
    ("R1 refuse only when strictly less than 2 s remain (boundary)", [("if remaining <= RESERVE_S:", "if remaining < RESERVE_S:")]),
    ("R2 reproposal ignores the original deadline", [("    if close >= d:\n        return \"skipped_deadline\"", "    if False:\n        return \"skipped_deadline\"")]),
    ("R3 collection cap of 10 s dropped", [("return min(COLLECTION_CAP_MS, (remaining - RESERVE_S) * 1000)", "return (remaining - RESERVE_S) * 1000")]),
    ("R4 validity reserve 1 s instead of 2 s in the re-proposal gate", [('return "skipped_validity" if remaining_ms <= RESERVE_S * 1000 else "sent"', 'return "skipped_validity" if remaining_ms <= 1000 else "sent"')]),
    ("R5 snapshot close ignores the deadline",
     [("limit = min(REPLY_TIMEOUT_MS, d)", "limit = REPLY_TIMEOUT_MS"), ("    if d <= REPLY_TIMEOUT_MS:\n        return d, \"deadline\"", "    if False:\n        return d, \"deadline\"")]),
    ("R6 a tie between the deadline and the reply timeout is called reply-timeout", [("    if d <= REPLY_TIMEOUT_MS:\n        return d, \"deadline\"", "    if d < REPLY_TIMEOUT_MS:\n        return d, \"deadline\"")]),
    ("R7 validity is checked before the deadline",
     [("    if close >= d:\n        return \"skipped_deadline\"\n    remaining_ms = exp * 1000 - (now0 * 1000 + close)\n    return \"skipped_validity\" if remaining_ms <= RESERVE_S * 1000 else \"sent\"",
       "    remaining_ms = exp * 1000 - (now0 * 1000 + close)\n    if remaining_ms <= RESERVE_S * 1000:\n        return \"skipped_validity\"\n    return \"skipped_deadline\" if close >= d else \"sent\"")]),
    ("R8 exactly 2000 ms left is treated as eligible", [('return "skipped_validity" if remaining_ms <= RESERVE_S * 1000 else "sent"', 'return "skipped_validity" if remaining_ms < RESERVE_S * 1000 else "sent"')]),
    ("R9 all-replied accepted at the limit itself", [("_int(all_replied_at_ms, \"all_replied_at_ms\") < limit", "_int(all_replied_at_ms, \"all_replied_at_ms\") <= limit")]),
]


def run_in_copy(ref_text):
    d = tempfile.mkdtemp(prefix="pool-adoption-mutant-")
    try:
        with open(os.path.join(d, "pool_adoption.py"), "w") as f:
            f.write(ref_text)
        shutil.copy(os.path.join(HERE, "test_pool_adoption.py"), os.path.join(d, "test_pool_adoption.py"))
        try:
            p = subprocess.run([sys.executable, "-B", "-I", os.path.join(d, "test_pool_adoption.py")], capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            return "timeout", None
        out = p.stdout
        m = re.search(r"^FAILED: (\d+)$", out, re.M)
        if p.returncode == 0 and "all expectations hold" in out:
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
                print("INVALID %s | anchor matches %d times: %r" % (name, text.count(old), old[:60]))
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
