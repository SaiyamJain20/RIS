"""Mutation check of the E regression pins (agent 2, Step 5). Standard library only. Same method as the other runners: one text replacement per mutant (it must match exactly once and change the file),
run the UNCHANGED tests/test_e_regression_pins.py in a temporary copy of the WHOLE protocol/ tree (the E inventory pin needs all 142 files; it is 7.7 MB), count a mutant DETECTED only when the tests ran and
failed; a crash or timeout is NOT detection; the unmutated copy runs first as a control. The historical reference is read with `git archive` from the real repository through GIT_DIR (the copy has no .git).

A mutant here is an edit that would change E behaviour or the reviewed shape of an E-listed path: the legacy worker fingerprint formula, the default worker export, the reviewed profile-3 / D-6 / --binding
changes, the E-listed adapter, and the committed default adapter export. The live half (test_e_regression_pins_live.py) needs Foundry and is NOT run here.

Usage (repository root):   python3 -B -I protocol/tools/run_e_regression_pins_mutants.py        (needs the root-lock Python with eth-account, pytest; the commit 376347d in the object store)
Exit 0 only when every mutant is detected and every claimed equivalent survives.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.abspath(os.path.join(HERE, ".."))
REPO = os.path.dirname(PROTO)

# (name, path relative to protocol/, [(old, new)])
M = [
    ("F1 the fingerprint drops the PBC RSC address", "hmbc_protocol/worker.py", [('dep["pbc"]["contracts"]["PSC"], dep["pbc"]["contracts"]["RSC"]]', 'dep["pbc"]["contracts"]["PSC"]]')]),
    ("F2 the fingerprint drops the DBC ACSC address", "hmbc_protocol/worker.py", [('dep["dbc"]["contracts"]["KSSC"], dep["dbc"]["contracts"]["ACSC"]]', 'dep["dbc"]["contracts"]["KSSC"]]')]),
    ("F3 the fingerprint JSON is not key-sorted", "hmbc_protocol/worker.py", [("sort_keys=True).encode()).hexdigest()", "sort_keys=False).encode()).hexdigest()")]),
    ("F4 the DBC slot carries the PBC chain id", "hmbc_protocol/worker.py", [('"dbc": [dep["dbc"]["chainId"]', '"dbc": [dep["pbc"]["chainId"]')]),
    ("F5 a field is ADDED to the legacy fingerprint (the D-2 hardening done in place)", "hmbc_protocol/worker.py", [('dep["pbc"]["contracts"]["PSC"], dep["pbc"]["contracts"]["RSC"]]', 'dep["pbc"]["contracts"]["PSC"], dep["pbc"]["contracts"]["RSC"], dep["pbc"]["contracts"]["TMSC"]]')]),
    ("F6 the fingerprint hash is SHA-1", "hmbc_protocol/worker.py", [("hashlib.sha256(json.dumps({", "hashlib.sha1(json.dumps({")]),
    ("L1 the default export renames its schema version", "hmbc_protocol/worker_log.py", [('"schemaVersion": "hmbc-worker-log/v0"', '"schemaVersion": "hmbc-worker-log/v1"')]),
    ("L2 the default export gains a member", "hmbc_protocol/worker_log.py", [('"adapterMode": "symbolic",', '"adapterMode": "symbolic", "extra": 1,')]),
    ("L3 the default export is indented by 2", "hmbc_protocol/worker_log.py", [("indent=1))\n    return 0", "indent=2))\n    return 0")]),
    ("L4 --binding is ON by default", "hmbc_protocol/worker_log.py", [('action="store_true"', 'action="store_false"')]),
    ("L5 events are ordered by timestamp descending", "hmbc_protocol/worker_log.py", [("from events order by id", "from events order by timestamp desc")]),
    ("L6 the raw token replaces its digest", "hmbc_protocol/worker_log.py", [('"tokenDigest": "0x" + keccak(bytes.fromhex(tok[2:])).hex()', '"tokenDigest": tok')]),
    ("L7 releases are ordered by grant id only", "hmbc_protocol/worker_log.py", [("order by created_at, grant_id", "order by grant_id")]),
    ("R1 the profile-3 recipient fix is lost (back to the historical test)", "hmbc_protocol/worker.py", [('in ("2", "3"):', '== "2":')]),
    ("R2 the profile test also accepts 4", "hmbc_protocol/worker.py", [('in ("2", "3"):', 'in ("2", "3", "4"):')]),
    ("R3 a SECOND change inside the allowed function: an unregistered recipient no longer refuses", "hmbc_protocol/worker.py", [("        if int(registered, 16) == 0:", "        if False:")]),
    ("R4 a change in a definition the plan does NOT allow (the grant expiry boundary)", "hmbc_protocol/worker.py", [('if now >= int(g["expiresAt"]):', 'if now > int(g["expiresAt"]):')]),
    ("D1 deviating_witness parses the deployment with plain json.loads again", "testtools/deviating_witness.py", [('dep = strict_loads(raw.decode("utf-8"))', 'dep = json.loads(raw.decode("utf-8"))')]),
    ("D2 deviating_witness no longer refuses a non-UTF-8 deployment", "testtools/deviating_witness.py", [('    except UnicodeDecodeError:\n        raise SystemExit("refusing: the deployment file is not valid UTF-8") from None\n', "")]),
    ("D3 the TEST-ONLY guard of deviating_witness is gone (a definition the plan does not allow)", "testtools/deviating_witness.py", [('    if "TEST-ONLY" not in str(led.deployment.get("fixture", {}).get("keyDerivation", "")):', "    if False:")]),
    ("A1 an operation status of the E-listed adapter changes (the default export no longer matches)", "hmbc_protocol/adapter.py", [('"collect_decision": {"handler": collect_decision, "status": "candidate-b-e1-not-unlocked"},', '"collect_decision": {"handler": collect_decision, "status": "implemented"},')]),
    ("A2 an E-listed adapter constant changes (a fourth inventory mismatch)", "hmbc_protocol/adapter.py", [("MAX_LINE_BYTES = 1 << 20", "MAX_LINE_BYTES = 1 << 21")]),
    ("X1 the committed default adapter export is edited", "exports/adapter.json", [('"candidateRevision": 6,', '"candidateRevision": 7,')]),
]
EQUIVALENT = []                                       # (name, path, [(old, new)], reason): must SURVIVE; none claimed


def git_dir():
    return subprocess.check_output(["git", "rev-parse", "--absolute-git-dir"], cwd=REPO, text=True).strip()


def run_in_copy(relpath, text, gitdir):
    d = tempfile.mkdtemp(prefix="e-pins-mutant-")
    try:
        p = os.path.join(d, "protocol")
        shutil.copytree(PROTO, p, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if relpath is not None:
            with open(os.path.join(p, relpath), "w") as f:
                f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", GIT_DIR=gitdir)
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_e_regression_pins.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
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


def apply(name, relpath, edits):
    src = open(os.path.join(PROTO, relpath)).read()
    text = src
    for old, new in edits:
        if text.count(old) != 1:
            print("INVALID %s | anchor matches %d times: %r" % (name, text.count(old), old[:70]))
            return None
        text = text.replace(old, new)
    if text == src:
        print("INVALID %s | the mutation changed nothing" % name)
        return None
    return text


def main():
    gd = git_dir()
    for name, relpath, edits in M:                     # every anchor is validated before anything runs
        if apply(name, relpath, edits) is None:
            return 2
    status, _ = run_in_copy(None, None, gd)
    if status != "pass":
        print("CONTROL FAILED: the unmutated tree does not pass its own pins (%s); nothing reported" % status)
        return 2
    print("control: the unmutated tree passes all pins")
    detected = 0
    for name, relpath, edits in M:
        status, n = run_in_copy(relpath, apply(name, relpath, edits), gd)
        if status == "fail":
            detected += 1
            print("DETECTED %s | failed tests: %d" % (name, n))
        else:
            print("NOT-DETECTED(%s) %s" % (status, name))
    survived = 0
    for name, relpath, edits, reason in EQUIVALENT:
        status, n = run_in_copy(relpath, apply(name, relpath, edits), gd)
        print("%s %s | %s" % ("SURVIVED-EQUIVALENT" if status == "pass" else "CLAIMED-EQUIVALENT-BUT-" + status.upper(), name, reason))
        survived += status == "pass"
    print("detected %d of %d; equivalent survivors %d of %d" % (detected, len(M), survived, len(EQUIVALENT)))
    return 0 if detected == len(M) and survived == len(EQUIVALENT) else 1


if __name__ == "__main__":
    sys.exit(main())
