#!/usr/bin/env python3
"""Producer self-check of an interfaces/v2 ledger deployment manifest (agent 1, A-F1).

Usage (repository root, after `forge build --root ledger`):
  <python with jsonschema> -I ledger/tools/check_successor_export.py --schema <interfaces/v2/hmbc.schema.json> \\
      [--live] <deployment.json> [...]

Checks, per manifest:
- schema: validates against `$defs/LedgerDeployment` of the given schema (skipped, and reported, when the
  interpreter has no `jsonschema`);
- source completeness (interfaces/v2.1, A3-0079): the manifest's `sources` list every `.sol` file of the compiled
  `src/` tree, so an E carrier must be the v2.1 source-complete carrier (the ten-file v2 E carrier omits
  `src/interfaces/IPolicyVersion.sol`, a KSSC import, and `src/Governance.sol`);
- export rule (design 2.2 section 8, interfaces/v2 BOUNDARY): every runtime's `runtimeBytes` < 2^32; the
  ranges are sorted, disjoint, length 32 and in bounds; `immutableRefsSha256` is the SHA-256 of the
  canonical JSON of the object list; each entry equals the compiled Forge artifact (runtime hash, length,
  ranges); under repaired-f, threshold 2 only with mask 0;
- --live (needs `cast` and the chains): the M4 equalities. `mutations()` of TMSC, PSC, KSSC, ACSC (and
  Governance under repaired-f) equal the manifest mask; `profile()` of the four profile holders equals the
  manifest enum; the PSC, KSSC (and Governance) witness sets equal `fixture.witnessSet` in order, with the
  same threshold and version; Governance `target()`, `governanceChainId()`, `maxGovernanceTtl()`;
  `TMSC.governance()`; `configured()` true on the six Bootstrapped contracts.
This is the producer's own check; it does not replace the evaluator's independent joins.
Exit 0 when every check passes, 1 otherwise, 2 on usage errors.
"""
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

