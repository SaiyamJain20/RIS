"""The production process transport for the witness pool (agent 2, F task 3, Step 2). Written BEFORE hmbc_protocol/witness_process_transport.py existed.

`WitnessSupervisor` starts four `witness_main` processes once, and `transport_factory(kind)` hands the pool driver a fresh per-collection transport with the driver's contract:
  send(witness, round, message), cancel(witness, round), next_event(deadline_ms) -> (t_ms, witness, round, reply) | None,
where t_ms is host-monotonic milliseconds since the first send, a reply exactly AT the deadline is NOT returned (the timer wins, as the collection's rule says), and what a witness really sent is parsed
strictly HERE (`{"type": "malformed", "detail"}` for a reply that is not a well-formed envelope). No chain is involved in this file: the children are a scripted stub (stub_witness_child.py) that speaks
hmbc-witness-rpc/v1 well or badly; the live file (test_witness_process_transport_live.py) uses four real witness_main processes.

Decisions these tests pin (each one is a choice where the driver doc is silent, recorded in the module docstring):
  * a duplicate reply for an already-answered request id IS delivered again (the collection's `replies` count and its first-valid-wins rule are what make a duplicate harmless; dropping it would hide evidence);
  * a reply whose id was issued earlier but not by THIS transport (a late reply of an earlier collection) is dropped; an id never issued, or issued to another witness, is a malformed reply;
  * cancel drops a write only if not one byte of it has reached the pipe (cutting a line in half would corrupt the child's next request); a reply to an already delivered write is still delivered;
  * a child that dies or never starts is silent, never an exception; there is no respawn inside one run; a stopped child is alive but silent.
"""
import json
import os
import select
import signal
import sys
import time

import pytest

from hmbc_protocol import witness_process_transport as wpt

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.abspath(os.path.join(HERE, ".."))
STUB = os.path.join(HERE, "stub_witness_child.py")
F2 = os.path.join(HERE, "fixtures", "agent1-85c59f5-f-base-deployment.json")
SIG = "0x" + "11" * 65


class Hung(BaseException):
    """Not an Exception and not an OSError: the code under test legitimately catches OSError (a dead pipe), and a watchdog that raised TimeoutError would be swallowed by the very loop it must interrupt."""


@pytest.fixture(autouse=True)
def watchdog():
    """A hang in the code under test must be a failure, not a stuck run."""
    def boom(*_):
        raise Hung("watchdog: the test hung for 30 s")
    old = signal.signal(signal.SIGALRM, boom)
    signal.alarm(30)
    yield
    signal.alarm(0)
    signal.signal(signal.SIGALRM, old)


class FakeClock:
    def __init__(self, ns=10_000_000_000):
        self.ns = ns

    def __call__(self):
        return self.ns


def sup_with(tmp_path, modes, **kw):
    state = tmp_path / "state"
    if not state.exists():
        state.mkdir(mode=0o700)
        os.chmod(state, 0o700)
    commands = [[sys.executable, "-B", STUB, *m.split()] for m in modes]
    return wpt.WitnessSupervisor(state_dir=str(state), commands=commands, **kw)


def wait_readable(child, seconds=10):
    r, _, _ = select.select([child.stdout_fd], [], [], seconds)
    assert r, "the child never wrote anything"


def collect(tr, n, deadline_ms=8000):
    out = []
    while len(out) < n:
        ev = tr.next_event(deadline_ms)
        if ev is None:
            break
        out.append(ev)
    return out


def malformed(ev):
    assert ev is not None and ev[3]["type"] == "malformed", ev
    d = ev[3]["detail"]
    assert isinstance(d, str) and 0 < len(d) <= 200
    return d


# ---- the wire shape ---------------------------------------------------------------------------------------------------------------------------------------------

def test_a_request_is_exactly_the_documented_envelope_with_increasing_ids_and_the_collection_kind(tmp_path):
    with sup_with(tmp_path, ["reflect"] * 4) as sup:
        tr = sup.transport_factory("decision")
        for w in range(4):
            tr.send(w, 1, {"requestDigest": "0x" + "ab" * 32})
        for w in range(4):
            tr.send(w, 2, {"m": "second"})
        events = collect(tr, 8)
        assert len(events) == 8
        seen = {}
        for t, w, rnd, reply in events:
            req = reply["message"]
            assert set(req) == {"schemaVersion", "id", "round", "kind", "message"}
            assert req["schemaVersion"] == "hmbc-witness-rpc/v1" and req["kind"] == "decision" and req["round"] == rnd
            assert isinstance(req["id"], int) and not isinstance(req["id"], bool) and req["id"] >= 0
            seen[req["id"]] = (w, rnd)
        assert sorted(seen) == list(range(8)) and [seen[i] for i in range(4)] == [(0, 1), (1, 1), (2, 1), (3, 1)]


