import copy
import json
import pathlib

import pytest

from hmbc_protocol import eip712, keys, messages

FIX = pathlib.Path(__file__).parent / "fixtures"
DOC = json.loads((FIX / "eip712-agent1-54262c2.json").read_text())
VECS = {v["name"]: v for v in DOC["vectors"] if "typedData" in v}


ALL_BUILDERS = ["AccessRequest", "AccessDecision", "StateCheckpoint", "GrantReceipt", "Registration", "RoleCertificate", "RevocationList", "TemporalAcl"]


@pytest.mark.parametrize("name", ALL_BUILDERS)
def test_builder_reproduces_producer_vector(name):
    v = VECS[name]
    td = v["typedData"]
    built = messages.typed_data(name, td["message"], td["domain"])
    assert built["types"] == td["types"]                       # exact field order, including nested struct types
    assert "0x" + eip712.digest(built).hex() == v["digest"]


def test_synthetic_key_derivation_matches_agent1_fixture_signers():
    for label, vec in (("alice", "AccessRequest"), ("witness-1", "AccessDecision")):
        _, addr = keys.resolve(f"keyref:{'user' if label == 'alice' else 'witness'}:{label}", ("user", "witness"))
        assert addr == VECS[vec]["signer"]
        assert keys.synthetic_private_key(label) == VECS[vec]["signerPrivateKey"]


@pytest.mark.parametrize("bad", ["alice", "keyref:user:", "keyref:user:Alice", "keyref:root:alice",
                                 "keyref:user:alice\n", "keyref:user:../alice", None, 7])
def test_bad_key_refs_rejected(bad):
    with pytest.raises(keys.KeyRefError):
        keys.parse(bad)


def test_role_confusion_rejected():
    with pytest.raises(keys.KeyRefError):
        keys.resolve("keyref:witness:witness-1", ("user",))


def test_domain_comes_from_deployment_not_caller():
    dep = {"chains": {"pbc": {"chainId": "18545", "contracts": {"PSC": "0x" + "11" * 20, "RSC": "0x" + "22" * 20}},
                      "dbc": {"chainId": "28545", "contracts": {"KSSC": "0x" + "33" * 20}}}}
    msg = copy.deepcopy(VECS["AccessDecision"]["typedData"]["message"])
    assert messages.domain_for("AccessDecision", msg, dep) == {
        "name": "HMBCDecision", "version": "1", "chainId": "28545", "verifyingContract": "0x" + "33" * 20}
    assert messages.domain_for("GrantReceipt", msg, dep)["verifyingContract"] == "0x" + "11" * 20


# A1-0015: fixture convention recipientKeyHash = keccak256("HMBC.recipient-key." || label); a commitment to a SYMBOLIC
# recipient key in E (G0 replaces it with a hash of a real public key). Values below are agent-1's `cast keccak` results.
@pytest.mark.parametrize("label,expected", [
    ("alice", "0x98d796e3229ebf5c50610744cf35aece58511751e387e8eef569a0117bb07e5d"),
    ("bob", "0x5fe346cd69926d7120dff3cc020f4d36ad8093b7c9bb95c6ecea9705a3f8c537"),
])
def test_recipient_key_hash_matches_agent1_fixture_convention(label, expected):
    assert keys.recipient_key_hash(f"keyref:user:{label}") == expected


def test_recipient_key_hash_matches_the_registration_and_request_vectors():
    alice = keys.recipient_key_hash("keyref:user:alice")
    for name in ("Registration", "AccessRequest"):
        assert VECS[name]["typedData"]["message"]["recipientKeyHash"] == alice


@pytest.mark.parametrize("bad", ["keyref:witness:witness-1", "alice", "keyref:user:Alice", "keyref:user:alice\n", None])
def test_recipient_key_hash_only_for_user_refs(bad):
    with pytest.raises(keys.KeyRefError):
        keys.recipient_key_hash(bad)
