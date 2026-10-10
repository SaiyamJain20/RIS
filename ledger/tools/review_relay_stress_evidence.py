"""Agent 1 ledger-scope review of E01 relay-stress (SL2) live evidence (solo phase).

Independent of agent 3's oracle (evaluation/oracles/provenance.py): every checked value is
re-derived from the raw native records the evaluator kept (<instance>/{pbc,dbc}-native/
transactions.json: calldata, receipts with raw logs, block timestamps, debug-trace return
values) using the ledger's own exported ABIs (ledger/exports/abi) and the EIP-712 type
strings / grantId rule in ledger/src/types/ProtocolTypes.sol. Signatures are recovered with
SigLib's canonical rules (65 bytes, v in {27, 28}, 0 < s <= n/2, r != 0).

  forged-tuple        paper-*     policyEnf with the fixed fabricated reference, which no PBC
                                  transaction or log contains, issues one grant (recipient 0,
                                  TTL block + 30 s, no nonce) and one allowed AccessLog.
                      repaired-e  the mined certificate carries the honest decision bytes and a
                                  signature recovering (under the HMBCDecision/KSSC digest) to the
                                  relay, not a witness; DV steps 1-5 hold for the request, so the
                                  revert is Rejected(BAD_SIGNATURE=1) at step 6; state unchanged.
  new-reference-replay paper-*    a second policyEnf of the same verified tuple under the fixed
                                  fresh reference issues a second grant; the first stays.
                      repaired-e  calldata identical to the granted original reverts REPLAY (8)
                                  (same grantId, KSSC.sol:180); state unchanged.
  same-nonce-distinct-digests     two requests equal except expiresAt (same gid, nonce 1) have
                      repaired-e  distinct digests/grantIds; both witness certificates name the one
                                  accepted checkpoint; the first consume grants and consumes
                                  (alice, 1); the second, mined before both expiries, reverts
                                  REPLAY (8) at the nonce guard (KSSC.sol:181-183).

Usage: .venv/bin/python -I ledger/tools/review_relay_stress_evidence.py <evidence run dir> > out.json
Exit 0 iff at least one row was found and every row passes. Reads public evidence only.
"""

import json
import sys
from pathlib import Path

from eth_abi import decode, encode
from eth_keys import keys
from eth_utils import keccak, to_checksum_address

ROOT = Path(__file__).resolve().parents[2]
ABI = {c: json.loads((ROOT / f"ledger/exports/abi/{c}.json").read_text()) for c in ("ACSC", "KSSC", "PSC", "LSC")}
REJECTED = "f73a052c"
CODES = {"BAD_SIGNATURE": 1, "REPLAY": 8}
GRANT_TTL = 30
HALF_ORDER = 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0
FORGED_REF = "0x" + keccak(text="HMBC.E01.forged-tuple.pbcRequestId.v1").hex()
FRESH_REF = "0x" + keccak(text="HMBC.E01.new-reference.pbcRequestId.v1").hex()

# ProtocolTypes.sol HMBCHash (pin 933d2a7).
DOMAIN_T = keccak(text="EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)")
REQUEST_T = keccak(text="AccessRequest(uint256 sourceChainId,uint256 destinationChainId,address psc,address kssc,address gid,"
                        "bytes32 dataId,uint8 action,uint64 policyVersion,uint64 authEpoch,uint64 keyEpoch,uint256 nonce,"
                        "uint64 expiresAt,bytes32 recipientKeyHash)")
DECISION_T = keccak(text="AccessDecision(bytes32 requestDigest,uint8 result,bytes32 credentialDigest,uint64 stateSequence,"
                         "uint64 witnessSetVersion,uint256 sourceBlockNumber,bytes32 sourceBlockHash,uint64 expiresAt)")
REQUEST_FIELDS = ("sourceChainId", "destinationChainId", "psc", "kssc", "gid", "dataId", "action", "policyVersion",
                  "authEpoch", "keyEpoch", "nonce", "expiresAt", "recipientKeyHash")
REQUEST_TYPES = ("uint256", "uint256", "address", "address", "address", "bytes32", "uint8", "uint64", "uint64", "uint64",
                 "uint256", "uint64", "bytes32")
DECISION_FIELDS = ("requestDigest", "result", "credentialDigest", "stateSequence", "witnessSetVersion", "sourceBlockNumber",
                   "sourceBlockHash", "expiresAt")
