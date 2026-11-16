"""Pool decision core (agent 2, F task 3 slice 3a). Written BEFORE hmbc_protocol/pool_core.py existed.

`pool_core.py` is the PRODUCTION port of the pinned specification reference `protocol/f0/vectors/pool_adoption.py` (SIGNING-RULES section 8, SUCCESSOR-WIRE "Recorded-value reports and adoption"),
plus the assembly of the wire evidence that rule produces (`recordedReports`, `inconsistentReports`, `lateReports`, `adopted`, `timing`). It is pure: no clock, no network, no key, no I/O. The pool
orchestration (slice 3b) will feed it reports whose signatures it has ALREADY recovered; this module decides adoption and builds the evidence, nothing else.

What these tests establish, and what they do not:
  * DIFFERENTIAL against the reference: the same verdicts on every report list up to three reports drawn from 20 distinct reports, on every four-subset in two orders, on the exhaustive f <= 1
    safety enumeration (3,456 assignments), and on the time functions (the exhaustive B4 grid). The reference stays the specification; if the two ever differ the pin wins.
  * PRODUCTION-ONLY rules the reference leaves open (written down here as explicit choices, not discovered behaviour): messages are compared by canonical content (`json.dumps(sort_keys=True)`,
    the order the wire checker uses); one signature is kept per (witness, message), the lexicographically smallest, so the evidence does not depend on arrival order; only reports with a valid
    signature for the collection's sequence reach the evidence; time inputs are non-negative integers (stricter than the reference).
  * The assembled evidence is also fed to my INDEPENDENT wire checker (`protocol/f0/vectors/check_wire_examples.py`) appended to a copy of SUCCESSOR-WIRE.md. Same author, so correlated.
  * NOT established: signature recovery, the transport, the effort gate's use of a real host clock, any integrated run. Nothing here talks to a witness.
"""
import ast
import copy
import hashlib
import importlib.util
import itertools
import json
import os
import re
import subprocess
import sys
import tempfile

import pytest

from hmbc_protocol import pool_core as pc

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
V = os.path.join(ROOT, "protocol", "f0", "vectors")
_spec = importlib.util.spec_from_file_location("pool_adoption", os.path.join(V, "pool_adoption.py"))
ref = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ref)

SEQ = 7
A, B, FAKE, WRONG = ("7", "A"), ("7", "B"), ("7", "FAKE"), ("8", "A")


def to_msg(t):
    return {"sequence": t[0], "tag": t[1]}


def canon(m):
    return json.dumps(m, sort_keys=True)


def sig_of(w, t):
    return "0x" + hashlib.sha256(f"{w}|{canon(to_msg(t))}".encode()).hexdigest() * 2 + "1b"


def prod(r):
    """Reference report {witness, message tuple, validSignature} -> production report."""
    return {"witness": r["witness"], "message": to_msg(r["message"]), "signature": sig_of(r["witness"], r["message"]), "validSignature": r["validSignature"]}


def rrep(w, t, valid=True):
    return {"witness": w, "message": t, "validSignature": valid}


def same_adopt(p, r):
    return (p is None and r is None) or (p is not None and r is not None and p == to_msg(r))


def cons_view(c):
    return {w: canon(v["message"]) for w, v in c.items()}


def incons_view(c):
    return {w: [canon(v["message"]) for v in vs] for w, vs in c.items()}


def ref_cons_view(c):
    return {w: canon(to_msg(m)) for w, m in c.items()}


def ref_incons_view(c):
    return {w: sorted(canon(to_msg(m)) for m in ms) for w, ms in c.items()}


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# constants and the differential against the reference
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_constants_equal_the_reference_and_the_wire_text():
    assert (pc.REPLY_TIMEOUT_MS, pc.COLLECTION_CAP_MS, pc.RESERVE_S) == (ref.REPLY_TIMEOUT_MS, ref.COLLECTION_CAP_MS, ref.RESERVE_S) == (5000, 10000, 2)
    assert (pc.WITNESS_COUNT, pc.POOL_QUORUM) == (4, 3)


REPORT_POOL = [rrep(w, v) for w in range(4) for v in (A, B, FAKE, WRONG)] + [rrep(w, A, False) for w in range(4)]


