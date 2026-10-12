"""Crash BEFORE the durable release intent (PLAN B-E2 and agent-2 ROLE: "crash before intent"; S2-0001 T2). In-process characterization test.

A test-local Worker subclass raises SimulatedCrash while the release resolves its recipient binding. That point is after the grant, expiry and key-epoch
validation and before the intent transaction (worker.py release: `_recipient_for` precedes `begin immediate`). No production code changes; the subclass
lives only in this file. Expected: nothing durable about the release and nothing transmitted; a fresh Worker on the same state directory then performs
an ordinary first release (one intent, one attempt, delivery unknown), and a retry returns that same response.

Paper-derived reconstruction, symbolic mode, synthetic TEST-ONLY keys. A logical crash point only: not power-loss or OS-kill durability. The catalog has
no crash-before-intent row; this is owner evidence for a PLAN/ROLE requirement, not an E2 result.
"""
import pytest

from hmbc_protocol.worker import SimulatedCrash, Worker
from test_paper_profile import paper_grant
from test_worker import P1_POLICY, P1_RECORD, grant

PROFILES = ["world", "world_paper", "world_paper_minimal"]


class CrashBeforeIntent(Worker):
    """Dies while binding the recipient: every check before it has passed, nothing of this release has been written yet."""

    def _recipient_for(self, g: dict) -> str:
        raise SimulatedCrash("crash before the durable release intent")


@pytest.mark.parametrize("fixture_name", PROFILES)
def test_crash_before_intent_leaves_no_trace_and_a_restart_releases_once(request, fixture_name, tmp_path):
    led, ctx = request.getfixturevalue(fixture_name)
    _, grant_id = grant(led, ctx) if fixture_name == "world" else paper_grant(led, ctx)
    state = tmp_path / "state"
    sent = []

    crashing = CrashBeforeIntent(led, state, clock=led.dbc.now)
    crashing.encrypt_record(P1_RECORD, P1_POLICY, "0")                       # record registration is a separate, earlier durable fact
    with pytest.raises(SimulatedCrash):
        crashing.release(grant_id, transmit=sent.append)
    crashing.db.close()                                                       # the "process" is gone

    restarted = Worker(led, state, clock=led.dbc.now)                         # a new process on the same durable state
    assert sent == []                                                         # nothing left the worker
    assert restarted.status(grant_id) is None and restarted.events() == []   # no release row, no event: no trace of the crashed attempt

    resp = restarted.release(grant_id, transmit=sent.append)                  # an ordinary FIRST release after the restart
    assert sent == [resp]
    assert [e["type"] for e in restarted.events()] == ["RELEASE_INTENT", "RELEASE_SENT"]
    st = restarted.status(grant_id)
    assert (st["delivery"], st["sendAttempts"], st["completedAttempts"]) == ("unknown", 1, 1)

    again = restarted.release(grant_id)                                       # a retry returns the same cached response, no second intent
    assert again == resp
    assert [e["type"] for e in restarted.events()] == ["RELEASE_INTENT", "RELEASE_SENT", "RELEASE_SENT"]
