"""Successor adapter handlers, part 2 (agent 2, F task 2 slice 6b-2). Written BEFORE hmbc_protocol/adapter_v2_witness.py existed.

The four witness operations behind `adapter_v2`: `collect_checkpoint`, `collect_decision`, `attest_grant`, `collect_governance`. Each derives the proposal from the PROPOSER'S OWN reads (the injected ledger view; for a
governance action the operator's whole action is the proposal), then either
  * POOL MODE (no `witnessIndex`): runs one `witness_pool.Collection` through the pool driver against four witnesses behind an injected transport and returns exactly three verified signatures plus the
    published `collection` evidence, or
  * SINGLE-WITNESS MODE (`witnessIndex` given): one exchange with that witness (5 s reply timeout), one signature, no `collection` member.
Every result and every response is validated against the PUBLISHED schema (byte-copied fixture). The witnesses are REAL `WitnessService` objects over real durable stores behind the TEST-ONLY virtual
transport; the ledger is the injected fake views of the service tests. Explicit choices where F0 and the published schema are silent (listed in the module docstring too): the F profile only; a declared
`witnessSetVersion` other than "2" is STALE_STATE/WITNESS_SET_MISMATCH; a pool that cannot start because 2 s or less of validity remain is EXPIRED; a receipt's pool window is the DBC's latest block
timestamp + 60 s; a single-witness reply that does not verify is an ADAPTER_UNAVAILABLE failure, never a signature.
"""
import copy
import json
import os

import jsonschema
import pytest
from eth_account import Account

from hmbc_protocol import adapter_v2 as av2
from hmbc_protocol import adapter_v2_witness as aw
from hmbc_protocol import eip712, keys, messages
from hmbc_protocol import pool_core as core
from hmbc_protocol import witness_service as svc
from hmbc_protocol import witness_state as ws

from test_witness_service import B, BIND, h
from test_witness_service_decision import DView, KSSC
from test_witness_service_governance import GOV, GView, NOW, R1, A1, A2, ALLOW, act, GDEPLOY
from test_witness_service_receipt import RView
from test_witness_service import PSC

from testtools.virtual_transport import ServiceEndpoint, VirtualTransport

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FX = os.path.join(ROOT, "protocol", "tests", "fixtures")
SCHEMA = json.load(open(os.path.join(FX, "agent3-v2.1-hmbc.schema.json")))
F2 = json.load(open(os.path.join(FX, "agent1-85c59f5-f-base-deployment.json")))
E21 = json.load(open(os.path.join(FX, "agent1-85c59f5-e-successor-v2.1-deployment.json")))
FORMATS = jsonschema.FormatChecker()

# the F manifest with the addresses the service-test fakes use
MAN = copy.deepcopy(F2)
MAN["chains"]["pbc"]["contracts"]["PSC"] = PSC
MAN["chains"]["pbc"]["contracts"]["Governance"] = GOV
MAN["chains"]["dbc"]["contracts"]["KSSC"] = KSSC
KEYS = [keys.synthetic_private_key("witness-%d" % i) for i in range(1, 5)]
ADDRS = [Account.from_key(k).address.lower() for k in KEYS]


def sv(name):
    return jsonschema.Draft202012Validator({"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": "#/$defs/" + name, "$defs": SCHEMA["$defs"]}, format_checker=FORMATS)


V_RESP = sv("AdapterResponse")
V_RESULT = {"collect_checkpoint": sv("CollectCheckpointResult"), "collect_decision": sv("CollectDecisionResult"), "attest_grant": sv("AttestGrantResult"), "collect_governance": sv("CollectGovernanceResult")}


class CView(RView, GView):
    """One ledger view for all four message types (the service tests use one fake per type)."""


