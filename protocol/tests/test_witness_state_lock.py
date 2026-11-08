"""The witness store is a COOPERATIVE writer (agent 2; found by cross-running agent 3's store_snapshot_v2.locked_store on a real store, evidence/af2-lock-probe). Written BEFORE the fix.

Agent 3's snapshot takes `flock(LOCK_EX | LOCK_NB)` on the store's `.lock` and documents "a cooperative writer must honor the same flock". The store took `LOCK_SH` at its first signing and never released it, so a
running witness that had signed once refused every snapshot ("Store lock is busy") until the process died. The contract tested here:
  * a signing transaction (and `clear_fault`, and the TEST-ONLY `exclusive()`) holds the lock only while it runs and ALWAYS releases it, also when it refuses or raises;
  * while it runs, an independent exclusive lock cannot be taken (the writer is visible to a snapshot taker);
  * a signing that starts while an independent exclusive holder exists WAITS, then proceeds when it is released (the writer honors the lock).
`flock` locks belong to open file descriptions, so a second `os.open` of `.lock` in the same process conflicts exactly as another process would.
"""
import fcntl
import os
import threading
import time

import pytest

from hmbc_protocol import witness_state as ws
from test_witness_state import B, BIND, DBC, DOM_S, OWNER, cp_effect, h, obs, refusal, sign_cp, signer


def try_external(directory, mode):
    """True if an INDEPENDENT descriptor can take `mode` without blocking right now (and releases it at once)."""
    fd = os.open(os.path.join(directory, ".lock"), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, mode | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(fd, fcntl.LOCK_UN)
        return True
    finally:
        os.close(fd)


@pytest.fixture
def store(tmp_path):
    d = str(tmp_path / "witness-0")
    st = ws.init_store(d, BIND, B, OWNER)
    yield d, st
    st.close()


def test_the_lock_is_free_before_any_signing(store):
    d, st = store
    assert try_external(d, fcntl.LOCK_EX) is True


def test_the_lock_is_free_again_after_a_signing_returns(store):
    d, st = store
    sign_cp(st, 4, 138, 1791521610, "d1", obs(DBC, 160, 1791521600))
    assert try_external(d, fcntl.LOCK_EX) is True            # the A3 snapshot case: the store is open, the witness has signed, nothing is running


def test_the_lock_is_free_again_after_a_refused_signing(store):
    d, st = store
    sign_cp(st, 4, 138, 1791521610, "d1", obs(DBC, 160, 1791521600))
    e = refusal(lambda: sign_cp(st, 4, 139, 1791521650, "d2", obs(DBC, 160, 1791521601)))            # a different effect for a live key: pinned
    assert e is not None and e.reason == "CONFLICT_PINNED"
    assert try_external(d, fcntl.LOCK_EX) is True


def test_the_lock_is_free_again_after_a_signing_that_raises(store):
    d, st = store

    def boom(digest):
        raise RuntimeError("the signer failed")
    with pytest.raises(RuntimeError):
        st.sign(type="StateCheckpoint", domain=DOM_S, wsv="2", key="4", effect=cp_effect(138), expires_at="1791521610", digest=h("d1"), signer=boom, observe=lambda: obs(DBC, 160, 1791521600))
    assert try_external(d, fcntl.LOCK_EX) is True


def test_the_lock_is_free_again_after_clear_fault(store):
    d, st = store
    sign_cp(st, 4, 138, 1791521610, "d1", obs(DBC, 160, 1791521600))
    refusal(lambda: sign_cp(st, 5, 139, 1791521650, "d2", obs(DBC, 158, 1791521600)))               # a regression: the store is faulted
    st.clear_fault("operator clear after a test restart of the DBC", lambda: obs(DBC, 158, 1791521605))
    assert try_external(d, fcntl.LOCK_EX) is True


def test_the_lock_is_free_again_after_a_refused_clear_fault(store):
    d, st = store
    with pytest.raises(ValueError):
        st.clear_fault("nothing to clear", lambda: obs(DBC, 160, 1791521620))                         # not faulted: refused
    assert try_external(d, fcntl.LOCK_EX) is True


def test_a_signing_in_progress_is_visible_to_a_snapshot_taker(store):
    """While the signing transaction runs (the signer callback is called inside it) an independent exclusive lock is NOT available, and neither is a shared one, so a snapshot cannot read half a write."""
    d, st = store
    seen = {}

    def spy(digest):
        seen["ex"], seen["sh"] = try_external(d, fcntl.LOCK_EX), try_external(d, fcntl.LOCK_SH)
        return signer(digest)
    st.sign(type="StateCheckpoint", domain=DOM_S, wsv="2", key="4", effect=cp_effect(138), expires_at="1791521610", digest=h("d1"), signer=spy, observe=lambda: obs(DBC, 160, 1791521600))
    assert seen == {"ex": False, "sh": True}            # a writer holds a SHARED lock: an exclusive request must wait, another shared one is compatible


def test_exclusive_holds_the_lock_inside_and_releases_it_on_exit(store):
    d, st = store
    with st.exclusive():
        assert try_external(d, fcntl.LOCK_EX) is False and try_external(d, fcntl.LOCK_SH) is False
    assert try_external(d, fcntl.LOCK_EX) is True


def test_a_signing_waits_for_an_independent_exclusive_holder_and_proceeds_when_it_is_released(store):
    d, st = store
    fd = os.open(os.path.join(d, ".lock"), os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)                                                    # a snapshot taker holds the lock
    done, errors = threading.Event(), []

    def sign():
        try:
            sign_cp(st, 4, 138, 1791521610, "d1", obs(DBC, 160, 1791521600))
        except Exception as e:  # noqa: BLE001
            errors.append(e)
        done.set()
    t = threading.Thread(target=sign, daemon=True)
    t.start()
    try:
        assert not done.wait(1.5), "the writer did not honor the exclusive lock"      # it must be waiting
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    assert done.wait(15), "the writer never proceeded after the lock was released"
    t.join(5)
    assert errors == [] and try_external(d, fcntl.LOCK_EX) is True


def test_clear_fault_holds_the_lock_while_it_runs_and_releases_it_afterwards(store):
    d, st = store
    sign_cp(st, 4, 138, 1791521610, "d1", obs(DBC, 160, 1791521600))
    refusal(lambda: sign_cp(st, 5, 139, 1791521650, "d2", obs(DBC, 158, 1791521600)))               # a regression: the store is faulted
    seen = {}

    def spy():
        seen["ex"] = try_external(d, fcntl.LOCK_EX)                                                   # observe() runs inside the clear transaction
        return obs(DBC, 158, 1791521605)
    st.clear_fault("operator clear after a test restart of the DBC", spy)
    assert seen["ex"] is False and try_external(d, fcntl.LOCK_EX) is True
