"""The adapter's four ledger-backed operations against the live ledger, validated with the revision-4 response rules."""
import json

import pytest
from eth_account import Account
from eth_utils import keccak

from hmbc_protocol import adapter, eip712, keys, messages, wire
from hmbc_protocol.client import UserClient
from hmbc_protocol.relay import Relay
from hmbc_protocol.witness import Witness
import ledger_setup as setup

P1_POLICY = {"clauses": [[{"role": setup.ROLE_DOCTOR, "kind": "1", "issuerMode": "0"}, {"role": setup.ROLE_ON_DUTY, "kind": "2", "issuerMode": "2"}]]}
P1_RECORD = {"dataId": setup.DATA_P1, "owner": setup.addr("H2-root"), "payloadDigest": "0x" + keccak(text="synthetic payload P1").hex()}


@pytest.fixture
def configured(world, tmp_path):
    """Start the adapter the way a runner must: a private state dir and the deployment PINNED out of band."""
    led, ctx = world
    adapter.configure(str(tmp_path / "adapter-state"), led.deployment)
    yield
    adapter.configure(None)


def call(led, op, inp, dep=None):
    line = json.dumps({"schemaVersion": "v1", "operation": op, "input": inp, "deploymentManifest": dep or led.deployment})
    resp = adapter.handle_line(line)
    wire.adapter_response(resp)                                   # always a well-formed response
    wire.adapter_response(resp, op)                               # and bound to the pending operation
    return resp


def grant(led, ctx, nonce="1"):
    client = UserClient("alice", led.deployment)
    signed = client.sign_request(setup.make_request(led, ctx, client, nonce=nonce))
    relay, w = Relay(led, "relay"), Witness(led)
    assert relay.forward(signed, ctx.bundle).code == "NONE"
    relay.accept_state(w.checkpoint())
    return signed, relay.deliver(signed, w.decide(signed["requestDigest"]))


ENC = {"record": P1_RECORD, "policy": P1_POLICY, "keyEpoch": "0"}


def test_encrypt_record_through_the_adapter(world, configured):
    led, ctx = world
    r = call(led, "encrypt_record", ENC)
    assert r["ok"], r
    assert r["result"]["policyDigest"] == "0x4bd063e1a4c348bf656f983104839fec2594aaee710b4627e9e46368ba1abc3a"
    assert r["result"]["adapterMode"] == "symbolic" and r["result"]["dataId"] == setup.DATA_P1


def test_encrypt_record_refuses_a_policy_the_acsc_did_not_register(world, configured):
    led, ctx = world
    r = call(led, "encrypt_record", {**ENC, "policy": {"clauses": [[P1_POLICY["clauses"][0][0]]]}})
    assert not r["ok"] and r["error"]["code"] == "WRONG_SUBJECT"


def test_release_then_finish_decryption_through_the_adapter(world, configured):
    led, ctx = world
    signed, grant_id = grant(led, ctx)
    assert call(led, "encrypt_record", ENC)["ok"]
    rel = call(led, "release", {"grantId": grant_id})
    assert rel["ok"], rel
    res = rel["result"]
    assert (res["requestDigest"], res["grantId"], res["dataId"], res["keyEpoch"]) == (signed["requestDigest"], grant_id, setup.DATA_P1, "0")
    assert call(led, "release", {"grantId": grant_id})["result"] == res                      # retry: same cached response
    fin = call(led, "finish_decryption", {"response": res, "userKeyRef": "keyref:user:alice"})
    assert fin["ok"] and fin["result"]["decryptable"] is True and fin["result"]["dataId"] == setup.DATA_P1
    bad = call(led, "finish_decryption", {"response": res, "userKeyRef": "keyref:user:bob"})
    assert not bad["ok"] and bad["error"]["code"] == "WRONG_SUBJECT"


def test_release_of_an_unknown_grant_is_not_committed(world, configured):
    led, ctx = world
    r = call(led, "release", {"grantId": "0x" + "55" * 32})
    assert not r["ok"] and r["error"]["code"] == "NOT_COMMITTED"


