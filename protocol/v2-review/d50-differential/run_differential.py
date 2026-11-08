"""Agent 2 differential of MY D50 reconstruction (`hmbc_protocol.binding_open.reconstruct`) against AGENT 3's independent evaluator-side reconstruction (`evaluation.binding_context_v2.reconstruct`,
A3-0081, origin/agent-3 49fdb51) on the SAME synthetic chain facts. Read-only: agent 3's code and the schemas it needs are extracted with `git archive` into a scratch directory (nothing is copied into
this repository); agent 1's real manifests are read as git blobs (85c59f5). Both reconstructions are same-project and same-model: this is an independent CODE PATH, not an independent author or an external oracle.

The chain is a FAKE answering from each manifest (synthetic runtime bytes of the pinned lengths whose masked hash REPLACES the manifest's runtimeSha256, since the compiled bytes are not available);
nothing here is a measured ledger.

    python3 -B protocol/v2-review/d50-differential/run_differential.py [scratch-dir]      (repository root; needs jsonschema and the E dependencies)
Exit 0 only when the documents agree on every honest case and the two implementations agree on accept/refuse for every fault, except the documented one-sided checks.
"""
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
A3 = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "49fdb51"], text=True).strip()
A1 = "85c59f5"
scratch = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="a3-eval-")
os.makedirs(scratch, exist_ok=True)
tar = subprocess.run(["git", "-C", ROOT, "archive", A3, "evaluation", "interfaces"], capture_output=True, check=True).stdout
subprocess.run(["tar", "-x", "-C", scratch], input=tar, check=True)
sys.path.insert(0, scratch)
sys.path.insert(1, os.path.join(ROOT, "protocol"))
from evaluation import binding_context_v2 as bc3  # noqa: E402
from evaluation.schema_v2 import binding_hash  # noqa: E402
from hmbc_protocol import binding as bd  # noqa: E402
from hmbc_protocol import binding_open as bo  # noqa: E402

FAILS, NOTES = [], []


def check(name, cond):
    if not cond:
        FAILS.append(name)
    print(("ok   " if cond else "FAIL ") + name)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def blob(rev, path):
    return subprocess.check_output(["git", "-C", ROOT, "show", f"{rev}:{path}"])


