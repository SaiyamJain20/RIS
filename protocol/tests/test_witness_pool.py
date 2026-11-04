"""Pool collection state machine (agent 2, F task 3 slice 3b). Written BEFORE hmbc_protocol/witness_pool.py existed.

`witness_pool.Collection` is ONE pool collection as a sans-IO state machine: it is told what happened (a reply from witness w at host-monotonic millisecond t, or that time passed) and answers with
actions to perform (send the retained proposal, cancel an undelivered send). It holds no key, opens no socket, reads no clock and signs nothing. The decision core is `pool_core` (slice 3a); this
module owns the PROCEDURE of SIGNING-RULES section 8 and SUCCESSOR-WIRE section 2: retain the proposal, fan out to four witnesses, validate every reply itself (strict parse, digest recomputed,
signer recovered and equal to the replying witness's configured address), deduplicate, stop at three distinct valid signatures over one message, close the decision snapshot, adopt, apply the effort
gate, run one second round inside the original deadline, and classify every witness.

How these tests work. A deterministic virtual-time harness plays four witnesses against a Collection. Honest witnesses are a small model of the F signing rule (first value for a sequence is
recorded and signed; the same value returns the stored signature; another value is refused CONFLICT_PINNED with the recorded value and its stored signature). The cryptography is REAL (synthetic
public keys, the production EIP-712 digest and signature recovery), the witnesses are NOT the real witness service and there is no ledger. The assembled outputs are also given to my independent wire
checker. NOT established: anything about a real transport, a real clock, the real witness store or the adapter envelope.

Explicit choices where F0 is silent (recorded, not discovered): a timer due at millisecond t fires BEFORE a reply at t (a reply exactly at the reply timeout is late; a reply at or after the deadline
is ignored); the collection ends early when nothing can change (all four replied and no round can start); an early success takes no snapshot and serializes no evidence members; the status of a
witness is judged against the final reference message M* (the certificate's message, else the adopted value, else the retained proposal); `duplicate-only` is in the wire vocabulary but no reply sequence
over per-witness channels reaches it, so the collector never emits it (the unreachable status is listed as a limit).
"""
import copy
import hashlib
import heapq
import json
import os
import subprocess
import sys
import tempfile

import pytest

from hmbc_protocol import eip712, keys, messages
from hmbc_protocol import pool_core as core
from hmbc_protocol import witness_pool as wp

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
V = os.path.join(ROOT, "protocol", "f0", "vectors")
DEPLOY = json.load(open(os.path.join(ROOT, "protocol", "tests", "fixtures", "deployment-agent1-91add8c-v1-repaired-e.json")))
LABELS = [f"witness-{i}" for i in range(1, 5)]
KEYS = [keys.synthetic_private_key(l) for l in LABELS]
from eth_account import Account  # noqa: E402  (after the package imports: it is a third-party dependency of the existing E code)
ADDR = [Account.from_key(k).address.lower() for k in KEYS]
_RECOVER_RAW = wp.make_recover("StateCheckpoint", DEPLOY)
_RCACHE, _SCACHE = {}, {}
T0 = 1791521470


def RECOVER(m, signature):                                    # memoised: the property test below makes thousands of calls (deterministic ECDSA, same answers)
    k = (json.dumps(m, sort_keys=True, default=str), signature if isinstance(signature, str) else repr(signature))
    if k not in _RCACHE:
        _RCACHE[k] = _RECOVER_RAW(m, signature)
    return _RCACHE[k]


def cp(seq="4", block="250", fill="5", expires=None):
    return {"sequence": seq, "authEpoch": "3", "policyVersion": "1", "keyEpoch": "0", "witnessSetVersion": "2", "sourceChainId": "18545",
            "psc": "0x1613beb3b2c4f22ee086b2b38c1476a3ce7f78e8", "sourceBlockNumber": block, "sourceBlockHash": "0x" + fill * 64, "expiresAt": str(T0 + 30 if expires is None else expires)}


A = cp(block="250", fill="5", expires=T0 + 30)
B = cp(block="251", fill="6", expires=T0 + 30)
C = cp(block="252", fill="7", expires=T0 + 30)


def canon(m):
    return json.dumps(m, sort_keys=True)


def sign(w, m):
    k = (w, canon(m))
    if k not in _SCACHE:
        _SCACHE[k] = eip712.sign_digest(KEYS[w], messages.digest_of("StateCheckpoint", m, messages.domain_for("StateCheckpoint", m, DEPLOY)))
    return _SCACHE[k]


def sig_reply(m, signature):
    return {"type": "signature", "message": m, "signature": signature}


def pinned(m, signature):
    return {"type": "error", "code": "STALE_STATE", "reason": "CONFLICT_PINNED", "recorded": {"message": m, "signature": signature}}