def test_release_after_expiry_is_expired(world, configured):
    led, ctx = world
    _, grant_id = grant(led, ctx)
    assert call(led, "encrypt_record", ENC)["ok"] and call(led, "release", {"grantId": grant_id})["ok"]
    setup.advance(led, 40)
    r = call(led, "release", {"grantId": grant_id})
    assert not r["ok"] and r["error"]["code"] == "EXPIRED"


def test_collect_decision_without_a_dbc_checkpoint_is_stale_state(world, configured):
    led, ctx = world
    client = UserClient("alice", led.deployment)
    signed = client.sign_request(setup.make_request(led, ctx, client))
    assert Relay(led, "relay").forward(signed, ctx.bundle).code == "NONE"
    r = call(led, "collect_decision", {"requestDigest": signed["requestDigest"]})
    assert not r["ok"] and r["error"]["code"] == "STALE_STATE"


def test_collect_decision_returns_a_witness_signed_decision_once_a_checkpoint_is_accepted(world, configured):
    led, ctx = world
    client = UserClient("alice", led.deployment)
    signed = client.sign_request(setup.make_request(led, ctx, client))
    relay, w = Relay(led, "relay"), Witness(led)
    assert relay.forward(signed, ctx.bundle).code == "NONE"
    relay.accept_state(w.checkpoint())
    r = call(led, "collect_decision", {"requestDigest": signed["requestDigest"]})
    assert r["ok"], r
    d = r["result"]["decision"]
    dig = messages.digest_of("AccessDecision", d, messages.domain_for("AccessDecision", d, led.deployment))
    assert eip712.recover(dig, r["result"]["signatures"][0]) == Account.from_key(keys.synthetic_private_key("witness-1")).address.lower()
    assert relay.deliver(signed, {"decision": d, "signatures": r["result"]["signatures"], "credentialRecords": r["result"]["credentialRecords"]}) is not None


def test_collect_decision_for_an_unforwarded_digest_is_refused(world, configured):
    led, ctx = world
    Relay(led, "relay").accept_state(Witness(led).checkpoint())
    r = call(led, "collect_decision", {"requestDigest": "0x" + "99" * 32})
    assert not r["ok"] and r["error"]["code"] == "WRONG_SUBJECT"


def test_unreachable_ledger_is_adapter_unavailable_not_a_crash(world, tmp_path):
    led, ctx = world
    dep = json.loads(json.dumps(led.deployment))
    dep["chains"]["dbc"]["rpcUrl"] = "http://127.0.0.1:1"                                      # nothing listens here
    adapter.configure(str(tmp_path / "s"), dep)                                                # pinned: the operator chose this (dead) ledger
    try:
        r = call(led, "release", {"grantId": "0x" + "55" * 32}, dep=dep)
        assert not r["ok"] and r["error"]["code"] == "ADAPTER_UNAVAILABLE"
    finally:
        adapter.configure(None)


@pytest.mark.parametrize("mutate", [lambda d: d["chains"]["dbc"].__setitem__("rpcUrl", "http://169.254.169.254:80"),
                                    lambda d: d["abi"]["KSSC"].__setitem__("abiSha256", "0" * 64)])
def test_in_band_changes_to_the_manifest_are_refused_as_a_different_destination(world, configured, mutate):
    """Superseded the earlier 'non-loopback / different ABI is MALFORMED' tests: with a pinned deployment ANY in-band difference is WRONG_DESTINATION,
    and the loader-level checks (loopback URL, ABI hash) are tested directly in test_ledger.py / test_chain_hardening.py."""
    led, ctx = world
    dep = json.loads(json.dumps(led.deployment))
    mutate(dep)
    r = call(led, "release", {"grantId": "0x" + "55" * 32}, dep=dep)
    assert not r["ok"] and r["error"]["code"] == "WRONG_DESTINATION"


def test_without_a_configured_state_dir_ledger_operations_are_unavailable(world):
    led, ctx = world
    adapter.configure(None)
    r = call(led, "release", {"grantId": "0x" + "55" * 32})
    assert not r["ok"] and r["error"]["code"] == "ADAPTER_UNAVAILABLE"