def synth_code(name, n, flip=None):
    raw = bytearray(hashlib.sha256(name.encode() + (i // 32).to_bytes(4, "big")).digest()[i % 32] for i in range(n))
    if flip is not None:
        raw[flip] ^= 0xFF
    return "0x" + bytes(raw).hex()


def patch_manifest(m):
    """Keep agent 1's real manifest, but replace each runtimeSha256 by the masked hash of my synthetic code of the pinned length (the real compiled bytes are not available)."""
    m = copy.deepcopy(m)
    for name, e in m["abi"].items():
        pairs = bd.pairs_from_object_list(e["immutableReferences"])
        e["runtimeSha256"] = bd.masked_runtime_sha256(synth_code(name, int(e["runtimeBytes"])), pairs, e["runtimeBytes"])
    return m


class Fake:
    """One honest chain pair answering from the manifest; `faults` are applied before BOTH implementations read it."""

    def __init__(self, m):
        self.m = m
        self.head = {"pbc": int(m["chains"]["pbc"]["deployBlock"]) + 100, "dbc": int(m["chains"]["dbc"]["deployBlock"]) + 100}
        self.genesis = {s: "0x" + sha(("genesis" + s).encode()) for s in ("pbc", "dbc")}
        self.chain = {s: m["chains"][s]["chainId"] for s in ("pbc", "dbc")}
        self.missing_block = set()
        self.code_flip, self.code_override, self.value_override = {}, {}, {}
        self.names = {(s, a): n for s in ("pbc", "dbc") for n, a in m["chains"][s]["contracts"].items()}   # the same address can hold a contract on each chain (agent 1's local deployments do)
        self.f = m["profile"] == "repaired-f"
        exp = bc3._expected_views(m)
        self.values = {n: dict(v) for n, v in exp.items()}

    def block_hash(self, side, n):
        return self.genesis[side] if n == 0 else "0x" + sha(("%s:%d" % (side, n)).encode())

    # ---- my view interface ------------------------------------------------------------------------------------------------
    def chain_id(self, side):
        return self.chain[side]

    def latest(self, side):
        return {"number": str(self.head[side]), "hash": self.block_hash(side, self.head[side])}

    def block(self, side, n):
        return None if (side, int(n)) in self.missing_block else {"number": str(int(n)), "hash": self.block_hash(side, int(n))}

    def _code(self, name):
        if name in self.code_override:
            return self.code_override[name]
        return synth_code(name, int(self.m["abi"][name]["runtimeBytes"]), self.code_flip.get(name))

    def code(self, side, address, at):
        return self._code(self.names[(side, address)])

    def call(self, side, address, fn, args, at):
        n = self.names[(side, address)]
        return self.value_override.get((n, fn), self.values[n][fn])

    # ---- agent 3's observation structure -----------------------------------------------------------------------------------
    def observations(self):
        out = {}
        for side in ("pbc", "dbc"):
            pin = self.m["chains"][side]
            anchor = {"number": str(self.head[side]), "hash": self.block_hash(side, self.head[side])}
            rec = lambda v: {"anchor": anchor, "value": v}  # noqa: E731
            out[side] = {"chainId": self.chain[side], "genesisHash": self.genesis[side],
                         "deployBlock": {"number": pin["deployBlock"], "hash": self.block_hash(side, int(pin["deployBlock"]))}, "anchor": anchor, "confirmedAnchor": anchor,
                         "code": {n: rec(self._code(n)) for n in pin["contracts"]},
                         "views": {n: {g: rec(self.value_override.get((n, g), self.values[n][g])) for g in self.values[n]} for n in pin["contracts"]}}
        return out


def mine(m, fake, key=None):
    role = "witness" if key else "worker"
    try:
        return "ok", bo.reconstruct(m, fake, role=role, key_address=key)["document"]
    except bd.OpenRefusal as e:
        return "refused", e.reason
    except ValueError as e:
        return "value-error", str(e)[:80]


def theirs(m, fake):
    try:
        return "ok", bc3.reconstruct(m, fake.observations(), compiled_max_admins="8" if m["profile"] == "repaired-f" else None)
    except Exception as e:  # noqa: BLE001 - agent 3's API raises ValueError for a context mismatch and jsonschema's ValidationError for a manifest the schema refuses; both are refusals
        return "refused", type(e).__name__ + ": " + str(e)[:80]


MANIFESTS = {"F base": "ledger/evidence/af1/migration-v2.1/f-base/deployment.json", "F q2": "ledger/evidence/af1/migration-v2.1/f-q2/deployment.json",
             "E successor (v2.1)": "ledger/evidence/af1/migration-v2.1/e-successor/deployment-v2.json"}
print("agent 3 evaluator", A3, "| agent 1 manifests", A1, "| scratch", scratch)
honest = {}
for label, path in MANIFESTS.items():
    m = patch_manifest(json.loads(blob(A1, path)))
    fake = Fake(m)
    a, b = mine(m, fake), theirs(m, fake)
    check(f"{label}: both reconstructions accept the honest deployment", a[0] == "ok" and b[0] == "ok")
    if a[0] == "ok" and b[0] == "ok":
        check(f"{label}: the two binding DOCUMENTS are equal", a[1] == b[1])
        check(f"{label}: the two binding HASHES are equal ({bd.binding_v2(a[1])[:12]}..)", bd.binding_v2(a[1]) == binding_hash(b[1]))
        honest[label] = (m, fake)
    else:
        print("      mine:", a, "| theirs:", b)

# --- fault differential ------------------------------------------------------------------------------------------------------------------------------------
def faults(m):
    f = m["profile"] == "repaired-f"
    out = []
    for n in ("TMSC", "PSC", "KSSC", "ACSC"):
        out.append((f"{n}.profile differs", lambda x, n=n: x.value_override.update({(n, "profile"): "0"})))
        out.append((f"{n}.mutations differs", lambda x, n=n: x.value_override.update({(n, "mutations"): "7"})))
    for n in ("LSC", "TMSC", "RSC", "PSC", "KSSC", "ACSC"):
        out.append((f"{n}.configured is false", lambda x, n=n: x.value_override.update({(n, "configured"): False})))
    for n, g in (("PSC", "ksscForChain"), ("KSSC", "acsc"), ("ACSC", "kssc"), ("ACSC", "pscRelay"), ("TMSC", "psc"), ("TMSC", "rsc"), ("LSC", "rsc"), ("LSC", "tmsc"), ("LSC", "psc"),
                 ("PSC", "rsc"), ("PSC", "tmsc"), ("PSC", "lsc"), ("RSC", "tmsc"), ("RSC", "lsc")) + ((("TMSC", "governance"), ("Governance", "target")) if f else ()):
        out.append((f"{n}.{g} differs", lambda x, n=n, g=g: x.value_override.update({(n, g): "0x" + "99" * 20})))
    for n in ("PSC", "KSSC") + (("Governance",) if f else ()):
        w = m["fixture"]["witnessSet"]
        out.append((f"{n}.witnesses reordered", lambda x, n=n, w=w: x.value_override.update({(n, "witnesses"): list(reversed(w["witnesses"])) if len(w["witnesses"]) > 1 else ["0x" + "55" * 20]})))
        out.append((f"{n}.threshold differs", lambda x, n=n, w=w: x.value_override.update({(n, "threshold"): "2" if w["threshold"] != "2" else "3"})))
        out.append((f"{n}.version differs", lambda x, n=n: x.value_override.update({(n, "witnessSetVersion"): "9"})))
    for n in m["abi"]:
        refs = m["abi"][n]["immutableReferences"]
        first_free = 0 if not refs or int(refs[0]["start"]) > 0 else int(refs[0]["start"]) + int(refs[0]["length"])
        out.append((f"{n}.code byte outside the slots flipped", lambda x, n=n, o=first_free: x.code_flip.update({n: o})))
        out.append((f"{n}.code empty", lambda x, n=n: x.code_override.update({n: "0x"})))
        out.append((f"{n}.code one byte short", lambda x, n=n: x.code_override.update({n: x._code(n)[:-2]})))
    out.append(("pbc chain id differs", lambda x: x.chain.update(pbc="1")))
    out.append(("dbc chain id differs", lambda x: x.chain.update(dbc="1")))
    return out


agree = disagree = 0
rows = []
for label, (m0, _) in honest.items():
    for fname, apply in faults(m0):
        fake = Fake(m0)
        apply(fake)
        a, b = mine(m0, fake), theirs(m0, fake)
        same = (a[0] == "ok") == (b[0] == "ok")
        rows.append((label, fname, a[0], b[0], same))
        agree += same
        disagree += not same
print(f"\nfaults: {len(rows)} cases, accept/refuse agreement {agree}, disagreement {disagree}")
for r in rows:
    if not r[4]:
        print("   DISAGREE:", r[:4])
check("no fault is accepted by either implementation (every fault is refused by BOTH)", all(r[2] != "ok" and r[3] != "ok" for r in rows))

# --- documented one-sided checks ---------------------------------------------------------------------------------------------------------------------------
m, _ = honest["F base"]
f1 = Fake(m)
f1.value_override[("Governance", "maxGovernanceTtl")] = "999"
a, b = mine(m, f1), theirs(m, f1)
print("one-sided: Governance.maxGovernanceTtl differs  -> mine:", a[0], "| agent 3:", b[0])
NOTES.append(("Governance.maxGovernanceTtl is read and compared only by agent 3's checker (D50 text lists it in neither B nor S0)", a[0] == "ok" and b[0] == "refused"))
m4 = copy.deepcopy(m)
m4["fixture"]["witnessSet"]["threshold"] = "4"
f2 = Fake(m4)
a, b = mine(m4, f2), theirs(m4, f2)
print("one-sided: F witness threshold 4 (set of 4)   -> mine:", a[0], a[1] if a[0] != "ok" else "", "| agent 3:", b[0])
NOTES.append(("an F threshold of 4 over four witnesses is refused by BOTH (mine by the SUCCESSOR-WIRE size/threshold rule, agent 3's by its schema)", a[0] != "ok" and b[0] != "ok"))
for text, flag in NOTES:
    print("   note:", text, "(confirmed)" if flag else "(NOT as expected)")
check("the documented one-sided check on Governance.maxGovernanceTtl behaves as noted", NOTES[0][1])
check("an F threshold of 4 is refused by both", NOTES[1][1])
print("\nFAILED: %d" % len(FAILS) if FAILS else "\nall checks hold")
sys.exit(1 if FAILS else 0)
