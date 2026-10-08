"""Honest witness against the live repaired-e ledger: it recomputes facts from PBC state and never trusts the relay."""
import pytest
from eth_account import Account

from hmbc_protocol import eip712, keys, messages
from hmbc_protocol.client import UserClient
from hmbc_protocol.relay import Relay
from hmbc_protocol.witness import Witness, WitnessError
import ledger_setup as setup

OUTCOME = "0x" + "ab" * 32


def forwarded(led, ctx, nonce="1", ttl=30, client=None):
    client = client or UserClient("alice", led.deployment)
    signed = client.sign_request(setup.make_request(led, ctx, client, nonce=nonce, ttl=ttl))
    res = Relay(led, "relay").forward(signed, ctx.bundle)
    assert res.code == "NONE", res.code
    return signed, res


def addr_of(label):
    return Account.from_key(keys.synthetic_private_key(label)).address.lower()


def test_checkpoint_covers_the_latest_pbc_state_and_is_accepted_by_the_dbc(world):
    led, ctx = world
    w, relay = Witness(led), Relay(led, "relay")
    cp = w.checkpoint()
    c = cp["checkpoint"]
    head = led.pbc.get_block()
    assert (c["sequence"], c["authEpoch"], c["keyEpoch"], c["witnessSetVersion"], c["policyVersion"]) == ("1", "3", "0", "1", "1")
    assert (c["sourceBlockNumber"], c["sourceBlockHash"]) == (str(head["number"]), head["hash"])
    assert c["psc"] == led.PSC.address and c["sourceChainId"] == str(led.pbc.chain_id)
    dig = messages.digest_of("StateCheckpoint", c, messages.domain_for("StateCheckpoint", c, led.deployment))
    assert eip712.recover(dig, cp["signatures"][0]) == addr_of("witness-1")
    relay.accept_state(cp)
    exists, cur = led.dbc.call(led.KSSC, "currentCheckpoint")
    assert exists is True and cur["sequence"] == "1" and cur["authEpoch"] == "3"
    assert int(c["expiresAt"]) - led.dbc.get_block()["timestamp"] <= 60                      # checkpoint TTL bound (D10)


def test_next_checkpoint_sequence_comes_from_the_dbc_not_the_caller(world):
    led, ctx = world
    w, relay = Witness(led), Relay(led, "relay")
    relay.accept_state(w.checkpoint())
    cp2 = w.checkpoint()
    assert cp2["checkpoint"]["sequence"] == "2"


def test_full_legitimate_flow_request_decision_grant_receipt_outcome(world):
    led, ctx = world
    w, relay = Witness(led), Relay(led, "relay")
    signed, res = forwarded(led, ctx)
    relay.accept_state(w.checkpoint())
    d = w.decide(signed["requestDigest"])
    dec = d["decision"]
    assert dec["result"] == "1" and dec["stateSequence"] == "1" and dec["credentialDigest"] == res.credential_digest
    assert dec["requestDigest"] == signed["requestDigest"] and int(dec["expiresAt"]) <= int(signed["request"]["expiresAt"])
    assert d["credentialRecords"] == res.records                                              # witness re-derived exactly what the PBC committed
    grant_id = relay.deliver(signed, d)
    assert grant_id == "0x" + eip712.grant_id(bytes.fromhex(signed["requestDigest"][2:]), led.KSSC.address, led.dbc.chain_id).hex()
    g = led.dbc.call(led.KSSC, "getGrant", grant_id)
    assert g[5] is True and g[0] == signed["requestDigest"] and g[1] == setup.DATA_P1 and g[2] == ctx.alice and g[3] == "0"
    receipt = w.attest_grant(grant_id)
    r = receipt["receipt"]
    assert (r["grantId"], r["requestDigest"], r["gid"], r["dataId"], r["keyEpoch"], r["witnessSetVersion"]) == (
        grant_id, signed["requestDigest"], ctx.alice, setup.DATA_P1, "0", "1")
    assert r["grantExpiresAt"] == g[4] and r["kssc"] == led.KSSC.address and r["dbcChainId"] == str(led.dbc.chain_id)
    blk = led.dbc.get_block(int(r["dbcBlockNumber"]))
    assert blk["hash"] == r["dbcBlockHash"]                                                   # the observed block, not a made-up one
    relay.report_outcome(signed["requestDigest"], OUTCOME, receipt)
    assert led.pbc.call(led.PSC, "getRequest", signed["requestDigest"])["status"] == "2"      # OUTCOME_RECORDED


def test_decide_for_a_digest_the_pbc_never_forwarded_is_refused(world):
    led, ctx = world
    Relay(led, "relay").accept_state(Witness(led).checkpoint())
    with pytest.raises(WitnessError) as e:
        Witness(led).decide("0x" + "99" * 32)
    assert e.value.code == "WRONG_SUBJECT"