def test_no_adapter_response_contains_key_material_or_a_foreign_token(world, configured):
    led, ctx = world
    _, grant_id = grant(led, ctx)
    outs = [call(led, "encrypt_record", ENC), call(led, "release", {"grantId": grant_id}), call(led, "release", {"grantId": "0x" + "55" * 32})]
    blob = json.dumps(outs)
    for label in ("alice", "witness-1", "relay", "H1-root"):
        k = keys.synthetic_private_key(label)
        assert k not in blob and k[2:] not in blob


# --- revision 5 witness operations (A2-0008 / A3-0012) --------------------------------------------------------------------------

def test_collect_checkpoint_is_a_witness_signed_checkpoint_the_dbc_accepts(world, configured):
    led, ctx = world
    r = call(led, "collect_checkpoint", {})
    assert r["ok"], r
    cp = r["result"]["checkpoint"]
    dig = messages.digest_of("StateCheckpoint", cp, messages.domain_for("StateCheckpoint", cp, led.deployment))
    assert eip712.recover(dig, r["result"]["signatures"][0]) == Account.from_key(keys.synthetic_private_key("witness-1")).address.lower()
    assert (cp["sequence"], cp["keyEpoch"], cp["witnessSetVersion"]) == ("1", "0", "1") and cp["authEpoch"] == "3"
    Relay(led, "relay").accept_state({"checkpoint": cp, "signatures": r["result"]["signatures"]})        # the runner submits it; the ledger accepts it
    assert led.dbc.call(led.KSSC, "currentCheckpoint")[1]["sequence"] == "1"
    assert call(led, "collect_checkpoint", {"witnessSetVersion": "1"})["result"]["checkpoint"]["sequence"] == "2"   # sequence comes from the DBC


@pytest.mark.parametrize("bad", [{"witnessSetVersion": "2"}, {"witnessSetVersion": 1}, {"sequence": "9"}, {"sourceBlockNumber": "1"}, {"expiresAt": "9999999999"}, []])
def test_collect_checkpoint_accepts_no_relay_supplied_state(world, configured, bad):
    led, ctx = world
    line = json.dumps({"schemaVersion": "v1", "operation": "collect_checkpoint", "input": bad, "deploymentManifest": led.deployment})
    r = adapter.handle_line(line)
    assert not r["ok"] and r["error"]["code"] == "MALFORMED"


def test_attest_grant_and_the_runner_reports_the_attested_outcome(world, configured):
    led, ctx = world
    signed, grant_id = grant(led, ctx)
    r = call(led, "attest_grant", {"grantId": grant_id})
    assert r["ok"], r
    rc = r["result"]["receipt"]
    assert (rc["grantId"], rc["requestDigest"], rc["gid"], rc["dataId"], rc["keyEpoch"]) == (grant_id, signed["requestDigest"], ctx.alice, setup.DATA_P1, "0")
    Relay(led, "relay").report_outcome(signed["requestDigest"], "0x" + "ab" * 32, {"receipt": rc, "signatures": r["result"]["signatures"]})
    assert led.pbc.call(led.PSC, "getRequest", signed["requestDigest"])["status"] == "2"


def test_attest_grant_for_an_unknown_grant_is_not_committed_and_after_the_outcome_is_wrong_subject(world, configured):
    led, ctx = world
    assert call(led, "attest_grant", {"grantId": "0x" + "55" * 32})["error"]["code"] == "NOT_COMMITTED"
    signed, grant_id = grant(led, ctx)
    r = call(led, "attest_grant", {"grantId": grant_id})
    Relay(led, "relay").report_outcome(signed["requestDigest"], "0x" + "ab" * 32, {"receipt": r["result"]["receipt"], "signatures": r["result"]["signatures"]})
    assert call(led, "attest_grant", {"grantId": grant_id})["error"]["code"] == "WRONG_SUBJECT"          # no second receipt once the outcome is recorded
