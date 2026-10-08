import copy
import io
import json
import pathlib
import subprocess
import sys

import pytest

from hmbc_protocol import adapter, eip712

FIX = pathlib.Path(__file__).parent / "fixtures"
DEP = json.loads((FIX / "deployment-agent1-54262c2-repaired-e.json").read_text())
VEC = json.loads((FIX / "eip712-agent1-54262c2.json").read_text())
ALICE_KEY = "0x5ae9decb17555998c229f97e1846cd52b643a4b10efd2bbbc09c89c6ba1f76db"  # TEST-ONLY, from the vector file


def request(**over):
    pbc, dbc = DEP["chains"]["pbc"], DEP["chains"]["dbc"]
    msg = {"sourceChainId": pbc["chainId"], "destinationChainId": dbc["chainId"], "psc": pbc["contracts"]["PSC"],
           "kssc": dbc["contracts"]["KSSC"], "gid": "0xc4ff0022e776c3471e39abf6c69ce679440c956d",
           "dataId": "0x" + "ab" * 32, "action": "1", "policyVersion": "1", "authEpoch": "3", "keyEpoch": "0",
           "nonce": "1", "expiresAt": "1800000030", "recipientKeyHash": "0x98d796e3229ebf5c50610744cf35aece58511751e387e8eef569a0117bb07e5d"}
    msg.update(over)
    return msg


def call(op="prepare_request", inp=None, dep=DEP, **extra):
    env = {"schemaVersion": "v1", "operation": op, "input": inp, "deploymentManifest": dep}
    env.update(extra)
    return adapter.handle_line(json.dumps(env))


def good_input(**over):
    return {"request": request(**over), "signingKeyRef": "keyref:user:alice"}


def check_envelope(resp):
    assert set(resp) == {"schemaVersion", "ok", "result", "error"} and resp["schemaVersion"] == "v1"
    assert (resp["result"] is None) != (resp["error"] is None) and resp["ok"] == (resp["error"] is None)
    if resp["error"]:
        assert set(resp["error"]) == {"code", "message"}


def test_deployment_fixture_is_pinned():
    """Byte copy of origin/agent-1 54262c2 ledger/exports/deployments/sample-repaired-e/deployment.json."""
    import hashlib
    assert hashlib.sha256((FIX / "deployment-agent1-54262c2-repaired-e.json").read_bytes()).hexdigest() == (
        "38b7631f5b977dac06f64fabf2615f846da8f8d0619e1b01797c7821fed2f3eb")


def test_prepare_request_signs_and_the_signature_recovers_the_user():
    r = call(inp=good_input())
    check_envelope(r)
    assert r["ok"], r
    res = r["result"]
    td = {"types": {"EIP712Domain": eip712.DOMAIN_TYPE, "AccessRequest": adapter.messages.TYPES["AccessRequest"]},
          "primaryType": "AccessRequest", "domain": adapter.messages.domain_for("AccessRequest", res["request"], DEP),
          "message": res["request"]}
    dig = eip712.digest(td)
    assert res["requestDigest"] == "0x" + dig.hex()
    assert eip712.recover(dig, res["signature"]) == res["signer"] == res["request"]["gid"]
    assert res["adapterMode"] == "symbolic"


def test_prepare_request_reproduces_agent1_vector_when_given_the_vector_request():
    v = next(x for x in VEC["vectors"] if x["name"] == "AccessRequest")
    td = v["typedData"]
    dep = copy.deepcopy(DEP)
    dep["chains"]["pbc"].update(chainId=td["domain"]["chainId"]); dep["chains"]["pbc"]["contracts"]["PSC"] = td["domain"]["verifyingContract"]
    dep["chains"]["dbc"]["chainId"] = td["message"]["destinationChainId"]; dep["chains"]["dbc"]["contracts"]["KSSC"] = td["message"]["kssc"]
    dep["fixture"]["keyEpoch"], dep["fixture"]["policyVersion"] = td["message"]["keyEpoch"], td["message"]["policyVersion"]
    r = call(inp={"request": td["message"], "signingKeyRef": "keyref:user:alice"}, dep=dep)
    assert r["ok"], r
    assert r["result"]["requestDigest"] == v["digest"] and r["result"]["signature"] == v["signature"]