LEDGER = pathlib.Path(__file__).resolve().parent.parent
CHAIN_OF = {"LSC": "pbc", "TMSC": "pbc", "RSC": "pbc", "PSC": "pbc", "ACSC": "dbc", "KSSC": "dbc", "Governance": "pbc"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def compiled(name):
    db = json.loads((LEDGER / "out" / f"{name}.sol" / f"{name}.json").read_text())["deployedBytecode"]
    code = bytes.fromhex(db["object"][2:] if db["object"].startswith("0x") else db["object"])
    ranges = sorted((r["start"], r["length"]) for refs in db.get("immutableReferences", {}).values() for r in refs)
    return code, [{"start": str(s), "length": str(n)} for s, n in ranges]


def source_completeness(d, problems):
    tree = sorted(str(p.relative_to(LEDGER)) for p in (LEDGER / "src").rglob("*.sol"))
    missing = [rel for rel in tree if rel not in d["sources"]]
    if missing:
        problems.append(f"sources omit compile inputs of this tree: {missing}")


def export_rule(d, problems):
    for name, e in d["abi"].items():
        n = int(e["runtimeBytes"])
        if n >= 2 ** 32:
            problems.append(f"{name}: runtimeBytes >= 2^32")
        end = 0
        for r in e["immutableReferences"]:
            s, ln = int(r["start"]), int(r["length"])
            if s < end or ln != 32 or s + ln > n:
                problems.append(f"{name}: range {r} breaks the export rule")
            end = s + ln
        if hashlib.sha256(canonical(e["immutableReferences"])).hexdigest() != e["immutableRefsSha256"]:
            problems.append(f"{name}: immutableRefsSha256 does not match the object list")
        code, refs = compiled(name)
        if (len(code), hashlib.sha256(code).hexdigest(), refs) != (n, e["runtimeSha256"], e["immutableReferences"]):
            problems.append(f"{name}: entry differs from the compiled artifact")
    if d["profile"] == "repaired-f" and d["fixture"]["witnessSet"]["threshold"] == "2" and d["mutations"] != "0":
        problems.append("threshold 2 with a non-zero mask")


def cast(rpc, addr, sig):
    out = subprocess.run([shutil.which("cast") or "cast", "call", addr, sig, "--rpc-url", rpc],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"cast call {addr} {sig}: {out.stderr.strip()}")
    return out.stdout.strip()


def addr_list(text):
    return [a.strip().lower() for a in text.strip("[]").split(",") if a.strip()]


def live(d, problems):
    rpc = {c: d["chains"][c]["rpcUrl"] for c in ("pbc", "dbc")}
    at = {name: (rpc[chain], d["chains"][chain]["contracts"][name])
          for name, chain in CHAIN_OF.items() if name in d["chains"][chain]["contracts"]}
    f = "Governance" in at
    mask, enum = d["mutations"], d["profileEnum"]
    for name in ["TMSC", "PSC", "KSSC", "ACSC"] + (["Governance"] if f else []):
        got = cast(*at[name], "mutations()(uint256)").split()[0]
        if got != mask:
            problems.append(f"{name}.mutations() = {got}, manifest {mask}")
    for name in ["TMSC", "PSC", "KSSC", "ACSC"]:
        got = cast(*at[name], "profile()(uint8)").split()[0]
        if got != enum:
            problems.append(f"{name}.profile() = {got}, manifest {enum}")
    ws = d["fixture"]["witnessSet"]
    for name in ["PSC", "KSSC"] + (["Governance"] if f else []):
        got = (addr_list(cast(*at[name], "witnesses()(address[])")), cast(*at[name], "threshold()(uint256)").split()[0],
               cast(*at[name], "witnessSetVersion()(uint64)").split()[0])
        if got != (ws["witnesses"], ws["threshold"], ws["version"]):
            problems.append(f"{name} witness set {got} differs from the fixture")
    for name in ["LSC", "TMSC", "RSC", "PSC", "ACSC", "KSSC"]:
        if cast(*at[name], "configured()(bool)") != "true":
            problems.append(f"{name} is not sealed")
    if f:
        g = at["Governance"]
        tmsc = d["chains"]["pbc"]["contracts"]["TMSC"]
        checks = {"target()(address)": tmsc, "governanceChainId()(uint256)": d["chains"]["pbc"]["chainId"],
                  "maxGovernanceTtl()(uint64)": d["fixture"]["governance"]["maxGovernanceTtl"]}
        for sig, want in checks.items():
            got = cast(*g, sig).split()[0].lower()
            if got != want:
                problems.append(f"Governance.{sig} = {got}, want {want}")
        if cast(*at["TMSC"], "governance()(address)").lower() != g[1]:
            problems.append("TMSC.governance() is not this Governance")


def main(argv):
    args = argv[1:]
    want_live = "--live" in args
    if want_live:
        args.remove("--live")
    if len(args) < 3 or args[0] != "--schema":
        print(__doc__, file=sys.stderr)
        return 2
    schema = json.loads(pathlib.Path(args[1]).read_text())
    try:
        import jsonschema

        def validator(ref):
            return jsonschema.Draft202012Validator({"$ref": f"#/$defs/{ref}", "$defs": schema["$defs"]})
    except ImportError:
        validator = None
        print("schema: SKIPPED (no jsonschema in this interpreter)")
    ok = True
    for path in args[2:]:
        d = json.loads(pathlib.Path(path).read_text())
        problems = []
        if validator is not None:
            # The union (LedgerDeployment = oneOf E/F) must hold; errors are reported from the branch the
            # profile selects, which names the failing member instead of the other branch's complaint.
            if d.get("profile") == "repaired-f":
                branch = "LedgerDeploymentF"
            elif d.get("schemaVersion") == "hmbc-ledger-deployment/v2.1":
                branch = "LedgerDeploymentEComplete"
            else:
                branch = "LedgerDeploymentE"
            if branch not in schema["$defs"]:
                problems.append(f"schema has no {branch} (use the interfaces/v2.1 schema)")
                branch = "LedgerDeployment"
            problems += [f"schema {branch}: {e.json_path}: {e.message[:160]}" for e in validator(branch).iter_errors(d)]
            if not validator("LedgerDeployment").is_valid(d) and not problems:
                problems.append("schema: not valid against the LedgerDeployment union")
        export_rule(d, problems)
        source_completeness(d, problems)
        if want_live:
            live(d, problems)
        ok &= not problems
        print(json.dumps({"manifest": path, "profile": d["profile"], "mutations": d["mutations"],
                          "threshold": d["fixture"]["witnessSet"]["threshold"], "schemaChecked": validator is not None,
                          "live": want_live, "problems": problems}))
    print("ALL SUCCESSOR EXPORT CHECKS PASS" if ok else "SUCCESSOR EXPORT CHECK FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
