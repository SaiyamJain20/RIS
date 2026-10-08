import copy

import pytest
from eth_utils import keccak

from hmbc_protocol import symbolic, wire

DOCTOR = "0x" + keccak(text="HMBC.role.Doctor").hex()
ON_DUTY = "0x" + keccak(text="HMBC.role.OnDuty").hex()
# agent-1 A1-0013/A1-0014: keccak256(abi.encode(acsc.policy(DATA_P1))), computed with `cast` and asserted by ledger test
# test_RegisteredPolicyDigestMatchesBoundaryEncoding (origin/agent-1 e6cf4ff).
DATA_P1_POLICY_DIGEST = "0x4bd063e1a4c348bf656f983104839fec2594aaee710b4627e9e46368ba1abc3a"
P1 = {"clauses": [[{"role": DOCTOR, "kind": "1", "issuerMode": "0"}, {"role": ON_DUTY, "kind": "2", "issuerMode": "2"}]]}


def test_policy_digest_equals_agent1_registered_policy_digest():
    assert symbolic.policy_digest(P1) == DATA_P1_POLICY_DIGEST


def test_policy_digest_is_order_and_value_sensitive():
    base = symbolic.policy_digest(P1)
    swapped = {"clauses": [list(reversed(P1["clauses"][0]))]}
    swapped["clauses"][0][0] = {**swapped["clauses"][0][0], "issuerMode": "0"}   # keep it valid (first cannot be SAME_AS_FIRST)
    assert symbolic.policy_digest(swapped) != base
    for path, val in ((("role",), "0x" + "00" * 32), (("kind",), "2"), (("issuerMode",), "1")):
        mutated = copy.deepcopy(P1)
        mutated["clauses"][0][0][path[0]] = val
        assert symbolic.policy_digest(mutated) != base
    two = {"clauses": P1["clauses"] + P1["clauses"]}
    assert symbolic.policy_digest(two) != base


def test_ciphertext_digest_binds_every_field():
    rec = {"dataId": "0x" + "11" * 32, "owner": "0x" + "22" * 20, "payloadDigest": "0x" + "33" * 32}
    base = symbolic.ciphertext_digest(rec, P1)
    for k, v in (("dataId", "0x" + "12" * 32), ("owner", "0x" + "23" * 20), ("payloadDigest", "0x" + "34" * 32)):
        assert symbolic.ciphertext_digest({**rec, k: v}, P1) != base
    other = {"clauses": [[{**P1["clauses"][0][0], "issuerMode": "1"}]]}
    assert symbolic.ciphertext_digest(rec, other) != base
    assert symbolic.ciphertext_digest(rec, P1) == base            # deterministic


def test_invalid_inputs_rejected():
    rec = {"dataId": "0x" + "11" * 32, "owner": "0x" + "22" * 20, "payloadDigest": "0x" + "33" * 32}
    with pytest.raises(wire.WireError):
        symbolic.ciphertext_digest(rec, P1, "1")
    with pytest.raises(wire.WireError):
        symbolic.ciphertext_digest({**rec, "owner": rec["owner"] + "\n"}, P1)
    with pytest.raises(wire.WireError):
        symbolic.policy_digest({"clauses": [[{**P1["clauses"][0][1]}]]})   # SAME_AS_FIRST first
