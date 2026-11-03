"""D50 reference: closed-shape binding document, canonical encoding, hash, and the strict masked-build check (agent 2, F0 revision 3).

SPECIFICATION VECTOR GENERATOR, NOT PRODUCTION CODE and NOT a measurement. Live-derived fields in the synthetic documents (genesis/deploy-block hashes,
live code hashes, witness addresses, wiring, Governance data) are PLACEHOLDERS built from labels; only the six E ABI/runtime hashes and lengths come from
`protocol/tests/fixtures/deployment-agent1-91add8c-v1-repaired-e.json`. Standard library only.

    python3 -I d50_reference.py --emit > d50_binding_vector.json
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

PREFIX = b"hmbc-deployment-binding/v2\n"
PROFILES = {"paper-strict", "paper-minimal", "repaired-e", "repaired-f"}
PBC_E, DBC_E = ("LSC", "TMSC", "RSC", "PSC"), ("ACSC", "KSSC")

_DEC = re.compile(r"(0|[1-9][0-9]*)")
_ADDR = re.compile(r"0x[0-9a-f]{40}")
_SHA = re.compile(r"[0-9a-f]{64}")
_BHASH = re.compile(r"0x[0-9a-f]{64}")
_HEXCODE = re.compile(r"0x(?:[0-9a-f]{2})*")
_IFACE = re.compile(r"v[0-9]+")
IMMUTABLE_SLOT_BYTES = 32      # agent 1's export rule (A1-0096 design 2.2 section 8): every immutable reference is exactly one 32-byte slot


def _dec(v, what, bits=256):
    if not isinstance(v, str) or not _DEC.fullmatch(v) or int(v) >= 1 << bits:
        raise ValueError(f"{what}: expected a decimal string below 2^{bits}")
    return int(v)


def _match(rx, v, what):
    if not isinstance(v, str) or not rx.fullmatch(v):
        raise ValueError(f"{what}: bad format")
    return v


def _closed(obj, required, optional, what):
    if not isinstance(obj, dict):
        raise ValueError(f"{what}: expected an object")
    keys = set(obj)
    if not set(required) <= keys or not keys <= set(required) | set(optional):
        raise ValueError(f"{what}: keys {sorted(keys)} do not match required {sorted(required)} optional {sorted(optional)}")
    return obj


def canonical_json(doc) -> str:
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def validate(doc) -> bool:
    """Validate the closed shape of B. Returns True when it is a repaired-f document (Governance present)."""
    d = _closed(doc, ["interfaceVersion", "profile", "chains", "immutables", "witnessSets", "wiring"], [], "B")
    _match(_IFACE, d["interfaceVersion"], "interfaceVersion")
    p = _closed(d["profile"], ["name", "enum"], [], "profile")
    if p["name"] not in PROFILES:
        raise ValueError("profile.name")
    if _dec(p["enum"], "profile.enum", 8) > 3:
        raise ValueError("profile.enum")
    f = p["name"] == "repaired-f"
    sides = _closed(d["chains"], ["pbc", "dbc"], [], "chains")
    want = {"pbc": PBC_E + (("Governance",) if f else ()), "dbc": DBC_E}
    pins = []
    for side in ("pbc", "dbc"):
        c = _closed(sides[side], ["chainId", "genesisHash", "deployBlock", "contracts"], [], f"chains.{side}")
        _dec(c["chainId"], "chainId")
        _match(_BHASH, c["genesisHash"], "genesisHash")
        b = _closed(c["deployBlock"], ["number", "hash"], [], "deployBlock")
        _dec(b["number"], "deployBlock.number", 64)
        _match(_BHASH, b["hash"], "deployBlock.hash")
        cs = _closed(c["contracts"], list(want[side]), [], f"contracts.{side}")
        for name, row in cs.items():
            r = _closed(row, ["address", "codeSha256", "abiSha256", "runtimeSha256", "runtimeBytes"], ["immutableRefsSha256"], name)
            _match(_ADDR, r["address"], name + ".address")
            for k in ("codeSha256", "abiSha256", "runtimeSha256"):
                _match(_SHA, r[k], f"{name}.{k}")
            _dec(r["runtimeBytes"], name + ".runtimeBytes", 32)
            pins.append("immutableRefsSha256" in r)
            if "immutableRefsSha256" in r:
                _match(_SHA, r["immutableRefsSha256"], name + ".immutableRefsSha256")
    if any(pins) and not all(pins):
        raise ValueError("immutableRefsSha256 must be present on every contract or on none")
    imm_names = ("TMSC", "PSC", "KSSC", "ACSC") + (("Governance",) if f else ())
    im = _closed(d["immutables"], list(imm_names), [], "immutables")
    for n, row in im.items():
        if n == "Governance":
            _dec(_closed(row, ["mutations"], [], n)["mutations"], n + ".mutations")
        else:
            r = _closed(row, ["profile", "mutations"], [], n)
            _dec(r["profile"], n + ".profile", 8)
            _dec(r["mutations"], n + ".mutations")
    ws = _closed(d["witnessSets"], ["psc", "kssc"] + (["governance"] if f else []), [], "witnessSets")
    for n, row in ws.items():
        r = _closed(row, ["version", "threshold", "witnesses"], [], n)
        _dec(r["version"], n + ".version", 64)
        _dec(r["threshold"], n + ".threshold")
        if not isinstance(r["witnesses"], list) or not r["witnesses"]:
            raise ValueError(n + ".witnesses")
        for a in r["witnesses"]:
            _match(_ADDR, a, n + ".witnesses[]")
    w = _closed(d["wiring"], ["ksscForChain", "acsc", "kssc", "pscRelay", "tmsc", "lsc"], ["governance"] if f else [], "wiring")
    for k in ("ksscForChain", "acsc", "kssc", "pscRelay"):
        _match(_ADDR, w[k], "wiring." + k)
    for k, sub in (("tmsc", ["psc", "rsc"]), ("lsc", ["rsc", "tmsc", "psc"])):
        for s, v in _closed(w[k], sub, [], "wiring." + k).items():
            _match(_ADDR, v, f"wiring.{k}.{s}")
    if f:
        if "governance" not in w:
            raise ValueError("repaired-f needs wiring.governance")
        for s, v in _closed(w["governance"], ["tmsc", "target"], [], "wiring.governance").items():
            _match(_ADDR, v, "wiring.governance." + s)
    return f


def binding_v2(doc) -> str:
    validate(doc)
    return hashlib.sha256(PREFIX + canonical_json(doc).encode("ascii")).hexdigest()


# ---- masked build check -------------------------------------------------------------------------------------------------------
def _ranges(ranges, n):
    if not isinstance(ranges, list):
        raise ValueError("ranges must be a list")
    out, prev_end = [], 0
    for i, r in enumerate(ranges):
        if not isinstance(r, list) or len(r) != 2:
            raise ValueError(f"range {i}: expected [start, length]")
        start, length = _dec(r[0], f"range {i}.start", 32), _dec(r[1], f"range {i}.length", 32)
        if length == 0:
            raise ValueError(f"range {i}: zero length")
        if length != IMMUTABLE_SLOT_BYTES:
            raise ValueError(f"range {i}: length must be {IMMUTABLE_SLOT_BYTES}, got {length}")
        if start < prev_end:
            raise ValueError(f"range {i}: unsorted or overlapping (start {start} < previous end {prev_end})")
        if start + length > n:
            raise ValueError(f"range {i}: ends at {start + length}, past the {n}-byte runtime")
        out.append((start, length))
        prev_end = start + length
    return out


def masked_runtime_sha256(code_hex, ranges, runtime_bytes) -> str:
    """sha256 of the live runtime with every pinned immutable range zeroed. `ranges` and `runtime_bytes` are TRUSTED build pins, never RPC data.

    The output is built by concatenating segments, never by slice assignment: assigning to an out-of-bounds slice of a bytearray silently
    extends or truncates it, which would hide a malformed range."""
    _match(_HEXCODE, code_hex, "code")
    n = _dec(runtime_bytes, "runtimeBytes", 32)
    code = bytes.fromhex(code_hex[2:])
    if len(code) != n:
        raise ValueError(f"live runtime is {len(code)} bytes, the pin says {n}")
    parts, pos = [], 0
    for start, length in _ranges(ranges, n):
        parts += [code[pos:start], bytes(length)]
        pos = start + length
    parts.append(code[pos:])
    out = b"".join(parts)
    if len(out) != n:
        raise ValueError("internal: masked length differs from the pin")
    return hashlib.sha256(out).hexdigest()


# ---- synthetic documents ------------------------------------------------------------------------------------------------------
def _syn(label, hexlen=64):
    return hashlib.sha256(b"synthetic:" + label.encode()).hexdigest()[:hexlen]


def _addr(label):
    return "0x" + _syn("addr:" + label, 40)


def synthetic_binding_document(profile: str, fixture_path: str | None = None) -> dict:
    fixture_path = fixture_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tests", "fixtures",
                                                "deployment-agent1-91add8c-v1-repaired-e.json")
    with open(fixture_path, encoding="utf-8") as fh:
        fx = json.load(fh)
    f = profile == "repaired-f"
    enum = {"paper-strict": "0", "paper-minimal": "1", "repaired-e": "2", "repaired-f": "3"}[profile]
    witnesses = [_addr(f"witness-{i}") for i in range(1, 5)] if f else [fx["fixture"]["witnessSet"]["witnesses"][0]]
    wset = {"version": "2" if f else "1", "threshold": "3" if f else "1", "witnesses": witnesses}
    doc = {"interfaceVersion": "v1", "profile": {"name": profile, "enum": enum}, "chains": {}, "immutables": {},
           "witnessSets": {"psc": dict(wset), "kssc": dict(wset)}, "wiring": {}}
    for side, names in (("pbc", PBC_E + (("Governance",) if f else ())), ("dbc", DBC_E)):
        ch = fx["chains"][side]
        contracts = {}
        for n in names:
            if n == "Governance":
                row = {"address": _addr("Governance"), "codeSha256": _syn("code:Governance"), "abiSha256": _syn("abi:Governance"),
                       "runtimeSha256": _syn("runtime:Governance"), "runtimeBytes": "9001"}
            else:
                a = fx["abi"][n]
                row = {"address": ch["contracts"][n], "codeSha256": _syn("code:" + n), "abiSha256": a["abiSha256"],
                       "runtimeSha256": a["runtimeSha256"], "runtimeBytes": str(a["runtimeBytes"])}
            row["immutableRefsSha256"] = _syn("refs:" + n)
            contracts[n] = row
        doc["chains"][side] = {"chainId": ch["chainId"], "genesisHash": "0x" + _syn("genesis:" + side), "contracts": contracts,
                               "deployBlock": {"number": str(ch["deployBlock"]), "hash": "0x" + _syn("deployblock:" + side)}}
    for n in ("TMSC", "PSC", "KSSC", "ACSC"):
        doc["immutables"][n] = {"profile": enum, "mutations": "0"}
    pbc, dbc = doc["chains"]["pbc"]["contracts"], doc["chains"]["dbc"]["contracts"]
    doc["wiring"] = {"ksscForChain": dbc["KSSC"]["address"], "acsc": dbc["ACSC"]["address"], "kssc": dbc["KSSC"]["address"],
                     "pscRelay": fx["fixture"]["relay"]["address"],
                     "tmsc": {"psc": pbc["PSC"]["address"], "rsc": pbc["RSC"]["address"]},
                     "lsc": {"rsc": pbc["RSC"]["address"], "tmsc": pbc["TMSC"]["address"], "psc": pbc["PSC"]["address"]}}
    if f:
        doc["immutables"]["Governance"] = {"mutations": "0"}
        doc["witnessSets"]["governance"] = dict(wset)
        doc["wiring"]["governance"] = {"tmsc": pbc["Governance"]["address"], "target": pbc["TMSC"]["address"]}
    validate(doc)
    return doc


def emit() -> dict:
    out = {"schema": "hmbc-d50-binding-vector/v1", "status": "SPECIFICATION VECTOR; live-derived fields are SYNTHETIC placeholders, not measurements",
           "prefix": PREFIX.decode(), "encoding": "json.dumps(B, sort_keys=True, separators=(',',':'), ensure_ascii=True); binding_v2 = lowercase sha256 hex of prefix || canonical json",
           "documents": {}}
    for p in ("repaired-e", "repaired-f"):
        doc = synthetic_binding_document(p)
        out["documents"][p] = {"document": doc, "canonicalJson": canonical_json(doc), "bindingV2": binding_v2(doc)}
    code = bytes(range(128))
    live = bytearray(code)
    live[8:40] = b"\xaa" * 32
    live[64:96] = b"\xbb" * 32
    ranges = [["8", "32"], ["64", "32"]]
    out["maskedBuild"] = {"liveRuntimeHex": "0x" + live.hex(), "ranges": ranges, "runtimeBytes": "128",
                          "maskedSha256": masked_runtime_sha256("0x" + live.hex(), ranges, "128"),
                          "rule": "ranges and runtimeBytes are TRUSTED build pins; refuse unsorted, overlapping, zero-length, length != 32 (A1-0096), out-of-bounds or non-decimal ranges, a live length different from runtimeBytes, and non-canonical hex",
                          "limit": "checks the runtime outside the immutable slots only; it is NOT constructor or source attestation"}
    return out


if __name__ == "__main__":
    if "--emit" in sys.argv[1:]:
        print(json.dumps(emit(), indent=1, sort_keys=True))
    else:
        print(__doc__)
