"""Agent 1 ledger-scope review of the 12 pre-solo E2 catalog rows (crash-after-intent/send x6,
duplicate-outcome x3, identical nonce replay x3), for the gate E run (solo phase, A1-0082).

Independent of agent 3's oracles: every checked value is re-derived from the raw native records the
evaluator kept (<case>/<profile>/{pbc,dbc}-native/transactions.json: calldata, receipts with raw logs,
block timestamps, debug-trace return values) with the ledger's exported ABIs and the ProtocolTypes.sol
digests, reusing the decoders of review_barrier_stress_evidence.py (and, through it, the SL5/SL3/SL2
tools) and the receipt digest of review_receipt_stress_evidence.py. All unchanged.

  every instance  Alice: exactly one PSC.requestAccess with gid = Alice; recomputed digest = AccessForwarded.
                  Exactly one Alice grant transition in the whole DBC history:
                    paper-*: policyEnf(pbcRequestId = digest, exactly the forwarded records) -> GrantIssued
                    (grantId = H(digest, KSSC, dbcChainId), expiry = block + 30, recipient 0, no nonce) and an
                    allowed AccessLog;
                    repaired-e: consumeDecision(the forwarded request and records) with an honest ALLOW signed
                    by the witness under the HMBCDecision/KSSC digest, naming an accepted witness-signed
                    checkpoint; the DecisionVerifier order replayed at the consume block passes; GrantIssued
                    (derived grantId, expiry = min(decision, request), signed recipient, nonce consumed).
                  Exactly one successful outcome report for Alice's digest (paper reportOutcome with the
                  derived grantId; repaired reportAttestedOutcome whose witness-signed HMBCReceipt names the
                  derived grantId and the native grant expiry) and its outcome event.
                  Bob (control): one request, denied on the DBC (AccessLog allowed = false, POLICY_DENIED),
                  no grant for Bob anywhere.
  crash rows      recovery/: originalExpiry = the native grant expiry; no second grant or outcome (above).
                  expired-retry/ (when present): grantId = the native grant; native-before = native-after;
                  the probe DBC time >= the grant expiry (half-open validity, as every ledger expiry check).
                  The crash, restart and EXPIRED refusal are worker behaviour (protocol scope, not checked).
                  Paper crash rows keep their label (frozen BLOCKED / decided SPEC_GAP, UNPROVED; D47): this
                  tool checks mechanics only and adjudicates no classification.
  duplicate       the duplicate PBC transaction is from the relay to the PSC with calldata byte-identical to
                  the mined original outcome report; status 0, Rejected(REPLAY=8), no logs. At that point the
                  request is OUTCOME_RECORDED and the profile and caller checks pass, so the first failing
                  check is PSC.sol:226 (reportOutcome) / PSC.sol:250 (reportAttestedOutcome). before = after.
  nonce replay    the replay DBC transaction is from the relay to the ACSC with calldata byte-identical to
                  Alice's granted call; status 0, Rejected(REPLAY=8), no logs. Repaired: the replayed
                  DecisionVerifier passes at the replay block, so the code comes from KSSC.sol:180 (grant
                  exists), which precedes the nonce guard at KSSC.sol:182. Paper: KSSC.sol:180 (no nonce).
                  before = after.

Usage: .venv/bin/python -I ledger/tools/review_early_rows_evidence.py <evidence run dir> > out.json
Exit 0 iff at least one row was found and every row passes. Reads public evidence only; writes nothing.
"""

import importlib.util
import json
import sys
from pathlib import Path


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(file))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rb = _load("rb", "review_barrier_stress_evidence.py")  # registers ACSC/KSSC/PSC/LSC/RSC/TMSC events
rr = _load("rr", "review_receipt_stress_evidence.py")
rt, ra, rv = rb.rt, rb.ra, rb.rv

REPLAY, POLICY_DENIED, GRANT_TTL = 8, 9, 30
ZERO = "0x" + "00" * 32


