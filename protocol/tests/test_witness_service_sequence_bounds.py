"""The checkpoint sequence at the uint64 boundary (agent 2, slice 10b). Written BEFORE running it; prompted by A3-0095.

A3-0095 reproduced on the real ledger that a certified checkpoint may skip sequences (the KSSC rule is strictly increasing, not current + 1) and that three controlled keys can install uint64 max, after which no
representable checkpoint successor exists. My earlier conclusion "honest witnesses are not blocked" holds for ordinary skips only. This file pins what MY side does at the boundary, with the fake view of the
service tests: the proposer derives max from max-1, REFUSES to derive past max (a WireError, never a wrapped or oversized sequence), and a witness refuses a proposal whose sequence is not current + 1, including
max + 1 and a skip to max. It does NOT show any recovery from a saturated ledger: there is none on the witness side.
"""
import pytest

from hmbc_protocol import wire
from hmbc_protocol import witness_service as svc

from test_witness_service import DEPLOY, FakeView, KEY, ADDR, OWNER, B, BIND, h, refusal
from hmbc_protocol import witness_state as ws

MAX = 2 ** 64 - 1


def view_at(seq):
    v = FakeView()
    v.current = {"sequence": str(seq), "sourceBlockNumber": "100"}
    return v


@pytest.mark.parametrize("current,expected", [(5, "6"), (7, "8"), (MAX - 1, str(MAX))])
def test_the_proposer_derives_current_plus_one_below_the_boundary(current, expected):
    assert svc.derive_checkpoint(view_at(current), DEPLOY)["sequence"] == expected


def test_the_proposer_refuses_to_derive_past_uint64_max():
    with pytest.raises(wire.WireError):
        svc.derive_checkpoint(view_at(MAX), DEPLOY)


@pytest.fixture
def service(tmp_path):
    v = view_at(5)
    st = ws.init_store(str(tmp_path / "w"), BIND, B, OWNER)
    return svc.WitnessService(store=st, key=KEY, view=v, deployment=DEPLOY, witness_set_version="2"), v


def test_a_witness_refuses_a_skipped_sequence_a_repeat_a_lower_one_and_max_plus_one(service):
    s, v = service
    good = svc.derive_checkpoint(v, DEPLOY)
    assert good["sequence"] == "6"
    for seq in ("7", "8", str(MAX), "5", "4", "0", str(MAX + 1)):
        e = refusal(lambda seq=seq: s.sign_checkpoint(dict(good, sequence=seq)))
        assert e is not None and e.code in ("STALE_STATE", "MALFORMED"), (seq, e and e.code)
    assert s.sign_checkpoint(good)                                          # the exact successor still signs


def test_a_witness_on_a_saturated_ledger_signs_nothing(tmp_path):
    v = view_at(MAX)
    st = ws.init_store(str(tmp_path / "w"), BIND, B, OWNER)
    s = svc.WitnessService(store=st, key=KEY, view=v, deployment=DEPLOY, witness_set_version="2")
    base = svc.derive_checkpoint(view_at(5), DEPLOY)
    for seq in (str(MAX), str(MAX + 1), "1", "6"):
        e = refusal(lambda seq=seq: s.sign_checkpoint(dict(base, sequence=seq)))
        assert e is not None, seq
