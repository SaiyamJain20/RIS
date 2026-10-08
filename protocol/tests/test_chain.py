"""Chain client against the live repaired-e deployment (agent-1 ledger, pinned commit)."""
import json
import pathlib

import pytest

from hmbc_protocol import abi, chain

ABI_DIR = pathlib.Path(__file__).resolve().parents[1] / "abi"


def contract(ledger, name, side):
    dep = ledger.deployment["chains"][side]["contracts"][name]
    return abi.Contract(json.loads((ABI_DIR / f"{name}.json").read_text()), dep)


def pbc(ledger):
    return chain.Chain(ledger.pbc_url, int(ledger.deployment["chains"]["pbc"]["chainId"]))


def test_call_reads_deployed_state(ledger):
    psc = contract(ledger, "PSC", "pbc")
    assert pbc(ledger).call(psc, "profile") == "2"                     # REPAIRED_E
    assert pbc(ledger).call(psc, "witnessSetVersion") == "1"
    assert pbc(ledger).call(psc, "witnesses") == [ledger.deployment["fixture"]["witnessSet"]["witnesses"][0]]


def test_chain_id_is_checked_against_the_deployment(ledger):
    with pytest.raises(chain.ChainError, match="chain id"):
        chain.Chain(ledger.pbc_url, 1).call(contract(ledger, "PSC", "pbc"), "profile")


def test_call_at_a_past_block_tag_sees_past_state(ledger):
    tmsc = contract(ledger, "TMSC", "pbc")
    c = pbc(ledger)
    head = c.block_number()
    assert c.call(tmsc, "authEpoch", block=head) == c.call(tmsc, "authEpoch")
    with pytest.raises(chain.ChainError):
        c.call(tmsc, "authEpoch", block=head + 1000)                   # a block that does not exist is an error, never "latest"


def test_revert_reason_is_decoded_to_the_ledger_error_name(ledger):
    ksscc = contract(ledger, "KSSC", "dbc")
    dbc = chain.Chain(ledger.dbc_url, int(ledger.deployment["chains"]["dbc"]["chainId"]))
    # a stranger cannot call requestData (only the ACSC may): UNAUTHORIZED_CALLER
    stranger = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"   # Anvil public account 1 (funded, not the ACSC)
    with pytest.raises(chain.Rejected) as e:
        dbc.send(stranger, ksscc, "requestData", {"requestDigest": "0x" + "00" * 32, "dataId": "0x" + "00" * 32, "gid": "0x" + "00" * 20, "keyEpoch": "0",
                                                  "expiresAt": "1", "recipientKeyHash": "0x" + "00" * 32, "consumeNonce": False, "nonce": "0"})
    assert e.value.code == "UNAUTHORIZED_CALLER"


def test_send_mines_a_transaction_and_returns_a_successful_receipt(ledger):
    """A denial is a normal PSC outcome (logged, not reverted), so this transaction mines. Regression: `to` must be checksummed for signing."""
    psc = contract(ledger, "PSC", "pbc")
    c = pbc(ledger)
    dep = ledger.deployment["chains"]
    req = {"sourceChainId": dep["pbc"]["chainId"], "destinationChainId": dep["dbc"]["chainId"], "psc": psc.address,
           "kssc": dep["dbc"]["contracts"]["KSSC"], "gid": "0x" + "22" * 20, "dataId": "0x" + "33" * 32, "action": "1",
           "policyVersion": "1", "authEpoch": "0", "keyEpoch": "0", "nonce": "1", "expiresAt": "1", "recipientKeyHash": "0x" + "44" * 32}
    bundle = {"certificates": [], "temporalClaims": []}
    before = c.block_number()
    rc = c.send("0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d", psc, "requestAccess", req, "0x" + "00" * 65, bundle)
    assert int(rc["status"], 16) == 1 and c.block_number() == before + 1