class Wit:
    """An honest witness (the F signing rule, none of the store's other machinery). Behaviour knobs: per-round delivery delay and reply delay; `muted` never replies."""

    def __init__(self, idx, deliver_delay=0, reply_delay=100, muted=False):
        self.idx, self.deliver_delay, self.reply_delay, self.muted = idx, deliver_delay, reply_delay, muted
        self.store, self.deliveries = {}, []

    def preload(self, m):
        self.store[m["sequence"]] = (m, sign(self.idx, m))

    def _delay(self, knob, rnd):
        return knob[rnd] if isinstance(knob, dict) else knob

    def send_delay(self, rnd):
        return self._delay(self.deliver_delay, rnd)

    def handle(self, rnd, m):
        rec = self.store.get(m["sequence"])
        if rec is None:
            self.store[m["sequence"]] = (m, sign(self.idx, m))
            return sig_reply(m, self.store[m["sequence"]][1])
        if canon(rec[0]) == canon(m):
            return sig_reply(rec[0], rec[1])
        return pinned(rec[0], rec[1])

    def deliver(self, rnd, m):
        self.deliveries.append((rnd, canon(m)))
        if self.muted:
            return []
        r = self.handle(rnd, m)
        return [(self._delay(self.reply_delay, rnd), r)]


class Scripted(Wit):
    """A witness (Byzantine or merely odd) that answers with a fixed list of (delay, reply) per round."""

    def __init__(self, idx, script, deliver_delay=0):
        super().__init__(idx, deliver_delay)
        self.script = script

    def deliver(self, rnd, m):
        self.deliveries.append((rnd, canon(m)))
        s = self.script
        return list(s[rnd]) if isinstance(s, dict) else list(s)


def make(proposal=None, now0=T0, prop=T0 + 30, adoption=True, **kw):
    return wp.Collection(witnesses=ADDR, recover=RECOVER, proposal=A if proposal is None else proposal, ledger_now_at_start=now0, proposal_expires_at=prop,
                         adoption=adoption, witness_set_version="2", **kw)


def drive(coll, wits, limit_ms=60000):
    """Run the collection on virtual time. Returns the list of (t, action) the collection emitted."""
    q, seq, log, now = [], 0, [], 0

    def push(t, kind, payload):
        nonlocal seq
        seq += 1
        heapq.heappush(q, (t, 1 if kind == "reply" else 0, seq, kind, payload))

    def perform(actions, t):
        for a in actions:
            log.append((t, copy.deepcopy(a)))
            if a["op"] == "send":
                push(t + wits[a["witness"]].send_delay(a["round"]), "deliver", (a["witness"], a["round"], a["message"]))
            elif a["op"] == "cancel":
                q[:] = [e for e in q if not (e[3] == "deliver" and e[4][0] == a["witness"] and e[4][1] == a["round"])]
                heapq.heapify(q)

    perform(coll.start(), 0)
    steps = 0
    while not coll.done:
        steps += 1
        assert steps < 5000, "the collection does not advance: a timer is due but nothing changes"     # a guard so that a defective timer fails the test instead of hanging it
        nxt_timer = coll.next_timer_ms()
        nxt_event = q[0][0] if q else None
        cands = [x for x in (nxt_timer, nxt_event) if x is not None]
        if not cands:
            break
        t = min(cands)
        if t > limit_ms:
            break
        if nxt_timer is not None and nxt_timer == t and (nxt_event is None or nxt_event >= t):
            perform(coll.on_time(t), t)
            continue
        _, _, _, kind, payload = heapq.heappop(q)
        if kind == "deliver":
            w, rnd, m = payload
            for delay, reply in wits[w].deliver(rnd, m):
                push(t + delay, "reply", (w, rnd, reply))
        else:
            w, rnd, reply = payload
            perform(coll.on_reply(t, w, reply, rnd), t)
    return log


def honest(**knobs):
    return [Wit(i, **knobs) for i in range(4)]


def outcome_view(res):
    return [(o["status"], o["replies"]) for o in res["collection"]["outcomes"]]


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# refusal before any contact, and the retained proposal
# --------------------------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("prop", [T0 + 2, T0 + 1, T0, T0 - 3])
def test_a_proposal_with_two_seconds_or_less_is_refused_expired_before_any_witness_is_contacted(prop):
    with pytest.raises(wp.CollectionRefused) as e:
        make(prop=prop)
    assert e.value.code == "EXPIRED" and e.value.reason is None


def test_the_proposal_is_retained_and_sent_verbatim_to_all_four_witnesses_exactly_once():
    c = make()
    first = c.start()
    assert [(a["op"], a["witness"], a["round"]) for a in first] == [("send", w, 1) for w in range(4)]
    assert all(canon(a["message"]) == canon(A) for a in first)
    with pytest.raises(wp.CollectionError):
        c.start()                                                                           # a collection starts once


