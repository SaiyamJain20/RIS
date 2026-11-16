"""TEST-ONLY Byzantine witness variants H1 and the per-witness view override H3 (agent 2, F task 3 slice 7a). Written BEFORE testtools/byzantine.py existed.

Each variant is an endpoint for the virtual transport that replaces ONE witness (f = 1) or TWO of the four. The honest ones are real `WitnessService` objects over real durable stores and one injected fake ledger
view, driven by the real pool state machine through the real driver, so these runs exercise the pool's classification and its quorum rule, not a model of them. What is claimed: with one Byzantine witness of
these kinds a verifying three-signature certificate over the proposal still forms from the honest witnesses alone, and a Byzantine reply is never counted; with two impersonating or silent witnesses nothing is
submitted. NOT claimed: anything about a real transport, clock, process or independent ledger views (H3 here swaps the view object of one service; it breaks the safe-ledger assumption by design, as the
inventory says, and is for the conditional rows only). The expected per-witness STATUS of each variant was predicted from SIGNING-RULES section 8 before the first run (the prediction for the equivocator is
the least certain); a disagreement is recorded in the evidence README, not hidden.
"""
import pytest

from hmbc_protocol import eip712, keys, messages
from hmbc_protocol import witness_service as svc
from testtools import byzantine as bz
from testtools.virtual_transport import ServiceEndpoint, VirtualTransport

from test_witness_pool_driver import ADDRS, DEPLOY, KEYS, PoolView, collection, drv, make_witnesses, verify

OUTSIDER = keys.synthetic_private_key("outsider")


def run(tmp_path, variants, view=None, honest_view=None):
    """variants: {index: endpoint factory(service) -> endpoint}. Returns (result, transport, coll, services, proposal)."""
    view = view or PoolView()
    services = make_witnesses(tmp_path, view)
    proposal = svc.derive_checkpoint(view, DEPLOY)
    eps = [variants[i](services[i]) if i in variants else ServiceEndpoint(services[i].sign_checkpoint, reply_delay=300) for i in range(4)]          # the honest replies come LAST, so the collection sees the Byzantine one first
    tr = VirtualTransport(eps)
    coll = collection(view, proposal)
    r = drv.run_collection(coll, tr)
    return r, tr, coll, services, proposal


def statuses(r):
    return [o["status"] for o in r["collection"]["outcomes"]]


def signers(proposal, r):
    return [verify(proposal, s) for s in r["signatures"]]


def impersonate(i):
    return lambda s: bz.Impersonator(s.sign_checkpoint, KEYS[(i + 1) % 4], "StateCheckpoint", DEPLOY)


VARIANTS = {
    "withhold": (lambda s: bz.withhold(s.sign_checkpoint), "silent"),
    "impersonate (a signature that recovers to another witness)": (impersonate(3), "invalid"),
    "outsider (a signature by a key outside the set)": (lambda s: bz.Impersonator(s.sign_checkpoint, OUTSIDER, "StateCheckpoint", DEPLOY), "invalid"),
    "poison (signs a different checkpoint)": (lambda s: bz.Poisoner(s.sign_checkpoint, KEYS[3], "StateCheckpoint", DEPLOY, lambda m: dict(m, authEpoch="99")), "dissent"),
    "repeat (the same reply three times)": (lambda s: bz.Repeater(ServiceEndpoint(s.sign_checkpoint), 3), "signed"),
    "equivocate (signs two values)": (lambda s: bz.Equivocator(ServiceEndpoint(s.sign_checkpoint), KEYS[3], "StateCheckpoint", DEPLOY, lambda m: dict(m, authEpoch="99")), "signed"),
    "garbage (a reply of no known type)": (lambda s: bz.Garbage(), "invalid"),
    "late (answers after the reply timeout)": (lambda s: bz.delayed(ServiceEndpoint(s.sign_checkpoint), 6000), "silent"),
}


