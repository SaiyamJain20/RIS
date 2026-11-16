"""Successor adapter front-end (agent 2, F task 2 slice 6a). Written BEFORE hmbc_protocol/adapter_v2.py existed.

This slice is the successor adapter's BOUNDARY only: strict JSON-lines parsing, the v2 request/response envelopes, EXPLICIT schema-revision selection (v2 or v2.1, never guessed), whole-manifest equality with the
pinned manifest, v2 input validation (the three `collect_*`/`attest_grant` inputs gain `witnessSetVersion` 1|2 and `witnessIndex`; `collect_governance` is new; `finish_decryption` now carries a v2 `ReleaseResult`),
the reason table, one total `handle_line`, and the serve loop. Operation HANDLERS are injected: wiring the pool, the witness service, the worker store and the open-time checks behind them is the next slice. The carried
E adapter (`adapter.py`) is untouched and stays the v1 adapter.

Evidence discipline: the PUBLISHED schema (agent 3's `interfaces/v2.1/hmbc.schema.json`, d43c3a9a..) is a byte-identical fixture of this repository (`tests/fixtures/agent3-interfaces-provenance.json`), so every request and error
response here is validated against it offline, and the input validators are differentially tested against its `*Input` definitions. Same project, same model: a cross-check against published bytes, not an external oracle.
A finding kept as a test: the carried E `wire.finish_decryption_input` requires a `ReleaseResult` with `schemaVersion` "v1", and v2 requires "v2", so the E validators cannot be reused for that operation.
"""
import ast
import copy
import io
import itertools
import json
import os

import jsonschema
import pytest

from hmbc_protocol import adapter_v2 as av2

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FX = os.path.join(ROOT, "protocol", "tests", "fixtures")
SCHEMA = json.load(open(os.path.join(FX, "agent3-v2.1-hmbc.schema.json")))
REASONS = json.load(open(os.path.join(FX, "agent3-v2-reason-codes.json")))
E21 = json.load(open(os.path.join(FX, "agent1-85c59f5-e-successor-v2.1-deployment.json")))
F2 = json.load(open(os.path.join(FX, "agent1-85c59f5-f-base-deployment.json")))
H = "0x" + "ab" * 32
ADDR = "0x" + "11" * 20
SIG = "0x" + "cd" * 65


FORMATS = jsonschema.FormatChecker()


@FORMATS.checks("user-key-ref")
def _user_key_ref(v):
    """The schema NAMES this format and bounds it at 76 characters ("keyref:user:" plus at most 64); the pattern is the carried E/v0 rule (wire._USER_KEY_REF), registered here so the differential is not blind to it."""
    import re
    return not isinstance(v, str) or re.fullmatch(r"keyref:user:[a-z0-9][a-z0-9-]{0,63}", v) is not None


def sv(name):
    return jsonschema.Draft202012Validator({"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": "#/$defs/" + name, "$defs": SCHEMA["$defs"]}, format_checker=FORMATS)


V_REQ, V_RESP = sv("AdapterRequest"), sv("AdapterResponse")
INPUT_DEF = {"prepare_request": "PrepareRequestInput", "collect_decision": "CollectDecisionInput", "collect_checkpoint": "CollectCheckpointInput", "attest_grant": "AttestGrantInput",
             "collect_governance": "CollectGovernanceInput", "release": "ReleaseInput", "encrypt_record": "EncryptRecordInput", "finish_decryption": "FinishDecryptionInput", "rotate_epoch": "RotateEpochInput"}
ACCESS_REQUEST = {"sourceChainId": "18545", "destinationChainId": "28545", "psc": ADDR, "kssc": "0x" + "22" * 20, "gid": "0x" + "33" * 20, "dataId": H, "action": "1", "policyVersion": "1", "authEpoch": "3",
                  "keyEpoch": "0", "nonce": "7", "expiresAt": "1020", "recipientKeyHash": H}
RELEASE_RESULT = {"schemaVersion": "v2", "adapterMode": "symbolic", "requestDigest": H, "grantId": H, "dataId": H, "ciphertextDigest": H, "recipientKeyHash": H, "keyEpoch": "0",
                  "responseEnvelope": {"kind": "symbolic-partial/v1", "token": H}}
