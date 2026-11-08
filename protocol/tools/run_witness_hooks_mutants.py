"""Mutation check of the TEST-ONLY witness hooks H4 (testtools/faulty_witness.py), H5 (testtools/compromised_worker.py), H6 (testtools/delayed_witness.py) and of the process-level H7 tests, which mutate the
PRODUCTION store checks of hmbc_protocol/witness_state.py in a temporary copy (agent 2, F task 3). Standard library only. Same method as the other runners: one text replacement per mutant (it must match
exactly once and change the file); the UNCHANGED tests run in a temporary copy of the tree that keeps the repository layout; a mutant is DETECTED only when pytest ran and reported failures (a crash or a
timeout is NOT detection); the unmutated tree runs first as a control for every selection. EQUIVALENT mutants are listed with an argument, they RUN and must SURVIVE, and they are never counted as detected.

Usage (repository root):
  python3 -B -I protocol/tools/run_witness_hooks_mutants.py            OFFLINE mutants only (the hooks; no chain, a few minutes)
  python3 -B -I protocol/tools/run_witness_hooks_mutants.py --live     also the H7 mutants of witness_state.py (needs Foundry 1.8.5 at ~/.local/share/hmbc-tools/foundry-1.8.5 and ledger commit 85c59f5;
                                                                      run it under the shared live lock; the temporary copy gets its own git repository that borrows this repository's objects)
Needs pytest and the E dependencies (protocol/requirements.txt). The live selections abort (exit 2) if their control run does not pass, so a missing Foundry can never be mistaken for detection.
Exit 0 only when every mutant is detected and every equivalent survives.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(PROTO, ".."))
LIVE = "--live" in sys.argv[1:]

FW, DW, CW, WS = "testtools/faulty_witness.py", "testtools/delayed_witness.py", "testtools/compromised_worker.py", "hmbc_protocol/witness_state.py"
T_FW, T_DW, T_CW, T_H7 = "tests/test_faulty_witness.py", "tests/test_delayed_witness.py", "tests/test_compromised_worker.py", "tests/test_witness_process_state_refusals.py"
OFFLINE = "not live"

# (name, target file, tests, -k expression, [(old, new), ...])
M = [
    # H4 faulty_witness
    ("F1 the hook fires at every store point", FW, T_FW, OFFLINE, [("        if p == point:\n            os._exit(CRASH_EXIT)", "        if True:\n            os._exit(CRASH_EXIT)")]),
    ("F2 the hook never fires", FW, T_FW, OFFLINE, [("        if p == point:\n            os._exit(CRASH_EXIT)", "        if False:\n            os._exit(CRASH_EXIT)")]),
    ("F3 the crash exits 0", FW, T_FW, OFFLINE, [("            os._exit(CRASH_EXIT)", "            os._exit(0)")]),
    ("F4 the crash exits 87", FW, T_FW, OFFLINE, [("CRASH_EXIT = 86", "CRASH_EXIT = 87")]),
    ("F5 the hook always names the first point", FW, T_FW, OFFLINE, [("        if p == point:\n", "        if p == POINTS[0]:\n")]),
    ("F6 neither store function carries the hook", FW, T_FW, OFFLINE,
     [('        kwargs["crash_hook"] = hook\n        return init_store(*args, **kwargs)', "        return init_store(*args, **kwargs)"),
      ('        kwargs["crash_hook"] = hook\n        return open_store(*args, **kwargs)', "        return open_store(*args, **kwargs)")]),
    ("F7 the store functions are not replaced", FW, T_FW, OFFLINE, [("    ws.init_store, ws.open_store = hooked_init_store, hooked_open_store", "    pass")]),
    ("F8 the TEST-ONLY check is dropped", FW, T_FW, OFFLINE, [("        require_test_only(deployment)", "        pass")]),
    ("F9 an unknown crash point is accepted", FW, T_FW, OFFLINE, [("    if args.crash_at not in POINTS:", "    if False:")]),
    ("F10 a duplicate-key deployment escapes as a traceback", FW, T_FW, OFFLINE, [("    except (OSError, ValueError, adapter.AdapterError) as e:", "    except (OSError, ValueError) as e:")]),
    ("F11 a missing deployment argument is not refused", FW, T_FW, OFFLINE, [("    if args.deployment is None:", "    if False:")]),
    ("F12 the deployment is not passed on to the production process", FW, T_FW, OFFLINE, [('    return witness_main.main(["--deployment", args.deployment, *rest])', "    return witness_main.main(rest)")]),
    # H6 delayed_witness
    ("D1 no delay is ever applied", DW, T_DW, OFFLINE, [("        hold = delay_ms > 0 and matches(line)", "        hold = False")]),
    ("D2 every line is delayed, parsable or not", DW, T_DW, OFFLINE, [("        hold = delay_ms > 0 and matches(line)", "        hold = delay_ms > 0")]),
    ("D3 the two hold positions are swapped", DW, T_DW, OFFLINE,
     [('        if hold and when == "before":\n            sleep(delay_ms / 1000)\n        reply = original(line, service)\n        if hold and when == "after":\n            sleep(delay_ms / 1000)',
       '        if hold and when == "after":\n            sleep(delay_ms / 1000)\n        reply = original(line, service)\n        if hold and when == "before":\n            sleep(delay_ms / 1000)')]),
    ("D4 the hold before is a hundred times too short", DW, T_DW, OFFLINE, [('        if hold and when == "before":\n            sleep(delay_ms / 1000)', '        if hold and when == "before":\n            sleep(delay_ms / 100000)')]),
    ("D5 the hold after is a hundred times too short", DW, T_DW, OFFLINE, [('        if hold and when == "after":\n            sleep(delay_ms / 1000)', '        if hold and when == "after":\n            sleep(delay_ms / 100000)')]),
    ("D6 a leading-zero delay is accepted", DW, T_DW, OFFLINE, [('_DELAY = re.compile(r"0|[1-9][0-9]{0,4}")', '_DELAY = re.compile(r"[0-9]{1,5}")')]),
    ("D7 a delay above sixty seconds is accepted", DW, T_DW, OFFLINE, [(" or int(args.delay_ms) > MAX_DELAY_MS", "")]),
    ("D8 --only-kind selects nothing", DW, T_DW, OFFLINE, [("(kind == only_kind if only_kind is not None else kind in KINDS)", "(kind in KINDS)")]),
    ("D9 the production reply is altered", DW, T_DW, OFFLINE, [("        return reply\n    witness_main.handle_line = delayed", "        return dict(reply, extra=1)\n    witness_main.handle_line = delayed")]),
    ("D10 the TEST-ONLY check is dropped", DW, T_DW, OFFLINE, [("        require_test_only(deployment)", "        pass")]),
    ("D11 an unknown hold position is accepted", DW, T_DW, OFFLINE, [("    if args.when is not None and args.when not in WHEN:", "    if False:")]),
    ("D12 an unknown kind is accepted", DW, T_DW, OFFLINE, [("    if args.only_kind is not None and args.only_kind not in KINDS:", "    if False:")]),
    ("D13 the default hold position is before", DW, T_DW, OFFLINE, [('args.when or "after")', 'args.when or "before")')]),
    ("D14 an unparsable line escapes the serve loop", DW, T_DW, OFFLINE, [("        except adapter.AdapterError:\n            return False", "        except KeyError:\n            return False")]),
    ("D15 a missing deployment argument is not refused", DW, T_DW, OFFLINE, [("    if args.deployment is None:", "    if False:")]),
    # H5 compromised_worker
    ("C1 claims are never honoured", CW, T_CW, OFFLINE, [("        c = self.claims.get(grant_id)", "        c = None")]),
    ("C2 an unclaimed grant is not released honestly", CW, T_CW, OFFLINE, [("        if c is None:\n            return super().release(grant_id, transmit)", "        if False:\n            return super().release(grant_id, transmit)")]),
    ("C3 the real ledger is not restored", CW, T_CW, OFFLINE, [("            self.led, self._forging = real, False", "            self._forging = False")]),
    ("C4 the recipient is always forged", CW, T_CW, OFFLINE, [('        return g["recipientKeyHash"] if self._forging else super()._recipient_for(g)', '        return g["recipientKeyHash"]')]),
    ("C5 the TEST-ONLY check is dropped", CW, T_CW, OFFLINE, [("        require_test_only(led.deployment)", "        pass")]),
    ("C6 a claim may carry extra or miss fields", CW, T_CW, OFFLINE, [("        if not isinstance(c, dict) or set(c) != CLAIM_FIELDS:", "        if not isinstance(c, dict):")]),
    ("C7 duplicate claims are accepted", CW, T_CW, OFFLINE, [('    if len({c["requestDigest"] for c in out}) != len(out):', "    if False:")]),
    ("C8 the forged grant is already expired", CW, T_CW, OFFLINE, [("FORGED_TTL = 30", "FORGED_TTL = 0")]),
    ("C9 the forged grant is not allowed", CW, T_CW, OFFLINE, [('"exists": True, "allowed": True,', '"exists": True, "allowed": False,')]),
    ("C10 the claimed data id is not validated", CW, T_CW, OFFLINE, [('        wire.hash32(c["dataId"])', "        pass")]),
    ("C11 the recipient key reference is not validated", CW, T_CW, OFFLINE, [('\n        keys.recipient_key_hash(c["recipientKeyRef"])', "\n        pass")]),
    ("C12 claims need not be a list", CW, T_CW, OFFLINE, [("    if not isinstance(claims, list):", "    if False:")]),
    ("C13 the claimed release is bound to the wrong recipient", CW, T_CW, OFFLINE, [('"recipientKeyHash": keys.recipient_key_hash(c["recipientKeyRef"])}', '"recipientKeyHash": keys.recipient_key_hash("keyref:user:alice")}')]),
]

# H7: mutants of the PRODUCTION store checks, detected by the process-level tests (live: a real chain, one test per mutant)
M_LIVE = [
    ("W1 a missing database behind a marker is not refused as missing", WS, T_H7, "missing_database_behind",
     [('        raise StoreError("STORE_MISSING", "the INITIALIZED marker exists but the database does not")', "        pass")]),
    ("W2 record rows without a marker are accepted", WS, T_H7, "record_rows_without_the_marker",
     [('        if rows:\n            raise StoreError("STORE_CORRUPT", "record rows exist but the INITIALIZED marker is missing")', "        if False:\n            raise StoreError(\"STORE_CORRUPT\", \"record rows exist but the INITIALIZED marker is missing\")")]),
    ("W3 a marker that disagrees with the database is accepted", WS, T_H7, "marker_that_disagrees",
     [('    if mk != {"binding_v2": meta["binding_v2"], "owner": meta["owner"], "schema": meta["schema"]} or meta["schema"] != SCHEMA:', "    if False:")]),
    ("W4 a store bound to another deployment is accepted", WS, T_H7, "another_deployment", [('    if meta["binding_v2"] != binding_v2:', "    if False:")]),
    ("W5 a store of another witness key is accepted", WS, T_H7, "another_witnesss_slot", [('    if meta["owner"] != owner:', "    if False:")]),
    ("W6 the store is not in write-ahead-log mode", WS, T_H7, "f27", [('        self._con.execute("PRAGMA journal_mode=WAL")', '        self._con.execute("PRAGMA journal_mode=DELETE")')]),
]

# EQUIVALENT mutants: they change the file but cannot change what any test can observe; each RUNS and must SURVIVE.
E = [
    ("F13 init_store does not carry the hook itself", "witness_main opens its store through init_store, which delegates to the (wrapped) open_store: the hook still reaches the store. Only a caller that opened the store through "
     "`init_store` alone with the wrapper for open_store removed could tell (that is F6, detected)", FW, T_FW, OFFLINE, [('        kwargs["crash_hook"] = hook\n        return init_store(*args, **kwargs)', "        return init_store(*args, **kwargs)")]),
    ("F14 open_store does not carry the hook itself", "every store in this process is created or opened through init_store (which injects the hook and passes it on to open_store); no process path calls open_store alone",
     FW, T_FW, OFFLINE, [('        kwargs["crash_hook"] = hook\n        return open_store(*args, **kwargs)', "        return open_store(*args, **kwargs)")]),
]


def read(rel):
    with open(os.path.join(PROTO, rel)) as f:
        return f.read()


def validate_anchors(items):
    bad = []
    for name, target, _t, _k, edits in items:
        src = read(target)
        for old, _new in edits:
            if src.count(old) != 1:
                bad.append((name, src.count(old), old[:60]))
    if bad:
        print("INVALID anchors (nothing was run):", bad)
    return not bad


def build_tree():
    d = tempfile.mkdtemp(prefix="hooks-mutant-")
    p = os.path.join(d, "protocol")
    for sub in ("testtools", "hmbc_protocol", "abi"):
        shutil.copytree(os.path.join(PROTO, sub), os.path.join(p, sub), ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(PROTO, "f0", "vectors"), os.path.join(p, "f0", "vectors"), ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(PROTO, "tests", "fixtures"), os.path.join(p, "tests", "fixtures"))
    os.makedirs(os.path.join(p, "exports"))
    shutil.copytree(os.path.join(PROTO, "exports"), os.path.join(p, "exports"), dirs_exist_ok=True)
    for rel in ("pytest.ini",) + tuple(os.path.join("tests", n) for n in ("conftest.py", "support.py", "ledger_setup.py", "test_witness_state.py", "test_rpc_binding_view_live.py", "test_faulty_witness.py",
                                                                          "test_delayed_witness.py", "test_compromised_worker.py", "test_witness_process_state_refusals.py")):
        os.makedirs(os.path.dirname(os.path.join(p, rel)) or p, exist_ok=True)
        shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
    if LIVE:                                            # the live fixtures run `git archive <ledger commit>` in the repository that contains the tests: give the copy one that borrows our objects
        subprocess.run(["git", "init", "-q", d], check=True)
    return d, p


def git_objects():
    out = subprocess.run(["git", "rev-parse", "--git-path", "objects"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    return out if os.path.isabs(out) else os.path.join(ROOT, out)


def run_tests(tree_p, tests, k, live):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    if live:
        env["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = git_objects()
    try:
        cmd = [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rs", tests] + (["-k", k] if k else [])
        r = subprocess.run(cmd, cwd=tree_p, capture_output=True, text=True, timeout=900 if live else 300, env=env)
    except subprocess.TimeoutExpired:
        return "timeout", None
    skipped = re.search(r"(\d+) skipped", r.stdout)
    if r.returncode == 0:
        return ("pass-with-skips" if skipped else "pass"), 0
    m = re.search(r"(\d+) failed", r.stdout)
    if r.returncode == 1 and m:
        return "fail", int(m.group(1))
    return "crash", None


def main():
    items = M + (M_LIVE if LIVE else [])
    if not validate_anchors(items) or not validate_anchors([(n, t, tt, k, e) for n, _w, t, tt, k, e in E]):
        return 2
    tree, p = build_tree()
    try:
        selections = sorted({(tests, k, False) for _n, _t, tests, k, _e in items if k == OFFLINE} | {(tests, k, False) for _n, _w, _t, tests, k, _e in E}
                            | {(tests, "", True) for _n, _t, tests, k, _e in items if k != OFFLINE})
        for tests, k, live in selections:
            status, _ = run_tests(p, tests, k, live)
            if status != "pass":
                print("CONTROL FAILED: %s -k %r does not pass unmutated (%s); nothing reported" % (tests, k, status))
                return 2
        print("control: every selection passes unmutated (no skips)")
        detected, survivors, equiv_ok = 0, [], True
        for name, target, tests, k, edits in items:
            path, src = os.path.join(p, target), read(target)
            text = src
            for old, new in edits:
                text = text.replace(old, new)
            assert text != src
            with open(path, "w") as f:
                f.write(text)
            try:
                status, nfail = run_tests(p, tests, k, k != OFFLINE)
            finally:
                with open(path, "w") as f:
                    f.write(src)
            if status == "fail":
                detected += 1
                print("DETECTED %s | failed tests: %d" % (name, nfail))
            else:
                survivors.append(name)
                print("NOT DETECTED %s | %s" % (name, status))
        for name, why, target, tests, k, edits in E:
            path, src = os.path.join(p, target), read(target)
            text = src
            for old, new in edits:
                text = text.replace(old, new)
            with open(path, "w") as f:
                f.write(text)
            try:
                status, _ = run_tests(p, tests, k, False)
            finally:
                with open(path, "w") as f:
                    f.write(src)
            ok = status == "pass"
            equiv_ok &= ok
            print("EQUIVALENT %s | %s | survived: %s" % (name, why[:110], ok))
        print("detected %d of %d" % (detected, len(items)))
        return 0 if not survivors and equiv_ok else 1
    finally:
        shutil.rmtree(tree, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