def test_ids_keep_increasing_across_collections_of_one_supervisor(tmp_path):
    with sup_with(tmp_path, ["reflect"] * 4) as sup:
        a = sup.transport_factory("checkpoint")
        a.send(0, 1, {"a": "1"})
        first = collect(a, 1)[0][3]["message"]["id"]
        b = sup.transport_factory("receipt")
        b.send(0, 1, {"a": "2"})
        second = collect(b, 1)[0][3]["message"]["id"]
        assert second == first + 1


def test_a_well_formed_reply_is_returned_with_integer_time_witness_round_and_the_reply_object(tmp_path):
    with sup_with(tmp_path, ["echo"] * 4) as sup:
        tr = sup.transport_factory("checkpoint")
        for w in range(4):
            tr.send(w, 1, {"sequence": "7"})
        events = collect(tr, 4)
        assert sorted(e[1] for e in events) == [0, 1, 2, 3]
        times = [e[0] for e in events]
        assert times == sorted(times) and all(isinstance(t, int) and not isinstance(t, bool) and t >= 0 for t in times)
        assert all(e[2] == 1 and e[3] == {"type": "signature", "message": {"sequence": "7"}, "signature": SIG} for e in events)


# ---- time: host-monotonic, the timer wins -----------------------------------------------------------------------------------------------------------------------

def test_a_reply_exactly_at_the_deadline_is_not_returned_the_timer_wins_and_it_is_returned_by_the_next_call(tmp_path):
    clock = FakeClock()
    with sup_with(tmp_path, ["echo"] * 4, clock_ns=clock) as sup:
        tr = sup.transport_factory("checkpoint")
        base = clock.ns
        tr.send(0, 1, {"a": "b"})                                       # the fan-out starts here: t = 0
        wait_readable(sup.children[0])
        clock.ns = base + 5000 * 1_000_000                              # the reply is read at exactly 5000 ms
        assert tr.next_event(5000) is None
        assert tr.next_event(5000) is None                              # still queued, still stamped 5000: the timer keeps winning at the same deadline
        clock.ns += 1_000_000
        ev = tr.next_event(5001)
        assert ev is not None and ev[0] == 5000 and ev[1] == 0 and ev[2] == 1


def test_a_reply_read_one_millisecond_before_the_deadline_is_returned(tmp_path):
    clock = FakeClock()
    with sup_with(tmp_path, ["echo"] * 4, clock_ns=clock) as sup:
        tr = sup.transport_factory("checkpoint")
        base = clock.ns
        tr.send(0, 1, {"a": "b"})
        wait_readable(sup.children[0])
        clock.ns = base + 4999 * 1_000_000
        ev = tr.next_event(5000)
        assert ev is not None and ev[0] == 4999


def test_time_is_measured_from_the_first_send_and_floored_to_milliseconds(tmp_path):
    clock = FakeClock(ns=123_456_789_012)
    with sup_with(tmp_path, ["echo"] * 4, clock_ns=clock) as sup:
        tr = sup.transport_factory("checkpoint")
        base = clock.ns
        tr.send(2, 1, {"a": "b"})
        clock.ns += 7_000_000_000                                       # a later send must not move the origin
        tr.send(3, 1, {"a": "b"})
        wait_readable(sup.children[2])
        clock.ns = base + 250_999_999                                   # 250.999999 ms floors to 250
        ev = tr.next_event(10_000)
        assert ev is not None and ev[0] == 250


def test_with_nothing_asked_and_nothing_arriving_the_deadline_elapses_in_real_time(tmp_path):
    with sup_with(tmp_path, ["hang"] * 4) as sup:
        tr = sup.transport_factory("checkpoint")
        t0 = time.monotonic()
        assert tr.next_event(300) is None
        assert 0.25 <= time.monotonic() - t0 < 5


def test_a_witness_that_never_answers_makes_the_call_return_none_at_the_deadline_not_before(tmp_path):
    with sup_with(tmp_path, ["hang"] * 4) as sup:
        tr = sup.transport_factory("checkpoint")
        tr.send(0, 1, {"a": "b"})
        t0 = time.monotonic()
        assert tr.next_event(400) is None
        assert 0.35 <= time.monotonic() - t0 < 5
        assert sup.status()[0]["alive"] is True


def test_a_partial_reply_line_is_not_delivered_until_it_is_complete(tmp_path):
    with sup_with(tmp_path, ["partial"] * 4) as sup:
        tr = sup.transport_factory("checkpoint")
        tr.send(1, 1, {"a": "b"})
        assert tr.next_event(150) is None                                # the first half is in the pipe, the second half comes 0.4 s later
        ev = tr.next_event(5000)
        assert ev is not None and ev[1] == 1 and ev[3]["type"] == "signature"


