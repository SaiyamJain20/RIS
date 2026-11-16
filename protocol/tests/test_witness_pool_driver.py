"""Pool driver and TEST-ONLY virtual transport (agent 2, F task 3 slice 3c). Tests written for `hmbc_protocol/witness_pool_driver.py` and `testtools/virtual_transport.py`.

PROCESS NOTE, stated plainly: I wrote the 25-line driver and the transport BEFORE these tests (a repeat of my slice-4a slip); the red run on file was made by moving the driver aside, and the mutation run is the
real evidence. What the tests establish: the driver gives the sans-IO `Collection` its world correctly; and, more than the earlier pool tests, a REAL END-TO-END collection in process: four real `WitnessService`s
(real durable stores, real EIP-712 signatures with synthetic keys) behind the virtual transport, driven by the real pool state machine, against one injected fake ledger view. The two pre-registered recovery
schedules of SIGNING-RULES section 8 are run with the real witnesses: (a) the pool's held writes are cancelled and the adopted value completes the collection, and the held witnesses NEVER receive the second value;
(b) pinned availability, nothing submitted. NOT established: any real transport, clock, process or ledger; the witnesses share one fake view of one fake ledger.
"""
import ast
import json
import os

import pytest

from eth_account import Account

from hmbc_protocol import eip712, keys, messages
from hmbc_protocol import witness_pool as wp
from hmbc_protocol import witness_pool_driver as drv
from hmbc_protocol import witness_service as svc
from hmbc_protocol import witness_state as ws
from testtools.virtual_transport import ServiceEndpoint, VirtualTransport

from test_witness_service import B, BIND, DEPLOY, FakeView

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
KEYS = [keys.synthetic_private_key("witness-%d" % i) for i in range(1, 5)]
ADDRS = [Account.from_key(k).address.lower() for k in KEYS]
T0 = 1000
RECOVER = wp.make_recover("StateCheckpoint", DEPLOY)


def canon(m):
    return json.dumps(m, sort_keys=True)


class PoolView(FakeView):
    def now(self, chain):
        return self.dbc_ts


def make_witnesses(tmp_path, view, n=4):
    out = []
    for i in range(n):
        st = ws.init_store(str(tmp_path / ("w%d" % i)), BIND, B, "witness:" + ADDRS[i])
        out.append(svc.WitnessService(store=st, key=KEYS[i], view=view, deployment=DEPLOY, witness_set_version="2"))
    return out


def collection(view, proposal):
    return wp.Collection(witnesses=ADDRS, recover=RECOVER, proposal=proposal, ledger_now_at_start=view.now("dbc"), proposal_expires_at=int(proposal["expiresAt"]), adoption=True, witness_set_version="2")


def verify(m, sig):
    return eip712.recover(messages.digest_of("StateCheckpoint", m, messages.domain_for("StateCheckpoint", m, DEPLOY)), sig)


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the virtual transport's own contract
# --------------------------------------------------------------------------------------------------------------------------------------------------------
class Scripted:
    def __init__(self, replies=(), hold=0):
        self.replies, self.hold, self.got = list(replies), hold, []

    def send_delay(self, r):
        return self.hold

    def deliver(self, r, m):
        self.got.append((r, m))
        return list(self.replies)


def test_a_delivery_happens_before_a_reply_at_the_same_millisecond_and_a_reply_at_the_deadline_waits():
    a = Scripted([(100, {"type": "x"})])
    t = VirtualTransport([a])
    t.send(0, 1, {"m": 1})
    assert t.next_event(100) is None and t.now_ms() == 100 and a.got == [(1, {"m": 1})]                 # delivered at 0; its reply is due exactly at the deadline: the timer wins
    assert t.next_event(200) == (100, 0, 1, {"type": "x"})                                               # and the reply is returned by the next call, at its own time


def test_a_cancelled_write_is_never_delivered_and_a_delivered_one_cannot_be_cancelled():
    held, quick = Scripted(hold=5000), Scripted([(10, {"type": "y"})])
    t = VirtualTransport([held, quick])
    t.send(0, 1, {"a": 1})
    t.send(1, 1, {"b": 1})
    assert t.next_event(50) == (10, 1, 1, {"type": "y"})
    t.cancel(0, 1)
    t.cancel(1, 1)                                                                                          # already delivered: nothing to drop
    assert t.next_event(10 ** 6) is None and held.got == [] and quick.got == [(1, {"b": 1})]


