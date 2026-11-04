"""Expectations for the exact --binding and witness_state --evidence layouts (agent 2, F0 revision 8; A3-0066 item 4). Written BEFORE the reference exists.

Run: python3 -B -I protocol/f0/vectors/test_export_layouts.py   (standard library only; exit 0 = every expectation holds)
The reference is a SPECIFICATION CHECKER, not production code, and the synthetic documents are illustrative: digests and signatures are well-formed placeholders, not
recovered signatures (no crypto library is used); the record-level invariants it enforces do not need one.
"""
import copy
import hashlib
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


d50 = _load("d50_reference")
L = _load("export_layouts_reference")          # does not exist yet: this file fails at import (the red)
FAILS = []


def check(name, cond):
    if not cond:
        FAILS.append(name)
    print(("ok   " if cond else "FAIL ") + name)


def refuses(fn, token):
    """True when fn raises LayoutError whose message contains `token` (the PRIMARY rule must refuse, not a backstop)."""
    try:
        fn()
    except L.LayoutError as e:
        return token in str(e)
    except Exception:  # noqa: BLE001
        return False
    return False


def ok_ev(doc):
    """None when the evidence document is accepted, else the refusal text: a positive expectation fails, it never crashes the run."""
    try:
        L.validate_evidence(doc)
        return None
    except Exception as e:  # noqa: BLE001
        return "refused: %s" % e


def ok_bx(doc):
    try:
        L.validate_binding_export(doc)
        return None
    except Exception as e:  # noqa: BLE001
        return "refused: %s" % e


def safe_emit():
    try:
        return L.emit()
    except Exception:  # noqa: BLE001
        return {}


def mut(doc, path, value, reseal=True):
    d = copy.deepcopy(doc)
    cur = d
    for k in path[:-1]:
        cur = cur[k]
    if value is KeyError:
        del cur[path[-1]]
    else:
        cur[path[-1]] = value
    if reseal and "evidenceSha256" in d:
        L.seal(d)
    return d


def flip(h):
    return h[:-1] + ("0" if h[-1] != "0" else "1")


# ======================================= --binding =======================================================================================
BE, BF = d50.synthetic_binding_document("repaired-e"), d50.synthetic_binding_document("repaired-f")
ANCHOR = {"pbc": {"number": "141", "hash": "0x" + "ab" * 32}, "dbc": {"number": "161", "hash": "0x" + "cd" * 32}}
WIT = "witness:0x" + "11" * 20
bw, bf = L.binding_export("worker", BE, ANCHOR), L.binding_export(WIT, BF, ANCHOR)
check("B1 the worker and witness exports validate and have exactly the four members {owner, binding_v2, document, anchor}",
      ok_bx(bw) is None and ok_bx(bf) is None and set(bw) == {"owner", "binding_v2", "document", "anchor"})
check("B1 binding_v2 is the D50 hash of the document (E 242f7ca6.., F is the revision-5 value)", bw["binding_v2"] == d50.binding_v2(BE) and bw["binding_v2"].startswith("242f7ca6") and bf["binding_v2"] == d50.binding_v2(BF))
line = L.render(bw)
check("B2 the output is ONE line: canonical compact JSON with sorted keys, ASCII, one LF", line.endswith("\n") and line.count("\n") == 1 and ": " not in line and ", " not in line
      and line[:-1] == json.dumps(bw, sort_keys=True, separators=(",", ":"), ensure_ascii=True) and json.loads(line) == bw)
check("B2 key order of the input does not change the output", L.render(dict(reversed(list(bw.items())))) == line)
check("B3 an extra member is refused", refuses(lambda: L.validate_binding_export({**bw, "createdAt": "x"}), "members"))
check("B3 a missing member is refused", refuses(lambda: L.validate_binding_export({k: v for k, v in bw.items() if k != "anchor"}), "members"))
check("B4 a wrong binding_v2 is refused", refuses(lambda: L.validate_binding_export({**bw, "binding_v2": flip(bw["binding_v2"])}), "binding_v2"))
check("B4 a document changed without recomputing binding_v2 is refused", refuses(lambda: L.validate_binding_export({**bw, "document": {**BE, "interfaceVersion": "v2"}}), "binding_v2"))
check("B4 an invalid D50 document is refused (an excluded mutable field cannot leak in)", refuses(lambda: L.validate_binding_export({**bw, "document": {**BE, "authEpoch": "1"}}), "document"))
for bad in ("Worker", "witness:", "witness:0x" + "AB" * 20, "witness:0x" + "11" * 19, "witness:" + "11" * 20, "worker ", "witness:0x" + "11" * 20 + "x"):
    check("B5 owner %r is refused" % bad, refuses(lambda bad=bad: L.validate_binding_export({**bw, "owner": bad}), "owner"))
