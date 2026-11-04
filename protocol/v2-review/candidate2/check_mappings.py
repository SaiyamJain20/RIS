"""Candidate 2, operations and D50: (1) schema validity and the 16 wire/success responses; (2) my semantic wire checker on the candidate's 12 examples (and the stale-provenance
note on wire.json); (3) reason table; (4) the owner-vector copies equal my vectors; (5) `recorded`/`collection` scoping; (6) the P-corrections as schema behaviour: reporters,
non-empty arrays, profile pairs, F interfaceVersion v2, unique witnesses; (7) differential of the D50 B shape (my revision-5 reference versus DeploymentBindingDocument)."""
import copy, importlib.util, json, os, re, subprocess, sys, tempfile, collections
from common import *
from jsonschema import Draft202012Validator
root = proposal(sys.argv)
schema = load(root, "hmbc.schema.json"); D = schema["$defs"]
Draft202012Validator.check_schema(schema); print("PASS schema is a valid draft 2020-12 schema; %d definitions" % len(D))
V = lambda ref: Draft202012Validator({"$ref": "#/$defs/" + ref, "$defs": D})
resp = V("AdapterResponse"); bad = 0
def rep(ok, text):
    global bad
    bad += (not ok); print(("PASS " if ok else "FAIL ") + text)
wire, succ = load(root, "vectors/wire.json"), load(root, "vectors/success.json")
for i, r in enumerate(wire["responses"], 1): rep(resp.is_valid(r), "wire example %d validates against AdapterResponse" % i)
for i, x in enumerate(succ, 1): rep(resp.is_valid(x["response"]), "success vector %d (%s) validates against AdapterResponse" % (i, x["operation"]))
print("INFO wire.json sourceSha256 = %s; pinned SUCCESSOR-WIRE = %s; equal: %s" % (wire["sourceSha256"][:16], sha(os.path.join(F0, "SUCCESSOR-WIRE.md"))[:16], wire["sourceSha256"] == sha(os.path.join(F0, "SUCCESSOR-WIRE.md"))))
src = open(os.path.join(F0, "SUCCESSOR-WIRE.md")).read()
blocks = re.findall(r"```json\n(.*?)\n```", src, re.S); assert len(blocks) == len(wire["responses"]) == 12
doc = src
for b, r in zip(blocks, wire["responses"]): doc = doc.replace(b, json.dumps(r, separators=(",", ":")), 1)
with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, "w.md"); open(p, "w").write(doc)
    r = subprocess.run([sys.executable, "-B", os.path.join(F0, "vectors", "check_wire_examples.py"), p], capture_output=True, text=True)
rep(r.returncode == 0, "my revision-8 check_wire_examples.py on the candidate's 12 examples: exit %d" % r.returncode)
tab = {}
for line in src.splitlines():
    m = re.match(r"^\| ((?:`[A-Z_]+`(?:, )?)+) \| `([A-Z_]+)` \|", line)
    if m:
        for n in re.findall(r"`([A-Z_]+)`", m.group(1)): tab[n] = m.group(2)
rep(load(root, "reason-codes.json") == tab and len(tab) == 19, "reason-codes.json equals the 19-row table of SUCCESSOR-WIRE section 1")
rep(load(root, "d50-owner-vectors.json") == json.load(open(os.path.join(F0, "vectors", "d50_binding_vector.json"))), "d50-owner-vectors.json equals my revision-5 d50_binding_vector.json")
rep(load(root, "export-layout-owner-vectors.json") == json.load(open(os.path.join(F0, "vectors", "export_layouts_vectors.json"))), "export-layout-owner-vectors.json equals my export_layouts_vectors.json")
rec = [r for r in wire["responses"] if r.get("error") and "recorded" in r["error"]][0]; col = [r for r in wire["responses"] if r.get("error") and "collection" in r["error"]][0]
for op in ("CollectDecisionResponse", "AttestGrantResponse", "ReleaseResponse", "PrepareRequestResponse", "CollectGovernanceResponse"): rep(not V(op).is_valid(rec), "`recorded` error rejected by %s" % op)
rep(V("CollectCheckpointResponse").is_valid(rec), "`recorded` error accepted by CollectCheckpointResponse")
for op in ("ReleaseResponse", "PrepareRequestResponse", "EncryptRecordResponse"): rep(not V(op).is_valid(col), "pool `collection` failure rejected by %s" % op)
# P-corrections as schema behaviour
late = [x for x in wire["responses"] if x.get("error") and "collection" in x["error"] and "lateReports" in x["error"]["collection"]][0]
def mod(base, fn):
    r = copy.deepcopy(base); fn(r); return resp.is_valid(r)
