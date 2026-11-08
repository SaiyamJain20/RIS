"""Agent 2 protocol-scope check of A3-0078 (E source-closure amendment, MANIFEST 7810ad10..). Read-only: every input is a git blob at a pinned commit; nothing in the repository is written.

Scope (what A3-0078 asks of agent 2): confirm (1) the exact manifest and base hashes, (2) the new carrier marker and that my consumers recognise it only as a different pinned manifest,
(3) whole-manifest equality in the adapter, (4) an unchanged D50 preimage. This script runs real code of mine (hmbc_protocol.binding, hmbc_protocol.adapter, hmbc_protocol.ledger) on the
exact example. It does NOT run a ledger, a witness, the pool, or agent 3's full validator, and it is a same-model check (correlated).

    python3 -B protocol/v2-review/e-source-closure/check_proposal.py   (repository root; needs jsonschema and the E dependencies; exit 0 = all checks hold)
"""
import copy
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "protocol"))
A3 = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "222cdf2"], text=True).strip()
A3_PUB = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "2f2af3c"], text=True).strip()
A1 = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "2b3d389"], text=True).strip()
FAILS = []


def check(name, cond):
    if not cond:
        FAILS.append(name)
    print(("ok   " if cond else "FAIL ") + name)


def blob(rev, path):
    return subprocess.check_output(["git", "-C", ROOT, "show", f"{rev}:{path}"])


def sha(b):
    return hashlib.sha256(b).hexdigest()


P = "interfaces/proposals/v2-e-source-closure/"
print("origin/agent-3", A3, "| accepted v2 publication", A3_PUB, "| origin/agent-1", A1)

# ---- 1. exact hashes --------------------------------------------------------------------------------------------------------------------------------------------------------------
mf_bytes = blob(A3, P + "MANIFEST.json")
check("MANIFEST.json sha256 is 7810ad105330de73920450d82f4850ebb6de0846396e5bb786818e700e49bb0a", sha(mf_bytes) == "7810ad105330de73920450d82f4850ebb6de0846396e5bb786818e700e49bb0a")
mf = json.loads(mf_bytes)
check("MANIFEST lists exactly AMENDMENT.json, README.md and e-complete-example.json", set(mf["files"]) == {P + "AMENDMENT.json", P + "README.md", P + "e-complete-example.json"})
check("every listed file hashes as the manifest says", all(sha(blob(A3, p)) == h for p, h in mf["files"].items()))
check("the manifest states PROPOSED_NO_ACK, implementationAuthorized false, executionAuthorized false", mf["status"] == "PROPOSED_NO_ACK" and mf["implementationAuthorized"] is False and mf["executionAuthorized"] is False)
base_bytes = blob(A3, "interfaces/v2/hmbc.schema.json")
check("baseSha256 equals the published interfaces/v2/hmbc.schema.json at the proposal commit", sha(base_bytes) == mf["baseSha256"] == "79e34dbb8f9b11b310decf416d27a57aa8c1f249e0c5a6d3985e52740376c093")
check("the published schema and FREEZE.json are byte-identical at the proposal commit and at the accepted publication 2f2af3c",
      blob(A3, "interfaces/v2/hmbc.schema.json") == blob(A3_PUB, "interfaces/v2/hmbc.schema.json") and blob(A3, "interfaces/v2/FREEZE.json") == blob(A3_PUB, "interfaces/v2/FREEZE.json"))
check("FREEZE.json hashes to 7bb1d243d546dcc6ab76dea3edcb23a74240bd96fe274ae3ca0ff56f6aff83cd (the freeze the amendment leaves unchanged)", sha(blob(A3, "interfaces/v2/FREEZE.json")) == "7bb1d243d546dcc6ab76dea3edcb23a74240bd96fe274ae3ca0ff56f6aff83cd")

# ---- 2. the patch and the new carrier ---------------------------------------------------------------------------------------------------------------------------------------------
am = json.loads(blob(A3, P + "AMENDMENT.json"))
check("AMENDMENT pins the same base hash and carries exactly two operations, both `add`", am["baseSha256"] == mf["baseSha256"] and [o["op"] for o in am["operations"]] == ["add", "add"])
base = json.loads(base_bytes)
patched = copy.deepcopy(base)
for op in am["operations"]:
    parts = op["path"].lstrip("/").split("/")
    node = patched
    for k in parts[:-1]:
        node = node[int(k)] if isinstance(node, list) else node[k]
    if parts[-1] == "-":
        node.append(copy.deepcopy(op["value"]))
    else:
        check("add never overwrites: " + op["path"], parts[-1] not in node)
        node[parts[-1]] = copy.deepcopy(op["value"])
