"""Integrated OWNER measurement of the revocation window (A1-0045 W-3). Owner evidence, not C-E2 or gate evidence.

repaired-e, per trial: Alice's fresh request (TTL 30 s) is forwarded and certified (checkpoint C1 accepted, decision D1 collected by
agent 2's unmodified adapter); at T0 the H1 CRL revoking serial 101 is installed on the PBC; the runner accepts the next checkpoint at
T0 + d (d in --delays, "never" = no new checkpoint); every 0.5 s the pre-collected consumeDecision(request, D1) is probed with eth_call
at an explicit DBC block (non-consuming) until the DBC refuses it. W = refusing block timestamp - revocation block timestamp.
Control: a NEW Alice request after T0 is denied at the PBC (AccessDenied).
paper-strict contrast: a tuple forwarded before T0 is probed with the relay's policyEnf (eth_call from the relay) at T0 + 5/35/65 s.

Usage (repository root; the e1/e2 rehearsal venv; Foundry on PATH):
    <venv>/bin/python -I ledger/tools/revocation_window.py --protocol <agent-2 checkout>/protocol --out <dir> [--ports 38545 48545]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import subprocess
import sys
import time

TOOLS = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("e2_rehearsal", TOOLS / "e2_rehearsal.py")
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)
R = E.R


def block_ts(chain, n: int) -> int:
    return int(chain.rpc("eth_getBlockByNumber", [hex(n), False])["timestamp"], 16)


def latest(chain) -> tuple[int, int]:
    b = chain.rpc("eth_getBlockByNumber", ["latest", False])
    return int(b["number"], 16), int(b["timestamp"], 16)


def probe_consume(w, n: int, request, dec) -> str:
    data = w.ACSC.data("consumeDecision", request, {"decision": dec["decision"], "signatures": dec["signatures"]}, dec["credentialRecords"])
    try:
        w.dbc.rpc("eth_call", [{"to": w.ACSC.address, "data": data}, hex(n)])
        return "ACCEPT"
    except R.Reverted as r:
        return r.code


def repaired_trial(w, d):
    s = w.request()
    w.forward(s)
    dec = w.certify(s["requestDigest"])
    w.submit_list(w.sign_list("crl", "H1", "--revoke", "101"))
    t0 = block_ts(w.pbc, w.ev[-1]["block"])
    got = w.tx("new request after revocation", w.pbc, w.relay, w.PSC, "requestAccess", *(lambda x: (x["request"], x["signature"]))(w.request()),
               w.boot["users"]["alice"]["bundle"])
    new_denied = R.ERRORS[int(got["AccessDenied"]["code"])] if "AccessDenied" in got else "FORWARDED"
    barrier_ts, probes, refusal = None, 0, None
    deadline = time.time() + 45
    while time.time() < deadline:
        if d is not None and barrier_ts is None and w.dbc.now() >= t0 + d:
            cp = w.adp.call("collect_checkpoint", {})
            w.tx("barrier acceptState", w.dbc, w.relay, w.KSSC, "acceptState", cp["checkpoint"], cp["signatures"])
            barrier_ts = block_ts(w.dbc, w.ev[-1]["block"])
        n, ts = latest(w.dbc)
        code = probe_consume(w, n, s["request"], dec)
        probes += 1
        if code != "ACCEPT":
            refusal = {"block": n, "timestamp": ts, "code": code}
            break
        time.sleep(0.5)
    req_exp = int(s["request"]["expiresAt"])
    w.restore_trust()
    return {"profile": w.profile, "barrierDelaySeconds": "never" if d is None else d, "revocationBlockTimestamp": t0,
            "barrierAcceptedTimestamp": barrier_ts, "requestExpiresAt": req_exp, "requestTtlLeftAtRevocation": req_exp - t0,
            "firstRefusal": refusal, "windowSeconds": None if refusal is None else refusal["timestamp"] - t0, "probes": probes,
            "newRequestAfterRevocation": new_denied}


def paper_trial(w):
    s = w.request()
    f = w.forward(s)
    w.submit_list(w.sign_list("crl", "H1", "--revoke", "101"))
    t0 = block_ts(w.pbc, w.ev[-1]["block"])
    fwd = {"pbcRequestId": s["requestDigest"], "gid": f["gid"], "dataId": R.DATA_P1, "action": "1"}
    data = w.ACSC.data("policyEnf", fwd, f["verifiedAttributes"])
    out = []
    for offset in (5, 35, 65):
        while w.dbc.now() < t0 + offset:
            time.sleep(0.5)
        n, ts = latest(w.dbc)
        raw = w.dbc.rpc("eth_call", [{"from": R.Account.from_key(R.key("relay")).address, "to": w.ACSC.address, "data": data}, hex(n)])
        allowed, grant = w.ACSC.decode_out("policyEnf", raw)
        out.append({"secondsAfterRevocation": ts - t0, "wouldGrant": allowed is True and int(grant, 16) != 0})
    w.restore_trust()
    return {"profile": w.profile, "revocationBlockTimestamp": t0, "probes": out, "requestExpiresAt": int(s["request"]["expiresAt"])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--protocol", required=True, type=pathlib.Path)
    ap.add_argument("--out", required=True, type=pathlib.Path)
    ap.add_argument("--ports", nargs=2, type=int, default=[38545, 48545])
    ap.add_argument("--delays", nargs="+", default=["0", "5", "10", "20", "never"])
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    anvils = [subprocess.Popen(["anvil", "--port", str(p), "--chain-id", str(c), "--block-time", "1", "--silent"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for p, c in zip(a.ports, (18545, 28545))]
    urls = (f"http://127.0.0.1:{a.ports[0]}", f"http://127.0.0.1:{a.ports[1]}")
    trials, paper = [], None
    try:
        for _ in range(100):
            try:
                R.Chain(urls[0]), R.Chain(urls[1])
                break
            except Exception:
                time.sleep(0.1)
        w = E.World("repaired-e", a.protocol.resolve(), urls, a.out / "repaired-e")
        try:
            for d in a.delays:
                trials.append(repaired_trial(w, None if d == "never" else int(d)))
        finally:
            w.close()
        p = E.World("paper-strict", a.protocol.resolve(), urls, a.out / "paper-strict")
        try:
            paper = paper_trial(p)
        finally:
            p.close()
    finally:
        for proc in anvils:
            proc.terminate()
            proc.wait(timeout=10)
    summary = {"schemaVersion": "hmbc-revocation-window/v0", "note": "OWNER measurement (A1-0045); not C-E2 or gate evidence",
               "repaired": trials, "paperContrast": paper}
    json.dump(summary, open(a.out / "summary.json", "w"), indent=1)
    for t in trials:
        r = t["firstRefusal"] or {}
        print(f"repaired-e d={str(t['barrierDelaySeconds']):5} W={t['windowSeconds']}s refusal={r.get('code')} "
              f"barrierAt=+{None if t['barrierAcceptedTimestamp'] is None else t['barrierAcceptedTimestamp'] - t['revocationBlockTimestamp']}s "
              f"ttlLeft={t['requestTtlLeftAtRevocation']}s newRequest={t['newRequestAfterRevocation']}")
    if paper:
        print("paper-strict", [(p["secondsAfterRevocation"], p["wouldGrant"]) for p in paper["probes"]])
    ok = all(t["firstRefusal"] is not None for t in trials) and paper and all(p["wouldGrant"] for p in paper["probes"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