def test_differential_every_report_list_of_up_to_three_reports():
    n = 0
    for k in range(0, 4):
        for combo in itertools.product(REPORT_POOL, repeat=k):
            rl = list(combo)
            pl = [prod(r) for r in rl]
            pa = pc.adopt_recorded(pl, SEQ)
            assert same_adopt(pa, ref.adopt_recorded(rl, SEQ)), rl
            c, i = pc.classify(pl, SEQ)
            rc, ri = ref.classify(rl, SEQ)
            assert cons_view(c) == ref_cons_view(rc) and incons_view(i) == ref_incons_view(ri), rl
            assert same_adopt(pc.decide(pl, [], SEQ), ref.decide(rl, [], SEQ))
            n += 1
    assert n == 1 + 20 + 400 + 8000


def test_differential_every_four_subset_in_two_orders():
    n = 0
    for combo in itertools.combinations(REPORT_POOL, 4):
        for rl in (list(combo), list(reversed(combo))):
            pl = [prod(r) for r in rl]
            assert same_adopt(pc.adopt_recorded(pl, SEQ), ref.adopt_recorded(rl, SEQ)), rl
            c, i = pc.classify(pl, SEQ)
            rc, ri = ref.classify(rl, SEQ)
            assert cons_view(c) == ref_cons_view(rc) and incons_view(i) == ref_incons_view(ri), rl
            n += 1
    assert n == 2 * 4845


def test_exhaustive_f_le_1_safety_matches_the_reference_assignment_by_assignment():
    honest_choices = [None, A, B]
    byz_pool = [A, B, FAKE, WRONG, ("7", "FAKE", "invalid")]
    cases = adopted_cases = 0
    for byz in range(4):
        honest = [i for i in range(4) if i != byz]
        for hv in itertools.product(honest_choices, repeat=3):
            for mask in range(1 << len(byz_pool)):
                rl = [rrep(w, v) for w, v in zip(honest, hv) if v is not None]
                for j, bz in enumerate(byz_pool):
                    if mask >> j & 1:
                        rl.append(rrep(byz, bz[:2], False) if len(bz) == 3 else rrep(byz, bz))
                got = pc.adopt_recorded([prod(r) for r in rl], SEQ)
                assert same_adopt(got, ref.adopt_recorded(rl, SEQ))
                cases += 1
                if got is not None:
                    adopted_cases += 1
                    assert got in [to_msg(v) for v in hv if v is not None], (byz, hv, mask)     # A1: an honest witness recorded it
    assert cases == 3456 and 0 < adopted_cases < cases


def test_control_outside_the_bound_two_byzantine_witnesses_get_a_fake_value_adopted():
    assert pc.adopt_recorded([prod(rrep(0, FAKE)), prod(rrep(1, FAKE))], SEQ) == to_msg(FAKE)


def test_named_cases_of_the_reference_hold():
    P = lambda *rs: [prod(r) for r in rs]  # noqa: E731
    assert pc.adopt_recorded(P(rrep(3, FAKE), rrep(3, A), rrep(0, A)), SEQ) is None                         # A8: the equivocator is excluded
    assert pc.adopt_recorded(P(rrep(3, FAKE), rrep(3, B), rrep(0, A), rrep(1, A)), SEQ) == to_msg(A)         # an equivocator does not block two honest reporters
    assert pc.adopt_recorded(P(rrep(0, A), rrep(0, A), rrep(1, A)), SEQ) == to_msg(A)                        # identical repeats are one report
    assert pc.adopt_recorded(P(rrep(3, FAKE), rrep(3, FAKE), rrep(3, FAKE)), SEQ) is None                    # A5
    assert pc.adopt_recorded(P(rrep(0, A), rrep(1, A), rrep(2, B), rrep(3, B)), SEQ) is None                 # A3 ambiguity
    assert pc.adopt_recorded(P(rrep(0, A, False), rrep(1, A, False)), SEQ) is None                           # A6
    assert pc.adopt_recorded(P(rrep(0, WRONG), rrep(1, WRONG)), SEQ) is None


