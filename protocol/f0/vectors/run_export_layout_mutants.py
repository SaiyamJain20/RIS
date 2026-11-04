"""Mutation check of the export-layout reference (agent 2, F0 revision 8). Standard library only. Same method as run_pool_adoption_mutants.py / run_d50_r5_mutants.py:
one text replacement per mutant (must match exactly once and change the file), run the unchanged expectations in a temporary copy that keeps the repository layout, DETECTED only
when they ran and reported failures; a crash or timeout is NOT detection; the unmutated copy runs first as a control.

Usage (repository root):   python3 -B -I protocol/f0/vectors/run_export_layout_mutants.py > protocol/f0/evidence/export-layouts-mutants.txt
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
REF = open(os.path.join(HERE, "export_layouts_reference.py")).read()

MUTANTS = [
    ("L1 binding_v2 is not recomputed in the --binding export", [('    if doc["binding_v2"] != d50.binding_v2(doc["document"]):\n        _fail("binding_v2 is not the D50 hash of document")', "    if False:\n        _fail(\"binding_v2 is not the D50 hash of document\")")]),
    ("L2 the evidence owner may be the worker", [('_owner(doc["owner"], witness_only=True)', '_owner(doc["owner"])')]),
    ("L3 conflicts need not be sorted", [("        if i and _sort_key(conflicts[i - 1]) > _sort_key(r):", "        if False:")]),
    ("L4 a duplicate K among live conflicts is accepted", [('        if k in seen_k:\n            _fail("conflicts: duplicate K', '        if False:\n            _fail("conflicts: duplicate K')]),
    ("L5 a digest may occur in a live record twice", [('        for d in r["digests"]:\n            if d["digest"] in seen_dig:', '        for d in r["digests"]:\n            if False:')]),
    ("L6 a digest may repeat between a superseded row and the store", [('        for d in s["digests"]:\n            if d["digest"] in seen_dig:', '        for d in s["digests"]:\n            if False:')]),
    ("L7 death by expiry does not compare the timestamp", [('        if dth["kind"] == "expiry" and int(dth["observation"]["timestamp"]) < max(', '        if False and int(dth["observation"]["timestamp"]) < max(')]),
    ("L8 overtaken-decision-sequence accepts observed equal to stateSequence", [('int(dth["observed"]) <= int(s["effect"]["stateSequence"])', 'int(dth["observed"]) < int(s["effect"]["stateSequence"])')]),
    ("L9 the revision-8 rule: every superseded generation is compared with the LIVE one (A -> B -> A is refused)", [("        for a, b in zip(chain_, chain_[1:]):", "        for a, b in ((x, chain_[-1]) for x in chain_[:-1]):")]),
    ("L9b adjacent generations may have the same effect (a no-op supersession is accepted)", [('            if a["vHash"] == b["vHash"]:', "            if False:")]),
    ("L9c the live record is left out of the generation chain", [('        chain_ = rows + ([seen_k[k]] if k in seen_k else [])', "        chain_ = rows")]),
    ("L25 generation order is not checked (a later generation may be signed before the death of the one it replaced)", [('                if int(o["blockNumber"]) < int(dobs["blockNumber"]) or int(o["timestamp"]) < int(dobs["timestamp"]):', "                if False:")]),
    ("L26 overtaken-decision-grant does not require ALLOW (a DENY is accepted)", [('        if dth["kind"] == "overtaken-decision-grant" and s["effect"]["result"] != "1":', "        if False:")]),
    ("L27 the ALLOW guard is inverted (only a DENY is accepted under overtaken-decision-grant)", [('        if dth["kind"] == "overtaken-decision-grant" and s["effect"]["result"] != "1":', '        if dth["kind"] == "overtaken-decision-grant" and s["effect"]["result"] == "1":')]),
    ("L10 the monotonicity of recorded observations is not checked", [('    if doc["faulted"] is None and not log:', "    if False:")]),
    ("L11 a store with a fault log is still held to monotonicity only when faulted (log ignored)", [('    if doc["faulted"] is None and not log:', '    if doc["faulted"] is None:')]),
    ("L12 a fault reason need not match the observations", [('    if ok is not True:', "    if False:")]),
    ("L13 evidenceSha256 is not verified", [('    if doc["evidenceSha256"] != evidence_sha256(doc):', "    if False:")]),
    ("L14 vHash is not verified", [('    if r["vHash"] != hashlib.sha256(canonical_json(r["effect"]).encode("ascii")).hexdigest():', "    if False:")]),
    ("L15 observed is never carried (numeric kinds lose it)", [('(["observed"] if has_obs else [])', "[]")]),
    ("L16 a digest observation may be of the wrong ledger", [('    for r in conflicts:     # every digest observation is of the target ledger of its type\n        for d in r["digests"]:\n            if d["observation"]["chainId"] != chains[TARGET[r["type"]]]:', '    for r in conflicts:\n        for d in r["digests"]:\n            if False:')]),
    ("L17 superseded rows need not be numbered 1..n", [('        if s["seq"] != str(i + 1):', "        if False:")]),
    ("L18 the clear baseline is not checked", [('        if c["chainId"] != row["fault"]["observed"]["chainId"] or lc is None or int(c["blockNumber"]) > int(lc["blockNumber"]) or int(c["timestamp"]) > int(lc["timestamp"]):', "        if False:")]),
    ("L19 an exporter may refuse any reason", [('    if reason not in ERROR_REASONS:\n        _fail("reason: an exporter', '    if False:\n        _fail("reason: an exporter')]),
    ("L20 a receipt digest may carry expiresAt", [('        if not HAS_EXPIRY[t] and "expiresAt" in r:', "        if False:")]),
    ("L21 the key field format is not checked", [('    _rx(_KEY_RX[t], r["keyField"], what + ".keyField")\n', "")]),
    ("L22 effect.witnessSetVersion need not equal the key's version", [('    if r["effect"]["witnessSetVersion"] != r["witnessSetVersion"]:', "    if False:")]),
    ("L23 the marker need not equal the binding", [('    if m["binding_v2"] != b["binding_v2"] or m["owner"] != doc["owner"] or m["schema"] != "2":', "    if False:")]),
    ("L24 observations may omit a target chain of a recorded type", [('    if not needed <= set(last):', "    if False:")]),
]


def run_in_copy(ref_text):
    d = tempfile.mkdtemp(prefix="layout-mutant-")
    try:
        vec = os.path.join(d, "protocol", "f0", "vectors")
        fix = os.path.join(d, "protocol", "tests", "fixtures")
        os.makedirs(vec)
        os.makedirs(fix)
        with open(os.path.join(vec, "export_layouts_reference.py"), "w") as f:
            f.write(ref_text)
        for n in ("d50_reference.py", "test_export_layouts.py"):
            shutil.copy(os.path.join(HERE, n), os.path.join(vec, n))
        shutil.copy(FIXTURE, fix)
        try:
            p = subprocess.run([sys.executable, "-B", "-I", os.path.join(vec, "test_export_layouts.py")], capture_output=True, text=True, timeout=300)
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
