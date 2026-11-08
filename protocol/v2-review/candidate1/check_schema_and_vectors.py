"""1. schema validity; 2. every candidate vector validates against AdapterResponse; 3. the candidate's 12 wire examples satisfy MY semantic wire checker
(protocol/f0/vectors/check_wire_examples.py run on a copy of SUCCESSOR-WIRE.md whose 12 JSON examples are replaced by the candidate's);
4. the 19-reason table equals SUCCESSOR-WIRE section 1; 5. the D50 owner vectors equal protocol/f0/vectors/d50_binding_vector.json;
6. `recorded`/`collection` are accepted only by the operation that owns them."""
import copy, json, os, re, subprocess, sys, tempfile
from common import *
from jsonschema import Draft202012Validator
root = proposal(sys.argv)
schema = load(root, "hmbc.schema.json"); D = schema["$defs"]
Draft202012Validator.check_schema(schema); print("PASS schema is a valid draft 2020-12 schema; %d definitions" % len(D))
V = lambda ref: Draft202012Validator({"$ref": "#/$defs/" + ref, "$defs": D})
resp = V("AdapterResponse"); bad = 0
wire = load(root, "vectors/wire.json"); succ = load(root, "vectors/success.json")
print("wire.json sourceSha256 == my SUCCESSOR-WIRE.md sha256:", wire["sourceSha256"] == sha(os.path.join(F0, "SUCCESSOR-WIRE.md")))
for i, r in enumerate(wire["responses"], 1):
    ok = resp.is_valid(r); bad += (not ok); print("%s wire example %d validates against AdapterResponse" % ("PASS" if ok else "FAIL", i))
for i, x in enumerate(succ, 1):
    ok = resp.is_valid(x["response"]); bad += (not ok); print("%s success vector %d (%s) validates against AdapterResponse" % ("PASS" if ok else "FAIL", i, x["operation"]))
# 3. my semantic checker on their examples
src = open(os.path.join(F0, "SUCCESSOR-WIRE.md")).read()
blocks = re.findall(r"```json\n(.*?)\n```", src, re.S)
assert len(blocks) == len(wire["responses"]) == 12
doc = src
for b, r in zip(blocks, wire["responses"]):
    doc = doc.replace(b, json.dumps(r, separators=(",", ":")), 1)
with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, "wire_with_candidate_examples.md"); open(p, "w").write(doc)
    r = subprocess.run([sys.executable, "-B", os.path.join(F0, "vectors", "check_wire_examples.py"), p], capture_output=True, text=True)
fails = [l for l in r.stdout.splitlines() if l.startswith("FAIL")]
print("%s my check_wire_examples.py on the candidate's 12 examples: exit %d, %d FAIL lines" % ("PASS" if r.returncode == 0 else "FAIL", r.returncode, len(fails))); bad += r.returncode != 0
# 4. reasons
tab = {}
for line in src.splitlines():
    m = re.match(r"^\| ((?:`[A-Z_]+`(?:, )?)+) \| `([A-Z_]+)` \|", line)
    if m:
        for n in re.findall(r"`([A-Z_]+)`", m.group(1)): tab[n] = m.group(2)
theirs = load(root, "reason-codes.json")
ok = tab == theirs and len(tab) == 19; bad += (not ok); print("%s reason-codes.json equals the 19-row table of SUCCESSOR-WIRE section 1" % ("PASS" if ok else "FAIL"))
ok = set(D["Error"]["properties"]["reason"]["enum"]) == set(tab) == set(D["WitnessOutcome"]["properties"]["reason"]["enum"]); bad += (not ok)
print("%s Error.reason and WitnessOutcome.reason enums equal the table" % ("PASS" if ok else "FAIL"))
# 5. D50 vectors
mine = json.load(open(os.path.join(F0, "vectors", "d50_binding_vector.json"))); their = load(root, "d50-owner-vectors.json")
ok = mine == their; bad += (not ok); print("%s d50-owner-vectors.json content equals protocol/f0/vectors/d50_binding_vector.json" % ("PASS" if ok else "FAIL"))
# 6. scoping
rec = [r for r in wire["responses"] if r.get("error") and "recorded" in r["error"]][0]
col = [r for r in wire["responses"] if r.get("error") and "collection" in r["error"]][0]
for op in ("CollectDecisionResponse", "AttestGrantResponse", "ReleaseResponse", "PrepareRequestResponse", "CollectGovernanceResponse"):
    ok = not V(op).is_valid(rec); bad += (not ok); print("%s `recorded` error is rejected by %s" % ("PASS" if ok else "FAIL", op))
ok = V("CollectCheckpointResponse").is_valid(rec); bad += (not ok); print("%s `recorded` error is accepted by CollectCheckpointResponse" % ("PASS" if ok else "FAIL"))
for op in ("ReleaseResponse", "PrepareRequestResponse", "EncryptRecordResponse"):
    ok = not V(op).is_valid(col); bad += (not ok); print("%s pool `collection` failure is rejected by %s" % ("PASS" if ok else "FAIL", op))
print("\nfailures: %d" % bad); sys.exit(1 if bad else 0)
