"""Findings 4, 9 and 11 of the independent review: never sign an ALLOW the DBC will revert; pin the forwarding tx; no assert for a signing check."""
import pytest

from hmbc_protocol import eip712
from hmbc_protocol.client import UserClient
from hmbc_protocol.relay import Relay
from hmbc_protocol.witness import Witness, WitnessError
import ledger_setup as setup


def forward(led, ctx, nonce, ttl=30):
    client = UserClient("alice", led.deployment)
    req = setup.make_request(led, ctx, client, nonce=nonce, ttl=ttl)
    signed = client.sign_request(req)
    assert Relay(led, "relay").forward(signed, ctx.bundle).code == "NONE"
    return signed


def test_a_nonce_the_dbc_already_consumed_is_refused_as_replay(world):
    """Two forwarded requests with the same (gid, nonce) but different digests: after the first is consumed the DBC would revert REPLAY."""
    led, ctx = world
    w, relay = Witness(led), Relay(led, "relay")
    first = forward(led, ctx, "7", ttl=30)
    relay.accept_state(w.checkpoint())
    assert relay.deliver(first, w.decide(first["requestDigest"])) is not None
    second = forward(led, ctx, "7", ttl=20)                                   # expiry 10 s earlier -> different digest, same nonce (not a 1 s coincidence)
    assert second["requestDigest"] != first["requestDigest"]
    relay.accept_state(w.checkpoint())
    with pytest.raises(WitnessError) as e:
        w.decide(second["requestDigest"])
    assert e.value.code == "REPLAY"


def test_credentials_that_lapsed_by_dbc_time_give_a_signed_deny_with_no_records_not_a_reverting_allow(ledger):
    """The checkpoint block is old enough for the 20 s duty entry to be valid there but not at DBC 'now'; DecisionVerifier step 13 checks records at now."""
    from hmbc_protocol import ledger as ledger_mod
    led = ledger_mod.Ledger.from_deployment(ledger.deployment)
    ctx = setup.setup_pbc(led, duty_seconds=20)
    w, relay = Witness(led), Relay(led, "relay")
    signed = forward(led, ctx, "1", ttl=30)
    relay.accept_state(w.checkpoint())                                        # PBC block timestamp t0: duty entry still valid at t0
    setup.advance(led, 22)                                                    # DBC now = t0 + 22: entry lapsed; request (30 s) and checkpoint (60 s) still live
    d = w.decide(signed["requestDigest"])
    assert d["decision"]["result"] == "0" and d["credentialRecords"] == []
    assert d["decision"]["credentialDigest"] == "0x" + eip712.credential_digest([]).hex()
    assert relay.deliver(signed, d) is None                                   # audited denial, not a revert


def test_the_forwarding_transaction_must_have_been_sent_to_the_psc(world, monkeypatch):
    led, ctx = world
    signed = forward(led, ctx, "1")
    Relay(led, "relay").accept_state(Witness(led).checkpoint())
    real = led.pbc.get_transaction
    monkeypatch.setattr(led.pbc, "get_transaction", lambda h: {**real(h), "to": "0x" + "22" * 20})   # e.g. a wrapper contract that called the PSC
    with pytest.raises(WitnessError) as e:
        Witness(led).decide(signed["requestDigest"])
    assert e.value.code == "WRONG_SUBJECT"


def test_a_signature_that_does_not_recover_to_the_witness_is_an_error_not_an_assert(world, monkeypatch):
    led, ctx = world
    w = Witness(led)
    monkeypatch.setattr(eip712, "recover", lambda digest, sig: "0x" + "00" * 20)
    with pytest.raises(WitnessError) as e:
        w.checkpoint()
    assert e.value.code == "BAD_SIGNATURE"


def test_an_expired_request_is_refused_even_though_the_checkpoint_is_still_live(world):
    led, ctx = world
    w, relay = Witness(led), Relay(led, "relay")
    signed = forward(led, ctx, "1", ttl=30)
    relay.accept_state(w.checkpoint())
    setup.advance(led, 31)                                                    # request (30 s) expired; checkpoint (60 s) alive
    with pytest.raises(WitnessError) as e:
        w.decide(signed["requestDigest"])
    assert e.value.code == "EXPIRED"


def finish_flow(led, ctx):
    w, relay = Witness(led), Relay(led, "relay")
    signed = forward(led, ctx, "1")
    relay.accept_state(w.checkpoint())
    grant_id = relay.deliver(signed, w.decide(signed["requestDigest"]))
    relay.report_outcome(signed["requestDigest"], "0x" + "ab" * 32, w.attest_grant(grant_id))
    return w, signed, grant_id


def test_after_an_outcome_is_recorded_decide_says_replay_and_attest_refuses(world):
    led, ctx = world
    w, signed, grant_id = finish_flow(led, ctx)
    with pytest.raises(WitnessError) as e:
        w.decide(signed["requestDigest"])
    assert e.value.code == "REPLAY"                                           # distinct from WRONG_SUBJECT (never forwarded)
    with pytest.raises(WitnessError) as e2:
        w.attest_grant(grant_id)                                              # the PBC record is no longer FORWARDED: no second receipt
    assert e2.value.code == "WRONG_SUBJECT"
