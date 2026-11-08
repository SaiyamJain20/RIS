"""D50 live-read reconstruction at open (HMBC2020 successor, F task 2 slice 5a): the startup read schedule S0 and the open-time checks, stages 1 to 8.

PAPER-DERIVED RECONSTRUCTION of D50-DEPLOYMENT-BINDING.md sections 2 to 4 and the precedence of SUCCESSOR-WIRE.md section 1. `reconstruct` reads EVERY value of the binding document B through an INJECTED chain
view (all reads after the anchor pinned to ONE block per chain), compares the manifest-asserted values, and returns B, its `binding_v2`, the anchor and whether the build check could run, or refuses with the
reason of the FIRST failing stage. It touches no store (stage 9, the store itself, is `witness_state.open_store`); `open_witness_store` composes the two. No clock, no network, no randomness: the view is the
only source of facts, and the module counts nothing but what it asks.

The chain view (every method is ONE request; the totals are D50 section 3: 48 for an E deployment, 55 for F):
  chain_id(chain) -> str; latest(chain) -> {"number", "hash"}; block(chain, number) -> {"number", "hash"} or None;
  code(chain, address, at) -> "0x..." hex; call(chain, address, function, args, at) -> a str, a bool or a list of str.
Functions read: profile, mutations (TMSC, PSC, KSSC, ACSC; Governance: mutations only), witnesses/threshold/witnessSetVersion (PSC, KSSC, Governance), configured (LSC, TMSC, RSC, PSC, ACSC, KSSC), and the
wiring views of D50 section 2 plus the five immutable cross-checks. A view that cannot answer raises `LedgerUnreachable` (stage 1).

Stages, first failing wins (SUCCESSOR-WIRE section 1): 1 LEDGER_UNREACHABLE; 2 PROFILE_MISMATCH; 3 BUILD_PIN_INVALID; 4 UNSEALED; 5 WIRING_MISMATCH; 6 GENESIS_MISMATCH; 7 CODE_MISMATCH, then
MUTATIONS_MISMATCH, then BUILD_MISMATCH; 8 WITNESS_SET_MISMATCH, then UNKNOWN_AUTHORITY (witness role only).

Explicit choices where D50 does not say (recorded, not discovered): a chain id that differs from the manifest's, or a genesis or deploy block the chain does not have (or a deploy block after the anchor), is
GENESIS_MISMATCH; an `immutableRefsSha256` that is not the hash of the pinned object list, a malformed range, or a missing pin under repaired-f (or on only some E contracts) is BUILD_PIN_INVALID; live code that is
not canonical lowercase hex of exactly `runtimeBytes` bytes is BUILD_MISMATCH even when no pins exist, but the MASKED hash is compared only with pins (otherwise `buildChecked` is False and the limit is reported, not
hidden); the F witness set must hold 4 witnesses with threshold 2 or 3 (SUCCESSOR-WIRE section 2) and every live set must equal the manifest's in order; a manifest that is not shaped like a deployment is a
ValueError, outside the reason table.
"""
from __future__ import annotations

import hashlib
import re

from . import binding as bd
from . import witness_state as ws

OPEN_REASON_CODE = {"LEDGER_UNREACHABLE": "ADAPTER_UNAVAILABLE", "PROFILE_MISMATCH": "WRONG_PROFILE", "BUILD_PIN_INVALID": "MALFORMED", "UNSEALED": "WRONG_DESTINATION",
                    "WIRING_MISMATCH": "WRONG_DESTINATION", "GENESIS_MISMATCH": "WRONG_DESTINATION", "CODE_MISMATCH": "WRONG_DESTINATION", "MUTATIONS_MISMATCH": "WRONG_DESTINATION",
                    "BUILD_MISMATCH": "WRONG_DESTINATION", "WITNESS_SET_MISMATCH": "STALE_STATE", "UNKNOWN_AUTHORITY": "UNKNOWN_AUTHORITY"}
_ADDR = re.compile(r"0x[0-9a-f]{40}")
_SHA = re.compile(r"[0-9a-f]{64}")
_DEC = re.compile(r"(0|[1-9][0-9]*)")
BOOTSTRAPPED = ("LSC", "TMSC", "RSC", "PSC", "ACSC", "KSSC")
HOLDERS = bd.MASK_HOLDERS_E


