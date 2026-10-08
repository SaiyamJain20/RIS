"""E2 OWNER REHEARSAL (A1-0035): the frozen E0 case catalog run against the real modules. Owner evidence, NOT a C-E2/E2 result.

Prepared ahead of E2 (E1/C-E1 not yet complete) and disclosed as such. For each of paper-strict, paper-minimal and repaired-e, one
deployment (agent-1 deploy + bootstrap producer, lists, registrations) and one UNMODIFIED agent-2 adapter process; each case uses a
fresh request. Adversarial steps are played by the relay/CA-admin keys only; honest signatures come from the adapter; inconsistent
receipts come from agent 2's TEST-ONLY deviating-witness tool. Each observation is compared with the frozen
interfaces/v1/scenarios/e0_cases.json / e0_supplement_cases.json expectation:
  ACCEPT or CONDITIONAL  <-> the adversarial/legitimate action was accepted (grant/outcome/list), no error
  REJECT, NO_NEW_GRANT, NO_NEW_OUTCOME  <-> rejected with the frozen error code (native Rejected(code), mined status-0 tx)
  PENDING                <-> no outcome, PSC status stays FORWARDED
NOT_REHEARSED (with the reason): wrong-destination (needs a certificate genuinely issued for a second destination deployment) and
the crash-after-* cases (no crash hook through the adapter process; A2-0014, A3-0024).

Usage (repository root; the e1_rehearsal.py venv; Foundry on PATH):
    <venv>/bin/python -I ledger/tools/e2_rehearsal.py --protocol <agent-2 checkout>/protocol --cases <frozen e0_cases.json>
        --supplement <frozen e0_supplement_cases.json> --out <dir> [--ports 38545 48545]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

from eth_abi import encode as abi_encode
from eth_utils import keccak

TOOLS = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("e1_rehearsal", TOOLS / "e1_rehearsal.py")
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)
LEDGER, ROOT = R.LEDGER, R.ROOT


def h(text: str) -> str:
    return "0x" + keccak(text=text).hex()


class Obs(dict):
    def __init__(self, result: str, error: str | None = None, **native):
        super().__init__(result=result, error=error, native=native)


class World:
    def __init__(self, profile: str, protocol: pathlib.Path, urls, out: pathlib.Path):
        self.profile, self.protocol, self.urls, self.out = profile, protocol, urls, out
        self.repaired, self.paper = profile == "repaired-e", profile != "repaired-e"
        out.mkdir(parents=True, exist_ok=True)
        run_id = f"e2-{profile}-{os.getpid()}"
        env = {**os.environ, "DEPLOYER_PK": R.ANVIL_KEY0, "LEDGER_DEPLOY_FAST": "1"}
        subprocess.run([str(TOOLS / "deploy_local.sh"), *urls, profile, "complete-details", run_id], cwd=ROOT, env=env, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.dep_file = out / "deployment.json"
        shutil.copy(LEDGER / "exports" / "deployments" / run_id / "deployment.json", self.dep_file)
        shutil.rmtree(LEDGER / "exports" / "deployments" / run_id)
        subprocess.run([str(TOOLS / "bootstrap_fixture.sh"), urls[0], str(self.dep_file), str(out / "bootstrap.json")], cwd=ROOT,
                       check=True, stdout=subprocess.DEVNULL)
        self.dep, self.boot = json.load(open(self.dep_file)), json.load(open(out / "bootstrap.json"))
        self.pbc, self.dbc = R.Chain(urls[0]), R.Chain(urls[1])
        pc, dc = self.dep["chains"]["pbc"]["contracts"], self.dep["chains"]["dbc"]["contracts"]
        self.PSC, self.TMSC, self.RSC = R.Contract("PSC", pc["PSC"]), R.Contract("TMSC", pc["TMSC"]), R.Contract("RSC", pc["RSC"])
        self.KSSC, self.ACSC = R.Contract("KSSC", dc["KSSC"]), R.Contract("ACSC", dc["ACSC"])
        self.relay, self.nonce, self.ev = R.key("relay"), 100, []
        for item in self.boot["trustLists"]:
            self.submit_list(item)
        for label in ("alice", "bob"):
            u = self.boot["users"][label]
            self.tx("register " + label, self.pbc, self.relay, self.RSC, "register", u["registration"], u["possessionSignature"],
                    u["certificate"])
        self.state = pathlib.Path(tempfile.mkdtemp(prefix="adapter-", dir=out))
        os.chmod(self.state, 0o700)
        self.adp = R.Adapter(protocol, self.dep_file, self.state)
        self.adp.call("encrypt_record", {"record": {"dataId": R.DATA_P1, "owner": R.addr("H2-root"), "payloadDigest": h("synthetic payload P1")},
                                         "policy": R.P1_POLICY, "keyEpoch": "0"})

    # -------------------------------------------------------------- primitives
    def tx(self, step, chain, signer, c, fn, *args, expect=None):
        r = chain.send(signer, c, fn, *args, expect=expect)
        evs = [e for k in (self.PSC, self.TMSC, self.RSC, self.KSSC, self.ACSC) for e in k.decode_logs(r["receipt"])]
        self.ev.append({"step": step, "tx": r["tx"], "block": r["block"], "status": r["status"], "revert": r["revert"], "events": evs})
        return {e["event"]: e["args"] for e in evs}

    def submit_list(self, item, signer_role=None, expect=None):
        fn = "updateRevocationList" if item["kind"] == "RevocationList" else "updateTemporalAcl"
        return self.tx(f"{item['kind']} v{item['list']['version']} via {signer_role or item['submitterRole']}", self.pbc,
                       R.key(signer_role or item["submitterRole"]), self.TMSC, fn, item["list"], item["signature"], expect=expect)

    def sign_list(self, *args):
        out = self.out / f"list-{len(self.ev)}.json"
        subprocess.run([str(TOOLS / "sign_list.sh"), self.urls[0], str(self.dep_file), str(out), *args], cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL)
        return json.load(open(out))["item"]

    def request(self, label="alice", ttl=30, nonce=None):
        u = self.boot["users"][label]
        if nonce is None:
            self.nonce += 1
            nonce = str(self.nonce)
        fx = self.dep["fixture"]
        req = {"sourceChainId": str(self.pbc.chain_id), "destinationChainId": str(self.dbc.chain_id), "psc": self.PSC.address,
               "kssc": self.KSSC.address, "gid": u["gid"], "dataId": R.DATA_P1, "action": "1", "policyVersion": fx["policyVersion"],
               "authEpoch": self.pbc.call(self.TMSC, "authEpoch"), "keyEpoch": fx["keyEpoch"], "nonce": nonce,
               "expiresAt": str(self.pbc.now() + ttl), "recipientKeyHash": u["recipientKeyHash"]}
        return self.adp.call("prepare_request", {"request": req, "signingKeyRef": f"keyref:user:{label}"})

    def forward(self, signed, label="alice"):
        got = self.tx("requestAccess", self.pbc, self.relay, self.PSC, "requestAccess", signed["request"], signed["signature"],
                      self.boot["users"][label]["bundle"])
        return got["AccessForwarded"]

    def certify(self, digest):
        cp = self.adp.call("collect_checkpoint", {})
        self.tx("acceptState", self.dbc, self.relay, self.KSSC, "acceptState", cp["checkpoint"], cp["signatures"])
        return self.adp.call("collect_decision", {"requestDigest": digest})

    def consume(self, request, dec, expect=None, signatures=None):
        return self.tx("consumeDecision", self.dbc, self.relay, self.ACSC, "consumeDecision", request,
                       {"decision": dec["decision"], "signatures": signatures or dec["signatures"]}, dec["credentialRecords"], expect=expect)

    def policy_enf(self, ref, gid, records, expect=None):
        return self.tx("policyEnf", self.dbc, self.relay, self.ACSC, "policyEnf",
                       {"pbcRequestId": ref, "gid": gid, "dataId": R.DATA_P1, "action": "1"}, records, expect=expect)

    def grant_id(self, digest):
        return "0x" + keccak(abi_encode(["bytes32", "address", "uint256"],
                                        [bytes.fromhex(digest[2:]), self.KSSC.address, self.dbc.chain_id])).hex()

    def legit(self, label="alice"):
        """A fresh legitimate request through to its grant. Returns (signed, forwarded, decision or None, grantId)."""
        s = self.request(label)
        f = self.forward(s, label)
        if self.repaired:
            d = self.certify(s["requestDigest"])
            got = self.consume(s["request"], d)
        else:
            d = None
            got = self.policy_enf(s["requestDigest"], f["gid"], f["verifiedAttributes"])
        return s, f, d, got["GrantIssued"]["grantId"]

    def report(self, digest, grant, expect=None, receipt=None, signatures=None):
        outcome = h("rehearsal outcome " + digest)
        if self.repaired:
            if receipt is None:
                att = self.adp.call("attest_grant", {"grantId": grant})
                receipt, signatures = att["receipt"], att["signatures"]
            return self.tx("reportAttestedOutcome", self.pbc, self.relay, self.PSC, "reportAttestedOutcome", digest, outcome, receipt,
                           signatures, expect=expect)
        return self.tx("reportOutcome", self.pbc, self.relay, self.PSC, "reportOutcome", digest, grant, outcome, expect=expect)

    def status(self, digest):
        return self.pbc.call(self.PSC, "getRequest", digest)["status"]

    def restore_trust(self):
        self.submit_list(self.sign_list("crl", "H1"))
        self.submit_list(self.sign_list("tempacl", "H1", "--duty", "alice:60:3600"))

    def deviating(self, grant, field, block):
        out = subprocess.run([sys.executable, "-m", "testtools.deviating_witness", "--deployment", str(self.dep_file), "receipt",
                              "--grant-id", grant, "--field", field, "--at-block", block], cwd=self.protocol,
                             env={"PYTHONPATH": str(self.protocol), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True, check=True)
        return json.loads(out.stdout)

    def close(self):
        json.dump(R._redact(self.adp.transcript), open(self.out / "adapter-transcript.json", "w"), indent=1)
        json.dump(self.ev, open(self.out / "ledger-evidence.json", "w"), indent=1)
        try:
            self.adp.close()
        finally:
            shutil.rmtree(self.state)


# ------------------------------------------------------------------ cases (variant -> function(world) -> Obs)

def subject_substitution(w):
    s, f = (x := w.request()), w.forward(x)
    if w.paper:
        got = w.policy_enf(s["requestDigest"], w.boot["users"]["bob"]["gid"], f["verifiedAttributes"])
        return Obs("ACCEPT", grantGid=got["GrantIssued"]["gid"], requester=s["request"]["gid"])
    d = w.certify(s["requestDigest"])
    w.consume({**s["request"], "gid": w.boot["users"]["bob"]["gid"]}, d, expect="WRONG_SUBJECT")
    return Obs("REJECT", "WRONG_SUBJECT")


def nonce_replay(w):
    s, f, d, g = w.legit()
    if w.paper:
        w.policy_enf(s["requestDigest"], f["gid"], f["verifiedAttributes"], expect="REPLAY")
    else:
        w.consume(s["request"], d, expect="REPLAY")
    return Obs("NO_NEW_GRANT", "REPLAY", firstGrantAllowed=w.dbc.call(w.KSSC, "getGrant", g)[5])


def expiry_boundary(w):
    s = w.request(ttl=10)
    f = w.forward(s)
    exp = int(s["request"]["expiresAt"])
    d = w.certify(s["requestDigest"]) if w.repaired else None
    while w.dbc.now() < exp - 1:  # wait in real time, then pin the next DBC block to expiresAt: no cross-chain skew accumulates
        time.sleep(0.25)
    if w.dbc.now() < exp:
        w.dbc.rpc("evm_setNextBlockTimestamp", [exp])
    if w.paper:
        got = w.policy_enf(s["requestDigest"], f["gid"], f["verifiedAttributes"])
        blk = w.ev[-1]["block"]
        return Obs("ACCEPT", requestExpiresAt=str(exp), grantBlockTimestamp=str(int(w.dbc.rpc("eth_getBlockByNumber", [hex(blk), False])["timestamp"], 16)),
                   grant=got["GrantIssued"]["grantId"])
    w.consume(s["request"], d, expect="EXPIRED")
    blk = w.ev[-1]["block"]
    return Obs("REJECT", "EXPIRED", requestExpiresAt=str(exp),
               consumeBlockTimestamp=str(int(w.dbc.rpc("eth_getBlockByNumber", [hex(blk), False])["timestamp"], 16)))


def forged_tuple(w):
    if w.paper:
        u = w.boot["users"]["alice"]
        recs = w.pbc.call(w.TMSC, "checkCredentials", u["gid"], u["bundle"], str(w.pbc.now()))[1]
        got = w.policy_enf(h(f"fabricated {time.time()}"), R.addr("mallory"), recs)
        return Obs("ACCEPT", grantGid=got["GrantIssued"]["gid"], pbcLogged=False)
    s = w.request()
    w.forward(s)
    d = w.certify(s["requestDigest"])
    sig = d["signatures"][0]
    forged = sig[:2] + format(int(sig[2:4], 16) ^ 0x01, "02x") + sig[4:]  # flip one bit of r: recovers to a non-witness address
    w.consume(s["request"], d, expect="BAD_SIGNATURE", signatures=[forged])
    return Obs("REJECT", "BAD_SIGNATURE")


def new_reference_replay(w):
    s, f, d, g = w.legit()
    if w.paper:
        got = w.policy_enf(h(f"new reference {time.time()}"), f["gid"], f["verifiedAttributes"])
        return Obs("ACCEPT", secondGrant=got["GrantIssued"]["grantId"], firstGrant=g)
    w.consume(s["request"], d, expect="REPLAY")
    return Obs("NO_NEW_GRANT", "REPLAY")


def signed_list_rollback(w):
    w.submit_list(w.sign_list("crl", "H1", "--revoke", "101"))
    old = w.boot["trustLists"][0]
    if w.paper:
        w.submit_list(old)
        res = Obs("ACCEPT", aliceAfter=w.alice_code())
    else:
        w.submit_list(old, expect="STALE_ANCHOR")
        res = Obs("REJECT", "STALE_ANCHOR", aliceAfter=w.alice_code())
    w.restore_trust()
    return res


def wrong_issuer(w):
    w.submit_list(w.sign_list("crl", "H2"), signer_role="H1-ca-admin", expect="UNAUTHORIZED_CALLER")
    return Obs("REJECT", "UNAUTHORIZED_CALLER")


def _revocation(w, barrier: bool):
    s = w.request()
    f = w.forward(s)
    d = w.certify(s["requestDigest"]) if w.repaired else None
    w.submit_list(w.sign_list("crl", "H1", "--revoke", "101"))
    try:
        if w.paper:
            got = w.policy_enf(s["requestDigest"], f["gid"], f["verifiedAttributes"])
            return Obs("ACCEPT", grant=got["GrantIssued"]["grantId"])
        if barrier:
            cp = w.adp.call("collect_checkpoint", {})
            w.tx("acceptState", w.dbc, w.relay, w.KSSC, "acceptState", cp["checkpoint"], cp["signatures"])
            w.consume(s["request"], d, expect="STALE_STATE")
            return Obs("REJECT", "STALE_STATE", nonceConsumed=w.dbc.call(w.KSSC, "nonceConsumed", s["request"]["gid"], s["request"]["nonce"]))
        got = w.consume(s["request"], d)
        return Obs("ACCEPT", grant=got["GrantIssued"]["grantId"], windowNote="pre-barrier acceptance is the designed window")
    finally:
        w.restore_trust()


def expired_duty(w):
    w.submit_list(w.sign_list("tempacl", "H1", "--duty", "alice:60:14"))
    s = w.request()
    f = w.forward(s)
    d = w.certify(s["requestDigest"]) if w.repaired else None
    duty_end = max(int(r["validUntil"]) for r in (d["credentialRecords"] if d else f["verifiedAttributes"]) if r["kind"] == "2")
    while w.dbc.now() < duty_end:
        time.sleep(0.5)
    try:
        if w.paper:
            got = w.policy_enf(s["requestDigest"], f["gid"], f["verifiedAttributes"])
            return Obs("ACCEPT", dutyEnd=str(duty_end), grant=got["GrantIssued"]["grantId"])
        w.consume(s["request"], d, expect="EXPIRED")
        return Obs("REJECT", "EXPIRED", dutyEnd=str(duty_end), requestExpiresAt=s["request"]["expiresAt"])
    finally:
        w.restore_trust()


def dropped_outcome(w):
    s, f, d, g = w.legit()
    return Obs("PENDING", status=w.status(s["requestDigest"])) if w.status(s["requestDigest"]) == "1" else Obs("UNEXPECTED_STATUS")


def fabricated_outcome(w):
    s = w.request()
    w.forward(s)
    g = w.grant_id(s["requestDigest"])
    if w.paper:
        w.report(s["requestDigest"], g)
        return Obs("ACCEPT", status=w.status(s["requestDigest"]), dbcGrantExists=w.dbc.call(w.KSSC, "getGrant", g)[5])
    w.tx("reportOutcome", w.pbc, w.relay, w.PSC, "reportOutcome", s["requestDigest"], g, h("fabricated"), expect="WRONG_PROFILE")
    return Obs("REJECT", "WRONG_PROFILE", status=w.status(s["requestDigest"]))


def duplicate_outcome(w):
    """The duplicate resubmits the SAME report (same receipt in repaired-e): the honest witness refuses to attest a request whose
    outcome is already recorded (agent-2 attest_grant -> WRONG_SUBJECT), so a duplicate never carries a fresh attestation."""
    s, f, d, g = w.legit()
    if w.repaired:
        att = w.adp.call("attest_grant", {"grantId": g})
        w.report(s["requestDigest"], g, receipt=att["receipt"], signatures=att["signatures"])
        w.report(s["requestDigest"], g, expect="REPLAY", receipt=att["receipt"], signatures=att["signatures"])
    else:
        w.report(s["requestDigest"], g)
        w.report(s["requestDigest"], g, expect="REPLAY")
    return Obs("NO_NEW_OUTCOME", "REPLAY", status=w.status(s["requestDigest"]))


def same_nonce_distinct_digests(w):
    w.nonce += 1
    n = str(w.nonce)
    a, b = w.request(nonce=n, ttl=30), w.request(nonce=n, ttl=29)
    w.forward(a), w.forward(b)
    cp = w.adp.call("collect_checkpoint", {})
    w.tx("acceptState", w.dbc, w.relay, w.KSSC, "acceptState", cp["checkpoint"], cp["signatures"])
    da = w.adp.call("collect_decision", {"requestDigest": a["requestDigest"]})
    db = w.adp.call("collect_decision", {"requestDigest": b["requestDigest"]})
    w.consume(a["request"], da)
    w.consume(b["request"], db, expect="REPLAY")
    return Obs("NO_NEW_GRANT", "REPLAY", distinctDigests=a["requestDigest"] != b["requestDigest"])


def receipt_control(field: str | None, keep_signature: bool):
    def run(w):
        s, f, d, g = w.legit()
        att = w.adp.call("attest_grant", {"grantId": g})
        if field is None:
            w.report(s["requestDigest"], g, receipt=att["receipt"], signatures=att["signatures"])
            return Obs("ACCEPT", status=w.status(s["requestDigest"]))
        if keep_signature:
            alt = {"requestDigest": h("altered digest"), "gid": w.boot["users"]["bob"]["gid"], "dataId": h("altered data")}[field]
            receipt, sigs = {**att["receipt"], field: alt}, att["signatures"]
        else:
            art = w.deviating(g, field, att["receipt"]["dbcBlockNumber"])
            receipt, sigs = art["receipt"], art["signatures"]
            others = {k: v for k, v in receipt.items() if k != field} == {k: v for k, v in att["receipt"].items() if k != field}
            if not others:
                return Obs("INVALID_TRIAL", note="deviating receipt differs in more than the altered field")
        w.report(s["requestDigest"], g, expect="WRONG_SUBJECT", receipt=receipt, signatures=sigs)
        return Obs("NO_NEW_OUTCOME", "WRONG_SUBJECT", status=w.status(s["requestDigest"]))
    return run


def _alice_code(w):
    u = w.boot["users"]["alice"]
    return R.ERRORS[int(w.pbc.call(w.TMSC, "checkCredentials", u["gid"], u["bundle"], str(w.pbc.now()))[0])]


World.alice_code = _alice_code

VARIANTS = {  # order matters: trust-mutating cases restore trust; expiry-boundary (moves the DBC clock) runs last
    "subject-substitution": subject_substitution, "nonce-replay": nonce_replay, "forged-tuple": forged_tuple,
    "new-reference-replay": new_reference_replay, "wrong-issuer": wrong_issuer, "dropped-outcome": dropped_outcome,
    "fabricated-outcome": fabricated_outcome, "duplicate-outcome": duplicate_outcome, "signed-list-rollback": signed_list_rollback,
    "pre-barrier-revocation": lambda w: _revocation(w, False), "post-barrier-revocation": lambda w: _revocation(w, True),
    "expired-duty": expired_duty, "expiry-boundary": expiry_boundary,
}
SUPPLEMENT = {
    "E01-same-nonce-distinct-digests-repaired-e": same_nonce_distinct_digests,
    "E03-receipt-binding-control-requestDigest-repaired-e": receipt_control("requestDigest", False),
    "E03-receipt-binding-control-gid-repaired-e": receipt_control("gid", False),
    "E03-receipt-binding-control-dataId-repaired-e": receipt_control("dataId", False),
    "E03-receipt-signature-control-requestDigest-repaired-e": receipt_control("requestDigest", True),
    "E03-receipt-signature-control-gid-repaired-e": receipt_control("gid", True),
    "E03-receipt-signature-control-dataId-repaired-e": receipt_control("dataId", True),
    "E03-receipt-binding-positive-repaired-e": receipt_control(None, False),
}
NOT_REHEARSED = {
    "wrong-destination": "needs an otherwise valid request/certificate genuinely issued for a second destination deployment",
    "crash-after-intent": "no crash hook through the adapter process (A2-0014, A3-0024)",
    "crash-after-send": "no crash hook through the adapter process (A2-0014, A3-0024)",
}


def compare(case: dict, obs: dict) -> dict:
    e = case["expected"]
    want, err = e["outcome"], e["error"]
    if want in ("ACCEPT", "CONDITIONAL"):
        ok = obs["result"] == "ACCEPT" and obs["error"] is None
    else:
        ok = obs["result"] == want and obs["error"] == err
    return {"id": case["id"], "expectedOutcome": want, "expectedError": err, "expectedClass": e["classification"],
            "observed": obs["result"], "observedError": obs["error"], "native": obs["native"], "match": ok}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--protocol", required=True, type=pathlib.Path)
    ap.add_argument("--cases", required=True, type=pathlib.Path)
    ap.add_argument("--supplement", required=True, type=pathlib.Path)
    ap.add_argument("--out", required=True, type=pathlib.Path)
    ap.add_argument("--ports", nargs=2, type=int, default=[38545, 48545])
    ap.add_argument("--profiles", nargs="+", default=["paper-strict", "paper-minimal", "repaired-e"])
    a = ap.parse_args()
    cases = {c["id"]: c for c in json.load(open(a.cases))["cases"]}
    supp = {c["id"]: c for c in (lambda s: s.get("cases") or s)(json.load(open(a.supplement)))}
    a.out.mkdir(parents=True, exist_ok=True)
    anvils = [subprocess.Popen(["anvil", "--port", str(p), "--chain-id", str(c), "--block-time", "1", "--silent"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for p, c in zip(a.ports, (18545, 28545))]
    urls = (f"http://127.0.0.1:{a.ports[0]}", f"http://127.0.0.1:{a.ports[1]}")
    rows = []
    try:
        for _ in range(100):
            try:
                R.Chain(urls[0]), R.Chain(urls[1])
                break
            except Exception:
                time.sleep(0.1)
        for p in a.profiles:
            w = World(p, a.protocol.resolve(), urls, a.out / p)
            try:
                for v, fn in VARIANTS.items():
                    cid = next(c for c in cases if cases[c]["profile"] == p and cases[c]["variant"] == v)
                    try:
                        rows.append(compare(cases[cid], fn(w)))
                    except BaseException as ex:  # record and continue; a crash of one case is a finding, not a silent skip
                        rows.append({"id": cid, "observed": "HARNESS_ERROR", "error": repr(ex)[:300], "match": False})
                for cid, c in cases.items():
                    if c["profile"] == p and c["variant"] in NOT_REHEARSED:
                        rows.append({"id": cid, "observed": "NOT_REHEARSED", "reason": NOT_REHEARSED[c["variant"]], "match": None})
                if p == "repaired-e":
                    for cid, fn in SUPPLEMENT.items():
                        try:
                            rows.append(compare(supp[cid], fn(w)))
                        except BaseException as ex:
                            rows.append({"id": cid, "observed": "HARNESS_ERROR", "error": repr(ex)[:300], "match": False})
            finally:
                w.close()
    finally:
        for p in anvils:
            p.terminate()
            p.wait(timeout=10)
    blob = "".join(f.read_text() for f in a.out.rglob("*.json"))
    leaked = [lbl for lbl in ("alice", "bob", "relay", "witness-1", "H1-root", "H2-root") if R.key(lbl)[2:] in blob]
    run = [r for r in rows if r["match"] is not None]
    summary = {"schemaVersion": "hmbc-e2-owner-rehearsal/v0", "note": "OWNER rehearsal (A1-0035), prepared ahead of E2; not a C-E2 or gate result",
               "rehearsed": len(run), "matched": sum(bool(r["match"]) for r in run), "notRehearsed": len(rows) - len(run),
               "privateKeysInOutputs": leaked, "rows": rows}
    json.dump(summary, open(a.out / "summary.json", "w"), indent=1)
    for r in rows:
        tag = "SKIP " if r["match"] is None else ("MATCH" if r["match"] else "DIFF ")
        print(f"{tag} {r['id']:58} expected={r.get('expectedOutcome', '-')}/{r.get('expectedError')} "
              f"observed={r['observed']}/{r.get('observedError', r.get('error', r.get('reason', '')))}")
    print(f"REHEARSED {summary['rehearsed']} MATCHED {summary['matched']} NOT_REHEARSED {summary['notRehearsed']} | key leaks: {leaked}")
    return 0 if summary["matched"] == summary["rehearsed"] and not leaked else 1


if __name__ == "__main__":
    sys.exit(main())