check("B6 anchor must have exactly the chains pbc and dbc", refuses(lambda: L.validate_binding_export({**bw, "anchor": {"pbc": ANCHOR["pbc"]}}), "anchor")
      and refuses(lambda: L.validate_binding_export({**bw, "anchor": {**ANCHOR, "x": ANCHOR["pbc"]}}), "anchor"))
check("B6 anchor number must be a decimal string and the hash 0x + 64 lowercase hex", refuses(lambda: L.validate_binding_export({**bw, "anchor": {**ANCHOR, "pbc": {"number": 141, "hash": ANCHOR["pbc"]["hash"]}}}), "anchor")
      and refuses(lambda: L.validate_binding_export({**bw, "anchor": {**ANCHOR, "dbc": {"number": "161", "hash": "0x" + "CD" * 32}}}), "anchor"))
check("B6 an anchor below the deploy block is refused", refuses(lambda: L.validate_binding_export({**bw, "anchor": {**ANCHOR, "pbc": {"number": "135", "hash": ANCHOR["pbc"]["hash"]}}}), "anchor"))
check("B7 the E and F exports bind differently", bw["binding_v2"] != bf["binding_v2"])
check("B8 the stderr refusal line is canonical JSON {code, message, reason} with the code the reason maps to",
      L.error_line("STORE_MISSING", "no store") == '{"code":"ADAPTER_UNAVAILABLE","message":"no store","reason":"STORE_MISSING"}\n'
      and json.loads(L.error_line("STORE_CORRUPT", "x"))["code"] == "ADAPTER_UNAVAILABLE" and json.loads(L.error_line("LEGACY_STATE", "x"))["code"] == "WRONG_DESTINATION")
check("B8 an exporter may refuse only STORE_MISSING, STORE_CORRUPT or LEGACY_STATE (it reads the store only and makes no RPC)", all(
      refuses(lambda r=r: L.error_line(r, "x"), "reason") for r in ("BINDING_MISMATCH", "CODE_MISMATCH", "LEDGER_UNREACHABLE", "WITNESS_FAULTED", "NOPE")))

# ======================================= --evidence ======================================================================================
H, FA, CL = L.synthetic_evidence("history"), L.synthetic_evidence("faulted"), L.synthetic_evidence("cleared")
for n, d in (("history", H), ("faulted", FA), ("cleared", CL)):
    check("E1 the synthetic %s document validates" % n, ok_ev(d) is None)
