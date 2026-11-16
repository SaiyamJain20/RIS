#!/usr/bin/env python3
"""Compare live deployed runtime code with the compiled build, masking immutable slots (agent 1, F0).

Input to the D-f / D50 design discussion (A1-0088 D-f, A2-0041 section 4). Exported `runtimeSha256` hashes the
compiled `deployedBytecode`, whose immutable slots are zero; live code (`eth_getCode`) carries the constructor
values there, so the two differ per deployment. This tool zeroes the `immutableReferences` ranges of the Forge
artifact in the live code and checks that the result hashes to the compiled runtime. It also prints the raw live hash.

Usage (repository root; `forge build --root ledger` artifacts present):
  python3 -I ledger/tools/check_masked_runtime.py [--save-code DIR] <deployment.json> [...]   # chains running
  python3 -I ledger/tools/check_masked_runtime.py --code-dir DIR <deployment.json> [...]       # offline replay
`--save-code` writes each live runtime to DIR/<deployment dir name>/<Contract>.hex; `--code-dir` reads it back
instead of calling the RPC. The immutable ranges must be sorted, non-overlapping, 32 bytes each and inside the
compiled length, and the live length must equal the compiled length.
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


def ranges_valid(ranges, size):
    """Sorted, non-overlapping, inside [0, size), each 32 bytes (one EVM word per immutable read)."""
    end = 0
    for start, length in ranges:
        if start < end or length != 32 or start + length > size:
            return False
        end = start + length
    return True


def live_code(d, name, chain, code_dir, save_dir, stem):
    """Live runtime from RPC, or from `<code_dir>/<stem>/<name>.hex` for an offline replay."""
    if code_dir:
        return bytes.fromhex((Path(code_dir) / stem / f"{name}.hex").read_text().strip())
    addr = d["chains"][chain]["contracts"][name]
    code = bytes.fromhex(rpc(d["chains"][chain]["rpcUrl"], "eth_getCode", [addr, "latest"])[2:])
    if save_dir:
        out = Path(save_dir) / stem
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{name}.hex").write_text(code.hex() + "\n")
    return code


def check(deployment_path, code_dir=None, save_dir=None):
    d = json.loads(Path(deployment_path).read_text())
    stem = Path(deployment_path).parent.name
    rows, ok = [], True
    chain_of = dict(CHAIN_OF)
    if "Governance" in d["chains"]["pbc"]["contracts"]:  # REPAIRED_F (A-F1): the seventh runtime
        chain_of["Governance"] = "pbc"
    for name, chain in chain_of.items():
        addr = d["chains"][chain]["contracts"][name]
        live = live_code(d, name, chain, code_dir, save_dir, stem)
        compiled, ranges = artifact(name)
        compiled_sha = hashlib.sha256(compiled).hexdigest()
        manifest_sha = d["abi"][name]["runtimeSha256"]
        valid = ranges_valid(ranges, len(compiled))
        masked_sha = None
        if valid and len(live) == len(compiled):
            # Build the masked copy by concatenation, only after the ranges and length are validated
            # (a slice assignment past the end would silently resize the buffer; A2-0043 item 4).
            parts, pos = [], 0
            for start, length in ranges:
                parts += [live[pos:start], bytes(length)]
                pos = start + length
            masked_sha = hashlib.sha256(b"".join(parts + [live[pos:]])).hexdigest()
        match = masked_sha is not None and masked_sha == compiled_sha == manifest_sha
        ok &= match
        rows.append({
            "contract": name, "address": addr, "liveBytes": len(live), "compiledBytes": len(compiled),
            "immutableRanges": [{"start": s, "length": n} for s, n in ranges], "rangesValid": valid,
            "rawLiveSha256": hashlib.sha256(live).hexdigest(), "maskedLiveSha256": masked_sha,
            "compiledSha256": compiled_sha, "manifestRuntimeSha256": manifest_sha, "maskedEqualsCompiled": match,
        })
    return {"deployment": str(deployment_path), "profile": d["profile"], "mutations": d.get("mutations"),
            "contracts": rows, "allMatch": ok}


def main():
    args = sys.argv[1:]
    opts = {}
    for flag in ("--code-dir", "--save-code"):
        if flag in args:
            i = args.index(flag)
            opts[flag] = args[i + 1]
            del args[i:i + 2]
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    results = [check(p, opts.get("--code-dir"), opts.get("--save-code")) for p in args]
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
