"""D50 deployment binding, production code (agent 2, F task 2): paper-derived reconstruction, SYMBOLIC, synthetic fixtures; not a measured system.

The PRODUCTION port of the pinned specification reference (D50 revision 5, protocol/f0 8ed6f1a4..): the closed shape of the binding document B, its canonical encoding and hash, the closed
manifest-profile table with the open-time profile/mutation refusals, the pinned object list of immutable ranges and the strict masked-build check. Standard library only; no clock, no randomness,
no network. The live reads that FILL a document (genesis, live code hashes, getters) are not here: they need a chain client and belong to the witness service slice.

The binding does not and cannot separate signature DOMAINS: two deployments with the same chain ids and addresses share every EIP-712 domain. It binds STORES (code, storage, genesis, owner).
`tests/test_binding.py` proves this module equivalent to the reference on the pinned vector and on a corruption corpus; if they ever differ the pin wins.
"""
from __future__ import annotations

import hashlib
import json
import re

PREFIX = b"hmbc-deployment-binding/v2\n"
PROFILES = {"paper-strict", "paper-minimal", "repaired-e", "repaired-f"}
PBC_E, DBC_E = ("LSC", "TMSC", "RSC", "PSC"), ("ACSC", "KSSC")
IMMUTABLE_SLOT_BYTES = 32                # every immutable reference is exactly one 32-byte slot (agent 1's export rule)
# The manifest `profile` NAME is validated against this closed table and is NEVER copied into B: B.profile = {name: BASE_NAME[enum], enum} (D50 revision 5).
# (enum, mask): an int mask is exact (the E mutants, make_manifest.py); None = any mask 0..MUT_ALL (repaired-f).
PROFILE_TABLE = {"paper-strict": (0, 0), "paper-minimal": (1, 0), "repaired-e": (2, 0), "repaired-f": (3, None),
                 "mutant-no-destination-binding": (2, 1), "mutant-no-state-barrier": (2, 2), "mutant-no-record-freshness": (2, 4),
                 "mutant-no-nonce": (2, 8), "mutant-no-version-monotone": (2, 16), "mutant-no-receipt-binding": (2, 32)}
BASE_NAME = {0: "paper-strict", 1: "paper-minimal", 2: "repaired-e", 3: "repaired-f"}
MUT_ALL = (1 << 9) - 1
MASK_HOLDERS_E = ("TMSC", "PSC", "KSSC", "ACSC")

_DEC = re.compile(r"(0|[1-9][0-9]*)")
_ADDR = re.compile(r"0x[0-9a-f]{40}")
_SHA = re.compile(r"[0-9a-f]{64}")
_BHASH = re.compile(r"0x[0-9a-f]{64}")
_HEXCODE = re.compile(r"0x(?:[0-9a-f]{2})*")
_IFACE = re.compile(r"v[0-9]+")


class OpenRefusal(ValueError):
    """A refusal at store open with its SUCCESSOR-WIRE section 1 reason: PROFILE_MISMATCH (stage 2) or MUTATIONS_MISMATCH (stage 7)."""

    def __init__(self, reason: str, message: str):
        super().__init__(f"{reason}: {message}")
        self.reason = reason


def _is_dec(v) -> bool:
    return isinstance(v, str) and _DEC.fullmatch(v) is not None


def _dec(v, what: str, bits: int = 256) -> int:
    if not _is_dec(v) or int(v) >= 1 << bits:
        raise ValueError(f"{what}: expected a decimal string below 2^{bits}")
    return int(v)


def _match(rx, v, what: str) -> None:
    if not isinstance(v, str) or not rx.fullmatch(v):
        raise ValueError(f"{what}: bad format")


def _closed(obj, required, optional, what: str) -> dict:
    if not isinstance(obj, dict):
        raise ValueError(f"{what}: expected an object")
    keys = set(obj)
    if not set(required) <= keys or not keys <= set(required) | set(optional):
        raise ValueError(f"{what}: keys {sorted(keys)} do not match required {sorted(required)} optional {sorted(optional)}")
    return obj


def canonical_json(doc) -> str:
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def profile_from_manifest(name, enum, mutations, live_enum, live_mutations) -> dict:
    """Map a manifest profile to B.profile and apply the open-time profile and mutation checks. Returns {"name", "enum"} (the BASE name) or raises OpenRefusal.
    A wrong profile is reported before wrong mutations; `mutantNote` and every other free text are never read."""
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


def validate(doc) -> bool:
    """Validate the CLOSED shape of B (an unknown or missing key is refused, never ignored). Returns True for a repaired-f document (Governance present)."""
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
        raise ValueError("repaired-f requires interfaceVersion v2")
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
        raise ValueError("repaired-f requires immutableRefsSha256 on every contract")
    im = _closed(d["immutables"], list(MASK_HOLDERS_E) + (["Governance"] if f else []), [], "immutables")
    for n, row in im.items():
        if n == "Governance":
            _dec(_closed(row, ["mutations"], [], n)["mutations"], n + ".mutations")
        else:
            r = _closed(row, ["profile", "mutations"], [], n)
            _dec(r["profile"], n + ".profile", 8)
            _dec(r["mutations"], n + ".mutations")
    wsets = _closed(d["witnessSets"], ["psc", "kssc"] + (["governance"] if f else []), [], "witnessSets")
    for n, row in wsets.items():
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
    """sha256(PREFIX || canonical JSON of B), lowercase hex without 0x. The shape is validated first."""
    validate(doc)
    return hashlib.sha256(PREFIX + canonical_json(doc).encode("ascii")).hexdigest()


# ---- the pinned immutable ranges and the strict masked-build check ---------------------------------------------------------------
def _ranges(ranges, n: int):
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
    """The wire object list [{"start": "8", "length": "32"}, ...] -> [[start, length], ...]; the pair form is only the argument of the masked check, never a wire representation."""
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
    pairs = pairs_from_object_list(refs)
    _ranges(pairs, _dec(runtime_bytes, "runtimeBytes", 32))
    return json.dumps(refs, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def immutable_refs_sha256(refs, runtime_bytes) -> str:
    """`immutableRefsSha256` of B: sha256 of the canonical JSON of the PINNED object list. Never hash ranges that came from RPC."""
    return hashlib.sha256(immutable_refs_canonical_json(refs, runtime_bytes).encode("utf-8")).hexdigest()


def masked_runtime_sha256(code_hex, ranges, runtime_bytes) -> str:
    """sha256 of the live runtime with every pinned immutable range zeroed. `ranges` and `runtime_bytes` are TRUSTED build pins, never RPC data. The output is built by concatenating segments,
    never by slice assignment (assigning to an out-of-bounds slice of a bytearray silently changes its length and would hide a malformed range)."""
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