class LedgerUnreachable(Exception):
    """The chain view could not answer a request (stage 1)."""


def _refuse(reason, message):
    raise bd.OpenRefusal(reason, message)


def _bad(what):
    raise ValueError(f"manifest unusable: {what}")


def _dec(v, what):
    if not isinstance(v, str) or _DEC.fullmatch(v) is None:
        _bad(what + " must be a canonical decimal string")
    return v


def _addr(v, what):
    if not isinstance(v, str) or _ADDR.fullmatch(v) is None:
        _bad(what + " must be a lowercase 0x address")
    return v


def read_manifest(m):
    """The pins and assertions the open needs, with shape checked (ValueError outside the reason table). The profile name, enum and mutations are NOT judged here (stage 2 and 7); the pins' consistency is not
    judged here either (stage 3). Returns a plain dict."""
    if not isinstance(m, dict):
        _bad("not an object")
    for k in ("interfaceVersion", "profile"):
        if not isinstance(m.get(k), str):
            _bad(k + " must be a string")
    enum, mutations = _dec(m.get("profileEnum"), "profileEnum"), _dec(m.get("mutations"), "mutations")
    family = "F" if m["profile"] == "repaired-f" else "E"
    want = {"pbc": bd.PBC_E + (("Governance",) if family == "F" else ()), "dbc": bd.DBC_E}
    chains = {}
    try:
        for side in ("pbc", "dbc"):
            c = m["chains"][side]
            contracts = c["contracts"]
            if not isinstance(contracts, dict) or set(contracts) != set(want[side]):
                _bad(f"chains.{side}.contracts must be exactly {sorted(want[side])} for this profile")
            chains[side] = {"chainId": _dec(c["chainId"], "chainId"), "deployBlock": _dec(c["deployBlock"], "deployBlock"), "contracts": {n: _addr(a, n) for n, a in contracts.items()}}
        abi = {}
        for n in want["pbc"] + want["dbc"]:
            a = m["abi"][n]
            if not isinstance(a, dict):
                _bad(f"abi.{n} must be an object")
            for k in ("abiSha256", "runtimeSha256"):
                if not isinstance(a[k], str) or _SHA.fullmatch(a[k]) is None:
                    _bad(f"abi.{n}.{k} must be a lowercase sha256")
            abi[n] = {"abiSha256": a["abiSha256"], "runtimeSha256": a["runtimeSha256"], "runtimeBytes": _dec(a["runtimeBytes"], f"abi.{n}.runtimeBytes"),
                      "refs": a.get("immutableReferences"), "refsSha256": a.get("immutableRefsSha256")}
        w = m["fixture"]["witnessSet"]
        wset = {"version": _dec(w["version"], "witnessSet.version"), "threshold": _dec(w["threshold"], "witnessSet.threshold"), "witnesses": w["witnesses"]}
        if not isinstance(wset["witnesses"], list) or not all(isinstance(a, str) and _ADDR.fullmatch(a) for a in wset["witnesses"]):
            _bad("witnessSet.witnesses must be a list of lowercase addresses")
        relay = _addr(m["fixture"]["relay"]["address"], "relay.address")
    except (KeyError, TypeError):
        _bad("a required member is missing or mistyped")
    return {"family": family, "interfaceVersion": m["interfaceVersion"], "profile": m["profile"], "enum": enum, "mutations": mutations, "chains": chains, "abi": abi, "relay": relay, "witnessSet": wset}


def _names(p):
    return {"pbc": bd.PBC_E + (("Governance",) if p["family"] == "F" else ()), "dbc": bd.DBC_E}


def _side_of(p, name):
    return "pbc" if name in _names(p)["pbc"] else "dbc"