defs0, defs1 = base["$defs"], patched["$defs"]
changed = [k for k in defs0 if defs0[k] != defs1[k]]
check("exactly one existing definition changes (LedgerDeployment) and exactly one is added (LedgerDeploymentEComplete)", changed == ["LedgerDeployment"] and set(defs1) - set(defs0) == {"LedgerDeploymentEComplete"})
check("LedgerDeployment gains one oneOf branch, the new carrier, at the end", defs1["LedgerDeployment"]["oneOf"][:-1] == defs0["LedgerDeployment"]["oneOf"] and defs1["LedgerDeployment"]["oneOf"][-1] == {"$ref": "#/$defs/LedgerDeploymentEComplete"})
e_old, e_new = defs0["LedgerDeploymentE"], defs1["LedgerDeploymentEComplete"]
diff_props = {k for k in set(e_old["properties"]) | set(e_new["properties"]) if e_old["properties"].get(k) != e_new["properties"].get(k)}
check("LedgerDeploymentEComplete differs from LedgerDeploymentE only in the properties schemaVersion and sources", diff_props == {"schemaVersion", "sources"}
      and {k: v for k, v in e_old.items() if k != "properties"} == {k: v for k, v in e_new.items() if k != "properties"})
check("the new marker is hmbc-ledger-deployment/v2.1 and its sources are the closed twelve-entry LedgerSourceHashesF",
      e_new["properties"]["schemaVersion"] == {"const": "hmbc-ledger-deployment/v2.1"} and e_new["properties"]["sources"] == {"$ref": "#/$defs/LedgerSourceHashesF"} and len(defs1["LedgerSourceHashesF"]["required"]) == 12)

# ---- 3. validation on the exact example and on the owner's artifacts (jsonschema, draft 2020-12) ----------------------------------------------------------------------------------
import jsonschema  # noqa: E402


def verdict(schema, inst):
    s = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": "#/$defs/LedgerDeployment", "$defs": schema["$defs"]}
    return jsonschema.Draft202012Validator(s).is_valid(inst)


example = json.loads(blob(A3, P + "e-complete-example.json"))
e_v2 = json.loads(blob(A1, "ledger/evidence/af1/slice6-smoke/e-successor/deployment-v2.json"))
f_base = json.loads(blob(A1, "ledger/evidence/af1/slice6-smoke/f-base/deployment.json"))
old_marker_expanded = copy.deepcopy(example); old_marker_expanded["schemaVersion"] = "hmbc-ledger-deployment/v2"
new_marker_ten = copy.deepcopy(example); new_marker_ten["sources"] = dict(list(example["sources"].items())[:10])
extra_key = copy.deepcopy(example); extra_key["unexpected"] = "x"
print("   (example marker %r, owner E carrier marker %r, owner F marker %r)" % (example["schemaVersion"], e_v2["schemaVersion"], f_base["schemaVersion"]))
check("owner v2 E carrier (ten sources): valid under the base schema and under the amended schema", verdict(base, e_v2) and verdict(patched, e_v2))
check("owner F base carrier: valid under the base schema and under the amended schema", verdict(base, f_base) and verdict(patched, f_base))
check("the example: invalid under the base schema, valid under the amended schema", not verdict(base, example) and verdict(patched, example))
check("negative controls under the amended schema: old marker with twelve sources, new marker with ten sources and an extra key are all refused",
      not verdict(patched, old_marker_expanded) and not verdict(patched, new_marker_ten) and not verdict(patched, extra_key))

# ---- 4. my scope: the example against my own code ---------------------------------------------------------------------------------------------------------------------------------
proj = lambda d: {k: v for k, v in d.items() if k not in ("schemaVersion", "sources")}  # noqa: E731
check("the example differs from the owner's v2 E carrier ONLY in schemaVersion and sources (every other member, abi, chains, fixture, compiler, profile, mutations, equal)", proj(example) == proj(e_v2) and example["sources"] != e_v2["sources"])
from hmbc_protocol import adapter, binding, ledger  # noqa: E402