def test_snapshot_only_late_reports_never_cancel_or_create_an_adoption():
    late_split = [prod(rrep(2, B)), prod(rrep(3, B))]
    pair_a = [prod(rrep(0, A)), prod(rrep(1, A))]
    assert pc.decide(pair_a, late_split, SEQ) == to_msg(A)                                    # A11
    assert pc.decide(late_split, pair_a, SEQ) == to_msg(B)
    assert pc.decide([prod(rrep(0, A))], [prod(rrep(1, A))], SEQ) is None
    assert pc.decide(pair_a + late_split, [prod(rrep(1, A))], SEQ) is None
    assert {canon(pc.decide(pair_a, late_split, SEQ)), canon(pc.decide(late_split, pair_a, SEQ))} == {canon(to_msg(A)), canon(to_msg(B))}   # A12


def test_decide_checks_the_shape_of_late_reports_even_though_they_are_not_an_input():
    bad = {"witness": 9, "message": to_msg(A), "signature": sig_of(0, A), "validSignature": True}
    with pytest.raises(pc.PoolCoreError):
        pc.decide([prod(rrep(0, A)), prod(rrep(1, A))], [bad], SEQ)


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the time functions
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_time_functions_agree_with_the_reference_on_the_exhaustive_grid_and_on_the_boundaries():
    n = 0
    for now0 in (1000, 1791521470):
        for prop in range(now0 - 2, now0 + 16):
            assert pc.collection_deadline_ms(now0, prop) == ref.collection_deadline_ms(now0, prop)
            d = ref.collection_deadline_ms(now0, prop)
            if d is None:
                continue
            for t_all in [None, 0, 500, 1999, 2000, 4999, 5000, 7000]:
                assert pc.snapshot_close(d, t_all) == ref.snapshot_close(d, t_all)
                close, _ = ref.snapshot_close(d, t_all)
                for exp in range(now0, now0 + 41):
                    assert pc.reproposal_status(now0, exp, close, d) == ref.reproposal_status(now0, exp, close, d)
                    n += 1
    assert n > 1000
    assert pc.collection_deadline_ms(1000, 1030) == 10000 and pc.collection_deadline_ms(1000, 1012) == 10000 and pc.collection_deadline_ms(1000, 1011) == 9000
    assert pc.collection_deadline_ms(1000, 1004) == 2000 and pc.collection_deadline_ms(1000, 1003) == 1000
    assert pc.collection_deadline_ms(1000, 1002) is None and pc.collection_deadline_ms(1000, 999) is None
    assert pc.snapshot_close(10000, 1200) == (1200, "all-replied") and pc.snapshot_close(10000, None) == (5000, "reply-timeout")
    assert pc.snapshot_close(10000, 5000) == (5000, "reply-timeout") and pc.snapshot_close(5000, None) == (5000, "deadline")
    assert pc.snapshot_close(2000, None) == (2000, "deadline") and pc.snapshot_close(6000, None) == (5000, "reply-timeout") and pc.snapshot_close(2000, 1500) == (1500, "all-replied")
    assert pc.reproposal_status(1000, 1007, 5000, 10000) == "skipped_validity"          # exactly 2000 ms left
    assert pc.reproposal_status(1000, 1007, 4999, 10000) == "sent"                     # 2001 ms left
    assert pc.reproposal_status(1000, 1006, 5000, 10000) == "skipped_validity"
    assert pc.reproposal_status(1000, 1030, 5000, 5000) == "skipped_deadline"          # the deadline is checked first
    assert pc.reproposal_status(1000, 1001, 2000, 2000) == "skipped_deadline"


@pytest.mark.parametrize("call", [
    lambda: pc.collection_deadline_ms(1000.5, 1030), lambda: pc.collection_deadline_ms("1000", 1030), lambda: pc.collection_deadline_ms(1000, True),
    lambda: pc.collection_deadline_ms(-1, 1030), lambda: pc.collection_deadline_ms(1000, -5),
    lambda: pc.snapshot_close(10000.0, None), lambda: pc.snapshot_close(True, None), lambda: pc.snapshot_close(10000, "1"), lambda: pc.snapshot_close(10000, -1), lambda: pc.snapshot_close(-5, None),
    lambda: pc.reproposal_status(1000.5, 1006, 5000, 10000), lambda: pc.reproposal_status(1000, True, 5000, 10000), lambda: pc.reproposal_status(1000, 1006, -1, 10000),
    lambda: pc.reproposal_status(1000, 1006, 5000, None),
])
def test_time_inputs_must_be_non_negative_integers(call):
    with pytest.raises(pc.PoolCoreError):
        call()


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# shape refusals
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def good(w=0, t=A):
    return prod(rrep(w, t))


