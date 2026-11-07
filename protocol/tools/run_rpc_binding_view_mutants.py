"""Mutation check of the successor adapter handlers the D50 JSON-RPC chain view (agent 2, F task 2 slice 8a). Standard library only. Same method as the other runners: one text replacement per mutant (it must match exactly once
and change the file), run the UNCHANGED tests/test_rpc_binding_view.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or
timeout is NOT detection; the unmutated copy runs first as a control. the carried adapter.py, wire.py, witness_service.py, witness_pool.py and witness_pool_driver.py are NOT mutated here (their own runners do that).

Usage (repository root):   python3 -B -I protocol/tools/run_rpc_binding_view_mutants.py        (needs pytest and the E dependencies: protocol/requirements.txt)
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
SRC = open(os.path.join(PROTO, "hmbc_protocol", "rpc_binding_view.py")).read()

# EQUIVALENT MUTANTS found in run 1 and dropped (run 1: 25 of 32; see evidence/af2-state/rpc-view-mutants-run1-25-of-32.txt):
#   R15/R16 address (list) not lowercased: eth_abi 6.0.0 already decodes addresses to lowercase hex, so the `.lower()` calls are defence in depth against a library that checksums; no input of this
#           library version distinguishes them.
#   R21 an unsupported INPUT type is callable: `_arg` itself refuses a value for any type it does not know (a bytes32 argument fails the decimal rule), so the early refusal and `_arg` refuse the same calls.
#   R25 a call reply of any shape is accepted: a non-string or non-hex reply fails inside the decode `try` and is the same LedgerUnreachable.
#   R38 (added for A3-0091) the address array re-encoded from the decoded tuple instead of a list: eth_abi encodes a tuple and a list identically.
#   R28 an unreadable ABI file is not refused: the substituted bytes cannot hash to the manifest's abiSha256, so the hash check refuses the same call.
M = [
    ("R1 a transport failure is not a ledger fault", [("        except ChainError as e:\n            raise _unreachable(f\"{side} {method}: {e}\") from None", "        except ChainError:\n            raise")]),
    ("R2 any chain name is accepted", [("        if side not in SIDES:\n            raise ValueError(\"chain must be 'pbc' or 'dbc'\")\n", "")]),
    ("R3 any reply is a hex quantity", [('if not isinstance(v, str) or _QTY.fullmatch(v) is None:', "if False:")]),
    ("R4 a block at another height than asked is accepted", [("        if expect is not None and number != expect:", "        if False:")]),
    ("R5 a block hash of any shape is accepted", [('or not isinstance(b.get("hash"), str) or _HASH.fullmatch(b["hash"]) is None', "")]),
    ("R6 a missing block is a ledger fault", [("        if b is None:\n            return None\n        if not isinstance(b, dict)", "        if b is None:\n            raise _unreachable('missing')\n        if not isinstance(b, dict)")]),
    ("R7 a boolean block number is accepted", [("        if isinstance(at, bool) or not isinstance(at, int) or at < 0:", "        if not isinstance(at, int) or at < 0:")]),
    ("R8 a negative block number is accepted", [("not isinstance(at, int) or at < 0:", "not isinstance(at, int):")]),
    ("R9 a call is not pinned to the block", [('[{"to": address, "data": data}, block]', '[{"to": address, "data": data}, "latest"]')]),
    ("R10 the selector ignores the argument types", [("function_signature_to_4byte_selector(f\"{fn}({','.join(types)})\")", "function_signature_to_4byte_selector(f\"{fn}()\")")]),
    ("R11 a uint argument may exceed its width", [(' or int(v) >= 1 << int(t[4:]):', ":")]),
    ("R12 an address argument may be of any shape", [('if not isinstance(v, str) or _ADDR.fullmatch(v) is None:\n                raise ValueError("an address argument', 'if False:\n                raise ValueError("an address argument')]),
    ("R13 a decoding failure escapes as another exception", [("        except Exception:  # noqa: BLE001 - eth_abi raises several types", "        except KeyError:  # noqa: BLE001 - eth_abi raises several types")]),
    ("R14 a uint comes back as an int", [("        return str(v)\n", "        return v\n")]),
    ("R17 an ambiguous overload is accepted", [("        if len(hits) != 1:", "        if len(hits) < 1:")]),
    ("R18 a state-changing function is callable", [('        if f.get("stateMutability") not in ("view", "pure") or len(f.get("outputs", [])) != 1 or', '        if len(f.get("outputs", [])) != 1 or')]),
    ("R19 a function with several outputs is callable", [('len(f.get("outputs", [])) != 1 or not _supported_output', 'len(f.get("outputs", [])) < 1 or not _supported_output')]),
    ("R20 an unsupported output type is callable", [("or not _supported_output(f[\"outputs\"][0][\"type\"]):", ":")]),
    ("R22 the contract key ignores the chain", [("names[(side, address)] = name", 'names[("pbc", address)] = name')]),
    ("R23 code of an unknown address is sent to the node", [('        if (chain, address) not in self._names:\n            raise ValueError("not a contract of that chain")\n        out = self._rpc(chain, "eth_getCode"', '        out = self._rpc(chain, "eth_getCode"')]),
    ("R24 a code reply of any shape is accepted", [('if not isinstance(out, str) or _HEX.fullmatch(out) is None:\n            raise _unreachable(f"{chain}: eth_getCode', 'if False:\n            raise _unreachable(f"{chain}: eth_getCode')]),
    ("R26 the ABI file hash is not checked", [("        if hashlib.sha256(raw).hexdigest() != pinned:", "        if False:")]),
    ("R27 the chain client's id is not checked against the manifest", [("if sc.uint_text(manifest[\"chains\"][side][\"chainId\"], 256, f\"{side} chainId\") != chains[side].chain_id:", "if False:")]),
    ("R29 chain clients for one chain only are accepted", [("if not isinstance(chains, dict) or set(chains) != set(SIDES):\n            raise ValueError(\"chains must be exactly", "if False:\n            raise ValueError(\"chains must be exactly")]),
    ("R30 a contract address of any shape is accepted", [("if not isinstance(address, str) or _ADDR.fullmatch(address) is None:", "if False:")]),
    ("R31 a contract without an ABI is accepted", [("                if not isinstance(abis.get(name), list):", "                if False:")]),
    ("R33 a hex quantity may contain separators or leading zeros", [('if not isinstance(v, str) or _QTY.fullmatch(v) is None:', 'if not isinstance(v, str) or not v.startswith("0x") or len(v) < 3:')]),
    ("R34 a hex quantity may be upper case", [('_QTY = re.compile(r"0x(0|[1-9a-f][0-9a-f]*)")', '_QTY = re.compile(r"0x(0|[1-9a-fA-F][0-9a-fA-F]*)")')]),
    ("R35 a hex quantity may have leading zeros", [('_QTY = re.compile(r"0x(0|[1-9a-f][0-9a-f]*)")', '_QTY = re.compile(r"0x[0-9a-f]+")')]),
    ("R36 an ABI reply need not be exactly canonical", [("        if not canonical:", "        if False:")]),
    ("R37 the canonical check compares the wrong encoding", [("canonical = encode([t], [list(v) if t == \"address[]\" else v]) == raw", "canonical = True")]),
    ("R32 the chain id is read through the checked client path", [('return str(self._int(self._rpc(chain, "eth_chainId", []), f"{chain} chain id"))', 'return str(self._int(self._chains[chain]._check_chain() or self._rpc(chain, "eth_chainId", []), f"{chain} chain id"))')]),
]


def validate_anchors():
    bad = [(name, SRC.count(old)) for name, edits in M for old, _ in edits if SRC.count(old) != 1]
    if bad:
        print("INVALID anchors (nothing was run):", bad)
        return False
    return True


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="rpcview-mutant-")
    try:
        p = os.path.join(d, "protocol")
        shutil.copytree(os.path.join(PROTO, "testtools"), os.path.join(p, "testtools"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(PROTO, "f0", "vectors"), os.path.join(p, "f0", "vectors"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(PROTO, "tests", "fixtures"), os.path.join(p, "tests", "fixtures"))
        shutil.copytree(os.path.join(PROTO, "abi"), os.path.join(p, "abi"))                  # the carried code reads the ABI manifest at import time
        shutil.copytree(os.path.join(PROTO, "hmbc_protocol"), os.path.join(p, "hmbc_protocol"), ignore=shutil.ignore_patterns("__pycache__", "rpc_binding_view.py"))
        for rel in ("pytest.ini",) + tuple(os.path.join("tests", n) for n in ("conftest.py", "support.py", "test_witness_service.py", "test_witness_service_decision.py", "test_witness_service_governance.py",
                                                                              "test_witness_service_receipt.py", "test_binding_open.py", "test_rpc_binding_view.py")):
            os.makedirs(os.path.dirname(os.path.join(p, rel)) or p, exist_ok=True)
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "hmbc_protocol", "rpc_binding_view.py"), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_rpc_binding_view.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
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
