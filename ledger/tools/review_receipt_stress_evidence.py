"""Agent 1 ledger-scope review of E03 receipt-control (SL4) live evidence (solo phase).

Independent of agent 3's oracle (evaluation/oracles/receipt.py): every checked value is re-derived
from the raw native records (<row>/repaired-e/receipt-instance/{pbc,dbc}-native/transactions.json)
with the ledger's exported ABIs and ProtocolTypes.sol (HMBCHash.hashGrantReceipt /
grantReceiptDigest: domain HMBCReceipt, version 1, PBC chain id, PSC), reusing the decoders of
review_relay_stress_evidence.py / review_audit_stress_evidence.py (same directory).

Every row: one forwarded Alice request, one consumeDecision grant G = H(digest, KSSC, 28545), and the
honest receipt (receipt-stress/honest-receipt.json) recovers to the witness under the ledger digest
and joins the native grant (GrantIssued fields). Then the mined PSC.reportAttestedOutcome:

  receipt-binding-control    submitted receipt = honest receipt with exactly the named field changed;
                             its signature recovers to the WITNESS over the ALTERED receipt (a valid
                             witness signature, A40 deliberate deviation) -> Rejected(WRONG_SUBJECT=2)
                             from the binding check PSC.sol:266-269, no logs, state unchanged.
  receipt-signature-control  same alteration; the honest signature is kept: it recovers to the witness
                             only over the HONEST receipt, not the altered one -> Rejected(2) (binding
                             precedes quorum), no logs, state unchanged.
  receipt-binding-positive   honest receipt unchanged -> LSC LogRecorded(OUTCOME=4, subject digest,
                             details = abi.encode(digest, outcomeDigest, receipt, relay), detailsHash)
                             then PSC AttestedOutcomeRecorded(digest, grantId, outcome, dbcBlockNumber,
                             logId); status 2; DBC unchanged.

Usage: .venv/bin/python -I ledger/tools/review_receipt_stress_evidence.py <evidence run dir> > out.json
Exit 0 iff at least one row was found and every row passes. Reads public evidence only.
"""

import importlib.util
import json
import sys
from pathlib import Path

from eth_abi import encode
from eth_utils import keccak

_spec = importlib.util.spec_from_file_location("ra", Path(__file__).with_name("review_audit_stress_evidence.py"))
ra = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ra)  # also extends the shared event table with RSC/TMSC
rv = ra.rv

RECEIPT_T = keccak(text="GrantReceipt(bytes32 requestDigest,bytes32 grantId,address gid,bytes32 dataId,uint64 keyEpoch,"
                        "uint64 grantExpiresAt,uint64 witnessSetVersion,uint256 dbcChainId,address kssc,uint256 dbcBlockNumber,"
                        "bytes32 dbcBlockHash)")
RECEIPT_FIELDS = ("requestDigest", "grantId", "gid", "dataId", "keyEpoch", "grantExpiresAt", "witnessSetVersion", "dbcChainId",
                  "kssc", "dbcBlockNumber", "bytes32 dbcBlockHash")
RECEIPT_TYPES = ("bytes32", "bytes32", "address", "bytes32", "uint64", "uint64", "uint64", "uint256", "address", "uint256", "bytes32")
RECEIPT_FIELDS = tuple(f.split()[-1] for f in RECEIPT_FIELDS)
RECEIPT_OUTCOME = "0x" + keccak(text="HMBC.E03.receipt-control-outcome.v1").hex()
WRONG_SUBJECT = 2


def to_native(receipt_json):
    """Evaluator JSON receipt (decimal strings / hex) -> eth_abi values in ledger field order."""
    out = {}
    for k, t in zip(RECEIPT_FIELDS, RECEIPT_TYPES):
        v = receipt_json[k]
        out[k] = bytes.fromhex(v[2:]) if t == "bytes32" else (int(v) if t.startswith("uint") else rv.to_checksum_address(v))
    return out


def norm(receipt):
    """Decoded calldata tuple dict -> comparable form."""
    return {k: (receipt[k] if not isinstance(receipt[k], str) else rv.to_checksum_address(receipt[k])) for k in RECEIPT_FIELDS}