@pytest.mark.parametrize("mutate", [
    lambda r: r.update(witness=4), lambda r: r.update(witness=-1), lambda r: r.update(witness=True), lambda r: r.update(witness="0"), lambda r: r.update(witness=1.0),
    lambda r: r.update(validSignature="yes"), lambda r: r.update(validSignature=1), lambda r: r.update(validSignature=None),
    lambda r: r.pop("signature"), lambda r: r.pop("message"), lambda r: r.pop("witness"), lambda r: r.pop("validSignature"), lambda r: r.update(extra="x"),
    lambda r: r.update(signature=None), lambda r: r.update(signature=12),
    lambda r: r.update(message="not a dict"), lambda r: r.update(message={"tag": "A"}), lambda r: r.update(message={"sequence": 7, "tag": "A"}),
    lambda r: r.update(message={"sequence": "7", "tag": 1}), lambda r: r.update(message=("7", "A")),
])
def test_a_malformed_report_is_refused_with_the_documented_error(mutate):
    r = good()
    mutate(r)
    for fn in (lambda: pc.classify([r], SEQ), lambda: pc.adopt_recorded([r], SEQ), lambda: pc.decide([good(1)], [r], SEQ)):
        with pytest.raises(pc.PoolCoreError):
            fn()


@pytest.mark.parametrize("bad", [None, "7", 7.0, True, -1])
def test_the_sequence_must_be_a_non_negative_integer(bad):
    with pytest.raises(pc.PoolCoreError):
        pc.classify([good()], bad)


@pytest.mark.parametrize("bad", [None, "x", {"witness": 0}, 5, ["x"], [None], [good(), "x"], [good(), None], (good(),)])
def test_the_report_list_must_be_a_list_of_dicts(bad):
    with pytest.raises(pc.PoolCoreError):
        pc.classify(bad, SEQ)


@pytest.mark.parametrize("garbage", [None, "junk", 12, [], {"x": 1}, {"sequence": 7}, ("7", "A")])
def test_a_report_with_an_invalid_signature_is_ignored_whatever_its_message_says(garbage):
    """A Byzantine witness must not be able to crash the pool: nothing but the witness index and the flag of an invalid report is read (the reference never reads its message either)."""
    junk = {"witness": 3, "message": garbage, "signature": garbage, "validSignature": False}
    rl = [prod(rrep(0, A)), prod(rrep(1, A)), junk]
    assert pc.adopt_recorded(rl, SEQ) == to_msg(A)
    c, i = pc.classify(rl, SEQ)
    assert sorted(c) == [0, 1] and i == {}
    out = ev([crep(0, CP_A), crep(1, CP_A), junk], [junk])                         # the same holds for the assembled evidence, in the snapshot and among late reports
    assert out["adopted"]["reporters"] == ["0", "1"] and "lateReports" not in out and "inconsistentReports" not in out


def test_the_evidence_needs_a_decimal_expiry_on_the_value_it_adopts():
    for bad in ({k: v for k, v in CP_A.items() if k != "expiresAt"}, {**CP_A, "expiresAt": "0x10"}, {**CP_A, "expiresAt": "01"}, {**CP_A, "expiresAt": "-1"}):
        with pytest.raises(pc.PoolCoreError):
            ev([crep(0, bad), crep(1, bad)])


def test_the_error_class_is_a_value_error_subclass_and_not_a_bare_exception():
    assert issubclass(pc.PoolCoreError, ValueError)


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# production-only choices
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_messages_are_compared_by_canonical_content_not_by_key_order_or_identity():
    m1 = {"sequence": "7", "tag": "A"}
    m2 = {"tag": "A", "sequence": "7"}
    r0 = {"witness": 0, "message": m1, "signature": sig_of(0, A), "validSignature": True}
    r1 = {"witness": 1, "message": m2, "signature": sig_of(1, A), "validSignature": True}
    assert pc.adopt_recorded([r0, r1], SEQ) == m1
    other = {"witness": 1, "message": {"sequence": "7", "tag": "a"}, "signature": sig_of(1, A), "validSignature": True}
    assert pc.adopt_recorded([r0, other], SEQ) is None                             # a one-character difference is a different value
    assert pc.canonical_message(m1) == pc.canonical_message(m2) == '{"sequence": "7", "tag": "A"}'


