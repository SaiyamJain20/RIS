"""Pool driver (HMBC2020 successor, F task 3 slice 3c): runs ONE `witness_pool.Collection` against a transport until it is done.

PAPER-DERIVED RECONSTRUCTION. `Collection` is sans-IO; this loop gives it the world. The TRANSPORT is injected and offers
  send(witness, round_no, message) -> None        fire the retained proposal (or the adopted value) at one witness
  cancel(witness, round_no) -> None               drop a write that has not been delivered
  next_event(deadline_ms) -> (t_ms, witness, round_no, reply) or None
      block until the next reply arrives (host-monotonic milliseconds since the start of the fan-out) or until the clock reaches `deadline_ms`; return None in the second case. A reply exactly at the deadline is NOT
      returned yet: the timer wins at equal milliseconds, as the collection's rule says.
Replies are `{"type": "signature", "message", "signature"}`, `{"type": "error", "code", "reason", "recorded"}` or `{"type": "malformed", "detail"}` (the strict parse of what a witness really sent is the transport's).
A real transport (supervised channels to four witness processes, a host-monotonic clock) is the integrated run's business and is not here. No clock, no thread and no socket in this module.
"""
from __future__ import annotations

MAX_STEPS = 100000


class DriverError(RuntimeError):
    """The transport broke the contract (time going backwards, no progress)."""


def _perform(actions, transport):
    for a in actions:
        if a["op"] == "send":
            transport.send(a["witness"], a["round"], a["message"])
        elif a["op"] == "cancel":
            transport.cancel(a["witness"], a["round"])


def run_collection(collection, transport):
    """Drive `collection` to its end and return its result (`collection.result`)."""
    _perform(collection.start(), transport)
    steps = 0
    while not collection.done:
        steps += 1
        if steps > MAX_STEPS:
            raise DriverError("the collection does not advance")
        timer = collection.next_timer_ms()
        event = transport.next_event(timer)
        if event is None:
            actions = collection.on_time(timer)
        else:
            t, witness, round_no, reply = event
            actions = collection.on_reply(t, witness, reply, round_no)
        _perform(actions, transport)
    return collection.result
