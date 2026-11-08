"""Mutation check of the pool decision core (agent 2, F task 3 slice 3a). Standard library only. Same method as the other runners: one text replacement per mutant (it must match exactly once and
change the file), run the UNCHANGED tests/test_pool_core.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or timeout
is NOT detection; the unmutated copy runs first as a control.

Usage (repository root):   python3 -B -I protocol/tools/run_pool_core_mutants.py        (needs pytest: protocol/requirements.txt)
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
SRC = open(os.path.join(PROTO, "hmbc_protocol", "pool_core.py")).read()

M = [
    ("P1 an inconsistent witness is kept as a consistent reporter", [("if len(d) == 1}", "if len(d) >= 1}")]),
    ("P2 two distinct values are not enough to be inconsistent (three needed)", [("if len(d) >= 2}", "if len(d) >= 3}")]),
    ("P3 one reporter is enough to adopt", [("if len(ws) >= 2]", "if len(ws) >= 1]")]),
    ("P4 three reporters are needed to adopt", [("if len(ws) >= 2]", "if len(ws) >= 3]")]),
    ("P5 an ambiguous split adopts the first candidate", [("    if len(candidates) != 1:\n        return None\n", "    if len(candidates) < 1:\n        return None\n")]),
    ("P6 an invalid-signature report is not ignored", [('if not r["validSignature"] or r["message"]["sequence"] != seq:', 'if r["message"]["sequence"] != seq:')]),
    ("P7 a report for another sequence is not ignored", [('if not r["validSignature"] or r["message"]["sequence"] != seq:', 'if not r["validSignature"]:')]),
    ("P8 witness index 4 is accepted", [("not 0 <= w < WITNESS_COUNT", "not 0 <= w <= WITNESS_COUNT")]),
    ("P9 a boolean witness index is accepted", [("if isinstance(w, bool) or not isinstance(w, int) or not 0 <= w", "if not isinstance(w, int) or not 0 <= w")]),
    ("P10 a non-boolean validSignature is accepted", [('        if not isinstance(r["validSignature"], bool):\n            raise PoolCoreError("validSignature must be a boolean")\n', "")]),
    ("P11 the largest signature is kept", [('r["signature"] < slot[c][1]', 'r["signature"] > slot[c][1]')]),
    ("P12 the first-arrived signature is kept", [('if c not in slot or r["signature"] < slot[c][1]:', "if c not in slot:")]),
    ("P13 the canonical form does not sort keys", [("return json.dumps(message, sort_keys=True)", "return json.dumps(message)")]),
    ("P14 the decision uses the late reports", [("    classify(late, sequence)\n    return adopt_recorded(snapshot, sequence)\n", "    return adopt_recorded(snapshot + late, sequence)\n")]),
    ("P15 the shape of late reports is not checked by decide", [("    classify(late, sequence)\n    return adopt_recorded(snapshot, sequence)\n", "    return adopt_recorded(snapshot, sequence)\n")]),
    ("P16 the collection cap is 20 s", [("COLLECTION_CAP_MS = 10000", "COLLECTION_CAP_MS = 20000")]),
    ("P17 exactly 2 s remaining still starts a collection", [("    if remaining <= RESERVE_S:\n        return None", "    if remaining < RESERVE_S:\n        return None")]),
    ("P18 the 2 s reserve is not subtracted from the deadline", [("(remaining - RESERVE_S) * 1000", "remaining * 1000")]),
    ("P19 all-replied accepts a reply exactly at the limit", [("all_replied_at_ms, \"all_replied_at_ms\") < limit", "all_replied_at_ms, \"all_replied_at_ms\") <= limit")]),
    ("P20 a deadline tie with the reply timeout is the reply timeout", [("    if d <= REPLY_TIMEOUT_MS:\n        return d, \"deadline\"", "    if d < REPLY_TIMEOUT_MS:\n        return d, \"deadline\"")]),
    ("P21 a snapshot closing exactly at the deadline is not skipped", [("    if close >= d:\n        return \"skipped_deadline\"", "    if close > d:\n        return \"skipped_deadline\"")]),
    ("P22 exactly 2000 ms of validity is sent", [("return \"skipped_validity\" if remaining_ms <= RESERVE_S * 1000 else \"sent\"", "return \"skipped_validity\" if remaining_ms < RESERVE_S * 1000 else \"sent\"")]),
    ("P23 a boolean time input is accepted", [("    if isinstance(v, bool) or not isinstance(v, int) or v < 0:\n        raise PoolCoreError(f\"{what}", "    if not isinstance(v, int) or v < 0:\n        raise PoolCoreError(f\"{what}")]),
    ("P24 a negative time input is accepted", [("not isinstance(v, int) or v < 0:\n        raise PoolCoreError(f\"{what}", "not isinstance(v, int):\n        raise PoolCoreError(f\"{what}")]),
    ("P25 a late report is accepted after a snapshot closed at the deadline", [('    if by == "deadline" and late:', "    if False:")]),
    ("P26 recordedReports is emitted even when empty", [("    if consistent:\n        out[\"recordedReports\"]", "    if True:\n        out[\"recordedReports\"]")]),
    ("P27 timing is emitted even when no member is", [("    if out:\n        out[\"timing\"]", "    if True:\n        out[\"timing\"]")]),
    ("P28 lateReports is not sorted by witness index", [("for w, d in sorted(late_kept.items()) for c in sorted(d)]", "for w, d in late_kept.items() for c in sorted(d)]")]),
    ("P29 lateReports is not sorted by canonical message", [("for w, d in sorted(late_kept.items()) for c in sorted(d)]", "for w, d in sorted(late_kept.items()) for c in d]")]),
    ("P30 recordedReports follow arrival order, not the witness index", [("for w, d in sorted(kinds.items()) if len(d) == 1}", "for w, d in kinds.items() if len(d) == 1}")]),
    ("P31 an equivocator's values are not in canonical order", [("[_report(d[c]) for c in sorted(d)]", "[_report(d[c]) for c in d]")]),
    ("P32 the gate is evaluated on the proposal's expiry, not the adopted value's", [("reproposal_status(now0, int(expires), close, deadline)", "reproposal_status(now0, prop, close, deadline)")]),
    ("P33 the gate gets the close and the deadline swapped", [("reproposal_status(now0, int(expires), close, deadline)", "reproposal_status(now0, int(expires), deadline, close)")]),
    ("P34 the snapshot never closes by all-replied", [("close, by = snapshot_close(deadline, all_at)", "close, by = snapshot_close(deadline, None)")]),
    ("P35 late reports are mixed with the snapshot for the selection", [("consistent, inconsistent = classify(snapshot, seq)", "consistent, inconsistent = classify(snapshot + late, seq)")]),
    ("P36 the adopted message aliases the recorded report", [('            return dict(rep["message"])', '            return rep["message"]')]),
    ("P37 evidence members alias the input messages", [('return {"message": dict(entry[0]), "signature": entry[1]}', 'return {"message": entry[0], "signature": entry[1]}')]),
    ("P38 timing values are integers, not decimal strings", [('"ledgerNowAtStart": str(now0)', '"ledgerNowAtStart": now0')]),
    ("P39 the adopted expiry is not checked for a decimal string", [("or _DEC.fullmatch(expires) is None:", "or False:")]),
    ("P40 the witness count constant is 5", [("WITNESS_COUNT = 4", "WITNESS_COUNT = 5")]),
    ("P41 the pool quorum constant is 2", [("POOL_QUORUM = 3", "POOL_QUORUM = 2")]),
    ("P42 a valid report without a sequence is not refused", [('        if "sequence" not in m:\n            raise PoolCoreError("a valid report\'s message must carry a sequence")\n', "")]),
    ("P43 the report list type is not checked", [("    if not isinstance(reports, list):\n        raise PoolCoreError(\"reports must be a list\")\n", "")]),
    ("P44 extra keys in a report are accepted", [("set(r) != _REPORT_KEYS", "not _REPORT_KEYS <= set(r)")]),
    ("P45 reporters are not restricted to consistent witnesses reporting the value", [('[str(w) for w, r in consistent.items() if canonical_message(r["message"]) == c]', '[str(w) for w, r in consistent.items()]')]),
    ("P46 a valid report's signature type is not checked", [('        if not isinstance(r["signature"], str):\n            raise PoolCoreError("a valid report\'s signature must be a string")\n', "")]),
    ("P47 the sequence may be a boolean", [("def _sequence(sequence):\n    return _int(sequence, \"sequence\")", "def _sequence(sequence):\n    return sequence if isinstance(sequence, int) else _int(sequence, \"sequence\")")]),
    # P48 (removed after run 2): 'evidence does not validate proposal_expires_at itself' is an EQUIVALENT mutant, because collection_deadline_ms validates the same value with the same
    # exception class before anything observable happens. The explicit check in evidence() stays as cheap defence in depth; no test can distinguish it.
]


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="pool-core-mutant-")
    try:
        p = os.path.join(d, "protocol")
        for sub in ("hmbc_protocol", "tests", os.path.join("f0", "vectors")):
            os.makedirs(os.path.join(p, sub), exist_ok=True)
        for rel in ("pytest.ini", os.path.join("hmbc_protocol", "__init__.py"), os.path.join("tests", "test_pool_core.py"), os.path.join("f0", "SUCCESSOR-WIRE.md"),
                    os.path.join("f0", "vectors", "pool_adoption.py"), os.path.join("f0", "vectors", "check_wire_examples.py")):
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "hmbc_protocol", "pool_core.py"), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_pool_core.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
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
