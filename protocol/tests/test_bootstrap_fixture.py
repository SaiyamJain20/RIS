"""A3-0024: a public, TEST-ONLY bootstrap fixture producer for E1 (Alice registered and entitled; Bob registered but policy-denied).

The runner (Option A) holds only the relay and H1..H4-ca-admin TEST keys; the authority ROOT keys, the user GID keys and the witness key must stay in an owner
process. `python -m testtools.bootstrap_fixture --deployment F` is that process: it prints ONE JSON object holding signed public artifacts, ready-made calldata for
the runner's five transactions and both credential bundles, and never a key. These tests play the runner with ONLY the keys the plan names as submitters.

Nothing here is an E1 result: the chains are a local Anvil pair and the runner role is played by the test.
"""
import json
import os
import pathlib
import subprocess
import sys
import time

import pytest
from eth_account import Account
from eth_utils import keccak, to_checksum_address

from hmbc_protocol import eip712, keys, messages, wire
from hmbc_protocol.ledger import Ledger
from hmbc_protocol.relay import Relay
from support import foundry, rpc
import ledger_setup as setup
from test_adapter_process_live import AdapterProcess, P1_POLICY, RECORD

PROTOCOL = pathlib.Path(__file__).resolve().parents[1]
DEPLOYMENT_FIXTURE = PROTOCOL / "tests" / "fixtures" / "deployment-agent1-91add8c-v1-repaired-e.json"
ABI_DIR = PROTOCOL / "abi"
RUNNER_LABELS = {"H1-ca-admin", "H2-ca-admin", "relay"}
STEP_IDS = ["h1-revocation-list", "h1-temporal-acl", "h2-revocation-list", "register-alice", "register-bob"]
ALL_LABELS = ["H1-root", "H2-root", "H1-ca-admin", "H2-ca-admin", "relay", "alice", "bob", "witness-1"]
NOW = 1_800_000_000
CAST = foundry("cast")


def offline_ledger():
    return Ledger.from_deployment(json.loads(DEPLOYMENT_FIXTURE.read_text()))


def plan_offline(now=NOW):
    from testtools import bootstrap_fixture
    return bootstrap_fixture.build_plan(offline_ledger(), now)