def test_the_retained_proposal_is_a_private_copy_the_caller_cannot_change_later():
    mine = copy.deepcopy(A)
    c = make(proposal=mine)
    mine["sourceBlockNumber"] = "999"
    assert all(canon(a["message"]) == canon(A) for a in c.start())


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# validation of every reply, deduplication, and the certificate
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_three_valid_signatures_end_the_collection_at_once_with_exactly_three_sorted_signatures():
    c = make()
    drive(c, [Wit(0, reply_delay=100), Wit(1, reply_delay=200), Wit(2, reply_delay=300), Wit(3, reply_delay=400)])
    r = c.result
    assert c.done and r["ok"] is True and r["message"] == A
    sigs = r["signatures"]
    assert len(sigs) == 3 and len({eip712.recover(messages.digest_of("StateCheckpoint", A, messages.domain_for("StateCheckpoint", A, DEPLOY)), s) for s in sigs}) == 3
    addrs = [eip712.recover(messages.digest_of("StateCheckpoint", A, messages.domain_for("StateCheckpoint", A, DEPLOY)), s) for s in sigs]
    assert addrs == sorted(addrs) and r["collection"]["submittedSigners"] == addrs and set(addrs) == set(ADDR[:3])
    assert r["collection"]["quorum"] == "3" and r["collection"]["witnessSetVersion"] == "2"
    assert outcome_view(r) == [("signed", "1"), ("signed", "1"), ("signed", "1"), ("silent", "0")]          # the fourth reply had not arrived when the third signature completed it
    assert set(r["collection"]) == {"quorum", "witnessSetVersion", "outcomes", "submittedSigners"}              # an early success takes no snapshot and serializes no evidence members


def test_the_outcomes_are_one_per_index_in_order_with_the_configured_addresses():
    c = make()
    drive(c, honest())
    outs = c.result["collection"]["outcomes"]
    assert [o["witnessIndex"] for o in outs] == ["0", "1", "2", "3"] and [o["witness"] for o in outs] == ADDR


def test_a_signature_by_the_wrong_key_is_invalid_not_counted_and_collection_continues():
    wrong = Scripted(2, [(50, sig_reply(A, sign(0, A)))])                                    # witness 2 relays witness 0's valid signature
    c = make()
    drive(c, [Wit(0), Wit(1), wrong, Wit(3, reply_delay=300)])
    r = c.result
    assert r["ok"] is True and set(r["collection"]["submittedSigners"]) == {ADDR[0], ADDR[1], ADDR[3]}
    o2 = r["collection"]["outcomes"][2]
    assert o2["status"] == "invalid" and o2["replies"] == "1" and "recover" in o2["detail"] and "code" not in o2


def test_a_malformed_signature_and_garbage_replies_are_invalid_and_never_raise():
    garbage = [{"type": "signature", "message": A, "signature": "0x12"}, {"type": "signature", "message": A, "signature": 7}, {"type": "signature", "message": "x", "signature": "0x"},
               {"type": "error"}, {"type": "error", "code": 7}, {"type": "nonsense"}, {"type": "malformed", "detail": "not json"}, None, "junk", 12, [], {},
               {"type": "error", "code": "EXPIRED", "extra": 1}, {"type": "signature", "message": A, "signature": sign(2, A), "extra": 1},
               {"type": "signature", "message": {**A, "sequence": 4}, "signature": sign(2, A)}, {"type": "error", "code": "EXPIRED", "reason": 5}, {"type": "error", "code": ""}]
    for g in garbage:
        c = make()
        drive(c, [Wit(0), Wit(1), Scripted(2, [(10, g)]), Wit(3, reply_delay=300)])
        r = c.result
        assert r["ok"] is True, g
        o = r["collection"]["outcomes"][2]
        assert o["status"] == "invalid" and o["replies"] == "1" and o["detail"], g


def test_a_signature_over_another_message_is_a_dissent_kept_as_evidence_and_never_counted():
    other = Scripted(1, [(50, sig_reply(B, sign(1, B)))])
    c = make()
    drive(c, [Wit(0), other, Wit(2), Wit(3, reply_delay=300)])
    r = c.result
    assert r["ok"] is True and set(r["collection"]["submittedSigners"]) == {ADDR[0], ADDR[2], ADDR[3]}
    assert r["collection"]["outcomes"][1]["status"] == "dissent" and r["collection"]["outcomes"][1]["replies"] == "1"
    assert "differs from the one asked" in r["collection"]["outcomes"][1]["detail"]


def test_a_repeated_reply_counts_in_replies_but_never_adds_a_signer():
    dup = Scripted(0, [(50, sig_reply(A, sign(0, A))), (60, sig_reply(A, sign(0, A))), (70, sig_reply(A, sign(0, A)))])
    c = make()
    drive(c, [dup, Wit(1, reply_delay=500), Wit(2, reply_delay=600), Wit(3, reply_delay=9000)])
    r = c.result
    assert r["ok"] is True and len(r["signatures"]) == 3 and set(r["collection"]["submittedSigners"]) == set(ADDR[:3])
    assert r["collection"]["outcomes"][0]["replies"] == "3" and r["collection"]["outcomes"][0]["status"] == "signed"


def test_two_silent_witnesses_end_the_collection_at_the_deadline_with_nothing_submitted():
    c = make()
    drive(c, [Wit(0), Wit(1), Wit(2, muted=True), Wit(3, muted=True)])
    r = c.result
    assert c.done and r["ok"] is False and r["collection"]["submittedSigners"] == [] and "signatures" not in r
    assert outcome_view(r) == [("signed", "1"), ("signed", "1"), ("silent", "0"), ("silent", "0")]
    assert set(r["collection"]) == {"quorum", "witnessSetVersion", "outcomes", "submittedSigners"}
    assert r["failure"] and c.finished_at_ms == 10000                                          # the 10 s cap is the deadline; nothing is extended


