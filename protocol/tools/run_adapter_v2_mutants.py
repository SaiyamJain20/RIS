"""Mutation check of the successor adapter front-end (agent 2, F task 2 slice 6a). Standard library only. Same method as the other runners: one text replacement per mutant (it must match exactly once
and change the file), run the UNCHANGED tests/test_adapter_v2.py and tests/test_adapter_v2_output.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or
timeout is NOT detection; the unmutated copy runs first as a control. the carried adapter.py, wire.py and witness_service.py are NOT mutated here.

Usage (repository root):   python3 -B -I protocol/tools/run_adapter_v2_mutants.py        (needs pytest and the E dependencies: protocol/requirements.txt)
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
SRC = open(os.path.join(PROTO, "hmbc_protocol", "adapter_v2.py")).read()

# EQUIVALENT MUTANT dropped (run 2: 58 of 59): A59, a non-string judged by the format instead of the type. wire.uint and wire.signature already refuse a non-string, and every published type that carries
# one of these formats also has `type: string`, so the guard and the type keyword refuse the same values.
M = [
    ("A1 the line limit is 2 MiB", [("MAX_LINE_BYTES = 1 << 20", "MAX_LINE_BYTES = 1 << 21")]),
    ("A2 extra request members are accepted", [("or set(obj) != REQUEST_FIELDS:", "or not REQUEST_FIELDS <= set(obj):")]),
    ("A3 the request schemaVersion is not checked", [('        if obj["schemaVersion"] != SCHEMA_VERSION:', "        if False:")]),
    ("A4 the pinned-manifest equality is not enforced", [('        if obj["deploymentManifest"] != ctx.manifest:', "        if False:")]),
    ("A5 the structural minimum of the request manifest is not checked", [('            _e._deployment(obj["deploymentManifest"])\n        except _e.AdapterError as e:\n            raise _malformed(e.message) from None\n        if obj', '            pass\n        except _e.AdapterError as e:\n            raise _malformed(e.message) from None\n        if obj')]),
    ("A6 the input is not validated before dispatch", [('        validate_input(op, obj["input"])\n', "")]),
    ("A7 rotate_epoch may be enabled by a handler", [('        if op == "rotate_epoch":\n            raise OperationError("NOT_IMPLEMENTED_IN_PHASE"', '        if False:\n            raise OperationError("NOT_IMPLEMENTED_IN_PHASE"')]),
    ("A8 a non-object handler result is passed through", [("        if not isinstance(result, dict):\n            return _generic()", "        if False:\n            return _generic()")]),
    ("A9 the generic failure message differs", [('GENERIC_FAILURE = ("ADAPTER_UNAVAILABLE", "internal adapter failure")', 'GENERIC_FAILURE = ("ADAPTER_UNAVAILABLE", "internal adapter failure!")')]),
    ("A10 an operation error becomes a generic failure", [("    except OperationError as e:\n        return ctx.checked(known, _response(error=e))\n", "")]),
    ("A11 the reason is not put into the response", [('    if error.reason is not None:\n        err["reason"] = error.reason\n', "")]),
    ("A12 the collection is not put into the response", [('    if error.collection is not None:\n        err["collection"] = error.collection\n', "")]),
    ("A13 the recorded value is not put into the response", [('    if error.recorded is not None:\n        err["recorded"] = error.recorded\n', "")]),
    ("A14 an unknown error code is accepted", [("        if code not in CODES:", "        if False:")]),
    ("A15 an empty error message is accepted", [("        if not isinstance(message, str) or not message:", "        if False:")]),
    ("A16 a reason of another code is accepted", [(" or REASON_CODE[reason] != code):", "):")]),
    ("A17 recorded is accepted without CONFLICT_PINNED", [('        if recorded is not None and reason != "CONFLICT_PINNED":', "        if False:")]),
    ("A18 a collection is accepted without QUORUM_UNAVAILABLE", [('        if collection is not None and reason != "QUORUM_UNAVAILABLE":', "        if False:")]),
    ("A19 PROFILE_MISMATCH maps to WRONG_DESTINATION", [('"PROFILE_MISMATCH": "WRONG_PROFILE"', '"PROFILE_MISMATCH": "WRONG_DESTINATION"')]),
    ("A20 a code is missing from the closed list", [('"REVOKED", "MALFORMED", "WRONG_PROFILE")', '"REVOKED", "MALFORMED")')]),
    ("A21 any schema revision string is accepted", [("        if schema_revision not in MARKER or not isinstance(schema_revision, str):", "        if False:")]),
    ("A22 a non-object pinned manifest is accepted", [("        if not isinstance(manifest, dict):\n            raise ValueError(\"the pinned manifest must be an object\")", "        if False:\n            raise ValueError(\"the pinned manifest must be an object\")")]),
    ("A23 an unknown carrier marker can be pinned", [("        if marker not in MARKER.values():", "        if False:")]),
    ("A24 the v2.1 marker is allowed under revision v2", [('        if marker == MARKER["v2.1"] and schema_revision != "v2.1":', "        if False:")]),
    ("A25 the pinned manifest need not bind a request", [("            _e._deployment(manifest)\n        except _e.AdapterError as e:\n            raise ValueError", "            pass\n        except _e.AdapterError as e:\n            raise ValueError")]),
    ("A26 the supplied schema is not used", [("            self._validate_against(schema, manifest, schema_revision)\n", "            pass\n")]),
    ("A28 the handlers are not validated", [('        if not isinstance(handlers, dict) or not set(handlers) <= set(OPERATIONS) or not all(callable(h) for h in handlers.values()):', "        if False:")]),
    ("A29 the pinned manifest is aliased, not copied", [("self.manifest, self.schema_revision, self.handlers = copy.deepcopy(manifest),", "self.manifest, self.schema_revision, self.handlers = manifest,")]),
    ("A30 the output is not compact", [('stdout.write(json.dumps(resp, separators=(",", ":")) + "\\n")', 'stdout.write(json.dumps(resp) + "\\n")')]),
    ("A31 invalid UTF-8 is replaced instead of refused", [('            text = chunk.decode("utf-8")', '            text = chunk.decode("utf-8", "replace")')]),
    ("A32 a blank line is not recognised as empty", [("        if not text.strip():", "        if not text:")]),
    ("A33 an oversized line is not discarded", [('            while chunk and not chunk.endswith(b"\\n"):                # discard', '            while False:                # discard')]),
    ("A34 governance accepts another witnessSetVersion", [('    if core["witnessSetVersion"] != "2":', "    if False:")]),
    ("A35 the selector accepts index 4", [('v not in ("0", "1", "2", "3")', 'v not in ("0", "1", "2", "3", "4")')]),
    ("A36 the set version accepts 3", [('v not in ("1", "2"):\n        raise wire.WireError("MALFORMED: witnessSetVersion', 'v not in ("1", "2", "3"):\n        raise wire.WireError("MALFORMED: witnessSetVersion')]),
    ("A37 finish_decryption takes the v1 release result", [("response=_release_result_v2, userKeyRef", "response=wire.release_result, userKeyRef")]),
    ("A38 the v2 release result accepts schemaVersion v1", [('schemaVersion=wire._e_const("v2"), adapterMode=wire._e_const("symbolic"), requestDigest', 'schemaVersion=wire._e_const("v1"), adapterMode=wire._e_const("symbolic"), requestDigest')]),
    ("A39 every optional member becomes required", [("return _closed(v, {**core, **present}, what)", "return _closed(v, {**core, **optionals}, what)")]),
    ("A40 a witnessIndex is accepted on governance without being checked", [('    if "witnessIndex" in v:\n        _selector(v["witnessIndex"])\n', "")]),
    ("A41 collect_checkpoint requires a request digest", [('return _with_optionals(v, {}, dict(witnessSetVersion=_version, witnessIndex=_selector), "CollectCheckpointInput")', 'return _with_optionals(v, dict(requestDigest=wire.hash32), dict(witnessSetVersion=_version, witnessIndex=_selector), "CollectCheckpointInput")')]),
    ("A42 the attest_grant input accepts a witnessSetVersion", [('dict(witnessIndex=_selector), "AttestGrantInput")', 'dict(witnessIndex=_selector, witnessSetVersion=_version), "AttestGrantInput")')]),
    ("A44 a response is never checked", [("        if self._response_validators is None:\n            return response\n        try:", "        if True:\n            return response\n        try:")]),
    ("A45 an invalid response is emitted anyway", [("            pass\n        return _generic()\n\n    @staticmethod\n    def _validate_against", "            pass\n        return response\n\n    @staticmethod\n    def _validate_against")]),
    ("A46 a validator that cannot decide lets the response through", [("        except Exception:  # noqa: BLE001 - a validator that cannot decide (for example a pathological value) is a refusal to emit\n            pass", "        except Exception:  # noqa: BLE001\n            return response")]),
    ("A47 every response is checked against the generic type only", [('RESPONSE_TYPE.get(op, "AdapterResponse")', '"AdapterResponse"')]),
    ("A48 the operation is never recorded for the check", [("        known = op\n", "")]),
    ("A49 the published formats are not enforced", [("format_checker=formats)", "format_checker=None)")]),
    ("A51 the check_responses flag is ignored", [("if schema is not None and check_responses else None", "if schema is not None else None")]),
    ("A52 check_responses may be any value", [("        if not isinstance(check_responses, bool):\n            raise ValueError(\"check_responses must be a boolean\")\n", "")]),
    ("A53 the generic type is not built", [('names = ("AdapterResponse",) + tuple(RESPONSE_TYPE.values())', "names = tuple(RESPONSE_TYPE.values())")]),
    ("A54 the response of a rotate_epoch refusal is not checked against its own type", [('"rotate_epoch": "RotateEpochResponse"}', '"rotate_epoch": "AdapterResponse"}')]),
    ("A55 the published custom formats are not registered", [("        formats = published_format_checker()\n", "        formats = jsonschema.FormatChecker()\n")]),
    ("A56 uint64 is checked at 256 bits", [('("uint64", 64)', '("uint64", 256)')]),
    ("A57 the width check accepts anything", [("                wire.uint(v, bits)\n", "                pass\n")]),
    ("A58 canonical-signature is not enforced", [("            wire.signature(v)\n", "            pass\n")]),
    ("A43 a bare TypeError from a validator escapes", [("    except (wire.WireError, TypeError, KeyError, ValueError, AttributeError) as e:", "    except wire.WireError as e:")]),
]


# Equivalent mutants: each is RUN and must SURVIVE; if a test starts to notice one, the claim below is false and the runner exits 1.
E = [
    ("A27 a schema without the revision's carrier branch is accepted", "Context.__init__ asks schema_problem() first, which already refuses a schema without the revision's carrier branches; _validate_against is called ONLY from there, so its own missing-branch check is an unreachable duplicate kept as defence in depth (made equivalent by the schema_problem refactor, A2-0073 follow-up)", [("        if missing:\n            raise ValueError(f\"the supplied schema does not define {missing}: it cannot serve revision", "        if False:\n            raise ValueError(f\"the supplied schema does not define {missing}: it cannot serve revision")]),
    ("A50 a schema without response types is accepted", 'Context.__init__ asks schema_problem(responses=check_responses) first, which already refuses a schema without the response types; _build_response_validators is called only from there under the same condition, so its own missing-definition check is an unreachable duplicate kept as defence in depth', [("        if missing:\n            raise ValueError(f\"the supplied schema does not define {missing}: it cannot validate responses\")", "        if False:\n            pass")]),
]

def validate_anchors():
    bad = [(name, SRC.count(old)) for name, edits in M for old, _ in edits if SRC.count(old) != 1]
    bad += [(name, SRC.count(old)) for name, _why, edits in E for old, _ in edits if SRC.count(old) != 1]
    if bad:
        print("INVALID anchors (nothing was run):", bad)
        return False
    return True


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="adv2-mutant-")
    try:
        p = os.path.join(d, "protocol")
        for sub in ("hmbc_protocol", "tests", "testtools", os.path.join("f0", "vectors")):
            os.makedirs(os.path.join(p, sub), exist_ok=True)
        tt = os.path.join(PROTO, "testtools")
        for name in os.listdir(tt):
            if name.endswith(".py"):
                shutil.copy(os.path.join(tt, name), os.path.join(p, "testtools", name))
        pkg = os.path.join(PROTO, "hmbc_protocol")
        for name in os.listdir(pkg):
            if name.endswith(".py") and name != "adapter_v2.py":
                shutil.copy(os.path.join(pkg, name), os.path.join(p, "hmbc_protocol", name))
        fx = os.path.join(PROTO, "tests", "fixtures")
        os.makedirs(os.path.join(p, "tests", "fixtures"), exist_ok=True)
        for name in os.listdir(fx):
            if name.startswith(("agent1-85c59f5", "agent3-")) and os.path.isfile(os.path.join(fx, name)):     # agent1-85c59f5-abi became a DIRECTORY fixture; copying it crashed the runner
                shutil.copy(os.path.join(fx, name), os.path.join(p, "tests", "fixtures", name))
        for rel in ("pytest.ini", os.path.join("tests", "test_adapter_v2.py"), os.path.join("tests", "test_adapter_v2_output.py"), os.path.join("tests", "test_adapter_v2_ops.py")):
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "hmbc_protocol", "adapter_v2.py"), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_adapter_v2.py", "tests/test_adapter_v2_output.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
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
    false_claims = 0
    for name, why, edits in E:
        text = SRC
        for old, new in edits:
            text = text.replace(old, new)
        status, n = run_in_copy(text)
        if status == "pass":
            print("SURVIVED-EQUIVALENT %s | %s" % (name, why))
        else:
            false_claims += 1
            print("FALSE-EQUIVALENT-CLAIM (%s) %s: the tests notice it, so it is not equivalent" % (status, name))
    print("detected %d of %d; equivalent survivors %d (claims checked by running them)" % (detected, len(M), len(E) - false_claims))
    return 0 if detected == len(M) and false_claims == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
