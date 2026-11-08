"""Output validation of the successor adapter (agent 2, F task 2 slice 6d). Written BEFORE `Context` validated responses.

A3-0089 named two limits of the isolated API: `Context(schema=None)` applies no published schema, and an injected handler may return an arbitrary dict. When the PUBLISHED schema is supplied, `handle_line` now
checks every response it is about to emit against the published response type of the operation (`<Op>Response`; `AdapterResponse` when the operation is not even known) and, on any mismatch, emits the generic
internal failure instead (fail closed, nothing of the invalid value leaks). Without the schema nothing is checked: that stays an explicit, tested limit. The schema must define every response type or the Context
is refused at construction.
"""
import copy
import json
import os

import jsonschema
import pytest

from hmbc_protocol import adapter_v2 as av2
from hmbc_protocol.adapter_v2 import OperationError

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FX = os.path.join(ROOT, "protocol", "tests", "fixtures")
SCHEMA = json.load(open(os.path.join(FX, "agent3-v2.1-hmbc.schema.json")))
F2 = json.load(open(os.path.join(FX, "agent1-85c59f5-f-base-deployment.json")))
H = "0x" + "ab" * 32
GENERIC = ("ADAPTER_UNAVAILABLE", "internal adapter failure")
V_RESP = jsonschema.Draft202012Validator({"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": "#/$defs/AdapterResponse", "$defs": SCHEMA["$defs"]}, format_checker=jsonschema.FormatChecker())


def line(op, inp):
    return json.dumps({"schemaVersion": "v2", "operation": op, "input": inp, "deploymentManifest": F2})


def ctx(handlers, schema=SCHEMA):
    return av2.Context(manifest=F2, schema_revision="v2", handlers=handlers, schema=schema)


def generic(r):
    return r["ok"] is False and r["error"]["code"] == GENERIC[0] and r["error"]["message"] == GENERIC[1] and set(r["error"]) == {"code", "message"}


# a result that is certainly valid is easiest to get from a real handler of the ops slice: use prepare_request, a pure offline operation
def prepare_handler():
    from hmbc_protocol import adapter_v2_ops as ops
    return ops.prepare_request


def prepare_input():
    from test_adapter_v2_ops import KEYREF, request_for
    return {"request": request_for(F2), "signingKeyRef": KEYREF}


def test_a_schema_valid_result_passes_through_unchanged_with_and_without_the_schema():
    inp = prepare_input()
    a = av2.handle_line(line("prepare_request", inp), ctx({"prepare_request": prepare_handler()}))
    b = av2.handle_line(line("prepare_request", inp), ctx({"prepare_request": prepare_handler()}, schema=None))
    assert a["ok"] is True and a == b and V_RESP.is_valid(a)


@pytest.mark.parametrize("damage", [lambda r: r.pop("signature"), lambda r: r.update(schemaVersion="v1"), lambda r: r.update(extra="x"), lambda r: r.update(adapterMode="live"),
                                    lambda r: r.update(signer="not-an-address"), lambda r: r.update(requestDigest=5)], ids=["missing key", "wrong schemaVersion", "extra key", "wrong mode", "bad address", "bad hash"])
def test_a_handler_result_that_breaks_the_published_type_becomes_the_generic_failure_when_the_schema_is_supplied(damage):
    h = prepare_handler()

    def bad(inp, c):
        r = h(inp, c)
        damage(r)
        return r
    r = av2.handle_line(line("prepare_request", prepare_input()), ctx({"prepare_request": bad}))
    assert generic(r) and V_RESP.is_valid(r)
    unchecked = av2.handle_line(line("prepare_request", prepare_input()), ctx({"prepare_request": bad}, schema=None))
    assert unchecked["ok"] is True                              # the documented limit without the schema: the invalid value goes out


def test_a_refusal_the_published_response_type_forbids_becomes_the_generic_failure():
    rec = {"message": {"a": "b"}, "signature": "0x" + "00" * 65}

    def pinned(inp, c):                                         # `recorded` is allowed for a checkpoint only; the decision response forbids it
        raise OperationError("STALE_STATE", "pinned", reason="CONFLICT_PINNED", recorded=rec)
    r = av2.handle_line(line("collect_decision", {"requestDigest": H}), ctx({"collect_decision": pinned}))
    assert generic(r)
    assert av2.handle_line(line("collect_decision", {"requestDigest": H}), ctx({"collect_decision": pinned}, schema=None))["error"]["recorded"] == rec