# ---- strict reply parsing ---------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("mode,fragment", [
    ("garbage", "strict JSON"), ("badutf8", "UTF-8"), ("badutf8-in-json", "UTF-8"), ("badschema", "schemaVersion"), ("extra-key", "envelope"), ("missing-reply", "envelope"),
    ("reply-not-object", "not an object"), ("dup-keys", "strict JSON"), ("deep", "strict JSON"), ("json-number", "envelope"), ("id-null", "id"), ("id-bool", "id"), ("id-str", "id"), ("id-neg", "id"), ("id-future", "id"),
])
def test_a_reply_that_is_not_a_well_formed_envelope_is_one_malformed_reply_for_the_asked_round(tmp_path, mode, fragment):
    with sup_with(tmp_path, [mode] * 4) as sup:
        tr = sup.transport_factory("checkpoint")
        tr.send(2, 1, {"secret": "TOP-SECRET-PROPOSAL"})
        ev = tr.next_event(5000)
        assert ev is not None and ev[1] == 2 and ev[2] == 1
        detail = malformed(ev)
        assert fragment in detail
        assert "TOP-SECRET" not in detail and "ff" not in detail.lower().replace("buffer", "")      # the detail never echoes what the child sent


def test_a_boolean_id_is_not_an_integer_even_when_it_equals_an_issued_id(tmp_path):
    with sup_with(tmp_path, ["hang", "hang", "id-bool", "hang"]) as sup:
        tr = sup.transport_factory("checkpoint")
        tr.send(2, 1, {"a": "b"})                                        # id 0 ...
        tr.send(2, 1, {"a": "c"})                                        # ... and id 1, which `true` equals in Python
        evs = collect(tr, 2)
        assert len(evs) == 2 and all("not an integer" in malformed(e) for e in evs)


@pytest.mark.parametrize("extra,kind", [(0, "signature"), (1, "malformed")])
def test_a_reply_line_of_exactly_one_mib_is_accepted_and_one_byte_more_is_malformed(tmp_path, extra, kind):
    with sup_with(tmp_path, [f"limit {extra}"] * 4) as sup:
        tr = sup.transport_factory("checkpoint")
        tr.send(0, 1, {"a": "b"})
        ev = tr.next_event(15000)
        assert ev is not None and ev[3]["type"] == kind
        if kind == "malformed":
            assert "1 MiB" in ev[3]["detail"]


def test_a_line_nobody_asked_for_is_dropped(tmp_path):
    with sup_with(tmp_path, ["echo", "echo", "echo", "spontaneous"]) as sup:
        tr = sup.transport_factory("checkpoint")
        tr.send(0, 1, {"a": "b"})                                        # witness 3 was never asked, but writes an unprompted line at startup
        evs = collect(tr, 5, deadline_ms=1500)
        assert [e[1] for e in evs] == [0]


def test_a_request_larger_than_the_pipe_is_completed_once_the_child_starts_reading(tmp_path):
    with sup_with(tmp_path, ["slowreader"] * 4) as sup:
        tr = sup.transport_factory("checkpoint")
        big = {"pad": "x" * 300_000}
        tr.send(0, 1, big)
        assert len(sup.children[0].pending) == 1                          # the child is still asleep: the first write was partial
        ev = tr.next_event(15000)
        assert ev is not None and ev[3]["type"] == "signature" and ev[3]["message"] == big
        assert sup.children[0].pending == []


def test_a_malformed_reply_is_attributed_to_the_round_of_the_latest_request_of_that_witness(tmp_path):
    with sup_with(tmp_path, ["garbage"] * 4) as sup:
        tr = sup.transport_factory("checkpoint")
        tr.send(0, 1, {"a": "b"})
        tr.send(0, 2, {"a": "c"})
        evs = collect(tr, 2)
        assert [e[2] for e in evs] == [2, 2]                              # both unattributable lines are charged to the latest round asked of witness 0


def test_a_reply_that_claims_an_id_issued_to_another_witness_is_malformed_for_the_replying_witness(tmp_path):
    with sup_with(tmp_path, ["echo", "fixed-id 0", "echo", "echo"]) as sup:
        tr = sup.transport_factory("checkpoint")
        tr.send(0, 1, {"a": "b"})                                        # id 0 belongs to witness 0
        tr.send(1, 1, {"a": "b"})                                        # witness 1 answers with id 0
        evs = {e[1]: e for e in collect(tr, 2)}
        assert evs[0][3]["type"] == "signature"
        assert "another witness" in malformed(evs[1])


def test_a_duplicate_reply_to_one_request_is_delivered_twice_as_evidence(tmp_path):
    with sup_with(tmp_path, ["duplicate"] * 4) as sup:
        tr = sup.transport_factory("checkpoint")
        tr.send(3, 1, {"a": "b"})
        evs = collect(tr, 2)
        assert len(evs) == 2 and evs[0][1:] == evs[1][1:] and evs[0][3]["type"] == "signature"
        assert tr.next_event(200) is None


