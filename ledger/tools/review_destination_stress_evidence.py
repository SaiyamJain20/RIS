"""Agent 1 ledger-scope review of E01 wrong-destination and expiry-boundary (SL7) live evidence (solo phase).

Independent of agent 3's oracle (evaluation/oracles/destination.py): every checked value is re-derived from
the raw native records of the receiving deployment A (<row>/<profile>/destination-instance/{pbc,dbc}-native/
transactions.json) and, for wrong destination, of the source deployment B (<row>/<profile>/source-instance/
{pbc,dbc}-native/transactions.json), with the ledger ABIs and the ProtocolTypes.sol digests, reusing the
decoders of review_barrier_stress_evidence.py. DecisionVerifier steps 1-2 and 9 (DecisionVerifier.sol:60-64,
74) are replayed in Python on the mined calldata against A's deployment.

  wrong destination  B is another deployment on the same chain pair (same chain ids, other PSC/KSSC); one Alice
                     requestAccess on B's PSC, digest recomputed = AccessForwarded. A's PBC has no requestAccess
                     for that digest, and B's DBC has no consumeDecision/policyEnf.
                     paper-*: A's policyEnf carries pbcRequestId = B's digest and exactly B's forwarded records;
                     grant at A (grantId = H(B digest, A KSSC, DBC chain), recipient 0, block + 30, no nonce).
                     repaired: A's consumeDecision carries B's request (field-identical, unrewritten), B's records
                     and a decision witness-signed under B's HMBCDecision/KSSC domain; the replayed verifier first
                     fails at step 1 (r.psc is B's PSC); step 2 also mismatches; Rejected(3), no logs.
  expiry boundary    one Alice requestAccess on A; the consume block timestamp equals r.expiresAt exactly and every
                     earlier DBC transaction is below it.
                     paper-*: policyEnf grant with expiry r.expiresAt + 30 (block + grantTtl).
                     repaired: the decision is witness-signed under A's domain with d.expiresAt == r.expiresAt; the
                     current checkpoint expires later; the replayed verifier first fails at step 9 on equality;
                     Rejected(7), no logs.

Usage: .venv/bin/python -I ledger/tools/review_destination_stress_evidence.py <evidence run dir> > out.json
Exit 0 iff at least one row was found and every row passes. Reads public evidence only.
"""

import importlib.util
import json
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("rb", Path(__file__).with_name("review_barrier_stress_evidence.py"))
rb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rb)
rt, ra, rv = rb.rt, rb.ra, rb.rv

WRONG_DESTINATION, EXPIRED, GRANT_TTL = 3, 7, 30


class Instance:
    """One deployment's public records (A = destination-instance, B = source-instance)."""

    def __init__(self, inst):
        self.dep = rv.load(inst / "deployment.json")
        self.boot = rv.load(inst / "bootstrap-checked.json")
        self.pbc_txs = rv.load(inst / "pbc-native/transactions.json")
        dbc_path = inst / "dbc-native/transactions.json"
        self.dbc_txs = rv.load(dbc_path) if dbc_path.exists() else []
        p, d = self.dep["chains"]["pbc"], self.dep["chains"]["dbc"]
        self.pbc_id, self.dbc_id = int(p["chainId"]), int(d["chainId"])
        self.psc, self.tmsc = p["contracts"]["PSC"].lower(), p["contracts"]["TMSC"].lower()
        self.acsc, self.kssc = d["contracts"]["ACSC"].lower(), d["contracts"]["KSSC"].lower()
        self.relay = self.dep["fixture"]["relay"]["address"].lower()
        self.witnesses = [w.lower() for w in self.dep["fixture"].get("witnessSet", {}).get("witnesses", [])]
        self.policy_version = int(self.dep["fixture"]["policyVersion"])
        self.alice = self.boot["users"]["alice"]["gid"].lower()


def methods(txs, *names):
    return [t for t in txs if t.get("method") in names]


