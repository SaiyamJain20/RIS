"""Live check of the E2 signed-list producer (A1-0034) against the E02 trust-anchor behaviours. Owner evidence only.

Usage (repository root; the same Python 3.13 venv as e1_rehearsal.py; Foundry on PATH):
    <venv>/bin/python -I ledger/tools/check_sign_list.py --out <dir> [--ports 38545 48545]
Per profile (paper-strict, paper-minimal, repaired-e), on a private Anvil pair: deploy, bootstrap (A1-0030), then lists from
tools/sign_list.sh submitted by the right CA-Admin, reading TMSC.checkCredentials(alice) after each step:
  1 duty window shortened to end in 3 s          -> after it ends: EXPIRED (7)
  2 duty window restored (next version)           -> NONE
  3 H1 CRL revoking Alice's serial 101            -> REVOKED (19)
  4 replay of the bootstrap's older signed H1 CRL -> paper: accepted, Alice NONE again (rollback; SPEC_GAP);
                                                     repaired-e: Rejected(STALE_ANCHOR), Alice stays REVOKED
  5 equal version, different content (H1 CRL)     -> paper: accepted; repaired-e: Rejected(STALE_ANCHOR)
  6 refusals: unknown authority H9, wrong RPC     -> exit 1, no output file
Exit 0 only if every expectation holds.
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
import time

TOOLS = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("e1_rehearsal", TOOLS / "e1_rehearsal.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
LEDGER, ROOT = R.LEDGER, R.ROOT

EXPECT = {  # step -> (paper result, repaired-e result); a result is the Alice code, or "REJECT:<code>" for the submission
    "1 duty ended": ("EXPIRED", "EXPIRED"),
    "2 duty restored": ("NONE", "NONE"),
    "3 Alice revoked": ("REVOKED", "REVOKED"),
    "4 old CRL replayed": ("ACCEPT", "REJECT:STALE_ANCHOR"),
    "4 Alice after replay": ("NONE", "REVOKED"),
    "5 equal version swap": ("ACCEPT", "REJECT:STALE_ANCHOR"),
    "6 unknown authority refused": ("REFUSED", "REFUSED"),
    "6 wrong RPC refused": ("REFUSED", "REFUSED"),
}


def sign(urls, dep, out, *args) -> int:
    return subprocess.run([str(TOOLS / "sign_list.sh"), urls[0], str(dep), str(out), *args], cwd=ROOT,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode


def run_profile(profile: str, urls, out: pathlib.Path) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    run_id = f"sl-{profile}-{os.getpid()}"
    env = {**os.environ, "DEPLOYER_PK": R.ANVIL_KEY0, "LEDGER_DEPLOY_FAST": "1"}
    subprocess.run([str(TOOLS / "deploy_local.sh"), *urls, profile, "complete-details", run_id], cwd=ROOT, env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    dep = out / "deployment.json"
    shutil.copy(LEDGER / "exports" / "deployments" / run_id / "deployment.json", dep)
    shutil.rmtree(LEDGER / "exports" / "deployments" / run_id)
    subprocess.run([str(TOOLS / "bootstrap_fixture.sh"), urls[0], str(dep), str(out / "bootstrap.json")], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL)
    boot, d = json.load(open(out / "bootstrap.json")), json.load(open(dep))
    pbc = R.Chain(urls[0])
    pc = d["chains"]["pbc"]["contracts"]
    TMSC, RSC = R.Contract("TMSC", pc["TMSC"]), R.Contract("RSC", pc["RSC"])
    for item in boot["trustLists"]:
        fn = "updateRevocationList" if item["kind"] == "RevocationList" else "updateTemporalAcl"
        pbc.send(R.key(item["submitterRole"]), TMSC, fn, item["list"], item["signature"])
    for label in ("alice", "bob"):
        u = boot["users"][label]
        pbc.send(R.key("relay"), RSC, "register", u["registration"], u["possessionSignature"], u["certificate"])
    alice = boot["users"]["alice"]
    paper = profile != "repaired-e"
    results, log = [], []

    def code() -> str:
        return R.ERRORS[int(pbc.call(TMSC, "checkCredentials", alice["gid"], alice["bundle"], str(pbc.now()))[0])]

    def submit(path: pathlib.Path, expect: str | None = None) -> str:
        item = json.load(open(path))["item"] if "item" in json.load(open(path)) else json.load(open(path))
        fn = "updateRevocationList" if item["kind"] == "RevocationList" else "updateTemporalAcl"
        r = pbc.send(R.key(item["submitterRole"]), TMSC, fn, item["list"], item["signature"], expect=expect)
        log.append({"list": path.name, "kind": item["kind"], "version": item["list"]["version"], "tx": r["tx"], "status": r["status"],
                    "revert": r["revert"]})
        return "ACCEPT" if r["status"] == 1 else f"REJECT:{expect}"

    def record(step: str, observed: str) -> None:
        want = EXPECT[step][0 if paper else 1]
        results.append({"profile": profile, "step": step, "expected": want, "observed": observed, "match": want == observed})

    assert code() == "NONE", "baseline: Alice must verify after bootstrap"
    assert sign(urls, dep, out / "acl-short.json", "tempacl", "H1", "--duty", "alice:60:3") == 0
    submit(out / "acl-short.json")
    time.sleep(5)
    record("1 duty ended", code())
    assert sign(urls, dep, out / "acl-restore.json", "tempacl", "H1", "--duty", "alice:60:3600") == 0
    submit(out / "acl-restore.json")
    record("2 duty restored", code())
    assert sign(urls, dep, out / "crl-revoke.json", "crl", "H1", "--revoke", "101") == 0
    submit(out / "crl-revoke.json")
    record("3 Alice revoked", code())
    old = out / "crl-v1-replay.json"
    json.dump(boot["trustLists"][0], open(old, "w"))
    record("4 old CRL replayed", submit(old, expect=None if paper else "STALE_ANCHOR"))
    record("4 Alice after replay", code())
    current = pbc.call(TMSC, "revocationListState", R.addr("H1-root"))["version"]
    assert sign(urls, dep, out / "crl-equal.json", "crl", "H1", "--version", current, "--revoke", "201") == 0
    record("5 equal version swap", submit(out / "crl-equal.json", expect=None if paper else "STALE_ANCHOR"))
    bad = sign(urls, dep, out / "refused-h9.json", "crl", "H9")
    record("6 unknown authority refused", "REFUSED" if bad == 1 and not (out / "refused-h9.json").exists() else f"exit {bad}")
    bad = subprocess.run([str(TOOLS / "sign_list.sh"), urls[1], str(dep), str(out / "refused-rpc.json"), "crl", "H1"], cwd=ROOT,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    record("6 wrong RPC refused", "REFUSED" if bad == 1 and not (out / "refused-rpc.json").exists() else f"exit {bad}")
    json.dump(log, open(out / "submissions.json", "w"), indent=1)
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=pathlib.Path)
    ap.add_argument("--ports", nargs=2, type=int, default=[38545, 48545])
    ap.add_argument("--profiles", nargs="+", default=["paper-strict", "paper-minimal", "repaired-e"])
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    anvils = [subprocess.Popen(["anvil", "--port", str(p), "--chain-id", str(c), "--block-time", "1", "--silent"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for p, c in zip(a.ports, (18545, 28545))]
    urls = (f"http://127.0.0.1:{a.ports[0]}", f"http://127.0.0.1:{a.ports[1]}")
    results = []
    try:
        for _ in range(100):
            try:
                R.Chain(urls[0]), R.Chain(urls[1])
                break
            except Exception:
                time.sleep(0.1)
        for p in a.profiles:
            results += run_profile(p, urls, a.out / p)
    finally:
        for p in anvils:
            p.terminate()
            p.wait(timeout=10)
    ok = all(r["match"] for r in results)
    json.dump({"schemaVersion": "hmbc-signed-list-check/v0", "note": "owner evidence (A1-0034); not an E2 case result",
               "results": results, "allMatch": ok}, open(a.out / "summary.json", "w"), indent=1)
    for r in results:
        print(f"{'OK ' if r['match'] else 'BAD'} {r['profile']:13} {r['step']:28} expected={r['expected']:20} observed={r['observed']}")
    print("ALL SIGNED-LIST CHECKS PASSED" if ok else "SIGNED-LIST CHECK FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