def test_time_never_goes_backwards_and_an_empty_queue_advances_to_the_deadline():
    t = VirtualTransport([Scripted()])
    assert t.next_event(700) is None and t.now_ms() == 700
    assert t.next_event(300) is None and t.now_ms() == 700


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the driver
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_four_real_witnesses_complete_a_collection_with_three_verifying_signatures(tmp_path):
    view = PoolView()
    ws_ = make_witnesses(tmp_path, view)
    proposal = svc.derive_checkpoint(view, DEPLOY)
    tr = VirtualTransport([ServiceEndpoint(w.sign_checkpoint, reply_delay=100 * (4 - i)) for i, w in enumerate(ws_)])          # witness 3 answers first, witness 0 last
    r = drv.run_collection(collection(view, proposal), tr)
    assert r["ok"] is True and r["message"] == proposal and len(r["signatures"]) == 3
    assert {verify(proposal, s) for s in r["signatures"]} == set(ADDRS[1:])                             # the three fastest; the slowest reply had not arrived
    assert r["collection"]["submittedSigners"] == sorted(ADDRS[1:]) and [x for _, x, rd in tr.delivered if rd == 1] == [0, 1, 2, 3]


def test_two_silent_real_witnesses_end_the_collection_at_the_deadline_with_nothing_submitted(tmp_path):
    view = PoolView()
    ws_ = make_witnesses(tmp_path, view)
    proposal = svc.derive_checkpoint(view, DEPLOY)
    tr = VirtualTransport([ServiceEndpoint(ws_[0].sign_checkpoint), ServiceEndpoint(ws_[1].sign_checkpoint), ServiceEndpoint(ws_[2].sign_checkpoint, muted=True), ServiceEndpoint(ws_[3].sign_checkpoint, muted=True)])
    coll = collection(view, proposal)
    r = drv.run_collection(coll, tr)
    assert r["ok"] is False and r["collection"]["submittedSigners"] == [] and coll.finished_at_ms == 10000


def preload(ws_, view, indices):
    """Witnesses `indices` signed the checkpoint of the CURRENT view in an earlier collection; then the PBC mines a block, so the pool's next proposal is a second valid value for the same sequence."""
    first = svc.derive_checkpoint(view, DEPLOY)
    for i in indices:
        ws_[i].sign_checkpoint(first)
    view.pbc_head += 1
    return first


def test_schedule_a_with_real_witnesses_held_writes_are_cancelled_and_the_adopted_value_completes(tmp_path):
    view = PoolView()
    ws_ = make_witnesses(tmp_path, view)
    first = preload(ws_, view, (0, 1))
    second = svc.derive_checkpoint(view, DEPLOY)
    assert second["sequence"] == first["sequence"] and second["sourceBlockHash"] != first["sourceBlockHash"]
    eps = [ServiceEndpoint(w.sign_checkpoint) for w in ws_]
    eps[2].deliver_delay = eps[3].deliver_delay = {1: 20000, 2: 0}                                          # the pool's first writes to witnesses 2 and 3 are held
    tr = VirtualTransport(eps)
    r = drv.run_collection(collection(view, second), tr)
    assert r["ok"] is True and r["message"] == first and r["collection"]["adopted"]["reproposal"] == "sent"
    assert [(rd, canon(m)) for rd, m in eps[2].deliveries] == [(2, canon(first))] and [(rd, canon(m)) for rd, m in eps[3].deliveries] == [(2, canon(first))]      # the second value never reached them
    assert [c[1] for c in tr.cancelled] == [2, 3] and {verify(first, s) for s in r["signatures"]} <= set(ADDRS) and len(r["signatures"]) == 3
    ev = ws_[2]._store.evidence()
    assert [c["effect"]["sourceBlockNumber"] for c in ev["conflicts"]] == [first["sourceBlockNumber"]]       # witness 2's own durable record holds only the adopted value