c = lambda r: r["error"]["collection"]
import itertools
subs = [list(map(str, s)) for k in (2, 3, 4) for s in itertools.combinations(range(4), k)]
rep(all(mod(late, lambda r, s=s: c(r)["adopted"].__setitem__("reporters", s)) for s in subs), "P5 adopted.reporters accepts all 11 ascending subsets of size 2 to 4")
rep(not any(mod(late, lambda r, s=s: c(r)["adopted"].__setitem__("reporters", s)) for s in (["1", "0"], ["0", "0"], ["0"], [], ["0", "1", "1"], ["3", "2"])), "P5 adopted.reporters refuses non-ascending, duplicate, too short and empty lists")
for k in ("lateReports", "recordedReports", "inconsistentReports"):
    holder = late if k in c(late) else None
    if holder is None:
        holder = [x for x in wire["responses"] if x.get("error") and "collection" in x["error"] and k in x["error"]["collection"]]
        holder = holder[0] if holder else None
    rep(holder is not None and not mod(holder, lambda r, k=k: c(r).__setitem__(k, [])), "P4 an empty %s array is refused" % k)
# D50 B-shape differential (my revision-5 reference vs the candidate's DeploymentBindingDocument)
spec = importlib.util.spec_from_file_location("d50ref", os.path.join(F0, "vectors", "d50_reference.py")); ref = importlib.util.module_from_spec(spec); spec.loader.exec_module(ref)
sch = V("DeploymentBindingDocument")
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
cases = []
for name, base in docs.items():
    cases.append((name, "BASE", base))
    for p, v in paths(base):
        if not p: continue
        if isinstance(get(base, p[:-1]), dict):
            d = copy.deepcopy(base); del get(d, p[:-1])[p[-1]]; cases.append((name, "delete " + ".".join(map(str, p)), d))
        if isinstance(v, dict):
            d = copy.deepcopy(base); get(d, p)["zz"] = "0"; cases.append((name, "add-key " + ".".join(map(str, p)), d))
        if isinstance(v, str):
            for tag, nv in (("empty", ""), ("suffix", v + "A"), ("int", 5), ("null", None), ("leading-zero", "0" + v if v.isdigit() else v)):
                if nv != v:
                    d = copy.deepcopy(base); get(d, p[:-1])[p[-1]] = nv; cases.append((name, "leaf-%s %s" % (tag, ".".join(map(str, p))), d))
    def add(tag, fn):
        d = copy.deepcopy(base); fn(d); cases.append((name, tag, d))
    add("profile.name=mutant-no-nonce", lambda d: d["profile"].__setitem__("name", "mutant-no-nonce"))
    add("profile.enum=4", lambda d: d["profile"].__setitem__("enum", "4"))
    add("profile name/enum disagree", lambda d: d["profile"].__setitem__("enum", "3" if base["profile"]["name"] == "repaired-e" else "2"))
    add("interfaceVersion=v1", lambda d: d.__setitem__("interfaceVersion", "v1"))
    add("interfaceVersion=v2", lambda d: d.__setitem__("interfaceVersion", "v2"))
    for ws in base["witnessSets"]:
        add("%s duplicate witness" % ws, lambda d, ws=ws: d["witnessSets"][ws]["witnesses"].append(d["witnessSets"][ws]["witnesses"][0]))
        add("%s threshold above the count" % ws, lambda d, ws=ws: d["witnessSets"][ws].__setitem__("threshold", str(len(d["witnessSets"][ws]["witnesses"]) + 1)))
        add("%s threshold 0" % ws, lambda d, ws=ws: d["witnessSets"][ws].__setitem__("threshold", "0"))
        add("%s witnesses reversed (order is meaningful; must stay valid)" % ws, lambda d, ws=ws: d["witnessSets"][ws]["witnesses"].reverse())
    for side in ("pbc", "dbc"):
        for cn, row in base["chains"][side]["contracts"].items():
            if "immutableRefsSha256" in row: add("drop immutableRefsSha256 on %s only" % cn, lambda d, side=side, cn=cn: d["chains"][side]["contracts"][cn].pop("immutableRefsSha256"))
res = collections.Counter(); diff = []
for name, tag, d in cases:
    m, t = mine(d), sch.is_valid(d)
    key = "both accept" if m and t else "both reject" if not m and not t else "SCHEMA LOOSER" if t else "SCHEMA STRICTER"
    res[key] += 1
    if key.startswith("SCHEMA"): diff.append((key, name, tag))
print("INFO D50 B-shape differential: %d cases: %s" % (len(cases), dict(res)))
BOUNDARY_ONLY = ("threshold above the count", "threshold 0")      # BOUNDARY: "1<=threshold<=set length": a string cannot be compared with a list length in JSON Schema
for x in diff: print("%s %s | %s | %s" % ("BOUNDARY-ONLY" if x[0] == "SCHEMA LOOSER" and any(t in x[2] for t in BOUNDARY_ONLY) else "DIFF", *x))
rep(all(x[0] == "SCHEMA LOOSER" and any(t in x[2] for t in BOUNDARY_ONLY) for x in diff),
    "D50 B-shape: the schema and my revision-5 reference agree on every case except the threshold bound, which BOUNDARY carries as a mandatory semantic rule; the schema is never stricter")
print("\nfailures: %d" % bad); sys.exit(1 if bad else 0)