DECISION_TYPES = ("bytes32", "uint8", "bytes32", "uint64", "uint64", "uint256", "bytes32", "uint64")


def _type(i):
    if i["type"].startswith("tuple"):
        return "(" + ",".join(_type(c) for c in i["components"]) + ")" + i["type"][5:]
    return i["type"]


def _names(i):
    """Nested field names for a (possibly tuple) ABI input."""
    if i["type"].startswith("tuple"):
        return {"_": i["name"], "c": [_names(c) for c in i["components"]], "array": i["type"].endswith("]")}
    return i["name"]


def _named(spec, value):
    if isinstance(spec, dict):
        if spec["array"]:
            return [_named(dict(spec, array=False), v) for v in value]
        return {(c["_"] if isinstance(c, dict) else c): _named(c, v) for c, v in zip(spec["c"], value)}
    return value


def function(contract, name):
    (f,) = [f for f in ABI[contract] if f.get("type") == "function" and f["name"] == name]
    types = [_type(i) for i in f["inputs"]]
    return "0x" + keccak(text=f"{name}({','.join(types)})")[:4].hex(), types, f


def decode_call(contract, name, data):
    sel, types, f = function(contract, name)
    if data[:10] != sel:
        raise ValueError(f"selector {data[:10]} is not {contract}.{name}")
    values = decode(types, bytes.fromhex(data[10:]))
    return [_named(_names(i), v) for i, v in zip(f["inputs"], values)]


EVENTS = {}
for _c in ("ACSC", "KSSC", "PSC", "LSC"):
    for _e in ABI[_c]:
        if _e.get("type") == "event":
            EVENTS["0x" + keccak(text=f"{_e['name']}({','.join(_type(i) for i in _e['inputs'])})").hex()] = (_c, _e)


def decode_log(log):
    contract, e = EVENTS[log["topics"][0]]
    idx = [i for i in e["inputs"] if i.get("indexed")]
    non = [i for i in e["inputs"] if not i.get("indexed")]
    vals = dict(zip([i["name"] for i in non], decode([_type(i) for i in non], bytes.fromhex(log["data"][2:]))))
    for i, t in zip(idx, log["topics"][1:]):
        vals[i["name"]] = decode([_type(i)], bytes.fromhex(t[2:]))[0]
    return dict(contract=contract, name=e["name"], address=log["address"].lower(), fields=vals)


def h(b):
    return "0x" + b.hex() if isinstance(b, (bytes, bytearray)) else (b.lower() if isinstance(b, str) else b)


def domain(name, chain_id, contract):
    return keccak(encode(["bytes32", "bytes32", "bytes32", "uint256", "address"],
                         [DOMAIN_T, keccak(text=name), keccak(text="1"), int(chain_id), to_checksum_address(contract)]))


def typed(dom, struct):
    return keccak(b"\x19\x01" + dom + struct)


def request_digest(r):
    struct = keccak(encode(("bytes32",) + REQUEST_TYPES, [REQUEST_T] + [r[k] for k in REQUEST_FIELDS]))
    return typed(domain("HMBCRequest", r["sourceChainId"], r["psc"]), struct)


def decision_digest(d, dbc_chain_id, kssc):
    struct = keccak(encode(("bytes32",) + DECISION_TYPES, [DECISION_T] + [d[k] for k in DECISION_FIELDS]))
    return typed(domain("HMBCDecision", dbc_chain_id, kssc), struct)


def grant_id(ref, kssc, dbc_chain_id):
    ref = bytes.fromhex(ref[2:]) if isinstance(ref, str) else ref
    return "0x" + keccak(encode(["bytes32", "address", "uint256"], [ref, to_checksum_address(kssc), int(dbc_chain_id)])).hex()


def recover(digest, sig):
    """SigLib.tryRecover: zero address for any non-canonical signature."""
    if len(sig) != 65:
        return None
    r, s, v = int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:64], "big"), sig[64]
    if v not in (27, 28) or s > HALF_ORDER or s == 0 or r == 0:
        return None
    return keys.Signature(vrs=(v - 27, r, s)).recover_public_key_from_msg_hash(digest).to_checksum_address().lower()


def load(p):
    return json.loads(Path(p).read_text())


