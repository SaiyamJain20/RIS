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
TESTS = {"wire": ["protocol/tests/test_candidate_schema_review.py", "protocol/tests/test_eip712_vs_agent1.py", "protocol/tests/test_boundary_review.py", "protocol/tests/test_boundary_review_r5.py"],
         "adapter": ["protocol/tests/test_adapter.py", "protocol/tests/test_adapter_hardening.py"], "keys": ["protocol/tests/test_messages_keys.py"],
         "witness": ["protocol/tests/test_witness.py", "protocol/tests/test_witness_policy.py", "protocol/tests/test_witness_hardening.py"],
         "worker": ["protocol/tests/test_worker.py", "protocol/tests/test_worker_hardening.py"],
         "chain": ["protocol/tests/test_chain.py", "protocol/tests/test_ledger.py", "protocol/tests/test_edges.py", "protocol/tests/test_chain_hardening.py", "protocol/tests/test_chain_stub.py"], "adapter_live": ["protocol/tests/test_adapter_live.py"],
         "controls": ["protocol/tests/test_paper_profile.py", "protocol/tests/test_paper_release.py", "protocol/tests/test_supplement_controls.py"], "eip712": ["protocol/tests/test_eip712_vs_agent1.py"],
         "bootstrap": ["protocol/tests/test_bootstrap_fixture.py"],
         "worker_log": ["protocol/tests/test_worker_log.py", "protocol/tests/test_adapter_process_paper.py"]}