def _read_all(view, p):
    """Stage 1: every read, in a fixed order. Returns the raw facts; raises OpenRefusal(LEDGER_UNREACHABLE)."""
    names, ch = _names(p), p["chains"]
    R = {"anchor": {}, "chain": {}, "genesis": {}, "deploy": {}, "code": {}, "profile": {}, "mutations": {}, "sets": {}, "wiring": {}, "cross": {}, "configured": {}}
    try:
        for side in ("pbc", "dbc"):
            R["chain"][side] = view.chain_id(side)
            R["anchor"][side] = view.latest(side)
            R["genesis"][side] = view.block(side, 0)
            R["deploy"][side] = view.block(side, int(ch[side]["deployBlock"]))
        at = {s: int(R["anchor"][s]["number"]) for s in ("pbc", "dbc")}
        addr = lambda n: ch[_side_of(p, n)]["contracts"][n]  # noqa: E731

        def call(n, fn, args=()):
            s = _side_of(p, n)
            return view.call(s, addr(n), fn, list(args), at[s])

        for n in names["pbc"] + names["dbc"]:
            s = _side_of(p, n)
            R["code"][n] = view.code(s, addr(n), at[s])
        for n in HOLDERS:
            R["profile"][n] = call(n, "profile")
        for n in HOLDERS + (("Governance",) if p["family"] == "F" else ()):
            R["mutations"][n] = call(n, "mutations")
        for n in ("PSC", "KSSC") + (("Governance",) if p["family"] == "F" else ()):
            R["sets"][n] = {"witnesses": call(n, "witnesses"), "threshold": call(n, "threshold"), "version": call(n, "witnessSetVersion")}
        w = R["wiring"]
        w["ksscForChain"] = call("PSC", "ksscForChain", [ch["dbc"]["chainId"]])
        w["acsc"], w["kssc"], w["pscRelay"] = call("KSSC", "acsc"), call("ACSC", "kssc"), call("ACSC", "pscRelay")
        w["tmsc"] = {"psc": call("TMSC", "psc"), "rsc": call("TMSC", "rsc")}
        w["lsc"] = {"rsc": call("LSC", "rsc"), "tmsc": call("LSC", "tmsc"), "psc": call("LSC", "psc")}
        if p["family"] == "F":
            w["governance"] = {"tmsc": call("TMSC", "governance"), "target": call("Governance", "target")}
        R["cross"] = {"PSC": {"rsc": call("PSC", "rsc"), "tmsc": call("PSC", "tmsc"), "lsc": call("PSC", "lsc")}, "RSC": {"tmsc": call("RSC", "tmsc"), "lsc": call("RSC", "lsc")}}
        for n in BOOTSTRAPPED:
            R["configured"][n] = call(n, "configured")
    except LedgerUnreachable as e:
        _refuse("LEDGER_UNREACHABLE", f"the chain could not be read: {e}")
    return R


def _profile_stage(p, R):
    """Stage 2: the closed table and the live profile() of the four holders. The mutation part is stage 7, so it is fed values that cannot fail."""
    row = bd.PROFILE_TABLE.get(p["profile"])
    ok_mask = str(row[1]) if row is not None and row[1] is not None else "0"
    holders = set(HOLDERS) | ({"Governance"} if row is not None and row[0] == 3 else set())
    result = None
    for n in HOLDERS:
        result = bd.profile_from_manifest(p["profile"], p["enum"], ok_mask, R["profile"][n], {h: ok_mask for h in holders})
    return result


def _pins_stage(p):
    """Stage 3: the trusted build pins must be internally consistent. Returns True when every contract carries pins (so the masked check can run), False when none does."""
    pinned = []
    for n, a in p["abi"].items():
        has_refs, has_sha = a["refs"] is not None, a["refsSha256"] is not None
        if has_refs != has_sha:
            _refuse("BUILD_PIN_INVALID", f"{n}: immutableReferences and immutableRefsSha256 must come together")
        pinned.append(has_refs)
        if has_refs:
            try:
                bd.immutable_refs_canonical_json(a["refs"], a["runtimeBytes"])
                good = bd.immutable_refs_sha256(a["refs"], a["runtimeBytes"])
            except (ValueError, TypeError, KeyError):
                _refuse("BUILD_PIN_INVALID", f"{n}: the immutable object list is malformed")
            if good != a["refsSha256"]:
                _refuse("BUILD_PIN_INVALID", f"{n}: immutableRefsSha256 is not the hash of the pinned object list")
    if p["family"] == "F" and not all(pinned):
        _refuse("BUILD_PIN_INVALID", "repaired-f requires the immutable pins on every contract")
    if any(pinned) and not all(pinned):
        _refuse("BUILD_PIN_INVALID", "the immutable pins must be on every contract or on none")
    return all(pinned)