GOV = {"action": "1", "root": "0x" + "88" * 20, "admins": ["0x" + "11" * 20, "0x" + "22" * 20], "nonce": "1", "witnessSetVersion": "2", "expiresAt": "1800000060"}
BASE = {"prepare_request": {"request": ACCESS_REQUEST, "signingKeyRef": "keyref:user:alice"}, "collect_decision": {"requestDigest": H}, "collect_checkpoint": {}, "attest_grant": {"grantId": H},
        "collect_governance": GOV, "release": {"grantId": H}, "encrypt_record": {"record": {"dataId": H, "owner": ADDR, "payloadDigest": H}, "policy": {"clauses": [[{"role": H, "kind": "1", "issuerMode": "0"}]]}, "keyEpoch": "0"},
        "finish_decryption": {"response": RELEASE_RESULT, "userKeyRef": "keyref:user:alice"}, "rotate_epoch": {"targetEpoch": "1"}}
OPS = list(INPUT_DEF)


def line(op, inp, manifest=None, schema="v2"):
    return json.dumps({"schemaVersion": schema, "operation": op, "input": inp, "deploymentManifest": F2 if manifest is None else manifest})


def ctx(manifest=F2, revision="v2", handlers=None):
    return av2.Context(manifest=manifest, schema_revision=revision, handlers=handlers or {}, schema=SCHEMA, check_responses=False)          # these tests are about dispatch with small STUB results; output validation is test_adapter_v2_output.py


def is_error_response(r):
    return V_RESP.is_valid(r) and r["ok"] is False


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the fixtures are the published bytes
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_fixtures_are_agent_3_and_agent_1s_published_bytes():
    import hashlib
    prov = json.load(open(os.path.join(FX, "agent3-interfaces-provenance.json")))
    for name, meta in prov["files"].items():
        assert hashlib.sha256(open(os.path.join(FX, name), "rb").read()).hexdigest() == meta["sha256"], name
    assert prov["files"]["agent3-v2.1-hmbc.schema.json"]["sha256"] == "d43c3a9a4cbb10214135afb767a2adc109da462f88bd11a81a8c8955d44fd1f3"
    assert E21["schemaVersion"] == "hmbc-ledger-deployment/v2.1" and F2["schemaVersion"] == "hmbc-ledger-deployment/v2"


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# explicit schema selection and whole-manifest equality
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_schema_revision_is_selected_explicitly_and_the_v2_1_marker_needs_the_v2_1_revision():
    assert ctx(F2, "v2").schema_revision == "v2" and ctx(E21, "v2.1").schema_revision == "v2.1"
    assert ctx(F2, "v2.1").schema_revision == "v2.1"                                                # F carriers are valid under both revisions (they are unchanged)
    with pytest.raises(ValueError):
        av2.Context(manifest=E21, schema_revision="v2", handlers={})                                # the v2.1 marker is refused under revision v2, with or without a schema
    with pytest.raises(ValueError):
        av2.Context(manifest=E21, schema_revision="v2", handlers={}, schema=SCHEMA)
    for rev in ("v2.2", "v1", "", None, 2):
        with pytest.raises(ValueError):
            av2.Context(manifest=F2, schema_revision=rev, handlers={})
    with pytest.raises(TypeError):
        av2.Context(manifest=F2, handlers={})                                                     # never defaulted, never guessed


def test_the_old_ten_source_e_carrier_is_historical_compatibility_valid_under_both_revisions():
    ten = copy.deepcopy(E21)
    ten["schemaVersion"] = "hmbc-ledger-deployment/v2"
    ten["sources"] = {k: E21["sources"][k] for k in list(E21["sources"])[:10]}
    ten["sources"].pop("src/Governance.sol", None)
    if len(ten["sources"]) != 10:
        ten["sources"] = {k: v for k, v in E21["sources"].items() if k not in ("src/Governance.sol", "src/interfaces/IPolicyVersion.sol")}
    assert len(ten["sources"]) == 10
    assert ctx(ten, "v2").schema_revision == "v2" and ctx(ten, "v2.1").schema_revision == "v2.1"