class Rig:
    def __init__(self, tmp_path, view=None, muted=(), reply_delay=100, signers=None):
        self.view = view or CView()
        self.view.authorities = set()                    # ADD of R1 is valid
        self.services = []
        for i in range(4):
            st = ws.init_store(str(tmp_path / ("w%d" % i)), BIND, B, "witness:" + ADDRS[i])
            self.services.append(svc.WitnessService(store=st, key=KEYS[i], view=self.view, deployment=MAN, witness_set_version="2", allowed_governance=ALLOW))
        self.muted, self.reply_delay = set(muted), reply_delay
        self.signers = signers or {}
        self.made = []

    def factory(self, kind):
        method = {"checkpoint": "sign_checkpoint", "decision": "sign_decision", "receipt": "sign_receipt", "governance": "sign_governance"}[kind]
        eps = {}
        for i in range(4):
            sign = getattr(self.services[self.signers.get(i, i)], method)
            eps[i] = ServiceEndpoint(sign, reply_delay=self.reply_delay, muted=i in self.muted)
        t = VirtualTransport(eps)
        self.made.append((kind, t))
        return t

    def handlers(self, **kw):
        return aw.witness_handlers(view=self.view, witnesses=ADDRS, transport_factory=self.factory, **kw)


def line(op, inp, dep=MAN):
    return json.dumps({"schemaVersion": "v2", "operation": op, "input": inp, "deploymentManifest": dep})


def run(rig, op, inp, dep=MAN, rev="v2", **kw):
    c = av2.Context(manifest=dep, schema_revision=rev, handlers=rig.handlers(**kw), schema=SCHEMA)
    r = av2.handle_line(line(op, inp, dep), c)
    assert V_RESP.is_valid(r), (r, list(V_RESP.iter_errors(r))[:1])
    if r["ok"]:
        assert V_RESULT[op].is_valid(r["result"]), list(V_RESULT[op].iter_errors(r["result"]))[:1]
    return r


def digest(name, m):
    if name == "GrantReceipt":
        return svc._receipt_digest(m, MAN)
    if name == "GovernanceAction":
        return svc._governance_digest(m, MAN)
    return messages.digest_of(name, m, messages.domain_for(name, m, MAN))


def signers_of(name, m, sigs):
    return [eip712.recover(digest(name, m), s) for s in sigs]


DIGEST = CView().digest()
GRANT = CView().grant_id()
CASES = {
    "collect_checkpoint": ("collect_checkpoint", {}, "checkpoint", "StateCheckpoint", "checkpoint"),
    "collect_decision": ("collect_decision", {"requestDigest": DIGEST}, "decision", "AccessDecision", "decision"),
    "attest_grant": ("attest_grant", {"grantId": GRANT}, "receipt", "GrantReceipt", "receipt"),
    "collect_governance": ("collect_governance", act(), "governance", "GovernanceAction", "governanceAction"),
}


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# pool mode: three verified signatures and the published collection evidence
# --------------------------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("op", list(CASES))
def test_pool_mode_returns_exactly_three_signatures_that_recover_to_distinct_witnesses_and_the_collection(tmp_path, op):
    name, inp, kind, typed, member = CASES[op]
    rig = Rig(tmp_path)
    r = run(rig, name, inp)
    assert r["ok"] is True
    res = r["result"]
    assert res["schemaVersion"] == "v2" and res["adapterMode"] == "symbolic" and len(res["signatures"]) == 3
    who = signers_of(typed, res[member], res["signatures"])
    assert len(set(who)) == 3 and set(who) <= set(ADDRS) and who == sorted(who)
    assert res["collection"]["submittedSigners"] == who and res["collection"]["quorum"] == "3" and res["collection"]["witnessSetVersion"] == "2"
    assert [k for k, _ in rig.made] == [kind]


def test_a_decision_result_carries_the_credential_records_the_proposer_derived(tmp_path):
    rig = Rig(tmp_path)
    r = run(rig, *CASES["collect_decision"][:2])
    _, records = svc.derive_decision(rig.view, MAN, DIGEST, witness_set_version="2")
    assert r["result"]["credentialRecords"] == records and records


