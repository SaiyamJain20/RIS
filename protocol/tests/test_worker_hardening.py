"""Findings 3, 6, 12, 13 and 15 of the independent review (worker): idle clock, races, rollback, deployment binding, boundary, durability."""
import copy
import os
import sqlite3
import threading

import pytest
from eth_utils import keccak

from hmbc_protocol.worker import Worker, WorkerError
import ledger_setup as setup
from test_worker import P1_POLICY, P1_RECORD, grant, worker


def test_release_after_an_idle_period_is_expired_even_though_no_block_was_mined(world, tmp_path):
    from support import rpc
    led, ctx = world
    _, grant_id = grant(led, ctx)
    w = worker(led, tmp_path)
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    rpc(led.dbc.url, "evm_increaseTime", [300])                                  # idle: the latest block's timestamp does not move
    with pytest.raises(WorkerError) as e:
        w.release(grant_id)
    assert e.value.code == "EXPIRED"


def test_the_expiry_boundary_is_exclusive_at_the_grant_expiry_second(world, tmp_path):
    led, ctx = world
    _, grant_id = grant(led, ctx)
    expires = int(led.dbc.call(led.KSSC, "grantDetails", grant_id)["expiresAt"])
    for now, ok in ((expires - 1, True), (expires, False), (expires + 1, False)):
        w = Worker(led, tmp_path / f"s{now}", clock=lambda n=now: n)
        w.encrypt_record(P1_RECORD, P1_POLICY, "0")
        if ok:
            assert w.release(grant_id)["grantId"] == grant_id
        else:
            with pytest.raises(WorkerError) as e:
                w.release(grant_id)
            assert e.value.code == "EXPIRED"


def test_concurrent_registrations_of_the_same_record_are_all_idempotent_successes(world, tmp_path):
    led, ctx = world
    results, errors = [], []

    def go():
        try:
            results.append(Worker(led, tmp_path / "state", clock=led.dbc.now).encrypt_record(P1_RECORD, P1_POLICY, "0"))
        except Exception as e:  # noqa: BLE001
            errors.append(repr(e))

    for _ in range(12):                                                          # repeat: the race is probabilistic
        threads = [threading.Thread(target=go) for _ in range(6)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        os.remove(tmp_path / "state" / "worker.sqlite")
    assert errors == [], errors
    assert len({repr(r) for r in results}) == 1


def test_concurrent_releases_of_one_grant_mint_exactly_one_token_and_one_intent(world, tmp_path):
    led, ctx = world
    _, grant_id = grant(led, ctx)
    worker(led, tmp_path).encrypt_record(P1_RECORD, P1_POLICY, "0")
    tokens, errors = [], []

    def go():
        try:
            tokens.append(worker(led, tmp_path).release(grant_id)["responseEnvelope"]["token"])
        except Exception as e:  # noqa: BLE001
            errors.append(repr(e))

    threads = [threading.Thread(target=go) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert errors == [] and len(set(tokens)) == 1 and len(tokens) == 8
    assert [e["type"] for e in worker(led, tmp_path).events()].count("RELEASE_INTENT") == 1


def test_a_failure_while_recording_the_send_does_not_wedge_the_connection(world, tmp_path, monkeypatch):
    led, ctx = world
    _, grant_id = grant(led, ctx)
    w = worker(led, tmp_path)
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    real, calls = w._event, []

    def flaky(kind, row, ts):
        calls.append(kind)
        if kind == "RELEASE_SENT" and calls.count("RELEASE_SENT") == 1:
            raise sqlite3.OperationalError("disk I/O error")
        return real(kind, row, ts)

    monkeypatch.setattr(w, "_event", flaky)
    with pytest.raises(sqlite3.OperationalError):
        w.release(grant_id)
    again = w.release(grant_id)                                                  # must work: the failed transaction was rolled back
    st = w.status(grant_id)
    assert again["grantId"] == grant_id and (st["sendAttempts"], st["completedAttempts"]) == (1, 1)   # the failed attempt was rolled back, not counted


def test_durability_pragmas_are_on(world, tmp_path):
    led, ctx = world
    w = worker(led, tmp_path)
    assert w.db.execute("pragma synchronous").fetchone()[0] == 2                 # FULL
    assert w.db.execute("pragma journal_mode").fetchone()[0] == "wal"


def test_state_directory_open_to_group_or_other_is_refused(world, tmp_path):
    led, ctx = world
    d = tmp_path / "open"
    d.mkdir(mode=0o755)
    os.chmod(d, 0o755)
    with pytest.raises(WorkerError):
        Worker(led, d, clock=led.dbc.now)


def test_state_created_for_one_deployment_is_refused_by_another(world, tmp_path):
    from hmbc_protocol import ledger as ledger_mod
    led, ctx = world
    worker(led, tmp_path).encrypt_record(P1_RECORD, P1_POLICY, "0")
    other = copy.deepcopy(led.deployment)
    other["chains"]["dbc"]["contracts"]["KSSC"] = "0x" + "99" * 20               # a different (e.g. fake) DBC
    with pytest.raises(WorkerError) as e:
        Worker(ledger_mod.Ledger.from_deployment(other), tmp_path / "state", clock=lambda: 0)
    assert e.value.code == "WRONG_DESTINATION"