@pytest.mark.parametrize("marker", ["hmbc-ledger-deployment/v2.2", "hmbc-ledger-deployment/v1", "x", None, 2])
def test_an_unknown_or_missing_carrier_marker_cannot_be_pinned(marker):
    m = copy.deepcopy(F2)
    m["schemaVersion"] = marker
    with pytest.raises(ValueError):
        av2.Context(manifest=m, schema_revision="v2", handlers={})
    m.pop("schemaVersion")
    with pytest.raises(ValueError):
        av2.Context(manifest=m, schema_revision="v2", handlers={})


def test_a_pinned_manifest_that_the_selected_schema_refuses_cannot_be_pinned():
    m = copy.deepcopy(F2)
    m["unexpected"] = "x"                                                                          # the schema's carriers are closed
    with pytest.raises(ValueError):
        av2.Context(manifest=m, schema_revision="v2", handlers={}, schema=SCHEMA)
    m = copy.deepcopy(E21)
    m["sources"] = dict(list(m["sources"].items())[:10])                                          # v2.1 marker with ten sources
    with pytest.raises(ValueError):
        av2.Context(manifest=m, schema_revision="v2.1", handlers={}, schema=SCHEMA)
    m = copy.deepcopy(E21)
    m["schemaVersion"] = "hmbc-ledger-deployment/v2"                                               # the v2 marker with the twelve-source map: neither carrier
    with pytest.raises(ValueError):
        av2.Context(manifest=m, schema_revision="v2.1", handlers={}, schema=SCHEMA)
    broken = {k: v for k, v in SCHEMA.items()}
    broken["$defs"] = {k: v for k, v in SCHEMA["$defs"].items() if k != "LedgerDeploymentEComplete"}      # a schema without the v2.1 carrier cannot serve revision v2.1
    with pytest.raises(ValueError):
        av2.Context(manifest=F2, schema_revision="v2.1", handlers={}, schema=broken)


def test_the_whole_manifest_must_equal_the_pinned_one_a_different_carrier_or_member_is_refused():
    c = ctx(F2, "v2", {"release": lambda i, k: {"called": True}})
    ok = av2.handle_line(line("release", {"grantId": H}, F2), c)
    assert ok == {"schemaVersion": "v2", "ok": True, "result": {"called": True}, "error": None}
    for other in (E21, dict(F2, createdAt="2099-01-01T00:00:00Z"), dict(F2, producer="someone else"), {k: v for k, v in F2.items() if k != "mutantNote"}):
        r = av2.handle_line(line("release", {"grantId": H}, other), c)
        assert r["error"]["code"] == "WRONG_DESTINATION" and r["ok"] is False and r["result"] is None
    reordered = dict(reversed(list(F2.items())))
    assert av2.handle_line(line("release", {"grantId": H}, reordered), c)["ok"] is True                    # equality of the manifest, not of its key order


def test_a_manifest_that_lacks_what_binds_a_request_is_malformed():
    c = ctx()
    for bad in (None, [], "x", 5, {}, {"chains": {}}, {"chains": {"pbc": {}, "dbc": {}}, "fixture": {}}):
        text = json.dumps({"schemaVersion": "v2", "operation": "release", "input": {"grantId": H}, "deploymentManifest": bad})
        r = av2.handle_line(text, c)
        assert r["error"]["code"] == "MALFORMED", bad


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the envelope, strict parsing, totality
# --------------------------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("op", OPS)
def test_a_well_formed_request_of_every_operation_validates_against_the_published_request_schema(op):
    req = json.loads(line(op, BASE[op]))
    errs = sorted(V_REQ.iter_errors(req), key=str)
    assert not errs, errs[:1]


def test_the_closed_request_envelope():
    c = ctx(handlers={"release": lambda i, k: {"x": 1}})
    good = json.loads(line("release", {"grantId": H}))
    assert av2.handle_line(json.dumps(good), c)["ok"] is True
    for mutate in (lambda r: r.update(extra=1), lambda r: r.pop("input"), lambda r: r.pop("deploymentManifest"), lambda r: r.update(schemaVersion="v1"), lambda r: r.update(schemaVersion="v2.1"),
                   lambda r: r.update(schemaVersion=2), lambda r: r.update(operation="nonsense"), lambda r: r.update(operation=7), lambda r: r.update(operation=None), lambda r: r.update(input=[])):
        r = copy.deepcopy(good)
        mutate(r)
        resp = av2.handle_line(json.dumps(r), c)
        assert resp["ok"] is False and resp["error"]["code"] == "MALFORMED", r