def test_every_response_the_adapter_builds_for_the_common_errors_is_schema_valid_and_unchanged():
    c = ctx({})
    cases = [("not json", None), (line("collect_decision", {"requestDigest": "bad"}), None), (line("rotate_epoch", {"targetEpoch": "1"}), "NOT_IMPLEMENTED_IN_PHASE"), (line("release", {"grantId": H}), "ADAPTER_UNAVAILABLE")]
    for text, code in cases:
        r = av2.handle_line(text, c)
        assert r["ok"] is False and V_RESP.is_valid(r)
        if code:
            assert r["error"]["code"] == code
    unknown = json.dumps({"schemaVersion": "v2", "operation": "nope", "input": {}, "deploymentManifest": F2})
    assert av2.handle_line(unknown, c)["error"]["code"] == "MALFORMED"


def test_a_non_object_result_is_still_the_generic_failure():
    r = av2.handle_line(line("release", {"grantId": H}), ctx({"release": lambda inp, c: "x"}))
    assert generic(r)


def test_a_schema_that_cannot_validate_responses_is_refused_at_construction():
    for name in ("AdapterResponse", "CollectDecisionResponse", "RotateEpochResponse"):
        broken = copy.deepcopy(SCHEMA)
        del broken["$defs"][name]
        with pytest.raises(ValueError):
            ctx({}, schema=broken)


def test_the_response_validators_are_built_once_not_per_line():
    c = ctx({})
    v = c._response_validators
    av2.handle_line("not json", c)
    av2.handle_line("not json", c)
    assert c._response_validators is v and len(v) == 10          # AdapterResponse and the nine per-operation response types


def test_the_generic_failure_itself_is_a_valid_response():
    assert V_RESP.is_valid(av2._generic())


def test_check_responses_must_be_a_boolean_and_false_turns_the_check_off_even_with_the_schema():
    for bad in (None, 1, "yes"):
        with pytest.raises(ValueError):
            av2.Context(manifest=F2, schema_revision="v2", handlers={}, schema=SCHEMA, check_responses=bad)
    off = av2.Context(manifest=F2, schema_revision="v2", handlers={"release": lambda i, c: {"called": True}}, schema=SCHEMA, check_responses=False)
    assert av2.handle_line(line("release", {"grantId": H}), off)["result"] == {"called": True}
    on = av2.Context(manifest=F2, schema_revision="v2", handlers={"release": lambda i, c: {"called": True}}, schema=SCHEMA)
    assert generic(av2.handle_line(line("release", {"grantId": H}), on))


def test_a_validator_that_cannot_decide_means_no_response_is_emitted_only_the_generic_failure():
    class Boom:
        def is_valid(self, _):
            raise RuntimeError("cannot decide")

    c = ctx({"release": lambda i, k: {"called": True}})
    c._response_validators["ReleaseResponse"] = Boom()
    assert generic(av2.handle_line(line("release", {"grantId": H}), c))


def test_the_published_patterns_are_enforced_on_a_result():
    h = prepare_handler()

    def bad(inp, c):
        r = h(inp, c)
        r["requestDigest"] = "0x" + "AB" * 32                 # upper-case hex: the published Hash type is lower-case only
        return r
    assert generic(av2.handle_line(line("prepare_request", prepare_input()), ctx({"prepare_request": bad})))


SECP_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


def broken_prepare(damage):
    h = prepare_handler()

    def bad(inp, c):
        r = h(inp, c)
        damage(r)
        return r
    return av2.handle_line(line("prepare_request", prepare_input()), ctx({"prepare_request": bad}))


def test_the_published_custom_formats_are_enforced_not_ignored():
    # `format: uint64` is an annotation unless a checker is registered; 20 digits satisfy the pattern and maxLength of Uint64 but exceed 2**64 - 1
    assert generic(broken_prepare(lambda r: r["request"].update(expiresAt="99999999999999999999")))
    assert generic(broken_prepare(lambda r: r["request"].update(expiresAt="18446744073709551616")))
    assert broken_prepare(lambda r: r["request"].update(expiresAt="18446744073709551615"))["ok"] is True          # the largest uint64 is fine


def test_a_high_s_signature_is_not_canonical_and_is_refused_on_a_result():
    def high_s(r):
        sig = r["signature"]
        rr, ss, v = int(sig[2:66], 16), int(sig[66:130], 16), int(sig[130:], 16)
        r["signature"] = "0x%064x%064x%02x" % (rr, SECP_N - ss, 27 + (1 - (v - 27)))
    assert generic(broken_prepare(high_s))
    assert broken_prepare(lambda r: None)["ok"] is True


def test_a_result_valid_for_another_operation_is_refused_for_this_one():
    prepared = prepare_handler()(prepare_input(), ctx({}))        # a perfectly valid PrepareRequestResult
    r = av2.handle_line(line("collect_decision", {"requestDigest": H}), ctx({"collect_decision": lambda i, c: prepared}))
    assert generic(r)
    assert av2.handle_line(line("prepare_request", prepare_input()), ctx({"prepare_request": prepare_handler()}))["ok"] is True