def test_a_2_mib_reply_line_is_one_malformed_reply_and_the_next_normal_reply_still_parses(tmp_path):
    with sup_with(tmp_path, ["big-then-echo"] * 4) as sup:
        tr = sup.transport_factory("checkpoint")
        tr.send(0, 1, {"n": "1"})
        assert "1 MiB" in malformed(tr.next_event(8000))
        tr.send(0, 1, {"n": "2"})
        ev = tr.next_event(8000)
        assert ev is not None and ev[3]["type"] == "signature" and ev[3]["message"] == {"n": "2"}


def test_a_late_reply_of_an_earlier_collection_is_dropped_by_the_next_collection(tmp_path):
    with sup_with(tmp_path, ["late 400"] * 4) as sup:
        a = sup.transport_factory("checkpoint")
        a.send(0, 1, {"who": "A"})
        b = sup.transport_factory("checkpoint")                           # the adapter is serial: A is over
        b.send(0, 1, {"who": "B"})
        ev = b.next_event(8000)
        assert ev is not None and ev[3]["message"] == {"who": "B"}        # A's reply (id 0) arrived first and was dropped
        assert b.next_event(600) is None
        with pytest.raises(wpt.TransportError):
            a.send(0, 1, {"who": "A"})
        with pytest.raises(wpt.TransportError):
            a.next_event(10)
        with pytest.raises(wpt.TransportError):
            a.cancel(0, 1)


# ---- cancel ------------------------------------------------------------------------------------------------------------------------------------------------------

def test_cancel_after_the_write_was_delivered_changes_nothing_and_the_reply_still_arrives(tmp_path):
    with sup_with(tmp_path, ["echo"] * 4) as sup:
        tr = sup.transport_factory("checkpoint")
        tr.send(1, 1, {"a": "b"})
        assert sup.children[1].pending == []                              # a small write reached the pipe at once
        tr.cancel(1, 1)
        ev = tr.next_event(5000)
        assert ev is not None and ev[1] == 1 and ev[3]["type"] == "signature"


def test_cancel_drops_a_write_of_which_no_byte_was_written_but_never_a_started_one(tmp_path):
    with sup_with(tmp_path, ["noread"] * 4, close_grace_s=0.3) as sup:
        tr = sup.transport_factory("checkpoint")
        child = sup.children[0]
        tr.send(0, 1, {"pad": "x" * 400_000})                             # more than a pipe holds: the first write is partial
        assert len(child.pending) == 1 and child.pending[0].off > 0
        tr.send(0, 1, {"small": "first"})                                 # a second round-1 write, untouched
        tr.send(0, 2, {"small": "m"})
        assert len(child.pending) == 3 and child.pending[1].off == 0 and child.pending[2].off == 0
        tr.cancel(0, 2)
        assert len(child.pending) == 2                                    # only the untouched ROUND-2 write is gone
        tr.cancel(0, 1)
        assert len(child.pending) == 1 and child.pending[0].off > 0       # the untouched round-1 write is gone too; the started one must complete, or the child's next line would be cut in half


def test_send_never_blocks_on_a_child_that_does_not_read(tmp_path):
    with sup_with(tmp_path, ["noread"] * 4, close_grace_s=0.3) as sup:
        tr = sup.transport_factory("checkpoint")
        t0 = time.monotonic()
        for r in (1, 2):
            tr.send(0, r, {"pad": "x" * 600_000})
        assert time.monotonic() - t0 < 5


# ---- supervision -------------------------------------------------------------------------------------------------------------------------------------------------

def test_a_child_that_exits_at_startup_is_a_silent_witness_with_its_first_stderr_line_kept(tmp_path):
    with sup_with(tmp_path, ["echo", "echo", "exit2", "echo"]) as sup:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            st = sup.status()[2]
            if not st["alive"] and st["stderrFirstLine"]:
                break
            time.sleep(0.05)
        st = sup.status()[2]
        assert st["alive"] is False and st["returncode"] == 2
        assert st["stderrFirstLine"] == '{"error":{"code":"MALFORMED","message":"stub startup refusal"}}'
        tr = sup.transport_factory("checkpoint")
        for w in range(4):
            tr.send(w, 1, {"a": "b"})                                     # writing to the dead child must not raise
        assert sorted(e[1] for e in collect(tr, 4, deadline_ms=1500)) == [0, 1, 3]
        assert os.path.exists(sup.pid_path(2))                            # evidence stays


def test_an_unterminated_endless_line_is_bounded_and_discarded_unread(tmp_path):
    with sup_with(tmp_path, ["endless"] * 4, close_grace_s=0.3) as sup:
        tr = sup.transport_factory("checkpoint")
        tr.send(0, 1, {"a": "b"})
        assert "1 MiB" in malformed(tr.next_event(15000))                  # reported as soon as the buffer passes the limit, long before any newline
        assert tr.next_event(1500) is None                                 # the rest of the 3 MiB is read and thrown away
        child = sup.children[0]
        assert len(child.buf) == 0 and child.skipping is True