def test_the_governance_admins_are_the_pooled_list(tmp_path):
    rig = Rig(tmp_path)
    r = run(rig, "collect_governance", act(admins=(A1, A2)))
    assert r["result"]["governanceAction"]["admins"] == [A1, A2]


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# single-witness mode: one witness, one signature, no collection
# --------------------------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("op", list(CASES))
@pytest.mark.parametrize("index", ["0", "3"])
def test_single_witness_mode_returns_one_verified_signature_from_that_witness_and_no_collection(tmp_path, op, index):
    name, inp, kind, typed, member = CASES[op]
    rig = Rig(tmp_path)
    r = run(rig, name, dict(inp, witnessIndex=index))
    assert r["ok"] is True
    res = r["result"]
    assert "collection" not in res and len(res["signatures"]) == 1
    assert signers_of(typed, res[member], res["signatures"]) == [ADDRS[int(index)]]
    (_, t), = rig.made
    assert [(w, rd) for _, w, rd in t.sent] == [(int(index), 1)]          # exactly one write, to that witness, in round 1


def test_a_single_witness_that_never_answers_fails_after_five_seconds_and_the_write_is_cancelled(tmp_path):
    rig = Rig(tmp_path, muted={1})
    r = run(rig, "collect_checkpoint", {"witnessIndex": "1"})
    assert r["ok"] is False and r["error"]["code"] == "ADAPTER_UNAVAILABLE" and "collection" not in r["error"]
    (_, t), = rig.made
    assert t.t == 5000 and t.cancelled == [(5000, 1, 1)]


def test_a_single_witness_reply_exactly_at_five_seconds_is_a_timeout(tmp_path):
    rig = Rig(tmp_path, reply_delay=5000)
    r = run(rig, "collect_checkpoint", {"witnessIndex": "0"})
    assert r["ok"] is False and r["error"]["code"] == "ADAPTER_UNAVAILABLE"
    rig2 = Rig(tmp_path / "again", reply_delay=4999)
    assert run(rig2, "collect_checkpoint", {"witnessIndex": "0"})["ok"] is True


def test_a_single_witness_that_answers_with_another_witnesss_signature_is_refused_not_returned(tmp_path):
    rig = Rig(tmp_path, signers={2: 3})                  # endpoint 2 is backed by witness 3's service
    r = run(rig, "collect_checkpoint", {"witnessIndex": "2"})
    assert r["ok"] is False and r["error"]["code"] == "ADAPTER_UNAVAILABLE" and "signatures" not in json.dumps(r)


def test_a_single_witness_refusal_keeps_its_closed_code_and_reason(tmp_path):
    rig = Rig(tmp_path)
    rig.services[0]._allow = frozenset()                  # POLICY_DENIED for governance on witness 0
    r = run(rig, "collect_governance", dict(act(), witnessIndex="0"))
    assert r["ok"] is False and r["error"]["code"] == "POLICY_DENIED"


def test_a_pinned_checkpoint_refusal_from_a_single_witness_returns_the_recorded_value(tmp_path):
    rig = Rig(tmp_path)
    assert run(rig, "collect_checkpoint", {"witnessIndex": "0"})["ok"] is True
    rig.view.reads[250] = {"authEpoch": "4", "policyVersion": "1", "witnessSetVersion": "2"}          # a different valid value for the same sequence
    r = run(rig, "collect_checkpoint", {"witnessIndex": "0"})
    assert r["ok"] is False and r["error"]["code"] == "STALE_STATE" and r["error"]["reason"] == "CONFLICT_PINNED"
    assert set(r["error"]["recorded"]) == {"message", "signature"}


def test_a_refusal_of_a_decision_or_receipt_never_carries_a_recorded_member(tmp_path):
    rig = Rig(tmp_path)
    other = CView()
    other.status = "0"                                  # witness 0 reads a PBC record that was not forwarded: it refuses while the proposer's own derivation succeeds
    rig.services[0]._view = other
    for op in ("collect_decision", "attest_grant"):
        r = run(rig, CASES[op][0], dict(CASES[op][1], witnessIndex="0"))
        assert r["ok"] is False and "recorded" not in r["error"]


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# pool failure, refusal and the choices
# --------------------------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("op", list(CASES))
def test_two_silent_witnesses_fail_the_pool_with_quorum_unavailable_and_nothing_submitted(tmp_path, op):
    name, inp = CASES[op][:2]
    rig = Rig(tmp_path, muted={0, 1})
    r = run(rig, name, inp)
    assert r["ok"] is False and r["error"]["code"] == "ADAPTER_UNAVAILABLE" and r["error"]["reason"] == "QUORUM_UNAVAILABLE"
    coll = r["error"]["collection"]
    assert coll["submittedSigners"] == [] and [o["witnessIndex"] for o in coll["outcomes"]] == ["0", "1", "2", "3"]
    assert [o["status"] for o in coll["outcomes"]][:2] == ["silent", "silent"]
    now, expires = {"collect_checkpoint": (1000, 1030), "collect_decision": (1000, int(svc.derive_decision(rig.view, MAN, DIGEST, witness_set_version="2")[0]["expiresAt"])),
                    "attest_grant": (1000, 1060), "collect_governance": (NOW, NOW + 60)}[op]
    (_, t), = rig.made
    assert t.t == core.collection_deadline_ms(now, expires)                 # the window each operation chose, ended by the deadline


