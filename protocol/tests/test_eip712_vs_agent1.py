"""Byte-exact comparison against agent 1's ledger vectors (pinned copies of origin/agent-1 e351be5 and 54262c2).

Three-way check per signed vector: this module's independent encoder, eth_account's encoder, and
the stored Solidity/cast values. Signatures are RFC 6979 deterministic, so equal signature bytes
imply equal digests and the same signer key.
"""
import copy
import hashlib
import json
import pathlib
import re

import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data

from hmbc_protocol import eip712

FIXDIR = pathlib.Path(__file__).parent / "fixtures"
FIXTURES = {  # tag -> (file, sha256 of the byte copy of agent-1's ledger/exports/vectors/eip712-v0-ledger.json)
    "e351be5": ("eip712-agent1-e351be5.json", "6e931f83c53303350d847f61b192d57fe0f9c30f9d815effa57e36c279278cdf"),
    "54262c2": ("eip712-agent1-54262c2.json", "6aa399e038be204a0420e7503f11300196fcaaf4bc7acbaef2724163f8cf0574"),
}
DOCS = {tag: json.loads((FIXDIR / f).read_text()) for tag, (f, _) in FIXTURES.items()}
SIGNED = [dict(v, _tag=tag) for tag, d in DOCS.items() for v in d["vectors"] if "typedData" in v]
IDS = lambda v: f'{v["_tag"]}-{v["name"]}'  # noqa: E731


def hx(b: bytes) -> str:
    return "0x" + b.hex()


@pytest.mark.parametrize("tag", FIXTURES)
def test_fixture_is_the_pinned_agent1_file(tag):
    f, sha = FIXTURES[tag]
    assert hashlib.sha256((FIXDIR / f).read_bytes()).hexdigest() == sha


def test_new_file_only_adds_the_receipt_vector():
    """A1-0011: the 9 earlier vectors are byte-unchanged; GrantReceipt is the only addition."""
    old = {v["name"]: v for v in DOCS["e351be5"]["vectors"]}
    new = {v["name"]: v for v in DOCS["54262c2"]["vectors"]}
    assert set(new) - set(old) == {"GrantReceipt"} and set(old) <= set(new)
    for name, v in old.items():
        assert v == new[name], name


@pytest.mark.parametrize("v", SIGNED, ids=IDS)
def test_digest_components_match(v):
    td = v["typedData"]
    types = {k: x for k, x in td["types"].items() if k != "EIP712Domain"}
    assert hx(eip712.type_hash(td["primaryType"], types)) == v["typeHash"]
    assert hx(eip712.domain_separator(td["domain"])) == v["domainSeparator"]
    assert hx(eip712.struct_hash(td)) == v["structHash"]
    assert hx(eip712.digest(td)) == v["digest"]


@pytest.mark.parametrize("v", SIGNED, ids=IDS)
def test_matches_eth_account_encoder(v):
    td = copy.deepcopy(v["typedData"])
    td["domain"]["chainId"] = int(td["domain"]["chainId"])
    def conv_val(types, t, val):
        if t.endswith("[]"):
            return [conv_val(types, t[:-2], e) for e in val]
        if t in types:
            return {f["name"]: conv_val(types, f["type"], val[f["name"]]) for f in types[t]}
        return int(val) if t.startswith("uint") else val
    def conv(types, name, obj):
        return conv_val(types, name, obj)
    msg = conv(td["types"], td["primaryType"], td["message"])
    signable = encode_typed_data(full_message={**td, "message": msg})
    ea = Account  # noqa: F841 - documents that only eth_account is used here
    from eth_account.messages import _hash_eip191_message
    assert hx(_hash_eip191_message(signable)) == v["digest"]


@pytest.mark.parametrize("v", SIGNED, ids=IDS)
def test_signature_bytes_and_signer_match(v):
    dig = bytes.fromhex(v["digest"][2:])
    assert eip712.sign_digest(v["signerPrivateKey"], dig) == v["signature"]
    assert eip712.recover(dig, v["signature"]) == v["signer"]
    assert Account.from_key(v["signerPrivateKey"]).address.lower() == v["signer"]