check("E1 evidenceSha256 is the sha256 of the canonical JSON of the document without that member", all(
      d["evidenceSha256"] == hashlib.sha256(json.dumps({k: v for k, v in d.items() if k != "evidenceSha256"}, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()
      for d in (H, FA, CL)))
check("E1 the three variants differ (a fault and a clear change the evidence)", len({H["evidenceSha256"], FA["evidenceSha256"], CL["evidenceSha256"]}) == 3)
check("E1 the history covers all four types, a supersession by expiry and one by a decision overtaken by the checkpoint sequence",
      {c["type"] for c in H["conflicts"]} == set(L.TYPES) and {s["death"]["kind"] for s in H["superseded"]} == {"expiry", "overtaken-decision-sequence"})
check("E2 an extra top-level member is refused", refuses(lambda: L.validate_evidence({**H, "privateKey": "0x00"}), "members"))
check("E2 a missing top-level member is refused", refuses(lambda: L.validate_evidence({k: v for k, v in H.items() if k != "faultLog"}), "members"))
check("E2 a wrong schemaVersion is refused", refuses(lambda: L.validate_evidence(mut(H, ["schemaVersion"], "hmbc-witness-evidence/v1")), "schemaVersion"))
check("E3 owner must be a witness (the worker has no signing store): changed together with the marker so that only this rule can refuse",
      refuses(lambda: L.validate_evidence(mut(mut(H, ["owner"], "worker"), ["marker", "owner"], "worker")), "witness:0x"))
check("E3 the marker must equal the binding and the owner", refuses(lambda: L.validate_evidence(mut(H, ["marker", "owner"], "witness:0x" + "22" * 20)), "marker")
      and refuses(lambda: L.validate_evidence(mut(H, ["marker", "binding_v2"], flip(H["marker"]["binding_v2"]))), "marker") and refuses(lambda: L.validate_evidence(mut(H, ["marker", "schema"], "1")), "marker"))
check("E3 binding.binding_v2 must be the D50 hash of binding.document", refuses(lambda: L.validate_evidence(mut(H, ["binding", "binding_v2"], flip(H["binding"]["binding_v2"]))), "binding_v2"))
check("E3 a wrong evidenceSha256 is refused (any unsealed change is caught)", refuses(lambda: L.validate_evidence({**H, "evidenceSha256": flip(H["evidenceSha256"])}), "evidenceSha256")
      and refuses(lambda: L.validate_evidence(mut(H, ["conflicts", 0, "digests", 0, "signature"], "0x" + "9" * 130, reseal=False)), "evidenceSha256"))
# observations
check("E4 observations: exactly one per chain, ascending chainId, closed shape", refuses(lambda: L.validate_evidence(mut(H, ["observations"], list(reversed(H["observations"])))), "observations")
      and refuses(lambda: L.validate_evidence(mut(H, ["observations"], H["observations"] + [H["observations"][0]])), "observations")
      and refuses(lambda: L.validate_evidence(mut(H, ["observations", 0, "extra"], "1")), "observations") and refuses(lambda: L.validate_evidence(mut(H, ["observations"], [])), "observations"))
# conflicts: shape and order
c0 = H["conflicts"][0]
check("E5 conflicts are sorted by (type order, domainSeparator, witnessSetVersion, key) and unique per K", refuses(lambda: L.validate_evidence(mut(H, ["conflicts"], list(reversed(H["conflicts"])))), "sorted")
      and refuses(lambda: L.validate_evidence(mut(H, ["conflicts"], H["conflicts"][:1] + H["conflicts"][:1] + H["conflicts"][1:])), "K"))
check("E5 digests inside a record are sorted by (expiresAt, digest)", any(len(c["digests"]) > 1 for c in H["conflicts"]) and refuses(lambda: L.validate_evidence(
      mut(H, ["conflicts", [i for i, c in enumerate(H["conflicts"]) if len(c["digests"]) > 1][0], "digests"], list(reversed(next(c for c in H["conflicts"] if len(c["digests"]) > 1)["digests"])))), "sorted"))
check("E5 vHash must be the sha256 of the canonical JSON of the effect", refuses(lambda: L.validate_evidence(mut(H, ["conflicts", 0, "vHash"], flip(c0["vHash"]))), "vHash"))
check("E5 the effect is closed per type: a missing and an extra field are refused", refuses(lambda: L.validate_evidence(mut(H, ["conflicts", 0, "effect", "zz"], "0")), "effect")
      and refuses(lambda: L.validate_evidence(mut(H, ["conflicts", 0, "effect"], {})), "effect"))
check("E5 effect.witnessSetVersion must equal the key's witnessSetVersion (1 versus 2: both legal alone, so only the equality rule can refuse)",
      refuses(lambda: L.validate_evidence(mut(H, ["conflicts", 0, "effect", "witnessSetVersion"], "1")), "differs from effect.witnessSetVersion"))
by = {c["type"]: i for i, c in enumerate(H["conflicts"])}
check("E5 keyField format per type: decimal for StateCheckpoint and GovernanceAction, 0x + 64 hex for AccessDecision and GrantReceipt",
      refuses(lambda: L.validate_evidence(mut(H, ["conflicts", by["StateCheckpoint"], "keyField"], "0x" + "1" * 64)), "keyField")
      and refuses(lambda: L.validate_evidence(mut(H, ["conflicts", by["GovernanceAction"], "keyField"], "03")), "keyField")
      and refuses(lambda: L.validate_evidence(mut(H, ["conflicts", by["AccessDecision"], "keyField"], "7")), "keyField")
      and refuses(lambda: L.validate_evidence(mut(H, ["conflicts", by["GrantReceipt"], "keyField"], "0x" + "A" * 64)), "keyField"))
check("E5 expiresAt is present on every digest of a type with a liveness field and absent for GrantReceipt", refuses(lambda: L.validate_evidence(mut(H, ["conflicts", by["GrantReceipt"], "digests", 0, "expiresAt"], "5")), "must be absent")
      and refuses(lambda: L.validate_evidence(mut(H, ["conflicts", by["StateCheckpoint"], "digests", 0, "expiresAt"], KeyError)), "is required"))
check("E5 a record has at least one digest, and signatures and digests are well formed", refuses(lambda: L.validate_evidence(mut(H, ["conflicts", 0, "digests"], [])), "digests")
      and refuses(lambda: L.validate_evidence(mut(H, ["conflicts", 0, "digests", 0, "signature"], "0x12")), "signature")
      and refuses(lambda: L.validate_evidence(mut(H, ["conflicts", 0, "digests", 0, "digest"], "0x" + "G" * 64)), "digest"))
dg = H["conflicts"][1]["digests"][0]["digest"]
check("E5 a digest occurs once in the whole store (live and superseded)", refuses(lambda: L.validate_evidence(mut(H, ["conflicts", 0, "digests", 0, "digest"], dg)), "digest")
      and refuses(lambda: L.validate_evidence(mut(H, ["superseded", 0, "digests", 0, "digest"], dg)), "digest"))
# superseded and death evidence
check("E6 superseded rows are numbered 1..n in append order", refuses(lambda: L.validate_evidence(mut(H, ["superseded", 0, "seq"], "2")), "seq") and refuses(lambda: L.validate_evidence(mut(H, ["superseded"], list(reversed(H["superseded"])))), "seq"))
sx = next(i for i, s in enumerate(H["superseded"]) if s["death"]["kind"] == "expiry")
so = next(i for i, s in enumerate(H["superseded"]) if s["death"]["kind"] == "overtaken-decision-sequence")
e_max = max(int(d["expiresAt"]) for d in H["superseded"][sx]["digests"])
check("E6 death by expiry needs observation.timestamp >= the latest expiresAt of every digest of the record", refuses(lambda: L.validate_evidence(mut(H, ["superseded", sx, "death", "observation", "timestamp"], str(e_max - 1))), "expiry")
      and ok_ev(mut(H, ["superseded", sx, "death", "observation", "timestamp"], str(e_max))) is None)
check("E6 death by overtaken-decision-sequence needs observed > effect.stateSequence", refuses(lambda: L.validate_evidence(mut(H, ["superseded", so, "death", "observed"], H["superseded"][so]["effect"]["stateSequence"])), "overtaken")
      and ok_ev(mut(H, ["superseded", so, "death", "observed"], str(int(H["superseded"][so]["effect"]["stateSequence"]) + 1))) is None)
check("E6 a death kind must match the type of the record", refuses(lambda: L.validate_evidence(mut(H, ["superseded", sx, "death", "kind"], "executed-receipt")), "kind")
      and refuses(lambda: L.validate_evidence(mut(H, ["superseded", sx, "death", "kind"], "no-such-kind")), "kind"))
check("E6 observed is present exactly for the three numeric kinds", refuses(lambda: L.validate_evidence(mut(H, ["superseded", sx, "death", "observed"], "1")), "observed")
      and refuses(lambda: L.validate_evidence(mut(H, ["superseded", so, "death", "observed"], KeyError)), "observed"))
check("E6 the death observation's chain must be one of the observed chains", refuses(lambda: L.validate_evidence(mut(H, ["superseded", sx, "death", "observation", "chainId"], "99999")), "chain"))
live_k = H["conflicts"][by["StateCheckpoint"]]
check("E6 a superseded effect must differ from the live effect for the same K (otherwise it is not a supersession)", refuses(lambda: L.validate_evidence(
      mut(mut(H, ["superseded", sx, "effect"], live_k["effect"]), ["superseded", sx, "vHash"], live_k["vHash"])), "supersession"))
# tripwire and monotonicity
last = {o["chainId"]: o for o in H["observations"]}
cid = H["binding"]["document"]["chains"]["dbc"]["chainId"]          # conflicts[0] is an AccessDecision: its target ledger is the DBC (SIGNING-RULES section 6)
pid = H["binding"]["document"]["chains"]["pbc"]["chainId"]
check("E7 without a fault, no recorded observation may exceed the stored last observation of its chain (number, timestamp), and equal numbers need equal hashes",
      refuses(lambda: L.validate_evidence(mut(H, ["conflicts", 0, "digests", 0, "observation"], {**last[cid], "blockNumber": str(int(last[cid]["blockNumber"]) + 1)})), "monoton")
      and refuses(lambda: L.validate_evidence(mut(H, ["conflicts", 0, "digests", 0, "observation"], {**last[cid], "timestamp": str(int(last[cid]["timestamp"]) + 1)})), "monoton")
      and refuses(lambda: L.validate_evidence(mut(H, ["conflicts", 0, "digests", 0, "observation"], {**last[cid], "blockHash": flip(last[cid]["blockHash"])})), "monoton"))
lastcl = {o["chainId"]: o for o in CL["observations"]}
check("E7 the same regression inside a store that has a fault log is accepted (explicitly out of the safe-ledger assumption for that interval)",
      ok_ev(mut(CL, ["conflicts", 0, "digests", 0, "observation"], {**lastcl[cid], "blockNumber": str(int(lastcl[cid]["blockNumber"]) + 5)})) is None)
check("E7 a digest's observation must be of the target ledger of its type (DBC for checkpoint and decision, PBC for governance and receipt)",
      refuses(lambda: L.validate_evidence(mut(H, ["conflicts", 0, "digests", 0, "observation"], last[pid])), "target"))
check("E7 a fault must be consistent with its reason (number-regression, timestamp-regression, hash-changed)", ok_ev(FA) is None
      and refuses(lambda: L.validate_evidence(mut(FA, ["faulted", "reason"], "timestamp-regression")), "fault") and refuses(lambda: L.validate_evidence(mut(FA, ["faulted", "reason"], "hash-changed")), "fault")
      and refuses(lambda: L.validate_evidence(mut(FA, ["faulted", "reason"], "other")), "fault"))
check("E7 a faulted store keeps the previous observation as its last one", refuses(lambda: L.validate_evidence(mut(FA, ["faulted", "previous"], {**FA["faulted"]["previous"], "blockNumber": "1"})), "fault"))
check("E7 a cleared fault is a fault-log row with a note, appended in order, and the store is no longer faulted", CL["faulted"] is None and len(CL["faultLog"]) == 1
      and refuses(lambda: L.validate_evidence(mut(CL, ["faultLog", 0, "note"], "")), "note") and refuses(lambda: L.validate_evidence(mut(CL, ["faultLog", 0, "seq"], "2")), "seq")
      and refuses(lambda: L.validate_evidence(mut(CL, ["faultLog", 0, "clearedAgainst"], {**CL["faultLog"][0]["clearedAgainst"], "blockNumber": str(int(lastcl[cid]["blockNumber"]) + 100)})), "baseline")
      and refuses(lambda: L.validate_evidence(mut(CL, ["faultLog", 0, "clearedAgainst", "chainId"], "99999")), "baseline"))
older = {"chainId": cid, "blockNumber": "155", "blockHash": L._h("block:%s:155" % cid), "timestamp": "1791521550"}      # an earlier clear, at or before the stored last observation
check("E7 a store that is faulted again after an earlier clear is accepted (the log row's baseline is not later than the stored last observation)",
      ok_ev(L.seal({**copy.deepcopy(FA), "faultLog": [{**copy.deepcopy(CL["faultLog"][0]), "clearedAgainst": older}]})) is None)
# refusal line and the emitted vector
EM = safe_emit()
check("E8 the vector can be emitted (the emitter validates every document it lists)", bool(EM))
check("E8 the emitted vector holds the binding exports, the three evidence documents and the refusal lines, and every one validates",
      all(k in EM for k in ("bindingExports", "evidence", "refusalLines")) and all(ok_bx(x) is None for x in EM.get("bindingExports", {}).values())
      and all(ok_ev(x) is None for x in EM.get("evidence", {}).values()))
check("E8 the emitted vector is deterministic", json.dumps(EM, sort_keys=True) == json.dumps(safe_emit(), sort_keys=True))

print("\nFAILED: %d" % len(FAILS) if FAILS else "\nall expectations hold")
sys.exit(1 if FAILS else 0)
