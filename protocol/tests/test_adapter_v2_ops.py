"""Successor adapter handlers, part 1 (agent 2, F task 2 slice 6b-1). Written BEFORE hmbc_protocol/adapter_v2_ops.py existed.

The non-witness operations behind `adapter_v2`: `prepare_request` (the user's signing client, offline), and the key worker's `encrypt_record`, `release`, `finish_decryption`. They REUSE the carried E code
unchanged (`adapter.prepare_request`, `worker.Worker`) and do exactly two things on top: D-4, the relabel of the result from schemaVersion "v1" to "v2" (the published v2 result types carry const "v2"; the
carried E validators and handlers produce "v1"), and the mapping of every E failure onto the closed v2 errors without leaking internals. Every result is validated against the PUBLISHED schema
(byte-copied fixture). The worker is an INJECTED object here: its three methods are stubs returning E-shaped results (checked with the carried E result validators first); the real worker on a live ledger is
the carried E suite's business and an integrated run's, not this file's. The witness operations (collect_*, attest_grant, collect_governance) are the next slice.
"""
import copy
import json
import os

import jsonschema
import pytest

from hmbc_protocol import adapter_v2 as av2
from hmbc_protocol import adapter_v2_ops as ops
from hmbc_protocol import chain, eip712, keys, messages, wire
from hmbc_protocol.worker import WorkerError

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FX = os.path.join(ROOT, "protocol", "tests", "fixtures")
SCHEMA = json.load(open(os.path.join(FX, "agent3-v2.1-hmbc.schema.json")))
F2 = json.load(open(os.path.join(FX, "agent1-85c59f5-f-base-deployment.json")))
E21 = json.load(open(os.path.join(FX, "agent1-85c59f5-e-successor-v2.1-deployment.json")))
H = "0x" + "ab" * 32
G = "0x" + "cd" * 32
KEYREF = "keyref:user:alice"
_, SIGNER = keys.resolve(KEYREF, ("user",))


def sv(name):
    return jsonschema.Draft202012Validator({"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": "#/$defs/" + name, "$defs": SCHEMA["$defs"]})


V_RESP = sv("AdapterResponse")


def request_for(dep, **over):
    pbc, dbc, fx = dep["chains"]["pbc"], dep["chains"]["dbc"], dep["fixture"]
    r = {"sourceChainId": pbc["chainId"], "destinationChainId": dbc["chainId"], "psc": pbc["contracts"]["PSC"], "kssc": dbc["contracts"]["KSSC"], "gid": SIGNER, "dataId": H, "action": "1",
         "policyVersion": fx["policyVersion"], "authEpoch": "3", "keyEpoch": fx["keyEpoch"], "nonce": "7", "expiresAt": "1020", "recipientKeyHash": keys.recipient_key_hash(KEYREF)}
    r.update(over)
    return r


def line(op, inp, dep):
    return json.dumps({"schemaVersion": "v2", "operation": op, "input": inp, "deploymentManifest": dep})


def run(op, inp, handlers, dep=F2, rev="v2"):
    c = av2.Context(manifest=dep, schema_revision=rev, handlers=handlers, schema=SCHEMA)
    r = av2.handle_line(line(op, inp, dep), c)
    assert V_RESP.is_valid(r), (r, list(V_RESP.iter_errors(r))[:1])
    return r


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# prepare_request: the user's signing client, real code, no chain
# --------------------------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("dep,rev", [(F2, "v2"), (E21, "v2.1")], ids=["F", "E v2.1"])
def test_prepare_request_signs_for_the_referenced_user_and_returns_a_schema_valid_v2_result(dep, rev):
    inp = {"request": request_for(dep), "signingKeyRef": KEYREF}
    r = run("prepare_request", inp, {"prepare_request": ops.prepare_request}, dep, rev)
    assert r["ok"] is True and r["result"]["schemaVersion"] == "v2" and r["result"]["adapterMode"] == "symbolic"
    res = r["result"]
    digest = messages.digest_of("AccessRequest", res["request"], messages.domain_for("AccessRequest", res["request"], dep))
    assert res["requestDigest"] == "0x" + digest.hex() and res["signer"] == SIGNER and eip712.recover(digest, res["signature"]) == SIGNER
    assert res["request"] == inp["request"]