@pytest.mark.parametrize("name", list(VARIANTS))
def test_one_byzantine_witness_cannot_stop_or_taint_the_certificate_and_is_classified_as_predicted(tmp_path, name):
    make, status = VARIANTS[name]
    r, tr, coll, services, proposal = run(tmp_path, {3: make})
    assert r["ok"] is True and r["message"] == proposal and len(r["signatures"]) == 3
    if name.startswith(("repeat", "equivocate")):
        # these two variants ARE valid signers of the asked value: the first reply of witness 3 is a genuine signature and counts ONCE; the repeat or the second value never adds a signer
        got = signers(proposal, r)
        assert len(set(got)) == 3 and ADDRS[3] in got and set(got) <= set(ADDRS) and got == r["collection"]["submittedSigners"] == sorted(got)
        assert statuses(r)[3] == status
        return
    assert signers(proposal, r) == sorted(ADDRS[:3]) == r["collection"]["submittedSigners"]          # the three honest witnesses, each once, none of the Byzantine one
    assert statuses(r) == ["signed", "signed", "signed", status]


@pytest.mark.parametrize("name", ["withhold", "impersonate (a signature that recovers to another witness)", "outsider (a signature by a key outside the set)", "garbage (a reply of no known type)"])
def test_two_byzantine_witnesses_of_these_kinds_leave_nothing_submitted(tmp_path, name):
    make, _ = VARIANTS[name]
    r, tr, coll, services, proposal = run(tmp_path, {2: make, 3: make})
    assert r["ok"] is False and r["collection"]["submittedSigners"] == [] and "signatures" not in r


def test_an_impersonator_replying_as_witness_three_does_not_make_witness_zero_count_twice(tmp_path):
    r, tr, coll, services, proposal = run(tmp_path, {3: impersonate(3)})          # impersonate(3) signs with witness 0's key
    assert signers(proposal, r) == sorted(ADDRS[:3]) and r["collection"]["outcomes"][3]["detail"] == "signature does not recover to the replying witness"


def test_the_impersonator_signature_verifies_on_its_own_so_only_the_origin_check_stops_it(tmp_path):
    ep = bz.Impersonator(lambda m: None, KEYS[0], "StateCheckpoint", DEPLOY)
    view = PoolView()
    proposal = svc.derive_checkpoint(view, DEPLOY)
    (delay, reply), = ep.deliver(1, proposal)
    assert reply["type"] == "signature" and reply["message"] == proposal and verify(reply["message"], reply["signature"]) == ADDRS[0]


def test_an_equivocators_two_signatures_are_both_real_signatures_of_the_same_key(tmp_path):
    ep = bz.Equivocator(ServiceEndpoint(lambda m: eip712.sign_digest(KEYS[3], messages.digest_of("StateCheckpoint", m, messages.domain_for("StateCheckpoint", m, DEPLOY)))),
                        KEYS[3], "StateCheckpoint", DEPLOY, lambda m: dict(m, authEpoch="99"))
    proposal = svc.derive_checkpoint(PoolView(), DEPLOY)
    replies = [rep for _, rep in ep.deliver(1, proposal)]
    assert len(replies) == 2 and replies[0]["message"] == proposal and replies[1]["message"]["authEpoch"] == "99"
    assert {verify(x["message"], x["signature"]) for x in replies} == {ADDRS[3]}


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# H3: one witness reads a different ledger view
# --------------------------------------------------------------------------------------------------------------------------------------------------------
class DivergentView(PoolView):
    def reads_at(self, number):
        r = super().reads_at(number)
        r["authEpoch"] = "9"
        return r


def test_one_witness_on_a_divergent_view_refuses_and_the_other_three_complete_the_certificate(tmp_path):
    view = PoolView()
    services = make_witnesses(tmp_path, view)
    proposal = svc.derive_checkpoint(view, DEPLOY)
    with bz.view_override(services[3], DivergentView()):
        tr = VirtualTransport([ServiceEndpoint(s.sign_checkpoint, reply_delay=300 if i < 3 else 100) for i, s in enumerate(services)])
        r = drv.run_collection(collection(view, proposal), tr)
    assert r["ok"] is True and signers(proposal, r) == sorted(ADDRS[:3]) and statuses(r) == ["signed", "signed", "signed", "refused"]
    assert services[3]._view is view                                         # restored


def test_two_witnesses_on_a_divergent_view_leave_nothing_submitted(tmp_path):
    view = PoolView()
    services = make_witnesses(tmp_path, view)
    proposal = svc.derive_checkpoint(view, DEPLOY)
    with bz.view_override(services[2], DivergentView()), bz.view_override(services[3], DivergentView()):
        r = drv.run_collection(collection(view, proposal), VirtualTransport([ServiceEndpoint(s.sign_checkpoint) for s in services]))
    assert r["ok"] is False and r["collection"]["submittedSigners"] == []


