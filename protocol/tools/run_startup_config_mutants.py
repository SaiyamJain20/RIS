"""Mutation check of the strict startup readers (agent 2, F task 2; answer to A3-0096 and A3-0097): `hmbc_protocol/startup_config.py` and the `schema_problem` rule of `hmbc_protocol/adapter_v2.py`.
Standard library only. Same method as the other runners: one text replacement per mutant (it must match exactly once and change the file), run the UNCHANGED tests in a temporary copy that keeps the
repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or timeout is NOT detection; the unmutated copy runs first as a control. Each mutant names its TARGET file.
Tests run (test_adapter_v2_ops.py is copied only because test_adapter_v2_output.py imports it): tests/test_startup_refusals.py (the new class test), tests/test_adapter_v2_main.py and tests/test_witness_main.py (the two command lines), tests/test_adapter_v2.py and
tests/test_adapter_v2_output.py (the Context rules). A survivor is a TEST GAP unless it is listed in E with the argument why no input can tell it apart; every E entry is RUN and must survive.

Usage (repository root):   python3 -B -I protocol/tools/run_startup_config_mutants.py        (needs pytest and the E dependencies: protocol/requirements.txt)
Exit 0 only when every mutant is detected and every equivalence claim holds.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.abspath(os.path.join(HERE, ".."))
TARGETS = ("startup_config.py", "adapter_v2.py")
SRC = {t: open(os.path.join(PROTO, "hmbc_protocol", t)).read() for t in TARGETS}
TESTS = ("test_startup_refusals.py", "test_adapter_v2_main.py", "test_witness_main.py", "test_adapter_v2.py", "test_adapter_v2_output.py")
SUPPORT = ("conftest.py", "support.py", "test_witness_service.py", "test_witness_service_decision.py", "test_witness_service_governance.py", "test_witness_service_receipt.py", "test_adapter_v2_ops.py")

SC, AV = "startup_config.py", "adapter_v2.py"
M = [
    # ---- startup_config.py
    ("S1 a nested file escapes as RecursionError", SC, [("    except (ValueError, RecursionError): ", "    except ValueError: ")]),
    ("S2 a JSON failure is returned as None instead of refused", SC, [('        raise ConfigError(f"the {what} is not JSON") from None', "        return None")]),
    ("S3 a manifest number is read with plain int()", SC, [("        return wire.uint(value, bits)", "        return int(value)")]),
    ("S4 a rejected number escapes as a WireError", SC, [("    except wire.WireError:\n        raise ConfigError(", "    except KeyError:\n        raise ConfigError(")]),
    ("S5 the chainId width is narrowed to 64 bits", SC, [('chains[side]["chainId"], 256,', 'chains[side]["chainId"], 64,')]),
    ("S6 the deployBlock width is widened to 256 bits", SC, [('chains[side]["deployBlock"], 64,', 'chains[side]["deployBlock"], 256,')]),
    ("S7 only the PBC numbers are checked", SC, [('for side in ("pbc", "dbc")}\n    except (KeyError, TypeError):', 'for side in ("pbc",)}\n    except (KeyError, TypeError):')]),
    ("S8 the deployBlock is not checked", SC, [('"deployBlock": uint_text(chains[side]["deployBlock"], 64, f"{side} deployBlock")', '"deployBlock": 0')]),
    ("S9 the chainId is read with plain int()", SC, [('"chainId": uint_text(chains[side]["chainId"], 256, f"{side} chainId")', '"chainId": int(chains[side]["chainId"])')]),
    ("S10 a manifest whose chains are not objects escapes as TypeError", SC, [("    except (KeyError, TypeError):\n        raise ConfigError(\"the deployment declares no chains", "    except KeyError:\n        raise ConfigError(\"the deployment declares no chains")]),
    ("S11 a ConfigError is no longer a ValueError", SC, [("class ConfigError(ValueError):", "class ConfigError(Exception):")]),
    # ---- adapter_v2.py: schema_problem and its use by Context
    ("A1 a non-object schema is not recognised", AV, [("    if not isinstance(schema, dict) or not isinstance(schema.get(\"$defs\"), dict):", "    if not isinstance(schema.get(\"$defs\"), dict):")]),
    ("A2 a schema whose $defs is not an object is not recognised", AV, [("    if not isinstance(schema, dict) or not isinstance(schema.get(\"$defs\"), dict):", "    if not isinstance(schema, dict):")]),
    ("A3 the response types are never required", AV, [('    names = BRANCHES[revision] + (("AdapterResponse",) + tuple(RESPONSE_TYPE.values()) if responses else ())', "    names = BRANCHES[revision]")]),
    ("A4 the missing-definition test is inverted", AV, [("    missing = [n for n in names if n not in schema[\"$defs\"]]", "    missing = [n for n in names if n in schema[\"$defs\"]]")]),
    ("A5 a schema with missing definitions is accepted", AV, [('    return f"the schema does not define {missing}" if missing else None', "    return None")]),
    ("A6 Context ignores the schema problem", AV, [("            if problem is not None:\n                raise ValueError(problem)", "            if False:\n                raise ValueError(problem)")]),
    ("A7 Context always requires the response types", AV, [("responses=check_responses)", "responses=True)")]),
    ("A8 the carrier branches of v2 are required for every revision", AV, [("    names = BRANCHES[revision] + ((", '    names = BRANCHES["v2"] + ((')]),
]

# EQUIVALENT mutants: they change the file but cannot change what any test can observe; each is RUN and must SURVIVE, otherwise the claim is false.
E = []


def validate_anchors():
    bad = []
    for name, target, edits in M + [(n, t, e) for n, _w, t, e in E]:
        text = SRC[target]
        for old, new in edits:
            if text.count(old) != 1:
                bad.append((name, text.count(old), old[:60]))
            text = text.replace(old, new)
        if text == SRC[target]:
            bad.append((name, "changed nothing"))
    if bad:
        print("INVALID anchors (nothing was run):", bad)
        return False
    return True


def run_in_copy(target, text):
    d = tempfile.mkdtemp(prefix="startup-config-mutant-")
    try:
        p = os.path.join(d, "protocol")
        shutil.copytree(os.path.join(PROTO, "testtools"), os.path.join(p, "testtools"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(PROTO, "f0", "vectors"), os.path.join(p, "f0", "vectors"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(PROTO, "tests", "fixtures"), os.path.join(p, "tests", "fixtures"))
        shutil.copytree(os.path.join(PROTO, "abi"), os.path.join(p, "abi"))                  # the carried code reads the ABI manifest at import time
        shutil.copytree(os.path.join(PROTO, "hmbc_protocol"), os.path.join(p, "hmbc_protocol"), ignore=shutil.ignore_patterns("__pycache__", target))
        for rel in ("pytest.ini",) + tuple(os.path.join("tests", n) for n in SUPPORT + TESTS):
            os.makedirs(os.path.dirname(os.path.join(p, rel)) or p, exist_ok=True)
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "hmbc_protocol", target), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", *[os.path.join("tests", n) for n in TESTS]], cwd=p, capture_output=True, text=True, timeout=600, env=env)
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


def apply(target, edits):
    text = SRC[target]
    for old, new in edits:
        text = text.replace(old, new, 1)
    return text


def main():
    if not validate_anchors():
        return 2
    status, _ = run_in_copy(SC, SRC[SC])
    if status != "pass":
        print("CONTROL FAILED: the unmutated modules do not pass their own tests (%s); nothing reported" % status)
        return 2
    print("control: unmutated modules pass all tests")
    detected, survivors = 0, []
    for name, target, edits in M:
        status, n = run_in_copy(target, apply(target, edits))
        if status == "fail":
            detected += 1
            print("DETECTED %s | failed tests: %d" % (name, n))
        else:
            survivors.append(name)
            print("NOT-DETECTED(%s) %s" % (status, name))
    false_claims = 0
    for name, why, target, edits in E:
        status, n = run_in_copy(target, apply(target, edits))
        if status == "pass":
            print("SURVIVED-EQUIVALENT %s | %s" % (name, why))
        else:
            false_claims += 1
            print("EQUIVALENCE CLAIM FALSE (%s) %s: the tests DO see this change" % (status, name))
    print("detected %d of %d; equivalent survivors %d; test-gap survivors %d" % (detected, len(M), len(E) - false_claims, len(survivors)))
    return 0 if detected == len(M) and false_claims == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