class Review:
    def __init__(self, row_dir):
        self.f = []
        self.stress_dir = row_dir / "destination-stress"
        self.result = rv.load(self.stress_dir / "result.json")
        self.a = Instance(row_dir / "destination-instance")
        self.b = Instance(row_dir / "source-instance") if (row_dir / "source-instance").exists() else None
        self.profile = self.a.dep["profile"]
        self.out = dict(row=row_dir.parent.name, profile=self.profile, variant=self.result["variant"])

    def check(self, cond, msg):
        if not cond:
            self.f.append(msg)
        return cond

    def request_on(self, inst, label):
        reqs = methods(inst.pbc_txs, "requestAccess")
        self.check(len(reqs) == 1 and reqs[0]["receipt"]["status"] == "0x1" and reqs[0]["sender"].lower() == inst.relay
                   and reqs[0]["address"].lower() == inst.psc, f"exactly one relay requestAccess mined on {label}'s PSC")
        req, _sig, _bundle = rv.decode_call("PSC", "requestAccess", reqs[0]["transaction"]["input"])
        digest = rv.h(rv.request_digest(req))
        fwd = [rv.decode_log(l)["fields"] for l in reqs[0]["receipt"]["logs"] if rv.decode_log(l)["name"] == "AccessForwarded"]
        self.check(len(fwd) == 1 and rv.h(fwd[0]["requestDigest"]) == digest, f"{label}: AccessForwarded for the recomputed digest")
        records = [rb.rec_tuple(r) for r in fwd[0]["verifiedAttributes"]] if fwd else []
        self.check(rb.credential_digest(records) == rv.h(fwd[0]["credentialDigest"]) if fwd else False, f"{label}: forwarded credentialDigest")
        self.check(rv.h(req["gid"]) == inst.alice and int(req["sourceChainId"]) == inst.pbc_id and rv.h(req["psc"]) == inst.psc
                   and int(req["destinationChainId"]) == inst.dbc_id and rv.h(req["kssc"]) == inst.kssc,
                   f"{label}: Alice request bound to {label}'s PBC/PSC and DBC/KSSC")
        return reqs[0], req, digest, records

    def stress(self):
        h = rv.load(self.stress_dir / "stress-transaction.json")["hash"]
        (t,) = [t for t in self.a.dbc_txs if t["transactionHash"] == h]
        self.check(t["sender"].lower() == self.a.relay and t["address"].lower() == self.a.acsc, "DBC call by the relay to A's ACSC")
        return t

    def paper_grant(self, s, digest, req_dataId, records, expect_expiry=None):
        fwd, attrs = rv.decode_call("ACSC", "policyEnf", s["transaction"]["input"])
        self.check(rv.h(fwd["pbcRequestId"]) == digest and rv.h(fwd["gid"]) == self.a.alice and rv.h(fwd["dataId"]) == rv.h(req_dataId)
                   and int(fwd["action"]) == 1, "policyEnf of the forwarded tuple (pbcRequestId = request digest)")
        self.check([rb.rec_tuple(x) for x in attrs] == records, "policyEnf carries exactly the forwarded records")
        ts = ra.ts_of(s)
        logs = [rv.decode_log(l) for l in s["receipt"]["logs"]]
        names = [l["name"] for l in logs]
        self.check(s["receipt"]["status"] == "0x1" and names == ["GrantIssued", "AccessLog"], f"paper grant mined (got {names})")
        if names[:1] == ["GrantIssued"]:
            g = logs[0]["fields"]
            self.check(rv.h(g["grantId"]) == rv.grant_id(digest, self.a.kssc, self.a.dbc_id) and int(g["expiresAt"]) == ts + GRANT_TTL
                       and rv.h(g["recipientKeyHash"]) == rb.ZERO and g["nonceConsumed"] is False,
                       "paper grant at A: H(digest, A KSSC, DBC chain), block + 30, recipient 0, no nonce")
            if expect_expiry is not None:
                self.check(int(g["expiresAt"]) == expect_expiry, f"paper grant expiry {expect_expiry}")
        return ts

    def decision_signers(self, d, sigs, inst):
        return [rv.recover(rv.decision_digest(d, inst.dbc_id, inst.kssc), sg) for sg in sigs]

    def wrong_destination(self):
        a, b = self.a, self.b
        self.check(b is not None, "source deployment B present")
        self.check(a.pbc_id == b.pbc_id and a.dbc_id == b.dbc_id and a.psc != b.psc and a.kssc != b.kssc and a.acsc != b.acsc,
                   "B: same chain pair, other PSC/KSSC/ACSC")
        req_tx, req, digest, records = self.request_on(b, "B")
        a_reqs = [rv.h(rv.request_digest(rv.decode_call("PSC", "requestAccess", t["transaction"]["input"])[0]))
                  for t in methods(a.pbc_txs, "requestAccess")]
        self.check(digest not in a_reqs, "A's PBC has no request with B's digest")
        self.check(not methods(b.dbc_txs, "consumeDecision", "policyEnf"), "B's DBC untouched (no consume/policyEnf at B)")
        s = self.stress()
        self.out.update(requestDigest=digest, bPsc=b.psc, aPsc=a.psc, bKssc=b.kssc, aKssc=a.kssc, stressTx=s["transactionHash"],
                        consumeTimestamp=ra.ts_of(s))
        if self.profile != "repaired-e":
            self.paper_grant(s, digest, req["dataId"], records)
            self.check(ra.ts_of(s) < int(req["expiresAt"]), "submitted before the request expiry")
            return
        r, cert, recs = rv.decode_call("ACSC", "consumeDecision", s["transaction"]["input"])
        d = cert["decision"]
        self.check(all(r[k] == req[k] for k in rv.REQUEST_FIELDS), "A received B's request with no signed field rewritten")
        self.check([rb.rec_tuple(x) for x in recs] == records, "A received B's forwarded records")
        signers_b = self.decision_signers(d, cert["signatures"], b)
        signers_a = self.decision_signers(d, cert["signatures"], a)
        self.check(rv.h(d["requestDigest"]) == digest and int(d["result"]) == 1 and signers_b and all(x in b.witnesses for x in signers_b),
                   "honest ALLOW certificate witness-signed under B's HMBCDecision/KSSC domain")
        step1 = int(r["sourceChainId"]) != a.pbc_id or rv.h(r["psc"]) != a.psc
        step2 = int(r["destinationChainId"]) != a.dbc_id or rv.h(r["kssc"]) != a.kssc
        first = "step1-source" if step1 else ("step2-destination" if step2 else None)
        self.check(first == "step1-source", f"replayed DecisionVerifier first fails at step 1 (got {first})")
        code = rv.rejection(s)
        self.check(code == WRONG_DESTINATION and s["receipt"]["logs"] == [], f"Rejected(WRONG_DESTINATION=3), no logs (got {code})")
        self.out.update(dvFirstFailure=first, step2Mismatch=step2, signersUnderBDomain=signers_b,
                        signerUnderADomainIsWitness=any(x in a.witnesses for x in signers_a))

    def expiry_boundary(self):
        a = self.a
        req_tx, req, digest, records = self.request_on(a, "A")
        s = self.stress()
        ts, e = ra.ts_of(s), int(req["expiresAt"])
        earlier = [t for t in a.dbc_txs if rb.bn(t) < rb.bn(s)]
        self.check(ts == e, f"consume block timestamp == request expiresAt exactly ({ts} vs {e})")
        self.check(all(ra.ts_of(t) < e for t in earlier), "every earlier DBC transaction below the request expiry")
        self.out.update(requestDigest=digest, stressTx=s["transactionHash"], consumeTimestamp=ts, requestExpiresAt=e)
        if self.profile != "repaired-e":
            self.paper_grant(s, digest, req["dataId"], records, expect_expiry=e + GRANT_TTL)
            return
        r, cert, recs = rv.decode_call("ACSC", "consumeDecision", s["transaction"]["input"])
        d = cert["decision"]
        self.check(all(r[k] == req[k] for k in rv.REQUEST_FIELDS) and [rb.rec_tuple(x) for x in recs] == records,
                   "consumed request and records = the forwarded ones")
        signers = self.decision_signers(d, cert["signatures"], a)
        self.check(rv.h(d["requestDigest"]) == digest and int(d["result"]) == 1 and signers and all(x in a.witnesses for x in signers),
                   "honest ALLOW certificate witness-signed under A's domain")
        cps = []
        for t in methods(a.dbc_txs, "acceptState"):
            cp, sigs = rv.decode_call("KSSC", "acceptState", t["transaction"]["input"])
            cps.append((rb.bn(t), cp, t["receipt"]["status"] == "0x1",
                        [rv.recover(rb.checkpoint_digest(cp, a.dbc_id, a.kssc), sg) for sg in sigs]))
        prior = [c for c in cps if c[2] and c[0] < rb.bn(s)]
        current = prior[-1][1] if prior else None
        self.check(current is not None and all(x in a.witnesses for x in prior[-1][3]) and int(d["stateSequence"]) == int(current["sequence"]),
                   "the decision's witness-signed checkpoint is current at consume")
        self.check(int(d["expiresAt"]) == e and current is not None and int(current["expiresAt"]) > e,
                   "d.expiresAt == r.expiresAt and checkpoint expiry later")
        first = rb.dv_first_failure(ts, r, d, current, records, a.policy_version)
        self.check(first == "step9-expired", f"replayed DecisionVerifier first fails at step 9 (got {first})")
        code = rv.rejection(s)
        self.check(code == EXPIRED and s["receipt"]["logs"] == [], f"Rejected(EXPIRED=7), no logs (got {code})")
        self.out.update(dvFirstFailure=first, decisionExpiresAt=int(d["expiresAt"]),
                        checkpointExpiresAt=int(current["expiresAt"]) if current else None)

    def run(self):
        try:
            {"wrong-destination": self.wrong_destination, "expiry-boundary": self.expiry_boundary}[self.out["variant"]]()
        except Exception as e:  # a review defect or malformed evidence is a failed row, never a pass
            self.f.append(f"review error: {type(e).__name__}: {e}")
        self.out.update(failures=self.f, **{"pass": not self.f})
        return self.out


def main():
    run = Path(sys.argv[1])
    rows = sorted(p.parent.parent for p in run.glob("*/*/destination-stress/result.json"))
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
