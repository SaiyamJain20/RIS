"""Differential check: agent 3's fault oracle (evaluation/oracles/faults.py, my READING of SIGNING-RULES section 6)
versus agent 2's real WitnessStore (durable SQLite store, synthetic keys). For each grid scenario the store is asked to
sign a second, different effect under one key after a first one; the caller claims the first death fact that is true
(the store re-checks it). Agreement = store accepts exactly when the oracle reports no violation.
Scope: pin-death logic only; one host; same-model author of both sides. Usage: python3 -I oracle_store_diff.py <protocol-root> <out.json>"""
import itertools, json, os, sys, tempfile
root = os.path.abspath(sys.argv[1]); out = sys.argv[2]
sys.dont_write_bytecode = True
here = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(root, "tests"), root, os.path.dirname(os.path.dirname(here))]
import test_witness_state as T                         # noqa: E402  (helpers only)
from hmbc_protocol import witness_state as ws          # noqa: E402
from evaluation.oracles import faults as F             # noqa: E402

CH = {"dbc": T.DBC, "pbc": T.PBC}
EXP = 1000

def effects(typ, which, dseq=4, result="1"):
    if typ == "StateCheckpoint":
        return T.cp_effect(138 if which == 0 else 139)
    if typ == "AccessDecision":
        return {"result": result if which == 0 else ("0" if result == "1" else "1"), "credentialDigest": T.h("c%d" % which), "stateSequence": str(dseq),
                "witnessSetVersion": "2", "sourceBlockNumber": "138", "sourceBlockHash": T.h("b138")}
    if typ == "GovernanceAction":
        return {"action": "1" if which == 0 else "2", "root": "0x" + "cc" * 20, "admins": [], "witnessSetVersion": "2"}
    return {"grantId": T.h("g%d" % which), "gid": "0x" + "dd" * 20, "dataId": T.h("d"), "keyEpoch": "0", "grantExpiresAt": "5000", "witnessSetVersion": "2",
            "dbcChainId": T.DBC, "kssc": "0x" + "ee" * 20, "dbcBlockNumber": "7", "dbcBlockHash": T.h("b7")}

DOM = {"StateCheckpoint": T.DOM_S, "AccessDecision": T.DOM_D, "GovernanceAction": "0x" + "a3" * 32, "GrantReceipt": "0x" + "a4" * 32}
KEY = {"StateCheckpoint": "10", "AccessDecision": T.h("req"), "GovernanceAction": "5", "GrantReceipt": T.h("req")}
SEQ = {"StateCheckpoint": 10, "AccessDecision": 4, "GovernanceAction": 5, "GrantReceipt": 0}   # the number the later observation is compared to

def scenario(typ, ts, observed, grant, outcome, result, tmp):
    st = ws.init_store(tmp, T.BIND, T.B, T.OWNER)
    chain = CH[ws.TARGET[typ]]
    exp = None if typ == "GrantReceipt" else str(EXP)
    st.sign(type=typ, domain=DOM[typ], wsv="2", key=KEY[typ], effect=effects(typ, 0, result=result), expires_at=exp, digest=T.h("first"), signer=T.signer,
            observe=lambda: T.obs(chain, 100, 50))
    # the oracle's facts for the later signing
    o = {"timestamp": ts, "sequence": observed, "nonce": observed, "grant_exists": grant, "outcome_recorded": outcome}
    first = {"witness": 0, "t": 1, "type": typ, "key": KEY[typ], "effect": "E0", "digest": "first", "expires_at": None if exp is None else int(exp),
             "seq": SEQ[typ], "result": "ALLOW" if result == "1" else "DENY", "obs": {"timestamp": 50, "sequence": 0, "nonce": 0, "grant_exists": False, "outcome_recorded": False}}
    second = {"witness": 0, "t": 2, "type": typ, "key": KEY[typ], "effect": "E1", "digest": "second", "expires_at": None if exp is None else int(exp) + 500,
              "seq": SEQ[typ], "result": "DENY" if result == "1" else "ALLOW", "obs": o}
    oracle_violation = bool(F.single_signing_violations([first, second]))
    # what an honest caller would claim: the first death fact that is true (the store re-checks it)
    over = None
    if typ == "StateCheckpoint" and observed >= SEQ[typ]: over = ("overtaken-checkpoint", str(observed))
    if typ == "GovernanceAction" and observed >= SEQ[typ]: over = ("overtaken-governance", str(observed))
    if typ == "AccessDecision":
        if observed > SEQ[typ]: over = ("overtaken-decision-sequence", str(observed))
        elif grant: over = ("overtaken-decision-grant", None)
    if typ == "GrantReceipt" and outcome: over = ("executed-receipt", None)
    try:
        st.sign(type=typ, domain=DOM[typ], wsv="2", key=KEY[typ], effect=effects(typ, 1, result=result), expires_at=None if exp is None else str(EXP + 500), digest=T.h("second"),
                signer=T.signer, observe=lambda: T.obs(chain, 101, ts), overtaken=over)
        accepted = True
    except ws.StoreError as e:
        accepted = False
        assert "CONFLICT_PINNED" in str(e), str(e)
    st.close()
    return accepted, oracle_violation

rows, mism = [], []
for typ in ws.TYPES:
    results = ("1", "0") if typ == "AccessDecision" else ("1",)
    for ts, observed, grant, outcome, result in itertools.product((EXP - 1, EXP, EXP + 1), (SEQ[typ] - 1, SEQ[typ], SEQ[typ] + 1), (False, True), (False, True), results):
        with tempfile.TemporaryDirectory() as tmp:
            acc, viol = scenario(typ, ts, observed, grant, outcome, result, tmp)
        rows.append({"type": typ, "ts": ts, "observed": observed, "grant": grant, "outcome": outcome, "earlier_result": result, "store_accepts": acc, "oracle_violation": viol})
        if acc == viol:
            mism.append(rows[-1])
summary = {"cases": len(rows), "agree": len(rows) - len(mism), "disagree": len(mism), "store_accepts": sum(r["store_accepts"] for r in rows),
           "oracle_violations": sum(r["oracle_violation"] for r in rows)}
json.dump({"summary": summary, "disagreements": mism, "rows": rows}, open(out, "w"), indent=1)
print(json.dumps(summary)); print(json.dumps(mism[:10], indent=1))
