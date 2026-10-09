"""Agent 1 ledger-scope review of E01 subject-substitution live evidence (solo phase).

Independent of agent 3's oracle: decodes the substituted ACSC call with the ledger's own exported
ABIs (ledger/exports/abi) and checks the native facts the ledger guarantees:

  repaired-e  consumeDecision(request with gid swapped, original certificate) reverts
              Rejected(WRONG_SUBJECT=2) at DecisionVerifier step 4; only gid differs from the
              signed original; grant/request/nonces/access count/logs unchanged.
  paper-*     policyEnf(fwd with gid swapped, original verified records) issues exactly one grant
              to the substituted gid with recipientKeyHash 0, keyEpoch 0, consumeNonce false,
              expiresAt = block.timestamp + 30, grantId = H(pbcRequestId, KSSC, dbcChainId); one
              AccessLog(allowed) for that gid; the original PSC request stays FORWARDED (1).

Usage: .venv/bin/python -I ledger/tools/review_subject_evidence.py <evidence run dir> > out.json
Exit 0 iff every row passes. Reads public evidence only; writes nothing.
"""

import json
import sys
from pathlib import Path

from eth_abi import decode, encode
from eth_utils import keccak, to_checksum_address

ROOT = Path(__file__).resolve().parents[2]
ABI = {c: json.loads((ROOT / f"ledger/exports/abi/{c}.json").read_text()) for c in ("ACSC", "KSSC", "PSC")}
REJECTED = "0xf73a052c"
WRONG_SUBJECT = 2
GRANT_TTL = 30


def _type(i):
    if i["type"].startswith("tuple"):
        return "(" + ",".join(_type(c) for c in i["components"]) + ")" + i["type"][5:]
    return i["type"]


def function(contract, name):
    (f,) = [f for f in ABI[contract] if f.get("type") == "function" and f["name"] == name]
    types = [_type(i) for i in f["inputs"]]
    sel = "0x" + keccak(text=f"{name}({','.join(types)})")[:4].hex()
    return sel, types, f


def event_topic(contract, name):
    (e,) = [e for e in ABI[contract] if e.get("type") == "event" and e["name"] == name]
    return "0x" + keccak(text=f"{name}({','.join(_type(i) for i in e['inputs'])})").hex(), e


def decode_event(contract, name, log):
    _, e = event_topic(contract, name)
    idx = [i for i in e["inputs"] if i.get("indexed")]
    non = [i for i in e["inputs"] if not i.get("indexed")]
    vals = dict(zip([i["name"] for i in non], decode([_type(i) for i in non], bytes.fromhex(log["data"][2:]))))
    for i, t in zip(idx, log["topics"][1:]):
        vals[i["name"]] = decode([_type(i)], bytes.fromhex(t[2:]))[0]
    return vals


def load(p):
    return json.loads(Path(p).read_text())


def check(cond, msg, failures):
    if not cond:
        failures.append(msg)
    return cond


def norm(v):
    return v.lower() if isinstance(v, str) else v


