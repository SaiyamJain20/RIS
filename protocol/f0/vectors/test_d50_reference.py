"""Expectations for the D50 binding reference and the masked-build check (agent 2, F0 revision 3). Written BEFORE the reference exists.

Run: python3 -I protocol/f0/vectors/test_d50_reference.py   (standard library only; exit 0 = all expectations hold)
The reference is a SPECIFICATION VECTOR generator, not production code. Live-derived fields in the vector are SYNTHETIC placeholders.
"""
import copy
import hashlib
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("d50_reference", os.path.join(HERE, "d50_reference.py"))
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)

FAILS = []


def check(name, cond):
    if not cond:
        FAILS.append(name)
    print(("ok   " if cond else "FAIL ") + name)


def raises(fn, contains=None, exc=ValueError):
    """True when fn raises exc (and, if given, the message contains `contains`: the PRIMARY check must refuse, not a backstop)."""
    try:
        fn()
    except exc as e:
        return contains is None or contains in str(e)
    except Exception:  # noqa: BLE001 - a different exception class is a failure of the expectation
        return False
    return False


E = ref.synthetic_binding_document("repaired-e")
F = ref.synthetic_binding_document("repaired-f")

# --- canonical form and hash representation -------------------------------------------------------------------------------------
text = ref.canonical_json(E)
check("canonical json has no spaces and sorted keys", ": " not in text and ", " not in text and text == json.dumps(E, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
check("key order of the input does not matter", ref.canonical_json(dict(reversed(list(E.items())))) == text)
expected = hashlib.sha256(b"hmbc-deployment-binding/v2\n" + text.encode("ascii")).hexdigest()
check("binding_v2 = sha256(prefix || canonical json), lowercase hex without 0x", ref.binding_v2(E) == expected and len(expected) == 64)
check("E and F documents bind differently", ref.binding_v2(E) != ref.binding_v2(F))


# --- binding-sensitive: every one of these must change the hash -----------------------------------------------------------------
def mutate(doc, path, value):
    d = copy.deepcopy(doc)
    cur = d
    for k in path[:-1]:
        cur = cur[k]
    cur[path[-1]] = value
    return d


def flip(hexstr):
    """Change the last hex digit, keeping the shape."""
    return hexstr[:-1] + ("0" if hexstr[-1] != "0" else "1")


SENSITIVE = [
    (["interfaceVersion"], "v2"),
    (["profile"], {"name": "paper-strict", "enum": "0"}),    # revision 5: a lone name or enum change is now REFUSED (R5-5, the name is derived from the enum); the pair still changes the hash
    (["chains", "pbc", "chainId"], "18546"),
    (["chains", "pbc", "genesisHash"], flip(E["chains"]["pbc"]["genesisHash"])),
    (["chains", "dbc", "deployBlock", "number"], "999"),
    (["chains", "dbc", "deployBlock", "hash"], flip(E["chains"]["dbc"]["deployBlock"]["hash"])),
    (["chains", "pbc", "contracts", "PSC", "address"], flip(E["chains"]["pbc"]["contracts"]["PSC"]["address"])),
    (["chains", "pbc", "contracts", "TMSC", "codeSha256"], flip(E["chains"]["pbc"]["contracts"]["TMSC"]["codeSha256"])),
    (["chains", "dbc", "contracts", "KSSC", "abiSha256"], flip(E["chains"]["dbc"]["contracts"]["KSSC"]["abiSha256"])),
    (["chains", "dbc", "contracts", "ACSC", "runtimeSha256"], flip(E["chains"]["dbc"]["contracts"]["ACSC"]["runtimeSha256"])),
    (["chains", "pbc", "contracts", "LSC", "runtimeBytes"], "3725"),
    (["immutables", "KSSC", "mutations"], "8"),
    (["immutables", "PSC", "profile"], "1"),
    (["witnessSets", "kssc", "version"], "9"),     # revision 5: the E threshold-2 case moved to the F list below (2 of 1 witness is now refused as unsatisfiable, R5-7)
    (["witnessSets", "psc", "witnesses"], ["0x" + "11" * 20]),
    (["wiring", "pscRelay"], "0x" + "22" * 20),
    (["wiring", "tmsc", "psc"], "0x" + "33" * 20),
    (["wiring", "lsc", "tmsc"], "0x" + "44" * 20),
]
for path, value in SENSITIVE:
    check("sensitive: " + ".".join(path), ref.binding_v2(mutate(E, path, value)) != ref.binding_v2(E))
for path, value in [(["witnessSets", "psc", "threshold"], "2"), (["witnessSets", "governance", "threshold"], "2"), (["immutables", "Governance", "mutations"], "64"),
                    (["wiring", "governance", "target"], "0x" + "55" * 20), (["chains", "pbc", "contracts", "Governance", "codeSha256"], flip(F["chains"]["pbc"]["contracts"]["Governance"]["codeSha256"]))]:
    check("sensitive (F only): " + ".".join(path), ref.binding_v2(mutate(F, path, value)) != ref.binding_v2(F))

# --- closed shape ---------------------------------------------------------------------------------------------------------------
check("an excluded mutable field is refused, never silently ignored", raises(lambda: ref.binding_v2({**E, "authEpoch": "1"})))
check("owner is not part of B", raises(lambda: ref.binding_v2({**E, "owner": "worker"})))
check("E document must not carry Governance", raises(lambda: ref.binding_v2(mutate(E, ["wiring", "governance"], {"tmsc": "0x" + "00" * 20, "target": "0x" + "00" * 20}))))
check("F document must carry Governance (contract set)", raises(lambda: ref.binding_v2({**F, "witnessSets": {k: v for k, v in F["witnessSets"].items() if k != "governance"}})))
check("integers are decimal strings: a JSON int is refused", raises(lambda: ref.binding_v2(mutate(E, ["chains", "pbc", "chainId"], 18545))))
check("leading zero refused", raises(lambda: ref.binding_v2(mutate(E, ["witnessSets", "psc", "threshold"], "01"))))
check("negative refused", raises(lambda: ref.binding_v2(mutate(E, ["immutables", "PSC", "mutations"], "-1"))))
check("uppercase address refused", raises(lambda: ref.binding_v2(mutate(E, ["wiring", "pscRelay"], "0x" + "AB" * 20))))
check("0x prefix on a sha256 value refused", raises(lambda: ref.binding_v2(mutate(E, ["chains", "pbc", "contracts", "TMSC", "codeSha256"], "0x" + E["chains"]["pbc"]["contracts"]["TMSC"]["codeSha256"]))))
check("block hash needs 0x and 64 hex", raises(lambda: ref.binding_v2(mutate(E, ["chains", "pbc", "genesisHash"], E["chains"]["pbc"]["genesisHash"][2:]))))
check("a block number that is a bool is refused", raises(lambda: ref.binding_v2(mutate(E, ["chains", "pbc", "deployBlock", "number"], True))))

# --- masked build check (A1-0096 export rule: ranges sorted, non-overlapping, length == 32, inside [0, runtimeBytes)) -------------
code = bytes(range(128))
ranges = [["8", "32"], ["64", "32"]]
live = bytearray(code)
live[8:40] = b"\xaa" * 32
live[64:96] = b"\xbb" * 32
masked_expected = bytearray(live)
masked_expected[8:40] = bytes(32)
masked_expected[64:96] = bytes(32)
want = hashlib.sha256(bytes(masked_expected)).hexdigest()
check("masked hash of a valid vector equals the independently built value", ref.masked_runtime_sha256("0x" + live.hex(), ranges, "128") == want)
check("masked hash ignores what sits in the immutable slots", ref.masked_runtime_sha256("0x" + code.hex(), ranges, "128") == want)
flipped = bytearray(live)
flipped[0] ^= 1
check("a changed byte outside the slots changes the masked hash", ref.masked_runtime_sha256("0x" + flipped.hex(), ranges, "128") != want)
check("an empty range list is valid (no immutables)", ref.masked_runtime_sha256("0x" + code.hex(), [], "128") == hashlib.sha256(code).hexdigest())
BAD_RANGES = {
    "unsorted": ([["64", "32"], ["8", "32"]], "unsorted or overlapping"),
    "overlapping": ([["8", "32"], ["20", "32"]], "unsorted or overlapping"),
    "overlap by one byte": ([["8", "32"], ["39", "32"]], "unsorted or overlapping"),
    "duplicate": ([["8", "32"], ["8", "32"]], "unsorted or overlapping"),
    "zero length": ([["8", "0"]], "zero length"),
    "length not 32 (short)": ([["8", "4"]], "length must be 32"),
    "length not 32 (long)": ([["8", "33"]], "length must be 32"),
    "length larger than the code": ([["0", "129"]], "length must be 32"),
    "start at the end": ([["128", "32"]], "past the"),
    "end past the end": ([["100", "32"]], "past the"),
    "leading zero": ([["08", "32"]], "decimal string"),
    "negative start": ([["-1", "32"]], "decimal string"),
    "non-numeric": ([["a", "32"]], "decimal string"),
    "integer instead of string": ([[8, 32]], "decimal string"),
    "bool": ([[True, "32"]], "decimal string"),
    "wrong arity": ([["8"]], "expected [start, length]"),
    "not a list": ("8:32", "must be a list"),
}
for name, (bad, why) in BAD_RANGES.items():
    check("malformed range refused by the primary check: " + name, raises(lambda bad=bad: ref.masked_runtime_sha256("0x" + code.hex(), bad, "128"), why))
check("adjacent ranges (end == next start) are accepted", ref.masked_runtime_sha256("0x" + code.hex(), [["8", "32"], ["40", "32"]], "128") != "")
check("the last 32 bytes can be a range (end == runtimeBytes)", ref.masked_runtime_sha256("0x" + code.hex(), [["96", "32"]], "128") != "")
check("code length differing from the pinned length is refused by the length check", raises(lambda: ref.masked_runtime_sha256("0x" + code.hex(), ranges, "127"), "pin says"))
check("a longer pin is refused too", raises(lambda: ref.masked_runtime_sha256("0x" + code.hex(), ranges, "129"), "pin says"))
check("pinned length must be a decimal string", raises(lambda: ref.masked_runtime_sha256("0x" + code.hex(), ranges, 128), "decimal string"))
check("uppercase hex code refused", raises(lambda: ref.masked_runtime_sha256("0x" + code.hex().upper(), ranges, "128"), "bad format"))
check("odd-length hex refused", raises(lambda: ref.masked_runtime_sha256("0x" + code.hex()[:-1], ranges, "128"), "bad format"))
check("missing 0x refused", raises(lambda: ref.masked_runtime_sha256(code.hex(), ranges, "128"), "bad format"))

# --- why the strict check exists: a naive slice assignment silently changes the buffer length ---------------------------------
naive = bytearray(code)
naive[124:124 + 8] = bytes(8)
check("documented hazard: naive slice masking of an out-of-bounds range EXTENDS the buffer", len(naive) == 132 != len(code))

# --- immutableRefsSha256 as a canonical OBJECT LIST (A3-0059; agent 3's proposal, accepted) -------------------------------------
OBJ = [{"start": "8", "length": "32"}, {"start": "64", "length": "32"}]
want_json = '[{"length":"32","start":"8"},{"length":"32","start":"64"}]'
check("object-list canonical JSON: sorted keys, compact, decimal strings", ref.immutable_refs_canonical_json(OBJ, "128") == want_json)
check("immutableRefsSha256 = sha256 of that UTF-8 text, lowercase hex", ref.immutable_refs_sha256(OBJ, "128") == hashlib.sha256(want_json.encode("utf-8")).hexdigest())
check("input key order does not matter", ref.immutable_refs_sha256([{"length": "32", "start": "8"}, {"length": "32", "start": "64"}], "128") == ref.immutable_refs_sha256(OBJ, "128"))
check("an empty list is valid and hashes the text []", ref.immutable_refs_sha256([], "128") == hashlib.sha256(b"[]").hexdigest())
check("the pair form is NOT a second wire representation: refused", raises(lambda: ref.immutable_refs_sha256([["8", "32"], ["64", "32"]], "128"), "object"))
check("an extra key is refused", raises(lambda: ref.immutable_refs_sha256([{"start": "8", "length": "32", "id": "7"}], "128"), "keys"))
check("a missing key is refused", raises(lambda: ref.immutable_refs_sha256([{"start": "8"}], "128"), "keys"))
check("integers instead of decimal strings are refused", raises(lambda: ref.immutable_refs_sha256([{"start": 8, "length": 32}], "128"), "decimal string"))
check("unsorted object list refused", raises(lambda: ref.immutable_refs_sha256([OBJ[1], OBJ[0]], "128"), "unsorted or overlapping"))
check("overlapping object list refused", raises(lambda: ref.immutable_refs_sha256([{"start": "8", "length": "32"}, {"start": "39", "length": "32"}], "128"), "unsorted or overlapping"))
check("length other than 32 refused", raises(lambda: ref.immutable_refs_sha256([{"start": "8", "length": "31"}], "128"), "length must be 32"))
check("a range ending after runtimeBytes is refused", raises(lambda: ref.immutable_refs_sha256([{"start": "100", "length": "32"}], "128"), "past the"))
check("a list that is not a list is refused", raises(lambda: ref.immutable_refs_sha256("x", "128"), "must be a list"))
check("object list and pair list drive the same masked hash", ref.masked_runtime_sha256("0x" + live.hex(), ref.pairs_from_object_list(OBJ), "128") == want)

# --- repaired-f REQUIRES immutableRefsSha256 on every contract; E documents allow all-or-none -----------------------------------
def drop_refs(doc, only=None):
    d = copy.deepcopy(doc)
    for side in ("pbc", "dbc"):
        for n, row in d["chains"][side]["contracts"].items():
            if only is None or n == only:
                row.pop("immutableRefsSha256", None)
    return d


check("E document without any immutableRefsSha256 is valid (all or none)", ref.binding_v2(drop_refs(E)) != "")
check("F document without immutableRefsSha256 is refused", raises(lambda: ref.binding_v2(drop_refs(F)), "repaired-f"))
check("F document missing it on one contract is refused", raises(lambda: ref.binding_v2(drop_refs(F, only="KSSC"))))
check("E document with it on one contract only is refused", raises(lambda: ref.binding_v2(drop_refs(E, only="KSSC"))))

# =================================================================================================================================
# REVISION 5 (A2-0054 P-1, P-7; agent 1's A1-0105 N3). Written BEFORE the reference changes; every expectation below fails on the revision-4 reference.
# The manifest `profile` name versus B.profile: a closed table, B.profile = {name: BASE[enum], enum}, open-time refusals, and four shape rules.
# =================================================================================================================================
def refusal(fn):
    """The `reason` of the OpenRefusal that fn raises, None when it does not refuse, 'other' for any other exception."""
    try:
        fn()
    except getattr(ref, "OpenRefusal", ()) as e:
        return e.reason
    except Exception:  # noqa: BLE001
        return "other"
    return None


E_MUTANTS = {"mutant-no-destination-binding": "1", "mutant-no-state-barrier": "2", "mutant-no-record-freshness": "4",
             "mutant-no-nonce": "8", "mutant-no-version-monotone": "16", "mutant-no-receipt-binding": "32"}      # agent 1, make_manifest.py:17-21
LIVE_E = {n: "0" for n in ("TMSC", "PSC", "KSSC", "ACSC")}
LIVE_F = {n: "0" for n in ("TMSC", "PSC", "KSSC", "ACSC", "Governance")}
check("R5-1 the manifest-name table is closed: four base names, six E mutants",
      set(getattr(ref, "PROFILE_TABLE", {})) == {"paper-strict", "paper-minimal", "repaired-e", "repaired-f"} | set(E_MUTANTS))
check("R5-1 base names map to enums 0..3 and every E mutant is enum 2 with one distinct bit (1, 2, 4, 8, 16, 32)",
      all(getattr(ref, "PROFILE_TABLE", {}).get(n, (None, None))[0] == int(e) for n, e in
          (("paper-strict", "0"), ("paper-minimal", "1"), ("repaired-e", "2"), ("repaired-f", "3")))
      and all(getattr(ref, "PROFILE_TABLE", {}).get(n) == (2, int(m)) for n, m in E_MUTANTS.items()))
pfm = getattr(ref, "profile_from_manifest", None)


def pf(*a):
    """Non-raising form for POSITIVE expectations: a refusal where a mapping was expected is a failed expectation, not a crash."""
    try:
        return pfm(*a)
    except Exception as e:  # noqa: BLE001
        return ("refused", getattr(e, "reason", repr(e)))


check("R5-2 the baseline name maps to itself", pfm and pf("repaired-e", "2", "0", "2", LIVE_E) == {"name": "repaired-e", "enum": "2"})
for name, mask in E_MUTANTS.items():
    live = {n: mask for n in LIVE_E}
    check("R5-2 %s binds under the BASE name repaired-e (enum 2)" % name, pfm and pf(name, "2", mask, "2", live) == {"name": "repaired-e", "enum": "2"})
check("R5-2 paper-strict and paper-minimal bind under themselves", pfm and pf("paper-strict", "0", "0", "0", LIVE_E) == {"name": "paper-strict", "enum": "0"}
      and pf("paper-minimal", "1", "0", "1", LIVE_E) == {"name": "paper-minimal", "enum": "1"})
check("R5-2 repaired-f accepts any mask 0..511 (0, 64, 511)", pfm and all(pf("repaired-f", "3", m, "3", {n: m for n in LIVE_F}) == {"name": "repaired-f", "enum": "3"} for m in ("0", "64", "511")))
mutE = ref.synthetic_binding_document("repaired-e", mutations="8") if "mutations" in ref.synthetic_binding_document.__code__.co_varnames else None
check("R5-3 a mutant's B differs from the baseline's: the live per-contract mutations (and code hashes) separate them",
      mutE is not None and ref.binding_v2(mutE) != ref.binding_v2(E) and mutE["profile"] == E["profile"]
      and all(mutE["immutables"][n]["mutations"] == "8" for n in LIVE_E))
check("R5-3 the baseline E binding is UNCHANGED by revision 5 (pinned regression: 242f7ca6..)", ref.binding_v2(E).startswith("242f7ca6977e22c9"))
check("R5-4 unknown manifest name is PROFILE_MISMATCH", refusal(lambda: pfm("mutant-no-such", "2", "0", "2", LIVE_E)) == "PROFILE_MISMATCH")
check("R5-4 a mutant name with the wrong manifest enum is PROFILE_MISMATCH", refusal(lambda: pfm("mutant-no-nonce", "3", "8", "3", {n: "8" for n in LIVE_F})) == "PROFILE_MISMATCH")
check("R5-4 manifest enum differing from the live profile() is PROFILE_MISMATCH", refusal(lambda: pfm("repaired-e", "2", "0", "3", LIVE_E)) == "PROFILE_MISMATCH")
check("R5-4 a baseline mislabelled as a mutant (live mask 0, name mutant-no-nonce) is MUTATIONS_MISMATCH", refusal(lambda: pfm("mutant-no-nonce", "2", "8", "2", LIVE_E)) == "MUTATIONS_MISMATCH")
check("R5-4 a mutant mislabelled as the baseline (live mask 8, name repaired-e) is MUTATIONS_MISMATCH", refusal(lambda: pfm("repaired-e", "2", "0", "2", {n: "8" for n in LIVE_E})) == "MUTATIONS_MISMATCH")
check("R5-4 the manifest mask differing from the table mask for an E name is MUTATIONS_MISMATCH", refusal(lambda: pfm("mutant-no-nonce", "2", "4", "2", {n: "4" for n in LIVE_E})) == "MUTATIONS_MISMATCH")
check("R5-4 one contract's live mask differing is MUTATIONS_MISMATCH", refusal(lambda: pfm("mutant-no-nonce", "2", "8", "2", {**{n: "8" for n in LIVE_E}, "KSSC": "0"})) == "MUTATIONS_MISMATCH")
check("R5-4 repaired-f mask 512 is MUTATIONS_MISMATCH", refusal(lambda: pfm("repaired-f", "3", "512", "3", {n: "512" for n in LIVE_F})) == "MUTATIONS_MISMATCH")
check("R5-4 F without Governance in the live masks is MUTATIONS_MISMATCH", refusal(lambda: pfm("repaired-f", "3", "0", "3", LIVE_E)) == "MUTATIONS_MISMATCH")
check("R5-4 E with a Governance live mask is MUTATIONS_MISMATCH", refusal(lambda: pfm("repaired-e", "2", "0", "2", LIVE_F)) == "MUTATIONS_MISMATCH")
check("R5-4 precedence: a wrong profile is reported before wrong mutations", refusal(lambda: pfm("mutant-no-such", "2", "99", "2", {n: "7" for n in LIVE_E})) == "PROFILE_MISMATCH")
check("R5-4 non-decimal manifest enum or mutations is PROFILE_MISMATCH / MUTATIONS_MISMATCH, never another exception",
      refusal(lambda: pfm("repaired-e", 2, "0", "2", LIVE_E)) == "PROFILE_MISMATCH" and refusal(lambda: pfm("repaired-e", "2", 0, "2", LIVE_E)) == "MUTATIONS_MISMATCH")
# shape rules of B (all four were accepted by BOTH the revision-4 reference and the candidate-1 schema for at least one case; A2-0054 differential)
check("R5-5 B.profile.name must equal BASE[enum]: a name/enum disagreement is refused", raises(lambda: ref.binding_v2(mutate(E, ["profile", "enum"], "3")), "profile"))
check("R5-5 B.profile.enum 4 is refused", raises(lambda: ref.binding_v2(mutate(E, ["profile", "enum"], "4")), "profile"))
check("R5-5 a mutant name in B.profile is refused (the name is derived, never copied)", raises(lambda: ref.binding_v2(mutate(E, ["profile", "name"], "mutant-no-nonce")), "profile"))
check("R5-6 repaired-f requires interfaceVersion v2 (A1-0105 N3)", raises(lambda: ref.binding_v2(mutate(F, ["interfaceVersion"], "v1")), "interfaceVersion"))
check("R5-6 the synthetic F document carries v2", F["interfaceVersion"] == "v2")
check("R5-6 E accepts v1 (historical manifests) and v2 (successor carriers)", ref.binding_v2(mutate(E, ["interfaceVersion"], "v1")) != "" and ref.binding_v2(mutate(E, ["interfaceVersion"], "v2")) != "")
def dup(doc, which):
    d = copy.deepcopy(doc); w = d["witnessSets"][which]["witnesses"]; w.append(w[0]); return d
check("R5-7 a duplicate witness member is refused", raises(lambda: ref.binding_v2(dup(F, "psc")), "duplicate") and raises(lambda: ref.binding_v2(dup(E, "kssc")), "duplicate"))
check("R5-7 a threshold above the witness count is refused", raises(lambda: ref.binding_v2(mutate(F, ["witnessSets", "kssc", "threshold"], "5")), "threshold"))
check("R5-7 threshold 0 is refused", raises(lambda: ref.binding_v2(mutate(E, ["witnessSets", "psc", "threshold"], "0")), "threshold"))
check("R5-7 threshold 2 of 4 (the q2 control deployment) is accepted", ref.binding_v2(mutate(mutate(mutate(F, ["witnessSets", "psc", "threshold"], "2"), ["witnessSets", "kssc", "threshold"], "2"), ["witnessSets", "governance", "threshold"], "2")) != "")
try:
    emitted = ref.emit()
except Exception as _e:  # noqa: BLE001 - reported as a failed expectation, not a crash (the emitter asserts its own cases)
    emitted = {}
check("R5-8 the vector can be emitted: every manifest-profile case it lists refuses or maps exactly as the function does", bool(emitted))
check("R5-8 the emitted vector carries the closed table and the manifest-profile cases, each equal to the function's result",
      "profileTable" in emitted and "manifestProfileCases" in emitted and all(
          (refusal(lambda c=c: pfm(*c["input"])) == c["expectedRefusal"]) if "expectedRefusal" in c else (pf(*c["input"]) == c["expectedProfile"])
          for c in emitted.get("manifestProfileCases", [])) and len(emitted.get("manifestProfileCases", [])) >= 12)
check("R5-8 the emitted vector carries a mutant document under the base name", "repaired-e-mutant-no-nonce" in emitted.get("documents", {}))
check("R5-8 the emitted F document is the v2 one and its binding is not the revision-4 value e6a14cab..", emitted.get("documents", {}).get("repaired-f", {}).get("document", {}).get("interfaceVersion") == "v2"
      and not emitted.get("documents", {}).get("repaired-f", {}).get("bindingV2", "").startswith("e6a14cab"))
check("R5-8 the emitted E binding is still 242f7ca6..", emitted.get("documents", {}).get("repaired-e", {}).get("bindingV2", "").startswith("242f7ca6977e22c9"))

print("\nFAILED: %d" % len(FAILS) if FAILS else "\nall expectations hold")
sys.exit(1 if FAILS else 0)
