"""Mutation check of the successor adapter handlers part 1 (agent 2, F task 2 slice 6b-1). Standard library only. Same method as the other runners: one text replacement per mutant (it must match exactly once
and change the file), run the UNCHANGED tests/test_adapter_v2_ops.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or
timeout is NOT detection; the unmutated copy runs first as a control. the carried adapter.py, wire.py and witness_service.py are NOT mutated here.

Usage (repository root):   python3 -B -I protocol/tools/run_adapter_v2_ops_mutants.py        (needs pytest and the E dependencies: protocol/requirements.txt)
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
SRC = open(os.path.join(PROTO, "hmbc_protocol", "adapter_v2_ops.py")).read()

M = [
    ("H1 the result keeps schemaVersion v1", [('    return dict(result, schemaVersion="v2")', '    return dict(result, schemaVersion="v1")')]),
    ("H2 the worker result is not checked before the relabel", [("    validator(result)\n", "")]),
    ("H3 finish_decryption hands the worker the v2 response", [('        response = dict(inp["response"], schemaVersion="v1")', '        response = inp["response"]')]),
    ("H4 a worker error escapes the mapping", [("    except (_e.AdapterError, WorkerError) as e:", "    except _e.AdapterError as e:")]),
    ("H5 a ledger rejection is not mapped", [("    except chain.Rejected as e:", "    except KeyError as e:")]),
    ("H6 an unknown rejection code is passed on", [('e.code if e.code in wire.ERROR_CODES else "ADAPTER_UNAVAILABLE", f"the ledger rejected', 'e.code, f"the ledger rejected')]),
    ("H7 a chain failure leaks its text", [('    except chain.ChainError:\n        raise OperationError("ADAPTER_UNAVAILABLE", LEDGER_UNAVAILABLE)', '    except chain.ChainError as e:\n        raise OperationError("ADAPTER_UNAVAILABLE", str(e))')]),
    ("H8 prepare_request signs against no deployment", [("_e.prepare_request(inp, ctx.manifest)", "_e.prepare_request(inp, {})")]),
    ("H9 encrypt_record swaps the record and the policy", [('encrypt_record(inp["record"], inp["policy"], inp["keyEpoch"])', 'encrypt_record(inp["policy"], inp["record"], inp["keyEpoch"])')]),
    ("H10 release ignores the grant id", [('.release(inp["grantId"])', '.release("0x" + "00" * 32)')]),
    ("H11 finish_decryption ignores the user key reference", [('.finish_decryption(response, inp["userKeyRef"])', '.finish_decryption(response, "keyref:user:other")')]),
    ("H13 the finish result is validated as a release result", [("wire.finish_decryption_result))", "wire.release_result))")]),
    ("H14 the encrypt result is validated as a finish result", [("wire.encrypt_record_result))", "wire.finish_decryption_result))")]),
    ("H15 the release result is validated as an encrypt result", [("wire.release_result))\n\n    def finish", "wire.encrypt_record_result))\n\n    def finish")]),
]


def validate_anchors():
    bad = [(name, SRC.count(old)) for name, edits in M for old, _ in edits if SRC.count(old) != 1]
    if bad:
        print("INVALID anchors (nothing was run):", bad)
        return False
    return True


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="adv2ops-mutant-")
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
            if name.endswith(".py") and name != "adapter_v2_ops.py":
                shutil.copy(os.path.join(pkg, name), os.path.join(p, "hmbc_protocol", name))
        fx = os.path.join(PROTO, "tests", "fixtures")
        os.makedirs(os.path.join(p, "tests", "fixtures"), exist_ok=True)
        for name in os.listdir(fx):
            if name.startswith(("agent1-85c59f5", "agent3-")):
                shutil.copy(os.path.join(fx, name), os.path.join(p, "tests", "fixtures", name))
        for rel in ("pytest.ini", os.path.join("tests", "test_adapter_v2.py"), os.path.join("tests", "test_adapter_v2_ops.py")):
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "hmbc_protocol", "adapter_v2_ops.py"), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_adapter_v2_ops.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
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