def rejection(tx):
    rv = (tx.get("rejectionTrace") or {}).get("returnValue", "")
    if tx["receipt"]["status"] != "0x0" or not rv.startswith("0x" + REJECTED) or len(rv) != 74:
        return None
    return int(rv[10:], 16)


class Review:
    def __init__(self, row_dir):
        self.row = row_dir
        self.f = []
        inst = row_dir / "relay-instance"
        self.dep = load(inst / "deployment.json")
        self.boot = load(inst / "bootstrap-checked.json")
        self.dbc_txs = load(inst / "dbc-native/transactions.json")
        self.pbc_txs = load(inst / "pbc-native/transactions.json")
        stress = row_dir / "relay-stress"
        self.result = load(stress / "result.json")
        self.stress_hash = load(stress / "stress-transaction.json")["hash"]
        self.before = load(stress / ("before.json" if (stress / "before.json").exists() else "before-second.json"))
        self.after = load(stress / ("after.json" if (stress / "after.json").exists() else "after-second.json"))
        self.stress_dir = stress
        dbc = self.dep["chains"]["dbc"]
        self.dbc_id, self.pbc_id = int(dbc["chainId"]), int(self.dep["chains"]["pbc"]["chainId"])
        self.acsc, self.kssc = dbc["contracts"]["ACSC"].lower(), dbc["contracts"]["KSSC"].lower()
        self.psc = self.dep["chains"]["pbc"]["contracts"]["PSC"].lower()
        self.relay = self.dep["fixture"]["relay"]["address"].lower()
        self.witnesses = [w.lower() for w in self.dep["fixture"].get("witnessSet", {}).get("witnesses", [])]
        self.alice = self.boot["users"]["alice"]["gid"].lower()
        (self.stress,) = [t for t in self.dbc_txs if t["transactionHash"] == self.stress_hash]
        self.ts = int(self.stress["receipt"]["blockTimestamp"]) if isinstance(self.stress["receipt"]["blockTimestamp"], int) \
            else int(self.stress["receipt"]["blockTimestamp"], 16)
        self.out = dict(row=row_dir.parent.name, profile=self.dep["profile"], variant=self.result["variant"],
                        stressTx=self.stress_hash, stressBlockTimestamp=self.ts)

    def check(self, cond, msg):
        if not cond:
            self.f.append(msg)
        return cond

    def relay_call(self, tx, name):
        self.check(tx["address"].lower() == self.acsc and tx["receipt"]["to"].lower() == self.acsc, f"{name} targets the D2 ACSC")
        self.check(tx["sender"].lower() == self.relay and tx["receipt"]["from"].lower() == self.relay, f"{name} sent by the configured relay")
        return decode_call("ACSC", name, tx["transaction"]["input"])

    def logs(self, tx):
        return [decode_log(l) for l in tx["receipt"]["logs"]]

    def unchanged(self):
        for k in ("grants", "requests", "nonces", "accessLogCount", "logs"):
            self.check(self.before[k] == self.after[k], f"{k} unchanged by the stress transaction")

    def pbc_requests(self):
        """Request digests of every PSC.requestAccess the relay mined on the D2 PBC."""
        out = []
        for t in self.pbc_txs:
            if t.get("contractRole") == "PSC" and t.get("method") == "requestAccess":
                (req, _sig, _bundle) = decode_call("PSC", "requestAccess", t["transaction"]["input"])
                out.append(dict(tx=t, request=req, digest=h(request_digest(req))))
        return out

    def paper_grant(self, tx, ref, gid):
        logs = self.logs(tx)
        self.check(tx["receipt"]["status"] == "0x1", "policyEnf mined with status 1")
        self.check([(l["contract"], l["name"]) for l in logs] == [("KSSC", "GrantIssued"), ("ACSC", "AccessLog")],
                   f"exactly GrantIssued then AccessLog (got {[l['name'] for l in logs]})")
        if len(logs) != 2:
            return None
        g, a = logs[0]["fields"], logs[1]["fields"]
        ts = int(tx["receipt"]["blockTimestamp"]) if isinstance(tx["receipt"]["blockTimestamp"], int) else int(tx["receipt"]["blockTimestamp"], 16)
        gid_expected = grant_id(ref, self.kssc, self.dbc_id)
        self.check(logs[0]["address"] == self.kssc and logs[1]["address"] == self.acsc, "events emitted by the D2 KSSC / ACSC")
        self.check(h(g["grantId"]) == gid_expected, "grantId = H(reference, KSSC, dbcChainId) (ProtocolTypes.sol:447)")
        self.check(h(g["requestDigest"]) == ref.lower(), "grant names the relay reference")
        self.check(h(g["gid"]) == gid, "grant to the tuple gid")
        self.check(int(g["expiresAt"]) == ts + GRANT_TTL, "paper grant expiry = policyEnf block + 30 s (ACSC.sol:154)")
        self.check(h(g["recipientKeyHash"]) == "0x" + "00" * 32 and g["nonceConsumed"] is False and int(g["nonce"]) == 0,
                   "native recipient 0, no nonce consumed")
        self.check(a["allowed"] is True and int(a["code"]) == 0 and h(a["grantId"]) == gid_expected
                   and h(a["submitter"]) == self.relay and h(a["requestRef"]) == ref.lower(), "AccessLog allowed for the relay reference")
        return dict(grantId=gid_expected, expiresAt=int(g["expiresAt"]), blockTimestamp=ts)

    def forged(self):
        if self.dep["profile"] != "repaired-e":
            fwd, recs = self.relay_call(self.stress, "policyEnf")
            ref = h(fwd["pbcRequestId"])
            self.check(ref == FORGED_REF, "reference is the fixed fabricated value")
            self.check(h(fwd["gid"]) == self.alice and int(fwd["action"]) == 1, "Alice READ tuple")
            seen = [r["digest"] for r in self.pbc_requests()]
            self.check(ref not in seen, "no PBC requestAccess has this digest")
            raw = ref[2:]
            self.check(not any(raw in json.dumps(t["receipt"]["logs"]).lower() for t in self.pbc_txs), "no PBC log mentions the reference")
            self.check(self.before["requests"][ref]["status"] == "0" and self.after["requests"][ref]["status"] == "0",
                       "PSC.getRequest(reference) NONE before and after")
            self.out.update(reference=ref, pbcRequests=len(seen), grant=self.paper_grant(self.stress, ref, self.alice))
            return
        req, cert, recs = self.relay_call(self.stress, "consumeDecision")
        dec, sigs = cert["decision"], cert["signatures"]
        rd = request_digest(req)
        self.check(int(req["sourceChainId"]) == self.pbc_id and int(req["destinationChainId"]) == self.dbc_id, "DV 1-2 source/destination")
        self.check(h(req["kssc"]) == self.kssc and h(req["psc"]) == self.psc, "request binds the D2 PSC/KSSC")
        self.check(int(req["action"]) == 1, "DV 3 action READ")
        self.check(h(dec["requestDigest"]) == h(rd), "DV 4 decision binds the request digest")
        self.check(int(dec["witnessSetVersion"]) == 1, "DV 5 witness-set version 1")
        dd = decision_digest(dec, self.dbc_id, self.kssc)
        signers = [recover(dd, s) for s in sigs]
        self.check(len(sigs) == 1 and signers[0] == self.relay and signers[0] not in self.witnesses,
                   "mined signature recovers (HMBCDecision/KSSC digest) to the relay, outside the witness set")
        honest = load(self.stress_dir / "public-call.json")["honestArguments"][1]
        honest_dec = {k: (int(v) if k in ("result", "stateSequence", "witnessSetVersion", "sourceBlockNumber", "expiresAt")
                          else bytes.fromhex(v[2:])) for k, v in honest["decision"].items()}
        self.check(honest_dec == dec, "mined decision bytes equal the honest witness decision")
        honest_signer = recover(decision_digest(honest_dec, self.dbc_id, self.kssc), bytes.fromhex(honest["signatures"][0][2:]))
        self.check(honest_signer in self.witnesses, "honest signature recovers to the witness under the same digest")
        self.check(h(sigs[0]) != honest["signatures"][0].lower(), "only the signature differs")
        code = rejection(self.stress)
        self.check(code == CODES["BAD_SIGNATURE"] and self.stress["receipt"]["logs"] == [], "Rejected(BAD_SIGNATURE=1), no logs")
        real = [r for r in self.pbc_requests() if r["digest"] == h(rd)]
        self.check(len(real) == 1, "disclosed: the repaired row's request was really forwarded on the PBC (A1-0065)")
        gid_ = grant_id(rd, self.kssc, self.dbc_id)
        self.check(self.after["grants"][gid_]["exists"] is False, "no grant for the request")
        self.unchanged()
        self.out.update(requestDigest=h(rd), decisionDigest=h(dd), minedSigner=signers[0], honestSigner=honest_signer,
                        witnesses=self.witnesses, rejectionCode=code, realPbcRequest=len(real) == 1)

    def new_reference(self):
        idx = self.dbc_txs.index(self.stress)
        if self.dep["profile"] != "repaired-e":
            fwd, recs = self.relay_call(self.stress, "policyEnf")
            prior = [t for t in self.dbc_txs[:idx] if t.get("method") == "policyEnf"]
            self.check(len(prior) == 1, "one original policyEnf before the replay")
            ofwd, orecs = self.relay_call(prior[-1], "policyEnf")
            reqs = self.pbc_requests()
            self.check(len(reqs) == 1 and h(ofwd["pbcRequestId"]) == reqs[0]["digest"], "original tuple names the real forwarded request")
            ref = h(fwd["pbcRequestId"])
            self.check(ref == FRESH_REF and ref not in [r["digest"] for r in reqs], "replay reference is the fixed fresh value, unseen by the PBC")
            self.check({k: v for k, v in fwd.items() if k != "pbcRequestId"} == {k: v for k, v in ofwd.items() if k != "pbcRequestId"}
                       and recs == orecs, "replay differs from the original only in pbcRequestId")
            first = self.paper_grant(prior[-1], h(ofwd["pbcRequestId"]), self.alice)
            second = self.paper_grant(self.stress, ref, self.alice)
            self.check(first and second and first["grantId"] != second["grantId"], "second, distinct grant")
            if first:
                self.check(self.after["grants"][first["grantId"]] == self.before["grants"][first["grantId"]], "original grant unchanged")
            self.out.update(originalRef=h(ofwd["pbcRequestId"]), replayRef=ref, originalGrant=first, replayGrant=second)
            return
        prior = [t for t in self.dbc_txs[:idx] if t.get("method") == "consumeDecision"]
        self.check(len(prior) == 1, "one original consumeDecision before the replay")
        orig = prior[-1]
        self.check(orig["transaction"]["input"] == self.stress["transaction"]["input"] and orig["transactionHash"] != self.stress_hash,
                   "replay calldata identical to the granted original, distinct transaction")
        req, cert, _ = self.relay_call(self.stress, "consumeDecision")
        rd = request_digest(req)
        signer = recover(decision_digest(cert["decision"], self.dbc_id, self.kssc), cert["signatures"][0])
        self.check(signer in self.witnesses, "certificate signed by the witness")
        gid_ = grant_id(rd, self.kssc, self.dbc_id)
        olog = self.logs(orig)
        self.check(orig["receipt"]["status"] == "0x1" and [h(l["fields"]["grantId"]) for l in olog if l["name"] == "GrantIssued"] == [gid_],
                   "original granted grantId = H(requestDigest, KSSC, dbcChainId)")
        code = rejection(self.stress)
        self.check(code == CODES["REPLAY"] and self.stress["receipt"]["logs"] == [], "Rejected(REPLAY=8), no logs")
        self.check(self.before["grants"][gid_]["exists"] is True, "grant already existed (KSSC.sol:180 is the firing guard)")
        self.unchanged()
        self.out.update(requestDigest=h(rd), grantId=gid_, rejectionCode=code)

    def same_nonce(self):
        idx = self.dbc_txs.index(self.stress)
        consumes = [t for t in self.dbc_txs[:idx] if t.get("method") == "consumeDecision"]
        self.check(len(consumes) == 1, "exactly one consume before the stress")
        first_tx = consumes[-1]
        r1, c1, _ = self.relay_call(first_tx, "consumeDecision")
        r2, c2, _ = self.relay_call(self.stress, "consumeDecision")
        diff = [k for k in REQUEST_FIELDS if r1[k] != r2[k]]
        self.check(diff == ["expiresAt"] and int(r1["nonce"]) == 1 and h(r1["gid"]) == self.alice, f"requests differ only in expiresAt (got {diff})")
        d1, d2 = request_digest(r1), request_digest(r2)
        g1, g2 = grant_id(d1, self.kssc, self.dbc_id), grant_id(d2, self.kssc, self.dbc_id)
        self.check(d1 != d2 and g1 != g2, "distinct digests and grantIds")
        for c, d in ((c1, d1), (c2, d2)):
            self.check(h(c["decision"]["requestDigest"]) == h(d), "certificate binds its own request")
            self.check(recover(decision_digest(c["decision"], self.dbc_id, self.kssc), c["signatures"][0]) in self.witnesses,
                       "certificate signed by the witness")
        self.check(c1["decision"]["stateSequence"] == c2["decision"]["stateSequence"]
                   and c1["decision"]["sourceBlockNumber"] == c2["decision"]["sourceBlockNumber"], "both certificates name one checkpoint")
        accepts = [t for t in self.dbc_txs[:idx] if t.get("method") == "acceptState"]
        self.check(len(accepts) == 1 and self.dbc_txs.index(accepts[0]) < self.dbc_txs.index(first_tx), "one checkpoint accepted before both consumes")
        reqs = {r["digest"]: r for r in self.pbc_requests()}
        self.check(h(d1) in reqs and h(d2) in reqs, "both requests forwarded on the PBC")
        if accepts and h(d2) in reqs:
            (cp, _sigs) = decode_call("KSSC", "acceptState", accepts[0]["transaction"]["input"])
            pblock = int(reqs[h(d2)]["tx"]["receipt"]["blockNumber"], 16)
            self.check(int(cp["sequence"]) == int(c2["decision"]["stateSequence"]) and int(cp["sourceBlockNumber"]) >= pblock,
                       "checkpoint after the second forward, named by both certificates")
        flogs = self.logs(first_tx)
        grants = [l["fields"] for l in flogs if l["name"] == "GrantIssued"]
        self.check(first_tx["receipt"]["status"] == "0x1" and len(grants) == 1 and h(grants[0]["grantId"]) == g1
                   and grants[0]["nonceConsumed"] is True and int(grants[0]["nonce"]) == 1, "first consume grants and consumes (alice, 1)")
        code = rejection(self.stress)
        self.check(code == CODES["REPLAY"] and self.stress["receipt"]["logs"] == [], "second consume Rejected(REPLAY=8), no logs")
        expiry = min(int(r2["expiresAt"]), int(c2["decision"]["expiresAt"]))
        self.check(self.ts < expiry and self.ts < int(r1["expiresAt"]), "second consume mined before both expiries (not EXPIRED)")
        self.check(self.before["grants"][g2]["exists"] is False, "no grant for the second digest (KSSC.sol:180 passes)")
        self.check([self.alice, "1", True] in [[n[0].lower(), str(n[1]), n[2]] for n in self.before["nonces"]],
                   "(alice, 1) already consumed before the second consume (KSSC.sol:182 fires)")
        self.check(self.after["grants"][g1] == self.before["grants"][g1], "first grant unchanged")
        self.unchanged()
        self.out.update(digests=[h(d1), h(d2)], grantIds=[g1, g2], rejectionCode=code, secondExpiry=expiry, marginSeconds=expiry - self.ts)

    def run(self):
        try:
            {"forged-tuple": self.forged, "new-reference-replay": self.new_reference,
             "same-nonce-distinct-digests": self.same_nonce}[self.out["variant"]]()
        except Exception as e:  # a review defect or malformed evidence is a failed row, never a pass
            self.f.append(f"review error: {type(e).__name__}: {e}")
        self.out.update(failures=self.f, **{"pass": not self.f})
        return self.out


def main():
    run = Path(sys.argv[1])
    rows = sorted(p.parent.parent for p in run.glob("*/*/relay-stress/result.json"))
    results = []
    for r in rows:
        try:
            results.append(Review(r).run())
        except Exception as e:  # missing or malformed evidence files: a failed row, never skipped
            results.append({"row": r.parent.name, "failures": [f"evidence error: {type(e).__name__}: {e}"], "pass": False})
    json.dump({"reviewer": "agent-1 (ledger scope, solo correlated)", "rows": results}, sys.stdout, indent=1, default=str)
    sys.exit(0 if results and all(r["pass"] for r in results) else 1)


if __name__ == "__main__":
    main()