def test_a_refusal_carries_its_code_and_reason_when_it_has_one():
    expired = {"type": "error", "code": "EXPIRED", "reason": None, "recorded": None}
    stale = {"type": "error", "code": "STALE_STATE", "reason": "WITNESS_SET_MISMATCH", "recorded": None}
    c = make()
    drive(c, [Wit(0), Wit(1), Scripted(2, [(10, expired)]), Scripted(3, [(10, stale)])])
    o = c.result["collection"]["outcomes"]
    assert (o[2]["status"], o[2]["code"], "reason" in o[2]) == ("refused", "EXPIRED", False)
    assert (o[3]["status"], o[3]["code"], o[3]["reason"]) == ("refused", "STALE_STATE", "WITNESS_SET_MISMATCH")


def test_a_recorded_value_outside_a_checkpoint_pinned_refusal_is_invalid():
    for reply in ({"type": "error", "code": "EXPIRED", "reason": None, "recorded": {"message": A, "signature": sign(2, A)}},
                  {"type": "error", "code": "EXPIRED", "reason": "CONFLICT_PINNED", "recorded": {"message": A, "signature": sign(2, A)}},
                  {"type": "error", "code": "STALE_STATE", "reason": "WITNESS_SET_MISMATCH", "recorded": {"message": A, "signature": sign(2, A)}}):
        c = make()
        drive(c, [Wit(0), Wit(1), Scripted(2, [(10, reply)]), Wit(3, reply_delay=300)])
        assert c.result["collection"]["outcomes"][2]["status"] == "invalid"
    c = make(adoption=False)                                                                 # decisions, receipts and governance never carry `recorded`
    drive(c, [Wit(0), Wit(1), Scripted(2, [(10, pinned(A, sign(2, A)))]), Wit(3, reply_delay=300)])
    assert c.result["collection"]["outcomes"][2]["status"] == "invalid"


def test_a_recorded_report_that_does_not_recover_to_the_replying_witness_is_invalid():
    for bad in (pinned(B, sign(0, B)), pinned(B, "0x" + "00" * 65), pinned(cp(seq="9", block="400", fill="8"), sign(2, cp(seq="9", block="400", fill="8")))):
        c = make()
        drive(c, [Wit(0), Wit(1), Scripted(2, [(10, bad)]), Wit(3, reply_delay=300)])
        assert c.result["collection"]["outcomes"][2]["status"] == "invalid", bad


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the decision snapshot, adoption and the second round
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def pinned_wits(values, **kw):
    ws = honest(**kw)
    for w, m in values.items():
        ws[w].preload(m)
    return ws


def test_an_ambiguous_split_adopts_nothing_and_ends_when_all_four_have_replied():
    c = make(proposal=C)
    ws = pinned_wits({0: A, 1: A, 2: B, 3: B})
    log = drive(c, ws)
    r = c.result
    assert r["ok"] is False and "adopted" not in r["collection"] and len(r["collection"]["recordedReports"]) == 4
    assert r["collection"]["timing"]["snapshotClosedBy"] == "all-replied" and r["collection"]["timing"]["snapshotClosedAtMs"] == "100"
    assert all(s == "refused" for s, _ in outcome_view(r)) and c.finished_at_ms == 100
    assert [a["op"] for _, a in log] == ["send"] * 4                                         # nothing else was ever sent


def test_a_prefix_adopts_and_the_value_is_reproposed_verbatim_with_its_recorded_expiry():
    a_short = cp(block="250", fill="5", expires=T0 + 25)
    c = make(proposal=C)
    ws = pinned_wits({0: a_short, 1: a_short}, reply_delay=100)
    ws[2].deliver_delay = ws[3].deliver_delay = {1: 20000, 2: 0}                              # the round-1 writes to witnesses 2 and 3 are held: the snapshot closes at the 5 s reply timeout
    log = drive(c, ws)
    r = c.result
    assert r["ok"] is True and r["message"] == a_short                                       # the certificate is over the ADOPTED value, not the retained proposal
    assert r["collection"]["adopted"] == {"message": a_short, "reporters": ["0", "1"], "reproposal": "sent"}
    assert r["collection"]["timing"] == {"ledgerNowAtStart": str(T0), "proposalExpiresAt": str(T0 + 30), "collectionDeadlineMs": "10000", "snapshotClosedAtMs": "5000", "snapshotClosedBy": "reply-timeout"}
    round2 = [a for _, a in log if a["op"] == "send" and a["round"] == 2]
    assert len(round2) == 4 and all(canon(a["message"]) == canon(a_short) for a in round2)    # verbatim, to every witness, with its recorded expiresAt
    assert [a["witness"] for _, a in log if a["op"] == "cancel"] == [2, 3]                  # the undelivered round-1 sends of the silent witnesses are cancelled
    addrs = [eip712.recover(messages.digest_of("StateCheckpoint", a_short, messages.domain_for("StateCheckpoint", a_short, DEPLOY)), s) for s in r["signatures"]]
    assert addrs == sorted(addrs) and len(set(addrs)) == 3 and r["collection"]["submittedSigners"] == addrs