@pytest.mark.parametrize("over,code", [
    ({"gid": "0x" + "11" * 20}, "WRONG_SUBJECT"),                                  # signing for another identity
    ({"kssc": "0x" + "11" * 20}, "WRONG_DESTINATION"),
    ({"psc": "0x" + "11" * 20}, "WRONG_DESTINATION"),
    ({"destinationChainId": "1"}, "WRONG_DESTINATION"),
    ({"sourceChainId": "1"}, "WRONG_DESTINATION"),
    ({"keyEpoch": "1"}, "WRONG_EPOCH"),
    ({"policyVersion": "2"}, "WRONG_EPOCH"),
    ({"nonce": "-1"}, "MALFORMED"),
    ({"nonce": 1}, "MALFORMED"),
    ({"gid": "0xC4FF0022E776C3471E39ABF6C69CE679440C956D"}, "MALFORMED"),
    ({"expiresAt": "1800000030\n"}, "MALFORMED"),
])
def test_prepare_request_refusals(over, code):
    r = call(inp=good_input(**over))
    check_envelope(r)
    assert not r["ok"] and r["error"]["code"] == code, r


@pytest.mark.parametrize("ref", ["alice", "keyref:witness:witness-1", "keyref:user:Alice", None, "keyref:user:alice\n"])
def test_bad_or_wrong_role_key_refs(ref):
    r = call(inp={"request": request(), "signingKeyRef": ref})
    assert not r["ok"] and r["error"]["code"] == "MALFORMED"


def test_input_must_have_exactly_the_documented_fields():
    for inp in ({"request": request()}, {**good_input(), "extra": 1}, [], None, "x"):
        r = call(inp=inp)
        assert not r["ok"] and r["error"]["code"] == "MALFORMED"


H = lambda n: "0x" + format(n, "064x")  # noqa: E731
CANONICAL_INPUTS = {
    "collect_decision": {"requestDigest": H(1)},
    "release": {"grantId": H(2)},
    "encrypt_record": {"record": {"dataId": H(3), "owner": "0x" + "44" * 20, "payloadDigest": H(5)},
                       "policy": {"clauses": [[{"role": H(6), "kind": "1", "issuerMode": "0"}, {"role": H(7), "kind": "2", "issuerMode": "2"}]]},
                       "keyEpoch": "0"},
    "finish_decryption": {"response": {"schemaVersion": "v1", "adapterMode": "symbolic", "requestDigest": H(1), "grantId": H(2), "dataId": H(3),
                                       "ciphertextDigest": H(8), "recipientKeyHash": H(9), "keyEpoch": "0",
                                       "responseEnvelope": {"kind": "symbolic-partial/v1", "token": H(10)}},
                          "userKeyRef": "keyref:user:alice"},
    "rotate_epoch": {"targetEpoch": "1"},
}


@pytest.mark.parametrize("op", ["collect_decision", "release", "encrypt_record", "finish_decryption"])
def test_unbuilt_e_operations_say_unavailable_never_succeed(op):
    r = call(op=op, inp=CANONICAL_INPUTS[op])
    check_envelope(r)
    assert not r["ok"] and r["error"]["code"] == "ADAPTER_UNAVAILABLE"


@pytest.mark.parametrize("op", ["collect_decision", "release", "encrypt_record", "finish_decryption", "rotate_epoch"])
def test_invalid_input_is_malformed_even_for_unbuilt_operations(op):
    """Revision 4: a request with an empty/extra-field/noncanonical input is a bad request, not 'unavailable'."""
    for bad in ({}, {**CANONICAL_INPUTS[op], "privateKey": "0x" + "11" * 32}, [], None):
        r = call(op=op, inp=bad)
        assert not r["ok"] and r["error"]["code"] == "MALFORMED", (op, bad)
    first = next(iter(CANONICAL_INPUTS[op]))
    if isinstance(CANONICAL_INPUTS[op][first], str):
        r = call(op=op, inp={**CANONICAL_INPUTS[op], first: CANONICAL_INPUTS[op][first] + "\n"})
        assert r["error"]["code"] == "MALFORMED"


def test_encrypt_record_rejects_unanchored_policy_before_anything_else():
    bad = copy.deepcopy(CANONICAL_INPUTS["encrypt_record"])
    bad["policy"]["clauses"][0][0]["issuerMode"] = "2"       # SAME_AS_FIRST cannot be a clause's first requirement (A32)
    assert call(op="encrypt_record", inp=bad)["error"]["code"] == "MALFORMED"


def test_rotate_epoch_is_not_implemented_in_phase():
    r = call(op="rotate_epoch", inp=CANONICAL_INPUTS["rotate_epoch"])
    assert not r["ok"] and r["error"]["code"] == "NOT_IMPLEMENTED_IN_PHASE"


def test_every_adapter_response_validates_against_the_revision4_response_rules():
    """Own revision-4 validators (hmbc_protocol.wire): requests canonical, responses bound to the pending operation."""
    from hmbc_protocol import wire
    cases = [("prepare_request", good_input())] + [(op, CANONICAL_INPUTS[op]) for op in CANONICAL_INPUTS]
    for op, inp in cases:
        env = {"schemaVersion": "v1", "operation": op, "input": inp, "deploymentManifest": DEP}
        wire.adapter_request(env)
        resp = adapter.handle_line(json.dumps(env))
        wire.adapter_response(resp)
        wire.adapter_response(resp, op)