def test_an_expiry_two_seconds_away_is_refused_before_any_witness_is_contacted(tmp_path):
    rig = Rig(tmp_path)
    r = run(rig, "collect_governance", act(exp=NOW + 2))
    assert r["ok"] is False and r["error"]["code"] == "EXPIRED"
    assert all(not t.sent for _, t in rig.made)


@pytest.mark.parametrize("op", ["collect_checkpoint", "collect_decision"])
def test_a_declared_witness_set_version_other_than_2_is_a_witness_set_mismatch_and_nothing_is_contacted(tmp_path, op):
    name, inp = CASES[op][:2]
    rig = Rig(tmp_path)
    r = run(rig, name, dict(inp, witnessSetVersion="1"))
    assert r["ok"] is False and r["error"]["code"] == "STALE_STATE" and r["error"]["reason"] == "WITNESS_SET_MISMATCH"
    assert rig.made == []
    assert run(rig, name, dict(inp, witnessSetVersion="2"))["ok"] is True


def test_the_proposers_own_derivation_failure_is_returned_with_its_code_and_no_witness_is_contacted(tmp_path):
    rig = Rig(tmp_path)
    rig.view.grant_allowed = False
    r = run(rig, "attest_grant", {"grantId": GRANT})
    assert r["ok"] is False and r["error"]["code"] == "NOT_COMMITTED"
    assert all(not t.sent for _, t in rig.made)


def test_an_unreachable_ledger_for_the_proposer_is_adapter_unavailable_and_no_witness_is_contacted(tmp_path):
    rig = Rig(tmp_path)
    rig.view.fail = "grant"
    r = run(rig, "attest_grant", {"grantId": GRANT})
    assert r["ok"] is False and r["error"]["code"] == "ADAPTER_UNAVAILABLE" and r["error"]["reason"] == "LEDGER_UNREACHABLE"
    assert all(not t.sent for _, t in rig.made)


def test_an_e_profile_manifest_is_not_wired_for_these_operations(tmp_path):
    rig = Rig(tmp_path)
    r = run(rig, "collect_checkpoint", {}, dep=E21, rev="v2.1")
    assert r["ok"] is False and r["error"]["code"] == "ADAPTER_UNAVAILABLE" and "not wired" in r["error"]["message"]
    assert rig.made == []


def test_a_transport_failure_is_a_generic_internal_failure_never_a_traceback(tmp_path):
    rig = Rig(tmp_path)

    def broken(kind):
        raise RuntimeError("secret path /home/x")
    c = av2.Context(manifest=MAN, schema_revision="v2", handlers=aw.witness_handlers(view=rig.view, witnesses=ADDRS, transport_factory=broken), schema=SCHEMA)
    r = av2.handle_line(line("collect_checkpoint", {}), c)
    assert r["ok"] is False and r["error"]["code"] == "ADAPTER_UNAVAILABLE" and "secret" not in json.dumps(r)


def test_the_handlers_are_exactly_the_four_witness_operations_and_need_four_distinct_addresses(tmp_path):
    rig = Rig(tmp_path)
    assert set(rig.handlers()) == {"collect_checkpoint", "collect_decision", "attest_grant", "collect_governance"}
    for bad in (ADDRS[:3], ADDRS + [ADDRS[0]], [ADDRS[0]] * 4, ["0x" + "AA" * 20] + ADDRS[1:]):
        with pytest.raises(ValueError):
            aw.witness_handlers(view=rig.view, witnesses=bad, transport_factory=rig.factory)


