"""D50 reference: closed-shape binding document, canonical encoding, hash, the strict masked-build check and (revision 5) the manifest-profile table (agent 2, F0 revision 8 of the set).

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
# D50 revision 5 (A2-0054 P-1). The manifest `profile` NAME is validated against this closed table and is NEVER copied into B: B.profile = {name: BASE_NAME[enum], enum}.
# (enum, mask): an int mask is exact (agent 1's E mutants, make_manifest.py:17-21); None = any mask 0..MUT_ALL (repaired-f, design section 1: MUT_ALL = (1 << 9) - 1 = 511).
PROFILE_TABLE = {"paper-strict": (0, 0), "paper-minimal": (1, 0), "repaired-e": (2, 0), "repaired-f": (3, None),
                 "mutant-no-destination-binding": (2, 1), "mutant-no-state-barrier": (2, 2), "mutant-no-record-freshness": (2, 4),
                 "mutant-no-nonce": (2, 8), "mutant-no-version-monotone": (2, 16), "mutant-no-receipt-binding": (2, 32)}
BASE_NAME = {0: "paper-strict", 1: "paper-minimal", 2: "repaired-e", 3: "repaired-f"}
MUT_ALL = (1 << 9) - 1
MASK_HOLDERS_E = ("TMSC", "PSC", "KSSC", "ACSC")
PBC_E, DBC_E = ("LSC", "TMSC", "RSC", "PSC"), ("ACSC", "KSSC")

_DEC = re.compile(r"(0|[1-9][0-9]*)")
_ADDR = re.compile(r"0x[0-9a-f]{40}")
_SHA = re.compile(r"[0-9a-f]{64}")
_BHASH = re.compile(r"0x[0-9a-f]{64}")
_HEXCODE = re.compile(r"0x(?:[0-9a-f]{2})*")
_IFACE = re.compile(r"v[0-9]+")
IMMUTABLE_SLOT_BYTES = 32      # agent 1's export rule (A1-0096 design 2.2 section 8): every immutable reference is exactly one 32-byte slot


class OpenRefusal(ValueError):
    """A refusal at store open with its SUCCESSOR-WIRE section 1 reason (PROFILE_MISMATCH at stage 2, MUTATIONS_MISMATCH at stage 7)."""

    def __init__(self, reason, message):
        super().__init__(f"{reason}: {message}")
        self.reason = reason


def _is_dec(v):
    return isinstance(v, str) and _DEC.fullmatch(v) is not None


def profile_from_manifest(name, enum, mutations, live_enum, live_mutations):
    """Map a manifest profile to B.profile and apply the open-time profile/mutation checks (stages 2 and 7). Returns {"name", "enum"} (the BASE name) or raises OpenRefusal."""
    row = PROFILE_TABLE.get(name) if isinstance(name, str) else None
    if row is None:
        raise OpenRefusal("PROFILE_MISMATCH", "manifest profile name is not in the closed table")
    if not _is_dec(enum) or int(enum) != row[0]:
        raise OpenRefusal("PROFILE_MISMATCH", "manifest profileEnum differs from the table entry for this name")
    if not _is_dec(live_enum) or int(live_enum) != row[0]:
        raise OpenRefusal("PROFILE_MISMATCH", "live profile() differs from the manifest")
    if not _is_dec(mutations):
        raise OpenRefusal("MUTATIONS_MISMATCH", "manifest mutations is not a decimal string")
    mask = int(mutations)
    if (row[1] is None and not 0 <= mask <= MUT_ALL) or (row[1] is not None and mask != row[1]):
        raise OpenRefusal("MUTATIONS_MISMATCH", "manifest mutations is not allowed for this profile name")
    want = set(MASK_HOLDERS_E) | ({"Governance"} if row[0] == 3 else set())
    if not isinstance(live_mutations, dict) or set(live_mutations) != want:
        raise OpenRefusal("MUTATIONS_MISMATCH", "live mutations are not reported by exactly the contracts of this profile")
    for n, v in live_mutations.items():
        if not _is_dec(v) or int(v) != mask:
            raise OpenRefusal("MUTATIONS_MISMATCH", f"live mutations of {n} differ from the manifest")
    return {"name": BASE_NAME[row[0]], "enum": str(row[0])}


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
        raise ValueError("profile.name is not a base profile name (the manifest name is never copied into B)")
    e = _dec(p["enum"], "profile.enum", 8)
    if e > 3 or BASE_NAME[e] != p["name"]:
        raise ValueError("profile: name and enum disagree or the enum is out of range")
    f = p["name"] == "repaired-f"
    if f and d["interfaceVersion"] != "v2":
        raise ValueError("repaired-f requires interfaceVersion v2 (A1-0105 N3)")
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
    if f and not all(pins):
        raise ValueError("repaired-f requires immutableRefsSha256 on every contract (A3-0059)")
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
        if len(set(r["witnesses"])) != len(r["witnesses"]):
            raise ValueError(n + ".witnesses: duplicate member")
        if not 1 <= int(r["threshold"]) <= len(r["witnesses"]):
            raise ValueError(n + ".threshold must be between 1 and the number of witnesses")
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


def pairs_from_object_list(refs):
    """Object list `[{"start": "8", "length": "32"}, ...]` (the wire form, agent 1's export and agent 3's schema) -> `[[start, length], ...]`, the argument of masked_runtime_sha256."""
    if not isinstance(refs, list):
        raise ValueError("ranges must be a list")
    out = []
    for i, r in enumerate(refs):
        if not isinstance(r, dict):
            raise ValueError(f"range {i}: expected an object with keys start and length")
        if set(r) != {"start", "length"}:
            raise ValueError(f"range {i}: keys {sorted(r)} must be exactly ['length', 'start']")
        out.append([r["start"], r["length"]])
    return out


def immutable_refs_canonical_json(refs, runtime_bytes) -> str:
    """Canonical UTF-8 text of the pinned object list: sorted object keys, compact separators, ensure_ascii. Validates every range rule first (the pair form is NOT accepted)."""
    pairs = pairs_from_object_list(refs)
    _ranges(pairs, _dec(runtime_bytes, "runtimeBytes", 32))
    return json.dumps(refs, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def immutable_refs_sha256(refs, runtime_bytes) -> str:
    """`immutableRefsSha256` of B: lowercase sha256 hex of the canonical JSON of the pinned object list (A3-0059). Never hash ranges that came from RPC."""
    return hashlib.sha256(immutable_refs_canonical_json(refs, runtime_bytes).encode("utf-8")).hexdigest()


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


def synthetic_binding_document(profile: str, fixture_path: str | None = None, mutations: str = "0") -> dict:
    fixture_path = fixture_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tests", "fixtures",
                                                "deployment-agent1-91add8c-v1-repaired-e.json")
    with open(fixture_path, encoding="utf-8") as fh:
        fx = json.load(fh)
    f = profile == "repaired-f"
    enum = {"paper-strict": "0", "paper-minimal": "1", "repaired-e": "2", "repaired-f": "3"}[profile]
    witnesses = [_addr(f"witness-{i}") for i in range(1, 5)] if f else [fx["fixture"]["witnessSet"]["witnesses"][0]]
    wset = {"version": "2" if f else "1", "threshold": "3" if f else "1", "witnesses": witnesses}
    doc = {"interfaceVersion": "v2" if f else "v1", "profile": {"name": profile, "enum": enum}, "chains": {}, "immutables": {},
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
                row = {"address": ch["contracts"][n], "codeSha256": _syn("code:" + n + (":m" + mutations if mutations != "0" else "")), "abiSha256": a["abiSha256"],
                       "runtimeSha256": a["runtimeSha256"], "runtimeBytes": str(a["runtimeBytes"])}
            row["immutableRefsSha256"] = _syn("refs:" + n)
            contracts[n] = row
        doc["chains"][side] = {"chainId": ch["chainId"], "genesisHash": "0x" + _syn("genesis:" + side), "contracts": contracts,
                               "deployBlock": {"number": str(ch["deployBlock"]), "hash": "0x" + _syn("deployblock:" + side)}}
    for n in ("TMSC", "PSC", "KSSC", "ACSC"):
        doc["immutables"][n] = {"profile": enum, "mutations": mutations}
    pbc, dbc = doc["chains"]["pbc"]["contracts"], doc["chains"]["dbc"]["contracts"]
    doc["wiring"] = {"ksscForChain": dbc["KSSC"]["address"], "acsc": dbc["ACSC"]["address"], "kssc": dbc["KSSC"]["address"],
                     "pscRelay": fx["fixture"]["relay"]["address"],
                     "tmsc": {"psc": pbc["PSC"]["address"], "rsc": pbc["RSC"]["address"]},
                     "lsc": {"rsc": pbc["RSC"]["address"], "tmsc": pbc["TMSC"]["address"], "psc": pbc["PSC"]["address"]}}
    if f:
        doc["immutables"]["Governance"] = {"mutations": mutations}
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
    mut = synthetic_binding_document("repaired-e", mutations="8")
    out["documents"]["repaired-e-mutant-no-nonce"] = {"document": mut, "canonicalJson": canonical_json(mut), "bindingV2": binding_v2(mut),
                                                      "note": "manifest profile 'mutant-no-nonce' (enum 2, mask 8) binds under the BASE name repaired-e; the live per-contract mutations and code hashes separate it from the baseline"}
    out["profileTable"] = {k: {"enum": str(v[0]), "mutations": "any 0..511" if v[1] is None else str(v[1])} for k, v in PROFILE_TABLE.items()}
    out["baseNames"] = {str(k): v for k, v in BASE_NAME.items()}
    le = {n: "0" for n in MASK_HOLDERS_E}
    lf = dict(le, Governance="0")
    cases = [
        (("repaired-e", "2", "0", "2", le), None), (("paper-strict", "0", "0", "0", le), None), (("paper-minimal", "1", "0", "1", le), None),
        (("mutant-no-nonce", "2", "8", "2", {n: "8" for n in le}), None), (("mutant-no-receipt-binding", "2", "32", "2", {n: "32" for n in le}), None),
        (("repaired-f", "3", "0", "3", lf), None), (("repaired-f", "3", "511", "3", {n: "511" for n in lf}), None),
        (("mutant-no-such", "2", "0", "2", le), "PROFILE_MISMATCH"), (("mutant-no-nonce", "3", "8", "3", {n: "8" for n in lf}), "PROFILE_MISMATCH"),
        (("repaired-e", "2", "0", "3", le), "PROFILE_MISMATCH"), (("mutant-no-nonce", "2", "8", "2", le), "MUTATIONS_MISMATCH"),
        (("repaired-e", "2", "0", "2", {n: "8" for n in le}), "MUTATIONS_MISMATCH"), (("repaired-f", "3", "512", "3", {n: "512" for n in lf}), "MUTATIONS_MISMATCH"),
        (("repaired-f", "3", "0", "3", le), "MUTATIONS_MISMATCH")]
    out["manifestProfileCases"] = []
    for inp, refusal in cases:
        case = {"input": [inp[0], inp[1], inp[2], inp[3], inp[4]], "fields": ["manifest.profile", "manifest.profileEnum", "manifest.mutations", "live profile()", "live mutations by contract"]}
        if refusal is None:
            case["expectedProfile"] = profile_from_manifest(*inp)
        else:
            case["expectedRefusal"] = refusal
            try:
                profile_from_manifest(*inp)
                raise AssertionError("vector case did not refuse")
            except OpenRefusal as e:
                assert e.reason == refusal
        out["manifestProfileCases"].append(case)
    code = bytes(range(128))
    live = bytearray(code)
    live[8:40] = b"\xaa" * 32
    live[64:96] = b"\xbb" * 32
    ranges = [["8", "32"], ["64", "32"]]
    out["maskedBuild"] = {"liveRuntimeHex": "0x" + live.hex(), "ranges": ranges, "runtimeBytes": "128",
                          "maskedSha256": masked_runtime_sha256("0x" + live.hex(), ranges, "128"),
                          "rule": "ranges and runtimeBytes are TRUSTED build pins; refuse unsorted, overlapping, zero-length, length != 32 (A1-0096), out-of-bounds or non-decimal ranges, a live length different from runtimeBytes, and non-canonical hex",
                          "limit": "checks the runtime outside the immutable slots only; it is NOT constructor or source attestation"}
    refs = [{"start": r[0], "length": r[1]} for r in ranges]
    out["immutableRefs"] = {"objectList": refs, "runtimeBytes": "128", "canonicalJson": immutable_refs_canonical_json(refs, "128"),
                            "immutableRefsSha256": immutable_refs_sha256(refs, "128"),
                            "note": "pins the representation of immutableRefsSha256; the synthetic documents above carry a placeholder value for that field, so their binding_v2 values are unaffected"}
    return out


if __name__ == "__main__":
    if "--emit" in sys.argv[1:]:
        print(json.dumps(emit(), indent=1, sort_keys=True))
    else:
        print(__doc__)
