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
TESTS = {"wire": ["protocol/tests/test_candidate_schema_review.py", "protocol/tests/test_eip712_vs_agent1.py"],
         "adapter": ["protocol/tests/test_adapter.py"], "eip712": ["protocol/tests/test_eip712_vs_agent1.py"]}

M = [  # (suite, file, old, new, equivalent-reason or None)
    ("wire", "protocol/hmbc_protocol/wire.py", "    if any(a >= b for a, b in zip(keys, keys[1:])):", "    if False:", None),
    ("wire", "protocol/hmbc_protocol/wire.py", "eip712._SIG.fullmatch(v)", "eip712._SIG.match(v)", None),
    ("wire", "protocol/hmbc_protocol/wire.py", "s <= SECP256K1_N // 2", "s <= SECP256K1_N", None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'if v["gid"] == ZERO_ADDRESS:', "if False:", None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'if not v["certificates"] and not v["temporalClaims"]:', "if False:", None),
    ("wire", "protocol/hmbc_protocol/wire.py", 'if int(v["grantExpiresAt"]) == 0:', "if False:", None),
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
    ("adapter", "protocol/hmbc_protocol/keys.py", 'if role not in allowed_roles:', "if False:", None),
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
    base_rc, base_line = run(["protocol/tests"])
    results, failed = [], base_rc != 0
    for suite, rel, old, new, equiv in M:
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
