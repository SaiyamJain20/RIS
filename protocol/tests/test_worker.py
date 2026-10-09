"""Durable key worker (symbolic mode) against the live repaired-e ledger."""
import sqlite3

import pytest
from eth_utils import keccak

from hmbc_protocol import eip712, keys
from hmbc_protocol.client import UserClient
from hmbc_protocol.relay import Relay
from hmbc_protocol.witness import Witness
from hmbc_protocol.worker import SimulatedCrash, Worker, WorkerError
import ledger_setup as setup

P1_POLICY = {"clauses": [[{"role": setup.ROLE_DOCTOR, "kind": "1", "issuerMode": "0"}, {"role": setup.ROLE_ON_DUTY, "kind": "2", "issuerMode": "2"}]]}
P1_POLICY_DIGEST = "0x4bd063e1a4c348bf656f983104839fec2594aaee710b4627e9e46368ba1abc3a"      # agent-1 A1-0013/A1-0014
H2_ROOT = setup.addr("H2-root")                                                              # data owner in the fixture
P1_RECORD = {"dataId": setup.DATA_P1, "owner": H2_ROOT, "payloadDigest": "0x" + keccak(text="synthetic payload P1").hex()}


def grant(led, ctx, nonce="1"):
    """Legitimate flow up to an issued DBC grant; returns (signed request, grant id)."""
    client = UserClient("alice", led.deployment)
    signed = client.sign_request(setup.make_request(led, ctx, client, nonce=nonce))
    relay, w = Relay(led, "relay"), Witness(led)
    assert relay.forward(signed, ctx.bundle).code == "NONE"
    relay.accept_state(w.checkpoint())
    return signed, relay.deliver(signed, w.decide(signed["requestDigest"]))


def worker(led, tmp_path, **kw):
    return Worker(led, tmp_path / "state", clock=led.dbc.now, **kw)


def rows(tmp_path, sql):
    con = sqlite3.connect(tmp_path / "state" / "worker.sqlite")
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


# --- encrypt_record ------------------------------------------------------------------------------------------------------------

def test_encrypt_record_commits_to_the_registered_policy(world, tmp_path):
    led, ctx = world
    r = worker(led, tmp_path).encrypt_record(P1_RECORD, P1_POLICY, "0")
    assert r["policyDigest"] == P1_POLICY_DIGEST and r["dataId"] == setup.DATA_P1 and r["keyEpoch"] == "0"
    from hmbc_protocol import symbolic
    assert r["ciphertextDigest"] == symbolic.ciphertext_digest(P1_RECORD, P1_POLICY)


@pytest.mark.parametrize("label,record,policy", [
    ("unregistered dataId", {**P1_RECORD, "dataId": "0x" + "77" * 32}, P1_POLICY),
    ("wrong owner", {**P1_RECORD, "owner": setup.addr("alice")}, P1_POLICY),
    ("policy differs from the ACSC's", P1_RECORD, {"clauses": [[{**P1_POLICY["clauses"][0][0]}]]}),
])
def test_encrypt_record_rejects_what_disagrees_with_the_registered_acsc_entry(world, tmp_path, label, record, policy):
    led, ctx = world
    with pytest.raises(WorkerError) as e:
        worker(led, tmp_path).encrypt_record(record, policy, "0")
    assert e.value.code == "WRONG_SUBJECT", label


def test_reencrypting_the_same_record_is_idempotent_but_a_conflicting_payload_is_refused(world, tmp_path):
    led, ctx = world
    w = worker(led, tmp_path)
    first = w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    assert w.encrypt_record(P1_RECORD, P1_POLICY, "0") == first
    with pytest.raises(WorkerError) as e:
        w.encrypt_record({**P1_RECORD, "payloadDigest": "0x" + "00" * 31 + "01"}, P1_POLICY, "0")
    assert e.value.code == "WRONG_SUBJECT"


def test_a_registered_record_survives_a_worker_restart(world, tmp_path):
    led, ctx = world
    first = worker(led, tmp_path).encrypt_record(P1_RECORD, P1_POLICY, "0")
    assert worker(led, tmp_path).encrypt_record(P1_RECORD, P1_POLICY, "0") == first


# --- release -------------------------------------------------------------------------------------------------------------------

def test_release_needs_a_committed_grant(world, tmp_path):
    led, ctx = world
    w = worker(led, tmp_path)
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    with pytest.raises(WorkerError) as e:
        w.release("0x" + "55" * 32)
    assert e.value.code == "NOT_COMMITTED"