def _sealed_stage(R):
    for n, v in R["configured"].items():
        if v is not True:
            _refuse("UNSEALED", f"{n}.configured() is not true: an unsealed deployment can still be rewired")


def _wiring_stage(p, R):
    A = {n: p["chains"][_side_of(p, n)]["contracts"][n] for n in _names(p)["pbc"] + _names(p)["dbc"]}
    w = R["wiring"]
    want = [("PSC.ksscForChain", w["ksscForChain"], A["KSSC"]), ("KSSC.acsc", w["acsc"], A["ACSC"]), ("ACSC.kssc", w["kssc"], A["KSSC"]), ("ACSC.pscRelay", w["pscRelay"], p["relay"]),
            ("TMSC.psc", w["tmsc"]["psc"], A["PSC"]), ("TMSC.rsc", w["tmsc"]["rsc"], A["RSC"]), ("LSC.rsc", w["lsc"]["rsc"], A["RSC"]), ("LSC.tmsc", w["lsc"]["tmsc"], A["TMSC"]),
            ("LSC.psc", w["lsc"]["psc"], A["PSC"]), ("PSC.rsc", R["cross"]["PSC"]["rsc"], A["RSC"]), ("PSC.tmsc", R["cross"]["PSC"]["tmsc"], A["TMSC"]), ("PSC.lsc", R["cross"]["PSC"]["lsc"], A["LSC"]),
            ("RSC.tmsc", R["cross"]["RSC"]["tmsc"], A["TMSC"]), ("RSC.lsc", R["cross"]["RSC"]["lsc"], A["LSC"])]
    if p["family"] == "F":
        want += [("TMSC.governance", w["governance"]["tmsc"], A["Governance"]), ("Governance.target", w["governance"]["target"], A["TMSC"])]
    for name, live, expected in want:
        if live != expected:
            _refuse("WIRING_MISMATCH", f"{name} differs from the manifest address")


def _genesis_stage(p, R):
    for side in ("pbc", "dbc"):
        if R["chain"][side] != p["chains"][side]["chainId"]:
            _refuse("GENESIS_MISMATCH", f"the {side} chain id differs from the manifest's")
        g, d, a = R["genesis"][side], R["deploy"][side], R["anchor"][side]
        if g is None or d is None or int(p["chains"][side]["deployBlock"]) > int(a["number"]):
            _refuse("GENESIS_MISMATCH", f"the {side} chain does not have its genesis or the manifest's deploy block (a restarted chain)")


def _decode_code(code, runtime_bytes):
    if not isinstance(code, str) or re.fullmatch(r"0x(?:[0-9a-f]{2})*", code) is None or len(code) != 2 + 2 * int(runtime_bytes):
        return None
    return bytes.fromhex(code[2:])


def _code_stage(p, R, pinned):
    for n, code in R["code"].items():
        if not isinstance(code, str) or code in ("", "0x"):
            _refuse("CODE_MISMATCH", f"{n}: no code at the manifest address")
    bd.profile_from_manifest(p["profile"], p["enum"], p["mutations"], R["profile"]["TMSC"], R["mutations"])        # the profile part passed at stage 2: only MUTATIONS_MISMATCH can come from here
    digests = {}
    for n, code in R["code"].items():
        a = p["abi"][n]
        raw = _decode_code(code, a["runtimeBytes"])
        if raw is None:
            _refuse("BUILD_MISMATCH", f"{n}: the live code is not canonical hex of exactly the pinned length")
        digests[n] = hashlib.sha256(raw).hexdigest()
        if pinned:
            try:
                masked = bd.masked_runtime_sha256(code, bd.pairs_from_object_list(a["refs"]), a["runtimeBytes"])
            except ValueError:
                _refuse("BUILD_MISMATCH", f"{n}: the masked live code could not be formed")
            if masked != a["runtimeSha256"]:
                _refuse("BUILD_MISMATCH", f"{n}: the live code outside the immutable slots differs from the compiled build")
    return digests


