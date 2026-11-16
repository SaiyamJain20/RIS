#!/usr/bin/env python3
"""Check the F0 ledger power matrix (ledger/f0/*.csv) against the ledger source.

Completeness and citation checks, standard library only:
  1. solc (pinned hash from ledger/toolchain.json) compiles ledger/src from the bytes on disk and returns
     the AST; no Forge artifact is trusted.
  2. Every non-constant state variable of every contract appears in exactly one ledger-state.csv row,
     and every row names only real state of that contract.
  3. Every constructor and every external/public non-view function appears in entry-points.csv.
  4. Every cited `src/<file>:<line>` exists and that line declares the named state or function.
  5. Every S-/E- id referenced from entry-points.csv and actor-powers.csv exists, and every test cited
     as evidence exists in ledger/test/*.t.sol.
This proves coverage and citation accuracy only. The power claims themselves are backed by the cited
tests (forge test) and by reading; the checker does not evaluate them.

Usage (repository root): python3 -I ledger/tools/check_f0_powers.py [--solc PATH] [--tree LEDGER_DIR]
--tree checks the inventory against another ledger tree (its src/ and test/), for example the pre-A-F1 tree
the F0 matrix describes; the CSVs and the pinned toolchain always come from this checkout. Since A-F1 the
current src/ has new state, entry points and shifted lines, so the F0 (E) inventory is checked against the
tree it characterizes, not HEAD.
Exit 0 when every check passes, 1 otherwise; a JSON summary goes to stdout.
"""
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

LEDGER = Path(__file__).resolve().parent.parent
F0 = LEDGER / "f0"
TREE = LEDGER  # the ledger tree whose src/ and test/ are checked (--tree)


def solc_ast(solc):
    pinned = json.loads((LEDGER / "toolchain.json").read_text())["solc"]["sha256"]
    actual = hashlib.sha256(Path(solc).read_bytes()).hexdigest()
    if actual != pinned:
        raise SystemExit(f"solc hash {actual} != pinned {pinned}")
    sources = sorted(p for p in (TREE / "src").rglob("*.sol"))
    inp = {
        "language": "Solidity",
        "sources": {str(p.relative_to(TREE)): {"content": p.read_text()} for p in sources},
        "settings": {"outputSelection": {"*": {"": ["ast"]}}, "evmVersion": "cancun"},
    }
    run = subprocess.run([solc, "--standard-json"], input=json.dumps(inp), capture_output=True, text=True)
    out = json.loads(run.stdout)
    errors = [e for e in out.get("errors", []) if e["severity"] == "error"]
    if errors:
        raise SystemExit("solc errors: " + json.dumps(errors)[:2000])
    digests = {k: hashlib.sha256(v["content"].encode()).hexdigest() for k, v in inp["sources"].items()}
    return out["sources"], actual, digests


def collect(sources):
    states, entries = {}, {}
    for path, s in sources.items():
        for c in s["ast"]["nodes"]:
            if c.get("nodeType") != "ContractDefinition" or c["contractKind"] != "contract":
                continue
            name = c["name"]
            for n in c["nodes"]:
                if n["nodeType"] == "VariableDeclaration" and n.get("mutability") != "constant":
                    states.setdefault(name, set()).add(n["name"])
                if n["nodeType"] == "FunctionDefinition":
                    if n["kind"] == "constructor":
                        entries.setdefault(name, set()).add("constructor")
                    elif n["visibility"] in ("external", "public") and n["stateMutability"] != "view":
                        entries.setdefault(name, set()).add(n["name"])
    return states, entries


def read_rows(name):
    with open(F0 / name, newline="") as f:
        return list(csv.DictReader(f))


