"""Candidate 2, exporter layouts: (1) my four evidence variants, two binding exports and three refusal lines validate against BindingExport / WitnessEvidence / ExporterError;
(2) the revision-9 cases that matter (A -> B -> A accepted, DENY under overtaken-decision-grant refused by the SCHEMA, orphan history) are probed against the schema;
(3) a differential: my revision-9 layout reference versus WitnessEvidence over a corpus of corruptions, every corrupted document re-sealed so that only the corruption
can make it invalid. SCHEMA STRICTER (the schema refuses what my checker accepts) would be a defect; SCHEMA LOOSER is expected for the rules JSON Schema cannot express
(sorting, hashes, uniqueness across records, generations, monotonicity) and is classified by corruption kind."""
import collections, copy, importlib.util, json, os, sys
from common import *
from jsonschema import Draft202012Validator
root = proposal(sys.argv)
D = load(root, "hmbc.schema.json")["$defs"]
V = lambda ref: Draft202012Validator({"$ref": "#/$defs/" + ref, "$defs": D})
spec = importlib.util.spec_from_file_location("L", os.path.join(F0, "vectors", "export_layouts_reference.py")); L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
vec = load(root, "export-layout-owner-vectors.json")
bad = 0
def rep(ok, text):
    global bad
    bad += (not ok); print(("PASS " if ok else "FAIL ") + text)
for k, x in vec["bindingExports"].items(): rep(V("BindingExport").is_valid(x), "binding export %s validates against BindingExport" % k)
for k, x in vec["evidence"].items(): rep(V("WitnessEvidence").is_valid(x), "evidence variant %s validates against WitnessEvidence" % k)
for k, line in vec["refusalLines"].items(): rep(V("ExporterError").is_valid(json.loads(line)), "refusal line %s validates against ExporterError" % k)
rep(all(not V("ExporterError").is_valid({"code": c, "message": "x", "reason": r}) for c, r in (("ADAPTER_UNAVAILABLE", "LEGACY_STATE"), ("WRONG_DESTINATION", "STORE_MISSING"), ("ADAPTER_UNAVAILABLE", "BINDING_MISMATCH"))), "ExporterError refuses a reason with the wrong code and reasons an exporter cannot raise")
WE = V("WitnessEvidence"); mine = L.validate_evidence
def seal(d): L.seal(d); return d
def probe(name, doc, expect_schema, expect_mine=None):
    s, m = WE.is_valid(doc), (lambda: (mine(doc), True)[1])() if False else None
    try: mine(doc); m = True
    except Exception: m = False
    print("PROBE %-95s schema:%-8s my checker:%s" % (name, "ACCEPTS" if s else "REJECTS", "ACCEPTS" if m else "REJECTS"))
    return s, m
