"""Needs eth-account 0.14.0 (protocol/requirements.txt) and the E protocol encoder protocol/hmbc_protocol/eip712.py (production E code, imported read-only).
1. witness label -> address derivation; 2. the six signing vectors: digest recomputed with eip712.digest, every signature recovered, ascending/distinct/set members;
3. every report, certificate and outcome address in the 12 wire examples and the 4 success vectors recovered under the HMBCState domain: report signers equal the reporting
witness, certificate signers sorted and distinct, submittedSigners equals the recovered signers, adopted.message equals the certificate message, adopted.reporters equal the
consistent reporters of that message, failures submit no signer."""
import copy, json, os, sys
from common import *
sys.path.insert(0, os.path.join(REPO, "protocol"))
from hmbc_protocol import eip712, keys
from eth_account import Account
root = proposal(sys.argv)
wit = load(root, "vectors/witnesses.json")["witnesses"]; ADDR = {w["index"]: w["address"].lower() for w in wit}
bad = []; n = 0
def chk(cond, what):
    global n; n += 1
    if not cond: bad.append(what)
for w in wit: chk(Account.from_key(keys.synthetic_private_key(w["label"])).address.lower() == w["address"].lower(), "derivation " + w["label"])
sgs = load(root, "vectors/signing.json")["vectors"]
for i, v in enumerate(sgs):
    dig = eip712.digest(v["typedData"]); chk("0x" + dig.hex() == v["digest"], "signing %d digest" % i)
    rec = [eip712.recover(dig, s["signature"]).lower() for s in v["signatures"]]
    chk(rec == [s["signer"].lower() for s in v["signatures"]], "signing %d recovered == claimed" % i)
    chk(rec == sorted(rec) and len(set(rec)) == 3 and all(r in ADDR.values() for r in rec), "signing %d ascending/distinct/members" % i)
cpt = [v for v in sgs if v["name"] == "StateCheckpoint"][0]["typedData"]
def rec(msg, sig):
    td = copy.deepcopy(cpt); td["message"] = msg; return eip712.recover(eip712.digest(td), sig).lower()
for i, r in enumerate(load(root, "vectors/wire.json")["responses"], 1):
    res, err = r.get("result"), r.get("error")
    col = (res or {}).get("collection") if res else (err or {}).get("collection")
    if err and "recorded" in err: chk(rec(err["recorded"]["message"], err["recorded"]["signature"]) in ADDR.values(), "ex%d recorded signer is a witness" % i)
    if not col: continue
    for k in ("recordedReports", "lateReports"):
        for x in col.get(k, []): chk(rec(x["message"], x["signature"]) == ADDR[x["witnessIndex"]], "ex%d %s witness %s" % (i, k, x["witnessIndex"]))
    for e in col.get("inconsistentReports", []):
        for x in e["reports"]: chk(rec(x["message"], x["signature"]) == ADDR[e["witnessIndex"]], "ex%d inconsistent witness %s" % (i, e["witnessIndex"]))
    for o in col["outcomes"]: chk(o["witness"].lower() == ADDR[o["witnessIndex"]], "ex%d outcome %s address" % (i, o["witnessIndex"]))
    if res:
        cp = res["checkpoint"]; sg = [rec(cp, s) for s in res["signatures"]]
        chk(len(sg) == 3 and len(set(sg)) == 3 and sg == sorted(sg) and all(s in ADDR.values() for s in sg), "ex%d certificate: 3 distinct sorted members" % i)
        chk([s.lower() for s in col["submittedSigners"]] == sg, "ex%d submittedSigners == recovered" % i)
        if "adopted" in col: chk(col["adopted"]["message"] == cp, "ex%d certificate message == adopted.message" % i)
    else: chk(col["submittedSigners"] == [], "ex%d failure submits no signer" % i)
    if "adopted" in col:
        rep = sorted(x["witnessIndex"] for x in col["recordedReports"] if x["message"] == col["adopted"]["message"])
        chk(rep == col["adopted"]["reporters"], "ex%d adopted.reporters == consistent reporters of that message" % i)
for j, x in enumerate(load(root, "vectors/success.json"), 1):
    if x["operation"] == "collect_checkpoint":
        r = x["response"]["result"]; sg = [rec(r["checkpoint"], s) for s in r["signatures"]]
        chk(sg == sorted(sg) and len(set(sg)) == 3, "success %d certificate sorted/distinct" % j)
        chk([a.lower() for a in r["collection"]["submittedSigners"]] == sg, "success %d submittedSigners == recovered" % j)
print("checks run: %d | failures: %d" % (n, len(bad))); [print("  FAIL", b) for b in bad]; sys.exit(1 if bad else 0)