GARBAGE = ["", " ", "{", "}", "null", "[]", "1", '"x"', "true", "NaN", '{"a": NaN}', '{"a": Infinity}', '{"a": -Infinity}', '{"schemaVersion":"v2","schemaVersion":"v2"}', '﻿{"schemaVersion":"v2"}',
           '{"schemaVersion":"v2"} trailing', '{"schemaVersion":"v2"}{"x":1}', "[" * 5000 + "]" * 5000, '{"a":' * 3000 + "1" + "}" * 3000, "\x00", "{'single': 'quotes'}", '{"input": 1e999}', "\ud800"]


@pytest.mark.parametrize("text", GARBAGE, ids=[repr(g)[:30] for g in GARBAGE])
def test_handle_line_is_total_and_every_garbage_line_is_a_published_schema_error_response(text):
    r = av2.handle_line(text, ctx())
    assert is_error_response(r) and r["error"]["code"] == "MALFORMED" and r["schemaVersion"] == "v2"


def test_a_duplicate_key_anywhere_in_the_request_is_refused_even_inside_the_manifest():
    c = ctx(handlers={"release": lambda i, k: {}})
    text = line("release", {"grantId": H}).replace('"chains"', '"chains": 1, "chains"', 1)
    assert av2.handle_line(text, c)["error"]["code"] == "MALFORMED"


def test_a_line_over_one_mebibyte_is_refused_before_it_is_parsed():
    r = av2.handle_line('{"x":"' + "a" * (1 << 20) + '"}', ctx())
    assert r["error"]["code"] == "MALFORMED" and "1 MiB" in r["error"]["message"]


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# dispatch
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_an_unwired_operation_is_unavailable_and_rotate_epoch_is_not_implemented_in_phase():
    c = ctx()
    r = av2.handle_line(line("release", {"grantId": H}), c)
    assert (r["error"]["code"], "reason" in r["error"]) == ("ADAPTER_UNAVAILABLE", False) and is_error_response(r)
    r = av2.handle_line(line("rotate_epoch", {"targetEpoch": "1"}), c)
    assert r["error"]["code"] == "NOT_IMPLEMENTED_IN_PHASE" and is_error_response(r)
    c2 = ctx(handlers={"rotate_epoch": lambda i, k: {"rotated": True}})
    assert av2.handle_line(line("rotate_epoch", {"targetEpoch": "1"}), c2)["error"]["code"] == "NOT_IMPLEMENTED_IN_PHASE"       # no handler can enable it: G is locked


def test_a_handler_gets_a_private_copy_of_a_validated_input_and_the_context():
    seen = {}

    def h(inp, k):
        seen["input"], seen["ctx"] = copy.deepcopy(inp), k
        inp["grantId"] = "tampered"
        return {"ok": 1}
    c = ctx(handlers={"release": h})
    req = line("release", {"grantId": H})
    assert av2.handle_line(req, c)["ok"] is True and seen["input"] == {"grantId": H} and seen["ctx"] is c
    assert av2.handle_line(req, c)["ok"] is True and seen["input"] == {"grantId": H}


def test_input_validation_happens_before_dispatch_a_bad_input_never_reaches_a_handler():
    calls = []
    c = ctx(handlers={op: (lambda i, k, op=op: calls.append(op) or {}) for op in OPS})
    for op in OPS:
        r = av2.handle_line(line(op, {"unexpected": 1}), c)
        assert r["error"]["code"] == "MALFORMED"
    assert calls == []


def test_a_handler_failure_is_a_generic_unavailable_error_that_never_leaks_its_text():
    def boom(i, k):
        raise RuntimeError("secret-key 0xdeadbeef /home/user/.keys")
    r = av2.handle_line(line("release", {"grantId": H}), ctx(handlers={"release": boom}))
    assert is_error_response(r) and r["error"] == {"code": "ADAPTER_UNAVAILABLE", "message": "internal adapter failure"}
    r = av2.handle_line(line("release", {"grantId": H}), ctx(handlers={"release": lambda i, k: "not a dict"}))
    assert r["error"] == {"code": "ADAPTER_UNAVAILABLE", "message": "internal adapter failure"}