def check_line(ref, token, kind, problems):
    m = re.fullmatch(r"(src/[\w/]+\.sol):(\d+)", ref)
    if not m:
        problems.append(f"bad source reference {ref!r}")
        return
    lines = (TREE / m.group(1)).read_text().splitlines()
    n = int(m.group(2))
    line = lines[n - 1] if 0 < n <= len(lines) else ""
    if kind == "state":
        ok = re.search(r"\b" + re.escape(token) + r"\s*;", line) is not None
    elif token == "constructor":
        ok = re.search(r"\bconstructor\s*\(", line) is not None
    else:
        ok = re.search(r"\bfunction\s+" + re.escape(token) + r"\s*\(", line) is not None
    if not ok:
        problems.append(f"{ref} does not declare {kind} {token!r}: {line.strip()[:90]!r}")


def main():
    solc = os.path.expanduser("~/.svm/0.8.37/solc-0.8.37")
    global TREE
    if "--tree" in sys.argv:
        TREE = Path(sys.argv[sys.argv.index("--tree") + 1]).resolve()
    if "--solc" in sys.argv:
        solc = sys.argv[sys.argv.index("--solc") + 1]
    sources, solc_sha, digests = solc_ast(solc)
    states, entries = collect(sources)
    problems = []

    state_rows = read_rows("ledger-state.csv")
    seen = {}
    for r in state_rows:
        names = r["state"].split("|")
        refs = r["source"].split("|")
        if len(names) != len(refs):
            problems.append(f"{r['id']}: {len(names)} states but {len(refs)} source references")
        for name, ref in zip(names, refs):
            if name not in states.get(r["contract"], set()):
                problems.append(f"{r['id']}: {r['contract']}.{name} is not a state variable")
            if (r["contract"], name) in seen:
                problems.append(f"{r['id']}: {r['contract']}.{name} already listed in {seen[(r['contract'], name)]}")
            seen[(r["contract"], name)] = r["id"]
            check_line(ref, name, "state", problems)
    for contract, names in states.items():
        for name in sorted(names - {n for (c, n) in seen if c == contract}):
            problems.append(f"state {contract}.{name} missing from ledger-state.csv")

    entry_rows = read_rows("entry-points.csv")
    listed = set()
    for r in entry_rows:
        key = (r["contract"], r["function"])
        if r["function"] not in entries.get(r["contract"], set()):
            problems.append(f"{r['id']}: {r['contract']}.{r['function']} is not a non-view entry point")
        if key in listed:
            problems.append(f"{r['id']}: {key} listed twice")
        listed.add(key)
        check_line(r["source"], r["function"], "function", problems)
    for contract, names in entries.items():
        for name in sorted(names):
            if (contract, name) not in listed:
                problems.append(f"entry point {contract}.{name} missing from entry-points.csv")

    state_ids = {r["id"] for r in state_rows}
    entry_ids = {r["id"] for r in entry_rows}
    tests = set()
    for p in (TREE / "test").glob("*.t.sol"):
        tests |= set(re.findall(r"function\s+(test\w+)\s*\(", p.read_text()))
    for r in entry_rows:
        for sid in filter(None, r["writes"].split("|")):
            if sid not in state_ids:
                problems.append(f"{r['id']}: writes unknown state id {sid}")
    actor_rows = read_rows("actor-powers.csv")
    cited = set()
    for r in actor_rows:
        for sid in re.findall(r"\bS\d\d\b", r["alone_changes"]):
            if sid not in state_ids:
                problems.append(f"{r['id']}: unknown state id {sid}")
        for t in re.findall(r"\btest\w+", r["evidence"]):
            cited.add(t)
            if t not in tests:
                problems.append(f"{r['id']}: cited test {t} not found in ledger/test")

    summary = {
        "solcSha256": solc_sha,
        "sourceSha256": digests,
        "contracts": sorted(states),
        "stateVariables": sum(len(v) for v in states.values()),
        "stateRows": len(state_rows),
        "entryPoints": sum(len(v) for v in entries.values()),
        "entryRows": len(entry_rows),
        "actorRows": len(actor_rows),
        "testsCited": len(cited),
        "problems": problems,
    }
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
