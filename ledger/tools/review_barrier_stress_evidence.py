"""Agent 1 ledger-scope review of E02 revocation-barrier and expired-duty (SL6) live evidence (solo phase).

Independent of agent 3's oracle (evaluation/oracles/barrier.py): every checked value is re-derived from
the raw native records (<row>/<profile>/barrier-instance/{pbc,dbc}-native/transactions.json) with the
ledger ABIs and the ProtocolTypes.sol digests (HMBCRequest, HMBCDecision, HMBCState, HMBCTrust), reusing
the decoders of review_trust_stress_evidence.py. The repaired DecisionVerifier order (DecisionVerifier.sol
52-96) is replayed in Python on the mined consumeDecision calldata, the checkpoint current at that block
(the last accepted acceptState before it) and the consume block time, and the first failing step must be
the frozen one.

  common        one Alice requestAccess on the D2 PBC, digest recomputed = AccessForwarded; the DBC call
                carries exactly the forwarded records.
  pre/post      the H1 CA-admin installs an H1-root-signed CRL v2 revoking [101] (TrustAnchorUpdated v2,
                authEpoch + 1) in a PBC block after the request.
                paper-*: policyEnf of the forwarded tuple grants (recipient 0, block + 30, no nonce) and no
                acceptState is mined.
                repaired pre: the certificate's decision state and the checkpoint current at consume both
                predate the revocation block; replayed DV passes; grant = min(decision, request) expiry,
                nonce consumed.
                repaired post: a second acceptState (sequence + 1, the revocation authEpoch, source block >=
                the revocation block) is current at consume; replayed DV first fails at line 87 on the
                SEQUENCE (decision expiry <= new checkpoint expiry; steps 9 and 10a pass); Rejected(6), no logs.
  expired duty  the H1 CA-admin installs an H1-root-signed TempACL v2 with one Alice ON_DUTY entry before
                the request; the forwarded temporal record ends at that entry's validUntil; the request block
                is inside the window; every DBC transaction before the consume is mined before the duty end
                and the consume at or after it (only the DBC clock moved; PBC transactions all precede it).
                paper-*: policyEnf grants with that expired record.
                repaired: replayed DV first fails at step 13 (duty end <= consume < decision, request and
                checkpoint expiry); Rejected(7), no logs.

Usage: .venv/bin/python -I ledger/tools/review_barrier_stress_evidence.py <evidence run dir> > out.json
Exit 0 iff at least one row was found and every row passes. Reads public evidence only.
"""

import importlib.util
import json
import sys
from pathlib import Path

from eth_abi import encode
from eth_utils import keccak

_spec = importlib.util.spec_from_file_location("rt", Path(__file__).with_name("review_trust_stress_evidence.py"))
rt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt)  # registers TMSC/RSC ABIs and events
ra, rv = rt.ra, rt.rv

TEMP_ENTRY_T = keccak(text="TempAclEntry(address gid,bytes32 role,uint64 validFrom,uint64 validUntil)")
TEMP_ACL_T = keccak(text="TemporalAcl(address authority,uint64 version,uint64 validUntil,TempAclEntry[] entries)"
                         "TempAclEntry(address gid,bytes32 role,uint64 validFrom,uint64 validUntil)")
RECORD_T = keccak(text="CredentialRecord(address issuer,bytes32 role,uint8 kind,uint64 serial,uint64 anchorVersion,uint64 validUntil)")
CHECKPOINT_T = keccak(text="StateCheckpoint(uint64 sequence,uint64 authEpoch,uint64 policyVersion,uint64 keyEpoch,"
                           "uint64 witnessSetVersion,uint256 sourceChainId,address psc,uint256 sourceBlockNumber,"
                           "bytes32 sourceBlockHash,uint64 expiresAt)")
STALE_STATE, EXPIRED, GRANT_TTL, ALICE_SERIAL = 6, 7, 30, 101
ANCHOR_CRL, ANCHOR_TEMP_ACL = 1, 2
ZERO = "0x" + "00" * 32


def bn(tx):
    b = tx["receipt"]["blockNumber"]
    return (b if isinstance(b, int) else int(b, 16), int(tx["receipt"]["transactionIndex"], 16)
            if isinstance(tx["receipt"]["transactionIndex"], str) else int(tx["receipt"]["transactionIndex"]))


def rec_tuple(r):
    if isinstance(r, dict):
        r = (r["issuer"], r["role"], r["kind"], r["serial"], r["anchorVersion"], r["validUntil"])
    return (rv.h(r[0]), rv.h(r[1]), int(r[2]), int(r[3]), int(r[4]), int(r[5]))


