"""Mutation check of the TEST-ONLY alternate successor adapter entry testtools/faulty_adapter_v2.py (agent 2, F task 3, proposal P3 of A2-0074). Standard library only. Same method as the other runners: one text
replacement per mutant (it must match exactly once and change the file); the UNCHANGED tests run in a temporary copy of the tree that keeps the repository layout; a mutant is DETECTED only when pytest ran and
reported failures (a crash or a timeout is NOT detection); the unmutated copy runs first as a control and must pass with no skips. EQUIVALENT mutants are listed with an argument, they RUN and must SURVIVE, and
they are never counted as detected.

Usage (repository root):   python3 -B -I protocol/tools/run_faulty_adapter_v2_mutants.py
OFFLINE ONLY: the selection is tests/test_faulty_adapter_v2.py (parsing, every refusal as a real process, the exact argv, the wiring with the REAL supervisor class, the production equivalence, the static boundary).
The live behaviour (rows F-13, F-20, F-19) is tests/test_faulty_adapter_v2_live.py and is NOT mutated here: every wiring defect that reaches it is already visible to the offline tests, and a live mutant run
would need the shared live lock and several minutes per mutant. Needs pytest and the E dependencies (protocol/requirements.txt). Exit 0 only when every mutant is detected and every equivalent survives.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.abspath(os.path.join(HERE, ".."))
TARGET = "testtools/faulty_adapter_v2.py"
TESTS = "tests/test_faulty_adapter_v2.py"
SRC = open(os.path.join(PROTO, TARGET)).read()

M = [
    ("P1 the index range is 0..9", [('_INDEX = re.compile(r"[0-3]")', '_INDEX = re.compile(r"[0-9]")')]),
    ("P2 the delay bound is not enforced", [(" or int(parts[1]) > MAX_DELAY_MS:", ":")]),
    ("P3 a leading zero is a valid delay", [('_DELAY = re.compile(r"0|[1-9][0-9]{0,4}")', '_DELAY = re.compile(r"[0-9]{1,5}")')]),
    ("P4 any crash point is accepted", [("if len(parts) != 2 or parts[1] not in fw.POINTS:", "if len(parts) != 2:")]),
    ("P5 a crash with extra fields is accepted", [("if len(parts) != 2 or parts[1] not in fw.POINTS:", "if len(parts) < 2 or parts[1] not in fw.POINTS:")]),
    ("P6 the delay kind is not checked", [("if kind is not None and kind not in dw.KINDS:", "if False:")]),
    ("P7 the delay position is not checked", [("if when is not None and when not in dw.WHEN:", "if False:")]),
    ("P8 up to five delay fields are accepted", [("if not 2 <= len(parts) <= 4 or", "if not 2 <= len(parts) <= 5 or")]),
    ("P9 a repeated index is allowed", [("if len({v.index for v in variants}) != len(variants):", "if False:")]),
    ("P10 an unknown variant name becomes a zero delay", [('    raise ValueError("variant must be crash or delay")', '    return Variant(int(left), "delay", None, 0, None, None)')]),
    ("S1 abbreviated flags are accepted", [("ap = _Parser(add_help=False, allow_abbrev=False)", "ap = _Parser(add_help=False, allow_abbrev=True)")]),
    ("S2 an argparse error is swallowed", [('        raise FlagError("malformed flag")', "        return None")]),
    ("S3 a flag error is reported as a variant syntax error", [("    except FlagError:\n        return _refuse(stderr, MSG_FLAGS)\n", "")]),
    ("C1 every other index is substituted too", [("        v = table.get(index)\n", "        v = table.get(index, next(iter(table.values()), None))\n")]),
    ("C2 the production module name stays in the command", [("head, tail = default_command[:i], default_command[i + 1:]", "head, tail = default_command[:i], default_command[i:]")]),
    ("C3 the crash point is always after_commit", [('"--crash-at", v.point, *tail]', '"--crash-at", "after_commit", *tail]')]),
    ("C4 the crash variant runs the delay hook", [('"testtools.faulty_witness", "--crash-at"', '"testtools.delayed_witness", "--crash-at"')]),
    ("C5 the delay flag carries a zero", [('flags = ["--delay-ms", str(v.delay_ms)]', 'flags = ["--delay-ms", "0"]')]),
    ("C6 the only-kind flag is dropped", [('        if v.only_kind is not None:\n            flags += ["--only-kind", v.only_kind]\n', "")]),
    ("C7 the when flag is dropped", [('        if v.when is not None:\n            flags += ["--when", v.when]\n', "")]),
    ("C8 the table is keyed one off", [("{v.index: v for v in variants.values()}", "{v.index + 1: v for v in variants.values()}")]),
    ("C9 a dict argument is iterated as a list", [("if isinstance(variants, dict) else", "if False else")]),
    ("L1 the claims are parsed without the strict parser", [('data = adapter.strict_loads(raw.decode("utf-8"))', 'data = json.loads(raw.decode("utf-8"))')]),
    ("L2 the claims are not validated", [("    return cw._validated(data)", "    return data")]),
    ("L3 an unreadable claims file escapes", [('    except (OSError, UnicodeDecodeError, adapter.AdapterError):\n        raise ValueError("unreadable claims file") from None',
                                              '    except (UnicodeDecodeError, adapter.AdapterError):\n        raise ValueError("unreadable claims file") from None')]),
    ("I1 the supervisor seam is installed for every run", [("    if table:\n        original = am.build_runtime", "    if True:\n        original = am.build_runtime")]),
    ("I2 the worker is patched for every run", [("    if claims is not None:\n        am.Worker", "    if True:\n        am.Worker")]),
    ("I3 an explicit supervisor factory is overridden", [('kwargs.setdefault("supervisor_factory", factory)', 'kwargs["supervisor_factory"] = factory')]),
    ("I4 the installed factory has no command seam", [("command_for=command_for_variants(table))", "command_for=None)")]),
    ("I5 the compromised worker gets no claims", [("cw.CompromisedWorker(led, state_dir, clock, claims)", "cw.CompromisedWorker(led, state_dir, clock, [])")]),
    ("M1 a refusal exits 1", [('separators=(",", ":")) + "\\n")\n    return 2', 'separators=(",", ":")) + "\\n")\n    return 1')]),
    ("M2 a refusal goes to stdout", [('    stderr.write(json.dumps({"error": {"code": "MALFORMED", "message": message}}', '    sys.stdout.write(json.dumps({"error": {"code": "MALFORMED", "message": message}}')]),
    ("M3 an unknown worker variant is accepted", [("    if parsed.worker is not None and parsed.worker not in WORKER_VARIANTS:", "    if False:")]),
    ("M4 a worker variant without claims is accepted", [("    if parsed.worker is not None and parsed.claims is None:", "    if False:")]),
    ("M5 claims without a worker variant are ignored", [("    if parsed.worker is None and parsed.claims is not None:", "    if False:")]),
    ("M6 the TEST-ONLY check is skipped", [("        require_test_only(deployment)\n    except", "        pass\n    except")]),
    ("M7 the deployment is parsed with the lenient parser", [('deployment = adapter.strict_loads(f.read().decode("utf-8"))', 'deployment = json.loads(f.read().decode("utf-8"))')]),
    ("M8 the whole command line is handed to the production main", [("    return am.main(parsed.base, stdin=stdin, stdout=stdout, stderr=stderr)", "    return am.main(argv, stdin=stdin, stdout=stdout, stderr=stderr)")]),
    ("M9 nothing is installed", [("    install({v.index: v for v in parsed.variants}, claims)", "    pass")]),
    ("M10 the claims are not installed", [("    install({v.index: v for v in parsed.variants}, claims)", "    install({v.index: v for v in parsed.variants}, None)")]),
    ("M11 the witness variants are not installed", [("    install({v.index: v for v in parsed.variants}, claims)", "    install({}, claims)")]),
]

E = [
    ("E1 the '=' guard of parse_variant is dropped", "without an '=' the right-hand side is empty, parts == [''] and the final 'variant must be crash or delay' check refuses it with the same ValueError; every caller passes an argv string",
     [('    if not isinstance(text, str) or "=" not in text:\n        raise ValueError("not I=variant")\n', "")]),
    ("E2 UnicodeDecodeError is not listed in load_claims", "UnicodeDecodeError is a ValueError, so main's `except ValueError` around load_claims refuses it with the same MSG_CLAIMS",
     [("    except (OSError, UnicodeDecodeError, adapter.AdapterError):", "    except (OSError, adapter.AdapterError):")]),
]


def validate_anchors():
    bad = [(name, SRC.count(old)) for name, edits in M for old, _ in edits if SRC.count(old) != 1]
    bad += [(name, SRC.count(old)) for name, _why, edits in E for old, _ in edits if SRC.count(old) != 1]
    if bad:
        print("INVALID anchors (nothing was run):", bad)
    return not bad


def build_tree():
    d = tempfile.mkdtemp(prefix="fav2-mutant-")
    p = os.path.join(d, "protocol")
    for sub in ("testtools", "hmbc_protocol", "abi", "exports"):
        shutil.copytree(os.path.join(PROTO, sub), os.path.join(p, sub), ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(PROTO, "f0", "vectors"), os.path.join(p, "f0", "vectors"), ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(PROTO, "tests", "fixtures"), os.path.join(p, "tests", "fixtures"))
    for rel in ("pytest.ini",) + tuple(os.path.join("tests", n) for n in ("conftest.py", "support.py", "test_faulty_adapter_v2.py")):
        os.makedirs(os.path.dirname(os.path.join(p, rel)) or p, exist_ok=True)
        shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
    return d, p


def run_tests(p):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rs", TESTS], cwd=p, capture_output=True, text=True, timeout=300, env=env)
    except subprocess.TimeoutExpired:
        return "timeout", None
    skipped = re.search(r"(\d+) skipped", r.stdout)
    if r.returncode == 0:
        return ("pass-with-skips" if skipped else "pass"), 0
    m = re.search(r"(\d+) failed", r.stdout)
    if r.returncode == 1 and m:
        return "fail", int(m.group(1))
    return "crash", None


def with_text(p, edits):
    path = os.path.join(p, TARGET)
    text = SRC
    for old, new in edits:
        text = text.replace(old, new)
    assert text != SRC, "the mutation changed nothing"
    with open(path, "w") as f:
        f.write(text)
    try:
        return run_tests(p)
    finally:
        with open(path, "w") as f:
            f.write(SRC)


def main():
    if not validate_anchors():
        return 2
    tree, p = build_tree()
    try:
        status, _ = run_tests(p)
        if status != "pass":
            print("CONTROL FAILED: the unmutated entry does not pass its own tests without skips (%s); nothing reported" % status)
            return 2
        print("control: the unmutated entry passes all tests (no skips)")
        detected, survivors, equiv_ok = 0, [], True
        for name, edits in M:
            status, n = with_text(p, edits)
            if status == "fail":
                detected += 1
                print("DETECTED %s | failed tests: %d" % (name, n))
            else:
                survivors.append(name)
                print("NOT DETECTED %s | %s" % (name, status))
        for name, why, edits in E:
            status, _ = with_text(p, edits)
            ok = status == "pass"
            equiv_ok &= ok
            print("EQUIVALENT %s | %s | survived: %s" % (name, why[:120], ok))
        print("detected %d of %d" % (detected, len(M)))
        return 0 if not survivors and equiv_ok else 1
    finally:
        shutil.rmtree(tree, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
