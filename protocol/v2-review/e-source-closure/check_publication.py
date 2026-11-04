"""Agent 2 protocol-scope receipt check of the v2.1 publication (A3-0079, interfaces/v2.1/FREEZE.json 232b84bb..) and of agent 1's v2.1 E carrier (A1-0115). Read-only: every input is a git blob
at a pinned commit; nothing in the repository is written. Real code of mine (hmbc_protocol.binding, hmbc_protocol.adapter) runs on the owner's actual v2.1 carrier. It does NOT run a ledger, a witness,
the pool, agent 3's validator, or any live check, and it is a same-model check (correlated). My successor adapter does not exist yet: this checks what a consumer must be able to rely on, not a migration.

    python3 -B protocol/v2-review/e-source-closure/check_publication.py   (repository root; needs jsonschema and the E dependencies; exit 0 = all checks hold)
"""
import copy
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "protocol"))


def rev(x):
    return subprocess.check_output(["git", "-C", ROOT, "rev-parse", x], text=True).strip()


A3, A3_OLD, A3_V2, A1, A1_PUB, A2_ACK = rev("11deed6"), rev("222cdf2"), rev("2f2af3c"), rev("85c59f5"), rev("4615617"), rev("b35d014")
FAILS = []


def check(name, cond):
    if not cond:
        FAILS.append(name)
    print(("ok   " if cond else "FAIL ") + name)


def blob(r, path):
    return subprocess.check_output(["git", "-C", ROOT, "show", f"{r}:{path}"])


def sha(b):
    return hashlib.sha256(b).hexdigest()


print("origin/agent-3", A3, "| agent-1 migration commit", A1, "| agent-1 head", A1_PUB)
fr_bytes = blob(A3, "interfaces/v2.1/FREEZE.json")
fr = json.loads(fr_bytes)
check("interfaces/v2.1/FREEZE.json sha256 is 232b84bb7f997b687a5dc671d79ab6ecdd592d17cd38e531d8460d33ed81660a", sha(fr_bytes) == "232b84bb7f997b687a5dc671d79ab6ecdd592d17cd38e531d8460d33ed81660a")
check("the freeze states implementationAuthorized true and executionAuthorized false, wire family v2, schema revision v2.1", fr["implementationAuthorized"] is True and fr["executionAuthorized"] is False
      and fr["interfaceVersion"] == "v2" and fr["schemaRevision"] == "v2.1")
sch_bytes = blob(A3, "interfaces/v2.1/hmbc.schema.json")
check("the published v2.1 schema hashes to d43c3a9a4cbb10214135afb767a2adc109da462f88bd11a81a8c8955d44fd1f3 and equals the freeze's pin", sha(sch_bytes) == fr["files"]["interfaces/v2.1/hmbc.schema.json"]["sha256"] == "d43c3a9a4cbb10214135afb767a2adc109da462f88bd11a81a8c8955d44fd1f3")
check("the README hashes as the freeze says", sha(blob(A3, "interfaces/v2.1/README.md")) == fr["files"]["interfaces/v2.1/README.md"]["sha256"])
acc_bytes = blob(A3, "communication/E_SOURCE_CLOSURE_ACCEPTANCE.json")
check("the acceptance receipt hashes to 511e235f3aff86a57822e26136282f97bcb9550e84c95263b14ed1bbab8e9fb6 and equals the freeze's pin", sha(acc_bytes) == fr["acceptance"]["sha256"] == "511e235f3aff86a57822e26136282f97bcb9550e84c95263b14ed1bbab8e9fb6")
check("the base freeze, base schema and amendment manifest pins equal the blobs (7bb1d243.., 79e34dbb.., 7810ad10..)", sha(blob(A3, "interfaces/v2/FREEZE.json")) == fr["baseFreeze"]["sha256"]
      and sha(blob(A3, "interfaces/v2/hmbc.schema.json")) == fr["baseSchema"]["sha256"] and sha(blob(A3, "interfaces/proposals/v2-e-source-closure/MANIFEST.json")) == fr["amendment"]["sha256"])
check("the original v2 publication is byte-identical at 2f2af3c and now (schema, FREEZE, and all thirteen inherited payloads equal their pins)",
      all(blob(A3, p) == blob(A3_V2, p) and sha(blob(A3, p)) == h for p, h in fr["inheritedPayloads"].items()) and blob(A3, "interfaces/v2/hmbc.schema.json") == blob(A3_V2, "interfaces/v2/hmbc.schema.json")
      and len(fr["inheritedPayloads"]) == 13)

# the schema is the v2 schema plus exactly the two ACKed operations ---------------------------------------------------------------------------------------------------------------------
am = json.loads(blob(A3_OLD, "interfaces/proposals/v2-e-source-closure/AMENDMENT.json"))
base = json.loads(blob(A3, "interfaces/v2/hmbc.schema.json"))
patched = copy.deepcopy(base)
for op in am["operations"]:
    parts = op["path"].lstrip("/").split("/")
    node = patched
    for k in parts[:-1]:
        node = node[int(k)] if isinstance(node, list) else node[k]
    node.append(copy.deepcopy(op["value"])) if parts[-1] == "-" else node.__setitem__(parts[-1], copy.deepcopy(op["value"]))
