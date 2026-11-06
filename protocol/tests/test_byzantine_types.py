"""TEST-ONLY Byzantine variants against the other three signed types (agent 2, F task 3 slice 7b). Written BEFORE `testtools/byzantine.sign_message` knew the receipt and governance digests.

Slice 7a ran the variants against checkpoints only. Here the same variants run against AccessDecision, GrantReceipt and GovernanceAction collections (no adoption: only a checkpoint adopts), with real
`WitnessService` objects, real stores, the real pool and driver and ONE shared fake ledger view (so this says nothing about independent views, a real transport or a real chain). Claim: with one Byzantine
witness a verifying three-signature certificate over the proposal still forms from signatures of distinct members, a Byzantine reply is never counted, and with two impersonating or silent witnesses nothing is
submitted; per-witness statuses as for checkpoints.
"""
import pytest

from hmbc_protocol import adapter_v2_witness as aw
from hmbc_protocol import eip712, keys
from hmbc_protocol import pool_core as core
from hmbc_protocol import witness_pool as wp
from hmbc_protocol import witness_pool_driver as drv
from hmbc_protocol import witness_service as svc
from testtools import byzantine as bz
from testtools.virtual_transport import ServiceEndpoint, VirtualTransport

from test_adapter_v2_witness import ADDRS, CASES, DIGEST, GRANT, KEYS, MAN, NOW, Rig, act, digest

OUTSIDER = keys.synthetic_private_key("outsider")

KINDS = {
    "decision": dict(method="sign_decision", typed="AccessDecision", mutate=lambda m: dict(m, expiresAt=str(int(m["expiresAt"]) + 1))),
    "receipt": dict(method="sign_receipt", typed="GrantReceipt", mutate=lambda m: dict(m, dbcBlockNumber="999")),
    "governance": dict(method="sign_governance", typed="GovernanceAction", mutate=lambda m: dict(m, nonce="99")),
}


def setup(tmp_path, kind):
    rig = Rig(tmp_path)
    v = rig.view
    if kind == "decision":
        proposal, now, expires = svc.derive_decision(v, MAN, DIGEST, witness_set_version="2")[0], 1000, None
        expires = int(proposal["expiresAt"])
    elif kind == "receipt":
        proposal, now = svc.derive_receipt(v, MAN, GRANT, witness_set_version="2"), 1000
        expires = now + 60
    else:
        proposal, now, expires = act(), NOW, NOW + 60
    return rig, proposal, now, expires


def run(tmp_path, kind, variants):
    rig, proposal, now, expires = setup(tmp_path, kind)
    k = KINDS[kind]
    eps = [variants[i](rig.services[i], k) if i in variants else ServiceEndpoint(getattr(rig.services[i], k["method"]), reply_delay=300) for i in range(4)]
    coll = wp.Collection(witnesses=ADDRS, recover=aw._recover(kind, MAN), proposal=proposal, ledger_now_at_start=now, proposal_expires_at=expires, adoption=False, witness_set_version="2")
    return drv.run_collection(coll, VirtualTransport(eps)), proposal


def signers(kind, proposal, r):
    return [eip712.recover(digest(KINDS[kind]["typed"], proposal), s) for s in r["signatures"]]


VARIANTS = {
    "withhold": (lambda s, k: bz.withhold(getattr(s, k["method"])), "silent"),
    "impersonate": (lambda s, k: bz.Impersonator(None, KEYS[0], k["typed"], MAN), "invalid"),
    "outsider": (lambda s, k: bz.Impersonator(None, OUTSIDER, k["typed"], MAN), "invalid"),
    "poison": (lambda s, k: bz.Poisoner(None, KEYS[3], k["typed"], MAN, k["mutate"]), "dissent"),
    "garbage": (lambda s, k: bz.Garbage(), "invalid"),
    "late": (lambda s, k: bz.delayed(ServiceEndpoint(getattr(s, k["method"])), 6000), "silent"),
}


@pytest.mark.parametrize("kind", list(KINDS))
@pytest.mark.parametrize("name", list(VARIANTS))
def test_one_byzantine_witness_cannot_stop_or_taint_a_certificate_of_any_type(tmp_path, kind, name):
    make, status = VARIANTS[name]
    r, proposal = run(tmp_path, kind, {3: make})
    assert r["ok"] is True and r["message"] == proposal
    assert signers(kind, proposal, r) == sorted(ADDRS[:3]) == r["collection"]["submittedSigners"]
    assert [o["status"] for o in r["collection"]["outcomes"]] == ["signed", "signed", "signed", status]


@pytest.mark.parametrize("kind", list(KINDS))
@pytest.mark.parametrize("name", ["withhold", "impersonate", "outsider", "garbage"])
def test_two_byzantine_witnesses_leave_nothing_submitted_for_any_type(tmp_path, kind, name):
    make, _ = VARIANTS[name]
    r, _ = run(tmp_path, kind, {2: make, 3: make})
    assert r["ok"] is False and r["collection"]["submittedSigners"] == [] and "signatures" not in r


@pytest.mark.parametrize("kind", list(KINDS))
def test_repeat_and_equivocate_count_the_genuine_signer_once_for_any_type(tmp_path, kind):
    for make in (lambda s, k: bz.Repeater(ServiceEndpoint(getattr(s, k["method"])), 3),
                 lambda s, k: bz.Equivocator(ServiceEndpoint(getattr(s, k["method"])), KEYS[3], k["typed"], MAN, k["mutate"])):
        r, proposal = run(tmp_path / ("a%d" % id(make)), kind, {3: make})
        got = signers(kind, proposal, r)
        assert r["ok"] is True and len(set(got)) == 3 and ADDRS[3] in got and got == r["collection"]["submittedSigners"] == sorted(got)
