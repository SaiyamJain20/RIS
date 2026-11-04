"""Exact layouts of the read-only evidence exporters (agent 2, F0 revision 8; A3-0066 item 4): SPECIFICATION CHECKER, not production code and not a measurement.

Defines, as executable rules, (1) the `--binding` export {owner, binding_v2, document, anchor}, (2) the `witness_state --evidence` document, sealed by `evidenceSha256`,
(3) the one-line canonical rendering and (4) the stderr refusal line. The synthetic documents are illustrative: digests and signatures are well-formed placeholders (no crypto
library is used); the record-level invariants below do not need recovery. Standard library only; the D50 reference supplies the binding document rules.

    python3 -B -I export_layouts_reference.py --emit > export_layouts_vectors.json
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("d50_reference", os.path.join(HERE, "d50_reference.py"))
d50 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(d50)


class LayoutError(ValueError):
    pass


def canonical_json(x) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def render(doc) -> str:
    """stdout of a successful export: canonical compact JSON, ASCII, sorted keys, exactly one trailing LF."""
    return canonical_json(doc) + "\n"


_DEC = re.compile(r"(0|[1-9][0-9]*)")
_ADDR = re.compile(r"0x[0-9a-f]{40}")
_H32 = re.compile(r"0x[0-9a-f]{64}")
_SHA = re.compile(r"[0-9a-f]{64}")
_SIG = re.compile(r"0x[0-9a-f]{130}")
_OWNER_W = re.compile(r"witness:0x[0-9a-f]{40}")


def _fail(msg):
    raise LayoutError(msg)


def _closed(obj, keys, what):
    if not isinstance(obj, dict) or set(obj) != set(keys):
        _fail(f"{what}: members {sorted(obj) if isinstance(obj, dict) else type(obj).__name__} do not equal {sorted(keys)}")
    return obj


def _rx(rx, v, what):
    if not isinstance(v, str) or not rx.fullmatch(v):
        _fail(f"{what}: bad format")
    return v


# ---- refusal line --------------------------------------------------------------------------------------------------------------------
ERROR_REASONS = {"STORE_MISSING": "ADAPTER_UNAVAILABLE", "STORE_CORRUPT": "ADAPTER_UNAVAILABLE", "LEGACY_STATE": "WRONG_DESTINATION"}


def error_line(reason, message) -> str:
    """stderr of a refused export (exit code 3): the closed successor Error members {code, message, reason}. An exporter reads the store only and makes no RPC, so it can refuse
    only a missing store, a corrupt store, or a store without binding rows that holds rows (a legacy E store)."""
    if reason not in ERROR_REASONS:
        _fail("reason: an exporter may refuse only " + ", ".join(sorted(ERROR_REASONS)))
    if not isinstance(message, str) or not message:
        _fail("message must be a non-empty string")
    return render({"code": ERROR_REASONS[reason], "message": message, "reason": reason})


# ---- --binding -----------------------------------------------------------------------------------------------------------------------
def binding_export(owner, document, anchor) -> dict:
    return {"owner": owner, "binding_v2": d50.binding_v2(document), "document": document, "anchor": anchor}


def _owner(v, what="owner", witness_only=False):
    if not isinstance(v, str) or not (_OWNER_W.fullmatch(v) or (v == "worker" and not witness_only)):
        _fail(f"{what}: must be 'worker' or 'witness:0x' + 40 lowercase hex" if not witness_only else f"{what}: must be 'witness:0x' + 40 lowercase hex")
    return v


def validate_binding_export(doc):
    _closed(doc, ["owner", "binding_v2", "document", "anchor"], "export members")
    _owner(doc["owner"])
    try:
        d50.validate(doc["document"])
    except ValueError as e:
        _fail("document: " + str(e))
    _rx(_SHA, doc["binding_v2"], "binding_v2")
    if doc["binding_v2"] != d50.binding_v2(doc["document"]):
        _fail("binding_v2 is not the D50 hash of document")
    a = _closed(doc["anchor"], ["pbc", "dbc"], "anchor members")
    for side in ("pbc", "dbc"):
        row = _closed(a[side], ["number", "hash"], f"anchor.{side} members")
        _rx(_DEC, row["number"], f"anchor.{side}.number")
        _rx(_H32, row["hash"], f"anchor.{side}.hash")
        if int(row["number"]) < int(doc["document"]["chains"][side]["deployBlock"]["number"]):
            _fail(f"anchor.{side}.number is below the deploy block")


# ---- --evidence ----------------------------------------------------------------------------------------------------------------------
TYPES = ("AccessDecision", "StateCheckpoint", "GrantReceipt", "GovernanceAction")
_RANK = {t: i for i, t in enumerate(TYPES)}
TARGET = {"AccessDecision": "dbc", "StateCheckpoint": "dbc", "GrantReceipt": "pbc", "GovernanceAction": "pbc"}
HAS_EXPIRY = {"AccessDecision": True, "StateCheckpoint": True, "GrantReceipt": False, "GovernanceAction": True}
_KEY_RX = {"StateCheckpoint": _DEC, "GovernanceAction": _DEC, "AccessDecision": _H32, "GrantReceipt": _H32}
_DEC_, _ADDR_, _H32_ = ("dec", _DEC), ("addr", _ADDR), ("h32", _H32)
_WSV = ("enum", ("1", "2"))
EFFECT = {   # V = every signed field except the key field and the liveness field (SIGNING-RULES section 1)
    "StateCheckpoint": {"authEpoch": _DEC_, "policyVersion": _DEC_, "keyEpoch": ("enum", ("0",)), "witnessSetVersion": _WSV, "sourceChainId": _DEC_, "psc": _ADDR_,
                        "sourceBlockNumber": _DEC_, "sourceBlockHash": _H32_},
    "AccessDecision": {"result": ("enum", ("0", "1")), "credentialDigest": _H32_, "stateSequence": _DEC_, "witnessSetVersion": _WSV, "sourceBlockNumber": _DEC_, "sourceBlockHash": _H32_},
    "GrantReceipt": {"grantId": _H32_, "gid": _ADDR_, "dataId": _H32_, "keyEpoch": ("enum", ("0",)), "grantExpiresAt": _DEC_, "witnessSetVersion": _WSV, "dbcChainId": _DEC_,
                     "kssc": _ADDR_, "dbcBlockNumber": _DEC_, "dbcBlockHash": _H32_},
    "GovernanceAction": {"action": ("enum", ("1", "2", "3")), "root": _ADDR_, "admins": ("addrs", None), "witnessSetVersion": ("enum", ("2",))},
}
DEATH = {   # kind -> (types it can apply to, whether `observed` (the state value read) is carried), SIGNING-RULES section 6
    "expiry": ({"AccessDecision", "StateCheckpoint", "GovernanceAction"}, False),
    "overtaken-checkpoint": ({"StateCheckpoint"}, True),
    "overtaken-governance": ({"GovernanceAction"}, True),
    "overtaken-decision-sequence": ({"AccessDecision"}, True),
    "overtaken-decision-grant": ({"AccessDecision"}, False),
    "executed-receipt": ({"GrantReceipt"}, False),
}
FAULT_REASONS = ("number-regression", "timestamp-regression", "hash-changed")
MEMBERS = ["schemaVersion", "owner", "binding", "marker", "observations", "faulted", "faultLog", "conflicts", "superseded", "evidenceSha256"]


def _obs(o, what):
    _closed(o, ["chainId", "blockNumber", "blockHash", "timestamp"], what)
    _rx(_DEC, o["chainId"], what + ".chainId")
    _rx(_DEC, o["blockNumber"], what + ".blockNumber")
    _rx(_H32, o["blockHash"], what + ".blockHash")
    _rx(_DEC, o["timestamp"], what + ".timestamp")
    return o


def _field(spec, v, what):
    kind, arg = spec
    if kind == "dec":
        _rx(_DEC, v, what)
    elif kind == "addr":
        _rx(_ADDR, v, what)
    elif kind == "h32":
        _rx(_H32, v, what)
    elif kind == "enum":
        if v not in arg:
            _fail(f"{what}: bad value")
    elif kind == "addrs":
        if not isinstance(v, list) or len(v) > 8:
            _fail(f"{what}: bad list")
        for a in v:
            _rx(_ADDR, a, what + "[]")


def _effect(t, e):
    _closed(e, EFFECT[t], "effect members")
    for k, spec in EFFECT[t].items():
        _field(spec, e[k], "effect." + k)


def _digests(t, rows, what):
    if not isinstance(rows, list) or not rows:
        _fail(f"{what}.digests: a record has at least one digest")
    keys = []
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            _fail(f"{what}.digests[{i}]: not an object")
        if HAS_EXPIRY[t] and "expiresAt" not in r:
            _fail(f"{what}.digests[{i}]: expiresAt is required for {t}")
        if not HAS_EXPIRY[t] and "expiresAt" in r:
            _fail(f"{what}.digests[{i}]: expiresAt must be absent for {t} (no liveness field)")
        _closed(r, ["digest", "signature", "observation"] + (["expiresAt"] if HAS_EXPIRY[t] else []), f"{what}.digests[{i}] members")
        _rx(_H32, r["digest"], f"{what}.digests[{i}].digest")
        _rx(_SIG, r["signature"], f"{what}.digests[{i}].signature")
        if HAS_EXPIRY[t]:
            _rx(_DEC, r["expiresAt"], f"{what}.digests[{i}].expiresAt")
        _obs(r["observation"], f"{what}.digests[{i}].observation")
        keys.append((int(r["expiresAt"]) if HAS_EXPIRY[t] else -1, r["digest"]))
    if keys != sorted(keys):
        _fail(f"{what}.digests: not sorted by (expiresAt, digest)")


def _record(r, what, extra=()):
    _closed(r, ["type", "domainSeparator", "witnessSetVersion", "keyField", "effect", "vHash", "digests"] + list(extra), what + " members")
    t = r["type"]
    if t not in TYPES:
        _fail(f"{what}.type: unknown")
    _rx(_H32, r["domainSeparator"], what + ".domainSeparator")
    _rx(_DEC, r["witnessSetVersion"], what + ".witnessSetVersion")
    _rx(_KEY_RX[t], r["keyField"], what + ".keyField")
    _effect(t, r["effect"])
    if r["effect"]["witnessSetVersion"] != r["witnessSetVersion"]:
        _fail(what + ".witnessSetVersion differs from effect.witnessSetVersion")
    _rx(_SHA, r["vHash"], what + ".vHash")
    if r["vHash"] != hashlib.sha256(canonical_json(r["effect"]).encode("ascii")).hexdigest():
        _fail(what + ".vHash is not the sha256 of the canonical JSON of effect")
    _digests(t, r["digests"], what)
    return (t, r["domainSeparator"], r["witnessSetVersion"], r["keyField"])


def _sort_key(r):
    k = r["keyField"]
    return (_RANK[r["type"]], r["domainSeparator"], int(r["witnessSetVersion"]), int(k) if _DEC.fullmatch(k) else 0, k)


def seal(doc):
    doc["evidenceSha256"] = evidence_sha256(doc)
    return doc


def evidence_sha256(doc) -> str:
    return hashlib.sha256(canonical_json({k: v for k, v in doc.items() if k != "evidenceSha256"}).encode("ascii")).hexdigest()


def _fault(f, what):
    _closed(f, ["reason", "previous", "observed"], what + " members")
    _obs(f["previous"], what + ".previous")
    _obs(f["observed"], what + ".observed")
    p, o = f["previous"], f["observed"]
    if p["chainId"] != o["chainId"]:
        _fail(what + ": previous and observed are of different chains (fault)")
    ok = {"number-regression": int(o["blockNumber"]) < int(p["blockNumber"]), "timestamp-regression": int(o["timestamp"]) < int(p["timestamp"]),
          "hash-changed": o["blockNumber"] == p["blockNumber"] and o["blockHash"] != p["blockHash"]}.get(f["reason"])
    if ok is not True:
        _fail(f"{what}: reason {f['reason']!r} is unknown or not consistent with the observations (fault)")


def validate_evidence(doc):
    _closed(doc, MEMBERS, "evidence members")
    if doc["schemaVersion"] != "hmbc-witness-evidence/v2":
        _fail("schemaVersion must be hmbc-witness-evidence/v2")
    _owner(doc["owner"], witness_only=True)
    b = _closed(doc["binding"], ["binding_v2", "document"], "binding members")
    try:
        d50.validate(b["document"])
    except ValueError as e:
        _fail("binding.document: " + str(e))
    if b["binding_v2"] != d50.binding_v2(b["document"]):
        _fail("binding.binding_v2 is not the D50 hash of binding.document")
    m = _closed(doc["marker"], ["binding_v2", "owner", "schema"], "marker members")
    if m["binding_v2"] != b["binding_v2"] or m["owner"] != doc["owner"] or m["schema"] != "2":
        _fail("marker must equal the binding, the owner and schema 2")
    chains = {side: b["document"]["chains"][side]["chainId"] for side in ("pbc", "dbc")}
    # observations: the last observation per chain
    obs_list = doc["observations"]
    if not isinstance(obs_list, list):
        _fail("observations: not a list")
    for i, o in enumerate(obs_list):
        _obs(o, f"observations[{i}]")
    ids = [int(o["chainId"]) for o in obs_list]
    if ids != sorted(set(ids)) or not set(map(str, ids)) <= set(chains.values()):
        _fail("observations: one per chain, ascending chainId, chains of the binding only")
    last = {o["chainId"]: o for o in obs_list}
    # records
    conflicts, superseded = doc["conflicts"], doc["superseded"]
    if not isinstance(conflicts, list) or not isinstance(superseded, list):
        _fail("conflicts and superseded must be lists")
    needed = {chains[TARGET[r["type"]]] for r in conflicts + superseded if isinstance(r, dict) and r.get("type") in TYPES}
    if not needed <= set(last):
        _fail("observations: missing the last observation of a target chain of a recorded type")
    seen_k, seen_dig = {}, set()
    for i, r in enumerate(conflicts):
        k = _record(r, f"conflicts[{i}]")
        if i and _sort_key(conflicts[i - 1]) > _sort_key(r):
            _fail("conflicts: not sorted by (type order, domainSeparator, witnessSetVersion, key)")
        if k in seen_k:
            _fail("conflicts: duplicate K (type, domainSeparator, witnessSetVersion, keyField)")
        seen_k[k] = r
        for d in r["digests"]:
            if d["digest"] in seen_dig:
                _fail("digest occurs more than once in the store")
            seen_dig.add(d["digest"])
    for i, s in enumerate(superseded):
        k = _record(s, f"superseded[{i}]", ["seq", "death"])
        if s["seq"] != str(i + 1):
            _fail(f"superseded[{i}].seq must be {i + 1} (rows are numbered 1..n in append order)")
        for d in s["digests"]:
            if d["digest"] in seen_dig:
                _fail("digest occurs more than once in the store")
            seen_dig.add(d["digest"])
        live = seen_k.get(k)
        if live is not None and live["vHash"] == s["vHash"]:
            _fail(f"superseded[{i}]: not a supersession, its effect equals the live effect for the same K")
        dth = s["death"]
        if not isinstance(dth, dict) or dth.get("kind") not in DEATH or s["type"] not in DEATH[dth["kind"]][0]:
            _fail(f"superseded[{i}].death.kind is unknown or does not apply to {s['type']}")
        has_obs = DEATH[dth["kind"]][1]
        _closed(dth, ["kind", "observation"] + (["observed"] if has_obs else []), f"superseded[{i}].death members (observed is present exactly for the numeric kinds)")
        _obs(dth["observation"], f"superseded[{i}].death.observation")
        if dth["observation"]["chainId"] != chains[TARGET[s["type"]]]:
            _fail(f"superseded[{i}].death observation chain is not the target ledger of its type")
        if has_obs:
            _rx(_DEC, dth["observed"], f"superseded[{i}].death.observed")
        if dth["kind"] == "expiry" and int(dth["observation"]["timestamp"]) < max(int(d["expiresAt"]) for d in s["digests"]):
            _fail(f"superseded[{i}]: death by expiry needs observation.timestamp >= the latest expiresAt of every digest")
        if dth["kind"] in ("overtaken-checkpoint", "overtaken-governance") and int(dth["observed"]) < int(s["keyField"]):
            _fail(f"superseded[{i}]: overtaken needs observed >= the key")
        if dth["kind"] == "overtaken-decision-sequence" and int(dth["observed"]) <= int(s["effect"]["stateSequence"]):
            _fail(f"superseded[{i}]: overtaken needs observed > effect.stateSequence")
    for r in conflicts:     # every digest observation is of the target ledger of its type
        for d in r["digests"]:
            if d["observation"]["chainId"] != chains[TARGET[r["type"]]]:
                _fail("digest observation chain is not the target ledger of its type")
    for s in superseded:
        for d in s["digests"]:
            if d["observation"]["chainId"] != chains[TARGET[s["type"]]]:
                _fail("digest observation chain is not the target ledger of its type")
    # fault state
    if doc["faulted"] is not None:
        _fault(doc["faulted"], "faulted")
        if doc["faulted"]["previous"] != last.get(doc["faulted"]["previous"]["chainId"]):
            _fail("faulted.previous must equal the stored last observation of its chain (fault)")
    log = doc["faultLog"]
    if not isinstance(log, list):
        _fail("faultLog: not a list")
    for i, row in enumerate(log):
        _closed(row, ["seq", "fault", "clearedAgainst", "note"], f"faultLog[{i}] members")
        if row["seq"] != str(i + 1):
            _fail(f"faultLog[{i}].seq must be {i + 1}")
        _fault(row["fault"], f"faultLog[{i}].fault")
        _obs(row["clearedAgainst"], f"faultLog[{i}].clearedAgainst")
        if not isinstance(row["note"], str) or not row["note"]:
            _fail(f"faultLog[{i}].note must be a non-empty string")
        c, lc = row["clearedAgainst"], last.get(row["clearedAgainst"]["chainId"])
        if c["chainId"] != row["fault"]["observed"]["chainId"] or lc is None or int(c["blockNumber"]) > int(lc["blockNumber"]) or int(c["timestamp"]) > int(lc["timestamp"]):
            _fail(f"faultLog[{i}].clearedAgainst is not a baseline of the faulted chain at or before the stored last observation")
    # monotonicity of every recorded observation, unless the store records a fault or a clear (then explicitly outside the safe-ledger assumption)
    if doc["faulted"] is None and not log:
        recorded = [d["observation"] for r in conflicts + superseded for d in r["digests"]] + [s["death"]["observation"] for s in superseded]
        for o in recorded:
            lo = last[o["chainId"]]
            if int(o["blockNumber"]) > int(lo["blockNumber"]) or int(o["timestamp"]) > int(lo["timestamp"]) or (o["blockNumber"] == lo["blockNumber"] and o["blockHash"] != lo["blockHash"]):
                _fail("a recorded observation exceeds the stored last observation or disagrees with its hash (monotonicity)")
    _rx(_SHA, doc["evidenceSha256"], "evidenceSha256")
    if doc["evidenceSha256"] != evidence_sha256(doc):
        _fail("evidenceSha256 is not the sha256 of the canonical JSON of the document without that member")


# ---- synthetic store history (deterministic) -----------------------------------------------------------------------------------------
def _h(label):
    return "0x" + hashlib.sha256(("hmbc-export-layouts-vector:" + label).encode()).hexdigest()


def _a(label):
    return "0x" + hashlib.sha256(("hmbc-export-layouts-vector:" + label).encode()).hexdigest()[:40]


def _sig(label):
    return "0x" + (hashlib.sha256(("sig:" + label).encode()).hexdigest() * 3)[:130]


def synthetic_evidence(variant="history") -> dict:
    B = d50.synthetic_binding_document("repaired-f")
    bind = d50.binding_v2(B)
    owner = "witness:" + _a("witness-1")
    dbc, pbc = B["chains"]["dbc"]["chainId"], B["chains"]["pbc"]["chainId"]

    def obs(chain, number, ts):
        return {"chainId": chain, "blockNumber": str(number), "blockHash": _h(f"block:{chain}:{number}"), "timestamp": str(ts)}

    def dig(label, o, e=None):
        d = {"digest": _h("digest:" + label), "signature": _sig(label), "observation": o}
        if e is not None:
            d["expiresAt"] = str(e)
        return d

    def rec(t, dom, key, effect, digests, **extra):
        r = {"type": t, "domainSeparator": _h("domain:" + dom), "witnessSetVersion": "2", "keyField": key, "effect": effect,
             "vHash": hashlib.sha256(canonical_json(effect).encode("ascii")).hexdigest(), "digests": digests}
        r.update(extra)
        return r

    def cp(block):
        return {"authEpoch": "3", "policyVersion": "1", "keyEpoch": "0", "witnessSetVersion": "2", "sourceChainId": pbc, "psc": _a("psc"),
                "sourceBlockNumber": str(block), "sourceBlockHash": _h(f"block:{pbc}:{block}")}

    def ad(seq):
        return {"result": "1", "credentialDigest": _h("credentials"), "stateSequence": str(seq), "witnessSetVersion": "2", "sourceBlockNumber": "158", "sourceBlockHash": _h(f"block:{dbc}:158")}

    last = {pbc: obs(pbc, 140, 1791521590), dbc: obs(dbc, 160, 1791521600)}
    req1, req2 = _h("request:1"), _h("request:2")
    conflicts = [
        rec("AccessDecision", "HMBCDecision", req1, ad(6), [dig("decision-2", obs(dbc, 158, 1791521570), 1791521620)]),
        rec("StateCheckpoint", "HMBCState", "4", cp(138), [dig("checkpoint-4-a", obs(dbc, 159, 1791521590), 1791521610), dig("checkpoint-4-b", obs(dbc, 160, 1791521600), 1791521640)]),
        rec("GrantReceipt", "HMBCReceipt", req2, {"grantId": _h("grant"), "gid": _a("gid"), "dataId": _h("data"), "keyEpoch": "0", "grantExpiresAt": "1791521700", "witnessSetVersion": "2",
                                                  "dbcChainId": dbc, "kssc": _a("kssc"), "dbcBlockNumber": "159", "dbcBlockHash": _h(f"block:{dbc}:159")},
            [dig("receipt", obs(pbc, 139, 1791521585))]),
        rec("GovernanceAction", "HMBCGovernance", "3", {"action": "1", "root": _a("root"), "admins": sorted([_a("admin-1"), _a("admin-2")]), "witnessSetVersion": "2"},
            [dig("governance-3", obs(pbc, 140, 1791521590), 1791521650)]),
    ]
    for c in conflicts:
        c["digests"].sort(key=lambda d: (int(d.get("expiresAt", -1)), d["digest"]))
    superseded = [
        rec("StateCheckpoint", "HMBCState", "4", cp(136), [dig("checkpoint-4-old", obs(dbc, 153, 1791521520), 1791521540)], seq="1",
            death={"kind": "expiry", "observation": obs(dbc, 157, 1791521545)}),
        rec("AccessDecision", "HMBCDecision", req1, ad(5), [dig("decision-1", obs(dbc, 154, 1791521530), 1791521560)], seq="2",
            death={"kind": "overtaken-decision-sequence", "observation": obs(dbc, 158, 1791521570), "observed": "6"}),
    ]
    doc = {"schemaVersion": "hmbc-witness-evidence/v2", "owner": owner, "binding": {"binding_v2": bind, "document": B}, "marker": {"binding_v2": bind, "owner": owner, "schema": "2"},
           "observations": [last[pbc], last[dbc]] if int(pbc) < int(dbc) else [last[dbc], last[pbc]], "faulted": None, "faultLog": [], "conflicts": conflicts, "superseded": superseded}
    fault = {"reason": "number-regression", "previous": last[dbc], "observed": obs(dbc, 158, 1791521600)}
    if variant == "faulted":
        doc["faulted"] = fault
    elif variant == "cleared":
        base = obs(dbc, 158, 1791521605)
        doc["faultLog"] = [{"seq": "1", "fault": fault, "clearedAgainst": base, "note": "operator clear after a test restart of the DBC"}]
        doc["observations"] = [dict(base) if o["chainId"] == dbc else o for o in doc["observations"]]       # a copy: no shared object between the two members
    elif variant != "history":
        raise ValueError(variant)
    return seal(doc)


def emit() -> dict:
    be, bf = d50.synthetic_binding_document("repaired-e"), d50.synthetic_binding_document("repaired-f")
    anchor = {"pbc": {"number": "141", "hash": _h("anchor:pbc")}, "dbc": {"number": "161", "hash": _h("anchor:dbc")}}
    out = {"schema": "hmbc-export-layouts-vector/v1", "status": "SPECIFICATION VECTOR; digests and signatures are well-formed PLACEHOLDERS, not recovered signatures; not a measurement",
           "outputContract": {"stdoutOnSuccess": "one line: canonical JSON (sorted keys, compact separators, ensure_ascii) followed by exactly one LF; stderr empty; exit 0",
                              "stderrOnRefusal": "one line: canonical JSON {code, message, reason} followed by one LF; stdout empty; exit 3", "usage": "exit 2 (argparse)"},
           "bindingExports": {"worker-repaired-e": binding_export("worker", be, anchor), "witness-repaired-f": binding_export("witness:" + _a("witness-1"), bf, anchor)},
           "evidence": {v: synthetic_evidence(v) for v in ("history", "faulted", "cleared")},
           "refusalLines": {r: error_line(r, "illustrative message") for r in sorted(ERROR_REASONS)}}
    out["lines"] = {"bindingExports": {k: render(v) for k, v in out["bindingExports"].items()}}
    for v in out["bindingExports"].values():
        validate_binding_export(v)
    for v in out["evidence"].values():
        validate_evidence(v)
    return out


if __name__ == "__main__":
    if "--emit" in sys.argv[1:]:
        print(json.dumps(emit(), indent=1, sort_keys=True))
    else:
        print(__doc__)
