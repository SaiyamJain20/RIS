"""PBC leg of the legitimate flow, driven by agent-2's client and relay against the real ledger."""
import pytest

from hmbc_protocol.client import UserClient
from hmbc_protocol.relay import Relay
import ledger_setup as setup


make_request = setup.make_request


def test_setup_registered_alice_with_the_fixture_recipient_key(world):
    led, ctx = world
    assert led.pbc.call(led.TMSC, "authEpoch") == "3"
    assert led.pbc.call(led.RSC, "isRegistered", ctx.alice) is True
    assert led.pbc.call(led.RSC, "recipientKeyHash", ctx.alice) == "0x98d796e3229ebf5c50610744cf35aece58511751e387e8eef569a0117bb07e5d"


def test_legitimate_request_is_forwarded_by_the_pbc(world):
    led, ctx = world
    client = UserClient("alice", led.deployment)
    signed = client.sign_request(make_request(led, ctx, client))
    result = Relay(led, "relay").forward(signed, ctx.bundle)
    assert result.code == "NONE" and result.request_digest == signed["requestDigest"]
    rec = led.pbc.call(led.PSC, "getRequest", result.request_digest)
    assert rec["status"] == "1" and rec["gid"] == ctx.alice and rec["dataId"] == setup.DATA_P1
    assert rec["credentialDigest"] == result.credential_digest
    assert [r["role"] for r in result.records] == [setup.ROLE_DOCTOR, setup.ROLE_ON_DUTY]


@pytest.mark.parametrize("label,over,code", [
    ("expired-at-submission", {"ttl": 0}, "EXPIRED"),
    ("ttl-too-long", {"ttl": 45}, "MALFORMED"),                      # clearly beyond the 30 s limit: 31 would flip with the seconds between building and mining
])
def test_pbc_denials_are_returned_as_codes_not_exceptions(world, label, over, code):
    led, ctx = world
    client = UserClient("alice", led.deployment)
    signed = client.sign_request(make_request(led, ctx, client, **over))
    result = Relay(led, "relay").forward(signed, ctx.bundle)
    assert result.code == code, label
    assert led.pbc.call(led.PSC, "getRequest", result.request_digest)["status"] == "0"


def test_replayed_request_is_denied_replay(world):
    led, ctx = world
    client = UserClient("alice", led.deployment)
    signed = client.sign_request(make_request(led, ctx, client))
    relay = Relay(led, "relay")
    assert relay.forward(signed, ctx.bundle).code == "NONE"
    assert relay.forward(signed, ctx.bundle).code == "REPLAY"