def test_a_late_split_does_not_cancel_the_adoption_and_only_two_signatures_exist():
    c = make(proposal=C)
    ws = pinned_wits({0: A, 1: A, 2: B, 3: B})
    ws[2].reply_delay = ws[3].reply_delay = 6000                                              # their round-1 reports arrive after the snapshot closed
    drive(c, ws)
    r = c.result
    assert r["ok"] is False and r["collection"]["adopted"]["message"] == A and r["collection"]["adopted"]["reproposal"] == "sent"
    assert [x["witnessIndex"] for x in r["collection"]["recordedReports"]] == ["0", "1"]
    assert {(x["witnessIndex"], canon(x["message"])) for x in r["collection"]["lateReports"]} == {("2", canon(B)), ("3", canon(B))}
    assert outcome_view(r)[:2] == [("signed", "2"), ("signed", "2")] and [o["status"] for o in r["collection"]["outcomes"][2:]] == ["refused", "refused"]
    assert r["collection"]["submittedSigners"] == []


def test_the_reversed_arrival_order_adopts_the_other_value():
    c = make(proposal=C)
    ws = pinned_wits({0: A, 1: A, 2: B, 3: B})
    ws[0].reply_delay = ws[1].reply_delay = 6000
    drive(c, ws)
    r = c.result
    assert r["collection"]["adopted"]["message"] == B and r["collection"]["adopted"]["reporters"] == ["2", "3"] and r["ok"] is False
    assert {x["witnessIndex"] for x in r["collection"]["lateReports"]} == {"0", "1"}


def test_an_equivocator_is_excluded_marked_invalid_and_its_values_are_kept_as_evidence():
    byz = Scripted(3, [(50, pinned(A, sign(3, A))), (60, pinned(B, sign(3, B)))])
    c = make(proposal=C)
    ws = [Wit(0), Wit(1, muted=True), Wit(2, muted=True), byz]
    ws[0].preload(A)
    drive(c, ws)
    r = c.result
    col = r["collection"]
    assert r["ok"] is False and "adopted" not in col and [x["witnessIndex"] for x in col["recordedReports"]] == ["0"]
    assert [e["witnessIndex"] for e in col["inconsistentReports"]] == ["3"] and len(col["inconsistentReports"][0]["reports"]) == 2
    o3 = col["outcomes"][3]
    assert o3["status"] == "invalid" and o3["replies"] == "2" and "two different recorded values" in o3["detail"]
    assert c.finished_at_ms == 10000                                                          # two witnesses stayed silent: it runs to the deadline


def test_the_effort_gate_skips_the_reproposal_when_two_seconds_of_validity_are_not_left():
    a6 = cp(block="250", fill="5", expires=T0 + 6)
    c = make(proposal=C)
    ws = pinned_wits({0: a6, 1: a6})
    ws[2].muted = ws[3].muted = True
    log = drive(c, ws)
    col = c.result["collection"]
    assert col["adopted"] == {"message": a6, "reporters": ["0", "1"], "reproposal": "skipped_validity"}                 # selected, never re-proposed
    assert not [a for _, a in log if a["op"] == "send" and a["round"] == 2]
    assert c.result["ok"] is False and col["timing"]["snapshotClosedBy"] == "reply-timeout"
    assert [s for s, _ in outcome_view(c.result)] == ["refused", "refused", "silent", "silent"]
    assert "validity" in c.result["failure"]


def test_the_original_deadline_is_a_hard_stop_and_no_second_round_runs():
    c = make(proposal=C, prop=T0 + 4)                                                           # remaining 4 s: the deadline is 2 s, before the 5 s reply timeout
    ws = pinned_wits({0: A, 1: A})
    ws[2].muted = ws[3].muted = True
    ws[2].reply_delay = ws[3].reply_delay = 100
    log = drive(c, ws)
    col = c.result["collection"]
    assert col["timing"] == {"ledgerNowAtStart": str(T0), "proposalExpiresAt": str(T0 + 4), "collectionDeadlineMs": "2000", "snapshotClosedAtMs": "2000", "snapshotClosedBy": "deadline"}
    assert col["adopted"]["reproposal"] == "skipped_deadline" and "lateReports" not in col and c.finished_at_ms == 2000
    assert not [a for _, a in log if a["op"] == "send" and a["round"] == 2]
    assert "deadline" in c.result["failure"]


def test_nothing_arriving_at_or_after_the_deadline_is_collected():
    c = make(proposal=C, prop=T0 + 4)
    ws = pinned_wits({0: A, 1: A})
    ws[2].muted = ws[3].muted = True
    c.start()
    c.on_reply(100, 0, pinned(A, sign(0, A)))
    c.on_reply(200, 1, pinned(A, sign(1, A)))
    assert not c.done
    c.on_reply(2000, 2, sig_reply(C, sign(2, C)))                                             # exactly at the deadline: ignored
    assert c.done and c.result["collection"]["outcomes"][2] == {"witnessIndex": "2", "witness": ADDR[2], "status": "silent", "replies": "0"}
    assert c.on_reply(2500, 3, sig_reply(C, sign(3, C))) == []                                # and a finished collection ignores everything