def run_cli(led_or_dep, tmp_path, *extra):
    dep = led_or_dep.deployment if hasattr(led_or_dep, "deployment") else led_or_dep
    f = tmp_path / "deployment.json"
    f.write_text(json.dumps(dep))
    return subprocess.run([sys.executable, "-m", "testtools.bootstrap_fixture", "--deployment", str(f), *extra], cwd=PROTOCOL,
                          env={"PYTHONPATH": str(PROTOCOL), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True, timeout=90)


# ------------------------------------------------------------------ the runner, played by the test --------------------------------------------------

def runner_send(chain_obj, step):
    """Submit ONE planned transaction using only what the plan hands the runner: the submitter label's TEST key, `to` and `calldata`."""
    assert step["submitter"] in RUNNER_LABELS, step["submitter"]
    acct = Account.from_key(keys.synthetic_private_key(step["submitter"]))
    tx = {"from": acct.address, "to": to_checksum_address(step["to"]), "data": step["calldata"]}
    gas = int(rpc(chain_obj.url, "eth_estimateGas", [tx]), 16)
    signed = acct.sign_transaction({"chainId": chain_obj.chain_id, "nonce": int(rpc(chain_obj.url, "eth_getTransactionCount", [acct.address, "pending"]), 16),
                                    "gasPrice": int(rpc(chain_obj.url, "eth_gasPrice"), 16), "gas": gas + gas // 5, "to": tx["to"], "value": 0, "data": step["calldata"]})
    h = rpc(chain_obj.url, "eth_sendRawTransaction", ["0x" + signed.raw_transaction.hex()])
    for _ in range(100):
        rc = rpc(chain_obj.url, "eth_getTransactionReceipt", [h])
        if rc is not None:
            assert int(rc["status"], 16) == 1, f"{step['id']} reverted"
            return rc
        time.sleep(0.1)
    raise AssertionError(f"{step['id']} not mined")


def submit_plan(led, plan):
    for step in plan["steps"]:
        assert step["chain"] == "pbc"
        runner_send(led.pbc, step)


def bootstrap(ledger_chains, tmp_path):
    """CLI -> parse -> runner submits. Returns (Ledger, plan)."""
    led = Ledger.from_deployment(ledger_chains.deployment)
    p = run_cli(led, tmp_path)
    assert p.returncode == 0 and p.stderr == "", p.stderr
    plan = json.loads(p.stdout)
    submit_plan(led, plan)
    return led, plan


# ------------------------------------------------------------------ offline: the shape of the plan --------------------------------------------------

def test_plan_lists_the_five_transactions_in_dependency_order_with_runner_held_submitters_only():
    plan = plan_offline()
    assert [s["id"] for s in plan["steps"]] == STEP_IDS
    assert {s["submitter"] for s in plan["steps"]} <= RUNNER_LABELS
    by = {s["id"]: s for s in plan["steps"]}
    assert (by["h1-revocation-list"]["submitter"], by["h1-revocation-list"]["function"]) == ("H1-ca-admin", "updateRevocationList")
    assert (by["h1-temporal-acl"]["submitter"], by["h1-temporal-acl"]["function"]) == ("H1-ca-admin", "updateTemporalAcl")
    assert (by["h2-revocation-list"]["submitter"], by["h2-revocation-list"]["function"]) == ("H2-ca-admin", "updateRevocationList")
    assert all(by[i]["submitter"] == "relay" and by[i]["function"] == "register" and by[i]["contract"] == "RSC" for i in ("register-alice", "register-bob"))
    dep = offline_ledger().deployment["chains"]["pbc"]["contracts"]
    for s in plan["steps"]:
        assert s["chain"] == "pbc" and s["to"] == dep[s["contract"]]


def test_plan_names_both_identities_with_the_a35_recipient_convention():
    ident = plan_offline()["identities"]
    assert set(ident) == {"alice", "bob"}
    for label in ("alice", "bob"):
        assert ident[label] == {"keyRef": f"keyref:user:{label}", "gid": setup.addr(label), "recipientKeyHash": keys.recipient_key_hash(f"keyref:user:{label}")}
    assert ident["alice"]["recipientKeyHash"] == "0x98d796e3229ebf5c50610744cf35aece58511751e387e8eef569a0117bb07e5d"
    assert ident["bob"]["recipientKeyHash"] == "0x5fe346cd69926d7120dff3cc020f4d36ad8093b7c9bb95c6ecea9705a3f8c537"


def test_every_artifact_is_valid_frozen_wire_form():
    plan = plan_offline()
    by = {s["id"]: s["args"] for s in plan["steps"]}
    for i in ("h1-revocation-list", "h2-revocation-list"):
        wire.validate("RevocationList", by[i]["list"])
        wire.signature(by[i]["issuerSignature"])
    wire.validate("TemporalAcl", by["h1-temporal-acl"]["acl"])
    wire.signature(by["h1-temporal-acl"]["issuerSignature"])
    for i in ("register-alice", "register-bob"):
        wire.validate("Registration", by[i]["reg"])
        wire.signature(by[i]["possessionSignature"])
        wire.validate("SignedRoleCertificate", by[i]["cert"])
    for label in ("alice", "bob"):
        wire.validate("CredentialBundle", plan["credentialBundles"][label])


def test_the_two_bundles_differ_exactly_as_the_scenario_needs():
    """Alice: Doctor certificate (H1) + OnDuty temporal claim. Bob: a VALID Researcher certificate (H2) and no duty claim, so he is registered but fails P1."""
    plan = plan_offline()
    alice, bob = plan["credentialBundles"]["alice"], plan["credentialBundles"]["bob"]
    assert [c["cert"]["roles"] for c in alice["certificates"]] == [[setup.ROLE_DOCTOR]]
    assert alice["certificates"][0]["cert"]["issuer"] == setup.addr("H1-root")
    assert alice["temporalClaims"] == [{"authority": setup.addr("H1-root"), "role": setup.ROLE_ON_DUTY}]
    researcher = "0x" + keccak(text="HMBC.role.Researcher").hex()
    assert [c["cert"]["roles"] for c in bob["certificates"]] == [[researcher]]
    assert bob["certificates"][0]["cert"]["issuer"] == setup.addr("H2-root") and bob["temporalClaims"] == []


def test_signatures_recover_to_the_authority_root_and_gid_keys_not_to_runner_keys():
    plan = plan_offline()
    dep = offline_ledger().deployment
    by = {s["id"]: s["args"] for s in plan["steps"]}

    def signer(name, msg, sig):
        return eip712.recover(messages.digest_of(name, msg, messages.domain_for(name, msg, dep)), sig)
    assert signer("RevocationList", by["h1-revocation-list"]["list"], by["h1-revocation-list"]["issuerSignature"]) == setup.addr("H1-root")
    assert signer("TemporalAcl", by["h1-temporal-acl"]["acl"], by["h1-temporal-acl"]["issuerSignature"]) == setup.addr("H1-root")
    assert signer("RevocationList", by["h2-revocation-list"]["list"], by["h2-revocation-list"]["issuerSignature"]) == setup.addr("H2-root")
    for label, issuer in (("alice", "H1-root"), ("bob", "H2-root")):
        a = by[f"register-{label}"]
        assert signer("Registration", a["reg"], a["possessionSignature"]) == setup.addr(label)           # GID possession
        assert signer("RoleCertificate", a["cert"]["cert"], a["cert"]["signature"]) == setup.addr(issuer)
        assert a["reg"]["certDigest"] == "0x" + messages.digest_of("RoleCertificate", a["cert"]["cert"], messages.domain_for("RoleCertificate", a["cert"]["cert"], dep)).hex()


def test_time_windows_follow_the_pbc_clock_it_was_given():
    plan = plan_offline(NOW)
    assert plan["binding"]["pbcTimestamp"] == str(NOW)
    by = {s["id"]: s["args"] for s in plan["steps"]}
    assert by["h1-revocation-list"]["list"]["validUntil"] == str(NOW + 86400) and by["h1-temporal-acl"]["acl"]["validUntil"] == str(NOW + 86400)
    entry = by["h1-temporal-acl"]["acl"]["entries"][0]
    assert (entry["gid"], entry["validFrom"], entry["validUntil"]) == (setup.addr("alice"), str(NOW - 60), str(NOW + 8 * 3600))
    assert by["register-alice"]["reg"]["expiresAt"] == str(NOW + 3600) and by["register-bob"]["reg"]["expiresAt"] == str(NOW + 3600)
    assert plan["validity"] == {"listSeconds": 86400, "dutySeconds": 28800, "registrationSeconds": 3600}


def test_binding_names_the_deployment_it_was_signed_for_and_other_deployments_get_other_signatures():
    plan = plan_offline()
    chains = offline_ledger().deployment["chains"]
    assert plan["binding"]["pbcChainId"] == chains["pbc"]["chainId"] and plan["binding"]["dbcChainId"] == chains["dbc"]["chainId"]
    assert plan["binding"]["tmsc"] == chains["pbc"]["contracts"]["TMSC"] and plan["binding"]["rsc"] == chains["pbc"]["contracts"]["RSC"]
    other = json.loads(DEPLOYMENT_FIXTURE.read_text())
    other["chains"]["pbc"]["contracts"]["TMSC"] = "0x" + "12" * 20
    from testtools import bootstrap_fixture
    p2 = bootstrap_fixture.build_plan(Ledger.from_deployment(other), NOW)
    assert p2["steps"][0]["args"]["issuerSignature"] != plan["steps"][0]["args"]["issuerSignature"]


def test_plan_carries_the_wrong_issuer_admin_control_apart_from_the_steps():
    """Frozen control WrongIssuerAdmin: an H1 CA-Admin submits H2's list. A validly H2-signed NEWER list, so only the caller can be wrong; never a bootstrap step."""
    plan = plan_offline()
    assert [c["id"] for c in plan["controls"]] == ["wrong-issuer-admin-h2-list"] and "wrong-issuer-admin-h2-list" not in [s["id"] for s in plan["steps"]]
    ctl = plan["controls"][0]
    assert (ctl["chain"], ctl["submitter"], ctl["contract"], ctl["function"], ctl["expected"]) == ("pbc", "H1-ca-admin", "TMSC", "updateRevocationList", "UNAUTHORIZED_CALLER")
    wire.validate("RevocationList", ctl["args"]["list"])
    assert ctl["args"]["list"]["authority"] == setup.addr("H2-root") and ctl["args"]["list"]["version"] == "2"
    dep = offline_ledger().deployment
    msg = ctl["args"]["list"]
    assert eip712.recover(messages.digest_of("RevocationList", msg, messages.domain_for("RevocationList", msg, dep)), ctl["args"]["issuerSignature"]) == setup.addr("H2-root")
    assert ctl["to"] == dep["chains"]["pbc"]["contracts"]["TMSC"]


def test_the_plan_is_deterministic_for_a_given_clock():
    assert plan_offline(NOW) == plan_offline(NOW)
    assert plan_offline(NOW) != plan_offline(NOW + 1)


def test_no_private_key_appears_anywhere_in_the_plan():
    blob = json.dumps(plan_offline())
    for label in ALL_LABELS:
        k = keys.synthetic_private_key(label)
        assert k not in blob and k[2:] not in blob, label
    assert "5ae9decb1755" not in blob


@pytest.mark.skipif(CAST is None, reason="Foundry cast not installed")
def test_calldata_equals_casts_independent_encoding_for_every_step():
    def fmt(t, v):
        ty = t["type"]
        if ty.endswith("[]"):
            return "[" + ",".join(fmt({**t, "type": ty[:-2]}, x) for x in v) + "]"
        if ty == "tuple":
            return "(" + ",".join(fmt(c, v[c["name"]]) for c in t["components"]) + ")"
        return v
    abis = {n: json.loads((ABI_DIR / f"{n}.json").read_text()) for n in ("TMSC", "RSC")}
    plan = plan_offline()
    for s in plan["steps"] + plan["controls"]:
        f = next(e for e in abis[s["contract"]] if e.get("type") == "function" and e["name"] == s["function"])
        args = [fmt(i, s["args"][i["name"]]) for i in f["inputs"]]
        sig = s["function"] + "(" + ",".join(_canon(i) for i in f["inputs"]) + ")"
        theirs = subprocess.run([CAST, "calldata", sig, *args], check=True, capture_output=True, text=True).stdout.strip()
        assert s["calldata"] == theirs, s["id"]


def _canon(t):
    if t["type"].startswith("tuple"):
        return "(" + ",".join(_canon(c) for c in t["components"]) + ")" + t["type"][len("tuple"):]
    return t["type"]


# ------------------------------------------------------------------ boundaries --------------------------------------------------------------------

def test_the_tool_is_not_part_of_the_production_adapter_boundary():
    code = "import sys, hmbc_protocol.adapter, hmbc_protocol.export; print(any('testtools' in m for m in sys.modules))"
    p = subprocess.run([sys.executable, "-c", code], cwd=PROTOCOL, env={"PYTHONPATH": str(PROTOCOL), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True)
    assert p.stdout.strip() == "False", p.stderr
    manifest = (PROTOCOL / "exports" / "adapter.json").read_text()
    assert "bootstrap" not in manifest and "testtools" not in manifest
    assert not any("testtools" in f.read_text() for f in (PROTOCOL / "hmbc_protocol").glob("*.py"))


def test_refuses_a_deployment_that_is_not_marked_test_only(tmp_path):
    dep = json.loads(DEPLOYMENT_FIXTURE.read_text())
    dep["fixture"]["keyDerivation"] = "production keys"
    p = run_cli(dep, tmp_path)
    assert p.returncode != 0 and p.stdout == "" and "refusing" in p.stderr and "TEST-ONLY" in p.stderr and "Traceback" not in p.stderr


def test_build_plan_itself_refuses_a_deployment_that_is_not_marked_test_only():
    """The library entry point is guarded too, not only the command line."""
    from testtools import bootstrap_fixture
    dep = json.loads(DEPLOYMENT_FIXTURE.read_text())
    dep["fixture"]["keyDerivation"] = "production keys"
    with pytest.raises(SystemExit) as e:
        bootstrap_fixture.build_plan(Ledger.from_deployment(dep), NOW)
    assert "TEST-ONLY" in str(e.value)


def test_refuses_unusable_input_cleanly(tmp_path):
    p = subprocess.run([sys.executable, "-m", "testtools.bootstrap_fixture", "--deployment", str(tmp_path / "missing.json")], cwd=PROTOCOL,
                       env={"PYTHONPATH": str(PROTOCOL), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True)
    assert p.returncode != 0 and p.stdout == "" and "refusing" in p.stderr and "Traceback" not in p.stderr
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    p = subprocess.run([sys.executable, "-m", "testtools.bootstrap_fixture", "--deployment", str(bad)], cwd=PROTOCOL,
                       env={"PYTHONPATH": str(PROTOCOL), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True)
    assert p.returncode != 0 and p.stdout == "" and "refusing" in p.stderr and "Traceback" not in p.stderr


def test_refuses_when_the_pbc_is_unreachable_without_a_traceback(tmp_path):
    dep = json.loads(DEPLOYMENT_FIXTURE.read_text())
    dep["chains"]["pbc"]["rpcUrl"] = "http://127.0.0.1:9"                      # nothing listens on the discard port
    p = run_cli(dep, tmp_path)
    assert p.returncode != 0 and p.stdout == "" and "refusing" in p.stderr and "Traceback" not in p.stderr


def test_refuses_a_non_loopback_rpc_url(tmp_path):
    dep = json.loads(DEPLOYMENT_FIXTURE.read_text())
    dep["chains"]["pbc"]["rpcUrl"] = "http://203.0.113.9:8545"
    p = run_cli(dep, tmp_path)
    assert p.returncode != 0 and p.stdout == "" and "refusing" in p.stderr and "Traceback" not in p.stderr


# ------------------------------------------------------------------ live: the runner submits ONLY the plan ------------------------------------------

@pytest.mark.parametrize("fixture_name", ["ledger", "ledger_paper", "ledger_paper_minimal"])
def test_cli_output_bootstraps_alice_and_bob_on_every_profile(request, fixture_name, tmp_path):
    chains = request.getfixturevalue(fixture_name)
    led = Ledger.from_deployment(chains.deployment)
    before = led.pbc.call(led.TMSC, "authEpoch")
    p = run_cli(led, tmp_path)
    assert p.returncode == 0 and p.stderr == "" and p.stdout.count("\n") == 1, p.stderr           # exactly ONE JSON line
    plan = json.loads(p.stdout)
    assert plan["testOnly"] is True and plan["schemaVersion"] == "hmbc-test-bootstrap/v0"
    if fixture_name == "ledger" and os.environ.get("HMBC_WRITE_EVIDENCE") == "1":
        (PROTOCOL / "evidence" / "bootstrap-plan-example.json").write_text(json.dumps(
            {"note": "Real CLI output against a local Anvil pair with agent-1 ledger 91add8c (repaired-e). Chain time, signatures and calldata vary per run; "
                     "only public artifacts, never a key. Not an E1 integration run.", "plan": plan}, indent=1) + "\n")
    submit_plan(led, plan)
    for label in ("alice", "bob"):
        ident = plan["identities"][label]
        assert led.pbc.call(led.RSC, "isRegistered", ident["gid"]) is True
        assert led.pbc.call(led.RSC, "recipientKeyHash", ident["gid"]) == ident["recipientKeyHash"]
    assert led.pbc.call(led.TMSC, "authEpoch") != before                                           # the lists were accepted (the epoch the request must carry moved)
    for label in ("alice", "bob"):                                                                  # both can now be forwarded on the PBC with the produced bundle
        from hmbc_protocol.client import UserClient
        client = UserClient(label, led.deployment)
        signed = client.sign_request(setup.make_request(led, None, client))
        assert Relay(led, "relay").forward(signed, plan["credentialBundles"][label]).code == "NONE", label


def test_the_plan_is_bound_to_the_pbc_clock_not_the_dbc_clock(ledger, tmp_path):
    """The two chains keep separate clocks. Skew the DBC by two hours: the registration/duty windows must still follow the PBC."""
    led = Ledger.from_deployment(ledger.deployment)
    rpc(led.dbc.url, "evm_increaseTime", [7200])
    rpc(led.dbc.url, "evm_mine")
    p = run_cli(led, tmp_path)
    assert p.returncode == 0, p.stderr
    stamp = int(json.loads(p.stdout)["binding"]["pbcTimestamp"])
    assert abs(stamp - led.pbc.now()) <= 30 and led.dbc.now() - stamp >= 7000


def test_the_wrong_issuer_admin_control_is_rejected_for_the_caller_alone_and_the_artifact_is_otherwise_valid(ledger, tmp_path):
    from hmbc_protocol.chain import Rejected
    led, plan = bootstrap(ledger, tmp_path)
    ctl = plan["controls"][0]
    epoch = led.pbc.call(led.TMSC, "authEpoch")
    with pytest.raises(Rejected) as e:
        led.pbc.send(keys.synthetic_private_key(ctl["submitter"]), led.TMSC, ctl["function"], *ctl["args"].values())
    assert e.value.code == ctl["expected"] == "UNAUTHORIZED_CALLER"
    assert led.pbc.call(led.TMSC, "authEpoch") == epoch                                           # nothing changed
    runner_send(led.pbc, {**ctl, "submitter": "H2-ca-admin"})                                     # the rightful admin may submit the very same artifact
    assert led.pbc.call(led.TMSC, "authEpoch") != epoch


def test_a_second_run_is_refused_by_the_ledger_because_list_versions_must_advance(ledger, tmp_path):
    led, plan = bootstrap(ledger, tmp_path)
    p = run_cli(led, tmp_path)
    again = json.loads(p.stdout)
    with pytest.raises(Exception):                                                                   # the ledger rejects the replayed version
        runner_send(led.pbc, again["steps"][0])


def assert_alice_flow(led, bundle, recipient_key_hash, state_dir):
    """Alice, through the adapter PROCESS, with a produced bundle: grant, release to her recipient hash, decryptable."""
    adp = AdapterProcess(state_dir, led.deployment)
    try:
        from hmbc_protocol.client import UserClient
        req = adp.call("prepare_request", {"request": UserClient("alice", led.deployment).build_request(
            data_id=setup.DATA_P1, nonce="1", auth_epoch=led.pbc.call(led.TMSC, "authEpoch"), expires_at=str(led.pbc.now() + 30)), "signingKeyRef": "keyref:user:alice"})
        assert req["ok"], req
        signed = {"request": req["result"]["request"], "requestDigest": req["result"]["requestDigest"], "signature": req["result"]["signature"]}
        relay = Relay(led, "relay")
        assert relay.forward(signed, bundle).code == "NONE"
        cp = adp.call("collect_checkpoint", {})
        assert cp["ok"], cp
        relay.accept_state({"checkpoint": cp["result"]["checkpoint"], "signatures": cp["result"]["signatures"]})
        dec = adp.call("collect_decision", {"requestDigest": signed["requestDigest"]})
        assert dec["ok"] and dec["result"]["decision"]["result"] == "1", dec
        grant_id = relay.deliver(signed, {"decision": dec["result"]["decision"], "signatures": dec["result"]["signatures"],
                                          "credentialRecords": dec["result"]["credentialRecords"]})
        assert grant_id is not None
        assert adp.call("encrypt_record", {"record": RECORD, "policy": P1_POLICY, "keyEpoch": "0"})["ok"]
        rel = adp.call("release", {"grantId": grant_id})
        assert rel["ok"] and rel["result"]["recipientKeyHash"] == recipient_key_hash, rel
        fin = adp.call("finish_decryption", {"response": rel["result"], "userKeyRef": "keyref:user:alice"})
        assert fin["ok"] and fin["result"]["decryptable"] is True
    finally:
        adp.close()


def assert_bob_denial(led, bundle, bob_gid, state_dir):
    """Bob must reach the native DBC denial (registered, valid credentials, fails P1), never NOT_REGISTERED."""
    adp = AdapterProcess(state_dir, led.deployment)
    try:
        from hmbc_protocol.client import UserClient
        req = adp.call("prepare_request", {"request": UserClient("bob", led.deployment).build_request(
            data_id=setup.DATA_P1, nonce="7", auth_epoch=led.pbc.call(led.TMSC, "authEpoch"), expires_at=str(led.pbc.now() + 30)), "signingKeyRef": "keyref:user:bob"})
        assert req["ok"], req
        signed = {"request": req["result"]["request"], "requestDigest": req["result"]["requestDigest"], "signature": req["result"]["signature"]}
        relay = Relay(led, "relay")
        assert relay.forward(signed, bundle).code == "NONE"                                          # the PBC accepts: Bob's credentials are valid and he IS registered
        cp = adp.call("collect_checkpoint", {})
        relay.accept_state({"checkpoint": cp["result"]["checkpoint"], "signatures": cp["result"]["signatures"]})
        dec = adp.call("collect_decision", {"requestDigest": signed["requestDigest"]})
        assert dec["ok"] and dec["result"]["decision"]["result"] == "0", dec                          # signed DENY: Researcher does not satisfy Doctor+OnDuty
        logs = int(led.dbc.call(led.ACSC, "accessLogCount"))
        assert relay.deliver(signed, {"decision": dec["result"]["decision"], "signatures": dec["result"]["signatures"],
                                      "credentialRecords": dec["result"]["credentialRecords"]}) is None
        assert int(led.dbc.call(led.ACSC, "accessLogCount")) == logs + 1                             # DBC_POLICY_DENIAL_LOGGED
        assert led.dbc.call(led.KSSC, "nonceConsumed", bob_gid, "7") is False                         # NONCE_UNCHANGED
    finally:
        adp.close()


def test_alice_completes_the_whole_flow_through_the_adapter_process_with_the_produced_bundle(ledger, tmp_path):
    led, plan = bootstrap(ledger, tmp_path)
    assert_alice_flow(led, plan["credentialBundles"]["alice"], plan["identities"]["alice"]["recipientKeyHash"], tmp_path / "adapter-state")


def test_bob_is_registered_forwarded_denied_with_a_logged_denial_and_an_unchanged_nonce(ledger, tmp_path):
    """The scenario A3-0024 needs: Bob must reach the native DBC denial, not fail earlier as NOT_REGISTERED."""
    led, plan = bootstrap(ledger, tmp_path)
    assert_bob_denial(led, plan["credentialBundles"]["bob"], plan["identities"]["bob"]["gid"], tmp_path / "adapter-state")
