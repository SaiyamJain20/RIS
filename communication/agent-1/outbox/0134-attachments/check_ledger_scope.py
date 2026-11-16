#!/usr/bin/env python3
"""Agent 1's ledger-scope FREEZE ACK checker: the mechanical items 1-4 of A1-0129 section 8.

Usage (repository root):
    python3 -I check_ledger_scope.py <plan.json | git-ref:path> [--scan-dir DIR]

Each check recomputes from git objects and the pinned ledger sources. It trusts nothing in the plan
except the values under test. The dev-key scan derives the key at runtime from the public Anvil test
mnemonic (cast), and never prints or writes it. Exit 0 only if every check passes.
Item 5 of A1-0129 section 8 (dry run of the runner's ledger calls) is separate: it needs the runner.
"""
import hashlib, json, os, re, subprocess, sys

REPO = os.getcwd()
LEDGER = "85c59f588de58a8ff5e87b9fe6f630c9d8c43642"
PUBLISH_REF = "origin/agent-1"
IFACE_REF = "origin/agent-3"
results = []


def git(*a, binary=False):
    out = subprocess.run(["git", *a], cwd=REPO, capture_output=True, check=True)
    return out.stdout if binary else out.stdout.decode().strip()


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


def load_plan(arg):
    if ":" in arg and not os.path.exists(arg):
        return json.loads(git("show", arg, binary=True))
    return json.load(open(arg))


def full_hex(text, n=64):
    m = re.search(r"\b[0-9a-f]{%d}\b" % n, text or "")
    return m.group(0) if m else None


