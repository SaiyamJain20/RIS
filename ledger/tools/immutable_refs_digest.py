#!/usr/bin/env python3
"""Reference `immutableReferences` lists and their canonical-JSON sha256 per contract (agent 1, F0).

Cross-check input for the successor export (design 2.2 section 8, A3-0059 `immutableRefsSha256`). Reads the
Forge artifacts (`ledger/out/<C>.sol/<C>.json`), flattens `deployedBytecode.immutableReferences` to a list of
`{start, length}` sorted by start, and hashes `json.dumps(list, sort_keys=True, separators=(",", ":"),
ensure_ascii=True)` as UTF-8. Both number forms are printed because the form changes the hash: decimal strings
(the interfaces convention, recommended) and JSON integers.

Usage (repository root, after `forge build --root ledger`): python3 -I ledger/tools/immutable_refs_digest.py
Standard library only. Prints JSON; exit 0.
"""
import hashlib
import json
import sys
from pathlib import Path

LEDGER = Path(__file__).resolve().parent.parent
CONTRACTS = ("LSC", "TMSC", "RSC", "PSC", "ACSC", "KSSC")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def main():
    out = {}
    for name in CONTRACTS:
        db = json.loads((LEDGER / "out" / f"{name}.sol" / f"{name}.json").read_text())["deployedBytecode"]
        code_hex = db["object"][2:] if db["object"].startswith("0x") else db["object"]
        ranges = sorted((r["start"], r["length"]) for refs in db["immutableReferences"].values() for r in refs)
        as_strings = [{"start": str(s), "length": str(n)} for s, n in ranges]
        as_ints = [{"start": s, "length": n} for s, n in ranges]
        out[name] = {
            "runtimeBytes": str(len(code_hex) // 2),
            "runtimeSha256": hashlib.sha256(bytes.fromhex(code_hex)).hexdigest(),
            "immutableReferences": as_strings,
            "immutableRefsSha256DecimalStrings": hashlib.sha256(canonical(as_strings)).hexdigest(),
            "immutableRefsSha256JsonIntegers": hashlib.sha256(canonical(as_ints)).hexdigest(),
        }
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
