"""Runner-style live check of a bootstrap fixture (A1-0029). Standard library plus Foundry `cast`.

Usage (repository root, chains running, ledger deployed by tools/deploy_local.sh):
    python3 -I ledger/tools/check_bootstrap.py <deployment.json> <bootstrap.json>

It does what the C-E1 runner would do with the JSON, using only the TEST-ONLY CA-Admin and relay keys:
submit the trust lists in order from their submitterRole accounts, register Alice and Bob through
RSC.register, then read TMSC.checkCredentials (PBC, at the PBC latest timestamp) and
ACSC.evaluate(DATA_P1, records) (DBC). Expected: Alice code 0 with 2 records and policy true; Bob
code 0 with 1 record and policy false. Exit 0 only if every expectation holds. It writes nothing.
"""

import json
import subprocess
import sys

DATA_P1 = "0x53ff15331656b9b303d95970634a992ed32268c5d9723c90ddc94ceeb397061e"
RECORD = "(address,bytes32,uint8,uint64,uint64,uint64)"
CERT = "((address,address,bytes32[],uint64,uint64,uint64),bytes)"
BUNDLE = f"({CERT}[],(address,bytes32)[])"


def cast(*args: str) -> str:
    out = subprocess.run(["cast", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"cast {args[0]} failed: {out.stderr.strip()[:400]}")
    return out.stdout.strip()


def key(label: str) -> str:
    return cast("keccak", "hmbc-e0-synthetic-key:" + label)


def cert_arg(sc: dict) -> str:
    c = sc["cert"]
    roles = "[" + ",".join(c["roles"]) + "]"
    return f"(({c['issuer']},{c['gid']},{roles},{c['serial']},{c['validFrom']},{c['validUntil']}),{sc['signature']})"


def bundle_arg(b: dict) -> str:
    certs = "[" + ",".join(cert_arg(c) for c in b["certificates"]) + "]"
    claims = "[" + ",".join(f"({t['authority']},{t['role']})" for t in b["temporalClaims"]) + "]"
    return f"({certs},{claims})"


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    dep = json.load(open(sys.argv[1]))
    boot = json.load(open(sys.argv[2]))
    pbc, dbc = dep["chains"]["pbc"], dep["chains"]["dbc"]
    prpc, drpc = pbc["rpcUrl"], dbc["rpcUrl"]
    tmsc, rsc, acsc = pbc["contracts"]["TMSC"], pbc["contracts"]["RSC"], dbc["contracts"]["ACSC"]
    assert boot["binding"]["tmsc"] == tmsc.lower() and boot["binding"]["rsc"] == rsc.lower(), "binding mismatch"
    ok = True

    for item in boot["trustLists"]:
        lst, pk = item["list"], key(item["submitterRole"])
        if item["kind"] == "RevocationList":
            arg = f"({lst['authority']},{lst['version']},{lst['validUntil']},[{','.join(lst['revokedSerials'])}])"
            sig = "updateRevocationList((address,uint64,uint64,uint64[]),bytes)"
        else:
            entries = ",".join(f"({e['gid']},{e['role']},{e['validFrom']},{e['validUntil']})" for e in lst["entries"])
            arg = f"({lst['authority']},{lst['version']},{lst['validUntil']},[{entries}])"
            sig = "updateTemporalAcl((address,uint64,uint64,(address,bytes32,uint64,uint64)[]),bytes)"
        cast("send", "--rpc-url", prpc, "--private-key", pk, tmsc, sig, arg, item["signature"])
        print(f"submitted {item['kind']} {item['submitterRole']} v{lst['version']}")

    relay = key("relay")
    for label in ("alice", "bob"):
        u = boot["users"][label]
        r = u["registration"]
        reg = f"({r['gid']},{r['certDigest']},{r['recipientKeyHash']},{r['expiresAt']})"
        cast("send", "--rpc-url", prpc, "--private-key", relay, rsc,
             f"register((address,bytes32,bytes32,uint64),bytes,{CERT})", reg, u["possessionSignature"],
             cert_arg(u["certificate"]))
        registered = cast("call", "--rpc-url", prpc, rsc, "recipientKeyHash(address)(bytes32)", u["gid"])
        print(f"registered {label} recipientKeyHash={registered}")
        ok &= registered == u["recipientKeyHash"]

    now = cast("block", "latest", "--field", "timestamp", "--rpc-url", prpc).split()[0]
    for label, n_records, policy in (("alice", 2, "true"), ("bob", 1, "false")):
        u = boot["users"][label]
        res = json.loads(cast("call", "--json", "--rpc-url", prpc, tmsc,
                              f"checkCredentials(address,{BUNDLE},uint64)(uint8,{RECORD}[])",
                              u["gid"], bundle_arg(u["bundle"]), now))
        code, records = res[0], res[1]
        if isinstance(records, str):
            records = json.loads(records)
        rec_arg = "[" + ",".join("(" + ",".join(str(x) for x in r) + ")" for r in records) + "]"
        allowed = cast("call", "--rpc-url", drpc, acsc, f"evaluate(bytes32,{RECORD}[])(bool)", DATA_P1, rec_arg)
        count = rec_arg.count("(")
        good = str(code) == "0" and count == n_records and allowed == policy
        ok &= good
        print(f"{'OK ' if good else 'BAD'} {label}: checkCredentials code={code} records={count} evaluate(P1)={allowed}")
    print("ALL BOOTSTRAP CHECKS PASSED" if ok else "BOOTSTRAP CHECK FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
