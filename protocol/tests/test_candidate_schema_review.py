"""Independent review of agent 3's candidate v1 revision 3 wire fixtures (A3-0009 request to agent 2).

Agent 2's own validator (hmbc_protocol.wire, written from A1-0003/A1-0008 and the interface text) gives a
verdict per case; it must agree with agent 3's recorded `valid` flag. The fixture and schema files are byte
copies of origin/agent-3 988e452 (hashes pinned). Disagreements are findings, never silently fixed here.
"""
import hashlib
import json
import pathlib

import pytest

from hmbc_protocol import wire

FIX = pathlib.Path(__file__).parent / "fixtures"
CASES_FILE = FIX / "schema-cases-a3-988e452.json"
SCHEMA_FILE = FIX / "hmbc-schema-candidate-a3-988e452.json"
CASES = json.loads(CASES_FILE.read_text())["cases"]


def test_fixture_copies_are_pinned():
    assert hashlib.sha256(CASES_FILE.read_bytes()).hexdigest() == "49a9dc29298495513340db2f4e4f78d7611e52c7b42409531bc5ed97f421e4d8"
    assert hashlib.sha256(SCHEMA_FILE.read_bytes()).hexdigest() == "6be244335aef3ceffb6977849db8b9013d144a0babf47981cc8a9ec2edf2a14c"
    assert len(CASES) == 68 and sum(c["valid"] for c in CASES) == 12


# Names in agent 3's fixtures that agent 2 does not implement as wire types (file hashes etc.): reported, not skipped silently.
NOT_AGENT2_WIRE = {"FileHash", "TempAclEntry"} - set(wire.VALIDATORS)


@pytest.mark.parametrize("i", range(len(CASES)), ids=lambda i: f"{i:02d}-{CASES[i]['schema']}-{'valid' if CASES[i]['valid'] else 'invalid'}")
def test_agent2_verdict_matches_agent3_fixture(i):
    case = CASES[i]
    if case["schema"] not in wire.VALIDATORS:
        pytest.skip(f"{case['schema']} is not an agent-2 wire type (agent-3 evaluation schema)")
    if case["valid"]:
        wire.validate(case["schema"], case["input"])
    else:
        with pytest.raises(wire.WireError):
            wire.validate(case["schema"], case["input"])


# --- gaps found in agent 3's 68 fixtures: agent 2's own mutations over every valid case ------------------

VALID = [c for c in CASES if c["valid"] and c["schema"] in wire.VALIDATORS]


def _scalar_paths(obj, path=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _scalar_paths(v, path + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _scalar_paths(v, path + (i,))
    else:
        yield path


def _get(obj, path):
    for p in path:
        obj = obj[p]
    return obj


def _set(obj, path, value):
    import copy
    obj = copy.deepcopy(obj)
    parent = _get(obj, path[:-1]) if len(path) > 1 else obj
    parent[path[-1]] = value
    return obj


@pytest.mark.parametrize("case", VALID, ids=lambda c: c["schema"] + "-" + str(CASES.index(c)))
def test_every_scalar_rejects_noncanonical_forms(case):
    n = 0
    top = not isinstance(case["input"], (dict, list))  # Signature/Address/Hash cases are bare strings
    for path in [()] if top else _scalar_paths(case["input"]):
        val = case["input"] if top else _get(case["input"], path)
        variants = [val + "\n", " " + val]
        if val.startswith("0x"):
            variants.append("0x" + val[2:].upper()) if any(ch.isalpha() for ch in val[2:]) else None
        if val.isdigit():
            variants += [int(val), val + ".0", "0" + val if val != "0" else "00", "-" + val if val != "0" else "-0"]
        for bad in variants:
            if bad is None:
                continue
            with pytest.raises(wire.WireError):
                wire.validate(case["schema"], bad if top else _set(case["input"], path, bad))
            n += 1
    assert n > 0


def test_ordering_rules_reject_swaps_duplicates():
    import copy
    by = {c["schema"]: c["input"] for c in VALID}
    rc = copy.deepcopy(by["RoleCertificate"])
    if len(rc["roles"]) >= 2:
        for bad in (rc["roles"][::-1], [rc["roles"][0], rc["roles"][0]]):
            with pytest.raises(wire.WireError):
                wire.validate("RoleCertificate", {**rc, "roles": bad})
    rl = copy.deepcopy(by["RevocationList"])
    for bad in (["9", "3"], ["3", "3"], ["10", "9"]):
        with pytest.raises(wire.WireError):
            wire.validate("RevocationList", {**rl, "revokedSerials": bad})
    wire.validate("RevocationList", {**rl, "revokedSerials": ["9", "10"]})  # numeric, not lexicographic, order
    ta = copy.deepcopy(by["TemporalAcl"])
    assert len(ta["entries"]) >= 2
    for bad in (ta["entries"][::-1], [ta["entries"][0], ta["entries"][0]]):
        with pytest.raises(wire.WireError):
            wire.validate("TemporalAcl", {**ta, "entries": bad})
    cb = copy.deepcopy(by["CredentialBundle"])
    if len(cb["certificates"]) >= 2:
        with pytest.raises(wire.WireError):
            wire.validate("CredentialBundle", {**cb, "certificates": cb["certificates"][::-1]})
    if len(cb["temporalClaims"]) >= 2:
        with pytest.raises(wire.WireError):
            wire.validate("CredentialBundle", {**cb, "temporalClaims": cb["temporalClaims"][::-1]})
    cr = copy.deepcopy(by["CredentialRecords"])
    if len(cr) >= 2:
        with pytest.raises(wire.WireError):
            wire.validate("CredentialRecords", cr[::-1])
    # a temporal-only bundle stays structurally valid (A3-0006); a certificate-less, claim-less bundle does not
    wire.validate("CredentialBundle", {"certificates": [], "temporalClaims": cb["temporalClaims"]})
    with pytest.raises(wire.WireError):
        wire.validate("CredentialBundle", {"certificates": [], "temporalClaims": []})


def test_signature_canonicality_edge_cases():
    sig = next(c["input"] for c in VALID if c["schema"] == "Signature")
    r, s, v = sig[2:66], int(sig[66:130], 16), sig[130:]
    n = wire.SECP256K1_N
    high = "0x" + r + format(n - s, "064x") + v
    zero_r = "0x" + "00" * 32 + sig[66:]
    r_eq_n = "0x" + format(n, "064x") + sig[66:]
    bad_v = "0x" + r + sig[66:130] + "1d"
    for bad in (high, zero_r, r_eq_n, bad_v):
        with pytest.raises(wire.WireError):
            wire.validate("Signature", bad)
    wire.validate("Signature", sig)