def test_a_fresh_transport_is_made_for_every_call(tmp_path):
    rig = Rig(tmp_path)
    run(rig, "collect_checkpoint", {})
    run(rig, "collect_checkpoint", {})
    assert len(rig.made) == 2 and rig.made[0][1] is not rig.made[1][1]


def test_the_module_reads_no_clock_no_thread_no_socket():
    src = open(os.path.join(ROOT, "protocol", "hmbc_protocol", "adapter_v2_witness.py")).read()
    for banned in ("import time", "from time", "datetime", "import threading", "import socket", "import random", "import asyncio", "subprocess", "os.environ", "open("):
        assert banned not in src, banned


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# single-witness mode against a SCRIPTED transport: what a witness may say, and what is never accepted as a signature
# --------------------------------------------------------------------------------------------------------------------------------------------------------
class Scripted:
    def __init__(self, event):
        self.event, self.sent, self.cancelled = event, [], []

    def send(self, witness, round_no, message):
        self.sent.append((witness, round_no, message))

    def cancel(self, witness, round_no):
        self.cancelled.append((witness, round_no))

    def next_event(self, deadline_ms):
        event, self.event = self.event, None                 # answers once, then is silent (a pool run against it ends at its deadline instead of looping)
        return event


def scripted(rig, event_for):
    """handlers whose transport answers with `event_for(proposal)` (None = silence)"""
    holder = {}

    class T(Scripted):
        def send(self, witness, round_no, message):
            super().send(witness, round_no, message)
            self.event = event_for(message)

    def factory(kind):
        holder["t"] = T(None)
        return holder["t"]
    c = av2.Context(manifest=MAN, schema_revision="v2", handlers=aw.witness_handlers(view=rig.view, witnesses=ADDRS, transport_factory=factory), schema=SCHEMA)
    return c, holder


def ask(rig, event_for, op="collect_checkpoint", inp=None, idx="1"):
    c, holder = scripted(rig, event_for)
    inp = dict(CASES[op][1] if inp is None else inp, witnessIndex=idx)
    r = av2.handle_line(line(op, inp), c)
    assert V_RESP.is_valid(r), r
    return r


def signed(rig, i, proposal, kind="checkpoint"):
    return getattr(rig.services[i], "sign_" + kind)(dict(proposal))


def alt_checkpoint(rig, *signers):
    """A DIFFERENT valid checkpoint for the same sequence, signed by each witness in `signers` (the ledger view reads another authEpoch while it is derived and signed)."""
    saved = dict(rig.view.reads)
    rig.view.reads[250] = {"authEpoch": "9", "policyVersion": "1", "witnessSetVersion": "2"}
    try:
        cp = svc.derive_checkpoint(rig.view, MAN)
        return (cp,) + tuple(rig.services[i].sign_checkpoint(cp) for i in signers)
    finally:
        rig.view.reads = saved


def test_a_scripted_valid_reply_is_accepted_and_each_defect_is_refused_not_returned(tmp_path):
    rig = Rig(tmp_path)

    def reply(**over):
        def f(m):
            body = {"type": "signature", "message": dict(m), "signature": signed(rig, 1, m)}
            body.update(over)
            return (10, 1, 1, body)
        return f

    assert ask(rig, reply())["ok"] is True
    other, other_sig = alt_checkpoint(rig, 2)
    defects = {
        "an extra key": reply(extra="x"),
        "a message that is not the one sent": reply(message=other),
        "a signature that is not a string": reply(signature=5),
        "a message that is not an object": reply(message="x"),
        "a signature over another message": reply(signature=other_sig),
        "an unknown reply type": reply(type="ok"),
    }
    for name, f in defects.items():
        r = ask(rig, f)
        assert r["ok"] is False and r["error"]["code"] == "ADAPTER_UNAVAILABLE" and "invalid reply" in r["error"]["message"], name
    for bad_event in ((10, 2, 1, {"type": "malformed", "detail": "x"}), (10, 1, 2, None), (10, 1, 1, "text"), (10, 1, 1, None), (10, 2, 1, "x")):
        r = ask(rig, lambda m, e=bad_event: e)
        assert r["ok"] is False and r["error"]["code"] == "ADAPTER_UNAVAILABLE" and "invalid reply" in r["error"]["message"], bad_event


