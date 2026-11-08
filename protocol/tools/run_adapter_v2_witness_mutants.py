"""Mutation check of the successor adapter handlers part 2, the witness operations (agent 2, F task 2 slice 6b-2). Standard library only. Same method as the other runners: one text replacement per mutant (it must match exactly once
and change the file), run the UNCHANGED tests/test_adapter_v2_witness.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or
timeout is NOT detection; the unmutated copy runs first as a control. the carried adapter.py, wire.py, witness_service.py, witness_pool.py and witness_pool_driver.py are NOT mutated here (their own runners do that).

Usage (repository root):   python3 -B -I protocol/tools/run_adapter_v2_witness_mutants.py        (needs pytest and the E dependencies: protocol/requirements.txt)
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
SRC = open(os.path.join(PROTO, "hmbc_protocol", "adapter_v2_witness.py")).read()

# EQUIVALENT MUTANTS found in run 1 and dropped (run 1: 52 of 64 detected; see evidence/af2-state/adapter-v2-witness-mutants-run1-52-of-64.txt):
#   V12 receipt window 600 s instead of 60 s: pool_core caps the collection deadline at 10 s, so any window of 12 s or more behaves identically (V11, a window of 1 s, IS detected).
#   V13 receipt window read from the PBC clock: only the difference `expires - now` reaches the pool and it is 60 s either way.
#   V60 the admins sorted: the typed-field rule already demands strictly ascending admins, so a valid action is already sorted and sorting changes nothing.
#   V25/V35 a signature that is not a string is not refused by an extra guard, V26/V37 a message that is not an object or holds non-strings: the signer recovery (`recover`) already returns None for each, so
#   the guard and the recovery refuse the same replies; the guards are defence in depth and are kept.
M = [
    ("V1 any profile is wired", [('if deployment.get("profile") != PROFILE:', "if False:")]),
    ("V2 the wired profile is repaired-e", [('PROFILE = "repaired-f"', 'PROFILE = "repaired-e"')]),
    ("V3 a declared witness set version is never checked", [('if inp.get("witnessSetVersion", SET_VERSION) != SET_VERSION:', "if False:")]),
    ("V4 an absent witness set version is a mismatch", [('inp.get("witnessSetVersion", SET_VERSION)', 'inp.get("witnessSetVersion", "1")')]),
    ("V5 the mismatch carries no reason", [('is 2", reason="WITNESS_SET_MISMATCH")', 'is 2")')]),
    ("V6 the governance proposal keeps the witness selector", [('for k, v in inp.items() if k != "witnessIndex"}', "for k, v in inp.items()}")]),
    ("V7 the governance window is read from the DBC", [('return proposal, int(view.observe("pbc")["timestamp"]), int(proposal["expiresAt"]), {}', 'return proposal, int(view.observe("dbc")["timestamp"]), int(proposal["expiresAt"]), {}')]),
    ("V8 the checkpoint window is read from the PBC", [('ttl=proposer_ttl)\n                return proposal, int(view.observe("dbc")', 'ttl=proposer_ttl)\n                return proposal, int(view.observe("pbc")')]),
    ("V9 the decision window is read from the PBC", [('int(view.observe("dbc")["timestamp"]), int(proposal["expiresAt"]), {"credentialRecords": records}', 'int(view.observe("pbc")["timestamp"]), int(proposal["expiresAt"]), {"credentialRecords": records}')]),
    ("V10 the decision result drops the credential records", [('{"credentialRecords": records}', "{}")]),
    ("V11 the receipt window is one second", [("RECEIPT_WINDOW_S = 60", "RECEIPT_WINDOW_S = 1")]),
    ("V14 the proposer's checkpoint lifetime is the maximum, not the default", [("ttl=proposer_ttl)", "ttl=svc.DEFAULT_MAX_TTL)")]),
    ("V15 a derivation refusal loses its code", [("        except svc.WitnessRefusal as e:\n            raise _from_refusal(e) from None", '        except svc.WitnessRefusal as e:\n            raise OperationError("ADAPTER_UNAVAILABLE", e.message) from None')]),
    ("V16 a derivation refusal loses its reason", [("return OperationError(e.code, e.message, reason=e.reason)", "return OperationError(e.code, e.message)")]),
    ("V17 an unreadable ledger on the proposer's side is not caught", [("        except svc.LedgerUnreachable as e:\n            raise _from_refusal(svc._unreachable(e)) from None", "        except svc.LedgerUnreachable:\n            raise")]),
    ("V18 the single exchange waits six seconds", [("transport.next_event(core.REPLY_TIMEOUT_MS)", "transport.next_event(core.REPLY_TIMEOUT_MS + 1000)")]),
    ("V19 the single exchange waits four seconds", [("transport.next_event(core.REPLY_TIMEOUT_MS)", "transport.next_event(core.REPLY_TIMEOUT_MS - 1000)")]),
    ("V20 a timed-out write is not cancelled", [("            transport.cancel(index, 1)\n", "            pass\n")]),
    ("V21 the reply's witness is not compared", [("if witness != index or round_no != 1", "if round_no != 1")]),
    ("V22 the reply's round is not compared", [("if witness != index or round_no != 1", "if witness != index")]),
    ("V23 a reply that is not an object is not refused", [(" or not isinstance(reply, dict):", ":")]),
    ("V24 a signature reply may carry extra keys", [('if set(reply) != {"type", "message", "signature"} or not isinstance(reply["signature"], str)', 'if not isinstance(reply["signature"], str)')]),
    ("V27 the replied message need not be the one sent", [("core.canonical_message(reply[\"message\"]) != core.canonical_message(proposal) or recover(", "recover(")]),
    ("V28 the signer is not compared with the chosen witness", [(' or recover(reply["message"], reply["signature"]) != witnesses[index]:', ":")]),
    ("V29 an error reply may carry extra keys", [('if not set(reply) <= {"type", "code", "reason", "recorded"} or reply.get("code") not in CODES:', 'if reply.get("code") not in CODES:')]),
    ("V30 an unknown error code is passed through", [('if not set(reply) <= {"type", "code", "reason", "recorded"} or reply.get("code") not in CODES:', 'if not set(reply) <= {"type", "code", "reason", "recorded"}:')]),
    ("V31 a reason of another code is accepted", [("if reason is not None and REASON_CODE.get(reason) != code:", "if False:")]),
    ("V32 a recorded value is accepted for any message type", [('if not (kind == "checkpoint" and code == "STALE_STATE"', 'if not (code == "STALE_STATE"')]),
    ("V33 a recorded value is accepted with any code or reason", [('code == "STALE_STATE" and reason == "CONFLICT_PINNED" and isinstance(recorded, dict)', "isinstance(recorded, dict)")]),
    ("V34 a recorded value may have other keys", [('isinstance(recorded, dict) and set(recorded) == {"message", "signature"}\n', "isinstance(recorded, dict)\n")]),
    ("V36 a recorded message need not be an object", [(' and isinstance(recorded["message"], dict)\n                    and all(', "\n                    and all(")]),
    ("V38 a recorded signature is not verified as the witness's", [('\n                    and _recover("checkpoint", deployment)(recorded["message"], recorded["signature"]) == witnesses[index]):', "):")]),
    ("V39 a witness refusal loses its recorded value", [("raise OperationError(code, text, reason=reason, recorded=recorded)", "raise OperationError(code, text, reason=reason)")]),
    ("V40 a witness refusal loses its reason", [("raise OperationError(code, text, reason=reason, recorded=recorded)", "raise OperationError(code, text, recorded=recorded)")]),
    ("V41 a refusal reply with an unknown type is a refusal", [('        raise _invalid(index)\n\n    def _refusal_of_witness', '        raise OperationError("ADAPTER_UNAVAILABLE", "x")\n\n    def _refusal_of_witness')]),
    ("V42 a collection adopts for every message type", [('adoption=(kind == "checkpoint")', "adoption=True")]),
    ("V43 a checkpoint collection does not adopt", [('adoption=(kind == "checkpoint")', "adoption=False")]),
    ("V44 the pool returns the proposal, not the collected message", [('return result["message"], result["signatures"], result["collection"]', 'return proposal, result["signatures"], result["collection"]')]),
    ("V45 a failed pool is returned as a success", [('if not result["ok"]:', "if False:")]),
    ("V46 a pool failure carries no evidence", [('reason="QUORUM_UNAVAILABLE", collection=result["collection"])', 'reason="QUORUM_UNAVAILABLE")')]),
    ("V47 a pool failure carries no reason", [('reason="QUORUM_UNAVAILABLE", collection=result["collection"])', 'collection=result["collection"])')]),
    ("V48 a refused pool is not translated", [("        except wp.CollectionRefused as e:\n            raise OperationError(e.code, e.message, reason=e.reason) from None", "        except wp.CollectionRefused:\n            raise")]),
    ("V49 the selector is ignored", [('if "witnessIndex" in inp:', "if False:")]),
    ("V50 the selector is read as zero", [('index = int(inp["witnessIndex"])', "index = 0")]),
    ("V51 a single result has the collection too", [('                result["signatures"] = single(kind, index, proposal, deployment)\n', '                result["signatures"] = single(kind, index, proposal, deployment)\n                result["collection"] = {}\n')]),
    ("V52 a witness list of another size is accepted", [("len(witnesses) == core.WITNESS_COUNT and all", "len(witnesses) >= 1 and all")]),
    ("V53 witnesses need not be distinct", [(" and len(set(witnesses)) == len(witnesses)):", "):")]),
    ("V54 an address need not be lowercase hex", [("_ADDR.fullmatch(a)", "True")]),
    ("V55 any transport factory is accepted", [("if not callable(transport_factory):", "if False:")]),
    ("V56 a failing signature recovery of a receipt or governance message crashes", [("        except (ValueError, KeyError, TypeError):\n            return None\n    return recover", "        except KeyError:\n            return None\n    return recover")]),
    ("V57 the decision signature is verified under the checkpoint domain", [('return wp.make_recover("AccessDecision", deployment)', 'return wp.make_recover("StateCheckpoint", deployment)')]),
    ("V58 a receipt signature is verified under the governance domain", [("return _recover_over(lambda m: svc._receipt_digest(svc._receipt_shape(m), deployment))", "return _recover_over(lambda m: svc._governance_digest(svc._governance_shape(m), deployment))")]),
    ("V59 the governance signature is verified under the receipt domain", [("    return _recover_over(lambda m: svc._governance_digest(svc._governance_shape(m), deployment))", "    return _recover_over(lambda m: svc._receipt_digest(svc._receipt_shape(m), deployment))")]),
    ("V61 the result schema version is v1", [('result = {"schemaVersion": "v2", "adapterMode": "symbolic"}', 'result = {"schemaVersion": "v1", "adapterMode": "symbolic"}')]),
    ("V62 the receipt is returned under the wrong member", [('"receipt": "receipt",', '"receipt": "grantReceipt",')]),
    ("V63 the pool is built for set version 1", [("witness_set_version=SET_VERSION)\n        except wp.CollectionRefused", 'witness_set_version="1")\n        except wp.CollectionRefused')]),
    ("V64 the proposal reaches the transport aliased with the caller's", [("transport.send(index, 1, dict(proposal))", "transport.send(index, 1, proposal)")]),
]


def validate_anchors():
    bad = [(name, SRC.count(old)) for name, edits in M for old, _ in edits if SRC.count(old) != 1]
    if bad:
        print("INVALID anchors (nothing was run):", bad)
        return False
    return True


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="adv2wit-mutant-")
    try:
        p = os.path.join(d, "protocol")
        shutil.copytree(os.path.join(PROTO, "testtools"), os.path.join(p, "testtools"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(PROTO, "f0", "vectors"), os.path.join(p, "f0", "vectors"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(PROTO, "tests", "fixtures"), os.path.join(p, "tests", "fixtures"))
        shutil.copytree(os.path.join(PROTO, "abi"), os.path.join(p, "abi"))                  # the carried code reads the ABI manifest at import time
        shutil.copytree(os.path.join(PROTO, "hmbc_protocol"), os.path.join(p, "hmbc_protocol"), ignore=shutil.ignore_patterns("__pycache__", "adapter_v2_witness.py"))
        for rel in ("pytest.ini",) + tuple(os.path.join("tests", n) for n in ("conftest.py", "support.py", "test_witness_service.py", "test_witness_service_decision.py", "test_witness_service_governance.py",
                                                                              "test_witness_service_receipt.py", "test_adapter_v2_witness.py")):
            os.makedirs(os.path.dirname(os.path.join(p, rel)) or p, exist_ok=True)
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "hmbc_protocol", "adapter_v2_witness.py"), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_adapter_v2_witness.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
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