M = [  # (suite, file, old, new, equivalent-reason or None)
    ("wire", "protocol/hmbc_protocol/wire.py", "    if any(a >= b for a, b in zip(keys, keys[1:])):", "    if False:", None),
    ("wire", "protocol/hmbc_protocol/wire.py", "eip712._SIG.fullmatch(v)", "eip712._SIG.match(v)", None),
    ("wire", "protocol/hmbc_protocol/wire.py", "s <= SECP256K1_N // 2", "s <= SECP256K1_N", None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'if v["gid"] == ZERO_ADDRESS:', "if False:", None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'if not v["certificates"] and not v["temporalClaims"]:', "if False:", None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'if int(v["grantExpiresAt"]) == 0:', "if False:", None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'if reqs[0]["issuerMode"] == "2":', "if False:", None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'def sigs(x):\n        if len(_list(x, "signatures")) != 1:', 'def sigs(x):\n        if False:', None),
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
    ("worker", "protocol/hmbc_protocol/worker.py", 'if int(g["recipientKeyHash"], 16) == 0 or g["recipientKeyHash"] != registered:', "if False:", "repaired-e PSC already forces request.recipientKeyHash == RSC.recipientKeyHash(gid) and the grant copies it, so this defensive check cannot fail on a real repaired-e ledger"),
    ("controls", "protocol/hmbc_protocol/worker.py", 'if int(registered, 16) == 0:', "if False:", None),
    ("controls", "protocol/hmbc_protocol/worker.py", 'if int(g["recipientKeyHash"], 16) != 0:', "if False:", "unreachable with the real ledger: only the relay-only policyEnf path mints paper grants and it always writes a zero recipient"),
    ("controls", "protocol/hmbc_protocol/worker.py", 'if led.pbc.call(led.PSC, "profile") == "2":', "if True:", None),
    ("controls", "protocol/testtools/deviating_witness.py", 'if at_block is not None and not re.fullmatch(r"[0-9]+", at_block):', "if False:", None),
    ("chain", "protocol/hmbc_protocol/chain.py", 'if got != self.chain_id:', "if False:", None),
    ("chain", "protocol/hmbc_protocol/chain.py", 'if tag != "latest" and _hex(tag) > self.block_number():', "if False:", None),
    ("chain", "protocol/hmbc_protocol/chain.py", 'parts.hostname not in ("127.0.0.1", "localhost", "::1")', "False", None),
    ("chain", "protocol/hmbc_protocol/ledger.py", 'if hashlib.sha256(raw).hexdigest() != dep["abi"][name]["abiSha256"]:', "if False:", None),
    ("witness", "protocol/hmbc_protocol/witness.py", 'if str(tx.get("to", "")).lower() != led.PSC.address:', "if False:", None),
    ("witness", "protocol/hmbc_protocol/witness.py", 'if led.dbc.call(led.KSSC, "nonceConsumed", request["gid"], request["nonce"]) is True:', "if False:", None),
    ("witness", "protocol/hmbc_protocol/witness.py", 'if code == "0" and any(int(r["validUntil"]) <= dbc_now for r in records):', "if False:", None),
    ("witness", "protocol/hmbc_protocol/witness.py", 'if request["destinationChainId"] != str(led.dbc.chain_id) or request["kssc"] != led.KSSC.address:', "if False:",
     "unreachable with the real PSC: it only forwards requests whose destination chain and KSSC it has configured, and the digest recomputation precedes this check"),
    ("witness", "protocol/hmbc_protocol/witness.py", 'if eip712.recover(digest, sig) != self.address:', "if False:", None),
    ("worker", "protocol/hmbc_protocol/worker.py", 'if stored != fp:', "if False:", None),
    ("worker", "protocol/hmbc_protocol/worker.py", 'fcntl.flock(lock, fcntl.LOCK_EX)', "pass", None),
    ("chain", "protocol/hmbc_protocol/chain.py", "        return None\n\n\n# No proxies", "        return super().redirect_request(*a, **k)\n\n\n# No proxies", None),
    ("chain", "protocol/hmbc_protocol/chain.py", "return max(latest, pending)", "return latest", None),
    ("chain", "protocol/hmbc_protocol/chain.py", 'if not isinstance(out, dict):', "if False:", None),
    ("adapter", "protocol/hmbc_protocol/adapter.py", 'if _PINNED is not None and dep != _PINNED:', "if False:", None),
    ("adapter", "protocol/hmbc_protocol/adapter.py", 'if not chunk.endswith(b"\\n") and len(chunk) > MAX_LINE_BYTES:', "if False:", None),
    ("adapter", "protocol/hmbc_protocol/eip712.py", "if len(value) > 78:", "if False:", None),   # tested via the adapter/wire hardening tests
    ("worker", "protocol/hmbc_protocol/worker.py", 'self.db.execute("update releases set sent_count=sent_count+1 where grant_id=?", (grant_id,))', "pass", None),
    ("worker", "protocol/hmbc_protocol/worker.py", 'self.db.execute("update releases set completed_count=completed_count+1 where grant_id=?", (grant_id,))', "pass", None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'def _one_signature(x):\n    if len(_list(x, "signatures")) != 1:', 'def _one_signature(x):\n    if False:', None),
    ("controls", "protocol/hmbc_protocol/witness.py", 'if led.pbc.call(led.PSC, "profile") != "2" or led.dbc.call(led.ACSC, "profile") != "2":', "if False:", None),
    ("controls", "protocol/testtools/deviating_witness.py", 'if "TEST-ONLY" not in str(led.deployment.get("fixture", {}).get("keyDerivation", "")):', "if False:", None),
    ("controls", "protocol/testtools/deviating_witness.py", "if field not in BOUND_FIELDS:", "if False:", None),
    ("controls", "protocol/testtools/deviating_witness.py", "if not allowed:", "if False:",
     "redundant with wire.grant_receipt: a missing grant reads as all zeros (grantExpiresAt 0), which the receipt validator rejects, so the tool still refuses"),
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
    ("keys", "protocol/hmbc_protocol/keys.py", 'if role not in allowed_roles:', "if False:", None),
    ("adapter", "protocol/hmbc_protocol/adapter.py", 'if eip712.recover(digest, signature) != signer:', "if False:", None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", 'ROLE_RESEARCHER = "0x" + keccak(text="HMBC.role.Researcher").hex()', 'ROLE_RESEARCHER = ROLE_DOCTOR', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", '"temporalClaims": [{"authority": h1, "role": ROLE_ON_DUTY}]}', '"temporalClaims": []}', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", '"entries": [{"gid": _addr("alice"), ', '"entries": [{"gid": _addr("bob"), ', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", '"possessionSignature": _sign(led, "Registration", reg_alice, "alice")', '"possessionSignature": _sign(led, "Registration", reg_alice, "relay")', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", 'REGISTRATION_SECONDS = 3600', 'REGISTRATION_SECONDS = 600', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", '        require_test_only(dep)\n        led = Ledger.from_deployment(dep)', '        led = Ledger.from_deployment(dep)', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", '    require_test_only(led.deployment)\n    h1, h2', '    h1, h2', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", '_step("register-alice", "relay",', '_step("register-alice", "H1-ca-admin",', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", 'contract.calldata(function, *args.values())', 'contract.calldata(function, *reversed(list(args.values())))', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", '"recipientKeyHash": keys.recipient_key_hash(f"keyref:user:{subject_label}"),', '"recipientKeyHash": keys.recipient_key_hash("keyref:user:alice"),', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", '"validFrom": str(now - 60)', '"validFrom": str(now + 60)', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", '"steps": steps, "credentialBundles": bundles, "notes": NOTES}', '"steps": steps, "credentialBundles": bundles, "notes": NOTES, "debug": keys.synthetic_private_key("alice")}', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", 'plan = build_plan(led, led.pbc.now())', 'plan = build_plan(led, led.dbc.now())', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", 'crl1 = {"authority": h1, "version": "1", "validUntil": str(now + LIST_SECONDS)', 'crl1 = {"authority": h1, "version": "1", "validUntil": str(now - LIST_SECONDS)', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", '_signed_cert(led, "H2-root", "bob", ROLE_RESEARCHER, "201")', '_signed_cert(led, "H1-root", "bob", ROLE_RESEARCHER, "201")', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", 'return {"schemaVersion": SCHEMA, "testOnly": True,', 'return {"schemaVersion": SCHEMA, "testOnly": False,', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", '_step("wrong-issuer-admin-h2-list", "H1-ca-admin",', '_step("wrong-issuer-admin-h2-list", "H2-ca-admin",', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", 'crl2_next = {"authority": h2, "version": "2"', 'crl2_next = {"authority": h2, "version": "1"', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", 'control["expected"] = "UNAUTHORIZED_CALLER"', 'control["expected"] = "BAD_SIGNATURE"', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", 'crl2_next = {"authority": h2, "version"', 'crl2_next = {"authority": h1, "version"', None),
    ("bootstrap", "protocol/testtools/bootstrap_fixture.py", '"controls": [control],', '"controls": [],', None),
    ("worker_log", "protocol/hmbc_protocol/worker_log.py", 'nested, direct = os.path.join(state_dir, "worker", "worker.sqlite"), os.path.join(state_dir, "worker.sqlite")', 'nested, direct = os.path.join(state_dir, "no-such-dir", "worker.sqlite"), os.path.join(state_dir, "worker.sqlite")', None),
    ("worker_log", "protocol/hmbc_protocol/worker_log.py", '    if len(found) == 2:\n        raise SystemExit(f"ambiguous', '    if False:\n        raise SystemExit(f"ambiguous', None),
    ("worker_log", "protocol/hmbc_protocol/worker_log.py", '    if not found:\n        raise SystemExit(f"no worker.sqlite', '    if False:\n        raise SystemExit(f"no worker.sqlite', None),
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
    grep = argv[argv.index("--grep") + 1].split("|") if "--grep" in argv else None       # restrict to mutants whose anchor contains any of these substrings
    base_rc, base_line = run(["protocol/tests"])
    results, failed = [], base_rc != 0
    for suite, rel, old, new, equiv in M:
        if only and suite not in only:
            continue
        if grep and not any(g in old for g in grep):
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
