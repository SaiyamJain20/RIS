"""Agent 1 ledger-scope review of E02 trust-freshness (SL5) live evidence (solo phase).

Independent of agent 3's oracle (evaluation/oracles/trust.py): every checked value is re-derived
from the raw native records (<row>/<profile>/trust-instance/pbc-native/transactions.json) with the
ledger ABIs and ProtocolTypes.sol (HMBCHash.hashRevocationList / revocationListDigest: domain
HMBCTrust, version 1, PBC chain id, TMSC), reusing the decoders of review_audit_stress_evidence.py.

  wrong-issuer          the mined updateRevocationList is sent by the H1 CA-admin with an H2 list whose
                        signature recovers to the H2 root (valid) at version = current H2 version + 1;
                        Rejected(UNAUTHORIZED_CALLER=16) (TMSC.sol:181, before the signature check),
                        no logs; anchors/authEpoch/logs unchanged. Same in every profile.
  signed-list-rollback  install: H1 admin, H1 list version 2 revoking [101], H1-root signature, status 1,
                        TrustAnchorUpdated(version 2). Replay: calldata list and signature byte-identical
                        to the bootstrap H1 CRL transaction found in the same PBC records (version 1,
                        no revocations), still valid at the replay block (validUntil > block ts, so a
                        repaired rejection can only be TMSC.sol:190).
                        paper-*: replay status 1, TrustAnchorUpdated(version 1, authEpoch +1); the
                        request carries the resulting authEpoch and is forwarded with Alice's H1
                        credential at anchorVersion 1.
                        repaired-e: replay Rejected(STALE_ANCHOR=5), no logs; the request carries the
                        unchanged authEpoch and is AccessDenied REVOKED(19).

Usage: .venv/bin/python -I ledger/tools/review_trust_stress_evidence.py <evidence run dir> > out.json
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
_spec.loader.exec_module(ra)  # also registers RSC/TMSC events
rv = ra.rv
# TMSC/RSC functions for calldata decoding (the committed SL2/SL3 tools only load ACSC/KSSC/PSC/LSC).
for _c in ("TMSC", "RSC"):
    rv.ABI.setdefault(_c, json.loads((rv.ROOT / f"ledger/exports/abi/{_c}.json").read_text()))

LIST_T = keccak(text="RevocationList(address authority,uint64 version,uint64 validUntil,uint64[] revokedSerials)")
UNAUTHORIZED_CALLER, STALE_ANCHOR, REVOKED = 16, 5, 19
ALICE_SERIAL = 101


def list_digest(lst, pbc_chain_id, tmsc):
    serials = b"".join(int(s).to_bytes(32, "big") for s in lst["revokedSerials"])
    struct = keccak(encode(["bytes32", "address", "uint64", "uint64", "bytes32"],
                           [LIST_T, rv.to_checksum_address(lst["authority"]), int(lst["version"]), int(lst["validUntil"]), keccak(serials)]))
    return rv.typed(rv.domain("HMBCTrust", pbc_chain_id, tmsc), struct)


class Review(ra.Review):
    def __init__(self, row_dir):
        self.f = []
        inst = row_dir / "trust-instance"
        self.stress_dir = row_dir / "trust-stress"
        self.dep = rv.load(inst / "deployment.json")
        self.boot = rv.load(inst / "bootstrap-checked.json")
        self.dbc_txs = rv.load(inst / "dbc-native/transactions.json")
        self.pbc_txs = rv.load(inst / "pbc-native/transactions.json")
        self.result = rv.load(self.stress_dir / "result.json")
        p, dbc = self.dep["chains"]["pbc"], self.dep["chains"]["dbc"]
        self.pbc_id, self.dbc_id = int(p["chainId"]), int(dbc["chainId"])
        self.tmsc, self.psc = p["contracts"]["TMSC"].lower(), p["contracts"]["PSC"].lower()
        self.kssc = dbc["contracts"]["KSSC"].lower()
        self.relay = self.dep["fixture"]["relay"]["address"].lower()
        self.alice = self.boot["users"]["alice"]["gid"].lower()
        self.auth = {a["id"]: a for a in self.dep["fixture"]["authorities"]}
        self.out = dict(row=row_dir.parent.name, profile=self.dep["profile"], variant=self.result["variant"])

    def lists(self):
        """Every updateRevocationList in the D2 PBC records, decoded, in order."""
        out = []
        for t in self.by_method(self.pbc_txs, "updateRevocationList"):
            lst, sig = rv.decode_call("TMSC", "updateRevocationList", t["transaction"]["input"])
            out.append(dict(tx=t, list=lst, sig=sig, signer=rv.recover(list_digest(lst, self.pbc_id, self.tmsc), sig),
                            status=t["receipt"]["status"], sender=t["sender"].lower(), ts=ra.ts_of(t)))
        return out

    def anchor_events(self, tx):
        return [rv.decode_log(l)["fields"] for l in tx["receipt"]["logs"] if rv.decode_log(l)["name"] == "TrustAnchorUpdated"]

    def same_state(self, a, b, keys=("anchors", "authEpoch", "revoked", "credentials", "logs")):
        for k in keys:
            self.check(a[k] == b[k], f"{k} unchanged")

    def wrong_issuer(self):
        h1, h2 = self.auth["H1"], self.auth["H2"]
        stress_hash = rv.load(self.stress_dir / "stress-transaction.json")["hash"]
        rows = self.lists()
        (s,) = [r for r in rows if r["tx"]["transactionHash"] == stress_hash]
        before, after = rv.load(self.stress_dir / "before.json"), rv.load(self.stress_dir / "after.json")
        self.check(s["sender"] == h1["caAdmins"][0].lower() and s["tx"]["address"].lower() == self.tmsc, "sent by the H1 CA-admin to the D2 TMSC")
        self.check(s["list"]["authority"].lower() == h2["root"].lower() and s["signer"] == h2["root"].lower(),
                   "an H2 list carrying a valid H2-root signature (ledger HMBCTrust digest)")
        h2_before = before["anchors"][h2["root"]] if h2["root"] in before["anchors"] else before["anchors"][h2["root"].lower()]
        self.check(int(s["list"]["version"]) == int(h2_before["version"]) + 1, "next H2 version")
        code = rv.rejection(s["tx"])
        self.check(code == UNAUTHORIZED_CALLER and s["tx"]["receipt"]["logs"] == [], "Rejected(UNAUTHORIZED_CALLER=16) at TMSC.sol:181, no logs")
        self.same_state(before, after)
        self.out.update(stressTx=stress_hash, rejectionCode=code, listVersion=int(s["list"]["version"]))

    def rollback(self):
        h1 = self.auth["H1"]
        admin, root = h1["caAdmins"][0].lower(), h1["root"].lower()
        rows = [r for r in self.lists() if r["list"]["authority"].lower() == root]
        boot = [r for r in rows if r["status"] == "0x1" and int(r["list"]["version"]) == 1]
        self.check(len(boot) >= 1, "bootstrap H1 CRL v1 transaction present in the PBC records")
        stress_hash = rv.load(self.stress_dir / "stress-transaction.json")["hash"]
        install_hash = rv.load(self.stress_dir / "install-transaction.json")["hash"]
        (ins,) = [r for r in rows if r["tx"]["transactionHash"] == install_hash]
        (rep,) = [r for r in rows if r["tx"]["transactionHash"] == stress_hash]
        b = boot[0]
        self.check(b["signer"] == root and list(b["list"]["revokedSerials"]) == [], "bootstrap v1: H1-root signed, no revocations")
        # Install v2.
        self.check(ins["sender"] == admin and ins["signer"] == root and int(ins["list"]["version"]) == 2
                   and [int(x) for x in ins["list"]["revokedSerials"]] == [ALICE_SERIAL] and ins["status"] == "0x1",
                   "install: H1 admin, H1-root-signed v2 revoking 101, status 1")
        ev = self.anchor_events(ins["tx"])
        self.check(len(ev) == 1 and int(ev[0]["version"]) == 2, "TrustAnchorUpdated(version 2)")
        epoch_installed = int(ev[0]["authEpoch"]) if ev else None
        # Replay of the bootstrap list, byte-identical.
        self.check(rep["sender"] == admin and rep["list"] == b["list"] and rep["sig"] == b["sig"],
                   "replay calldata list and signature byte-identical to the bootstrap H1 CRL transaction")
        self.check(int(rep["list"]["validUntil"]) > rep["ts"], "old list still valid at the replay block (only TMSC.sol:190 can reject)")
        paper = self.dep["profile"] != "repaired-e"
        if paper:
            rev = self.anchor_events(rep["tx"])
            self.check(rep["status"] == "0x1" and len(rev) == 1 and int(rev[0]["version"]) == 1
                       and epoch_installed is not None and int(rev[0]["authEpoch"]) == epoch_installed + 1,
                       "paper replay accepted: TrustAnchorUpdated(version 1, authEpoch +1); version goes backwards")
            expected_epoch = int(rev[0]["authEpoch"]) if rev else None
        else:
            code = rv.rejection(rep["tx"])
            self.check(rep["status"] == "0x0" and code == STALE_ANCHOR and rep["tx"]["receipt"]["logs"] == [],
                       "repaired replay Rejected(STALE_ANCHOR=5), no logs")
            expected_epoch = epoch_installed
            self.out.update(rejectionCode=code)
        # Request after the replay.
        reqs = self.by_method(self.pbc_txs, "requestAccess")
        self.check(len(reqs) == 1 and self.pbc_txs.index(reqs[0]) > self.pbc_txs.index(rep["tx"]), "one request, after the replay")
        req, _sig, _bundle = rv.decode_call("PSC", "requestAccess", reqs[0]["transaction"]["input"])
        digest = rv.h(rv.request_digest(req))
        self.check(rv.h(req["gid"]) == self.alice and int(req["authEpoch"]) == expected_epoch, "Alice request carries the current authEpoch")
        logs = [rv.decode_log(l) for l in reqs[0]["receipt"]["logs"]]
        names = [l["name"] for l in logs]
        if paper:
            fwd = [l["fields"] for l in logs if l["name"] == "AccessForwarded"]
            self.check(len(fwd) == 1 and rv.h(fwd[0]["requestDigest"]) == digest, f"paper: AccessForwarded (got {names})")
            if fwd:
                # CredentialRecord = (issuer, role, kind, serial, anchorVersion, validUntil). Alice also holds an H1
                # temporal role (kind 2, TempACL-anchored); the CRL-anchored record is her long-term certificate
                # (kind CREDENTIAL_LONG_TERM = 1, serial 101).
                recs = [r for r in fwd[0]["verifiedAttributes"] if rv.h(r[0]) == root and int(r[2]) == 1 and int(r[3]) == ALICE_SERIAL]
                self.check(len(recs) == 1 and int(recs[0][4]) == 1,
                           "Alice's H1 long-term credential (serial 101) verified at CRL anchorVersion 1 (the rolled-back list)")
        else:
            den = [l["fields"] for l in logs if l["name"] == "AccessDenied"]
            self.check(len(den) == 1 and rv.h(den[0]["requestDigest"]) == digest and int(den[0]["code"]) == REVOKED,
                       f"repaired: AccessDenied REVOKED(19) under v2 (got {names})")
        self.out.update(installTx=install_hash, replayTx=stress_hash, requestDigest=digest, requestAuthEpoch=int(req["authEpoch"]),
                        oldValidUntil=int(rep["list"]["validUntil"]), replayTimestamp=rep["ts"], requestEvents=names)

    def run(self):
        try:
            {"wrong-issuer": self.wrong_issuer, "signed-list-rollback": self.rollback}[self.out["variant"]]()
        except Exception as e:  # a review defect or malformed evidence is a failed row, never a pass
            self.f.append(f"review error: {type(e).__name__}: {e}")
        self.out.update(failures=self.f, **{"pass": not self.f})
        return self.out


def main():
    run = Path(sys.argv[1])
    rows = sorted(p.parent.parent for p in run.glob("*/*/trust-stress/result.json"))
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
