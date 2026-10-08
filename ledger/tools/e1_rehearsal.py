"""E1 OWNER REHEARSAL (A1-0032): the 9 frozen e_positive controls end to end. This is owner evidence, NOT a C-E1 result.

Runs, on a private Anvil pair started and stopped here, for each of paper-strict, paper-minimal and repaired-e:
  agent-1 deploy (tools/deploy_local.sh, LEDGER_DEPLOY_FAST=1) -> agent-1 bootstrap producer (tools/bootstrap_fixture.sh) ->
  WrongIssuerAdmin control (H2 list from H1-ca-admin, A2-0015 section 3) -> trust lists + registrations ->
  agent-2's UNMODIFIED adapter process (python -m hmbc_protocol.adapter, JSON lines) for every honest signature and worker action ->
  Alice and Bob flows, with the runner role played here using ONLY the TEST-ONLY relay and CA-admin keys (Option A).
Native evidence (transaction receipts, decoded events, reverts, PSC/KSSC reads) and agent 2's worker log are written per profile, and
each control is compared with its frozen expectedEvents/expectedError.

Usage (repository root; Python 3.13 with agent 2's protocol/requirements.txt, e.g. eth-account 0.14.0; Foundry on PATH):
    <venv>/bin/python -I ledger/tools/e1_rehearsal.py --protocol <agent-2 checkout>/protocol --out <dir> [--ports 38545 48545]
Exit 0 only if all 9 controls match.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

from eth_abi import decode as abi_decode, encode as abi_encode
from eth_account import Account
from eth_utils import keccak, to_checksum_address

LEDGER = pathlib.Path(__file__).resolve().parents[1]
ROOT = LEDGER.parent
ERRORS = ["NONE", "BAD_SIGNATURE", "WRONG_SUBJECT", "WRONG_DESTINATION", "UNKNOWN_AUTHORITY", "STALE_ANCHOR", "STALE_STATE", "EXPIRED",
          "REPLAY", "POLICY_DENIED", "INSUFFICIENT_QUORUM", "DUPLICATE_SIGNER", "WRONG_EPOCH", "NOT_COMMITTED", "ADAPTER_UNAVAILABLE",
          "NOT_IMPLEMENTED_IN_PHASE", "UNAUTHORIZED_CALLER", "NOT_REGISTERED", "ALREADY_REGISTERED", "REVOKED", "MALFORMED", "WRONG_PROFILE"]
REJECTED = keccak(text="Rejected(uint8)")[:4]
ANVIL_KEY0 = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"  # public Anvil default account, TEST-ONLY deployer
DATA_P1 = "0x" + keccak(text="HMBC.data.P1.MHR").hex()
ROLE_DOCTOR = "0x" + keccak(text="HMBC.role.Doctor").hex()
ROLE_ON_DUTY = "0x" + keccak(text="HMBC.role.OnDuty").hex()
P1_POLICY = {"clauses": [[{"role": ROLE_DOCTOR, "kind": "1", "issuerMode": "0"}, {"role": ROLE_ON_DUTY, "kind": "2", "issuerMode": "2"}]]}
FROZEN = {  # interfaces/v1/scenarios/e_positive.json (freeze E0-v1-r6-20261008)
    "Alice": (["REQUEST_LOGGED", "PBC_DECIDED", "DBC_AUTHORIZED", "RELEASE_INTENT", "RELEASE_SENT", "OUTCOME_RECORDED"], None),
    "Bob": (["REQUEST_LOGGED", "PBC_DECIDED"], "POLICY_DENIED"),
    "WrongIssuerAdmin": ([], "UNAUTHORIZED_CALLER"),
}


def key(label: str) -> str:
    return "0x" + keccak(text="hmbc-e0-synthetic-key:" + label).hex()


def addr(label: str) -> str:
    return Account.from_key(key(label)).address.lower()


class Reverted(Exception):
    def __init__(self, code: str, data: str):
        super().__init__(code)
        self.code, self.data = code, data


# ------------------------------------------------------------------ ABI (from agent 1's exported ABIs)

def _canon(p: dict) -> str:
    t = p["type"]
    if t.startswith("tuple"):
        return "(" + ",".join(_canon(c) for c in p["components"]) + ")" + t[5:]
    return t


def _to_py(v, p: dict):
    t = p["type"]
    if t.endswith("[]"):
        inner = {**p, "type": t[:-2]}
        return [_to_py(x, inner) for x in v]
    if t == "tuple":
        comps = p["components"]
        return tuple(_to_py(v[c["name"]] if isinstance(v, dict) else v[i], c) for i, c in enumerate(comps))
    if t.startswith(("uint", "int")):
        return int(v, 16) if isinstance(v, str) and v.startswith("0x") else int(v)
    if t == "bool":
        return v in (True, "true", "1", 1)
    if t.startswith("bytes"):
        return bytes.fromhex(v[2:])
    return v


def _to_json(v, p: dict):
    t = p["type"]
    if t.endswith("[]"):
        inner = {**p, "type": t[:-2]}
        return [_to_json(x, inner) for x in v]
    if t == "tuple":
        return {c["name"]: _to_json(x, c) for x, c in zip(v, p["components"])}
    if isinstance(v, bytes):
        return "0x" + v.hex()
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return str(v)
    return v.lower() if isinstance(v, str) and v.startswith("0x") else v


class Contract:
    def __init__(self, name: str, address: str):
        self.name, self.address = name, address.lower()
        self.abi = json.load(open(LEDGER / "exports" / "abi" / f"{name}.json"))
        self.fns = {e["name"]: e for e in self.abi if e["type"] == "function"}
        self.events = {keccak(text=f"{e['name']}({','.join(_canon(i) for i in e['inputs'])})"): e for e in self.abi if e["type"] == "event"}

    def data(self, fn: str, *args) -> str:
        f = self.fns[fn]
        sel = keccak(text=f"{fn}({','.join(_canon(i) for i in f['inputs'])})")[:4]
        return "0x" + (sel + abi_encode([_canon(i) for i in f["inputs"]], [_to_py(a, i) for a, i in zip(args, f["inputs"])])).hex()

    def decode_out(self, fn: str, raw: str):
        outs = self.fns[fn]["outputs"]
        vals = abi_decode([_canon(o) for o in outs], bytes.fromhex(raw[2:]))
        res = [_to_json(v, o) for v, o in zip(vals, outs)]
        return res[0] if len(res) == 1 else res

    def decode_logs(self, receipt: dict) -> list[dict]:
        out = []
        for log in receipt["logs"]:
            if log["address"].lower() != self.address:
                continue
            ev = self.events.get(bytes.fromhex(log["topics"][0][2:]))
            if ev is None:
                continue
            idx = [i for i in ev["inputs"] if i["indexed"]]
            non = [i for i in ev["inputs"] if not i["indexed"]]
            args = {i["name"]: _to_json(abi_decode([_canon(i)], bytes.fromhex(t[2:]))[0], i) for i, t in zip(idx, log["topics"][1:])}
            vals = abi_decode([_canon(i) for i in non], bytes.fromhex(log["data"][2:]))
            args.update({i["name"]: _to_json(v, i) for i, v in zip(non, vals)})
            out.append({"contract": self.name, "event": ev["name"], "args": args})
        return out


# ------------------------------------------------------------------ JSON-RPC

class Chain:
    def __init__(self, url: str):
        self.url = url
        self.chain_id = int(self.rpc("eth_chainId"), 16)

    def rpc(self, method: str, params=None):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode()
        req = urllib.request.Request(self.url, body, {"Content-Type": "application/json"})
        res = json.loads(urllib.request.urlopen(req, timeout=30).read())
        if "error" in res:
            data = res["error"].get("data")
            data = data.get("data") if isinstance(data, dict) else data
            if isinstance(data, str) and data.startswith("0x" + REJECTED.hex()):
                raise Reverted(ERRORS[int(data[10:], 16)], data)
            raise RuntimeError(f"{method}: {res['error']}")
        return res["result"]

    def now(self) -> int:
        return int(self.rpc("eth_getBlockByNumber", ["latest", False])["timestamp"], 16)

    def call(self, c: Contract, fn: str, *args):
        return c.decode_out(fn, self.rpc("eth_call", [{"to": c.address, "data": c.data(fn, *args)}, "latest"]))

    def send(self, signer: str, c: Contract, fn: str, *args, expect: str | None = None) -> dict:
        """Submit a transaction. expect=<code>: the call must revert with Rejected(<code>); the reverted transaction is still mined
        (fixed gas) so the native evidence is a status-0 receipt."""
        data, frm = c.data(fn, *args), Account.from_key(signer).address
        try:
            gas = int(self.rpc("eth_estimateGas", [{"from": frm, "to": c.address, "data": data}]), 16) + 50_000
            if expect:
                raise SystemExit(f"{c.name}.{fn} was expected to revert {expect} but would succeed")
        except Reverted as r:
            if r.code != expect:
                raise
            gas = 1_000_000
        tx = {"nonce": int(self.rpc("eth_getTransactionCount", [frm, "pending"]), 16), "gasPrice": int(self.rpc("eth_gasPrice"), 16),
              "gas": gas, "to": to_checksum_address(c.address), "value": 0, "data": data, "chainId": self.chain_id}
        signed = Account.sign_transaction(tx, signer)
        raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        h = self.rpc("eth_sendRawTransaction", ["0x" + raw.hex().removeprefix("0x")])
        for _ in range(300):
            rec = self.rpc("eth_getTransactionReceipt", [h])
            if rec:
                break
            time.sleep(0.1)
        else:
            raise SystemExit(f"no receipt for {h}")
        status = int(rec["status"], 16)
        if (status == 1) == bool(expect):
            raise SystemExit(f"{c.name}.{fn}: unexpected status {status}")
        return {"tx": h, "block": int(rec["blockNumber"], 16), "status": status, "revert": expect, "receipt": rec}


class Adapter:
    """agent 2's adapter process, started exactly per A2-0014 section 2 (private 0700 state dir, pinned deployment)."""

    def __init__(self, protocol: pathlib.Path, deployment: pathlib.Path, state_dir: pathlib.Path):
        self.dep, self.state_dir, self.protocol, self.transcript = json.load(open(deployment)), state_dir, protocol, []
        self.p = subprocess.Popen([sys.executable, "-m", "hmbc_protocol.adapter", "--state-dir", str(state_dir), "--deployment", str(deployment)],
                                  cwd=protocol, env={"PYTHONPATH": str(protocol), "PATH": "/usr/bin:/bin"},
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def call(self, op: str, inp: dict) -> dict:
        self.p.stdin.write(json.dumps({"schemaVersion": "v1", "operation": op, "input": inp, "deploymentManifest": self.dep}) + "\n")
        self.p.stdin.flush()
        resp = json.loads(self.p.stdout.readline())
        self.transcript.append({"operation": op, "input": inp, "response": resp})
        if not resp.get("ok"):
            raise SystemExit(f"adapter {op} failed: {resp.get('error')}")
        return resp["result"]

    def worker_log(self) -> dict:
        # The adapter keeps the worker database in <state-dir>/worker (adapter.py `_worker`); A2-0014 section 2 says "--state-dir <same
        # dir>", which fails ("no worker.sqlite"). Reported to agent 2 in A1-0033; the subdirectory is used here.
        out = subprocess.run([sys.executable, "-m", "hmbc_protocol.worker_log", "--state-dir", str(self.state_dir / "worker")], cwd=self.protocol,
                             env={"PYTHONPATH": str(self.protocol), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True, check=True)
        return json.loads(out.stdout)

    def close(self) -> None:
        self.p.stdin.close()
        err = self.p.stderr.read()
        self.p.wait(timeout=20)
        if self.p.returncode != 0 or err:
            raise SystemExit(f"adapter exit {self.p.returncode}: {err[:400]}")


# ------------------------------------------------------------------ one profile

def run_profile(profile: str, protocol: pathlib.Path, urls: tuple[str, str], out: pathlib.Path) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    run_id = f"reh-{profile}-{os.getpid()}"
    env = {**os.environ, "DEPLOYER_PK": ANVIL_KEY0, "LEDGER_DEPLOY_FAST": "1"}
    subprocess.run([str(LEDGER / "tools" / "deploy_local.sh"), *urls, profile, "complete-details", run_id], cwd=ROOT, env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    dep_dir = LEDGER / "exports" / "deployments" / run_id
    dep_file = out / "deployment.json"
    shutil.copy(dep_dir / "deployment.json", dep_file)
    shutil.rmtree(dep_dir)
    subprocess.run([str(LEDGER / "tools" / "bootstrap_fixture.sh"), urls[0], str(dep_file), str(out / "bootstrap.json")], cwd=ROOT,
                   check=True, stdout=subprocess.DEVNULL)
    dep, boot = json.load(open(dep_file)), json.load(open(out / "bootstrap.json"))
    pbc, dbc = Chain(urls[0]), Chain(urls[1])
    pc, dc = dep["chains"]["pbc"]["contracts"], dep["chains"]["dbc"]["contracts"]
    PSC, TMSC, RSC = Contract("PSC", pc["PSC"]), Contract("TMSC", pc["TMSC"]), Contract("RSC", pc["RSC"])
    KSSC, ACSC = Contract("KSSC", dc["KSSC"]), Contract("ACSC", dc["ACSC"])
    relay, repaired = key("relay"), profile == "repaired-e"
    ev: list[dict] = []
    results = []

    def log(step: str, r: dict, contracts) -> dict:
        events = [e for c in contracts for e in c.decode_logs(r["receipt"])]
        ev.append({"step": step, "tx": r["tx"], "block": r["block"], "status": r["status"], "revert": r["revert"], "events": events})
        return {e["event"]: e["args"] for e in events}

    # WrongIssuerAdmin (frozen control; A2-0015 section 3 sequencing): H2's own list submitted by H1's CA-Admin, before the legitimate one.
    h2 = boot["trustLists"][2]
    epoch0 = pbc.call(TMSC, "authEpoch")
    r = pbc.send(key("H1-ca-admin"), TMSC, "updateRevocationList", h2["list"], h2["signature"], expect="UNAUTHORIZED_CALLER")
    got = log("WrongIssuerAdmin H2 list from H1-ca-admin", r, [TMSC])
    st = pbc.call(TMSC, "revocationListState", h2["list"]["authority"])
    observed = []
    results.append(_verdict(profile, "WrongIssuerAdmin", observed, "UNAUTHORIZED_CALLER",
                            got == {} and pbc.call(TMSC, "authEpoch") == epoch0 and st["published"] is False))

    for item in boot["trustLists"]:
        fn = "updateRevocationList" if item["kind"] == "RevocationList" else "updateTemporalAcl"
        log(f"{item['kind']} via {item['submitterRole']}", pbc.send(key(item["submitterRole"]), TMSC, fn, item["list"], item["signature"]), [TMSC])
    for label in ("alice", "bob"):
        u = boot["users"][label]
        log(f"register {label}", pbc.send(relay, RSC, "register", u["registration"], u["possessionSignature"], u["certificate"]), [RSC])

    state = pathlib.Path(tempfile.mkdtemp(prefix="adapter-", dir=out))
    os.chmod(state, 0o700)
    adp = Adapter(protocol, dep_file, state)
    try:
        adp.call("encrypt_record", {"record": {"dataId": DATA_P1, "owner": addr("H2-root"),
                                               "payloadDigest": "0x" + keccak(text="synthetic payload P1").hex()},
                                    "policy": P1_POLICY, "keyEpoch": "0"})
        for actor, label, nonce in (("Alice", "alice", "1"), ("Bob", "bob", "7")):
            u, obs, err = boot["users"][label], [], None
            fx = dep["fixture"]
            req = {"sourceChainId": str(pbc.chain_id), "destinationChainId": str(dbc.chain_id), "psc": PSC.address, "kssc": KSSC.address,
                   "gid": u["gid"], "dataId": DATA_P1, "action": "1", "policyVersion": fx["policyVersion"],
                   "authEpoch": pbc.call(TMSC, "authEpoch"), "keyEpoch": fx["keyEpoch"], "nonce": nonce, "expiresAt": str(pbc.now() + 30),
                   "recipientKeyHash": u["recipientKeyHash"]}
            signed = adp.call("prepare_request", {"request": req, "signingKeyRef": f"keyref:user:{label}"})
            digest = signed["requestDigest"]
            got = log(f"{actor} requestAccess", pbc.send(relay, PSC, "requestAccess", signed["request"], signed["signature"], u["bundle"]),
                      [PSC])
            fwd = got.get("AccessForwarded")
            if fwd and fwd["requestLogId"] != "0":
                obs += ["REQUEST_LOGGED", "PBC_DECIDED"]
            grant = None
            if repaired:
                cp = adp.call("collect_checkpoint", {})
                log(f"{actor} acceptState", dbc.send(relay, KSSC, "acceptState", cp["checkpoint"], cp["signatures"]), [KSSC])
                dec = adp.call("collect_decision", {"requestDigest": digest})
                got = log(f"{actor} consumeDecision", dbc.send(relay, ACSC, "consumeDecision", signed["request"],
                                                               {"decision": dec["decision"], "signatures": dec["signatures"]},
                                                               dec["credentialRecords"]), [ACSC, KSSC])
            else:
                f = {"pbcRequestId": digest, "gid": u["gid"], "dataId": DATA_P1, "action": "1"}
                got = log(f"{actor} policyEnf", dbc.send(relay, ACSC, "policyEnf", f, fwd["verifiedAttributes"]), [ACSC, KSSC])
            acc = got.get("AccessLog", {})
            if "GrantIssued" in got and acc.get("allowed") is True:
                obs.append("DBC_AUTHORIZED")
                grant = got["GrantIssued"]["grantId"]
            elif acc.get("allowed") is False:
                err = ERRORS[int(acc["code"])]
            if grant:
                rel = adp.call("release", {"grantId": grant})
                fin = adp.call("finish_decryption", {"response": rel, "userKeyRef": f"keyref:user:{label}"})
                wl = adp.worker_log()
                if any(e["type"] == "RELEASE_INTENT" and e["grantId"] == grant for e in wl["events"]):
                    obs.append("RELEASE_INTENT")
                if any(e["type"] == "RELEASE_SENT" and e["grantId"] == grant for e in wl["events"]) and fin.get("decryptable") is True:
                    obs.append("RELEASE_SENT")
                outcome = "0x" + keccak(text=f"rehearsal outcome {actor}").hex()
                if repaired:
                    att = adp.call("attest_grant", {"grantId": grant})
                    got = log(f"{actor} reportAttestedOutcome", pbc.send(relay, PSC, "reportAttestedOutcome", digest, outcome,
                                                                         att["receipt"], att["signatures"]), [PSC])
                else:
                    got = log(f"{actor} reportOutcome", pbc.send(relay, PSC, "reportOutcome", digest, grant, outcome), [PSC])
                if ("AttestedOutcomeRecorded" in got or "OutcomeRecorded" in got) and pbc.call(PSC, "getRequest", digest)["status"] == "2":
                    obs.append("OUTCOME_RECORDED")
            extra = True
            if actor == "Bob":  # repaired-e expectedLedgerChecks: DBC_POLICY_DENIAL_LOGGED, NONCE_UNCHANGED (paper: denial logged as well)
                extra = err == "POLICY_DENIED" and grant is None and dbc.call(KSSC, "nonceConsumed", u["gid"], nonce) is False
            results.append(_verdict(profile, actor, obs, err, extra))
    finally:
        json.dump(_redact(adp.transcript), open(out / "adapter-transcript.json", "w"), indent=1)
        json.dump(ev, open(out / "ledger-evidence.json", "w"), indent=1)
        try:
            adp.close()
            json.dump(adp.worker_log(), open(out / "worker-log.json", "w"), indent=1)
        finally:
            shutil.rmtree(state)
    return results


def _redact(x):
    """Release tokens (symbolic capabilities) never enter evidence: keep only keccak256(token), like agent 2's worker_log."""
    if isinstance(x, dict):
        return {k: ({"tokenDigest": "0x" + keccak(bytes.fromhex(v[2:])).hex()} if k == "token" and isinstance(v, str) else _redact(v))
                for k, v in x.items()}
    return [_redact(v) for v in x] if isinstance(x, list) else x


def _verdict(profile: str, actor: str, observed: list[str], error: str | None, extra: bool) -> dict:
    exp_events, exp_error = FROZEN[actor]
    ok = observed == exp_events and error == exp_error and extra
    return {"control": f"E-control-{actor}-{profile}", "expectedEvents": exp_events, "observedEvents": observed,
            "expectedError": exp_error, "observedError": error, "nativeChecks": extra, "match": ok}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--protocol", required=True, type=pathlib.Path)
    ap.add_argument("--out", required=True, type=pathlib.Path)
    ap.add_argument("--ports", nargs=2, type=int, default=[38545, 48545])
    ap.add_argument("--profiles", nargs="+", default=["paper-strict", "paper-minimal", "repaired-e"])
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    anvils = [subprocess.Popen(["anvil", "--port", str(port), "--chain-id", str(cid), "--block-time", "1", "--silent"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
              for port, cid in zip(a.ports, (18545, 28545))]
    urls = (f"http://127.0.0.1:{a.ports[0]}", f"http://127.0.0.1:{a.ports[1]}")
    results = []
    try:
        for _ in range(100):
            try:
                Chain(urls[0]), Chain(urls[1])
                break
            except Exception:
                time.sleep(0.1)
        for p in a.profiles:
            results += run_profile(p, a.protocol.resolve(), urls, a.out / p)
    finally:
        for p in anvils:
            p.terminate()
            p.wait(timeout=10)
    blob = "".join(f.read_text() for f in a.out.rglob("*.json"))
    leaked = [lbl for lbl in ("alice", "bob", "relay", "witness-1", "H1-root", "H2-root", "H1-ca-admin", "H2-ca-admin") if key(lbl)[2:] in blob]
    leaked += ["release-token"] if re.search(r'"token":\s*"0x', blob) else []
    summary = {"schemaVersion": "hmbc-e1-owner-rehearsal/v0", "note": "OWNER rehearsal (A1-0032); not a C-E1 result or gate evidence",
               "results": results, "privateKeysInOutputs": leaked, "allMatch": all(r["match"] for r in results) and not leaked}
    json.dump(summary, open(a.out / "summary.json", "w"), indent=1)
    for r in results:
        print(f"{'MATCH' if r['match'] else 'DIFF '} {r['control']}: events={r['observedEvents']} error={r['observedError']} native={r['nativeChecks']}")
    print("ALL 9 CONTROLS MATCH" if summary["allMatch"] and len(results) == 9 else "REHEARSAL MISMATCH", "| key leaks:", leaked)
    return 0 if summary["allMatch"] else 1


if __name__ == "__main__":
    sys.exit(main())
