"""Mutation check of the successor adapter handlers the witness process (agent 2, F task 3 slice 11a). Standard library only. Same method as the other runners: one text replacement per mutant (it must match exactly once
and change the file), run the UNCHANGED tests/test_witness_main.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or
timeout is NOT detection; the unmutated copy runs first as a control. the carried adapter.py, wire.py, witness_service.py, witness_pool.py and witness_pool_driver.py are NOT mutated here (their own runners do that).

Usage (repository root):   python3 -B -I protocol/tools/run_witness_main_mutants.py        (needs pytest and the E dependencies: protocol/requirements.txt)
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
SRC = open(os.path.join(PROTO, "hmbc_protocol", "witness_main.py")).read()

M = [
    ("H1 a request is parsed with plain json.loads", [("obj = _e.strict_loads(line)", "obj = json.loads(line)")]),
    ("H2 a request may carry extra members", [("set(obj) != REQUEST_FIELDS", "not REQUEST_FIELDS <= set(obj)")]),
    ("H3 the schema version is not checked", [('or obj["schemaVersion"] != SCHEMA', "")]),
    ("H4 a boolean id is accepted", [("    return isinstance(v, int) and not isinstance(v, bool)", "    return isinstance(v, int)")]),
    ("H5 a negative id is accepted", [('and obj["id"] >= 0:', "and True:")]),
    ("H6 any round is accepted", [('or not _is_int(obj["round"]) or obj["round"] not in (1, 2)', "")]),
    ("H7 any kind is accepted", [('or not isinstance(obj["kind"], str) or obj["kind"] not in KINDS', "")]),
    ("H8 a message that is not an object is accepted", [(' or obj["kind"] not in KINDS or not isinstance(obj["message"], dict)):', ' or obj["kind"] not in KINDS):')]),
    ("H9 a refusal is not mapped", [("        except svc.WitnessRefusal as e:", "        except KeyError as e:")]),
    ("H10 the recorded value is dropped", [('"recorded": e.recorded}', '"recorded": None}')]),
    ("H11 the reason is dropped", [('"reason": e.reason, "recorded"', '"reason": None, "recorded"')]),
    ("H12 every refusal is MALFORMED", [('"code": e.code, "reason"', '"code": "MALFORMED", "reason"')]),
    ("H13 an unexpected exception escapes", [("        return _answer(ident, dict(GENERIC))\n\n\ndef serve", "        raise\n\n\ndef serve")]),
    ("H14 the signed message is not echoed", [('"message": dict(obj["message"]), "signature"', '"message": {}, "signature"')]),
    ("H15 decision requests go to the receipt signer", [('"decision": "sign_decision"', '"decision": "sign_receipt"')]),
    ("H16 the id of a refused well-formed envelope is lost", [("        return _answer(ident, dict(MALFORMED))\n        message = dict", "        return _answer(None, dict(MALFORMED))\n        message = dict")]),
    ("H17 an oversized line is not skipped", [("        if not chunk.endswith(b\"\\n\") and len(chunk) > MAX_LINE_BYTES:", "        if False:")]),
    ("H18 invalid UTF-8 kills the server", [("        except UnicodeDecodeError:\n            emit(_answer(None, dict(MALFORMED)))\n            continue", "        except TypeError:\n            emit(_answer(None, dict(MALFORMED)))\n            continue")]),
    ("H19 a key derivation that is not TEST-ONLY is accepted", [('if not isinstance(derivation, str) or not derivation.startswith("TEST-ONLY"):', "if False:")]),
    ("H20 the key address is not compared with the witness set", [("    if index >= len(witnesses) or witnesses[index] != address:", "    if False:")]),
    ("H21 an index beyond the witness set is accepted", [("index >= len(witnesses) or witnesses[index] != address", "witnesses[index] != address")]),
    ("H22 an index may have a leading zero or sign", [('_INDEX = re.compile(r"[0-3]")', '_INDEX = re.compile(r"[-+0-9]+")')]),
    ("H23 the allow-list action is not checked", [('action not in ("1", "2", "3") or ', "")]),
    ("H24 the allow-list root is not checked", [("not isinstance(root, str) or _ADDR.fullmatch(root) is None or ", "")]),
    ("H25 the allow-list admins are not checked", [(" or not isinstance(admins, list) or not all(isinstance(a, str) and _ADDR.fullmatch(a) for a in admins)", "")]),
    ("H26 a malformed allow-list escapes", [("    except (ValueError, TypeError):\n        raise am.Refusal(\"MALFORMED\", \"the allow-governance", "    except KeyError:\n        raise am.Refusal(\"MALFORMED\", \"the allow-governance")]),
    ("H27 a stage refusal maps to MALFORMED", [('bo.OPEN_REASON_CODE.get(e.reason, "ADAPTER_UNAVAILABLE")', '"MALFORMED"')]),
    ("H28 a refused startup exits 1", [("        return 2\n    return serve", "        return 1\n    return serve")]),
    ("H29 the refusal goes to stdout", [("        stderr.write(json.dumps({\"error\": err}", "        stdout.write(json.dumps({\"error\": err}")]),
    ("H30 a missing deployment fixture escapes", [("    except (KeyError, TypeError):\n        raise am.Refusal(\"MALFORMED\", \"the deployment declares no key derivation", "    except KeyError:\n        raise am.Refusal(\"MALFORMED\", \"the deployment declares no key derivation")]),
]


def validate_anchors():
    bad = [(name, SRC.count(old)) for name, edits in M for old, _ in edits if SRC.count(old) != 1]
    if bad:
        print("INVALID anchors (nothing was run):", bad)
        return False
    return True


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="wmain-mutant-")
    try:
        p = os.path.join(d, "protocol")
        shutil.copytree(os.path.join(PROTO, "testtools"), os.path.join(p, "testtools"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(PROTO, "f0", "vectors"), os.path.join(p, "f0", "vectors"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(PROTO, "tests", "fixtures"), os.path.join(p, "tests", "fixtures"))
        shutil.copytree(os.path.join(PROTO, "abi"), os.path.join(p, "abi"))                  # the carried code reads the ABI manifest at import time
        shutil.copytree(os.path.join(PROTO, "hmbc_protocol"), os.path.join(p, "hmbc_protocol"), ignore=shutil.ignore_patterns("__pycache__", "witness_main.py"))
        for rel in ("pytest.ini",) + tuple(os.path.join("tests", n) for n in ("conftest.py", "support.py", "test_witness_service.py", "test_witness_service_decision.py", "test_witness_service_governance.py",
                                                                              "test_witness_service_receipt.py", "test_witness_main.py")):
            os.makedirs(os.path.dirname(os.path.join(p, rel)) or p, exist_ok=True)
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "hmbc_protocol", "witness_main.py"), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_witness_main.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
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
