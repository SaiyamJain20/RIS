"""SPIKE (test-only) for agent 1's option (c) on open decision X-1 (A1-0021): in a paper profile the worker binds a release to the requesting GID's REGISTERED
recipient key, read from the PBC (RSC.recipientKeyHash(grant.gid)), mirroring HMBC III-D3 ("the PSC sends the response to the user, encrypted with the user's public key").

PRODUCTION CODE DOES NOT DO THIS: hmbc_protocol.worker still refuses paper grants (zero recipient). The decision is agent 3's. This file only MEASURES whether option (c) fits the
worker's evidence model (events, send-attempt counts, cached token, expiry, completion binding) so agent 1's question can be answered with evidence, via a subclass that
overrides the single seam `Worker._recipient_for`.
"""
import pytest

from hmbc_protocol import eip712, keys
from hmbc_protocol.client import UserClient
from hmbc_protocol.relay import Relay
from hmbc_protocol.worker import SimulatedCrash, Worker, WorkerError
import ledger_setup as setup
from test_paper_profile import paper_grant
from test_worker import P1_POLICY, P1_RECORD
from test_witness_policy import register_bob


class PaperModeWorker(Worker):
    """Option (c): in a paper deployment the response is bound to RSC.recipientKeyHash(grant.gid); the DBC grant itself carries none (A24)."""

    def _recipient_for(self, g):
        led = self.led
        if led.pbc.call(led.PSC, "profile") == "2":
            return super()._recipient_for(g)                                   # repaired-e is unchanged
        registered = led.pbc.call(led.RSC, "recipientKeyHash", g["gid"])
        if int(registered, 16) == 0:
            raise WorkerError("WRONG_SUBJECT", "the grant's GID has no registered recipient key")
        return registered


def make(led, tmp_path, **kw):
    return PaperModeWorker(led, tmp_path / "state", clock=led.dbc.now, **kw)


def test_paper_release_bound_to_the_registered_key_fits_the_evidence_model(world_paper, tmp_path):
    led, ctx = world_paper
    signed, grant_id = paper_grant(led, ctx)
    w = make(led, tmp_path)
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    resp = w.release(grant_id)
    assert resp["recipientKeyHash"] == keys.recipient_key_hash("keyref:user:alice") != "0x" + "00" * 32     # the registered key, not the grant's zero
    again = w.release(grant_id)
    assert again == resp                                                                                 # same cached response
    assert [e["type"] for e in w.events()] == ["RELEASE_INTENT", "RELEASE_SENT", "RELEASE_SENT"]          # intent once, one record per attempt
    st = w.status(grant_id)
    assert (st["delivery"], st["sendAttempts"]) == ("unknown", 2)
    assert w.finish_decryption(resp, "keyref:user:alice")["decryptable"] is True
    with pytest.raises(WorkerError) as e:
        w.finish_decryption(resp, "keyref:user:bob")
    assert e.value.code == "WRONG_SUBJECT"


def test_crash_counts_and_expiry_are_the_same_as_in_repaired_e(world_paper, tmp_path):
    led, ctx = world_paper
    _, grant_id = paper_grant(led, ctx)
    sent = []
    w = make(led, tmp_path, faults={"crash_after_send"})
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    with pytest.raises(SimulatedCrash):
        w.release(grant_id, transmit=sent.append)
    restarted = make(led, tmp_path)
    resp = restarted.release(grant_id, transmit=sent.append)
    assert sent[0] == sent[1] == resp
    assert [e["type"] for e in restarted.events()] == ["RELEASE_INTENT", "RELEASE_SENT", "RELEASE_SENT"]     # 1 intent, 2 attempts after a send crash
    assert restarted.status(grant_id)["delivery"] == "unknown"
    setup.advance(led, 40)                                                                                   # paper grant lifetime is ~30 s from the policyEnf block
    n = len(restarted.events())
    with pytest.raises(WorkerError) as e:
        restarted.release(grant_id)
    assert e.value.code == "EXPIRED" and len(restarted.events()) == n                                        # no new event, no new token


def test_the_binding_follows_the_RELAY_ASSERTED_gid_so_the_spec_gap_stays_visible(world_paper, tmp_path):
    """E01 subject substitution (paper): the relay puts Bob's gid in the policyEnf tuple for Alice's request. The release is then bound to BOB's registered key."""
    led, ctx = world_paper
    bundle_bob = register_bob(led)
    client = UserClient("alice", led.deployment)
    signed = client.sign_request(setup.make_request(led, ctx, client))
    relay = Relay(led, "relay")
    res = relay.forward(signed, ctx.bundle)
    assert res.code == "NONE"
    bob = setup.addr("bob")
    led.dbc.send(setup.key("relay"), led.ACSC, "policyEnf", {"pbcRequestId": signed["requestDigest"], "gid": bob, "dataId": setup.DATA_P1, "action": "1"}, res.records)
    grant_id = "0x" + eip712.grant_id(bytes.fromhex(signed["requestDigest"][2:]), led.KSSC.address, led.dbc.chain_id).hex()
    g = led.dbc.call(led.KSSC, "getGrant", grant_id)
    if not g[5]:
        pytest.skip("the paper DBC policy rejected the substituted tuple (Bob lacks Doctor/OnDuty); nothing to release")
    w = make(led, tmp_path)
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    resp = w.release(grant_id)
    assert resp["recipientKeyHash"] == keys.recipient_key_hash("keyref:user:bob")
    assert w.finish_decryption(resp, "keyref:user:bob")["decryptable"] is True                                # the substituted subject completes
    with pytest.raises(WorkerError):
        w.finish_decryption(resp, "keyref:user:alice")                                                      # the real requester cannot


def test_an_unregistered_gid_gets_a_grant_but_no_release(world_paper, tmp_path):
    """E01 forged tuple (paper): a grant for a GID nobody registered exists on the DBC, but the worker refuses to release (no registered key)."""
    led, ctx = world_paper
    ghost = "0x" + "ab" * 20
    fwd = {"pbcRequestId": "0x" + "cd" * 32, "gid": ghost, "dataId": setup.DATA_P1, "action": "1"}
    records = [{"issuer": ctx.h1, "role": setup.ROLE_DOCTOR, "kind": "1", "serial": "101", "anchorVersion": "1", "validUntil": "2100000000"},
               {"issuer": ctx.h1, "role": setup.ROLE_ON_DUTY, "kind": "2", "serial": "0", "anchorVersion": "1", "validUntil": str(led.dbc.now() + 3600)}]
    led.dbc.send(setup.key("relay"), led.ACSC, "policyEnf", fwd, records)
    grant_id = "0x" + eip712.grant_id(bytes.fromhex("cd" * 32), led.KSSC.address, led.dbc.chain_id).hex()
    assert led.dbc.call(led.KSSC, "getGrant", grant_id)[5] is True                                           # the paper DBC authorises the forged tuple (SPEC_GAP)
    w = make(led, tmp_path)
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    with pytest.raises(WorkerError) as e:
        w.release(grant_id)
    assert e.value.code == "WRONG_SUBJECT" and w.events() == []