def test_release_needs_a_record_registered_with_the_worker(world, tmp_path):
    led, ctx = world
    signed, grant_id = grant(led, ctx)
    with pytest.raises(WorkerError) as e:
        worker(led, tmp_path).release(grant_id)
    assert e.value.code == "WRONG_SUBJECT"


def test_release_persists_intent_before_transmitting_and_binds_every_field(world, tmp_path):
    led, ctx = world
    signed, grant_id = grant(led, ctx)
    w = worker(led, tmp_path)
    enc = w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    seen = {}

    def transmit(resp):
        seen["intent_rows_at_send_time"] = rows(tmp_path, "select grant_id, delivery from releases")          # a SECOND connection: must already be durable
        seen["events_at_send_time"] = [r[0] for r in rows(tmp_path, "select type from events order by id")]   # write-ahead: intent AND this attempt

    resp = w.release(grant_id, transmit=transmit)
    assert seen["intent_rows_at_send_time"] == [(grant_id, "unknown")] and seen["events_at_send_time"] == ["RELEASE_INTENT", "RELEASE_SENT"]
    g = led.dbc.call(led.KSSC, "grantDetails", grant_id)
    assert resp == {"schemaVersion": "v1", "adapterMode": "symbolic", "requestDigest": signed["requestDigest"], "grantId": grant_id,
                    "dataId": setup.DATA_P1, "ciphertextDigest": enc["ciphertextDigest"], "recipientKeyHash": g["recipientKeyHash"],
                    "keyEpoch": "0", "responseEnvelope": {"kind": "symbolic-partial/v1", "token": resp["responseEnvelope"]["token"]}}
    assert resp["recipientKeyHash"] == keys.recipient_key_hash("keyref:user:alice")
    assert len(bytes.fromhex(resp["responseEnvelope"]["token"][2:])) == 32 and int(resp["responseEnvelope"]["token"], 16) != 0
    ev = w.events()
    assert [e["type"] for e in ev] == ["RELEASE_INTENT", "RELEASE_SENT"]
    assert all((e["requestDigest"], e["grantId"], e["gid"], e["dataId"]) == (signed["requestDigest"], grant_id, ctx.alice, setup.DATA_P1) for e in ev)
    st = w.status(grant_id)
    assert (st["delivery"], st["sendAttempts"], st["completedAttempts"]) == ("unknown", 1, 1)      # delivery to the recipient is never acknowledged


def test_a_retry_returns_the_same_cached_response_without_a_new_intent(world, tmp_path):
    led, ctx = world
    signed, grant_id = grant(led, ctx)
    w = worker(led, tmp_path)
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    first, second = w.release(grant_id), w.release(grant_id)
    assert first == second
    assert [e["type"] for e in w.events()] == ["RELEASE_INTENT", "RELEASE_SENT", "RELEASE_SENT"]
    assert w.status(grant_id)["sendAttempts"] == 2


def test_distinct_grants_get_distinct_unpredictable_tokens(world, tmp_path):
    led, ctx = world
    _, g1 = grant(led, ctx, nonce="1")
    _, g2 = grant(led, ctx, nonce="2")
    w = worker(led, tmp_path)
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    assert w.release(g1)["responseEnvelope"]["token"] != w.release(g2)["responseEnvelope"]["token"]


def test_release_after_the_grant_expiry_fails_even_if_a_response_was_cached(world, tmp_path):
    led, ctx = world
    _, grant_id = grant(led, ctx)
    w = worker(led, tmp_path)
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    w.release(grant_id)
    setup.advance(led, 40)                                                                       # grant TTL <= 30 s
    with pytest.raises(WorkerError) as e:
        w.release(grant_id)
    assert e.value.code == "EXPIRED"
    assert [x["type"] for x in w.events()] == ["RELEASE_INTENT", "RELEASE_SENT"]                 # no event for the refused call


def test_first_release_after_expiry_fails_with_no_intent_recorded(world, tmp_path):
    led, ctx = world
    _, grant_id = grant(led, ctx)
    w = worker(led, tmp_path)
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    setup.advance(led, 40)
    with pytest.raises(WorkerError) as e:
        w.release(grant_id)
    assert e.value.code == "EXPIRED" and w.events() == []


# --- crash recovery ------------------------------------------------------------------------------------------------------------