def test_a_reply_exactly_at_the_reply_timeout_is_late_because_timers_fire_first():
    c = make(proposal=C)
    c.start()
    c.on_reply(100, 0, pinned(A, sign(0, A)))
    c.on_reply(200, 1, pinned(A, sign(1, A)))
    c.on_reply(5000, 2, pinned(B, sign(2, B)))
    col = c.current_evidence()
    assert [x["witnessIndex"] for x in col["recordedReports"]] == ["0", "1"] and [x["witnessIndex"] for x in col["lateReports"]] == ["2"]


def test_all_replied_closes_the_snapshot_strictly_before_the_limit_only():
    c = make(proposal=C)
    c.start()
    for w, t in ((0, 100), (1, 200), (2, 300), (3, 4999)):
        c.on_reply(t, w, pinned(A if w < 2 else B, sign(w, A if w < 2 else B)))
    assert c.current_evidence()["timing"]["snapshotClosedBy"] == "all-replied"
    c2 = make(proposal=C)
    c2.start()
    for w, t in ((0, 100), (1, 200), (2, 300)):
        c2.on_reply(t, w, pinned(A if w < 2 else B, sign(w, A if w < 2 else B)))
    c2.on_reply(5000, 3, pinned(B, sign(3, B)))                                               # the fourth reply is at the limit: not "before", so the timeout closes it
    assert c2.current_evidence()["timing"]["snapshotClosedBy"] == "reply-timeout"


def test_replies_must_not_go_back_in_time():
    c = make()
    c.start()
    c.on_reply(500, 0, sig_reply(A, sign(0, A)))
    with pytest.raises(wp.CollectionError):
        c.on_reply(400, 1, sig_reply(A, sign(1, A)))
    with pytest.raises(wp.CollectionError):
        c.on_time(100)


def test_an_unknown_witness_index_is_a_caller_bug_and_raises():
    c = make()
    c.start()
    for bad in (4, -1, True, "0", None):
        with pytest.raises(wp.CollectionError):
            c.on_reply(10, bad, sig_reply(A, sign(0, A)))


def test_a_bad_round_number_is_a_caller_bug():
    c = make()
    c.start()
    for bad in (0, 3, True, None, "1", 1.0):
        with pytest.raises(wp.CollectionError):
            c.on_reply(10, 0, sig_reply(A, sign(0, A)), bad)
    with pytest.raises(wp.CollectionError):
        c.on_reply(10, 0, sig_reply(A, sign(0, A)), 2)                                        # no second round was started


def test_the_collection_must_be_started_before_time_or_replies_arrive():
    c = make()
    with pytest.raises(wp.CollectionError):
        c.on_time(5)
    with pytest.raises(wp.CollectionError):
        c.on_reply(5, 0, sig_reply(A, sign(0, A)))
    assert c.next_timer_ms() is None
    c.start()
    assert c.next_timer_ms() == 5000


@pytest.mark.parametrize("bad", [dict(witnesses=ADDR[:3]), dict(witnesses=[ADDR[0]] * 4), dict(witnesses=[a.upper() for a in ADDR]), dict(recover=None), dict(proposal="x"),
                                 dict(proposal={"sequence": 4}), dict(adoption=1), dict(witness_set_version=2), dict(witness_set_version="02"), dict(proposal={"tag": "x"})])
def test_constructor_inputs_are_validated(bad):
    kw = dict(witnesses=ADDR, recover=RECOVER, proposal=A, ledger_now_at_start=T0, proposal_expires_at=T0 + 30, adoption=True, witness_set_version="2")
    kw.update(bad)
    with pytest.raises(wp.CollectionError):
        wp.Collection(**kw)


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the two pre-registered recovery schedules (SIGNING-RULES section 8)
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_schedule_a_held_writes_are_cancelled_and_the_adopted_value_completes_the_collection():
    """Witnesses 0 and 1 hold A (stored signatures); 2 and 3 are unpinned. A restarted pool proposes B but its writes to 2 and 3 are held until the snapshot closes."""
    c = make(proposal=B)
    ws = pinned_wits({0: A, 1: A})
    ws[2].deliver_delay = ws[3].deliver_delay = {1: 20000, 2: 0}                              # round 1 held far beyond the snapshot; round 2 delivered at once
    log = drive(c, ws)
    r = c.result
    assert r["ok"] is True and r["message"] == A and r["collection"]["adopted"]["reproposal"] == "sent"
    assert ws[2].deliveries == [(2, canon(A))] and ws[3].deliveries == [(2, canon(A))]       # B was never delivered to witnesses 2 and 3
    assert [a["witness"] for _, a in log if a["op"] == "cancel"] == [2, 3]
    assert len(r["signatures"]) == 3 and set(r["collection"]["submittedSigners"]) <= set(ADDR)


def test_schedule_b_pinned_availability_nothing_is_submitted_and_no_value_reaches_three():
    c = make(proposal=B)
    ws = pinned_wits({0: A, 1: A})
    drive(c, ws)
    r = c.result
    assert r["ok"] is False and r["collection"]["submittedSigners"] == [] and "signatures" not in r
    assert r["collection"]["adopted"]["message"] == A and r["collection"]["adopted"]["reproposal"] == "sent"
    assert [o["status"] for o in r["collection"]["outcomes"]] == ["signed", "signed", "refused", "refused"]          # judged against M* = A: 2 and 3 signed B but were refused A
    assert sum(o["status"] == "signed" for o in r["collection"]["outcomes"]) < 3
    assert {(x["witnessIndex"], canon(x["message"])) for x in r["collection"]["lateReports"]} == {("2", canon(B)), ("3", canon(B))}
    assert c.finished_at_ms == 200                                                            # all four replied in round 1 (100 ms) and again in round 2 (200 ms): nothing can change