def credential_digest(records):
    hs = b"".join(keccak(encode(["bytes32", "address", "bytes32", "uint8", "uint64", "uint64", "uint64"],
                                [RECORD_T, rv.to_checksum_address(r[0]), bytes.fromhex(r[1][2:]), r[2], r[3], r[4], r[5]]))
                  for r in records)
    return "0x" + keccak(hs).hex()


def temporal_acl_digest(acl, pbc_chain_id, tmsc):
    hs = b"".join(keccak(encode(["bytes32", "address", "bytes32", "uint64", "uint64"],
                                [TEMP_ENTRY_T, rv.to_checksum_address(e["gid"]), e["role"], int(e["validFrom"]), int(e["validUntil"])]))
                  for e in acl["entries"])
    struct = keccak(encode(["bytes32", "address", "uint64", "uint64", "bytes32"],
                           [TEMP_ACL_T, rv.to_checksum_address(acl["authority"]), int(acl["version"]), int(acl["validUntil"]), keccak(hs)]))
    return rv.typed(rv.domain("HMBCTrust", pbc_chain_id, tmsc), struct)


def checkpoint_digest(cp, dbc_chain_id, kssc):
    struct = keccak(encode(["bytes32", "uint64", "uint64", "uint64", "uint64", "uint64", "uint256", "address", "uint256", "bytes32", "uint64"],
                           [CHECKPOINT_T] + [cp[k] for k in ("sequence", "authEpoch", "policyVersion", "keyEpoch", "witnessSetVersion",
                                                             "sourceChainId", "psc", "sourceBlockNumber", "sourceBlockHash", "expiresAt")]))
    return rv.typed(rv.domain("HMBCState", dbc_chain_id, kssc), struct)


def dv_first_failure(now, r, d, cp, records, policy_version):
    """DecisionVerifier.sol:74-94 after steps 1-8 (checked separately): the first failing step, or None."""
    if now >= int(d["expiresAt"]) or now >= int(r["expiresAt"]):
        return "step9-expired"
    if cp is None or now >= int(cp["expiresAt"]):
        return "step10a-checkpoint"
    if int(d["stateSequence"]) != int(cp["sequence"]):
        return "line87-sequence"
    if int(d["expiresAt"]) > int(cp["expiresAt"]):
        return "line87-expiry"
    if int(r["authEpoch"]) != int(cp["authEpoch"]):
        return "line88-authEpoch"
    if int(r["policyVersion"]) != int(cp["policyVersion"]) or int(r["policyVersion"]) != policy_version:
        return "line89-policyVersion"
    if int(r["keyEpoch"]) != int(cp["keyEpoch"]):
        return "line90-keyEpoch"
    for rec in records:
        if now >= rec[5]:
            return "step13-record"
    return None