def test_a_command_that_cannot_be_executed_is_a_dead_witness_with_a_spawn_error_and_no_pid_file(tmp_path):
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    os.chmod(state, 0o700)
    cmds = [[sys.executable, "-B", STUB, "echo"]] * 3 + [["/nonexistent/interpreter"]]
    sup = wpt.WitnessSupervisor(state_dir=str(state), commands=cmds)
    sup.start()
    try:
        assert sup.status()[3] == {"index": 3, "pid": None, "alive": False, "returncode": None, "stderrFirstLine": "", "spawnError": "FileNotFoundError"}
        assert not os.path.exists(sup.pid_path(3)) and not os.path.exists(sup.stderr_path(3)) and os.path.exists(sup.pid_path(0)) and os.path.exists(sup.stderr_path(0))
        tr = sup.transport_factory("checkpoint")
        tr.send(3, 1, {"a": "b"})                                          # writing to a witness that never existed must not raise
        tr.send(0, 1, {"a": "b"})
        assert [e[1] for e in collect(tr, 2, deadline_ms=1500)] == [0]
    finally:
        sup.close()


def test_a_write_to_a_child_that_is_alive_but_closed_its_stdin_marks_it_broken_and_never_raises(tmp_path):
    with sup_with(tmp_path, ["close-stdin", "echo", "echo", "echo"], close_grace_s=0.3) as sup:
        tr = sup.transport_factory("checkpoint")
        child = sup.children[0]
        deadline = time.monotonic() + 10
        while not child.broken and time.monotonic() < deadline:            # the stub closes fd 0 a moment after it starts: until then the pipe still has a reader
            tr.send(0, 1, {"a": "b"})
            time.sleep(0.05)
        assert child.broken is True and child.pending == []                # EPIPE: the witness is silent from here on, nothing was raised
        assert sup.status()[0]["alive"] is True                            # alive is not the same as reachable
        tr.send(0, 1, {"a": "c"})                                          # and a later send is dropped without a sound
        assert child.pending == []


def test_a_supervisor_whose_four_children_all_fail_to_start_still_starts_and_reports_it(tmp_path):
    with sup_with(tmp_path, ["exit2"] * 4) as sup:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and any(s["alive"] for s in sup.status()):
            time.sleep(0.05)
        assert [s["alive"] for s in sup.status()] == [False] * 4
        tr = sup.transport_factory("checkpoint")
        tr.send(0, 1, {"a": "b"})
        assert tr.next_event(200) is None


def test_a_child_that_dies_stays_dead_there_is_no_respawn_and_its_pid_file_stays(tmp_path):
    with sup_with(tmp_path, ["die-after-first"] * 4) as sup:
        pid_before = sup.status()[0]["pid"]
        tr = sup.transport_factory("checkpoint")
        tr.send(0, 1, {"a": "b"})
        assert collect(tr, 1)[0][3]["type"] == "signature"
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and sup.status()[0]["alive"]:
            time.sleep(0.05)
        tr2 = sup.transport_factory("checkpoint")
        tr2.send(0, 1, {"a": "c"})
        assert tr2.next_event(400) is None
        st = sup.status()[0]
        assert st["alive"] is False and st["returncode"] == 0 and st["pid"] == pid_before
        assert open(sup.pid_path(0)).read() == f"{pid_before}\n"


def test_a_stopped_child_is_alive_but_silent_and_answers_after_it_continues(tmp_path):
    with sup_with(tmp_path, ["echo"] * 4) as sup:
        pid = sup.status()[1]["pid"]
        os.kill(pid, signal.SIGSTOP)
        try:
            tr = sup.transport_factory("checkpoint")
            tr.send(1, 1, {"a": "b"})
            assert tr.next_event(300) is None
            assert sup.status()[1]["alive"] is True
        finally:
            os.kill(pid, signal.SIGCONT)
        ev = tr.next_event(8000)
        assert ev is not None and ev[1] == 1


def test_a_child_that_writes_a_lot_to_stderr_does_not_block_and_only_its_first_line_is_kept(tmp_path):
    with sup_with(tmp_path, ["noise"] * 4) as sup:
        tr = sup.transport_factory("checkpoint")
        tr.send(0, 1, {"a": "b"})
        ev = tr.next_event(8000)
        assert ev is not None and ev[3]["type"] == "signature"
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and sup.status()[0]["stderrFirstLine"] != "FIRST-LINE noise":
            time.sleep(0.05)
        assert sup.status()[0]["stderrFirstLine"] == "FIRST-LINE noise"
        assert len(sup.children[0].stderr_kept) <= wpt.STDERR_FILE_BYTES