def test_a_non_canonical_sequence_string_is_a_wrong_sequence_not_a_match():
    rl = [{"witness": w, "message": {"sequence": "07", "tag": "A"}, "signature": sig_of(w, A), "validSignature": True} for w in (0, 1)]
    assert pc.adopt_recorded(rl, 7) is None and pc.classify(rl, 7) == ({}, {})


def test_one_witness_with_two_valid_signatures_over_one_value_is_consistent_and_keeps_the_smallest():
    s_lo, s_hi = "0x" + "11" * 65, "0x" + "ee" * 65
    rl = [{"witness": 0, "message": to_msg(A), "signature": s, "validSignature": True} for s in (s_hi, s_lo)]
    for order in (rl, rl[::-1]):
        c, i = pc.classify(order, SEQ)
        assert i == {} and c == {0: {"message": to_msg(A), "signature": s_lo}}


def test_an_equivocators_values_come_in_canonical_order_with_one_signature_each_whatever_the_arrival_order():
    rl = [prod(rrep(3, FAKE)), prod(rrep(3, A)), prod(rrep(3, B)), prod(rrep(3, A))]
    outs = []
    for p in itertools.permutations(rl):
        c, i = pc.classify(list(p), SEQ)
        assert c == {}
        outs.append(json.dumps(i, sort_keys=True))
    assert len(set(outs)) == 1
    _, i = pc.classify(rl, SEQ)
    assert [canon(v["message"]) for v in i[3]] == sorted(canon(to_msg(t)) for t in (A, B, FAKE))


def test_classify_returns_copies_and_never_mutates_its_input():
    rl = [prod(rrep(0, A)), prod(rrep(1, A)), prod(rrep(2, B))]
    before = copy.deepcopy(rl)
    c, _ = pc.classify(rl, SEQ)
    c[0]["message"]["tag"] = "TAMPERED"
    adopted = pc.adopt_recorded(rl, SEQ)
    adopted["tag"] = "TAMPERED"
    assert rl == before


def test_the_module_imports_only_the_standard_library_and_no_chain_key_or_network_code():
    src = open(os.path.join(ROOT, "protocol", "hmbc_protocol", "pool_core.py")).read()
    tree = ast.parse(src)
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            mods.add((node.module or "").split(".")[0] if node.level == 0 else "<relative>")
    assert mods <= {"__future__", "json", "re", "copy"}, mods
    assert "time" not in mods and "socket" not in mods and "subprocess" not in mods and "random" not in mods


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# evidence assembly
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def cp(seq="4", block="250", fill="5", expires="1791521500"):
    return {"sequence": seq, "authEpoch": "3", "policyVersion": "1", "keyEpoch": "0", "witnessSetVersion": "2", "sourceChainId": "18545",
            "psc": "0x1613beb3b2c4f22ee086b2b38c1476a3ce7f78e8", "sourceBlockNumber": block, "sourceBlockHash": "0x" + fill * 64, "expiresAt": expires}


def csig(w, m):
    return "0x" + hashlib.sha256(f"{w}|{canon(m)}".encode()).hexdigest() * 2 + "1b"


def crep(w, m, valid=True, signature=None):
    return {"witness": w, "message": m, "signature": csig(w, m) if signature is None else signature, "validSignature": valid}


T0 = 1791521470
CP_A = cp(block="250", fill="5", expires="1791521500")
CP_B = cp(block="251", fill="6", expires="1791521500")


def ev(snapshot, late=(), seq=4, now0=T0, prop=T0 + 30, all_at=None):
    return pc.evidence(list(snapshot), list(late), seq, ledger_now_at_start=now0, proposal_expires_at=prop, all_replied_at_ms=all_at)


def test_nothing_to_report_yields_no_members_and_no_timing():
    assert ev([]) == {}
    assert ev([crep(0, CP_A, valid=False), crep(1, CP_A, valid=False)]) == {}                    # invalid signatures are never evidence
    assert ev([crep(0, cp(seq="9"))]) == {}                                                       # nor are other sequences
    assert ev([], [crep(2, CP_A, valid=False), crep(3, cp(seq="9"))]) == {}


