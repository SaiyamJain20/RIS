#!/usr/bin/env python3
"""Cross-check the ledger's EIP-712 vectors with Foundry `cast` (alloy's independent encoder).

Usage (repository root): python3 -I ledger/tools/crosscheck_cast.py [vectors.json]

For every signed vector: `cast wallet sign --data --from-file typed/<T>.json` hashes the standard
typed-data JSON itself and signs with the TEST-ONLY key. RFC 6979 signatures are deterministic, so
equal signatures imply equal EIP-712 digests. `cast wallet sign --no-hash <digest>` checks the digest
column, and every mutation must change the digest and must not recover the original signer.
Exit status 0 only if every check passes. Standard library only.
"""
import json
import pathlib
import shutil
import subprocess
import sys

LEDGER = pathlib.Path(__file__).resolve().parent.parent


def cast(*args: str) -> str:
    exe = shutil.which("cast")
    if exe is None:
        raise SystemExit("cast not found on PATH")
    out = subprocess.run([exe, *args], check=True, capture_output=True, text=True)
    return out.stdout.strip().lower()


def main(argv) -> int:
    path = pathlib.Path(argv[1]) if len(argv) > 1 else LEDGER / "exports" / "vectors" / "eip712-v0-ledger.json"
    doc = json.loads(path.read_text())
    failures = 0
    checks = 0
    for v in doc["vectors"]:
        name = v["name"]
        if "typedData" not in v:  # unsigned encoding vector (credentialDigest)
            base = v["credentialDigest"]
            for m in v["mutations"]:
                checks += 1
                if m["digest"] == base:
                    failures += 1
                    print(f"FAIL {name}: mutation {m['field']} did not change the digest")
            print(f"ok   {name}: {len(v['mutations'])} mutations change credentialDigest")
            continue
        typed_file = LEDGER / "exports" / "vectors" / "typed" / f"{name}.json"
        on_disk = json.loads(typed_file.read_text())
        checks += 1
        if on_disk != v["typedData"]:
            failures += 1
            print(f"FAIL {name}: typed/{name}.json differs from the embedded typedData")
        key = v["signerPrivateKey"]
        sig_typed = cast("wallet", "sign", "--data", "--from-file", str(typed_file), "--private-key", key)
        sig_digest = cast("wallet", "sign", "--no-hash", v["digest"], "--private-key", key)
        signer = cast("wallet", "address", "--private-key", key)
        for label, got in (("typed-data hash", sig_typed), ("digest column", sig_digest)):
            checks += 1
            if got != v["signature"].lower():
                failures += 1
                print(f"FAIL {name}: cast signature over {label} differs\n  cast  {got}\n  forge {v['signature']}")
        checks += 1
        if signer != v["signer"]:
            failures += 1
            print(f"FAIL {name}: signer {signer} != {v['signer']}")
        for m in v["mutations"]:
            checks += 2
            if m["digest"] == v["digest"]:
                failures += 1
                print(f"FAIL {name}: mutation {m['field']} did not change the digest")
            if m["recoveredFromBaseSignature"] == v["signer"]:
                failures += 1
                print(f"FAIL {name}: base signature still recovers the signer after mutating {m['field']}")
        print(f"ok   {name}: cast typed-data signature == forge signature; {len(v['mutations'])} mutations rejected")
    print(f"{checks} checks, {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