def test_the_second_round_has_its_own_five_second_timeout_inside_the_original_deadline():
    c = make(proposal=C)
    ws = pinned_wits({0: A, 1: A})
    ws[2] = Wit(2)
    ws[3] = Scripted(3, {1: [(100, sig_reply(C, sign(3, C)))], 2: []})                        # witness 3 answers round 1 and then goes silent
    drive(c, ws)
    r = c.result
    assert r["collection"]["timing"]["snapshotClosedBy"] == "all-replied" and r["collection"]["timing"]["snapshotClosedAtMs"] == "100"
    assert r["collection"]["adopted"]["reproposal"] == "sent" and r["ok"] is False
    assert c.finished_at_ms == 5100                                                           # 100 ms close + 5 s round-2 timeout; not the 10 s deadline


def test_a_refusal_status_reports_the_latest_error_of_the_witness():
    first = {"type": "error", "code": "EXPIRED", "reason": None, "recorded": None}
    later = {"type": "error", "code": "STALE_STATE", "reason": "WITNESS_SET_MISMATCH", "recorded": None}
    c = make()
    drive(c, [Wit(0), Wit(1), Scripted(2, [(10, first), (20, later)]), Scripted(3, [(10, first)])])
    o = c.result["collection"]["outcomes"][2]
    assert (o["status"], o["code"], o["reason"], o["replies"]) == ("refused", "STALE_STATE", "WITNESS_SET_MISMATCH", "2")


def test_the_certificate_is_sorted_by_address_whatever_the_arrival_order():
    import itertools
    for order in itertools.permutations(range(4)):
        c = make()
        drive(c, [Wit(w, reply_delay=100 * (order.index(w) + 1)) for w in range(4)])
        r = c.result
        d = messages.digest_of("StateCheckpoint", A, messages.domain_for("StateCheckpoint", A, DEPLOY))
        addrs = [eip712.recover(d, sg) for sg in r["signatures"]]
        assert r["ok"] and addrs == sorted(addrs) and set(addrs) == {ADDR[w] for w in order[:3]} and r["collection"]["submittedSigners"] == addrs


def test_an_early_success_does_not_serialize_the_reports_seen_before_it():
    c = make(proposal=C)
    ws = [Wit(0, reply_delay=100), Wit(1, reply_delay=200), Wit(2, reply_delay=300), Wit(3, reply_delay=50)]
    ws[3].preload(A)                                                                           # witness 3 refuses CONFLICT_PINNED first, with a recorded value
    drive(c, ws)
    r = c.result
    assert r["ok"] is True and r["message"] == C and set(r["collection"]) == {"quorum", "witnessSetVersion", "outcomes", "submittedSigners"}
    assert r["collection"]["outcomes"][3]["status"] == "refused"


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# properties over many schedules
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def byz_menu(b):
    """What one Byzantine witness (index b) may send in either round: silence, valid signatures or recorded reports over A, B or C, garbage, a signature by another witness's key."""
    return {"silent": [],
            "sigA": [(40, sig_reply(A, sign(b, A)))], "sigB": [(40, sig_reply(B, sign(b, B)))], "sigC": [(40, sig_reply(C, sign(b, C)))],
            "pinA": [(40, pinned(A, sign(b, A)))], "pinB": [(40, pinned(B, sign(b, B)))], "pinC": [(40, pinned(C, sign(b, C)))],
            "garbage": [(40, {"type": "malformed", "detail": "x"})], "wrongkey": [(40, sig_reply(C, sign((b + 1) % 4, C)))]}


def test_with_one_byzantine_witness_any_certificate_is_over_a_value_an_honest_witness_recorded():
    """Exhaustive over every position of one Byzantine witness, its nine behaviours (the menu above, silence included), and three honest witnesses with every pin pattern (none, A, B), with C as the
    retained proposal. A produced certificate must have exactly three distinct sorted signers, every signature must verify, and the message must be one that an honest witness recorded; a failure
    submits nothing. (A model of honest witnesses, not the store; the cryptography is real.)"""
    import itertools
    checked = certs = 0
    for byz in range(4):
        honest_ix = [i for i in range(4) if i != byz]
        for pins in itertools.product([None, A, B], repeat=3):
            for name, replies in byz_menu(byz).items():
                ws = [None] * 4
                for i, pin in zip(honest_ix, pins):
                    ws[i] = Wit(i)
                    if pin is not None:
                        ws[i].preload(pin)
                ws[byz] = Scripted(byz, replies)
                c = make(proposal=C)
                drive(c, ws)
                checked += 1
                assert c.done, (byz, pins, name)
                r = c.result
                if r["ok"]:
                    certs += 1
                    m = r["message"]
                    d = messages.digest_of("StateCheckpoint", m, messages.domain_for("StateCheckpoint", m, DEPLOY))
                    addrs = [eip712.recover(d, sg) for sg in r["signatures"]]
                    assert len(addrs) == 3 and len(set(addrs)) == 3 and addrs == sorted(addrs) and set(addrs) <= set(ADDR) and r["collection"]["submittedSigners"] == addrs
                    assert canon(m) in {canon(ws[i].store[m["sequence"]][0]) for i in honest_ix if m["sequence"] in ws[i].store}, (byz, pins, name)
                else:
                    assert r["collection"]["submittedSigners"] == [] and "signatures" not in r
    assert checked == 4 * 27 * 9 and certs > 0


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the outputs through my independent wire checker (correlated: same author)
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def envelope(r):
    if r["ok"]:
        return {"schemaVersion": "v2", "ok": True, "result": {"schemaVersion": "v2", "adapterMode": "symbolic", "checkpoint": r["message"], "signatures": r["signatures"], "collection": r["collection"]}, "error": None}
    return {"schemaVersion": "v2", "ok": False, "result": None, "error": {"code": "ADAPTER_UNAVAILABLE", "reason": "QUORUM_UNAVAILABLE", "message": r["failure"], "collection": r["collection"]}}