def test_a_reply_from_another_witness_or_round_is_refused_even_when_it_is_a_valid_signature(tmp_path):
    rig = Rig(tmp_path)
    for witness, round_no in ((0, 1), (1, 2)):
        r = ask(rig, lambda m, w=witness, n=round_no: (10, w, n, {"type": "signature", "message": dict(m), "signature": signed(rig, 1, m)}))
        assert r["ok"] is False and "invalid reply" in r["error"]["message"], (witness, round_no)


def test_a_scripted_error_reply_is_accepted_only_with_a_closed_code_a_consistent_reason_and_a_verified_recorded_value(tmp_path):
    rig = Rig(tmp_path)
    VALID_RECORDED = alt_checkpoint(rig, 1)                 # a recorded checkpoint that DOES verify as witness 1's: only its context is wrong in these cases

    def err(**body):
        return lambda m: (10, 1, 1, dict({"type": "error", "code": "STALE_STATE", "reason": "PROPOSAL_MISMATCH", "recorded": None}, **body))

    r = ask(rig, err())
    assert r["ok"] is False and r["error"]["code"] == "STALE_STATE" and r["error"]["reason"] == "PROPOSAL_MISMATCH" and "recorded" not in r["error"]
    r = ask(rig, lambda m: (10, 1, 1, {"type": "error", "code": "EXPIRED"}))                  # no reason, no recorded key at all
    assert r["ok"] is False and r["error"]["code"] == "EXPIRED" and "reason" not in r["error"]
    for name, f in {"an unknown code": err(code="NOPE", reason=None), "a reason of another code": err(reason="QUORUM_UNAVAILABLE"), "an unknown reason": err(reason="NOPE"), "an extra key": err(extra="x"),
                    "a recorded value outside CONFLICT_PINNED": err(recorded={"message": VALID_RECORDED[0], "signature": VALID_RECORDED[1]}),
                    "a recorded value with another code": err(code="EXPIRED", reason=None, recorded={"message": VALID_RECORDED[0], "signature": VALID_RECORDED[1]})}.items():
        r = ask(rig, f)
        assert r["ok"] is False and r["error"]["code"] == "ADAPTER_UNAVAILABLE" and "invalid reply" in r["error"]["message"], name


def test_a_recorded_value_is_returned_only_when_it_verifies_as_that_witnesss_checkpoint(tmp_path):
    rig = Rig(tmp_path)
    recorded_cp, good_sig, wrong = alt_checkpoint(rig, 1, 3)
    pinned = lambda rec: (lambda m: (10, 1, 1, {"type": "error", "code": "STALE_STATE", "reason": "CONFLICT_PINNED", "recorded": rec}))
    r = ask(rig, pinned({"message": recorded_cp, "signature": good_sig}))
    assert r["ok"] is False and r["error"]["recorded"] == {"message": recorded_cp, "signature": good_sig}
    for name, rec in {"a signature of another witness": {"message": recorded_cp, "signature": wrong}, "a signature that is not a string": {"message": recorded_cp, "signature": 1},
                      "a message that is not an object": {"message": "x", "signature": good_sig}, "a non-string value": {"message": dict(recorded_cp, authEpoch=9), "signature": good_sig},
                      "an extra key": {"message": recorded_cp, "signature": good_sig, "x": "y"}, "a missing key": {"message": recorded_cp}, "not an object": "x"}.items():
        r = ask(rig, pinned(rec))
        assert r["ok"] is False and r["error"]["code"] == "ADAPTER_UNAVAILABLE" and "invalid reply" in r["error"]["message"], name
    for op in ("collect_decision", "attest_grant", "collect_governance"):               # the published responses of these forbid `recorded`
        r = ask(rig, pinned({"message": recorded_cp, "signature": good_sig}), op=op)
        assert r["ok"] is False and r["error"]["code"] == "ADAPTER_UNAVAILABLE" and "invalid reply" in r["error"]["message"], op