def test_a_pair_is_adopted_and_the_members_have_the_wire_shapes():
    out = ev([crep(0, CP_A), crep(1, CP_A), crep(2, CP_B), crep(3, cp(block="252", fill="7"))], all_at=1200)
    assert set(out) == {"recordedReports", "adopted", "timing"}
    assert [r["witnessIndex"] for r in out["recordedReports"]] == ["0", "1", "2", "3"]
    assert out["recordedReports"][0] == {"witnessIndex": "0", "message": CP_A, "signature": csig(0, CP_A)}
    assert out["adopted"] == {"message": CP_A, "reporters": ["0", "1"], "reproposal": "sent"}
    assert out["timing"] == {"ledgerNowAtStart": str(T0), "proposalExpiresAt": str(T0 + 30), "collectionDeadlineMs": "10000", "snapshotClosedAtMs": "1200", "snapshotClosedBy": "all-replied"}


def test_the_reporters_are_the_consistent_witnesses_reporting_the_value_in_ascending_order():
    out = ev([crep(3, CP_A), crep(0, CP_A), crep(2, CP_B), crep(1, CP_A)])
    assert out["adopted"]["reporters"] == ["0", "1", "3"]
    assert [r["witnessIndex"] for r in out["recordedReports"]] == ["0", "1", "2", "3"]


def test_an_equivocator_is_evidence_only_and_excluded_from_the_decision():
    out = ev([crep(3, CP_B), crep(3, CP_A), crep(0, CP_A)])
    assert "adopted" not in out
    assert [r["witnessIndex"] for r in out["recordedReports"]] == ["0"]
    assert out["inconsistentReports"] == [{"witnessIndex": "3", "reports": sorted(
        [{"message": CP_A, "signature": csig(3, CP_A)}, {"message": CP_B, "signature": csig(3, CP_B)}], key=lambda x: canon(x["message"]))}]
    assert set(out) == {"recordedReports", "inconsistentReports", "timing"}
    assert out["timing"]["snapshotClosedBy"] == "reply-timeout" and out["timing"]["snapshotClosedAtMs"] == "5000"


def test_an_equivocator_does_not_block_two_honest_reporters_and_the_lists_are_disjoint():
    out = ev([crep(3, CP_B), crep(3, cp(block="252", fill="7")), crep(0, CP_A), crep(1, CP_A)])
    assert out["adopted"]["message"] == CP_A and out["adopted"]["reporters"] == ["0", "1"]
    assert {r["witnessIndex"] for r in out["recordedReports"]}.isdisjoint({e["witnessIndex"] for e in out["inconsistentReports"]})


def test_late_reports_are_sorted_unique_evidence_that_never_change_the_adoption():
    snapshot = [crep(0, CP_A), crep(1, CP_A)]
    late = [crep(3, CP_B), crep(2, CP_B), crep(3, CP_B), crep(2, CP_A), crep(1, CP_B, valid=False), crep(2, cp(seq="9"))]
    out, bare = ev(snapshot, late), ev(snapshot)
    assert out["adopted"] == bare["adopted"] and out["recordedReports"] == bare["recordedReports"]
    keys = [(int(x["witnessIndex"]), canon(x["message"])) for x in out["lateReports"]]
    assert keys == sorted(set(keys)) and len(keys) == 3
    assert {k[0] for k in keys} == {2, 3} and all(set(x) == {"witnessIndex", "message", "signature"} for x in out["lateReports"])
    assert "lateReports" not in bare


def test_late_duplicates_keep_the_smallest_signature():
    s_lo, s_hi = "0x" + "11" * 65, "0x" + "ee" * 65
    for order in ((s_hi, s_lo), (s_lo, s_hi)):
        out = ev([crep(0, CP_A), crep(1, CP_A)], [crep(2, CP_B, signature=s) for s in order])
        assert out["lateReports"] == [{"witnessIndex": "2", "message": CP_B, "signature": s_lo}]


def test_the_adoption_is_independent_of_every_late_set_drawn_from_the_report_pool():
    snapshot = [crep(0, CP_A), crep(1, CP_A), crep(2, CP_B)]
    base = ev(snapshot)["adopted"]
    pool = [crep(w, m, v) for w in range(4) for m in (CP_A, CP_B) for v in (True, False)]
    n = 0
    for k in range(0, 3):
        for late in itertools.product(pool, repeat=k):
            assert ev(snapshot, late)["adopted"] == base
            n += 1
    assert n == 1 + 16 + 256