class Review(rt.Review):
    def __init__(self, row_dir):
        self.f = []
        inst = row_dir / "barrier-instance"
        self.stress_dir = row_dir / "barrier-stress"
        self.dep = rv.load(inst / "deployment.json")
        self.boot = rv.load(inst / "bootstrap-checked.json")
        self.dbc_txs = rv.load(inst / "dbc-native/transactions.json")
        self.pbc_txs = rv.load(inst / "pbc-native/transactions.json")
        self.result = rv.load(self.stress_dir / "result.json")
        p, dbc = self.dep["chains"]["pbc"], self.dep["chains"]["dbc"]
        self.pbc_id, self.dbc_id = int(p["chainId"]), int(dbc["chainId"])
        self.tmsc, self.psc = p["contracts"]["TMSC"].lower(), p["contracts"]["PSC"].lower()
        self.acsc, self.kssc = dbc["contracts"]["ACSC"].lower(), dbc["contracts"]["KSSC"].lower()
        self.relay = self.dep["fixture"]["relay"]["address"].lower()
        self.witnesses = [w.lower() for w in self.dep["fixture"].get("witnessSet", {}).get("witnesses", [])]
        self.policy_version = int(self.dep["fixture"]["policyVersion"])
        self.alice = self.boot["users"]["alice"]["gid"].lower()
        self.auth = {a["id"]: a for a in self.dep["fixture"]["authorities"]}
        self.profile = self.dep["profile"]
        self.out = dict(row=row_dir.parent.name, profile=self.profile, variant=self.result["variant"])

    # ------------------------------------------------------------------ PBC side
    def h1_update(self, method):
        """The single post-bootstrap H1 list update of the row (version 2), decoded and signature-checked."""
        h1 = self.auth["H1"]
        admin, root = h1["caAdmins"][0].lower(), h1["root"].lower()
        out = []
        for t in self.by_method(self.pbc_txs, method):
            lst, sig = rv.decode_call("TMSC", method, t["transaction"]["input"])
            if rv.h(lst["authority"]) != root or int(lst["version"]) < 2:
                continue
            dig = rt.list_digest(lst, self.pbc_id, self.tmsc) if method == "updateRevocationList" else temporal_acl_digest(lst, self.pbc_id, self.tmsc)
            out.append((t, lst, rv.recover(dig, sig)))
        self.check(len(out) == 1, f"exactly one H1 {method} after bootstrap (got {len(out)})")
        t, lst, signer = out[0]
        self.check(t["sender"].lower() == admin and t["address"].lower() == self.tmsc and t["receipt"]["status"] == "0x1",
                   f"{method} mined by the H1 CA-admin to the D2 TMSC")
        self.check(int(lst["version"]) == 2 and signer == root, f"{method}: version 2 signed by the H1 root (ledger HMBCTrust digest)")
        ev = self.anchor_events(t)
        kind = ANCHOR_CRL if method == "updateRevocationList" else ANCHOR_TEMP_ACL
        self.check(len(ev) == 1 and int(ev[0]["version"]) == 2 and int(ev[0]["kind"]) == kind, "TrustAnchorUpdated(version 2)")
        return t, lst, int(ev[0]["authEpoch"]) if ev else None

    def the_request(self):
        req_tx, req, digest = ra.Review.the_request(self)
        fwd = [rv.decode_log(l)["fields"] for l in req_tx["receipt"]["logs"] if rv.decode_log(l)["name"] == "AccessForwarded"]
        records = [rec_tuple(r) for r in fwd[0]["verifiedAttributes"]]
        self.check(credential_digest(records) == rv.h(fwd[0]["credentialDigest"]), "forwarded credentialDigest = ledger hash of the records")
        return req_tx, req, digest, records

    # ------------------------------------------------------------------ DBC side
    def stress(self):
        h = rv.load(self.stress_dir / "stress-transaction.json")["hash"]
        (t,) = [t for t in self.dbc_txs if t["transactionHash"] == h]
        self.check(t["sender"].lower() == self.relay and t["address"].lower() == self.acsc, "DBC call by the relay to the D2 ACSC")
        return t

    def checkpoints(self):
        out = []
        for t in self.by_method(self.dbc_txs, "acceptState"):
            cp, sigs = rv.decode_call("KSSC", "acceptState", t["transaction"]["input"])
            signers = [rv.recover(checkpoint_digest(cp, self.dbc_id, self.kssc), s) for s in sigs]
            out.append(dict(tx=t, cp=cp, signers=signers, ok=t["receipt"]["status"] == "0x1", pos=bn(t)))
        return out

    def logs(self, tx):
        return [rv.decode_log(l) for l in tx["receipt"]["logs"]]

    def paper_grant(self, s, digest, req, records):
        fwd, attrs = rv.decode_call("ACSC", "policyEnf", s["transaction"]["input"])
        self.check(rv.h(fwd["pbcRequestId"]) == digest and rv.h(fwd["gid"]) == self.alice and rv.h(fwd["dataId"]) == rv.h(req["dataId"])
                   and int(fwd["action"]) == 1, "policyEnf of the forwarded tuple (pbcRequestId = request digest)")
        self.check([rec_tuple(a) for a in attrs] == records, "policyEnf carries exactly the AccessForwarded records")
        ts = ra.ts_of(s)
        names = [l["name"] for l in self.logs(s)]
        self.check(s["receipt"]["status"] == "0x1" and names == ["GrantIssued", "AccessLog"], f"paper grant mined (got {names})")
        if names[:1] == ["GrantIssued"]:
            g = self.logs(s)[0]["fields"]
            self.check(rv.h(g["grantId"]) == rv.grant_id(digest, self.kssc, self.dbc_id) and int(g["expiresAt"]) == ts + GRANT_TTL
                       and rv.h(g["recipientKeyHash"]) == ZERO and g["nonceConsumed"] is False,
                       "paper grant: derived grantId, block + 30, recipient 0, no nonce")
        self.check(not [c for c in self.checkpoints() if c["ok"]], "paper: no checkpoint accepted")
        return ts

    def repaired(self, s, digest, req, records):
        r, cert, recs = rv.decode_call("ACSC", "consumeDecision", s["transaction"]["input"])
        d = cert["decision"]
        self.check(rv.h(rv.request_digest(r)) == digest and all(r[k] == req[k] for k in rv.REQUEST_FIELDS), "consumed request = the forwarded request")
        self.check([rec_tuple(x) for x in recs] == records, "consumed records = the AccessForwarded records")
        signers = [rv.recover(rv.decision_digest(d, self.dbc_id, self.kssc), sg) for sg in cert["signatures"]]
        self.check(rv.h(d["requestDigest"]) == digest and int(d["result"]) == 1 and rv.h(d["credentialDigest"]) == credential_digest(records)
                   and signers and all(x in self.witnesses for x in signers), "honest ALLOW decision signed by the witness (ledger HMBCDecision digest)")
        cps = self.checkpoints()
        self.check(all(c["ok"] for c in cps) and all(c["signers"] and all(x in self.witnesses for x in c["signers"]) for c in cps),
                   "every acceptState mined and witness-signed (ledger HMBCState digest)")
        prior = [c for c in cps if c["ok"] and c["pos"] < bn(s)]
        current = prior[-1]["cp"] if prior else None
        decided = [c for c in prior if int(c["cp"]["sequence"]) == int(d["stateSequence"])]
        self.check(len(decided) == 1, "the decision names one accepted checkpoint")
        return r, d, current, decided[0]["cp"] if decided else None, prior

    # ------------------------------------------------------------------ variants
    def revocation_row(self):
        req_tx, req, digest, records = self.the_request()
        rev_tx, crl, epoch_after = self.h1_update("updateRevocationList")
        self.check([int(x) for x in crl["revokedSerials"]] == [ALICE_SERIAL], "CRL v2 revokes Alice serial 101 only")
        self.check(bn(rev_tx) > bn(req_tx), "revocation mined after the request (PBC block order)")
        self.check(epoch_after == int(req["authEpoch"]) + 1, "revocation authEpoch = request authEpoch + 1")
        s = self.stress()
        self.out.update(requestDigest=digest, revocationTx=rev_tx["transactionHash"], revocationPbcBlock=bn(rev_tx)[0],
                        stressTx=s["transactionHash"], consumeTimestamp=ra.ts_of(s), revocationPbcTimestamp=ra.ts_of(rev_tx))
        if self.profile != "repaired-e":
            self.paper_grant(s, digest, req, records)
            return
        r, d, current, cp1, prior = self.repaired(s, digest, req, records)
        now = ra.ts_of(s)
        rev_block = bn(rev_tx)[0]
        self.check(int(d["sourceBlockNumber"]) < rev_block and cp1 is not None and int(cp1["sourceBlockNumber"]) < rev_block
                   and int(cp1["authEpoch"]) == int(req["authEpoch"]), "certificate and its checkpoint predate the revocation block")
        first = dv_first_failure(now, r, d, current, records, self.policy_version)
        self.out.update(dvFirstFailure=first, decisionExpiresAt=int(d["expiresAt"]), requestExpiresAt=int(r["expiresAt"]),
                        currentCheckpoint=dict(sequence=int(current["sequence"]), authEpoch=int(current["authEpoch"]),
                                               sourceBlockNumber=int(current["sourceBlockNumber"]), expiresAt=int(current["expiresAt"])) if current else None)
        if self.out["variant"] == "pre-barrier-revocation":
            self.check(current == cp1, "no checkpoint accepted between the decision's checkpoint and consume")
            self.check(first is None, f"replayed DecisionVerifier passes (got {first})")
            names = [l["name"] for l in self.logs(s)]
            self.check(s["receipt"]["status"] == "0x1" and names == ["GrantIssued", "AccessLog"], f"older certificate accepted (got {names})")
            if names[:1] == ["GrantIssued"]:
                g = self.logs(s)[0]["fields"]
                self.check(rv.h(g["grantId"]) == rv.grant_id(digest, self.kssc, self.dbc_id)
                           and int(g["expiresAt"]) == min(int(d["expiresAt"]), int(r["expiresAt"])) and g["nonceConsumed"] is True
                           and int(g["nonce"]) == int(r["nonce"]) and rv.h(g["recipientKeyHash"]) == rv.h(r["recipientKeyHash"]),
                           "grant: derived grantId, min(decision, request) expiry, nonce consumed")
        else:
            self.check(current is not None and current != cp1 and int(current["sequence"]) == int(cp1["sequence"]) + 1
                       and int(current["authEpoch"]) == epoch_after and int(current["sourceBlockNumber"]) >= rev_block,
                       "the checkpoint current at consume carries the revocation (sequence + 1, new authEpoch, source block >= revocation)")
            self.check(first == "line87-sequence", f"replayed DecisionVerifier first fails at line 87 on the sequence (got {first})")
            self.check(int(d["expiresAt"]) <= int(current["expiresAt"]) and now < int(d["expiresAt"]) and now < int(r["expiresAt"])
                       and now < int(current["expiresAt"]), "steps 9 and 10a pass and the line 87 expiry clause does not apply")
            code = rv.rejection(s)
            self.check(code == STALE_STATE and s["receipt"]["logs"] == [], f"Rejected(STALE_STATE=6), no logs (got {code})")

    def expired_row(self):
        acl_tx, acl, _ = self.h1_update("updateTemporalAcl")
        req_tx, req, digest, records = self.the_request()
        self.check(bn(acl_tx) < bn(req_tx), "TempACL v2 installed before the request")
        self.check(len(acl["entries"]) == 1 and rv.h(acl["entries"][0]["gid"]) == self.alice, "TempACL v2: one Alice entry")
        end = int(acl["entries"][0]["validUntil"])
        duty = [x for x in records if x[2] == ANCHOR_TEMP_ACL]
        self.check(len(duty) == 1 and duty[0][5] == end and duty[0][4] == 2, "forwarded temporal record: TempACL v2, validUntil = entry end")
        self.check(int(acl["entries"][0]["validFrom"]) <= ra.ts_of(req_tx) < end, "request block inside the duty window")
        self.check(not self.by_method(self.pbc_txs, "updateRevocationList") or
                   all(int(rv.decode_call("TMSC", "updateRevocationList", t["transaction"]["input"])[0]["version"]) == 1
                       for t in self.by_method(self.pbc_txs, "updateRevocationList")), "no CRL change in the expired-duty row")
        s = self.stress()
        now = ra.ts_of(s)
        earlier = [t for t in self.dbc_txs if bn(t) < bn(s)]
        self.check(all(ra.ts_of(t) < end for t in earlier) and now >= end, "every earlier DBC tx before the duty end; consume at or after it")
        self.check(all(ra.ts_of(t) < end for t in self.pbc_txs), "every PBC tx before the duty end (PBC clock not moved past it)")
        self.out.update(requestDigest=digest, tempAclTx=acl_tx["transactionHash"], dutyEnd=end, stressTx=s["transactionHash"],
                        consumeTimestamp=now, recordValidUntil=duty[0][5] if duty else None)
        if self.profile != "repaired-e":
            self.paper_grant(s, digest, req, records)
            self.check(now >= end, "paper grant issued with the duty record expired at the DBC block time")
            return
        r, d, current, cp1, prior = self.repaired(s, digest, req, records)
        self.check(current is not None and current == cp1, "no checkpoint accepted after the decision's checkpoint before consume")
        self.check(cp1 is not None and int(cp1["authEpoch"]) == int(req["authEpoch"]) and int(cp1["sourceBlockNumber"]) >= bn(acl_tx)[0],
                   "checkpoint after the TempACL install (same authEpoch as the request)")
        first = dv_first_failure(now, r, d, current, records, self.policy_version)
        self.out.update(dvFirstFailure=first, decisionExpiresAt=int(d["expiresAt"]), requestExpiresAt=int(r["expiresAt"]),
                        checkpointExpiresAt=int(current["expiresAt"]) if current else None)
        self.check(first == "step13-record", f"replayed DecisionVerifier first fails at step 13 (got {first})")
        self.check(end <= now < min(int(d["expiresAt"]), int(r["expiresAt"]), int(current["expiresAt"])),
                   "duty end <= consume < min(decision, request, checkpoint expiry)")
        code = rv.rejection(s)
        self.check(code == EXPIRED and s["receipt"]["logs"] == [], f"Rejected(EXPIRED=7), no logs (got {code})")

    def run(self):
        try:
            {"pre-barrier-revocation": self.revocation_row, "post-barrier-revocation": self.revocation_row,
             "expired-duty": self.expired_row}[self.out["variant"]]()
        except Exception as e:  # a review defect or malformed evidence is a failed row, never a pass
            self.f.append(f"review error: {type(e).__name__}: {e}")
        self.out.update(failures=self.f, **{"pass": not self.f})
        return self.out


def main():
    run = Path(sys.argv[1])
    rows = sorted(p.parent.parent for p in run.glob("*/*/barrier-stress/result.json"))
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