def test_schedule_b_with_real_witnesses_pinned_availability_nothing_is_submitted(tmp_path):
    view = PoolView()
    ws_ = make_witnesses(tmp_path, view)
    first = preload(ws_, view, (0, 1))
    second = svc.derive_checkpoint(view, DEPLOY)
    eps = [ServiceEndpoint(w.sign_checkpoint) for w in ws_]
    r = drv.run_collection(collection(view, second), VirtualTransport(eps))
    assert r["ok"] is False and r["collection"]["submittedSigners"] == [] and "signatures" not in r
    assert r["collection"]["adopted"]["message"] == first and [o["status"] for o in r["collection"]["outcomes"]] == ["signed", "signed", "refused", "refused"]
    assert {x["witnessIndex"] for x in r["collection"]["lateReports"]} == {"2", "3"}
    for i in (2, 3):
        assert [c["effect"]["sourceBlockNumber"] for c in ws_[i]._store.evidence()["conflicts"]] == [second["sourceBlockNumber"]]       # they signed the second value in round 1: pinned to it


def test_a_late_split_with_real_witnesses_keeps_the_late_reports_of_writes_the_pool_cancelled(tmp_path):
    """Witnesses 2 and 3 hold a different recorded value B and answer after the snapshot closed. The pool cancels their (already delivered) first writes at the close: that must not swallow the reply in flight."""
    view = PoolView()
    ws_ = make_witnesses(tmp_path, view)
    a = svc.derive_checkpoint(view, DEPLOY)
    for i in (0, 1):
        ws_[i].sign_checkpoint(a)
    view.pbc_head += 1
    b = svc.derive_checkpoint(view, DEPLOY)
    for i in (2, 3):
        ws_[i].sign_checkpoint(b)
    view.pbc_head += 1
    proposal = svc.derive_checkpoint(view, DEPLOY)                                                          # a third value for the same sequence: nobody can sign it
    eps = [ServiceEndpoint(w.sign_checkpoint) for w in ws_]
    eps[2].reply_delay = eps[3].reply_delay = {1: 6000, 2: 20000}
    r = drv.run_collection(collection(view, proposal), VirtualTransport(eps))
    col = r["collection"]
    assert r["ok"] is False and col["adopted"]["message"] == a and {x["witnessIndex"] for x in col["lateReports"]} == {"2", "3"}
    assert all(x["message"] == b for x in col["lateReports"])


def test_the_driver_runs_one_collection_and_returns_its_result_object(tmp_path):
    view = PoolView()
    ws_ = make_witnesses(tmp_path, view)
    proposal = svc.derive_checkpoint(view, DEPLOY)
    coll = collection(view, proposal)
    assert drv.run_collection(coll, VirtualTransport([ServiceEndpoint(w.sign_checkpoint) for w in ws_])) is coll.result and coll.done


def test_a_transport_that_goes_back_in_time_is_a_caller_bug_the_collection_refuses(tmp_path):
    view = PoolView()
    proposal = svc.derive_checkpoint(view, DEPLOY)

    class Backwards:
        n = 0

        def send(self, *a):
            pass

        def cancel(self, *a):
            pass

        def next_event(self, deadline):
            Backwards.n += 1
            return (500 if Backwards.n == 1 else 100), 0, 1, {"type": "malformed", "detail": "x"}
    with pytest.raises(wp.CollectionError):
        drv.run_collection(collection(view, proposal), Backwards())


def test_a_collection_that_never_advances_is_a_driver_error():
    class Stuck:
        done = False

        def start(self):
            return []

        def next_timer_ms(self):
            return 5

        def on_time(self, t):
            return []

    class Idle:
        def next_event(self, d):
            return None
    with pytest.raises(drv.DriverError):
        drv.run_collection(Stuck(), Idle())


def test_the_driver_reads_no_clock_no_thread_and_no_socket():
    src = open(os.path.join(ROOT, "protocol", "hmbc_protocol", "witness_pool_driver.py")).read()
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            mods.add((node.module or "").split(".")[0])
    assert not mods & {"time", "datetime", "random", "socket", "threading", "subprocess", "asyncio", "select"}, mods