def apply_mutation(td, path, value):
    """Apply a mutation path such as 'roles[0]', 'entries[1].gid' or 'domain.chainId'.

    AccessRequest's EIP-712 domain is {chainId: sourceChainId, verifyingContract: psc} (interfaces v0),
    so mutating those message fields also moves the domain, exactly as the Solidity encoder derives it.
    """
    if path.startswith("domain."):
        td["domain"][path.split(".", 1)[1]] = value
        return
    if td["primaryType"] == "AccessRequest" and path in ("sourceChainId", "psc"):
        td["domain"]["chainId" if path == "sourceChainId" else "verifyingContract"] = value
    obj, parts = td["message"], re.findall(r"[^.\[\]]+", path)
    for i, part in enumerate(parts):
        key = int(part) if part.isdigit() else part
        if i == len(parts) - 1:
            obj[key] = value
        else:
            obj = obj[key]


@pytest.mark.parametrize("v", SIGNED, ids=IDS)
def test_every_mutation_changes_digest_and_signer(v):
    base_sig = v["signature"]
    for m in v["mutations"]:
        td = copy.deepcopy(v["typedData"])
        field = m["field"]
        apply_mutation(td, field, m["mutatedValue"])
        d = eip712.digest(td)
        assert hx(d) == m["digest"], (v["name"], field)
        assert hx(d) != v["digest"]
        assert eip712.recover(d, base_sig) == m["recoveredFromBaseSignature"]
        assert eip712.recover(d, base_sig) != v["signer"]


@pytest.mark.parametrize("tag", FIXTURES)
def test_credential_digest_vector_and_mutations(tag):
    cv = next(v for v in DOCS[tag]["vectors"] if "credentialDigest" in v)
    assert hx(eip712.credential_digest(cv["records"])) == cv["credentialDigest"]
    for m in cv["mutations"]:
        recs = copy.deepcopy(cv["records"])
        if "field" in m and m["field"] in recs[0]:
            recs[0][m["field"]] = m["mutatedValue"]
            assert hx(eip712.credential_digest(recs)) == m["digest"]
            assert m["digest"] != cv["credentialDigest"]


def test_credential_set_is_standard_array_encoding():
    cs = next(v for v in SIGNED if v["name"] == "CredentialSet")
    recs = cs["typedData"]["message"]["records"]
    # structHash(CredentialSet) wraps the same array hash that credentialDigest uses
    from eth_utils import keccak
    th = bytes.fromhex(cs["typeHash"][2:])
    assert eip712.struct_hash(cs["typedData"]) == keccak(th + eip712.credential_digest(recs))


def test_rejects_malformed_inputs():
    v = next(x for x in SIGNED if x["name"] == "AccessRequest")
    for field, bad in [("nonce", "-1"), ("nonce", "01"), ("nonce", 1.5), ("expiresAt", str(1 << 64)),
                       ("gid", v["typedData"]["message"]["gid"].upper().replace("0X", "0x")),
                       ("dataId", "0x1234")]:
        td = copy.deepcopy(v["typedData"]); td["message"][field] = bad
        with pytest.raises(eip712.EncodingError):
            eip712.digest(td)
    td = copy.deepcopy(v["typedData"]); td["message"]["extra"] = "1"
    with pytest.raises(eip712.EncodingError):
        eip712.digest(td)
    td = copy.deepcopy(v["typedData"]); del td["message"]["nonce"]
    with pytest.raises(eip712.EncodingError):
        eip712.digest(td)