published = json.loads(sch_bytes)
check("the published v2.1 schema, parsed, EQUALS the published v2 schema with the two ACKed operations applied (the ACKed patch, nothing else)", published == patched)
check("exactly one existing definition differs from v2 (LedgerDeployment) and one is added (LedgerDeploymentEComplete)", [k for k in base["$defs"] if base["$defs"][k] != published["$defs"][k]] == ["LedgerDeployment"]
      and set(published["$defs"]) - set(base["$defs"]) == {"LedgerDeploymentEComplete"})

# the acceptance receipt names my ACK correctly --------------------------------------------------------------------------------------------------------------------------------------------
acc = json.loads(acc_bytes)
mine = next(a for a in acc["proposalAcks"] if a["owner"] == "agent-2")
my_blob = blob(A2_ACK, mine["path"])
first = subprocess.check_output(["git", "-C", ROOT, "log", "--format=%H", "--diff-filter=A", "--follow", "origin/agent-2", "--", mine["path"]], text=True).split()[-1]
check("the receipt's hash of my A2-0060 equals the blob at b35d014 and at the current head of my branch, and b35d014 is the commit that introduced it",
      sha(my_blob) == mine["sha256"] == "f5b462be848c8f1cb7a2632e5991f372dde2d23b9af5736cf4b18ae5ca03c6c1" and sha(blob(rev("origin/agent-2"), mine["path"])) == mine["sha256"] and first == mine["fileChangingCommit"] == A2_ACK)
check("the receipt records my ACK scope as an amendment PROPOSAL only, and lists no publication mapping ACK yet", mine["scope"] == "protocol producer/consumer amendment proposal only" and acc["publicationMappingAcks"] == [] and acc["executionAuthorized"] is False)

# my consumers on the owner's ACTUAL v2.1 carrier ----------------------------------------------------------------------------------------------------------------------------------------
import jsonschema  # noqa: E402


def valid(schema, inst):
    s = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": "#/$defs/LedgerDeployment", "$defs": schema["$defs"]}
    return jsonschema.Draft202012Validator(s).is_valid(inst)


e21 = json.loads(blob(A1, "ledger/evidence/af1/migration-v2.1/e-successor/deployment-v2.json"))
f_base = json.loads(blob(A1, "ledger/evidence/af1/migration-v2.1/f-base/deployment.json"))
e10 = json.loads(blob("2b3d389", "ledger/evidence/af1/slice6-smoke/e-successor/deployment-v2.json"))
print("   (agent 1's E successor marker %r with %d sources; the old one %r with %d)" % (e21["schemaVersion"], len(e21["sources"]), e10["schemaVersion"], len(e10["sources"])))
check("agent 1's migrated E carrier (85c59f5) carries marker hmbc-ledger-deployment/v2.1, interfaceVersion v2 and twelve sources", e21["schemaVersion"] == "hmbc-ledger-deployment/v2.1" and e21["interfaceVersion"] == "v2" and len(e21["sources"]) == 12)
check("it is valid under the published v2.1 schema and refused by the original v2 schema (so the schema must be SELECTED, never guessed)", valid(published, e21) and not valid(base, e21))
check("the old ten-source E carrier and the F carrier are valid under both schemas; the old carrier with the new marker is refused by v2.1", valid(base, e10) and valid(published, e10) and valid(base, f_base) and valid(published, f_base)
      and not valid(published, dict(e10, schemaVersion="hmbc-ledger-deployment/v2.1")))
proj = lambda d: {k: v for k, v in d.items() if k not in ("schemaVersion", "sources", "createdAt", "producer")}  # noqa: E731
from hmbc_protocol import adapter, binding  # noqa: E402

live = {n: e21["mutations"] for n in binding.MASK_HOLDERS_E}
check("my adapter's structural minimum accepts the owner's v2.1 carrier (it reads only chains, contracts and fixture)", adapter._deployment(e21) is e21)
check("D50's profile mapping (binding.profile_from_manifest) accepts it and gives the base name and enum, exactly as for the ten-source carrier", binding.profile_from_manifest(e21["profile"], e21["profileEnum"], e21["mutations"], e21["profileEnum"], live)
      == binding.profile_from_manifest(e10["profile"], e10["profileEnum"], e10["mutations"], e10["profileEnum"], live))
check("whole-manifest equality distinguishes the carriers (a manifest pinned at v2 is never the v2.1 one): the two E carriers are different manifests", e21 != e10)
vec = json.load(open(os.path.join(ROOT, "protocol", "f0", "vectors", "d50_binding_vector.json")))
doc = copy.deepcopy(vec["documents"]["repaired-e"]["document"])
h0 = binding.binding_v2(doc)
doc["sources"] = e21["sources"]
try:
    binding.binding_v2(doc)
    refused = False
except ValueError:
    refused = True
check("the D50 preimage is unchanged: pinned vector hashes equal (repaired-e 242f7ca6.., repaired-f 798f7d72..) and B still refuses a `sources` member", refused and h0 == vec["documents"]["repaired-e"]["bindingV2"]
      and binding.binding_v2(vec["documents"]["repaired-f"]["document"]).startswith("798f7d722b2c3a5d"))
check("my F0 pins still verify (protocol/f0/MANIFEST.sha256 from the repository root)", subprocess.run(["sha256sum", "-c", "--quiet", "protocol/f0/MANIFEST.sha256"], cwd=ROOT, capture_output=True).returncode == 0)
print("\nFAILED: %d" % len(FAILS) if FAILS else "\nall checks hold")
sys.exit(1 if FAILS else 0)
