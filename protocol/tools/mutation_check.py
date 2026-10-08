#!/usr/bin/env python3
"""Source-edit mutation check for the agent-2 boundary code (reproducible; restores every file it edits).

Usage (repo root): python protocol/tools/mutation_check.py [--out protocol/evidence/mutation-check.json]
Each mutation edits ONE expression in a source file and must make the named test files fail. A mutant that
survives is a test gap unless it is listed with an `equivalent` reason (another layer rejects the same input).
Exit 0 only if every non-equivalent mutant is detected and the unmutated baseline passes.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
TESTS = {"wire": ["protocol/tests/test_candidate_schema_review.py", "protocol/tests/test_eip712_vs_agent1.py", "protocol/tests/test_boundary_review.py"],
         "adapter": ["protocol/tests/test_adapter.py"], "keys": ["protocol/tests/test_messages_keys.py"],
         "witness": ["protocol/tests/test_witness.py", "protocol/tests/test_witness_policy.py"], "worker": ["protocol/tests/test_worker.py"],
         "chain": ["protocol/tests/test_chain.py", "protocol/tests/test_ledger.py", "protocol/tests/test_edges.py"], "adapter_live": ["protocol/tests/test_adapter_live.py"], "eip712": ["protocol/tests/test_eip712_vs_agent1.py"]}

M = [  # (suite, file, old, new, equivalent-reason or None)
    ("wire", "protocol/hmbc_protocol/wire.py", "    if any(a >= b for a, b in zip(keys, keys[1:])):", "    if False:", None),
    ("wire", "protocol/hmbc_protocol/wire.py", "eip712._SIG.fullmatch(v)", "eip712._SIG.match(v)", None),
    ("wire", "protocol/hmbc_protocol/wire.py", "s <= SECP256K1_N // 2", "s <= SECP256K1_N", None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'if v["gid"] == ZERO_ADDRESS:', "if False:", None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'if not v["certificates"] and not v["temporalClaims"]:', "if False:", None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'if int(v["grantExpiresAt"]) == 0:', "if False:", None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'if reqs[0]["issuerMode"] == "2":', "if False:", None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'if len(_list(x, "signatures")) != 1:', "if False:", None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'recipientKeyHash=hash32, keyEpoch=_e_const("0"),', "recipientKeyHash=hash32, keyEpoch=lambda x: None,", None),
    ("wire", "protocol/hmbc_protocol/wire.py", "if not isinstance(x, bool):", "if False:", None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'code=lambda c: _enum(c, tuple(ERROR_CODES), "code")', "code=lambda c: None", None),
    ("wire", "protocol/hmbc_protocol/wire.py", '        if v["error"] is not None:\n            _fail("success must have a null error")', '        if False:\n            _fail("success must have a null error")', None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'if operation == "rotate_epoch":', "if False:", None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'if not clauses:\n        _fail("policy needs at least one clause")', 'if False:\n        _fail("policy needs at least one clause")', None),
    ("adapter", "protocol/hmbc_protocol/adapter.py", '            wire.INPUTS[op](req["input"])', "            pass", None),
    ("witness", "protocol/hmbc_protocol/witness.py", '        if forwarded_at > src:', "        if False:", None),
    ("witness", "protocol/hmbc_protocol/witness.py", 'if request["authEpoch"] != cp["authEpoch"] or request["policyVersion"] != cp["policyVersion"]:', "if False:", None),
    ("witness", "protocol/hmbc_protocol/witness.py", 'satisfied = code == "0" and led.dbc.call(led.ACSC, "evaluate", request["dataId"], records) is True', 'satisfied = code == "0"', None),
    ("witness", "protocol/hmbc_protocol/witness.py", 'satisfied = code == "0" and led.dbc.call(led.ACSC, "evaluate", request["dataId"], records) is True', 'satisfied = True', None),
    ("witness", "protocol/hmbc_protocol/witness.py", "if not exists or dbc_now >= int(cp[\"expiresAt\"]):", "if not exists:", None),
    ("witness", "protocol/hmbc_protocol/witness.py", 'if not allowed or "0x" + eip712.grant_id(', 'if False and "0x" + eip712.grant_id(', None),
    ("witness", "protocol/hmbc_protocol/witness.py", 'if rec["status"] != "1":\n            raise WitnessError("WRONG_SUBJECT", "the PBC has not forwarded this request digest")', 'if False:\n            raise WitnessError("WRONG_SUBJECT", "the PBC has not forwarded this request digest")', 'redundant with the AccessForwarded log lookup, which raises the same WRONG_SUBJECT for any digest the PSC did not forward'),
    ("witness", "protocol/hmbc_protocol/witness.py", 'if recomputed != digest:', "if False:", 'defence against a PSC that emits AccessForwarded for a digest its own calldata does not hash to; unreachable with the real PSC (address-filtered log, indexed digest)'),
    ("witness", "protocol/hmbc_protocol/witness.py", 'if self.address not in pbc_set or self.address not in dbc_set:', "if False:", None),
    ("worker", "protocol/hmbc_protocol/worker.py", 'if now >= int(g["expiresAt"]):', "if False:", None),
    ("worker", "protocol/hmbc_protocol/worker.py", 'token = "0x" + os.urandom(32).hex()', 'token = "0x" + "11" * 32', None),
    ("worker", "protocol/hmbc_protocol/worker.py", 'if issued is None or not all(hmac.compare_digest(a.encode(), b.encode()) for a, b in zip(issued, offered)):', "if issued is None:", None),
    ("worker", "protocol/hmbc_protocol/worker.py", 'if keys.recipient_key_hash(user_key_ref) != issued[3]:', "if False:", None),
    ("worker", "protocol/hmbc_protocol/worker.py", 'if pd != registered:', "if False:", None),
    ("worker", "protocol/hmbc_protocol/worker.py", 'if not g["exists"] or not g["allowed"] or bound != grant_id:', 'if not g["exists"]:', 'unreachable with the real KSSC: every stored grant has allowed=true and grantId is derived from its own requestDigest, so only `exists` can fail'),
    ("worker", "protocol/hmbc_protocol/worker.py", 'if int(g["recipientKeyHash"], 16) == 0 or g["recipientKeyHash"] != led.pbc.call(led.RSC, "recipientKeyHash", g["gid"]):', "if False:", 'repaired-e PSC already forces request.recipientKeyHash == RSC.recipientKeyHash(gid) and the grant copies it; the zero/mismatch case only arises for paper-profile grants, which the fixture does not deploy'),
    ("chain", "protocol/hmbc_protocol/chain.py", 'if got != self.chain_id:', "if False:", None),
    ("chain", "protocol/hmbc_protocol/chain.py", 'if tag != "latest" and int(tag, 16) > self.block_number():', "if False:", None),
    ("chain", "protocol/hmbc_protocol/ledger.py", 'parts.hostname not in ("127.0.0.1", "localhost", "::1")', "False", None),
    ("chain", "protocol/hmbc_protocol/ledger.py", 'if hashlib.sha256(raw).hexdigest() != dep["abi"][name]["abiSha256"]:', "if False:", None),
    ("eip712", "protocol/hmbc_protocol/eip712.py", "_ADDR.fullmatch(value)", "_ADDR.match(value)", None),
    ("eip712", "protocol/hmbc_protocol/eip712.py", "if not isinstance(value, str) or not _DEC.fullmatch(value):", "if not isinstance(value, (str, int)) or (isinstance(value, str) and not _DEC.fullmatch(value)):", None),
    ("adapter", "protocol/hmbc_protocol/adapter.py", 'if req["gid"] != signer:', "if False:", None),
    ("adapter", "protocol/hmbc_protocol/adapter.py", '    if (req["sourceChainId"], req["psc"], req["destinationChainId"], req["kssc"]) != (', '    if False and (req["sourceChainId"], req["psc"], req["destinationChainId"], req["kssc"]) != (', None),
    ("adapter", "protocol/hmbc_protocol/adapter.py", 'if req["keyEpoch"] != dep["fixture"]["keyEpoch"] or req["policyVersion"] != dep["fixture"]["policyVersion"]:', "if False:", None),
    ("adapter", "protocol/hmbc_protocol/adapter.py", "    except Exception:  # noqa: BLE001 - boundary must not leak internals (e.g. key material in a traceback)", "    except ZeroDivisionError:", None),
    ("adapter", "protocol/hmbc_protocol/adapter.py", "object_pairs_hook=_reject_duplicates, ", "", None),
    ("adapter", "protocol/hmbc_protocol/adapter.py", "if not isinstance(obj, dict) or set(obj) != fields:", "if not isinstance(obj, dict):", None),
    ("adapter", "protocol/hmbc_protocol/adapter.py", 'if len(line.encode("utf-8", "replace")) > MAX_LINE_BYTES:', "if False:", None),
    ("adapter", "protocol/hmbc_protocol/adapter.py", 'if req["schemaVersion"] != SCHEMA_VERSION:', "if False:", None),
    ("adapter", "protocol/hmbc_protocol/adapter.py", "if not isinstance(op, str) or op not in OPERATIONS:", "if op not in OPERATIONS:", None),
    ("adapter", "protocol/hmbc_protocol/adapter.py", 'raise AdapterError("ADAPTER_UNAVAILABLE", f"{name} is B-E1', 'return {"ok": 1}; raise AdapterError("ADAPTER_UNAVAILABLE", f"{name} is B-E1', None),
    ("keys", "protocol/hmbc_protocol/keys.py", 'if role not in allowed_roles:', "if False:", None),
    ("adapter", "protocol/hmbc_protocol/adapter.py", "    assert eip712.recover(digest, signature) == signer  # never emit a signature that does not verify\n", "",
     "defence-in-depth assertion: deterministic signing of the digest cannot recover a different key"),
    ("adapter", "protocol/hmbc_protocol/adapter.py", "parse_constant=_reject_constant", "parse_constant=None",
     "NaN/Infinity become floats that the strict wire validators then reject as non-strings"),
]


def run(files):
    r = subprocess.run([PY, "-m", "pytest", "-q", "-x", "-c", "protocol/pytest.ini", "--rootdir", "protocol", *files],
                       cwd=ROOT, capture_output=True, text=True)
    return r.returncode, (r.stdout.strip().splitlines() or [""])[-1]


def main(argv):
    out = pathlib.Path(argv[argv.index("--out") + 1]) if "--out" in argv else ROOT / "protocol/evidence/mutation-check.json"
    only = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None      # restrict to suites, e.g. witness,worker
    base_rc, base_line = run(["protocol/tests"])
    results, failed = [], base_rc != 0
    for suite, rel, old, new, equiv in M:
        if only and suite not in only:
            continue
        path = ROOT / rel
        orig = path.read_text()
        assert orig.count(old) == 1, f"mutation anchor not unique/present: {rel}: {old!r}"
        try:
            path.write_text(orig.replace(old, new, 1))
            rc, line = run(TESTS[suite])
        finally:
            path.write_text(orig)
        detected = rc != 0
        status = "DETECTED" if detected else ("SURVIVED-EQUIVALENT" if equiv else "SURVIVED")
        failed |= (status == "SURVIVED")
        results.append({"file": rel, "old": old.strip(), "new": new.strip(), "status": status, "equivalentReason": equiv, "pytestTail": line})
    summary = {"baseline": {"exitCode": base_rc, "tail": base_line}, "python": sys.version.split()[0], "mutants": results,
               "detected": sum(r["status"] == "DETECTED" for r in results), "total": len(results),
               "survivedEquivalent": sum(r["status"] == "SURVIVED-EQUIVALENT" for r in results),
               "survivedGap": sum(r["status"] == "SURVIVED" for r in results)}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("baseline", "detected", "total", "survivedEquivalent", "survivedGap")}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