class Instance(rb.Review):
    """One <case>/<profile>/ instance of the early layouts (no <kind>-instance/ directory)."""

    def __init__(self, inst, kind):
        self.f = []
        self.inst = inst
        self.dep = rv.load(inst / "deployment.json")
        self.boot = rv.load(inst / "bootstrap-checked.json")
        self.dbc_txs = rv.load(inst / "dbc-native/transactions.json")
        self.pbc_txs = rv.load(inst / "pbc-native/transactions.json")
        p, dbc = self.dep["chains"]["pbc"], self.dep["chains"]["dbc"]
        self.pbc_id, self.dbc_id = int(p["chainId"]), int(dbc["chainId"])
        self.tmsc, self.psc = p["contracts"]["TMSC"].lower(), p["contracts"]["PSC"].lower()
        self.acsc, self.kssc = dbc["contracts"]["ACSC"].lower(), dbc["contracts"]["KSSC"].lower()
        self.relay = self.dep["fixture"]["relay"]["address"].lower()
        self.witnesses = [w.lower() for w in self.dep["fixture"].get("witnessSet", {}).get("witnesses", [])]
        self.policy_version = int(self.dep["fixture"]["policyVersion"])
        self.alice = self.boot["users"]["alice"]["gid"].lower()
        self.bob = self.boot["users"]["bob"]["gid"].lower()
        self.profile = self.dep["profile"]
        self.out = dict(row=inst.parent.name, profile=self.profile, kind=kind)

    # ------------------------------------------------------------------ common
    def requests(self, gid):
        out = []
        for t in self.by_method(self.pbc_txs, "requestAccess"):
            req, _sig, _bundle = rv.decode_call("PSC", "requestAccess", t["transaction"]["input"])
            if rv.h(req["gid"]) == gid and t["receipt"]["status"] == "0x1":
                out.append((t, req))
        return out

    def forwarded(self, gid, who):
        reqs = self.requests(gid)
        self.check(len(reqs) == 1, f"exactly one mined {who} request on the PBC (got {len(reqs)})")
        t, req = reqs[0]
        self.check(t["address"].lower() == self.psc and int(req["action"]) == 1 and rv.h(req["kssc"]) == self.kssc
                   and int(req["destinationChainId"]) == self.dbc_id and rv.h(req["psc"]) == self.psc,
                   f"{who} READ request bound to this PSC and KSSC")
        digest = rv.h(rv.request_digest(req))
        fwd = [rv.decode_log(l) for l in t["receipt"]["logs"]]
        fwd = [l["fields"] for l in fwd if l["name"] == "AccessForwarded"]
        self.check(len(fwd) == 1 and rv.h(fwd[0]["requestDigest"]) == digest, f"{who}: AccessForwarded for the recomputed digest")
        records = [rb.rec_tuple(r) for r in fwd[0]["verifiedAttributes"]] if fwd else []
        if fwd:
            self.check(rb.credential_digest(records) == rv.h(fwd[0]["credentialDigest"]), f"{who}: forwarded credentialDigest = ledger hash")
        return t, req, digest, records

    def dbc_calls_for(self, digest):
        """Every DBC grant-path transaction for this request digest (any status)."""
        out = []
        for t in self.by_method(self.dbc_txs, "policyEnf", "consumeDecision"):
            if t["method"] == "policyEnf":
                fwd, attrs = rv.decode_call("ACSC", "policyEnf", t["transaction"]["input"])
                if rv.h(fwd["pbcRequestId"]) == digest:
                    out.append((t, fwd, attrs, None))
            else:
                r, cert, recs = rv.decode_call("ACSC", "consumeDecision", t["transaction"]["input"])
                if rv.h(rv.request_digest(r)) == digest:
                    out.append((t, r, recs, cert))
        return out

    def grants(self):
        return [(t, l["fields"]) for t in self.dbc_txs if t["receipt"]["status"] == "0x1"
                for l in map(rv.decode_log, t["receipt"]["logs"]) if l["name"] == "GrantIssued"]

    def alice_grant(self):
        req_tx, req, digest, records = self.forwarded(self.alice, "Alice")
        gid_expected = rv.grant_id(digest, self.kssc, self.dbc_id)
        calls = self.dbc_calls_for(digest)
        ok_calls = [c for c in calls if c[0]["receipt"]["status"] == "0x1"]
        self.check(len(ok_calls) == 1, f"exactly one successful DBC grant call for Alice's digest (got {len(ok_calls)})")
        alice_grants = [(t, g) for t, g in self.grants() if rv.h(g["gid"]) == self.alice]
        self.check(len(alice_grants) == 1, f"exactly one GrantIssued for Alice in the whole DBC history (got {len(alice_grants)})")
        self.check(all(rv.h(g["gid"]) != self.bob for _, g in self.grants()), "no grant for Bob anywhere")
        t, a, recs, cert = ok_calls[0]
        self.check(t["sender"].lower() == self.relay and t["address"].lower() == self.acsc, "grant call by the relay to the ACSC")
        self.check([rb.rec_tuple(x) for x in recs] == records, "DBC call carries exactly the AccessForwarded records")
        logs = self.logs(t)
        names = [l["name"] for l in logs]
        self.check(names == ["GrantIssued", "AccessLog"], f"grant call emits GrantIssued then AccessLog (got {names})")
        ts = ra.ts_of(t)
        g = logs[0]["fields"] if names[:1] == ["GrantIssued"] else {}
        acc = logs[1]["fields"] if names[1:2] == ["AccessLog"] else {}
        self.check(g and rv.h(g["grantId"]) == gid_expected and rv.h(g["requestDigest"]) == digest,
                   "grantId = H(digest, KSSC, dbcChainId) (ProtocolTypes.sol:447)")
        self.check(acc and acc["allowed"] is True and int(acc["code"]) == 0 and rv.h(acc["grantId"]) == gid_expected, "AccessLog allowed")
        if self.profile == "repaired-e":
            r, d = a, cert["decision"]
            self.check(all(r[k] == req[k] for k in rv.REQUEST_FIELDS), "consumed request = the forwarded request")
            signers = [rv.recover(rv.decision_digest(d, self.dbc_id, self.kssc), s) for s in cert["signatures"]]
            self.check(rv.h(d["requestDigest"]) == digest and int(d["result"]) == 1 and rv.h(d["credentialDigest"]) == rb.credential_digest(records)
                       and signers and all(x in self.witnesses for x in signers), "honest ALLOW signed by the witness (HMBCDecision digest)")
            cps = self.checkpoints()
            self.check(all(c["ok"] and c["signers"] and all(x in self.witnesses for x in c["signers"]) for c in cps if c["ok"]),
                       "every accepted checkpoint is witness-signed (HMBCState digest)")
            prior = [c for c in cps if c["ok"] and c["pos"] < rb.bn(t)]
            current = prior[-1]["cp"] if prior else None
            self.check(any(int(c["cp"]["sequence"]) == int(d["stateSequence"]) for c in prior), "decision names an accepted checkpoint")
            first = rb.dv_first_failure(ts, r, d, current, records, self.policy_version)
            self.check(first is None, f"replayed DecisionVerifier passes at the consume block (got {first})")
            expiry = min(int(d["expiresAt"]), int(r["expiresAt"]))
            self.check(g and int(g["expiresAt"]) == expiry and g["nonceConsumed"] is True and int(g["nonce"]) == int(r["nonce"])
                       and rv.h(g["recipientKeyHash"]) == rv.h(r["recipientKeyHash"]),
                       "repaired grant: min(decision, request) expiry, signed recipient, nonce consumed")
            self.out.update(decisionExpiresAt=int(d["expiresAt"]), requestExpiresAt=int(r["expiresAt"]))
        else:
            self.check(rv.h(a["gid"]) == self.alice and rv.h(a["dataId"]) == rv.h(req["dataId"]) and int(a["action"]) == 1,
                       "policyEnf of the forwarded tuple (pbcRequestId = request digest)")
            self.check(g and int(g["expiresAt"]) == ts + GRANT_TTL and rv.h(g["recipientKeyHash"]) == ZERO
                       and g["nonceConsumed"] is False and int(g["nonce"]) == 0,
                       "paper grant: block + 30 (ACSC.sol:154), recipient 0, no nonce")
            self.check(not [c for c in self.checkpoints() if c["ok"]], "paper: no checkpoint accepted")
        exp = int(g["expiresAt"]) if g else None
        self.out.update(requestDigest=digest, grantTx=t["transactionHash"], grantId=gid_expected, grantExpiresAt=exp,
                        grantBlockTimestamp=ts)
        return dict(tx=t, digest=digest, grantId=gid_expected, expiresAt=exp, req=req, records=records)

    def outcome(self, grant):
        method = "reportAttestedOutcome" if self.profile == "repaired-e" else "reportOutcome"
        ok = []
        for t in self.by_method(self.pbc_txs, "reportOutcome", "reportAttestedOutcome"):
            args = rv.decode_call("PSC", t["method"], t["transaction"]["input"])
            if rv.h(args[0]) == grant["digest"] and t["receipt"]["status"] == "0x1":
                ok.append((t, args))
        self.check(len(ok) == 1, f"exactly one successful outcome report for Alice's digest (got {len(ok)})")
        t, args = ok[0]
        self.check(t["method"] == method and t["sender"].lower() == self.relay and t["address"].lower() == self.psc,
                   f"{method} by the relay to the PSC")
        names = [l["name"] for l in self.logs(t)]
        event = "AttestedOutcomeRecorded" if method == "reportAttestedOutcome" else "OutcomeRecorded"
        self.check(names == ["LogRecorded", event], f"outcome emits LogRecorded then {event} (got {names})")
        if method == "reportOutcome":
            self.check(rv.h(args[1]) == grant["grantId"], "reportOutcome names the derived grantId")
        else:
            _digest, _outcome, receipt, sigs = args
            signers = [rv.recover(rr.receipt_digest(rr.norm(receipt), self.pbc_id, self.psc), s) for s in sigs]
            self.check(rv.h(receipt["requestDigest"]) == grant["digest"] and rv.h(receipt["grantId"]) == grant["grantId"]
                       and rv.h(receipt["gid"]) == self.alice and int(receipt["grantExpiresAt"]) == grant["expiresAt"]
                       and rv.h(receipt["kssc"]) == self.kssc and int(receipt["dbcChainId"]) == self.dbc_id and int(receipt["keyEpoch"]) == 0,
                       "receipt names Alice's digest, derived grantId and the native grant expiry")
            self.check(signers and all(x in self.witnesses for x in signers), "receipt signed by the witness (HMBCReceipt digest)")
        self.out.update(outcomeTx=t["transactionHash"], outcomePbcTimestamp=ra.ts_of(t))
        return t

    def bob_denied(self):
        _t, _req, digest, _records = self.forwarded(self.bob, "Bob")
        calls = [c for c in self.dbc_calls_for(digest) if c[0]["receipt"]["status"] == "0x1"]
        self.check(len(calls) == 1, f"one mined DBC call for Bob's request (got {len(calls)})")
        if calls:
            logs = self.logs(calls[0][0])
            self.check([l["name"] for l in logs] == ["AccessLog"] and logs[0]["fields"]["allowed"] is False
                       and int(logs[0]["fields"]["code"]) == POLICY_DENIED and rv.h(logs[0]["fields"]["grantId"]) == ZERO,
                       "Bob denied: AccessLog allowed = false, POLICY_DENIED, no grant")
            if self.profile == "repaired-e":
                d = calls[0][3]["decision"]
                self.check(int(d["result"]) != 1, "Bob's certificate is a DENY decision")

    def common(self):
        grant = self.alice_grant()
        self.outcome(grant)
        self.bob_denied()
        return grant

    # ------------------------------------------------------------------ kinds
    def crash(self):
        grant = self.common()
        rec = rv.load(self.inst / "recovery/result.json")
        self.check(rec.get("ok") is True and int(rec["originalExpiry"]) == grant["expiresAt"],
                   "recovery: ok, originalExpiry = the native grant expiry")
        self.out.update(point=rec.get("point"), recoveryOriginalExpiry=int(rec["originalExpiry"]))
        er = self.inst / "expired-retry"
        if (er / "result.json").exists():
            res = rv.load(er / "result.json")
            before, after = rv.load(er / "native-before.json"), rv.load(er / "native-after.json")
            self.check(before == after, "expired retry: native-before = native-after")
            self.check(rv.h(res["grantId"]) == grant["grantId"] and int(res["originalExpiry"]) == grant["expiresAt"]
                       and int(before["grant"]["expiresAt"]) == grant["expiresAt"], "expired retry names the native grant and expiry")
            probe = int(res["observedDbcTime"])
            self.check(probe >= grant["expiresAt"], "probe DBC time >= grant expiry (expired at the instant, half-open)")
            self.check(res.get("error") == "EXPIRED", "retry refused EXPIRED (worker rule; protocol scope)")
            self.out.update(expiredRetryProbeDbcTime=probe, expiredRetryNativeUnchanged=before == after)
        else:
            self.out.update(expiredRetry="not in this run")

    def duplicate(self):
        grant = self.common()
        d = self.inst / "alice/duplicate-outcome"
        call, dup = rv.load(d / "public-call.json"), rv.load(d / "duplicate-transaction.json")
        before, after = rv.load(d / "before.json"), rv.load(d / "after.json")
        orig_hash = call["originalTransaction"]["hash"]
        (orig,) = [t for t in self.pbc_txs if t["transactionHash"] == orig_hash]
        (t,) = [t for t in self.pbc_txs if t["transactionHash"] == dup["hash"]]
        self.check(orig["receipt"]["status"] == "0x1" and orig["transactionHash"] == self.out["outcomeTx"],
                   "the original is the mined outcome report")
        self.check(t["transaction"]["input"] == orig["transaction"]["input"] and t["sender"].lower() == self.relay
                   and t["address"].lower() == self.psc and rb.bn(t) > rb.bn(orig), "duplicate: identical calldata, relay, after the original")
        code = rv.rejection(t)
        self.check(code == REPLAY and t["receipt"]["logs"] == [], f"Rejected(REPLAY=8), no logs (got {code})")
        line = "PSC.sol:250" if self.profile == "repaired-e" else "PSC.sol:226"
        for k in ("grant", "request", "logs"):
            self.check(before[k] == after[k], f"{k} unchanged by the duplicate")
        self.check(str(after["request"]["status"]) == "2", "request stays OUTCOME_RECORDED (2)")
        self.out.update(duplicateTx=t["transactionHash"], rejectionCode=code, firstFailingCheck=line)

    def nonce_replay(self):
        grant = self.common()
        d = self.inst / "alice/nonce-replay"
        call, rep = rv.load(d / "public-call.json"), rv.load(d / "replay-transaction.json")
        before, after = rv.load(d / "before.json"), rv.load(d / "after.json")
        self.check(call["originalTransaction"]["hash"] == grant["tx"]["transactionHash"], "the original is Alice's granted call")
        (t,) = [t for t in self.dbc_txs if t["transactionHash"] == rep["hash"]]
        self.check(t["transaction"]["input"] == grant["tx"]["transaction"]["input"] and t["sender"].lower() == self.relay
                   and t["address"].lower() == self.acsc and rb.bn(t) > rb.bn(grant["tx"]), "replay: identical calldata, relay, after the grant")
        code = rv.rejection(t)
        self.check(code == REPLAY and t["receipt"]["logs"] == [], f"Rejected(REPLAY=8), no logs (got {code})")
        now = ra.ts_of(t)
        if self.profile == "repaired-e":
            r, cert, recs = rv.decode_call("ACSC", "consumeDecision", t["transaction"]["input"])
            prior = [c for c in self.checkpoints() if c["ok"] and c["pos"] < rb.bn(t)]
            first = rb.dv_first_failure(now, r, cert["decision"], prior[-1]["cp"] if prior else None,
                                        [rb.rec_tuple(x) for x in recs], self.policy_version)
            self.check(first is None, f"replayed DecisionVerifier passes at the replay block (got {first})")
            self.check(before.get("nonceConsumed") is True, "Alice's nonce already consumed (KSSC.sol:182 would also reject)")
            self.out.update(dvFirstFailure=first)
        for k in ("grant", "request", "nonceConsumed", "accessLogCount", "logs"):
            if k in before:
                self.check(before[k] == after.get(k), f"{k} unchanged by the replay")
        self.check(before["grant"]["exists"] is True and rv.h(before["grant"]["requestDigest"]) == grant["digest"],
                   "the grant for the same grantId already exists")
        self.out.update(replayTx=t["transactionHash"], replayBlockTimestamp=now, rejectionCode=code, firstFailingCheck="KSSC.sol:180")

    def run(self):
        try:
            {"crash": self.crash, "duplicate-outcome": self.duplicate, "nonce-replay": self.nonce_replay}[self.out["kind"]]()
        except Exception as e:  # a review defect or malformed evidence is a failed row, never a pass
            self.f.append(f"review error: {type(e).__name__}: {e}")
        self.out.update(failures=self.f, **{"pass": not self.f})
        return self.out


def main():
    run = Path(sys.argv[1])
    found = [(p.parent.parent, "crash") for p in run.rglob("recovery/result.json")]
    found += [(p.parent.parent.parent, "duplicate-outcome") for p in run.rglob("alice/duplicate-outcome/result.json")]
    found += [(p.parent.parent.parent, "nonce-replay") for p in run.rglob("alice/nonce-replay/result.json")]
    results = []
    for inst, kind in sorted(found):
        try:
            results.append(Instance(inst, kind).run())
        except Exception as e:  # missing or malformed evidence files: a failed row, never skipped
            results.append({"row": inst.parent.name, "kind": kind, "failures": [f"evidence error: {type(e).__name__}: {e}"], "pass": False})
    json.dump({"reviewer": "agent-1 (ledger scope, solo correlated)", "rows": results}, sys.stdout, indent=1, default=str)
    sys.exit(0 if results and all(r["pass"] for r in results) else 1)


if __name__ == "__main__":
    main()