def test_the_view_is_restored_even_when_the_block_raises(tmp_path):
    view = PoolView()
    services = make_witnesses(tmp_path, view)
    with pytest.raises(RuntimeError):
        with bz.view_override(services[0], DivergentView()):
            raise RuntimeError("x")
    assert services[0]._view is view


def test_the_module_is_test_only_and_reads_no_clock_thread_or_socket():
    import os
    src = open(os.path.join(os.path.dirname(__file__), "..", "testtools", "byzantine.py")).read()
    assert "TEST-ONLY" in src.splitlines()[0] + src.splitlines()[1] + src.splitlines()[2]
    for banned in ("import time", "datetime", "import threading", "import socket", "import random", "subprocess", "os.environ"):
        assert banned not in src, banned


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# what each variant emits, directly (so a variant that silently stops being what its name says is caught even where the pool outcome would not change)
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def honest_endpoint(i=3):
    return ServiceEndpoint(lambda m: bz.sign_message(KEYS[i], "StateCheckpoint", m, DEPLOY), reply_delay=100)


def test_each_variant_emits_exactly_what_its_name_says():
    m = svc.derive_checkpoint(PoolView(), DEPLOY)
    assert bz.withhold(lambda x: None).deliver(1, m) == []
    d = bz.delayed(honest_endpoint(), 4000).deliver(1, m)
    assert [x for x, _ in d] == [4100] and d[0][1]["message"] == m
    rep = bz.Repeater(honest_endpoint(), 3).deliver(1, m)
    assert len(rep) == 3 and len({r["signature"] for _, r in rep}) == 1
    eq = bz.Equivocator(honest_endpoint(), KEYS[3], "StateCheckpoint", DEPLOY, lambda x: dict(x, authEpoch="99")).deliver(1, m)
    assert [r["message"]["authEpoch"] for _, r in eq] == [m["authEpoch"], "99"] and eq[1][0] > eq[0][0]
    po = bz.Poisoner(None, KEYS[3], "StateCheckpoint", DEPLOY, lambda x: dict(x, authEpoch="99")).deliver(1, m)
    assert len(po) == 1 and po[0][1]["message"]["authEpoch"] == "99" and verify(po[0][1]["message"], po[0][1]["signature"]) == ADDRS[3]
    assert bz.Garbage().deliver(1, m) == [(100, {"type": "no-such-reply"})]
    im = bz.Impersonator(None, KEYS[0], "StateCheckpoint", DEPLOY).deliver(1, m)
    assert len(im) == 1 and im[0][1]["message"] == m and verify(m, im[0][1]["signature"]) == ADDRS[0]


def test_the_variants_do_not_alias_the_message_they_were_given_and_record_each_delivery():
    m = svc.derive_checkpoint(PoolView(), DEPLOY)
    ep = bz.Poisoner(None, KEYS[3], "StateCheckpoint", DEPLOY, lambda x: x.update(authEpoch="99") or x)
    ep.deliver(1, m)
    assert m["authEpoch"] != "99" and ep.deliveries == [(1, m)]
    eq = bz.Equivocator(honest_endpoint(), KEYS[3], "StateCheckpoint", DEPLOY, lambda x: x.update(authEpoch="99") or x)         # an `alt` that edits its argument in place
    eq.deliver(1, m)
    assert m["authEpoch"] != "99"
    for e in (bz.Garbage(), bz.Impersonator(None, KEYS[0], "StateCheckpoint", DEPLOY), bz.delayed(honest_endpoint(), 1), bz.Repeater(honest_endpoint(), 2),
              bz.Equivocator(honest_endpoint(), KEYS[3], "StateCheckpoint", DEPLOY, lambda x: dict(x))):
        e.deliver(2, m)
        assert e.deliveries == [(2, m)]


def test_a_wrapper_keeps_the_inner_endpoints_delivery_hold():
    inner = ServiceEndpoint(lambda m: "0x", deliver_delay={1: 7, 2: 9})
    for w in (bz.delayed(inner, 5), bz.Repeater(inner, 2), bz.Equivocator(inner, KEYS[3], "StateCheckpoint", DEPLOY, lambda x: x)):
        assert (w.send_delay(1), w.send_delay(2)) == (7, 9)