def test_the_stderr_file_is_private_created_empty_bounded_to_4096_bytes_and_a_chatty_child_neither_blocks_nor_grows_it(tmp_path):
    with sup_with(tmp_path, ["noise", "echo", "echo", "echo"]) as sup:
        for i in range(4):
            assert (os.stat(sup.stderr_path(i)).st_mode & 0o777) == 0o600
        assert sup.stderr_path(1) == str(tmp_path / "state" / "witness-1.stderr") and os.path.getsize(sup.stderr_path(1)) == 0     # a quiet child leaves an empty file
        tr = sup.transport_factory("checkpoint")
        tr.send(0, 1, {"a": "b"})
        ev = tr.next_event(10000)                                          # 300 KiB of stderr must not keep the reply from arriving
        assert ev is not None and ev[3]["type"] == "signature"
        for _ in range(5):
            sup.status()                                                    # more drains must not grow it
        written = open(sup.stderr_path(0), "rb").read()
        assert len(written) == wpt.STDERR_FILE_BYTES == 4096
        assert written.startswith(b"FIRST-LINE noise\n") and written == bytes(sup.children[0].stderr_kept)
    assert os.path.getsize(sup.stderr_path(0)) == 4096                      # and it stays after close


def test_the_stderr_file_keeps_the_startup_error_line_of_a_witness_that_failed_and_stays_after_close(tmp_path):
    line = '{"error":{"code":"MALFORMED","message":"stub startup refusal"}}\n'
    with sup_with(tmp_path, ["echo", "echo", "exit2", "echo"]) as sup:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not (not sup.status()[2]["alive"] and sup.status()[2]["stderrFirstLine"]):
            time.sleep(0.05)
        assert open(sup.stderr_path(2)).read() == line
        assert [os.path.getsize(sup.stderr_path(i)) for i in (0, 1, 3)] == [0, 0, 0]
    assert open(sup.stderr_path(2)).read() == line


def test_a_stale_stderr_file_of_an_earlier_run_is_replaced_not_appended_to(tmp_path):
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    (state / "witness-0.stderr").write_text("STALE EVIDENCE OF AN EARLIER RUN\n")
    with sup_with(tmp_path, ["echo"] * 4) as sup:
        assert open(sup.stderr_path(0)).read() == ""


def test_close_closes_stdin_so_a_cooperating_child_exits_zero_and_leaves_the_pid_and_stderr_files(tmp_path):
    sup = sup_with(tmp_path, ["echo"] * 4)
    sup.start()
    pids = [s["pid"] for s in sup.status()]
    sup.close()
    assert [s["returncode"] for s in sup.status()] == [0, 0, 0, 0] and all(not s["alive"] for s in sup.status())
    for i, pid in enumerate(pids):
        assert open(sup.pid_path(i)).read() == f"{pid}\n"
        assert os.path.exists(sup.stderr_path(i))
    sup.close()                                                           # idempotent


def test_close_kills_a_child_that_does_not_react_to_eof_after_the_bounded_grace(tmp_path):
    sup = sup_with(tmp_path, ["echo"] * 4)
    sup.start()
    pid = sup.status()[2]["pid"]
    os.kill(pid, signal.SIGSTOP)
    t0 = time.monotonic()
    sup.close(grace_s=0.5)
    assert 0.4 <= time.monotonic() - t0 < 8
    assert sup.status()[2]["returncode"] == -signal.SIGKILL


def test_a_closed_supervisor_refuses_new_transports_and_sends(tmp_path):
    sup = sup_with(tmp_path, ["echo"] * 4)
    sup.start()
    tr = sup.transport_factory("checkpoint")
    sup.close()
    with pytest.raises(wpt.SupervisorError):
        sup.transport_factory("checkpoint")
    with pytest.raises(wpt.TransportError):
        tr.send(0, 1, {"a": "b"})


# ---- pid files and the state directory ----------------------------------------------------------------------------------------------------------------------

def test_the_pid_file_is_next_to_the_witness_directory_private_atomic_and_never_deleted(tmp_path):
    with sup_with(tmp_path, ["hang"] * 4) as sup:
        state = tmp_path / "state"
        for i, st in enumerate(sup.status()):
            p = state / f"witness-{i}.pid"
            assert sup.pid_path(i) == str(p) and p.read_text() == f"{st['pid']}\n"
            assert (os.stat(p).st_mode & 0o777) == 0o600
        assert sorted(os.listdir(state)) == sorted([f"witness-{i}.pid" for i in range(4)] + [f"witness-{i}.stderr" for i in range(4)])    # no temp file left, no witness-<i> directory (the store makes those)
        os.kill(sup.status()[1]["pid"], signal.SIGKILL)
    assert all((state / f"witness-{i}.pid").exists() for i in range(4))


def test_a_stale_pid_file_of_an_earlier_run_is_replaced_by_the_new_pid(tmp_path):
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    (state / "witness-0.pid").write_text("999999\n")
    with sup_with(tmp_path, ["hang"] * 4) as sup:
        assert (state / "witness-0.pid").read_text() == f"{sup.status()[0]['pid']}\n"