live_mut = {n: example["mutations"] for n in binding.MASK_HOLDERS_E}
check("D50 profile mapping (binding.profile_from_manifest) gives the same result for the example and for the v2 E carrier",
      binding.profile_from_manifest(example["profile"], example["profileEnum"], example["mutations"], example["profileEnum"], live_mut)
      == binding.profile_from_manifest(e_v2["profile"], e_v2["profileEnum"], e_v2["mutations"], e_v2["profileEnum"], live_mut))
src = {p: open(os.path.join(ROOT, "protocol", p), encoding="utf-8").read() for p in ("f0/D50-DEPLOYMENT-BINDING.md", "f0/vectors/d50_reference.py", "hmbc_protocol/binding.py")}
check("D50 never names the deployment's source map or its marker: no `sources`/`hmbc-ledger-deployment` token in the D50 document, its reference or my production module",
      all("hmbc-ledger-deployment" not in t and '"sources"' not in t and "`sources`" not in t and "LedgerSourceHashes" not in t for t in src.values()))
vec = json.load(open(os.path.join(ROOT, "protocol", "f0", "vectors", "d50_binding_vector.json")))
doc = copy.deepcopy(vec["documents"]["repaired-e"]["document"])
h0 = binding.binding_v2(doc)
doc["sources"] = example["sources"]
try:
    binding.binding_v2(doc)
    refused = False
except ValueError:
    refused = True
check("the closed shape of B refuses a `sources` member: the source map cannot enter the binding preimage (B for the pinned repaired-e vector still hashes to its pinned value)", refused and h0 == vec["documents"]["repaired-e"]["bindingV2"])
check("the pinned D50 vector hashes are unchanged by this proposal (repaired-e 242f7ca6.., repaired-f 798f7d72..)", h0.startswith("242f7ca6977e22c9") and binding.binding_v2(vec["documents"]["repaired-f"]["document"]).startswith("798f7d722b2c3a5d"))
check("the existing adapter's structural minimum accepts the example (it reads only chains, contracts and fixture, never the marker or the source map)", adapter._deployment(example) is example)
ok_old = ok_new = None
try:
    ledger.Ledger.from_deployment(e_v2)
    ok_old = "accepted"
except Exception as e:  # noqa: BLE001 - recording the verdict of existing code, whatever it is
    ok_old = type(e).__name__ + ": " + str(e)[:90]
try:
    ledger.Ledger.from_deployment(example)
    ok_new = "accepted"
except Exception as e:  # noqa: BLE001
    ok_new = type(e).__name__ + ": " + str(e)[:90]
print("   Ledger.from_deployment: v2 E carrier ->", ok_old, "| example ->", ok_new)
check("the E ledger loader gives the SAME verdict for the example and for the v2 E carrier (the marker and the source map play no part)", ok_old == ok_new)
check("whole-manifest equality (adapter.py handle_line: `dep != _PINNED`) distinguishes the two carriers: they are different manifests, so an adapter pinned to one refuses the other as WRONG_DESTINATION", example != e_v2)
tokens = {}
for p in ("hmbc_protocol/adapter.py", "hmbc_protocol/ledger.py", "hmbc_protocol/chain.py", "hmbc_protocol/worker.py", "hmbc_protocol/worker_log.py", "hmbc_protocol/witness.py", "hmbc_protocol/witness_state.py",
          "hmbc_protocol/witness_pool.py", "hmbc_protocol/pool_core.py", "hmbc_protocol/binding.py", "hmbc_protocol/export.py"):
    t = open(os.path.join(ROOT, "protocol", p), encoding="utf-8").read()
    tokens[p] = ("hmbc-ledger-deployment" in t, '"sources"' in t or "['sources']" in t)
check("no module of mine reads the deployment's marker or its `sources` member (literal search over the eleven production modules)", not any(a or b for a, b in tokens.values()))
check("my F0 pins are untouched by this check: protocol/f0/MANIFEST.sha256 still verifies", subprocess.run(["sha256sum", "-c", "--quiet", "protocol/f0/MANIFEST.sha256"], cwd=ROOT, capture_output=True).returncode == 0)
print("\nFAILED: %d" % len(FAILS) if FAILS else "\nall checks hold")
sys.exit(1 if FAILS else 0)