def test_crash_after_intent_then_restart_reuses_the_persisted_response(world, tmp_path):
    led, ctx = world
    _, grant_id = grant(led, ctx)
    w = worker(led, tmp_path, faults={"crash_after_intent"})
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    with pytest.raises(SimulatedCrash):
        w.release(grant_id)
    assert rows(tmp_path, "select delivery from releases") == [("unknown",)]
    assert [r[0] for r in rows(tmp_path, "select type from events order by id")] == ["RELEASE_INTENT"]      # nothing was attempted yet
    persisted = rows(tmp_path, "select token from releases")[0][0]
    restarted = worker(led, tmp_path)
    resp = restarted.release(grant_id)
    assert resp["responseEnvelope"]["token"] == persisted                                        # the SAME capability, not a fresh one
    assert [e["type"] for e in restarted.events()] == ["RELEASE_INTENT", "RELEASE_SENT"]


def test_crash_after_send_leaves_delivery_unknown_and_a_retry_is_a_second_recorded_attempt_with_the_same_response(world, tmp_path):
    led, ctx = world
    _, grant_id = grant(led, ctx)
    sent = []
    w = worker(led, tmp_path, faults={"crash_after_send"})
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    with pytest.raises(SimulatedCrash):
        w.release(grant_id, transmit=sent.append)
    assert len(sent) == 1                                                                        # the response DID leave the process
    st = worker(led, tmp_path).status(grant_id)
    assert (st["delivery"], st["sendAttempts"], st["completedAttempts"]) == ("unknown", 1, 0)    # attempt recorded write-ahead; completion never seen
    restarted = worker(led, tmp_path)
    again = restarted.release(grant_id, transmit=sent.append)
    assert len(sent) == 2 and sent[0] == sent[1] == again                                        # at-least-once, same capability
    assert [e["type"] for e in restarted.events()] == ["RELEASE_INTENT", "RELEASE_SENT", "RELEASE_SENT"]   # one record per ATTEMPT (A3-0012)
    st = restarted.status(grant_id)
    assert (st["delivery"], st["sendAttempts"], st["completedAttempts"]) == ("unknown", 2, 1)


# --- finish_decryption ---------------------------------------------------------------------------------------------------------

def released(led, ctx, tmp_path):
    _, grant_id = grant(led, ctx)
    w = worker(led, tmp_path)
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    return w, w.release(grant_id)


def test_finish_decryption_completes_only_for_the_stored_binding_and_recipient(world, tmp_path):
    led, ctx = world
    w, resp = released(led, ctx, tmp_path)
    out = w.finish_decryption(resp, "keyref:user:alice")
    assert out == {"schemaVersion": "v1", "adapterMode": "symbolic", "decryptable": True, "dataId": setup.DATA_P1, "ciphertextDigest": resp["ciphertextDigest"]}


@pytest.mark.parametrize("label,mutate,ref", [
    ("another user's key", lambda r: r, "keyref:user:bob"),
    ("forged token", lambda r: {**r, "responseEnvelope": {**r["responseEnvelope"], "token": "0x" + "ee" * 32}}, "keyref:user:alice"),
    ("altered dataId", lambda r: {**r, "dataId": "0x" + "ee" * 32}, "keyref:user:alice"),
    ("altered ciphertextDigest", lambda r: {**r, "ciphertextDigest": "0x" + "ee" * 32}, "keyref:user:alice"),
    ("altered recipientKeyHash", lambda r: {**r, "recipientKeyHash": "0x" + "ee" * 32}, "keyref:user:alice"),
    ("altered requestDigest", lambda r: {**r, "requestDigest": "0x" + "ee" * 32}, "keyref:user:alice"),
    ("unknown grant", lambda r: {**r, "grantId": "0x" + "ee" * 32}, "keyref:user:alice"),
])
def test_finish_decryption_refuses_anything_but_the_exact_issued_response(world, tmp_path, label, mutate, ref):
    led, ctx = world
    w, resp = released(led, ctx, tmp_path)
    with pytest.raises(WorkerError) as e:
        w.finish_decryption(mutate(resp), ref)
    assert e.value.code == "WRONG_SUBJECT", label


def test_a_response_from_another_workers_state_is_refused(world, tmp_path):
    led, ctx = world
    _, resp = released(led, ctx, tmp_path)
    other = Worker(led, tmp_path / "other-state", clock=lambda: 0)
    with pytest.raises(WorkerError) as e:
        other.finish_decryption(resp, "keyref:user:alice")
    assert e.value.code == "WRONG_SUBJECT"