G = copy.deepcopy(vec["evidence"]["generations"])
s, m = probe("generations variant (A -> B -> A, ALLOW dead by grant then DENY)", G, True); rep(s and m, "the legal A -> B -> A history is accepted by the schema and by my checker")
gi = [i for i, r in enumerate(G["superseded"]) if r["death"]["kind"] == "overtaken-decision-grant"][0]
D2 = copy.deepcopy(G); e = D2["superseded"][gi]["effect"]; e["result"] = "0"
import hashlib
D2["superseded"][gi]["vHash"] = hashlib.sha256(L.canonical_json(e).encode("ascii")).hexdigest(); seal(D2)
s, m = probe("L2: DENY (result 0) under overtaken-decision-grant, vHash and evidenceSha256 recomputed", D2, False); rep(not s and not m, "a DENY under the ALLOW-only death kind is refused by the SCHEMA and by my checker")
orph = copy.deepcopy(G); orph["conflicts"] = [c for c in orph["conflicts"] if not (c["type"] == "GovernanceAction" and c["keyField"] == "5")]; seal(orph)
s, m = probe("orphan history: superseded rows of a key whose live record is absent", orph, True)
print("INFO orphan history: schema %s, my checker %s (BOUNDARY declares it a runner completeness check; my checker does not enforce it either)" % ("ACCEPTS" if s else "REJECTS", "ACCEPTS" if m else "REJECTS"))
# differential corpus
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
for name, base in vec["evidence"].items():
    cases.append((name, "BASE", "base", copy.deepcopy(base)))
    for p, v in paths(base):
        if not p or p[0] == "evidenceSha256" or (len(p) >= 2 and p[0] == "binding" and p[1] == "document"): continue     # the embedded B is covered by check_mappings.py
        parent = get(base, p[:-1])
        label = ".".join(str(x) for x in p)
        if isinstance(parent, dict):
            d = copy.deepcopy(base); del get(d, p[:-1])[p[-1]]; cases.append((name, "delete " + label, "shape", seal(d)))
        if isinstance(v, dict):
            d = copy.deepcopy(base); get(d, p)["zz"] = "0"; cases.append((name, "add-key under " + label, "shape", seal(d)))
        if isinstance(v, str):
            for tag, nv in (("empty", ""), ("suffix", v + "A"), ("int", 5), ("null", None)):
                d = copy.deepcopy(base); get(d, p[:-1])[p[-1]] = nv; cases.append((name, "leaf-%s %s" % (tag, label), "format", seal(d)))
    def add(tag, kind, fn):
        d = copy.deepcopy(base)
        try: fn(d)
        except Exception: return
        cases.append((name, tag, kind, seal(d)))
    add("conflicts reversed", "order", lambda d: d["conflicts"].reverse())
    add("superseded reversed", "order", lambda d: d["superseded"].reverse())
    add("observations reversed", "order", lambda d: d["observations"].reverse())
    add("first conflict duplicated (duplicate K and digests)", "uniqueness", lambda d: d["conflicts"].insert(0, copy.deepcopy(d["conflicts"][0])))
    add("vHash flipped", "hash", lambda d: d["conflicts"][0].__setitem__("vHash", d["conflicts"][0]["vHash"][:-1] + ("0" if d["conflicts"][0]["vHash"][-1] != "0" else "1")))
    add("evidenceSha256 flipped (not resealed)", "hash", lambda d: d.__setitem__("evidenceSha256", d["evidenceSha256"][:-1] + ("0" if d["evidenceSha256"][-1] != "0" else "1")) or d.__setitem__("_unsealed", True))
    add("marker.owner differs from owner", "cross-field", lambda d: d["marker"].__setitem__("owner", "witness:0x" + "22" * 20))
    add("binding.binding_v2 flipped", "hash", lambda d: d["binding"].__setitem__("binding_v2", d["binding"]["binding_v2"][:-1] + ("0" if d["binding"]["binding_v2"][-1] != "0" else "1")))
    add("superseded[0].seq = 2", "order", lambda d: d["superseded"][0].__setitem__("seq", "2"))
    add("superseded[0].death.kind = executed-receipt (wrong type)", "death", lambda d: d["superseded"][0]["death"].__setitem__("kind", "executed-receipt"))
    add("superseded[0].death.observed added to an expiry death", "death", lambda d: d["superseded"][0]["death"].__setitem__("observed", "1"))
    add("superseded[0].death timestamp before expiry", "death", lambda d: d["superseded"][0]["death"]["observation"].__setitem__("timestamp", "1"))
    add("faultLog row with empty note", "cross-field", lambda d: d["faultLog"][0].__setitem__("note", ""))
    add("faulted reason inconsistent with its observations", "cross-field", lambda d: d["faulted"].__setitem__("reason", "hash-changed"))
    add("a digest observation above the stored last observation (no fault)", "monotonicity", lambda d: d["conflicts"][0]["digests"][0]["observation"].__setitem__("blockNumber", "99999"))
    add("effect.witnessSetVersion differs from the key's witnessSetVersion", "cross-field", lambda d: d["conflicts"][0]["effect"].__setitem__("witnessSetVersion", "1" if d["conflicts"][0]["effect"]["witnessSetVersion"] == "2" else "2"))
res = collections.Counter(); bykind = collections.defaultdict(collections.Counter); stricter = []
for name, tag, kind, d in cases:
    unsealed = d.pop("_unsealed", False)
    if unsealed: d["evidenceSha256"] = d["evidenceSha256"]
    s = WE.is_valid({k: v for k, v in d.items() if k != "_unsealed"})
    try: mine({k: v for k, v in d.items() if k != "_unsealed"}); m = True
    except Exception: m = False
    key = "both accept" if s and m else "both reject" if not s and not m else "SCHEMA LOOSER" if s else "SCHEMA STRICTER"
    res[key] += 1; bykind[kind][key] += 1
    if key == "SCHEMA STRICTER": stricter.append((name, tag))
print("INFO layout differential: %d corrupted/base documents: %s" % (len(cases), dict(res)))
for kind in sorted(bykind): print("INFO   %-12s %s" % (kind, dict(bykind[kind])))
for x in stricter: print("STRICTER %s | %s" % x)
rep(not stricter, "the schema is never stricter than my layout checker (no document my checker accepts is refused by WitnessEvidence)")
rep(bykind["shape"]["SCHEMA LOOSER"] == 0 and bykind["format"]["SCHEMA LOOSER"] == 0, "shape and format corruptions: the schema refuses everything my checker refuses (no looser verdicts)")
print("\nfailures: %d" % bad); sys.exit(1 if bad else 0)
