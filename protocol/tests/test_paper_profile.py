"""What agent-2's candidate code does against a PAPER-STRICT deployment (A3-0016 asks agent 2 to review protocol-observable paper expectations).

Paper profiles have no checkpoint, no witness decision and no receipt (A1-0016). Their grants come from the relay-only ACSC.policyEnf path with a zero
recipientKeyHash and a 30 s grant lifetime (assumption A24). These tests MEASURE the candidate's behaviour so the review can name exact exceptions; they do not
claim the paper cases pass.
"""
import json

import pytest

from hmbc_protocol import adapter, wire
from hmbc_protocol.client import UserClient
from hmbc_protocol.relay import Relay
from hmbc_protocol.worker import Worker, WorkerError
import ledger_setup as setup


def call(led, op, inp):
    resp = adapter.handle_line(json.dumps({"schemaVersion": "v1", "operation": op, "input": inp, "deploymentManifest": led.deployment}))
    wire.adapter_response(resp, op)
    return resp


@pytest.fixture
def pinned(world_paper, tmp_path):
    led, ctx = world_paper
    adapter.configure(str(tmp_path / "s"), led.deployment)
    yield led, ctx
    adapter.configure(None)


def paper_grant(led, ctx):
    """Paper flow: user request -> PBC forward -> the configured relay's ACSC.policyEnf (no certificate, no checkpoint)."""
    client = UserClient("alice", led.deployment)
    signed = client.sign_request(setup.make_request(led, ctx, client))
    relay = Relay(led, "relay")
    res = relay.forward(signed, ctx.bundle)
    assert res.code == "NONE", res.code
    fwd = {"pbcRequestId": signed["requestDigest"], "gid": ctx.alice, "dataId": setup.DATA_P1, "action": "1"}
    led.dbc.send(setup.key("relay"), led.ACSC, "policyEnf", fwd, res.records)
    from hmbc_protocol import eip712
    grant_id = "0x" + eip712.grant_id(bytes.fromhex(signed["requestDigest"][2:]), led.KSSC.address, led.dbc.chain_id).hex()
    assert led.dbc.call(led.KSSC, "getGrant", grant_id)[5] is True
    return signed, grant_id


def test_the_deployment_is_really_a_paper_profile(world_paper):
    led, ctx = world_paper
    assert led.pbc.call(led.PSC, "profile") == "0" and led.dbc.call(led.ACSC, "profile") == "0"


@pytest.mark.parametrize("op,inp", [("collect_checkpoint", {}), ("collect_decision", {"requestDigest": "0x" + "11" * 32}), ("attest_grant", {"grantId": "0x" + "11" * 32})])
def test_witness_operations_say_wrong_profile_on_a_paper_deployment(pinned, op, inp):
    led, ctx = pinned
    r = call(led, op, inp)
    assert not r["ok"] and r["error"]["code"] == "WRONG_PROFILE", r


def test_paper_grants_carry_a_zero_recipient_and_a_short_lifetime(world_paper):
    led, ctx = world_paper
    signed, grant_id = paper_grant(led, ctx)
    g = led.dbc.call(led.KSSC, "grantDetails", grant_id)
    assert g["recipientKeyHash"] == "0x" + "00" * 32                                      # the Fig. 6 tuple carries no recipient (A24, S-e)
    now = led.dbc.now()
    assert 0 < int(g["expiresAt"]) - now <= 30
