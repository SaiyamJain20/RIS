"""Agent 1 ledger-scope review of E03 audit-stress (SL3) live evidence (solo phase).

Independent of agent 3's oracle (evaluation/oracles/audit.py): every checked value is re-derived
from the raw native records the evaluator kept (<row>/<profile>/audit-instance/{pbc,dbc}-native/
transactions.json) with the ledger's exported ABIs and the ProtocolTypes.sol rules, reusing the
decoders of review_relay_stress_evidence.py (same directory).

  dropped-outcome     the request is forwarded once; one grant for it (paper policyEnf: recipient
                      0, expiry = block + 30; repaired consumeDecision: signed recipient, expiry =
                      min(decision, request)); NO later DBC or PBC transaction (the release is off
                      chain); no reportOutcome / reportAttestedOutcome and no outcome event anywhere;
                      PSC.getRequest stays FORWARDED with outcomeLogId 0 after the release.
  fabricated-outcome  no DBC grant transaction and no GrantIssued on the D2 DBC at all;
                      paper-*: reportOutcome(digest, H(digest, KSSC, 28545), keccak("HMBC.E03.
                      fabricated-outcome.v1")) by the relay succeeds with LogRecorded(kind 4,
                      subject digest, details = abi.encode(digest, grantId, outcome, relay),
                      detailsHash = keccak(details)) then OutcomeRecorded; status 2.
                      repaired-e: the same call reverts Rejected(WRONG_PROFILE=21), no logs, state
                      unchanged.

Usage: .venv/bin/python -I ledger/tools/review_audit_stress_evidence.py <evidence run dir> > out.json
Exit 0 iff at least one row was found and every row passes. Reads public evidence only.
"""

import importlib.util
import json
import sys
from pathlib import Path

from eth_abi import encode
from eth_utils import keccak

_spec = importlib.util.spec_from_file_location("rv", Path(__file__).with_name("review_relay_stress_evidence.py"))
rv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rv)
# The D2 PBC records also hold the bootstrap RSC/TMSC transactions; register their events too so every
# PBC receipt log decodes (the SL2 tool only needed ACSC/KSSC/PSC/LSC and stays unchanged).
for _c in ("RSC", "TMSC"):
    for _e in json.loads((rv.ROOT / f"ledger/exports/abi/{_c}.json").read_text()):
        if _e.get("type") == "event":
            rv.EVENTS.setdefault("0x" + keccak(text=f"{_e['name']}({','.join(rv._type(i) for i in _e['inputs'])})").hex(), (_c, _e))

FABRICATED_OUTCOME = "0x" + keccak(text="HMBC.E03.fabricated-outcome.v1").hex()
RECIPIENT_ALICE = "0x" + keccak(text="HMBC.recipient-key.alice").hex()
WRONG_PROFILE = 21
OUTCOME_KIND = 4
ZERO = "0x" + "00" * 32


def ts_of(tx):
    t = tx["receipt"]["blockTimestamp"]
    return t if isinstance(t, int) else int(t, 16)