@pytest.mark.parametrize("line", [
    "", "not json", "[]", "null", '{"schemaVersion":"v1"}', '{"a":1,"a":2}', "NaN",
    json.dumps({"schemaVersion": "v2", "operation": "prepare_request", "input": {}, "deploymentManifest": {}}),
    json.dumps({"schemaVersion": "v1", "operation": "rm -rf /", "input": {}, "deploymentManifest": DEP}),
    json.dumps({"schemaVersion": "v1", "operation": ["prepare_request"], "input": {}, "deploymentManifest": DEP}),
    json.dumps({"schemaVersion": "v1", "operation": "prepare_request", "input": {}, "deploymentManifest": DEP, "cmd": "x"}),
    json.dumps({"schemaVersion": "v1", "operation": "prepare_request", "input": good_input(), "deploymentManifest": {}}),
    json.dumps({"schemaVersion": "v1", "operation": "prepare_request", "input": good_input(), "deploymentManifest": None}),
    "x" * (adapter.MAX_LINE_BYTES + 1),
])
def test_malformed_lines_always_get_a_wellformed_error(line):
    r = adapter.handle_line(line)
    check_envelope(r)
    assert not r["ok"] and r["error"]["code"] in {"MALFORMED"}


def test_duplicate_key_rejected_even_when_last_value_wins_would_succeed():
    """Last-wins parsing would turn this into a perfectly valid request, so only duplicate rejection stops it."""
    good = json.dumps({"schemaVersion": "v1", "operation": "prepare_request", "input": good_input(), "deploymentManifest": DEP})
    assert adapter.handle_line(good)["ok"]
    dup_nested = good.replace('"nonce": "1"', '"nonce": "999", "nonce": "1"')
    dup_top = good.replace('"operation"', '"operation": "release", "operation"', 1)
    for line in (dup_nested, dup_top):
        assert line != good
        r = adapter.handle_line(line)
        assert not r["ok"] and r["error"]["code"] == "MALFORMED" and "duplicate" in r["error"]["message"]


def test_oversize_line_rejected_even_if_otherwise_valid():
    good = json.dumps({"schemaVersion": "v1", "operation": "prepare_request", "input": good_input(), "deploymentManifest": DEP})
    padded = good + " " * adapter.MAX_LINE_BYTES            # still one valid JSON document, only too long
    r = adapter.handle_line(padded)
    assert not r["ok"] and r["error"]["code"] == "MALFORMED" and "1 MiB" in r["error"]["message"]


def test_wrong_schema_version_rejected_even_if_otherwise_valid():
    for ver in ("v2", "v0", 1, None):
        line = json.dumps({"schemaVersion": ver, "operation": "prepare_request", "input": good_input(), "deploymentManifest": DEP})
        r = adapter.handle_line(line)
        assert not r["ok"] and r["error"]["code"] == "MALFORMED" and "schemaVersion" in r["error"]["message"]


def test_no_response_ever_contains_private_key_material():
    outs = [call(inp=good_input()), call(inp=good_input(gid="0x" + "11" * 20)),
            call(inp={"request": request(), "signingKeyRef": "keyref:user:alice\n"}), adapter.handle_line("{")]
    blob = json.dumps(outs)
    assert ALICE_KEY not in blob and ALICE_KEY[2:] not in blob


def test_internal_failure_does_not_leak(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("secret " + ALICE_KEY)
    monkeypatch.setitem(adapter.OPERATIONS["prepare_request"], "handler", boom)
    r = call(inp=good_input())
    assert r["error"]["code"] == "ADAPTER_UNAVAILABLE" and ALICE_KEY not in json.dumps(r)


def test_subprocess_jsonl_roundtrip_one_response_per_line(tmp_path):
    env_line = json.dumps({"schemaVersion": "v1", "operation": "prepare_request", "input": good_input(), "deploymentManifest": DEP})
    p = subprocess.run([sys.executable, "-m", "hmbc_protocol.adapter", "--state-dir", str(tmp_path / "state")],
                       input=env_line + "\n\nnot json\n" + env_line + "\n", text=True, capture_output=True,
                       cwd=pathlib.Path(__file__).parent.parent, env={"PYTHONPATH": ".", "PATH": "/usr/bin:/bin"})
    assert p.returncode == 0, p.stderr
    lines = p.stdout.splitlines()
    assert len(lines) == 4
    rs = [json.loads(x) for x in lines]
    assert [r["ok"] for r in rs] == [True, False, False, True] and rs[0] == rs[3]   # deterministic signature
    assert (tmp_path / "state").stat().st_mode & 0o077 == 0