def _sets_stage(p, R, role, key):
    w = p["witnessSet"]
    if p["family"] == "F" and (len(w["witnesses"]) != 4 or w["threshold"] not in ("2", "3")):
        _refuse("WITNESS_SET_MISMATCH", "an F deployment needs 4 witnesses and a threshold of 2 or 3")
    for n, s in R["sets"].items():
        if s["witnesses"] != w["witnesses"] or s["threshold"] != w["threshold"] or s["version"] != w["version"]:
            _refuse("WITNESS_SET_MISMATCH", f"{n}'s witness set, threshold or version differs from the manifest")
    if role == "witness" and key not in w["witnesses"]:
        _refuse("UNKNOWN_AUTHORITY", "this witness key is not a member of the sets")


def reconstruct(manifest, view, *, role, key_address=None):
    """Stages 1 to 8. Returns {"document", "binding_v2", "anchor", "buildChecked"} or raises OpenRefusal."""
    if role not in ("worker", "witness"):
        raise ValueError("role must be 'worker' or 'witness'")
    if role == "witness" and (not isinstance(key_address, str) or _ADDR.fullmatch(key_address) is None):
        raise ValueError("a witness needs its lowercase key address")
    p = read_manifest(manifest)
    R = _read_all(view, p)
    profile = _profile_stage(p, R)
    pinned = _pins_stage(p)
    _sealed_stage(R)
    _wiring_stage(p, R)
    _genesis_stage(p, R)
    digests = _code_stage(p, R, pinned)
    _sets_stage(p, R, role, key_address)
    names = _names(p)
    chains = {}
    for side in ("pbc", "dbc"):
        contracts = {}
        for n in names[side]:
            a = p["abi"][n]
            row = {"address": p["chains"][side]["contracts"][n], "codeSha256": digests[n], "abiSha256": a["abiSha256"], "runtimeSha256": a["runtimeSha256"], "runtimeBytes": a["runtimeBytes"]}
            if pinned:
                row["immutableRefsSha256"] = a["refsSha256"]
            contracts[n] = row
        chains[side] = {"chainId": p["chains"][side]["chainId"], "genesisHash": R["genesis"][side]["hash"], "deployBlock": {"number": p["chains"][side]["deployBlock"], "hash": R["deploy"][side]["hash"]},
                        "contracts": contracts}
    immutables = {n: {"profile": R["profile"][n], "mutations": R["mutations"][n]} for n in HOLDERS}
    wsets = {("governance" if n == "Governance" else n.lower()): {"version": s["version"], "threshold": s["threshold"], "witnesses": list(s["witnesses"])} for n, s in R["sets"].items()}
    wiring = {k: (dict(v) if isinstance(v, dict) else v) for k, v in R["wiring"].items()}
    if p["family"] == "F":
        immutables["Governance"] = {"mutations": R["mutations"]["Governance"]}
    doc = {"interfaceVersion": p["interfaceVersion"], "profile": profile, "chains": chains, "immutables": immutables, "witnessSets": wsets, "wiring": wiring}
    bd.validate(doc)
    anchor = {s: {"number": R["anchor"][s]["number"], "hash": R["anchor"][s]["hash"]} for s in ("pbc", "dbc")}
    return {"document": doc, "binding_v2": bd.binding_v2(doc), "anchor": anchor, "buildChecked": pinned}


def open_witness_store(manifest, view, state_dir, key_address, *, init=False):
    """Stages 1 to 8, then stage 9 (the store). `init=True` creates (or opens an identical) store; without it a missing store is refused STORE_MISSING and nothing is created."""
    r = reconstruct(manifest, view, role="witness", key_address=key_address)
    owner = "witness:" + key_address
    if init:
        return ws.init_store(state_dir, r["binding_v2"], r["document"], owner, anchor=r["anchor"])
    return ws.open_store(state_dir, r["binding_v2"], owner)