def test_start_refuses_a_missing_non_directory_or_group_readable_state_directory_and_spawns_nothing(tmp_path):
    cmds = [[sys.executable, "-B", STUB, "hang"]] * 4
    with pytest.raises(wpt.SupervisorError):
        wpt.WitnessSupervisor(state_dir=str(tmp_path / "nope"), commands=cmds).start()
    f = tmp_path / "file"
    f.write_text("x")
    os.chmod(f, 0o700)                                                    # private, so that only the "not a directory" rule can refuse it
    sf = wpt.WitnessSupervisor(state_dir=str(f), commands=cmds)
    with pytest.raises(wpt.SupervisorError):
        sf.start()
    assert sf.children == []                                              # refused BEFORE anything was spawned
    d = tmp_path / "open"
    d.mkdir()
    os.chmod(d, 0o755)
    s = wpt.WitnessSupervisor(state_dir=str(d), commands=cmds)
    with pytest.raises(wpt.SupervisorError):
        s.start()
    assert s.children == [] and os.listdir(d) == []


def test_a_supervisor_starts_once_and_hands_out_transports_only_after_it_started(tmp_path):
    s = sup_with(tmp_path, ["hang"] * 4)
    with pytest.raises(wpt.SupervisorError):
        s.transport_factory("checkpoint")
    s.start()
    try:
        with pytest.raises(wpt.SupervisorError):
            s.start()
    finally:
        s.close()


def test_the_constructor_refuses_anything_but_four_commands(tmp_path):
    for bad in ([], [["x"]] * 3, [["x"]] * 5, [["x"], ["x"], ["x"], "x"], [["x"], ["x"], ["x"], []], "four"):
        with pytest.raises(wpt.SupervisorError):
            wpt.WitnessSupervisor(state_dir=str(tmp_path), commands=bad)


# ---- the command seam --------------------------------------------------------------------------------------------------------------------------------------------

def cmdline(pid):
    return open(f"/proc/{pid}/cmdline", "rb").read().rstrip(b"\0").decode().split("\0")


def test_without_command_for_every_child_runs_exactly_the_given_command(tmp_path):
    with sup_with(tmp_path, ["hang"] * 4) as sup:
        assert sup.command_for is None
        for i, st in enumerate(sup.status()):
            assert cmdline(st["pid"]) == sup.commands[i] == [sys.executable, "-B", STUB, "hang"]


def test_command_for_is_asked_once_per_index_in_order_with_a_copy_and_replaces_exactly_the_index_it_answers_for(tmp_path):
    asked = []
    replacement = [sys.executable, "-B", STUB, "exit2"]

    def hook(index, default):
        asked.append((index, list(default)))
        default.append("MUTATED-BY-THE-HOOK")                                # a copy: this must not reach sup.commands
        return replacement if index == 2 else [sys.executable, "-B", STUB, "hang"]

    with sup_with(tmp_path, ["hang"] * 4, command_for=hook) as sup:
        assert asked == [(i, [sys.executable, "-B", STUB, "hang"]) for i in range(4)]
        assert all("MUTATED-BY-THE-HOOK" not in c for c in sup.commands)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and sup.status()[2]["alive"]:
            time.sleep(0.05)
        st = sup.status()
        assert st[2]["alive"] is False and st[2]["returncode"] == 2          # the replaced child is the exit2 stub
        for i in (0, 1, 3):
            assert st[i]["alive"] is True and cmdline(st[i]["pid"]) == [sys.executable, "-B", STUB, "hang"]


@pytest.mark.parametrize("bad", [None, [], "not a list", ["ok", 5], 7, ("a", "b")], ids=["none", "empty", "string", "non-string-item", "number", "tuple"])
def test_a_command_for_answer_that_is_not_a_non_empty_list_of_strings_spawns_nothing(tmp_path, bad):
    sup = sup_with(tmp_path, ["hang"] * 4, command_for=lambda i, d: bad if i == 3 else d)
    with pytest.raises(wpt.SupervisorError):
        sup.start()
    assert sup.children == [] and os.listdir(tmp_path / "state") == []         # even indexes 0..2, which were answered correctly, were not spawned


def test_a_command_for_that_raises_is_a_supervisor_error_without_its_traceback_and_spawns_nothing(tmp_path):
    def hook(index, default):
        raise RuntimeError("TOP-SECRET-HOOK-INTERNALS")
    sup = sup_with(tmp_path, ["hang"] * 4, command_for=hook)
    with pytest.raises(wpt.SupervisorError) as e:
        sup.start()
    assert "RuntimeError" in str(e.value) and "TOP-SECRET" not in str(e.value)
    assert sup.children == [] and os.listdir(tmp_path / "state") == []


def test_command_for_must_be_callable_and_for_deployment_forwards_it(tmp_path):
    with pytest.raises(wpt.SupervisorError):
        wpt.WitnessSupervisor(state_dir=str(tmp_path), commands=[["x"]] * 4, command_for="no")
    hook = lambda i, d: d  # noqa: E731
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    sup = wpt.WitnessSupervisor.for_deployment(manifest=json.load(open(F2)), deployment_path="/d/dep.json", abi_dir="/d/abi", state_dir=str(state), command_for=hook)
    assert sup.command_for is hook


