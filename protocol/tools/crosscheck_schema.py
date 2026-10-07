#!/usr/bin/env python3
"""Run agent-2's mutated wire inputs through agent 3's candidate validator and report disagreements.

Usage: python protocol/tools/crosscheck_schema.py <path to an extracted agent-3 snapshot root> [--out FILE]
The snapshot must contain evaluation/schema.py and interfaces/proposals/v1/hmbc.schema.json (e.g. `git archive origin/agent-3`).
Agent-2's validator (hmbc_protocol.wire) is the oracle for 'should reject'; every mutation starts from a case agent 3
marks valid. A disagreement is reported, never fixed here. Exit 0 always unless the snapshot cannot be loaded.
"""
import copy
import importlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "protocol"))
from hmbc_protocol import wire  # noqa: E402

snap = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(snap))
a3 = importlib.import_module("evaluation.schema")
cases = json.loads((ROOT / "protocol/tests/fixtures/schema-cases-a3-988e452.json").read_text())["cases"]


def paths(o, p=()):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from paths(v, p + (k,))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from paths(v, p + (i,))
    else:
        yield p


def get(o, p):
    for k in p:
        o = o[k]
    return o


def put(o, p, v):
    o = copy.deepcopy(o)
    if not p:
        return v
    t = o
    for k in p[:-1]:
        t = t[k]
    t[p[-1]] = v
    return o


def a3_rejects(name, value):
    try:
        a3.validate(name, value)
        return False
    except Exception:
        return True


# Non-vacuity guard: the peer validator must ACCEPT every valid baseline, otherwise "rejects" proves nothing.
for c in cases:
    if c["valid"] and c["schema"] in wire.VALIDATORS:
        a3.validate(c["schema"], c["input"])

findings, n = [], 0
for c in cases:
    if not c["valid"] or c["schema"] not in wire.VALIDATORS:
        continue
    top = not isinstance(c["input"], (dict, list))
    for p in ([()] if top else list(paths(c["input"]))):
        val = c["input"] if top else get(c["input"], p)
        if not isinstance(val, str):
            continue
        vs = [("trailing-LF", val + "\n"), ("leading-space", " " + val)]
        if val.startswith("0x") and any(ch.isalpha() for ch in val[2:]):
            vs.append(("upper-hex", "0x" + val[2:].upper()))
        if val.isdigit():
            vs += [("json-integer", int(val)), ("float-string", val + ".0"), ("leading-zero", "0" + val if val != "0" else "00")]
        for tag, bad in vs:
            m = put(c["input"], p, bad)
            n += 1
            try:
                wire.validate(c["schema"], m)
                continue  # agent-2 would accept: not a 'must reject' oracle case
            except wire.WireError:
                pass
            if not a3_rejects(c["schema"], m):
                findings.append({"schema": c["schema"], "path": list(p), "mutation": tag, "a3": "ACCEPTED"})

by = {c["schema"]: c["input"] for c in cases if c["valid"] and c["schema"] in wire.VALIDATORS}
structural = []
rc, rl, ta, cb, cr = (copy.deepcopy(by[k]) for k in ("RoleCertificate", "RevocationList", "TemporalAcl", "CredentialBundle", "CredentialRecords"))
structural.append(("RoleCertificate roles reversed", "RoleCertificate", {**rc, "roles": rc["roles"][::-1]} if len(rc["roles"]) > 1 else None))
structural.append(("RoleCertificate roles duplicated", "RoleCertificate", {**rc, "roles": [rc["roles"][0]] * 2}))
structural.append(("RevocationList serials descending", "RevocationList", {**rl, "revokedSerials": ["9", "3"]}))
structural.append(("RevocationList serials duplicate", "RevocationList", {**rl, "revokedSerials": ["3", "3"]}))
structural.append(("TemporalAcl entries reversed", "TemporalAcl", {**ta, "entries": ta["entries"][::-1]}))
structural.append(("TemporalAcl entries duplicated", "TemporalAcl", {**ta, "entries": [ta["entries"][0]] * 2}))
structural.append(("CredentialBundle certificates reversed", "CredentialBundle", {**cb, "certificates": cb["certificates"][::-1]} if len(cb["certificates"]) > 1 else None))
structural.append(("CredentialBundle claims reversed", "CredentialBundle", {**cb, "temporalClaims": cb["temporalClaims"][::-1]} if len(cb["temporalClaims"]) > 1 else None))
structural.append(("CredentialRecords reversed", "CredentialRecords", cr[::-1] if len(cr) > 1 else None))
sig = by["Signature"]
nn = wire.SECP256K1_N
structural += [("Signature high-s", "Signature", "0x" + sig[2:66] + format(nn - int(sig[66:130], 16), "064x") + sig[130:]),
               ("Signature r=0", "Signature", "0x" + "00" * 32 + sig[66:]), ("Signature r=n", "Signature", "0x" + format(nn, "064x") + sig[66:]),
               ("Signature v=29", "Signature", "0x" + sig[2:130] + "1d")]
for label, schema, val in structural:
    if val is None:
        continue
    n += 1
    try:
        wire.validate(schema, val)
        findings.append({"schema": schema, "mutation": label, "a3": "agent-2 oracle ACCEPTS (oracle bug?)"})
        continue
    except wire.WireError:
        pass
    if not a3_rejects(schema, val):
        findings.append({"schema": schema, "mutation": label, "a3": "ACCEPTED"})

report = {"snapshot": str(snap), "mutationsTried": n, "disagreements": findings}
print(json.dumps(report, indent=1))
if "--out" in sys.argv:
    pathlib.Path(sys.argv[sys.argv.index("--out") + 1]).write_text(json.dumps(report, indent=1) + "\n")