class Review:
    def __init__(self, row_dir):
        self.f = []
        inst = row_dir / "audit-instance"
        self.stress_dir = row_dir / "audit-stress"
        self.dep = rv.load(inst / "deployment.json")
        self.boot = rv.load(inst / "bootstrap-checked.json")
        self.dbc_txs = rv.load(inst / "dbc-native/transactions.json")
        self.pbc_txs = rv.load(inst / "pbc-native/transactions.json")
        self.result = rv.load(self.stress_dir / "result.json")
        dbc = self.dep["chains"]["dbc"]
        self.dbc_id, self.pbc_id = int(dbc["chainId"]), int(self.dep["chains"]["pbc"]["chainId"])
        self.acsc, self.kssc = dbc["contracts"]["ACSC"].lower(), dbc["contracts"]["KSSC"].lower()
        self.psc = self.dep["chains"]["pbc"]["contracts"]["PSC"].lower()
        self.lsc = self.dep["chains"]["pbc"]["contracts"]["LSC"].lower()
        self.relay = self.dep["fixture"]["relay"]["address"].lower()
        self.alice = self.boot["users"]["alice"]["gid"].lower()
        self.out = dict(row=row_dir.parent.name, profile=self.dep["profile"], variant=self.result["variant"])

    def check(self, cond, msg):
        if not cond:
            self.f.append(msg)
        return cond

    def by_method(self, txs, *methods):
        return [t for t in txs if t.get("method") in methods]

    def the_request(self):
        reqs = self.by_method(self.pbc_txs, "requestAccess")
        self.check(len(reqs) == 1 and reqs[0]["receipt"]["status"] == "0x1", "exactly one forwarded request on the D2 PBC")
        req, _sig, _bundle = rv.decode_call("PSC", "requestAccess", reqs[0]["transaction"]["input"])
        self.check(rv.h(req["gid"]) == self.alice and int(req["action"]) == 1 and rv.h(req["kssc"]) == self.kssc
                   and int(req["destinationChainId"]) == self.dbc_id, "Alice READ request bound to the D2 KSSC")
        digest = rv.h(rv.request_digest(req))
        forwarded = [rv.decode_log(l) for l in reqs[0]["receipt"]["logs"]]
        self.check([(l["name"], rv.h(l["fields"].get("requestDigest"))) for l in forwarded if l["name"] == "AccessForwarded"] == [("AccessForwarded", digest)],
                   "AccessForwarded for the recomputed request digest")
        return reqs[0], req, digest

    def no_outcome(self, digest):
        self.check(not self.by_method(self.pbc_txs, "reportOutcome", "reportAttestedOutcome"), "no outcome report mined")
        names = [rv.decode_log(l)["name"] for t in self.pbc_txs for l in t["receipt"]["logs"]]
        self.check(not {"OutcomeRecorded", "AttestedOutcomeRecorded"} & set(names), "no outcome event in any PBC receipt")

    def dropped(self):
        req_tx, req, digest = self.the_request()
        gid_ = rv.grant_id(digest, self.kssc, self.dbc_id)
        method = "consumeDecision" if self.dep["profile"] == "repaired-e" else "policyEnf"
        grants_tx = self.by_method(self.dbc_txs, "policyEnf", "consumeDecision")
        self.check(len(grants_tx) == 1 and grants_tx[0]["method"] == method, f"exactly one {method} on the D2 DBC")
        g_tx = grants_tx[0]
        call = rv.decode_call("ACSC", method, g_tx["transaction"]["input"])
        self.check(g_tx["sender"].lower() == self.relay and g_tx["address"].lower() == self.acsc and g_tx["receipt"]["status"] == "0x1",
                   "grant call by the relay to the D2 ACSC, status 1")
        logs = [rv.decode_log(l) for l in g_tx["receipt"]["logs"]]
        issued = [l["fields"] for l in logs if l["name"] == "GrantIssued"]
        self.check(len(issued) == 1 and rv.h(issued[0]["grantId"]) == gid_ and rv.h(issued[0]["requestDigest"]) == digest,
                   "one GrantIssued for H(digest, KSSC, dbcChainId)")
        if issued:
            g = issued[0]
            if method == "policyEnf":
                self.check(rv.h(call[0]["pbcRequestId"]) == digest, "policyEnf names the forwarded digest")
                self.check(int(g["expiresAt"]) == ts_of(g_tx) + rv.GRANT_TTL and rv.h(g["recipientKeyHash"]) == ZERO
                           and g["nonceConsumed"] is False, "paper grant: TTL +30, recipient 0, no nonce (ACSC.sol:154)")
            else:
                r2, cert, _ = call
                dec = cert["decision"]
                self.check(rv.h(dec["requestDigest"]) == digest and r2 == req, "certificate and request are the forwarded ones")
                signer = rv.recover(rv.decision_digest(dec, self.dbc_id, self.kssc), cert["signatures"][0])
                self.check(signer in [w.lower() for w in self.dep["fixture"]["witnessSet"]["witnesses"]], "witness-signed certificate")
                self.check(int(g["expiresAt"]) == min(int(dec["expiresAt"]), int(req["expiresAt"])) and rv.h(g["recipientKeyHash"]) == RECIPIENT_ALICE
                           and g["nonceConsumed"] is True, "repaired grant: expiry = min(decision, request) (ACSC.sol:190), signed recipient, nonce consumed")
            self.out.update(grantId=gid_, grantExpiresAt=int(g["expiresAt"]), grantBlockTimestamp=ts_of(g_tx))
        later_dbc = self.dbc_txs[self.dbc_txs.index(g_tx) + 1:]
        later_pbc = self.pbc_txs[self.pbc_txs.index(req_tx) + 1:]
        self.check(later_dbc == [] , f"no DBC transaction after the grant (release is off chain; got {[t.get('method') for t in later_dbc]})")
        self.check(all(t.get("method") != "reportOutcome" and t.get("method") != "reportAttestedOutcome" for t in later_pbc),
                   "no PBC outcome transaction after the request")
        self.no_outcome(digest)
        after = rv.load(self.stress_dir / "after-release.json")
        before = rv.load(self.stress_dir / "before-release.json")
        st = after["requests"][digest]
        self.check(str(st["status"]) == "1" and str(st["outcomeLogId"]) == "0", "PSC request FORWARDED, outcomeLogId 0 after the release")
        for k in ("grants", "requests", "nonces", "accessLogCount", "logs"):
            self.check(before[k] == after[k], f"{k} unchanged across the release")
        tl = rv.load(self.stress_dir / "timeline.json")
        if issued:
            self.check(int(tl["releaseDbcClock"]) < int(issued[0]["expiresAt"]), "release observed before grant expiry (runner clock, A24)")
        self.out.update(requestDigest=digest, releaseDbcClock=tl.get("releaseDbcClock"), status=st["status"])

    def fabricated(self):
        _req_tx, req, digest = self.the_request()
        gid_ = rv.grant_id(digest, self.kssc, self.dbc_id)
        self.check(not self.by_method(self.dbc_txs, "policyEnf", "consumeDecision"), "no DBC grant or consume transaction at all")
        self.check(not any(rv.decode_log(l)["name"] == "GrantIssued" for t in self.dbc_txs for l in t["receipt"]["logs"]), "no GrantIssued on the D2 DBC")
        stress_hash = rv.load(self.stress_dir / "stress-transaction.json")["hash"]
        (tx,) = [t for t in self.pbc_txs if t["transactionHash"] == stress_hash]
        self.check(tx.get("method") == "reportOutcome" and tx["address"].lower() == self.psc and tx["sender"].lower() == self.relay,
                   "reportOutcome by the relay to the D2 PSC")
        d, g, o = rv.decode_call("PSC", "reportOutcome", tx["transaction"]["input"])
        self.check(rv.h(d) == digest and rv.h(g) == gid_ and rv.h(o) == FABRICATED_OUTCOME,
                   "arguments: forwarded digest, derived grantId H(digest, KSSC, 28545), fixed synthetic outcome")
        before, after = rv.load(self.stress_dir / "before.json"), rv.load(self.stress_dir / "after.json")
        self.check(after["grants"][gid_]["exists"] is False, "DBC grant still absent after the report")
        if self.dep["profile"] == "repaired-e":
            code = rv.rejection(tx)
            self.check(code == WRONG_PROFILE and tx["receipt"]["logs"] == [], "Rejected(WRONG_PROFILE=21) at PSC.sol:222, no logs")
            for k in ("grants", "requests", "nonces", "accessLogCount", "logs"):
                self.check(before[k] == after[k], f"{k} unchanged")
            self.check(str(after["requests"][digest]["status"]) == "1", "request still FORWARDED")
            self.out.update(rejectionCode=code)
        else:
            self.check(tx["receipt"]["status"] == "0x1", "paper reportOutcome mined with status 1")
            logs = [rv.decode_log(l) for l in tx["receipt"]["logs"]]
            self.check([(l["contract"], l["name"], l["address"]) for l in logs] == [("LSC", "LogRecorded", self.lsc), ("PSC", "OutcomeRecorded", self.psc)],
                       "LSC LogRecorded then PSC OutcomeRecorded")
            if len(logs) == 2:
                lf, of = logs[0]["fields"], logs[1]["fields"]
                details = encode(["bytes32", "bytes32", "bytes32", "address"], [bytes.fromhex(digest[2:]), bytes.fromhex(gid_[2:]),
                                                                                  bytes.fromhex(FABRICATED_OUTCOME[2:]), rv.to_checksum_address(self.relay)])
                self.check(int(lf["kind"]) == OUTCOME_KIND and rv.h(lf["subject"]) == digest and bytes(lf["details"]) == details
                           and rv.h(lf["detailsHash"]) == "0x" + keccak(details).hex(), "OUTCOME(4) log with complete details and detailsHash (LSC.sol:119-129)")
                self.check(rv.h(of["requestDigest"]) == digest and rv.h(of["grantId"]) == gid_ and rv.h(of["outcomeDigest"]) == FABRICATED_OUTCOME
                           and int(of["logId"]) == int(lf["logId"]), "OutcomeRecorded binds digest, derived grantId, outcome and log id")
                st = after["requests"][digest]
                self.check(str(st["status"]) == "2" and int(st["outcomeLogId"]) == int(lf["logId"]), "status OUTCOME_RECORDED, outcomeLogId set (PSC.sol:231-232)")
                self.out.update(logId=int(lf["logId"]))
            for k in ("grants", "nonces", "accessLogCount"):
                self.check(before[k] == after[k], f"DBC {k} unchanged")
            self.check(before["logs"]["dbc"] == after["logs"]["dbc"], "DBC history unchanged")
        self.out.update(requestDigest=digest, grantId=gid_, stressTx=stress_hash)

    def run(self):
        try:
            {"dropped-outcome": self.dropped, "fabricated-outcome": self.fabricated}[self.out["variant"]]()
        except Exception as e:  # a review defect or malformed evidence is a failed row, never a pass
            self.f.append(f"review error: {type(e).__name__}: {e}")
        self.out.update(failures=self.f, **{"pass": not self.f})
        return self.out


def main():
    run = Path(sys.argv[1])
    rows = sorted(p.parent.parent for p in run.glob("*/*/audit-stress/result.json"))
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
