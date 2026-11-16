"""Mutation check of the durable witness store (agent 2, F task 2). Standard library only. Same method as the F0 runners: one text replacement per mutant (it must match exactly once and
change the file), run the UNCHANGED tests/test_witness_state.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or
timeout is NOT detection; the unmutated copy runs first as a control.

Usage (repository root):   python3 -B -I protocol/tools/run_state_mutants.py        (needs pytest: protocol/requirements.txt)
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
SRC = open(os.path.join(PROTO, "hmbc_protocol", "witness_state.py")).read()

M = [
    ("S1 no durable record: the digest row is never inserted", [('        con.execute("INSERT INTO digests (digest, type, domain, wsv, key, expires_at, signature, observation, sup_seq) VALUES (?,?,?,?,?,?,?,?,NULL)",\n                    (digest, *k, None if expires_at is None else str(expires_at), sig, canonical_json(obs)))\n', "")]),
    ("S2 commit AFTER the crash point of the reply (the record is written after the signature could have left): hook and COMMIT swapped", [('                self._hook("before_commit")\n                self._con.execute("COMMIT")\n            except BaseException:\n                if self._con.in_transaction:\n                    self._con.execute("ROLLBACK")\n                raise\n            self._hook("after_commit")', '                self._con.execute("COMMIT")\n                self._hook("before_commit")\n            except BaseException:\n                if self._con.in_transaction:\n                    self._con.execute("ROLLBACK")\n                raise\n            self._hook("after_commit")')]),
    ("S3 wall-clock death: the expiry predicate reads the host clock instead of the observation", [('int(obs["timestamp"]) >= max(int(r[1]) for r in live)', '__import__("time").time() >= max(int(r[1]) for r in live)')]),
    ("S4 only the EARLIEST digest has to be dead", [('int(obs["timestamp"]) >= max(int(r[1]) for r in live)', 'int(obs["timestamp"]) >= min(int(r[1]) for r in live)')]),
    ("S5 a different effect for a live key is never pinned", [('            if death is None:\n                recorded = None', '            if False:\n                recorded = None')]),
    ("S6 supersession leaves the old digests live", [('            con.execute("UPDATE digests SET sup_seq = ? WHERE type=? AND domain=? AND wsv=? AND key=? AND sup_seq IS NULL", (seq, *k))\n', "")]),
    ("S7 the tripwire never fires", [("            if reason:\n                con.execute(", "            if False:\n                con.execute(")]),
    ("S8 the fault is not persisted before the refusal", [('con.execute("INSERT INTO fault (id, body) VALUES (1, ?)", (canonical_json({"reason": reason, "previous": last, "observed": obs}),))', 'con.execute("SELECT ?", (canonical_json({"reason": reason, "previous": last, "observed": obs}),))')]),
    ("S9 a clear deletes the signing history", [('                self._con.execute("DELETE FROM fault WHERE id = 1")\n', '                self._con.execute("DELETE FROM fault WHERE id = 1")\n                self._con.execute("DELETE FROM conflict")\n                self._con.execute("DELETE FROM superseded")\n')]),
    ("S10 a clear needs no note", [('        if not isinstance(note, str) or not note.strip():', "        if False:")]),
    ("S11 the observation need not be of the target ledger", [('        if obs["chainId"] != self._chains[TARGET[type]]:', "        if False:")]),
    ("S12 record rows without the marker are tolerated", [('        if rows:\n            raise StoreError("STORE_CORRUPT", "record rows exist but the INITIALIZED marker is missing")', '        if False:\n            raise StoreError("STORE_CORRUPT", "record rows exist but the INITIALIZED marker is missing")')]),
    ("S13 the binding is not compared at open", [('    if meta["binding_v2"] != binding_v2:\n        raise StoreError("BINDING_MISMATCH", "the store is bound to another deployment")\n', "")]),
    ("S14 the owner is not compared at open", [('    if meta["owner"] != owner:\n        raise StoreError("OWNER_MISMATCH", "the store belongs to another role or key")\n', "")]),
    ("S15 the integrity check is skipped", [('            if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":\n                raise StoreError("STORE_CORRUPT", "integrity_check failed")\n', "")]),
    ("S16 the recorded value is the EARLIEST digest, not the latest-expiry one", [('latest = max(live, key=lambda r: (int(r[1]), r[0]))', 'latest = min(live, key=lambda r: (int(r[1]), r[0]))')]),
    ("S17 overtaken-decision-sequence accepts observed equal to the stateSequence", [('int(observed) > int(old_effect["stateSequence"])', 'int(observed) >= int(old_effect["stateSequence"])')]),
    ("S18 a DENY may die by grant", [('        if kind == "overtaken-decision-grant" and old_effect.get("result") != "1":\n            return None                                                  # a DENY is never dead by grant (A1-0107)\n', "")]),
    ("S19 the owner is compared before the binding (precedence swapped)", [('    if meta["binding_v2"] != binding_v2:\n        raise StoreError("BINDING_MISMATCH", "the store is bound to another deployment")\n    if meta["owner"] != owner:\n        raise StoreError("OWNER_MISMATCH", "the store belongs to another role or key")', '    if meta["owner"] != owner:\n        raise StoreError("OWNER_MISMATCH", "the store belongs to another role or key")\n    if meta["binding_v2"] != binding_v2:\n        raise StoreError("BINDING_MISMATCH", "the store is bound to another deployment")')]),
    ("S20 a faulted store still opens for signing", [('    if signing and st._faulted():', "    if False and st._faulted():")]),
    ("S21 an idempotent re-sign asks the signer again instead of returning the stored signature", [('            self._stored = stored[0]\n            return None                                      # idempotent: the STORED signature, the signer is not asked', '            self._stored = signer(digest)\n            return None')]),
    ("S22 the effect fields of V are not enforced", [('        if not isinstance(effect, dict) or set(effect) != EFFECT_FIELDS[type]:\n            raise ValueError("effect must carry exactly the fields of V for this type")\n', "")]),
    ("S23 a regression of the hash at the same number is not a fault", [('                      else "hash-changed" if obs["blockNumber"] == last["blockNumber"] and obs["blockHash"] != last["blockHash"] else None)', "                      else None)")]),
    ("S24 the directory is not made private", [("    os.chmod(directory, 0o700)\n", "")]),
    ("S25 a marker next to missing binding rows is not corrupt", [('                if has_marker:\n                    raise StoreError("STORE_CORRUPT", "the INITIALIZED marker exists but the binding rows are missing")\n', "")]),
    ("C1 the exporter refusal exits 1 instead of 3", [("        return 3\n    sys.stdout.write", "        return 1\n    sys.stdout.write")]),
    ("C2 the exporter success prints two newlines", [('    sys.stdout.write(canonical_json(doc) + "\\n")\n    return 0', '    sys.stdout.write(canonical_json(doc) + "\\n\\n")\n    return 0')]),
    ("C3 the exporter refusal line is not canonical JSON", [('sys.stderr.write(canonical_json({"code": e.code, "message": e.message, "reason": e.reason}) + "\\n")', 'sys.stderr.write(json.dumps({"code": e.code, "message": e.message, "reason": e.reason}, indent=1) + "\\n")')]),
    ("C4 a binding export without an anchor is printed anyway", [('                if view.anchor is None:\n                    raise StoreError("STORE_CORRUPT", "the binding rows carry no anchor")\n', "")]),
    ("C5 init does not persist the anchor", [('                    rows.append(("anchor", canonical_json(anchor)))', "                    pass")]),
    ("C6 the anchor shape is not checked", [("    if not ok:\n        raise ValueError(\"anchor must be", "    if False:\n        raise ValueError(\"anchor must be")]),
    ("C7 the witness index range is not enforced", [("    if not 0 <= i <= 3:\n        raise argparse.ArgumentTypeError(\"--witness-index must be 0..3\")", "    if False:\n        raise argparse.ArgumentTypeError(\"--witness-index must be 0..3\")")]),
    ("C8 the exporter always reads witness-0", [('os.path.join(ns.state_dir, f"witness-{ns.witness_index}")', 'os.path.join(ns.state_dir, "witness-0")')]),
    ("L1 the cooperative-writer lock is never released", [("        finally:\n            fcntl.flock(self._lockfd, fcntl.LOCK_UN)\n\n    @contextmanager\n    def exclusive(self):", "        finally:\n            pass\n\n    @contextmanager\n    def exclusive(self):")]),
    ("L2 the cooperative-writer lock is never taken", [("        fcntl.flock(self._lockfd, fcntl.LOCK_SH)\n        try:\n            yield", "        try:\n            yield")]),
    ("L3 the writer takes the lock exclusively instead of shared", [("        fcntl.flock(self._lockfd, fcntl.LOCK_SH)\n        try:\n            yield", "        fcntl.flock(self._lockfd, fcntl.LOCK_EX)\n        try:\n            yield")]),
    ("L4 exclusive() does not release the lock on exit", [("            finally:\n                fcntl.flock(self._lockfd, fcntl.LOCK_UN)", "            finally:\n                pass")]),
    ("L5 signing does not take the cooperative lock", [("        with self._mutex, self._writing():\n            self._con.execute(\"BEGIN IMMEDIATE\")\n            pending = None", "        with self._mutex:\n            self._con.execute(\"BEGIN IMMEDIATE\")\n            pending = None")]),
    ("L6 clear_fault does not take the cooperative lock", [("        with self._mutex, self._writing():\n            self._con.execute(\"BEGIN IMMEDIATE\")\n            try:\n                row = self._con.execute(\"SELECT body FROM fault", "        with self._mutex:\n            self._con.execute(\"BEGIN IMMEDIATE\")\n            try:\n                row = self._con.execute(\"SELECT body FROM fault")]),
    ("L7 exclusive() takes a shared lock instead of an exclusive one", [("            fcntl.flock(self._lockfd, fcntl.LOCK_EX)\n            try:\n                yield", "            fcntl.flock(self._lockfd, fcntl.LOCK_SH)\n            try:\n                yield")]),
    ("R1 the recovery of a hot rollback journal in an uninitialised directory is never attempted", [('        if not has_marker and not _recovered and (getattr(e, "sqlite_errorcode", 0) & 0xFF) == sqlite3.SQLITE_READONLY:', "        if False:")]),
    ("R2 an INITIALISED store (marker present) is also repaired by the inspection", [('        if not has_marker and not _recovered and (getattr(e, "sqlite_errorcode", 0) & 0xFF) == sqlite3.SQLITE_READONLY:', '        if not _recovered and (getattr(e, "sqlite_errorcode", 0) & 0xFF) == sqlite3.SQLITE_READONLY:')]),
]


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="state-mutant-")
    try:
        p = os.path.join(d, "protocol")
        for sub in ("hmbc_protocol", "tests", "testtools", os.path.join("f0", "vectors"), os.path.join("tests", "fixtures")):
            os.makedirs(os.path.join(p, sub), exist_ok=True)
        for rel in ("pytest.ini", os.path.join("hmbc_protocol", "__init__.py"), os.path.join("tests", "test_witness_state.py"), os.path.join("tests", "test_witness_state_cli.py"), os.path.join("tests", "test_witness_state_lock.py"), os.path.join("tests", "test_witness_state_hot_journal.py"), os.path.join("tests", "state_child.py"),
                    os.path.join("testtools", "__init__.py"), os.path.join("testtools", "state_oracle.py"), os.path.join("f0", "vectors", "d50_reference.py"),
                    os.path.join("f0", "vectors", "export_layouts_reference.py"), os.path.join("tests", "fixtures", "deployment-agent1-91add8c-v1-repaired-e.json")):
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "hmbc_protocol", "witness_state.py"), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_witness_state.py", "tests/test_witness_state_cli.py", "tests/test_witness_state_lock.py", "tests/test_witness_state_hot_journal.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
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
        print("CONTROL FAILED: the unmutated store does not pass its own tests (%s); nothing reported" % status)
        return 2
    print("control: unmutated store passes all tests")
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
