"""Mutation check of the successor adapter handlers the successor adapter command line (agent 2, F task 2 slice 10a). Standard library only. Same method as the other runners: one text replacement per mutant (it must match exactly once
and change the file), run the UNCHANGED tests/test_adapter_v2_main.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or
timeout is NOT detection; the unmutated copy runs first as a control. the carried adapter.py, wire.py, witness_service.py, witness_pool.py and witness_pool_driver.py are NOT mutated here (their own runners do that).

Usage (repository root):   python3 -B -I protocol/tools/run_adapter_v2_main_mutants.py        (needs pytest and the E dependencies: protocol/requirements.txt)
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
SRC = open(os.path.join(PROTO, "hmbc_protocol", "adapter_v2_main.py")).read()

M = [
    ("C1 the schema hash is not checked", [("    if hashlib.sha256(raw).hexdigest() != pinned:", "    if False:")]),
    ("C2 the deployment is parsed with plain json.loads", [("m = _e.strict_loads(raw.decode(\"utf-8\"))", "m = json.loads(raw.decode(\"utf-8\"))")]),
    ("C3 a non-UTF-8 deployment escapes as a traceback", [("    except UnicodeDecodeError:\n        raise Refusal(\"MALFORMED\", \"the deployment file is not valid UTF-8\") from None\n", "")]),
    ("C4 a parse error of the deployment escapes", [("    except _e.AdapterError as e:\n        raise Refusal(\"MALFORMED\", f\"the deployment file: {e.message}\") from None\n", "")]),
    ("C5 an unreadable file escapes as a traceback", [("    except OSError:\n        raise Refusal(\"MALFORMED\", f\"the {what} file cannot be read\") from None", "    except OSError:\n        raise")]),
    ("C6 a schema that is not JSON escapes", [("    except ValueError:\n        raise Refusal(\"MALFORMED\", \"the schema file is not JSON\") from None", "    except TypeError:\n        raise Refusal(\"MALFORMED\", \"the schema file is not JSON\") from None")]),
    ("C7 a state path that is not a directory is accepted", [("        if not os.path.isdir(path):\n            raise Refusal(\"MALFORMED\", \"the state path is not a directory\")\n", "")]),
    ("C8 a state directory open to group or other is accepted", [("        if stat.S_IMODE(os.stat(path).st_mode) & 0o077:", "        if False:")]),
    ("C9 a URL or ABI problem escapes as a traceback", [("    except (KeyError, TypeError, ValueError, AttributeError, ChainError) as e:", "    except (KeyError, TypeError, ValueError, AttributeError) as e:")]),
    ("C10 a stage refusal maps to MALFORMED", [('bo.OPEN_REASON_CODE.get(e.reason, "ADAPTER_UNAVAILABLE")', '"MALFORMED"')]),
    ("C11 the stage reason is dropped", [("        if e.reason:\n            err[\"reason\"] = e.reason", "        if False:\n            err[\"reason\"] = e.reason")]),
    ("C12 a refused startup exits 1", [("        return 2\n    return av2.serve", "        return 1\n    return av2.serve")]),
    ("C13 the refusal goes to stdout", [("        stderr.write(json.dumps({\"error\": err}", "        stdout.write(json.dumps({\"error\": err}")]),
    ("C14 a startup ValueError escapes", [("    except ValueError as e:\n        raise Refusal(\"MALFORMED\", f\"startup refused: {e}\") from None", "    except TypeError as e:\n        raise Refusal(\"MALFORMED\", f\"startup refused: {e}\") from None")]),
    ("C15 the schema file is read before it is hashed, from the wrong path", [("    raw = _read(path, \"schema\")", "    raw = _read(path + \"x\", \"schema\")")]),
    ("C16 the explicit revision is not passed on", [("schema_revision=args.schema_revision", 'schema_revision="v2"')]),
    ("C17 the revision may be defaulted", [('ap.add_argument("--schema-revision", required=True,', 'ap.add_argument("--schema-revision", required=False, default="v2",')]),
    ("C18 the state directory may be defaulted", [('ap.add_argument("--state-dir", required=True,', 'ap.add_argument("--state-dir", required=False, default="/nonexistent-state",')]),
    ("C19 the abi directory may be defaulted", [('ap.add_argument("--abi-dir", required=True,', 'ap.add_argument("--abi-dir", required=False, default=".",')]),
    ("C20 the schema hash may be defaulted", [('ap.add_argument("--schema-sha256", required=True,', 'ap.add_argument("--schema-sha256", required=False, default="0" * 64,')]),
]


def validate_anchors():
    bad = [(name, SRC.count(old)) for name, edits in M for old, _ in edits if SRC.count(old) != 1]
    if bad:
        print("INVALID anchors (nothing was run):", bad)
        return False
    return True


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="cli-mutant-")
    try:
        p = os.path.join(d, "protocol")
        shutil.copytree(os.path.join(PROTO, "testtools"), os.path.join(p, "testtools"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(PROTO, "f0", "vectors"), os.path.join(p, "f0", "vectors"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(PROTO, "tests", "fixtures"), os.path.join(p, "tests", "fixtures"))
        shutil.copytree(os.path.join(PROTO, "abi"), os.path.join(p, "abi"))                  # the carried code reads the ABI manifest at import time
        shutil.copytree(os.path.join(PROTO, "hmbc_protocol"), os.path.join(p, "hmbc_protocol"), ignore=shutil.ignore_patterns("__pycache__", "adapter_v2_main.py"))
        for rel in ("pytest.ini",) + tuple(os.path.join("tests", n) for n in ("conftest.py", "support.py", "test_witness_service.py", "test_witness_service_decision.py", "test_witness_service_governance.py",
                                                                              "test_witness_service_receipt.py", "test_adapter_v2_main.py")):
            os.makedirs(os.path.dirname(os.path.join(p, rel)) or p, exist_ok=True)
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "hmbc_protocol", "adapter_v2_main.py"), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_adapter_v2_main.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
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
    if not validate_anchors():
        return 2
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