def test_a_snapshot_without_an_adoption_stays_so_whatever_arrives_late():
    out = ev([crep(0, CP_A)], [crep(1, CP_A)])
    assert "adopted" not in out and out["recordedReports"][0]["witnessIndex"] == "0" and out["lateReports"][0]["witnessIndex"] == "1"
    assert "adopted" not in ev([crep(0, CP_A), crep(1, CP_A), crep(2, CP_B), crep(3, CP_B)], [crep(1, CP_A)])


def test_the_reproposal_gate_is_recorded_as_the_action_beside_the_selection():
    exp6 = cp(expires=str(T0 + 6))
    out = ev([crep(0, exp6), crep(1, exp6)])                                  # closes at the 5 s reply timeout, 1 s of validity left
    assert out["adopted"]["message"] == exp6 and out["adopted"]["reproposal"] == "skipped_validity"
    exp7 = cp(expires=str(T0 + 7))
    assert ev([crep(0, exp7), crep(1, exp7)], all_at=4999)["adopted"]["reproposal"] == "sent"               # 2001 ms
    assert ev([crep(0, exp7), crep(1, exp7)])["adopted"]["reproposal"] == "skipped_validity"                # exactly 2000 ms at 5000
    hard = ev([crep(0, CP_A), crep(1, CP_A)], prop=T0 + 4)                    # deadline 2 s: closes at the deadline, no second round
    assert hard["timing"] == {"ledgerNowAtStart": str(T0), "proposalExpiresAt": str(T0 + 4), "collectionDeadlineMs": "2000", "snapshotClosedAtMs": "2000", "snapshotClosedBy": "deadline"}
    assert hard["adopted"]["reproposal"] == "skipped_deadline" and "lateReports" not in hard


def test_nothing_after_the_original_deadline_is_collected():
    with pytest.raises(pc.PoolCoreError):
        ev([crep(0, CP_A), crep(1, CP_A)], [crep(2, CP_A)], prop=T0 + 4)       # closed by the deadline: a late report cannot exist
    assert "lateReports" in ev([crep(0, CP_A), crep(1, CP_A)], [crep(2, CP_A)], prop=T0 + 12)


def test_no_collection_exists_when_two_seconds_or_less_remain():
    for prop in (T0 + 2, T0 + 1, T0, T0 - 5):
        with pytest.raises(pc.PoolCoreError):
            ev([crep(0, CP_A), crep(1, CP_A)], prop=prop)


def test_all_replied_must_be_strictly_inside_the_limit_and_nonnegative():
    assert ev([crep(0, CP_A), crep(1, CP_A)], all_at=4999)["timing"]["snapshotClosedBy"] == "all-replied"
    assert ev([crep(0, CP_A), crep(1, CP_A)], all_at=5000)["timing"]["snapshotClosedBy"] == "reply-timeout"
    for bad in (-1, True, 1.5, "1"):
        with pytest.raises(pc.PoolCoreError):
            ev([crep(0, CP_A), crep(1, CP_A)], all_at=bad)


def test_the_evidence_does_not_mutate_its_inputs_and_returns_copies():
    snapshot, late = [crep(0, CP_A), crep(1, CP_A)], [crep(2, CP_B)]
    before = copy.deepcopy((snapshot, late))
    out = pc.evidence(snapshot, late, 4, ledger_now_at_start=T0, proposal_expires_at=T0 + 30, all_replied_at_ms=None)
    out["adopted"]["message"]["sequence"] = "TAMPERED"
    assert out["recordedReports"][0]["message"] == CP_A and out["recordedReports"][1]["message"] == CP_A       # the members do not alias one another
    out["recordedReports"][0]["message"]["sequence"] = "TAMPERED"
    out["lateReports"][0]["message"]["sequence"] = "TAMPERED"
    assert (snapshot, late) == before


def test_evidence_with_the_wrong_witness_index_or_sequence_type_is_refused():
    with pytest.raises(pc.PoolCoreError):
        ev([crep(5, CP_A)])
    with pytest.raises(pc.PoolCoreError):
        pc.evidence([crep(0, CP_A)], [], "4", ledger_now_at_start=T0, proposal_expires_at=T0 + 30, all_replied_at_ms=None)


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the assembled evidence through my independent wire checker (correlated: same author)
# --------------------------------------------------------------------------------------------------------------------------------------------------------
ADDR = {i: "0x" + str(i + 1) * 40 for i in range(4)}