def scenarios():
    a25 = cp(block="250", fill="5", expires=T0 + 25)
    a6 = cp(block="250", fill="5", expires=T0 + 6)
    c = make(proposal=C); ws = pinned_wits({0: A, 1: A, 2: B, 3: B}); drive(c, ws); yield "ambiguous split", c.result
    c = make(proposal=C); ws = pinned_wits({0: a25, 1: a25}); ws[2].deliver_delay = ws[3].deliver_delay = {1: 20000, 2: 0}; drive(c, ws); yield "adoption then success", c.result
    c = make(proposal=C); ws = pinned_wits({0: A, 1: A, 2: B, 3: B}); ws[2].reply_delay = ws[3].reply_delay = 6000; drive(c, ws); yield "late split", c.result
    c = make(proposal=C); ws = pinned_wits({0: A, 1: A, 2: B, 3: B}); ws[0].reply_delay = ws[1].reply_delay = 6000; drive(c, ws); yield "reversed", c.result
    c = make(proposal=C); ws = [Wit(0), Wit(1, muted=True), Wit(2, muted=True), Scripted(3, [(50, pinned(A, sign(3, A))), (60, pinned(B, sign(3, B)))])]; ws[0].preload(A); drive(c, ws); yield "equivocator", c.result
    c = make(proposal=C); ws = pinned_wits({0: a6, 1: a6}); ws[2].muted = ws[3].muted = True; drive(c, ws); yield "skipped validity", c.result
    c = make(proposal=C, prop=T0 + 4); ws = pinned_wits({0: A, 1: A}); ws[2].muted = ws[3].muted = True; drive(c, ws); yield "hard stop", c.result
    c = make(proposal=B); ws = pinned_wits({0: A, 1: A}); drive(c, ws); yield "schedule b", c.result
    c = make(proposal=B); ws = pinned_wits({0: A, 1: A}); ws[2].deliver_delay = ws[3].deliver_delay = {1: 20000, 2: 0}; drive(c, ws); yield "schedule a", c.result
    c = make(); drive(c, [Wit(0), Wit(1), Wit(2, muted=True), Wit(3, muted=True)]); yield "two silent", c.result
    c = make(); drive(c, [Wit(0), Wit(1), Scripted(2, [(50, sig_reply(A, sign(0, A)))]), Wit(3, reply_delay=300)]); yield "invalid then success", c.result


def run_wire_checker(extra_examples):
    text = open(os.path.join(ROOT, "protocol", "f0", "SUCCESSOR-WIRE.md"), encoding="utf-8").read()
    text += "\n" + "".join("\n```json\n" + json.dumps(e) + "\n```\n" for e in extra_examples)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "SUCCESSOR-WIRE.md")
        open(p, "w", encoding="utf-8").write(text)
        r = subprocess.run([sys.executable, "-B", "-I", os.path.join(V, "check_wire_examples.py"), p], capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout


def test_every_collection_result_passes_my_wire_checker_and_a_tampered_one_does_not():
    named = list(scenarios())
    exs = [envelope(r) for _, r in named]
    rc0, out0 = run_wire_checker([])
    assert rc0 == 0
    rc, out = run_wire_checker(exs)
    assert rc == 0, "\n".join(l for l in out.splitlines() if l.startswith("FAIL"))
    assert out.count("ok   ") >= out0.count("ok   ") + 3 * len(exs)
    ok_ex = next(envelope(r) for n, r in named if n == "adoption then success")
    assert ok_ex["ok"] is True and run_wire_checker([ok_ex])[0] == 0
    for tamper in (lambda c: c["outcomes"][0].update(status="refused"),
                   lambda c: c.update(submittedSigners=c["submittedSigners"][:2]),
                   lambda c: c["timing"].update(snapshotClosedAtMs="4999"),
                   lambda c: c["adopted"].update(reproposal="skipped_deadline")):
        e = copy.deepcopy(ok_ex)
        tamper(e["result"]["collection"])
        assert run_wire_checker([e])[0] != 0