def receipt_digest(r, pbc_chain_id, psc):
    struct = keccak(encode(("bytes32",) + RECEIPT_TYPES, [RECEIPT_T] + [r[k] for k in RECEIPT_FIELDS]))
    return rv.typed(rv.domain("HMBCReceipt", pbc_chain_id, psc), struct)


class Review(ra.Review):
    def __init__(self, row_dir):
        self.f = []
        inst = row_dir / "receipt-instance"
        self.stress_dir = row_dir / "receipt-stress"
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
        self.witnesses = [w.lower() for w in self.dep["fixture"]["witnessSet"]["witnesses"]]
        self.out = dict(row=row_dir.parent.name, profile=self.dep["profile"], variant=self.result["variant"], field=self.result.get("field"))

    def receipts(self):
        self.check(self.dep["profile"] == "repaired-e", "repaired-e deployment")
        _req_tx, req, digest = self.the_request()
        gid_ = rv.grant_id(digest, self.kssc, self.dbc_id)
        grants_tx = self.by_method(self.dbc_txs, "policyEnf", "consumeDecision")
        self.check(len(grants_tx) == 1 and grants_tx[0]["method"] == "consumeDecision" and grants_tx[0]["receipt"]["status"] == "0x1",
                   "exactly one successful consumeDecision on the D2 DBC")
        issued = [rv.decode_log(l)["fields"] for l in grants_tx[0]["receipt"]["logs"] if rv.decode_log(l)["name"] == "GrantIssued"]
        self.check(len(issued) == 1 and rv.h(issued[0]["grantId"]) == gid_, "GrantIssued for H(digest, KSSC, dbcChainId)")
        g = issued[0]
        honest_json = rv.load(self.stress_dir / "honest-receipt.json")
        honest = to_native(honest_json["receipt"])
        hsig = bytes.fromhex(honest_json["signatures"][0][2:])
        hd = receipt_digest(honest, self.pbc_id, self.psc)
        self.check(rv.recover(hd, hsig) in self.witnesses, "honest receipt recovers to the witness (ledger HMBCReceipt digest)")
        self.check(rv.h(honest["requestDigest"]) == digest and rv.h(honest["grantId"]) == gid_ and honest["gid"].lower() == self.alice
                   and rv.h(honest["dataId"]) == rv.h(req["dataId"]) and honest["keyEpoch"] == 0
                   and honest["grantExpiresAt"] == int(g["expiresAt"]) and honest["witnessSetVersion"] == 1
                   and honest["dbcChainId"] == self.dbc_id and honest["kssc"].lower() == self.kssc,
                   "honest receipt joins the forwarded request and the native GrantIssued")
        self.check(honest["grantExpiresAt"] <= int(req["expiresAt"]), "grantExpiresAt <= request expiry (PSC.sol:276 not triggered)")
        # The mined report.
        stress_hash = rv.load(self.stress_dir / "stress-transaction.json")["hash"]
        (tx,) = [t for t in self.pbc_txs if t["transactionHash"] == stress_hash]
        self.check(tx.get("method") == "reportAttestedOutcome" and tx["address"].lower() == self.psc and tx["sender"].lower() == self.relay,
                   "reportAttestedOutcome by the relay to the D2 PSC")
        d, outcome, submitted, sigs = rv.decode_call("PSC", "reportAttestedOutcome", tx["transaction"]["input"])
        submitted = norm(submitted)
        self.check(rv.h(d) == digest and rv.h(outcome) == RECEIPT_OUTCOME and len(sigs) == 1, "outer digest, fixed outcome, one signature")
        sd = receipt_digest(submitted, self.pbc_id, self.psc)
        diff = [k for k in RECEIPT_FIELDS if submitted[k] != honest[k]]
        before, after = rv.load(self.stress_dir / "before.json"), rv.load(self.stress_dir / "after.json")
        self.check(str(before["requests"][digest]["status"]) == "1" and str(before["requests"][digest]["outcomeLogId"]) == "0",
                   "request FORWARDED without an outcome before the report")
        variant, field = self.out["variant"], self.out["field"]
        self.out.update(requestDigest=digest, grantId=gid_, stressTx=stress_hash, changedFields=diff,
                        honestReceiptDigest=rv.h(hd), submittedReceiptDigest=rv.h(sd))
        if variant == "receipt-binding-positive":
            self.check(diff == [] and sigs[0] == hsig, "honest receipt and signature submitted unchanged")
            self.check(tx["receipt"]["status"] == "0x1", "positive report mined with status 1")
            logs = [rv.decode_log(l) for l in tx["receipt"]["logs"]]
            self.check([(l["contract"], l["name"], l["address"]) for l in logs]
                       == [("LSC", "LogRecorded", self.lsc), ("PSC", "AttestedOutcomeRecorded", self.psc)], "LogRecorded then AttestedOutcomeRecorded")
            if len(logs) == 2:
                lf, of = logs[0]["fields"], logs[1]["fields"]
                tuple_t = "(" + ",".join(RECEIPT_TYPES) + ")"
                details = encode(["bytes32", "bytes32", tuple_t, "address"],
                                 [bytes.fromhex(digest[2:]), bytes.fromhex(RECEIPT_OUTCOME[2:]), tuple(honest[k] for k in RECEIPT_FIELDS),
                                  rv.to_checksum_address(self.relay)])
                self.check(int(lf["kind"]) == ra.OUTCOME_KIND and rv.h(lf["subject"]) == digest and bytes(lf["details"]) == details
                           and rv.h(lf["detailsHash"]) == "0x" + keccak(details).hex(), "OUTCOME(4) log, details = abi.encode(digest, outcome, receipt, relay) (PSC.sol:254)")
                self.check(rv.h(of["requestDigest"]) == digest and rv.h(of["grantId"]) == gid_ and rv.h(of["outcomeDigest"]) == RECEIPT_OUTCOME
                           and int(of["dbcBlockNumber"]) == honest["dbcBlockNumber"] and int(of["logId"]) == int(lf["logId"]),
                           "AttestedOutcomeRecorded binds digest, grantId, outcome, receipt block and log id")
                st = after["requests"][digest]
                self.check(str(st["status"]) == "2" and int(st["outcomeLogId"]) == int(lf["logId"]), "status OUTCOME_RECORDED with outcomeLogId")
                self.out.update(logId=int(lf["logId"]))
            for k in ("grants", "nonces", "accessLogCount"):
                self.check(before[k] == after[k], f"DBC {k} unchanged")
            self.check(before["logs"]["dbc"] == after["logs"]["dbc"], "DBC history unchanged")
            return
        self.check(diff == [field], f"exactly the named field {field} changed (got {diff})")
        signer = rv.recover(sd, sigs[0])
        if variant == "receipt-binding-control":
            self.check(signer in self.witnesses and sigs[0] != hsig, "re-signed: a valid WITNESS signature over the altered receipt (A40)")
        else:
            self.check(sigs[0] == hsig and signer not in self.witnesses and rv.recover(hd, sigs[0]) in self.witnesses,
                       "honest signature kept: valid only over the honest receipt, not the altered one")
        code = rv.rejection(tx)
        self.check(code == WRONG_SUBJECT and tx["receipt"]["logs"] == [], "Rejected(WRONG_SUBJECT=2) from the binding check (PSC.sol:266-269), no logs")
        for k in ("grants", "requests", "nonces", "accessLogCount", "logs"):
            self.check(before[k] == after[k], f"{k} unchanged")
        self.out.update(rejectionCode=code, submittedSigner=signer)

    def run(self):
        try:
            self.receipts()
        except Exception as e:  # a review defect or malformed evidence is a failed row, never a pass
            self.f.append(f"review error: {type(e).__name__}: {e}")
        self.out.update(failures=self.f, **{"pass": not self.f})
        return self.out


def main():
    run = Path(sys.argv[1])
    rows = sorted(p.parent.parent for p in run.glob("*/*/receipt-stress/result.json"))
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