def test_decide_for_a_pbc_denied_request_is_refused(world):
    led, ctx = world
    client = UserClient("alice", led.deployment)
    signed = client.sign_request(setup.make_request(led, ctx, client, ttl=0))                 # expired at submission: PBC denies
    assert Relay(led, "relay").forward(signed, ctx.bundle).code == "EXPIRED"
    Relay(led, "relay").accept_state(Witness(led).checkpoint())
    with pytest.raises(WitnessError) as e:
        Witness(led).decide(signed["requestDigest"])
    assert e.value.code == "WRONG_SUBJECT"


def test_decide_without_any_dbc_checkpoint_is_stale_state(world):
    led, ctx = world
    signed, _ = forwarded(led, ctx)
    with pytest.raises(WitnessError) as e:
        Witness(led).decide(signed["requestDigest"])
    assert e.value.code == "STALE_STATE"


def test_checkpoint_older_than_the_request_is_stale_state(world):
    led, ctx = world
    w, relay = Witness(led), Relay(led, "relay")
    relay.accept_state(w.checkpoint())                                                       # covers PBC state BEFORE the request
    signed, _ = forwarded(led, ctx)
    with pytest.raises(WitnessError) as e:
        w.decide(signed["requestDigest"])
    assert e.value.code == "STALE_STATE"
    relay.accept_state(w.checkpoint())                                                       # one re-collection per new checkpoint (D24)
    assert w.decide(signed["requestDigest"])["decision"]["stateSequence"] == "2"


def test_revocation_after_forwarding_makes_the_old_request_stale_not_allowed(world):
    led, ctx = world
    w, relay = Witness(led), Relay(led, "relay")
    signed, _ = forwarded(led, ctx)
    acl2 = {**ctx.acl, "version": "2", "entries": []}                                         # H1 removes Alice from duty on the PBC
    led.pbc.send(setup.key("H1-ca-admin"), led.TMSC, "updateTemporalAcl", acl2, setup.sign("TemporalAcl", acl2, led.deployment, "H1-root"))
    relay.accept_state(w.checkpoint())                                                       # DBC learns the revocation: authEpoch 4
    assert led.dbc.call(led.KSSC, "currentCheckpoint")[1]["authEpoch"] == "4"
    with pytest.raises(WitnessError) as e:
        w.decide(signed["requestDigest"])
    assert e.value.code == "STALE_STATE"                                                     # request.authEpoch 3 != checkpoint 4: never an ALLOW


def test_credentials_that_lapse_before_the_checkpoint_yield_a_signed_deny_and_no_grant(ledger):
    from hmbc_protocol import ledger as ledger_mod
    led = ledger_mod.Ledger.from_deployment(ledger.deployment)
    ctx = setup.setup_pbc(led, duty_seconds=20)
    w, relay = Witness(led), Relay(led, "relay")
    signed, _ = forwarded(led, ctx, ttl=30)
    setup.advance(led, 22)                                                                    # duty entry lapses, request still live
    relay.accept_state(w.checkpoint())
    d = w.decide(signed["requestDigest"])
    assert d["decision"]["result"] == "0" and d["credentialRecords"] == []
    assert relay.deliver(signed, d) is None                                                   # valid DENY: audited by the DBC, never a grant
    gid = "0x" + eip712.grant_id(bytes.fromhex(signed["requestDigest"][2:]), led.KSSC.address, led.dbc.chain_id).hex()
    assert led.dbc.call(led.KSSC, "getGrant", gid)[5] is False


def test_attest_unknown_or_denied_grant_is_not_committed(world):
    led, ctx = world
    with pytest.raises(WitnessError) as e:
        Witness(led).attest_grant("0x" + "55" * 32)
    assert e.value.code == "NOT_COMMITTED"


def test_a_key_outside_the_configured_witness_set_is_refused(world):
    led, ctx = world
    with pytest.raises(WitnessError) as e:
        Witness(led, key_label="witness-2")
    assert e.value.code == "UNKNOWN_AUTHORITY"


def test_an_expired_dbc_checkpoint_is_stale_state(world):
    led, ctx = world
    w, relay = Witness(led), Relay(led, "relay")
    signed, _ = forwarded(led, ctx)
    relay.accept_state(w.checkpoint())
    setup.advance(led, 61)                                                                    # past the 60 s checkpoint TTL (and the 30 s request TTL)
    with pytest.raises(WitnessError) as e:
        w.decide(signed["requestDigest"])
    assert e.value.code == "STALE_STATE"                                                      # the checkpoint check fires first, not the later request-expiry check
