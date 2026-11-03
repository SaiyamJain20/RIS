#!/usr/bin/env python3
"""Compare live deployed runtime code with the compiled build, masking immutable slots (agent 1, F0).

Input to the D-f / D50 design discussion (A1-0088 D-f, A2-0041 section 4). Exported `runtimeSha256` hashes the
compiled `deployedBytecode`, whose immutable slots are zero; live code (`eth_getCode`) carries the constructor
values there, so the two differ per deployment. This tool zeroes the `immutableReferences` ranges of the Forge
artifact in the live code and checks that the result hashes to the compiled runtime. It also prints the raw live hash.

Usage (repository root; `forge build --root ledger` artifacts present; chains running):
  python3 -I ledger/tools/check_masked_runtime.py <deployment.json> [<deployment.json> ...]
Standard library only. Exit 0 when every contract's masked live code equals the compiled runtime, 1 otherwise.
"""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

LEDGER = Path(__file__).resolve().parent.parent
CHAIN_OF = {"LSC": "pbc", "TMSC": "pbc", "RSC": "pbc", "PSC": "pbc", "ACSC": "dbc", "KSSC": "dbc"}


def rpc(url, method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        out = json.loads(r.read())
    if "error" in out:
        raise RuntimeError(f"{method}: {out['error']}")
    return out["result"]


def artifact(name):
    a = json.loads((LEDGER / "out" / f"{name}.sol" / f"{name}.json").read_text())
    db = a["deployedBytecode"]
    code = bytes.fromhex(db["object"][2:] if db["object"].startswith("0x") else db["object"])
    ranges = [(r["start"], r["length"]) for refs in db.get("immutableReferences", {}).values() for r in refs]
    return code, sorted(ranges)


def check(deployment_path):
    d = json.loads(Path(deployment_path).read_text())
    rows, ok = [], True
    for name, chain in CHAIN_OF.items():
        addr = d["chains"][chain]["contracts"][name]
        url = d["chains"][chain]["rpcUrl"]
        live = bytes.fromhex(rpc(url, "eth_getCode", [addr, "latest"])[2:])
        compiled, ranges = artifact(name)
        masked = bytearray(live)
        for start, length in ranges:
            masked[start:start + length] = bytes(length)
        compiled_sha = hashlib.sha256(compiled).hexdigest()
        manifest_sha = d["abi"][name]["runtimeSha256"]
        masked_sha = hashlib.sha256(bytes(masked)).hexdigest()
        match = len(live) == len(compiled) and masked_sha == compiled_sha == manifest_sha
        ok &= match
        rows.append({
            "contract": name, "address": addr, "liveBytes": len(live), "immutableRanges": len(ranges),
            "rawLiveSha256": hashlib.sha256(live).hexdigest(), "maskedLiveSha256": masked_sha,
            "compiledSha256": compiled_sha, "manifestRuntimeSha256": manifest_sha, "maskedEqualsCompiled": match,
        })
    return {"deployment": str(deployment_path), "profile": d["profile"], "mutations": d.get("mutations"),
            "contracts": rows, "allMatch": ok}


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    results = [check(p) for p in sys.argv[1:]]
    raw = {}
    for res in results:
        for row in res["contracts"]:
            raw.setdefault(row["contract"], set()).add(row["rawLiveSha256"])
    summary = {
        "deployments": len(results),
        "allMaskedMatch": all(r["allMatch"] for r in results),
        "distinctRawLiveHashesPerContract": {k: len(v) for k, v in sorted(raw.items())},
    }
    print(json.dumps({"summary": summary, "results": results}, indent=1))
    return 0 if summary["allMaskedMatch"] else 1


if __name__ == "__main__":
    sys.exit(main())