def test_the_single_witness_exchange_sends_the_proposal_once_to_the_chosen_witness_in_round_one(tmp_path):
    rig = Rig(tmp_path)
    c, holder = scripted(rig, lambda m: None)
    r = av2.handle_line(line("collect_checkpoint", {"witnessIndex": "3"}), c)
    assert r["ok"] is False and "did not answer" in r["error"]["message"]
    t = holder["t"]
    assert [(w, n) for w, n, _ in t.sent] == [(3, 1)] and t.cancelled == [(3, 1)]
    assert t.sent[0][2] == svc.derive_checkpoint(rig.view, MAN)


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# more edges: the proposer's own unreadable ledger, a junk signature, the adopted value, the constructor
# --------------------------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("op,failing", [("collect_checkpoint", "dbc_current_checkpoint"), ("collect_governance", "observe:pbc"), ("collect_decision", "observe:dbc")])
def test_an_unreadable_ledger_on_the_proposers_side_is_ledger_unreachable_for_every_operation(tmp_path, op, failing):
    rig = Rig(tmp_path)
    rig.view.fail = failing
    r = run(rig, op, CASES[op][1])
    assert r["ok"] is False and r["error"]["code"] == "ADAPTER_UNAVAILABLE" and r["error"]["reason"] == "LEDGER_UNREACHABLE"
    assert all(not t.sent for _, t in rig.made)


@pytest.mark.parametrize("op", ["attest_grant", "collect_governance", "collect_decision"])
def test_a_junk_signature_is_an_invalid_reply_for_every_message_type_never_a_crash(tmp_path, op):
    rig = Rig(tmp_path)
    for junk in ("0x12", "zz", "0x" + "00" * 65, ""):
        r = ask(rig, lambda m, j=junk: (10, 1, 1, {"type": "signature", "message": dict(m), "signature": j}), op=op)
        assert r["ok"] is False and r["error"]["code"] == "ADAPTER_UNAVAILABLE" and "invalid reply" in r["error"]["message"], (op, junk)


def test_the_pool_returns_the_adopted_checkpoint_not_the_proposal_when_three_witnesses_pinned_another_value(tmp_path):
    rig = Rig(tmp_path)
    adopted = dict(svc.derive_checkpoint(rig.view, MAN), sourceBlockNumber="249", sourceBlockHash=rig.view.pbc_hash(249))      # valid too: an older block of the same chain
    for i in (0, 1, 2):                                              # witnesses 0, 1, 2 already signed it for the sequence the proposer now proposes another value for
        rig.services[i].sign_checkpoint(adopted)
    r = run(rig, "collect_checkpoint", {})
    assert r["ok"] is True and r["result"]["checkpoint"] == adopted and r["result"]["checkpoint"] != svc.derive_checkpoint(rig.view, MAN)
    assert signers_of("StateCheckpoint", adopted, r["result"]["signatures"]) == sorted(ADDRS[:3]) and "adopted" in r["result"]["collection"]


def test_the_constructor_refuses_a_transport_factory_that_cannot_be_called(tmp_path):
    rig = Rig(tmp_path)
    for bad in (None, 5, "x"):
        with pytest.raises(ValueError):
            aw.witness_handlers(view=rig.view, witnesses=ADDRS, transport_factory=bad)


def test_a_valid_signature_of_the_chosen_witness_over_another_message_is_not_the_answer(tmp_path):
    rig = Rig(tmp_path)
    other, sig = alt_checkpoint(rig, 1)
    r = ask(rig, lambda m: (10, 1, 1, {"type": "signature", "message": other, "signature": sig}))
    assert r["ok"] is False and r["error"]["code"] == "ADAPTER_UNAVAILABLE" and "invalid reply" in r["error"]["message"]


def test_a_transport_that_alters_the_message_it_was_given_cannot_change_the_proposal(tmp_path):
    rig = Rig(tmp_path)

    def reply(m):
        original = dict(m)
        sig = signed(rig, 1, original)
        m["authEpoch"] = "999"                                   # the transport scribbles on the object it was handed
        return (10, 1, 1, {"type": "signature", "message": original, "signature": sig})
    r = ask(rig, reply)
    assert r["ok"] is True and r["result"]["checkpoint"]["authEpoch"] == "3"