def main():
    if len(sys.argv) < 2:
        print(__doc__); return 2
    plan = load_plan(sys.argv[1])
    scan = sys.argv[sys.argv.index("--scan-dir") + 1] if "--scan-dir" in sys.argv else None
    pins, dep = plan.get("pins", {}), plan.get("deployment", {})

    # 1. Pins: ledger commit, tree, manifest; interface FREEZE and schema hashes.
    check("ledger commit pinned in full", LEDGER in pins.get("ledger", ""), pins.get("ledger", "")[:60])
    check("ledger commit published on " + PUBLISH_REF,
          subprocess.run(["git", "merge-base", "--is-ancestor", LEDGER, PUBLISH_REF], cwd=REPO).returncode == 0)
    check("ledger/ unchanged from pin to " + PUBLISH_REF,
          subprocess.run(["git", "diff", "--quiet", LEDGER, PUBLISH_REF, "--", "ledger"], cwd=REPO).returncode == 0)
    tree = git("rev-parse", LEDGER + "^{tree}")
    check("ledger commit tree", tree in pins.get("ledger", ""), tree)
    man = git("show", LEDGER + ":ledger/evidence/source-manifest.sha256", binary=True)
    mh, mn = hashlib.sha256(man).hexdigest(), len(man.decode().splitlines())
    check("ledger manifest sha256 and entries", full_hex(pins.get("ledgerManifestSha256")) == mh and mn == 429, f"{mh[:16]}.. {mn} entries")
    for path in ("interfaces/v2/FREEZE.json", "interfaces/v2.1/FREEZE.json", "interfaces/v2.1/hmbc.schema.json"):
        h = hashlib.sha256(git("show", f"{IFACE_REF}:{path}", binary=True)).hexdigest()
        check(f"{path} sha256", full_hex(pins.get(path, "")) == h, h[:16] + "..")

    # 2. Deployment invocation against the pinned deploy_local.sh.
    src = git("show", LEDGER + ":ledger/tools/deploy_local.sh")
    profiles = set(re.findall(r"^\s+([a-z0-9-]+)\)\s+PROFILE=", src, re.M)) | {"paper-strict", "paper-minimal", "repaired-e"}
    check("deploy script path", dep.get("script") == "ledger/tools/deploy_local.sh")
    check("argument order", dep.get("argumentOrder") == ["pbc-rpc", "dbc-rpc", "profile", "log-mode", "run-id"])
    for k in ("fProfile", "f18Profile"):
        check(f"{k} is a deploy_local profile", dep.get(k) in profiles, str(dep.get(k)))
    check("fProfile is repaired-f / f18Profile is mutant-f-q2", dep.get("fProfile") == "repaired-f" and dep.get("f18Profile") == "mutant-f-q2")
    check("log mode valid", dep.get("logMode") in ("hash-only", "complete-details"), str(dep.get("logMode")))
    m = re.search(r"Chain ids default to (\d+) \(PBC\) and (\d+) \(DBC\)", src)
    check("chain ids recorded (defaults 18545/28545 or explicit)",
          dep.get("chainIds") == {"pbc": int(m.group(1)), "dbc": int(m.group(2))} or bool(dep.get("chainIds")), str(dep.get("chainIds")))
    check("deploy from a scratch git-archive extract", dep.get("deployInsideWorkingTree") is False and "git archive" in str(dep.get("scratchArchive")))
    check("deployment manifest read back, not hand-edited", "do not hand-edit" in str(dep.get("deploymentManifestReadback")).lower())
    check("deployer key from environment only", "environment" in str(dep.get("deployerSecret")).lower())
    check("E regression names repaired-e + SUCCESSOR_EXPORT=1", "repaired-e" in str(dep.get("eRegression")) and "SUCCESSOR_EXPORT=1" in str(dep.get("eRegression")))
    check("fresh chain pair per case", dep.get("freshChainPairPerCase") is True and plan.get("oracleRules", {}).get("freshChainPairPerCase") is True)

    # 3. Expected ledger codes against the ledger's own tests and source.
    fam = next((v for k, v in plan.get("families", {}).items() if k.startswith("A-")), {})
    rc = fam.get("rejectionCodes", {})
    want = {"thresholdZeroOrAboveMemberCount": "INSUFFICIENT_QUORUM", "invalidOrNonMemberSignature": "BAD_SIGNATURE",
            "sameAsPreviousSigner": "DUPLICATE_SIGNER", "lowerAndPreviouslySeenSigner": "DUPLICATE_SIGNER",
            "lowerSignerNotPreviouslySeen": "MALFORMED", "validListBelowThresholdAfterWalk": "INSUFFICIENT_QUORUM"}
    check("family A rejection codes", all(str(rc.get(k, "")).startswith(v) for k, v in want.items()),
          ", ".join(k for k, v in want.items() if not str(rc.get(k, "")).startswith(v)) or "all six")
    qt = git("show", LEDGER + ":ledger/test/Quorum.t.sol")
    check("Quorum.t.sol badLists codes are the four the plan uses",
          re.findall(r"want\[\d\] = ErrorCode\.(\w+)", qt) == ["INSUFFICIENT_QUORUM", "DUPLICATE_SIGNER", "BAD_SIGNATURE", "MALFORMED"])
    sig = git("show", LEDGER + ":ledger/src/lib/SigLib.sol")
    order = [c for c in re.findall(r"ErrorCode\.(\w+)", sig[sig.find("library QuorumLib"):])][:6]
    check("QuorumLib check order", order[:5] == ["INSUFFICIENT_QUORUM", "BAD_SIGNATURE", "DUPLICATE_SIGNER", "DUPLICATE_SIGNER", "MALFORMED"], ",".join(order))
    fl6 = plan.get("oracleRules", {}).get("f6StaleWitnessSet", "")
    check("FL-6 expects STALE_STATE first", "STALE_STATE" in fl6 and "witnessSetVersion" in fl6)
    gt = git("show", LEDGER + ":ledger/test/Governance.t.sol")
    check("ledger test for FL-6 governance-first exists", "test_AF1G_WrongWitnessSetVersionIsStaleStateFirst" in gt)
    rev = set(plan.get("oracleRules", {}).get("f31RollbackScope", []))
    check("F-31 rollback scope covers all ledger state",
          {"KSSC checkpoint sequence", "governance nonce", "grants and nonce consumption", "PSC request status", "LSC log"} <= rev)

    # 4. Dev-key scan of the FREEZE evidence (only with --scan-dir).
    if scan and not os.path.isdir(scan):
        check("dev-key scan directory exists", False, scan)
    elif scan:
        n_files = sum(len(fs) for _, _, fs in os.walk(scan))
        check("dev-key scan directory is non-empty", n_files > 0, f"{n_files} files")
        key = subprocess.run(["cast", "wallet", "private-key", "--mnemonic",
                              "test test test test test test test test test test test junk", "--mnemonic-index", "0"],
                             capture_output=True, text=True).stdout.strip().lower()
        if not re.fullmatch(r"0x[0-9a-f]{64}", key):
            check("dev-key scan", False, "could not derive the key (cast missing?)")
        else:
            hits = []
            for root, _, files in os.walk(scan):
                for f in files:
                    p = os.path.join(root, f)
                    try:
                        data = open(p, "rb").read().lower()
                    except OSError:
                        continue
                    if key[2:].encode() in data or re.search(rb"deployer_pk=0x[0-9a-f]{64}", data):
                        hits.append(os.path.relpath(p, scan))
            check("no dev key or DEPLOYER_PK value in evidence", not hits, f"{len(hits)} file(s): {hits[:5]}")
        del key

    width = max(len(n) for n, _, _ in results)
    for n, ok, d in results:
        print(f"{'PASS' if ok else 'FAIL'}  {n.ljust(width)}  {d}")
    bad = sum(not ok for _, ok, _ in results)
    print(f"{len(results) - bad}/{len(results)} passed")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