def outcomes(status_by_index, replies=None):
    out = []
    for i in range(4):
        st = status_by_index[i]
        o = {"witnessIndex": str(i), "witness": ADDR[i], "status": st, "replies": str((replies or {}).get(i, 0 if st == "silent" else 1))}
        if st == "refused":
            o.update(code="STALE_STATE", reason="CONFLICT_PINNED")
        if st == "invalid":
            o["detail"] = "returned two different recorded values; excluded from adoption"
        out.append(o)
    return out


def envelope(statuses, evidence):
    coll = {"quorum": "3", "witnessSetVersion": "2", "outcomes": outcomes(statuses), **evidence, "submittedSigners": []}
    return {"schemaVersion": "v2", "ok": False, "result": None, "error": {"code": "ADAPTER_UNAVAILABLE", "reason": "QUORUM_UNAVAILABLE", "message": "produced by pool_core for the cross-check", "collection": coll}}


def scenarios():
    R = "refused"
    yield "all-replied pair", envelope([R, R, R, R], ev([crep(0, CP_A), crep(1, CP_A), crep(2, CP_B), crep(3, cp(block="252", fill="7"))], all_at=1200))
    yield "equivocator", envelope([R, "silent", "silent", "invalid"], ev([crep(3, CP_B), crep(3, CP_A), crep(0, CP_A)]))
    yield "late split", envelope([R, R, R, R], ev([crep(0, CP_A), crep(1, CP_A)], [crep(2, CP_B), crep(3, CP_B)]))
    yield "late split reversed", envelope([R, R, R, R], ev([crep(2, CP_B), crep(3, CP_B)], [crep(0, CP_A), crep(1, CP_A)]))
    e6 = cp(expires=str(T0 + 6))
    yield "skipped validity", envelope([R, R, "silent", "silent"], ev([crep(0, e6), crep(1, e6)]))
    yield "hard stop", envelope([R, R, "silent", "silent"], ev([crep(0, CP_A), crep(1, CP_A)], prop=T0 + 4))
    yield "snapshot without adoption", envelope([R, R, "silent", "silent"], ev([crep(0, CP_A)], [crep(1, CP_A)]))


def run_wire_checker(extra_examples):
    text = open(os.path.join(ROOT, "protocol", "f0", "SUCCESSOR-WIRE.md"), encoding="utf-8").read()
    text += "\n" + "".join("\n```json\n" + json.dumps(e) + "\n```\n" for e in extra_examples)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "SUCCESSOR-WIRE.md")
        open(p, "w", encoding="utf-8").write(text)
        r = subprocess.run([sys.executable, "-B", "-I", os.path.join(V, "check_wire_examples.py"), p], capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout


def test_the_assembled_evidence_passes_my_wire_checker_and_a_tampered_copy_fails_it():
    exs = [e for _, e in scenarios()]
    rc0, out0 = run_wire_checker([])
    assert rc0 == 0
    rc, out = run_wire_checker(exs)
    assert rc == 0, "\n".join(l for l in out.splitlines() if l.startswith("FAIL"))
    assert out.count("ok   ") >= out0.count("ok   ") + 3 * len(exs)               # the appended examples were really checked
    # negative controls: the harness can fail. Each tampering changes one fact the checker recomputes.
    tamper = [
        lambda c: c["adopted"].update(reporters=["1", "0"]),
        lambda c: c["adopted"].update(reproposal="sent" if c["adopted"]["reproposal"] != "sent" else "skipped_validity"),
        lambda c: c["timing"].update(collectionDeadlineMs="9999"),
        lambda c: c["recordedReports"].reverse() if len(c["recordedReports"]) > 1 else c.pop("recordedReports"),
    ]
    base = envelope(["refused"] * 4, ev([crep(0, CP_A), crep(1, CP_A), crep(2, CP_B), crep(3, cp(block="252", fill="7"))], all_at=1200))
    assert run_wire_checker([base])[0] == 0
    for t in tamper:
        e = copy.deepcopy(base)
        t(e["error"]["collection"])
        rc2, _ = run_wire_checker([e])
        assert rc2 != 0, t