def test_an_operation_error_carries_its_code_reason_and_message_into_a_schema_valid_response():
    def refuse(i, k):
        raise av2.OperationError("STALE_STATE", "pinned", reason="CONFLICT_PINNED")
    r = av2.handle_line(line("collect_checkpoint", {}), ctx(handlers={"collect_checkpoint": refuse}))
    assert is_error_response(r) and r["error"] == {"code": "STALE_STATE", "reason": "CONFLICT_PINNED", "message": "pinned"}


def test_collection_and_recorded_evidence_travel_with_their_reason_into_the_response():
    rec = {"message": {"sequence": "1"}, "signature": SIG}
    col = {"quorum": "3", "witnessSetVersion": "2", "outcomes": [], "submittedSigners": []}

    def pinned(i, k):
        raise av2.OperationError("STALE_STATE", "pinned", reason="CONFLICT_PINNED", recorded=rec)

    def short(i, k):
        raise av2.OperationError("ADAPTER_UNAVAILABLE", "short", reason="QUORUM_UNAVAILABLE", collection=col)
    c = ctx(handlers={"collect_checkpoint": pinned, "collect_decision": short})
    assert av2.handle_line(line("collect_checkpoint", {}), c)["error"] == {"code": "STALE_STATE", "reason": "CONFLICT_PINNED", "message": "pinned", "recorded": rec}
    assert av2.handle_line(line("collect_decision", {"requestDigest": H}), c)["error"] == {"code": "ADAPTER_UNAVAILABLE", "reason": "QUORUM_UNAVAILABLE", "message": "short", "collection": col}


def test_a_pinned_manifest_that_cannot_bind_a_request_and_bad_handlers_cannot_be_pinned():
    for bad in ({}, {"schemaVersion": "hmbc-ledger-deployment/v2"}, {"schemaVersion": "hmbc-ledger-deployment/v2", "chains": {}}, "x", None):
        with pytest.raises(ValueError):
            av2.Context(manifest=bad, schema_revision="v2", handlers={})
    for handlers in ({"nonsense": lambda i, k: {}}, {"release": "not callable"}, None, [], {"release": None}):
        with pytest.raises(ValueError):
            av2.Context(manifest=F2, schema_revision="v2", handlers=handlers)


def test_the_context_keeps_its_own_copy_of_the_pinned_manifest():
    mine = copy.deepcopy(F2)
    c = av2.Context(manifest=mine, schema_revision="v2", handlers={"release": lambda i, k: {"x": 1}})
    mine["createdAt"] = "tampered"                                                                  # the caller edits its dict after pinning
    assert av2.handle_line(line("release", {"grantId": H}, F2), c)["ok"] is True


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the reason table
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_reason_table_equals_the_published_one_and_the_schema_enums():
    assert av2.REASON_CODE == REASONS
    err = SCHEMA["$defs"]["Error"]["properties"]
    assert set(av2.REASON_CODE) == set(err["reason"]["enum"]) and set(av2.REASON_CODE.values()) <= set(err["code"]["enum"])
    assert av2.CODES == tuple(err["code"]["enum"])


@pytest.mark.parametrize("reason", sorted(REASONS))
def test_every_reason_with_its_own_code_gives_a_valid_response_and_with_another_code_is_refused(reason):
    code = REASONS[reason]
    assert av2.OperationError(code, "m", reason=reason).reason == reason
    other = next(c for c in av2.CODES if c != code)
    with pytest.raises(ValueError):
        av2.OperationError(other, "m", reason=reason)


