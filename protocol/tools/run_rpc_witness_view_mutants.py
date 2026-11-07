"""Mutation check of the successor adapter handlers the witness-side JSON-RPC ledger view (agent 2, F task 2 slice 9a). Standard library only. Same method as the other runners: one text replacement per mutant (it must match exactly once
and change the file), run the UNCHANGED tests/test_rpc_witness_view.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or
timeout is NOT detection; the unmutated copy runs first as a control. the carried adapter.py, wire.py, witness_service.py, witness_pool.py and witness_pool_driver.py are NOT mutated here (their own runners do that).

Usage (repository root):   python3 -B -I protocol/tools/run_rpc_witness_view_mutants.py        (needs pytest and the E dependencies: protocol/requirements.txt)
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
SRC = open(os.path.join(PROTO, "hmbc_protocol", "rpc_witness_view.py")).read()

# EQUIVALENT MUTANT W46 (added for A3-0093, an AttributeError not caught by the guard): since the transaction reply is validated as an object, the junk-reply property test (every raw reply of every method
# replaced by junk) finds no remaining path that raises AttributeError, so the clause is defence in depth and no input distinguishes it.
# EQUIVALENT MUTANT dropped (run 1: 42 of 44, the other survivor W21 was a gap in my test: the fake contract addresses had no hex letters, so upper-casing them changed nothing): W34, an AbiError is not
# caught by the first `except`: abi.AbiError is a ValueError, and the second `except` clause catches ValueError, so the same LedgerUnreachable results.
M = [
    ("W1 observe reports another chain id", [('"chainId": str(c.chain_id)', '"chainId": "1"')]),
    ("W2 observe reports the block number as the timestamp", [('"timestamp": str(b["timestamp"])}', '"timestamp": str(b["number"])}')]),
    ("W3 a missing block is an empty dict", [("            if b is None:\n                return None\n            return {\"number\": str(n)", "            if b is None:\n                return {}\n            return {\"number\": str(n)")]),
    ("W4 the chain id is not checked for a block read", [("            c._check_chain()\n", "")]),
    ("W5 now is the latest block timestamp", [("return self._guard(c.now)", 'return self._guard(lambda: c.get_block("latest")["timestamp"])')]),
    ("W6 the auth epoch is not read at the block", [('self._call("pbc", "TMSC", "authEpoch", block=n)', 'self._call("pbc", "TMSC", "authEpoch")')]),
    ("W7 the policy version is read from the TMSC", [('self._call("pbc", "PSC", "policyVersion", block=n)', 'self._call("pbc", "TMSC", "policyVersion", block=n)')]),
    ("W8 the witness set version is read from the TMSC", [('self._call("pbc", "PSC", "witnessSetVersion", block=n)', 'self._call("pbc", "TMSC", "witnessSetVersion", block=n)')]),
    ("W9 the governance nonce is another getter", [('"Governance", "governanceNonce"', '"Governance", "governanceChainId"')]),
    ("W10 is_authority reads the removed flag", [('"TMSC", "isAuthority", root', '"TMSC", "removedAuthority", root')]),
    ("W11 removed_authority reads the authority flag", [('"TMSC", "removedAuthority", root', '"TMSC", "isAuthority", root')]),
    ("W12 the request record is another getter", [('"PSC", "getRequest"', '"PSC", "requests"')]),
    ("W13 the credential timestamp is not a decimal string", [("bundle, str(at_timestamp), block=", "bundle, at_timestamp, block=")]),
    ("W14 credentials are not read at the block", [('str(at_timestamp), block=self._number(block))', "str(at_timestamp))")]),
    ("W15 the credential result order is swapped", [("        code, records = self._exactly(out, 2)\n", "        records, code = self._exactly(out, 2)\n")]),
    ("W16 a multi-value answer of another size is accepted", [("or len(out) != n:", ":")]),
    ("W17 the forwarded block is parsed as decimal", [('"block": int(lg["blockNumber"], 16)} for lg in logs])\n\n    def forwarding_call', '"block": int(lg["blockNumber"])} for lg in logs])\n\n    def forwarding_call')]),
    ("W18 forwarded logs filter another event", [('"PSC", "AccessForwarded"', '"PSC", "AccessDenied"')]),
    ("W19 grant logs filter another event", [('"KSSC", "GrantIssued"', '"KSSC", "StateAccepted"')]),
    ("W20 the grant log hash is the transaction hash", [('"hash": lg["blockHash"]', '"hash": lg["transactionHash"]')]),
    ("W21 the transaction target is not lowercased", [('str(tx.get("to") or "").lower()', 'str(tx.get("to") or "")')]),
    ("W22 an undecodable transaction is a ledger fault", [("        except (AbiError, KeyError, TypeError, ValueError):\n            return None", "        except (AbiError, KeyError, TypeError, ValueError):\n            raise _unreachable('x')")]),
    ("W23 the request and signature of a call are swapped", [("request, signature, bundle = args", "signature, request, bundle = args")]),
    ("W24 another method still carries a request", [('"request": None, "signature": None, "bundle": None}', '"request": args, "signature": None, "bundle": None}')]),
    ("W25 a missing checkpoint is reported as present", [("if exists else None", "if not exists else None")]),
    ("W26 the checkpoint dict is not copied", [("self._guard(lambda: dict(cur))", "cur")]),
    ("W27 the nonce is passed as an int", [('"nonceConsumed", gid, str(nonce))', '"nonceConsumed", gid, nonce)')]),
    ("W28 the policy is another getter", [('"ACSC", "evaluate"', '"ACSC", "policy"')]),
    ("W29 the grant digest and data id are swapped", [('{"digest": digest, "dataId": data_id,', '{"digest": data_id, "dataId": digest,')]),
    ("W30 a hash argument of any shape is accepted", [("        if not isinstance(v, str) or _HASH.fullmatch(v) is None:", "        if False:")]),
    ("W31 a boolean block number is accepted", [("        if isinstance(n, bool) or not isinstance(n, int) or n < 0:", "        if not isinstance(n, int) or n < 0:")]),
    ("W32 a negative block number is accepted", [("not isinstance(n, int) or n < 0:", "not isinstance(n, int):")]),
    ("W33 any chain name is accepted", [("        if side not in SIDES:\n            raise ValueError(\"chain must be 'pbc' or 'dbc'\")\n", "")]),
    ("W35 an unusable answer is not a ledger fault", [("        except (KeyError, TypeError, ValueError, IndexError, AttributeError) as e:", "        except KeyError as e:")]),
    ("W36 a missing contract is a KeyError", [('            raise ValueError(f"this view has no {name} contract") from None', "            raise")]),
    ("W37 the pbc block timestamp is parsed as decimal", [('str(int(b["timestamp"], 16))', 'str(int(b["timestamp"]))')]),
    ("W38 the ABI file hash is not checked", [("                if hashlib.sha256(raw).hexdigest() != pinned:", "                if False:")]),
    ("W39 the chain id of the clients is not checked", [("                if sc.uint_text(manifest[\"chains\"][side][\"chainId\"], 256, f\"{side} chainId\") != chains[side].chain_id:", "                if False:")]),
    ("W40 the required contracts are not checked", [("not set(REQUIRED) <= set(contracts) <= set(CONTRACT_SIDE)", "False")]),
    ("W41 a contract address of any shape is accepted", [("or _ADDR.fullmatch(c.address) is None:", ":")]),
    ("W42 chain clients for one chain only are accepted", [("if not isinstance(chains, dict) or set(chains) != set(SIDES):\n            raise ValueError(\"chains must be exactly", "if False:\n            raise ValueError(\"chains must be exactly")]),
    ("W45 a non-object transaction reply is not validated", [("        if not isinstance(tx, dict):", "        if False:")]),
    ("W47 a non-object transaction reply is classified as a missing call", [('            raise _unreachable(f"the node answered {type(tx).__name__} where a transaction object was expected")', "            return None")]),
    ("W43 the logs hash is validated after the guard (a caller bug looks like a ledger fault)", [("        topic = self._hash32(topic_value, \"topic\")                       # validated BEFORE the guard: a caller bug must not look like a ledger fault\n        return self._guard(lambda: c.get_logs(contract.address, [topic0, topic]))", "        return self._guard(lambda: c.get_logs(contract.address, [topic0, self._hash32(topic_value, \"topic\")]))")]),
    ("W44 the transaction hash is validated inside the guard", [("        tx_hash = self._hash32(tx_hash, \"tx hash\")\n        tx = self._guard(lambda: c.get_transaction(tx_hash))", "        tx = self._guard(lambda: c.get_transaction(self._hash32(tx_hash, \"tx hash\")))")]),
]


def validate_anchors():
    bad = [(name, SRC.count(old)) for name, edits in M for old, _ in edits if SRC.count(old) != 1]
    if bad:
        print("INVALID anchors (nothing was run):", bad)
        return False
    return True


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="wview-mutant-")
    try:
        p = os.path.join(d, "protocol")
        shutil.copytree(os.path.join(PROTO, "testtools"), os.path.join(p, "testtools"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(PROTO, "f0", "vectors"), os.path.join(p, "f0", "vectors"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(PROTO, "tests", "fixtures"), os.path.join(p, "tests", "fixtures"))
        shutil.copytree(os.path.join(PROTO, "abi"), os.path.join(p, "abi"))                  # the carried code reads the ABI manifest at import time
        shutil.copytree(os.path.join(PROTO, "hmbc_protocol"), os.path.join(p, "hmbc_protocol"), ignore=shutil.ignore_patterns("__pycache__", "rpc_witness_view.py"))
        for rel in ("pytest.ini",) + tuple(os.path.join("tests", n) for n in ("conftest.py", "support.py", "test_witness_service.py", "test_witness_service_decision.py", "test_witness_service_governance.py",
                                                                              "test_witness_service_receipt.py", "test_witness_service.py", "test_rpc_witness_view.py")):
            os.makedirs(os.path.dirname(os.path.join(p, rel)) or p, exist_ok=True)
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "hmbc_protocol", "rpc_witness_view.py"), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_rpc_witness_view.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
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
