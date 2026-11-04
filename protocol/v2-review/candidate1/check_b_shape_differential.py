"""Differential test of the D50 binding document shape: my reference validator (protocol/f0/vectors/d50_reference.py `validate`) versus the candidate's
DeploymentBindingDocument. Corpus: every single-key deletion, every key addition at each object, five leaf corruptions per string leaf, and 14 structural cases, applied to
the owner's E and F documents. Prints the cases on which the two verdicts differ and the cases both accept. Exit 0 always (it is a measurement, not a gate); the review
message classifies the differences."""
import copy, importlib.util, json, os, sys, collections
from common import *
from jsonschema import Draft202012Validator
root = proposal(sys.argv)
spec = importlib.util.spec_from_file_location("d50ref", os.path.join(F0, "vectors", "d50_reference.py")); ref = importlib.util.module_from_spec(spec); spec.loader.exec_module(ref)
D = load(root, "hmbc.schema.json")["$defs"]; sch = Draft202012Validator({"$ref": "#/$defs/DeploymentBindingDocument", "$defs": D})
docs = {k: x["document"] for k, x in load(root, "d50-owner-vectors.json")["documents"].items()}
def mine(d):
    try: ref.validate(d); return True
    except Exception: return False
def paths(x, p=()):
    yield p, x
    if isinstance(x, dict):
        for k, v in x.items(): yield from paths(v, p + (k,))
    elif isinstance(x, list):
        for i, v in enumerate(x): yield from paths(v, p + (i,))
def get(d, p):
    for k in p: d = d[k]
    return d
def setp(d, p, v): get(d, p[:-1])[p[-1]] = v
cases = []
for name, base in docs.items():
    cases.append((name, "BASE", base))
    for p, v in paths(base):
        if not p: continue
        par = get(base, p[:-1])
        if isinstance(par, dict):
            d = copy.deepcopy(base); del get(d, p[:-1])[p[-1]]; cases.append((name, "delete " + ".".join(map(str, p)), d))
        if isinstance(v, dict):
            d = copy.deepcopy(base); get(d, p)["zz"] = "0"; cases.append((name, "add-key under " + ".".join(map(str, p)), d))
        if isinstance(v, str):
            for tag, nv in (("empty", ""), ("upper-or-suffix", v.upper() if v.startswith("0x") else v + "A"), ("int", 5), ("null", None), ("leading-zero", "0" + v if v.isdigit() else v)):
                if nv == v: continue
                d = copy.deepcopy(base); setp(d, p, nv); cases.append((name, "leaf-%s %s" % (tag, ".".join(map(str, p))), d))
    def add(tag, fn):
        d = copy.deepcopy(base); fn(d); cases.append((name, tag, d))
    add("profile.name=mutant-no-nonce (an E mutant manifest name)", lambda d: d["profile"].__setitem__("name", "mutant-no-nonce"))
    add("profile.enum=4", lambda d: d["profile"].__setitem__("enum", "4"))
    add("profile name/enum disagree", lambda d: d["profile"].__setitem__("enum", "3" if name == "repaired-e" else "2"))
    add("interfaceVersion=v2", lambda d: d.__setitem__("interfaceVersion", "v2"))
    add("interfaceVersion=v", lambda d: d.__setitem__("interfaceVersion", "v"))
    for side in ("pbc", "dbc"):
        for c, row in base["chains"][side]["contracts"].items():
            add("drop immutableRefsSha256 on %s only" % c, lambda d, side=side, c=c: d["chains"][side]["contracts"][c].pop("immutableRefsSha256"))
    def drop_all(d):
        for s in ("pbc", "dbc"):
            for row in d["chains"][s]["contracts"].values(): row.pop("immutableRefsSha256", None)
    add("drop immutableRefsSha256 on ALL contracts", drop_all)
    for ws in base["witnessSets"]:
        add("%s witnesses empty" % ws, lambda d, ws=ws: d["witnessSets"][ws].__setitem__("witnesses", []))
        add("%s witnesses: duplicate member" % ws, lambda d, ws=ws: d["witnessSets"][ws]["witnesses"].append(d["witnessSets"][ws]["witnesses"][0]))
        add("%s witnesses: order reversed (must stay valid)" % ws, lambda d, ws=ws: d["witnessSets"][ws]["witnesses"].reverse())
d = copy.deepcopy(docs["repaired-e"]); d["chains"]["pbc"]["contracts"]["Governance"] = copy.deepcopy(docs["repaired-f"]["chains"]["pbc"]["contracts"]["Governance"])
cases.append(("repaired-e", "E document carrying a Governance contract", d))
res = collections.Counter(); diff = []; both_accept = []
for name, tag, doc in cases:
    m, t = mine(doc), sch.is_valid(doc)
    key = "both accept" if m and t else "both reject" if not m and not t else "SCHEMA LOOSER" if t else "SCHEMA STRICTER"
    res[key] += 1
    if key.startswith("SCHEMA"): diff.append((key, name, tag))
    if m and t: both_accept.append((name, tag))
print("cases:", len(cases)); [print("  %-14s %d" % kv) for kv in sorted(res.items())]
print("verdicts that differ:"); [print("  %s | %s | %s" % x) for x in diff]
print("both accept (excluding BASE and decimal leaf truncations that stay valid):")
for name, tag in both_accept:
    if tag != "BASE" and not tag.startswith("leaf-short"): print("  %s | %s" % (name, tag))