# ---- the production command ---------------------------------------------------------------------------------------------------------------------------------------

def test_the_production_command_line_is_exactly_the_documented_witness_main_invocation():
    argv = wpt.witness_main_argv(deployment="/d/dep.json", abi_dir="/d/abi", state_dir="/s", index=2, key_label="witness-3", python="/usr/bin/python3")
    assert argv == ["/usr/bin/python3", "-B", "-m", "hmbc_protocol.witness_main", "--deployment", "/d/dep.json", "--abi-dir", "/d/abi", "--index", "2", "--key-label", "witness-3", "--state-dir", "/s"]
    argv = wpt.witness_main_argv(deployment="/d/dep.json", abi_dir="/d/abi", state_dir="/s", index=0, key_label="witness-1", allow_governance="/d/allow.json", python="p")
    assert argv[-2:] == ["--allow-governance", "/d/allow.json"]
    for bad in (dict(index=4), dict(index=-1), dict(index=True), dict(index="0"), dict(key_label="Witness 1"), dict(key_label="")):
        kw = dict(deployment="d", abi_dir="a", state_dir="s", index=0, key_label="witness-1", python="p")
        kw.update(bad)
        with pytest.raises(wpt.SupervisorError):
            wpt.witness_main_argv(**kw)


def test_the_child_environment_is_scrubbed_to_exactly_three_variables(monkeypatch):
    monkeypatch.setenv("HMBC_SECRET", "must-not-leak")
    monkeypatch.setenv("PYTHONPATH", "/somewhere/else")
    env = wpt.child_env()
    assert env == {"PYTHONPATH": PROTO, "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}


def test_the_key_labels_come_from_the_manifest_in_witness_set_order():
    m = json.load(open(F2))
    assert wpt.key_labels(m) == ["witness-1", "witness-2", "witness-3", "witness-4"]
    for bad in (["a"], ["witness-1", "witness-2", "witness-3"], ["witness-1", "witness-1", "witness-3", "witness-4"], ["witness-1", "witness-2", "witness-3", 4], ["witness-1", "witness-2", "witness-3", "W 4"],
                ["witness-1", "witness-2", "witness-3", "witness-4", "witness-1"]):                # five entries, four distinct: only the length rule refuses it
        m2 = json.loads(json.dumps(m))
        m2["fixture"]["witnessSet"]["keyLabels"] = bad
        with pytest.raises(wpt.SupervisorError):
            wpt.key_labels(m2)
    with pytest.raises(wpt.SupervisorError):
        wpt.key_labels({})


def test_for_deployment_builds_one_witness_main_command_per_label_with_the_scrubbed_environment(tmp_path):
    m = json.load(open(F2))
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    sup = wpt.WitnessSupervisor.for_deployment(manifest=m, deployment_path="/d/dep.json", abi_dir="/d/abi", state_dir=str(state), allow_governance="/d/allow.json", python="/usr/bin/python3",
                                            close_grace_s=0.7)
    assert sup.close_grace_s == 0.7
    assert sup.commands == [wpt.witness_main_argv(deployment="/d/dep.json", abi_dir="/d/abi", state_dir=str(state), index=i, key_label=f"witness-{i + 1}", allow_governance="/d/allow.json",
                                                  python="/usr/bin/python3") for i in range(4)]
    assert sup.cwd == PROTO and sup.env == wpt.child_env()


# ---- argument validation and the module's own discipline -----------------------------------------------------------------------------------------------------------

def test_a_caller_bug_is_a_transport_error_not_a_silent_drop(tmp_path):
    with sup_with(tmp_path, ["hang"] * 4) as sup:
        tr = sup.transport_factory("checkpoint")
        for args in ((4, 1, {}), (-1, 1, {}), (True, 1, {}), ("0", 1, {}), (0, 3, {}), (0, 0, {}), (0, True, {}), (0, 1, []), (0, 1, "x"), (0, 1, {"k": float("nan")}), (0, 1, {"k": object()}),
                     (0, 1, {"pad": "x" * (wpt.MAX_LINE_BYTES + 10)})):
            with pytest.raises(wpt.TransportError):
                tr.send(*args)
        for args in ((4, 1), (0, 3), (True, 1)):
            with pytest.raises(wpt.TransportError):
                tr.cancel(*args)
        for bad in (-1, True, "5", 1.5, None):
            with pytest.raises(wpt.TransportError):
                tr.next_event(bad)
        with pytest.raises(wpt.SupervisorError):
            sup.transport_factory("nonsense")


def test_the_module_reads_no_wall_clock_environment_thread_socket_or_randomness_and_sleeps_nowhere():
    src = open(os.path.join(PROTO, "hmbc_protocol", "witness_process_transport.py")).read()
    for banned in ("time.time(", "time.sleep(", "datetime", "import threading", "import socket", "import random", "os.environ", "import asyncio", "import signal"):
        assert banned not in src, banned
    assert "monotonic_ns" in src and "selectors" in src