@pytest.mark.parametrize("over,code", [
    (dict(gid="0x" + "99" * 20), "WRONG_SUBJECT"), (dict(sourceChainId="1"), "WRONG_DESTINATION"), (dict(destinationChainId="1"), "WRONG_DESTINATION"), (dict(psc="0x" + "99" * 20), "WRONG_DESTINATION"),
    (dict(kssc="0x" + "99" * 20), "WRONG_DESTINATION"), (dict(policyVersion="99"), "WRONG_EPOCH")])
def test_prepare_request_refuses_a_request_that_is_not_the_users_or_not_this_deployments(over, code):
    r = run("prepare_request", {"request": request_for(F2, **over), "signingKeyRef": KEYREF}, {"prepare_request": ops.prepare_request})
    assert r["ok"] is False and r["error"]["code"] == code and "reason" not in r["error"]


def test_prepare_request_refuses_a_key_reference_of_another_role_and_never_signs():
    r = run("prepare_request", {"request": request_for(F2), "signingKeyRef": "keyref:witness:witness-1"}, {"prepare_request": ops.prepare_request})
    assert r["ok"] is False and r["error"]["code"] == "MALFORMED"


def test_the_result_is_the_carried_e_result_relabelled_and_nothing_else():
    from hmbc_protocol import adapter as e
    inp = {"request": request_for(F2), "signingKeyRef": KEYREF}
    old = e.prepare_request(copy.deepcopy(inp), F2)
    new = ops.prepare_request(copy.deepcopy(inp), av2.Context(manifest=F2, schema_revision="v2", handlers={}))
    assert old["schemaVersion"] == "v1" and new["schemaVersion"] == "v2" and {k: v for k, v in old.items() if k != "schemaVersion"} == {k: v for k, v in new.items() if k != "schemaVersion"}


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the worker operations: relabel and error mapping
# --------------------------------------------------------------------------------------------------------------------------------------------------------
RELEASE_V1 = {"schemaVersion": "v1", "adapterMode": "symbolic", "requestDigest": H, "grantId": H, "dataId": H, "ciphertextDigest": H, "recipientKeyHash": H, "keyEpoch": "0",
              "responseEnvelope": {"kind": wire.SYMBOLIC_ENVELOPE_KIND, "token": H}}
ENCRYPT_V1 = {"schemaVersion": "v1", "adapterMode": "symbolic", "dataId": H, "keyEpoch": "0", "ciphertextDigest": H, "policyDigest": H}
FINISH_V1 = {"schemaVersion": "v1", "adapterMode": "symbolic", "decryptable": True, "dataId": H, "ciphertextDigest": H}
POLICY = {"clauses": [[{"role": H, "kind": "1", "issuerMode": "0"}]]}


class StubWorker:
    def __init__(self, **results):
        self.results, self.calls = results, []

    def encrypt_record(self, record, policy, key_epoch):
        self.calls.append(("encrypt_record", record, policy, key_epoch))
        return self._r("encrypt_record")

    def release(self, grant_id):
        self.calls.append(("release", grant_id))
        return self._r("release")

    def finish_decryption(self, response, user_key_ref):
        self.calls.append(("finish_decryption", response, user_key_ref))
        return self._r("finish_decryption")

    def _r(self, name):
        v = self.results[name]
        if isinstance(v, Exception):
            raise v
        return copy.deepcopy(v)


def handlers(worker):
    return ops.worker_handlers(lambda ctx: worker)


def test_the_stub_results_are_valid_for_the_carried_e_validators():
    wire.release_result(RELEASE_V1)
    wire.encrypt_record_result(ENCRYPT_V1)
    wire.finish_decryption_result(FINISH_V1)


def test_each_worker_result_is_relabelled_v2_and_valid_against_the_published_result_type():
    w = StubWorker(encrypt_record=ENCRYPT_V1, release=RELEASE_V1, finish_decryption=FINISH_V1)
    h = handlers(w)
    a = run("encrypt_record", {"record": {"dataId": H, "owner": "0x" + "11" * 20, "payloadDigest": H}, "policy": POLICY, "keyEpoch": "0"}, h)
    b = run("release", {"grantId": G}, h)
    v2_release = dict(RELEASE_V1, schemaVersion="v2")
    c = run("finish_decryption", {"response": v2_release, "userKeyRef": KEYREF}, h)
    for r, v1 in ((a, ENCRYPT_V1), (b, RELEASE_V1), (c, FINISH_V1)):
        assert r["ok"] is True and r["result"] == dict(v1, schemaVersion="v2")
    assert [x[0] for x in w.calls] == ["encrypt_record", "release", "finish_decryption"] and w.calls[1] == ("release", G)
    assert w.calls[0] == ("encrypt_record", {"dataId": H, "owner": "0x" + "11" * 20, "payloadDigest": H}, POLICY, "0")