def test_rejects_noncanonical_signatures():
    v = SIGNED[0]
    dig = bytes.fromhex(v["digest"][2:])
    raw = bytearray(bytes.fromhex(v["signature"][2:]))
    high_s = (eip712.SECP256K1_N - int.from_bytes(raw[32:64], "big")).to_bytes(32, "big")
    twin_v = 55 - raw[64]  # 27 <-> 28: the valid malleated twin (n-s, flipped v)
    flipped = bytes(raw[:32]) + high_s + bytes([twin_v])
    # the twin really is the same key's other valid signature, so only the low-s rule rejects it
    from eth_account import Account as _A
    assert _A._recover_hash(dig, vrs=(twin_v, int.from_bytes(raw[:32], 'big'), int.from_bytes(high_s, 'big'))).lower() == v["signer"]
    with pytest.raises(eip712.EncodingError):
        eip712.recover(dig, "0x" + flipped.hex())
    with pytest.raises(eip712.EncodingError):
        eip712.recover(dig, v["signature"][:-2])           # 64 bytes
    bad_v = bytes(raw[:64]) + bytes([0])
    with pytest.raises(eip712.EncodingError):
        eip712.recover(dig, "0x" + bad_v.hex())


# --- A3-0009 item 3: strict canonical wire validation (written before the fix) -------------------

def _req():
    return copy.deepcopy(next(x for x in SIGNED if x["name"] == "AccessRequest")["typedData"])


@pytest.mark.parametrize("field,bad", [
    ("gid", None), ("dataId", None), ("recipientKeyHash", None),     # final-LF variants built below
])
def test_trailing_newline_rejected_for_address_and_bytes32(field, bad):
    td = _req()
    td["message"][field] = td["message"][field] + "\n"
    with pytest.raises(eip712.EncodingError):
        eip712.digest(td)


def test_trailing_newline_rejected_for_uint_string():
    td = _req()
    td["message"]["nonce"] = td["message"]["nonce"] + "\n"
    with pytest.raises(eip712.EncodingError):
        eip712.digest(td)


@pytest.mark.parametrize("field", ["nonce", "expiresAt", "action", "authEpoch"])
def test_json_integers_rejected_on_the_wire(field):
    """interfaces v0: unsigned integers are decimal STRINGS in JSON; a JSON number must reject."""
    td = _req()
    td["message"][field] = int(td["message"][field])
    with pytest.raises(eip712.EncodingError):
        eip712.digest(td)


def test_domain_fields_are_validated_too():
    td = _req()
    td["domain"]["chainId"] = int(td["domain"]["chainId"])
    with pytest.raises(eip712.EncodingError):
        eip712.digest(td)
    td = _req()
    td["domain"]["verifyingContract"] += "\n"
    with pytest.raises(eip712.EncodingError):
        eip712.digest(td)


def test_signature_hex_must_be_canonical():
    v = SIGNED[0]
    dig = bytes.fromhex(v["digest"][2:])
    for bad in (v["signature"] + "\n", v["signature"].upper().replace("0X", "0x"), v["signature"][2:]):
        with pytest.raises(eip712.EncodingError):
            eip712.recover(dig, bad)


def test_grant_receipt_vector_is_complete_and_consistent():
    """Receipt reproduction at 54262c2: 13 mutations (11 fields + 2 domain), grantId rule, A1-0008 type string."""
    r = next(v for v in SIGNED if v["_tag"] == "54262c2" and v["name"] == "GrantReceipt")
    td = r["typedData"]
    assert eip712.encode_type("GrantReceipt", {k: x for k, x in td["types"].items() if k != "EIP712Domain"}) == (
        "GrantReceipt(bytes32 requestDigest,bytes32 grantId,address gid,bytes32 dataId,uint64 keyEpoch,"
        "uint64 grantExpiresAt,uint64 witnessSetVersion,uint256 dbcChainId,address kssc,uint256 dbcBlockNumber,"
        "bytes32 dbcBlockHash)")
    assert td["domain"]["name"] == "HMBCReceipt" and td["domain"]["version"] == "1"
    assert len(r["mutations"]) == 13
    m = td["message"]
    assert m["grantId"] == hx(eip712.grant_id(bytes.fromhex(m["requestDigest"][2:]), m["kssc"], int(m["dbcChainId"])))
    assert r["signerLabel"] == "witness-1"