def review_row(row_dir):
    row = row_dir.name
    sub = row_dir / "subject-stress/subject-substitution"
    inst = load(row_dir / "subject-instance/deployment.json")
    tx = load(sub / "substituted-transaction.json")
    call = load(sub / "public-call.json")
    before, after, res = load(sub / "before.json"), load(sub / "after.json"), load(sub / "result.json")
    f = []
    acsc = inst["chains"]["dbc"]["contracts"]["ACSC"].lower()
    kssc = inst["chains"]["dbc"]["contracts"]["KSSC"].lower()
    check(tx["to"].lower() == acsc, "substituted tx targets the D2 ACSC", f)
    orig = call["originalRequest"]
    out = {"row": row, "txHash": tx["hash"], "method": call["method"]}
    if call["method"] == "consumeDecision":
        sel, types, _ = function("ACSC", "consumeDecision")
        check(tx["input"][:10] == sel, "consumeDecision selector", f)
        req, cert, recs = decode(types, bytes.fromhex(tx["input"][10:]))
        fields = list(orig.keys())
        got = dict(zip(fields, req))
        diff = [k for k in fields if str(norm(got[k] if not isinstance(got[k], bytes) else "0x" + got[k].hex())).lower() != str(norm(orig[k])).lower()]
        out.update(substitutedGid=got["gid"], originalGid=orig["gid"], differingFields=diff)
        check(diff == ["gid"], f"only gid differs (got {diff})", f)
        dec = cert[0]
        check("0x" + dec[0].hex() == call["prepared"]["requestDigest"].lower(), "certificate is for the original request digest", f)
        code = int(res.get("rejectionCode", -1))
        out.update(rejectionCode=code, error=res.get("error"))
        check(code == WRONG_SUBJECT and res.get("error") == "WRONG_SUBJECT", "Rejected(2) WRONG_SUBJECT", f)
        for k in ("grant", "request", "nonceAlice", "nonceBob", "accessLogCount", "logs"):
            check(before[k] == after[k], f"{k} unchanged", f)
        check(after["grant"]["exists"] in (False, "False"), "no grant", f)
        check(str(after["request"]["status"]) == "1", "original request still FORWARDED", f)
    else:
        sel, types, _ = function("ACSC", "policyEnf")
        check(tx["input"][:10] == sel, "policyEnf selector", f)
        fwd, recs = decode(types, bytes.fromhex(tx["input"][10:]))
        _, _, fn = function("ACSC", "policyEnf")
        names = [c["name"] for c in fn["inputs"][0]["components"]]
        fwdd = dict(zip(names, fwd))
        out.update(substitutedGid=fwdd["gid"], originalGid=orig["gid"])
        check(fwdd["gid"].lower() != orig["gid"].lower(), "gid substituted", f)
        # The evidence stores DBC logs already decoded by agent 3's decoder ({name, fields}); this
        # review re-derives every checked value from the raw calldata and the tx block timestamp.
        new_dbc = after["logs"]["dbc"][len(before["logs"]["dbc"]):]
        check(after["logs"]["dbc"][:len(before["logs"]["dbc"])] == before["logs"]["dbc"], "prior DBC logs unchanged", f)
        grants = [l["fields"] for l in new_dbc if l.get("name") == "GrantIssued"]
        access = [l["fields"] for l in new_dbc if l.get("name") == "AccessLog"]
        check(len(new_dbc) == 2 and len(grants) == 1 and len(access) == 1, f"exactly one GrantIssued and one AccessLog (got {[l.get('name') for l in new_dbc]})", f)
        if grants:
            g = grants[0]
            a = access[0] if access else {}
            gid = g.get("gid")
            ts = int(tx.get("blockTimestamp", "0x0"), 16)
            exp = int(g.get("expiresAt"))
            rk = g.get("recipientKeyHash")
            out.update(grantGid=gid, grantExpiresAt=exp, blockTimestamp=ts, recipientKeyHash="0x" + rk.hex() if isinstance(rk, bytes) else rk,
                       nonceConsumed=g.get("nonceConsumed"), accessAllowed=a.get("allowed"), accessGid=a.get("gid"))
            check(gid.lower() == fwdd["gid"].lower(), "grant to substituted gid", f)
            check(exp == ts + GRANT_TTL, "grant expiry = policyEnf block + 30 s", f)
            check(rk in (b"\x00" * 32, "0x" + "00" * 32), "native recipient zero", f)
            check(g.get("nonceConsumed") in (False, None), "paper grant does not consume a nonce", f)
            check(a.get("allowed") is True and a.get("gid", "").lower() == fwdd["gid"].lower(), "AccessLog allowed for substituted gid", f)
            # HMBCHash.grantId = keccak256(abi.encode(requestDigest, kssc, destinationChainId)) (ProtocolTypes.sol:447)
            gid_expected = "0x" + keccak(encode(["bytes32", "address", "uint256"],
                                                [bytes.fromhex(fwdd_ref(fwdd)[2:]), to_checksum_address(kssc), int(inst["chains"]["dbc"]["chainId"])])).hex()
            logged = g.get("grantId")
            logged = "0x" + logged.hex() if isinstance(logged, bytes) else logged
            out.update(grantIdRecomputed=gid_expected, grantIdLogged=logged)
            check(logged == gid_expected, "grantId = H(pbcRequestId, KSSC, dbcChainId), independent of gid", f)
        check(str(after["request"]["status"]) == "1", "original request still FORWARDED", f)
        check(after["nonceAlice"] == before["nonceAlice"] and after["nonceBob"] == before["nonceBob"], "nonces unchanged", f)
    out["failures"] = f
    out["pass"] = not f
    return out


def fwdd_ref(fwdd):
    v = fwdd["pbcRequestId"]
    return "0x" + v.hex() if isinstance(v, bytes) else v


def main():
    run = Path(sys.argv[1])
    rows = sorted(p for p in run.glob("*-subject-substitution/*") if p.is_dir())
    results = [review_row(r) for r in rows]
    json.dump({"reviewer": "agent-1 (ledger scope, solo correlated)", "rows": results}, sys.stdout, indent=1, default=str)
    sys.exit(0 if results and all(r["pass"] for r in results) else 1)


if __name__ == "__main__":
    main()