def test_finish_decryption_hands_the_worker_the_release_result_in_the_form_the_worker_knows():
    """The worker is the carried E class: its `finish_decryption` validates a `schemaVersion` "v1" ReleaseResult. A v2 response from the caller is relabelled back to v1 for the worker."""
    w = StubWorker(finish_decryption=FINISH_V1)
    run("finish_decryption", {"response": dict(RELEASE_V1, schemaVersion="v2"), "userKeyRef": KEYREF}, handlers(w))
    (_, response, key), = w.calls
    assert response == RELEASE_V1 and key == KEYREF


@pytest.mark.parametrize("name", ["encrypt_record", "release", "finish_decryption"])
def test_a_worker_result_that_is_not_the_e_result_shape_is_an_internal_failure_not_relabelled_garbage(name):
    inp = {"encrypt_record": {"record": {"dataId": H, "owner": "0x" + "11" * 20, "payloadDigest": H}, "policy": POLICY, "keyEpoch": "0"}, "release": {"grantId": H},
           "finish_decryption": {"response": dict(RELEASE_V1, schemaVersion="v2"), "userKeyRef": KEYREF}}[name]
    for bad in (dict(ENCRYPT_V1, schemaVersion="v2"), {"schemaVersion": "v1"}, {}, "x", None, dict(RELEASE_V1, extra=1)):
        w = StubWorker(**{name: bad})
        r = run(name, inp, handlers(w))
        assert r["ok"] is False and r["error"] == {"code": "ADAPTER_UNAVAILABLE", "message": "internal adapter failure"}


@pytest.mark.parametrize("code", sorted(wire.ERROR_CODES - {"NOT_IMPLEMENTED_IN_PHASE"}))
def test_a_worker_error_keeps_its_closed_code_and_message(code):
    w = StubWorker(release=WorkerError(code, "because of the ledger"))
    r = run("release", {"grantId": H}, handlers(w))
    assert r["ok"] is False and r["error"] == {"code": code, "message": "because of the ledger"}


def test_a_ledger_rejection_and_a_chain_failure_are_mapped_without_leaking():
    r = run("release", {"grantId": H}, handlers(StubWorker(release=chain.Rejected("EXPIRED"))))
    assert r["error"]["code"] == "EXPIRED" and "secret" not in json.dumps(r)
    r = run("release", {"grantId": H}, handlers(StubWorker(release=chain.Rejected("NOT_A_CODE"))))
    assert r["error"] == {"code": "ADAPTER_UNAVAILABLE", "message": "the ledger rejected the call: NOT_A_CODE"}
    r = run("release", {"grantId": H}, handlers(StubWorker(release=chain.ChainError("http://127.0.0.1:38545 secret-token refused"))))
    assert r["error"] == {"code": "ADAPTER_UNAVAILABLE", "message": "the ledger is unreachable or returned an error"} and "secret" not in json.dumps(r)


def test_an_unexpected_worker_exception_is_the_generic_failure():
    r = run("release", {"grantId": H}, handlers(StubWorker(release=RuntimeError("secret path /home/x/.keys"))))
    assert r["error"] == {"code": "ADAPTER_UNAVAILABLE", "message": "internal adapter failure"}


def test_the_worker_factory_is_asked_per_call_with_the_context():
    seen = []

    def factory(ctx):
        seen.append(ctx)
        return StubWorker(release=RELEASE_V1)
    h = ops.worker_handlers(factory)
    c = av2.Context(manifest=F2, schema_revision="v2", handlers=h, schema=SCHEMA)
    for _ in range(2):
        assert av2.handle_line(line("release", {"grantId": H}, F2), c)["ok"] is True
    assert seen == [c, c]


def test_only_the_three_worker_operations_are_provided():
    assert set(ops.worker_handlers(lambda ctx: None)) == {"encrypt_record", "release", "finish_decryption"}
