"""A1-0017: the witness must evaluate the DBC policy too. A subject with VALID credentials that do not satisfy the record's policy
(fixture Bob, a Researcher) must get a signed DENY that the DBC audits, not a signed ALLOW that makes consumeDecision revert POLICY_DENIED."""
import pytest
from eth_utils import keccak

from hmbc_protocol import keys
from hmbc_protocol.chain import Rejected
from hmbc_protocol.client import UserClient
from hmbc_protocol.relay import Relay
from hmbc_protocol.witness import Witness
import ledger_setup as setup

ROLE_RESEARCHER = "0x" + keccak(text="HMBC.role.Researcher").hex()


def register_bob(led):
    dep, t = led.deployment, led.pbc.get_block()["timestamp"]
    bob, h2 = setup.addr("bob"), setup.addr("H2-root")
    cert = {"issuer": h2, "gid": bob, "roles": [ROLE_RESEARCHER], "serial": "201", "validFrom": "1700000000", "validUntil": "2100000000"}
    signed_cert = {"cert": cert, "signature": setup.sign("RoleCertificate", cert, dep, "H2-root")}
    from hmbc_protocol import messages
    cert_digest = "0x" + messages.digest_of("RoleCertificate", cert, messages.domain_for("RoleCertificate", cert, dep)).hex()
    reg = {"gid": bob, "certDigest": cert_digest, "recipientKeyHash": keys.recipient_key_hash("keyref:user:bob"), "expiresAt": str(t + 600)}
    led.pbc.send(setup.key("relay"), led.RSC, "register", reg, setup.sign("Registration", reg, dep, "bob"), signed_cert)
    return {"certificates": [signed_cert], "temporalClaims": []}


def test_valid_credentials_that_fail_the_dbc_policy_yield_a_signed_deny_the_dbc_audits(world):
    led, ctx = world
    bundle = register_bob(led)
    client = UserClient("bob", led.deployment)
    signed = client.sign_request(setup.make_request(led, ctx, client))
    relay, w = Relay(led, "relay"), Witness(led)
    assert relay.forward(signed, bundle).code == "NONE"                      # the PBC accepts Bob's credentials: they ARE valid
    relay.accept_state(w.checkpoint())
    d = w.decide(signed["requestDigest"])
    assert d["decision"]["result"] == "0"                                    # but the DBC policy needs Doctor AND OnDuty
    assert len(d["credentialRecords"]) == 1                                  # the valid Researcher record is still attested, not hidden
    logs_before = int(led.dbc.call(led.ACSC, "accessLogCount"))
    assert relay.deliver(signed, d) is None                                  # a valid DENY: no grant, and NO revert
    assert int(led.dbc.call(led.ACSC, "accessLogCount")) == logs_before + 1  # the DBC wrote its own denial audit record (Table 3 accessLog)


def test_the_ledger_still_reverts_a_forged_allow_for_that_subject(world):
    """Defence in depth stays: if a faulty/deviating witness signed ALLOW for Bob, ACSC reverts POLICY_DENIED with no state change."""
    led, ctx = world
    bundle = register_bob(led)
    client = UserClient("bob", led.deployment)
    signed = client.sign_request(setup.make_request(led, ctx, client))
    relay, w = Relay(led, "relay"), Witness(led)
    assert relay.forward(signed, bundle).code == "NONE"
    relay.accept_state(w.checkpoint())
    d = w.decide(signed["requestDigest"])
    forged = {**d["decision"], "result": "1"}
    from hmbc_protocol import messages, eip712
    dig = messages.digest_of("AccessDecision", forged, messages.domain_for("AccessDecision", forged, led.deployment))
    forged_bundle = {"decision": forged, "signatures": [eip712.sign_digest(setup.key("witness-1"), dig)], "credentialRecords": d["credentialRecords"]}
    with pytest.raises(Rejected) as e:
        relay.deliver(signed, forged_bundle)
    assert e.value.code == "POLICY_DENIED"


def test_alice_still_gets_an_allow(world):
    led, ctx = world
    client = UserClient("alice", led.deployment)
    signed = client.sign_request(setup.make_request(led, ctx, client))
    relay, w = Relay(led, "relay"), Witness(led)
    assert relay.forward(signed, ctx.bundle).code == "NONE"
    relay.accept_state(w.checkpoint())
    assert w.decide(signed["requestDigest"])["decision"]["result"] == "1"