def test_recorded_belongs_to_conflict_pinned_and_collection_to_quorum_unavailable_only():
    rec = {"message": {"sequence": "1"}, "signature": SIG}
    assert av2.OperationError("STALE_STATE", "m", reason="CONFLICT_PINNED", recorded=rec).recorded == rec
    with pytest.raises(ValueError):
        av2.OperationError("STALE_STATE", "m", reason="PROPOSAL_MISMATCH", recorded=rec)
    with pytest.raises(ValueError):
        av2.OperationError("EXPIRED", "m", recorded=rec)
    col = {"quorum": "3", "witnessSetVersion": "2", "outcomes": [], "submittedSigners": []}
    assert av2.OperationError("ADAPTER_UNAVAILABLE", "m", reason="QUORUM_UNAVAILABLE", collection=col).collection == col
    with pytest.raises(ValueError):
        av2.OperationError("ADAPTER_UNAVAILABLE", "m", reason="WITNESS_FAULTED", collection=col)
    with pytest.raises(ValueError):
        av2.OperationError("MALFORMED", "m", collection=col)


def test_an_unknown_code_or_an_empty_message_is_refused():
    for bad in (dict(code="NOPE", message="m"), dict(code="MALFORMED", message=""), dict(code="MALFORMED", message=5), dict(code="MALFORMED", message="m", reason="NOPE")):
        with pytest.raises(ValueError):
            av2.OperationError(**bad)


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the inputs against the published schema (differential)
# --------------------------------------------------------------------------------------------------------------------------------------------------------
ALT = [None, True, False, 0, 1, -1, 1.5, "", "x", "0", "1", "01", "-1", "2", "3", "4", "0x", H, H.upper(), ADDR, "0x" + "00" * 20, [], {}, [H], {"a": 1}, "keyref:user:alice", "keyref:user:", "9" * 80]


def mutations(base):
    yield copy.deepcopy(base)
    for k in base:
        m = copy.deepcopy(base)
        m.pop(k)
        yield m
        for a in ALT:
            m = copy.deepcopy(base)
            m[k] = copy.deepcopy(a)
            yield m
    for extra in ("witnessIndex", "witnessSetVersion", "unexpected"):
        for a in ALT[:20]:
            m = copy.deepcopy(base)
            m[extra] = copy.deepcopy(a)
            yield m
    yield {}
    yield []
    yield None
    yield "x"


def my_accepts(op, inp):
    try:
        av2.validate_input(op, copy.deepcopy(inp))
        return True
    except av2.OperationError as e:
        assert e.code == "MALFORMED" and e.reason is None
        return False


def schema_accepts(op, inp):
    return sv(INPUT_DEF[op]).is_valid(inp)


@pytest.mark.parametrize("op", [o for o in OPS if o not in ("collect_governance",)])
def test_the_input_validators_agree_with_the_published_schema_on_a_mutation_corpus(op):
    n = agree_accept = 0
    for m in mutations(BASE[op]):
        a, b = my_accepts(op, m), schema_accepts(op, m)
        assert a == b, (op, m, "mine accepts" if a else "schema accepts")
        n += 1
        agree_accept += a
    assert n > 40 and agree_accept >= 1


def test_the_witness_selector_and_set_version_are_accepted_exactly_where_the_schema_accepts_them():
    for op, extra in itertools.product(("collect_decision", "collect_checkpoint", "attest_grant"), [{}, {"witnessIndex": "0"}, {"witnessIndex": "3"}, {"witnessIndex": "4"}, {"witnessIndex": 0}, {"witnessIndex": "00"},
                                                                                                    {"witnessSetVersion": "1"}, {"witnessSetVersion": "2"}, {"witnessSetVersion": "3"}, {"witnessSetVersion": 2},
                                                                                                    {"witnessIndex": "1", "witnessSetVersion": "2"}]):
        inp = dict(BASE[op], **extra)
        assert my_accepts(op, inp) == schema_accepts(op, inp), (op, extra)


def test_collect_governance_is_never_more_permissive_than_the_schema_and_is_stricter_only_on_admin_order():
    stricter = []
    unsorted = dict(GOV, admins=["0x" + "22" * 20, "0x" + "11" * 20])
    for m in list(mutations(GOV)) + [unsorted]:
        a, b = my_accepts("collect_governance", m), schema_accepts("collect_governance", m)
        assert not (a and not b), m                                                                # never more permissive
        if b and not a:
            stricter.append(m)
    assert stricter and all(isinstance(m.get("admins"), list) and m["admins"] != sorted(m["admins"]) for m in stricter), stricter[:2]
    for admins in ([], ["0x" + "11" * 20], ["0x" + "11" * 20, "0x" + "22" * 20], ["0x" + "%02x" % (i + 1) * 20 for i in range(8)], ["0x" + "%02x" % (i + 1) * 20 for i in range(9)]):
        for action in "0123":
            inp = dict(GOV, action=action, admins=admins)
            assert my_accepts("collect_governance", inp) == schema_accepts("collect_governance", inp), (action, len(admins))     # the per-action admin counts
    for extra in ({"witnessIndex": "2"}, {"witnessIndex": "9"}, {"witnessSetVersion": "1"}):
        inp = dict(GOV, **extra)
        assert my_accepts("collect_governance", inp) == schema_accepts("collect_governance", inp), extra


def test_finish_decryption_takes_a_v2_release_result_not_the_v1_one():
    ok = BASE["finish_decryption"]
    assert my_accepts("finish_decryption", ok)
    bad = copy.deepcopy(ok)
    bad["response"]["schemaVersion"] = "v1"                                                         # what the carried E validator would demand
    assert not my_accepts("finish_decryption", bad) and not schema_accepts("finish_decryption", bad)
    from hmbc_protocol import wire
    with pytest.raises(wire.WireError):
        wire.finish_decryption_input(ok)                                                            # the finding: E rejects a valid v2 input
    wire.finish_decryption_input(bad)                                                               # and accepts the v1 one


@pytest.mark.parametrize("exc", [TypeError("x"), KeyError("k"), ValueError("v"), AttributeError("a")])
def test_a_validator_that_trips_on_an_odd_value_is_malformed_not_an_internal_failure(monkeypatch, exc):
    def odd(v):
        raise exc
    monkeypatch.setitem(av2.VALIDATORS, "release", odd)
    r = av2.handle_line(line("release", {"grantId": H}), ctx(handlers={"release": lambda i, k: {}}))
    assert r["error"]["code"] == "MALFORMED" and "reason" not in r["error"]


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the serve loop
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def serve(chunks, handlers=None):
    out = io.StringIO()
    rc = av2.serve(io.BytesIO(b"".join(chunks)), out, ctx(handlers=handlers or {"release": lambda i, k: {"released": True}}))
    return rc, out.getvalue()


def test_one_response_per_input_line_whatever_the_line_is():
    good = (line("release", {"grantId": H}) + "\n").encode()
    rc, out = serve([good, b"\xff\xfe not utf8\n", b"\n", b"   \n", good, b"{bad json}\n", good])
    rows = [json.loads(x) for x in out.splitlines()]
    assert rc == 0 and len(rows) == 7
    assert [r["ok"] for r in rows] == [True, False, False, False, True, False, True]
    assert all(V_RESP.is_valid(r) or r["result"] == {"released": True} for r in rows)
    assert rows[1]["error"]["message"] == "request is not valid UTF-8" and rows[2]["error"]["message"] == "empty request line"


def test_an_oversized_line_yields_one_error_and_the_next_line_is_still_served():
    big = b"{" + b"a" * (2 << 20) + b"}\n"
    good = (line("release", {"grantId": H}) + "\n").encode()
    rc, out = serve([big, good])
    rows = [json.loads(x) for x in out.splitlines()]
    assert [r["ok"] for r in rows] == [False, True] and "1 MiB" in rows[0]["error"]["message"]


def test_the_output_is_compact_ascii_json_lines():
    rc, out = serve([(line("release", {"grantId": H}) + "\n").encode(), b'{"x":"\xc3\xa9"}\n'])
    lines = out.splitlines()
    assert out.isascii() and out.endswith("\n") and len(lines) == 2 and all(json.dumps(json.loads(l), separators=(",", ":")) == l for l in lines)


def test_a_final_line_without_a_newline_is_still_answered():
    rc, out = serve([line("release", {"grantId": H}).encode()])
    assert json.loads(out)["result"] == {"released": True}


def test_the_module_reads_no_clock_no_network_and_no_subprocess():
    src = open(os.path.join(ROOT, "protocol", "hmbc_protocol", "adapter_v2.py")).read()
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            mods.add((node.module or "").split(".")[0])
    assert not mods & {"time", "datetime", "random", "socket", "urllib", "http", "subprocess"}, mods
