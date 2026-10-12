"""Evidence export for the collector: the worker's durable log as JSON, with capabilities REDACTED to digests (live ledger)."""
import json
import pathlib
import subprocess
import sys

import pytest
from eth_utils import keccak

from test_worker import P1_POLICY, P1_RECORD, grant, worker

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
URI_METACHARACTER_NAMES = ["has#hash", "has?query", "has%20pct", "has%23enc", "has space"]


def dump(state_dir):
    p = subprocess.run([sys.executable, "-m", "hmbc_protocol.worker_log", "--state-dir", str(state_dir)], cwd=ROOT,
                       env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout), p.stdout


def test_log_export_has_the_counts_the_collector_needs_and_never_a_token(world, tmp_path):
    led, ctx = world
    signed, grant_id = grant(led, ctx)
    w = worker(led, tmp_path)
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    resp = w.release(grant_id)
    w.release(grant_id)                                                              # a retry: a second recorded attempt, same cached response
    out, raw = dump(tmp_path / "state")
    token = resp["responseEnvelope"]["token"]
    assert token not in raw and token[2:] not in raw                                 # the capability itself is never exported...
    rel = out["releases"][0]
    assert rel["tokenDigest"] == "0x" + keccak(bytes.fromhex(token[2:])).hex()       # ...but a stable commitment lets the collector check 'same token'
    assert (rel["grantId"], rel["requestDigest"], rel["dataId"], rel["gid"]) == (grant_id, signed["requestDigest"], resp["dataId"], ctx.alice)
    assert (rel["delivery"], rel["sendAttempts"], rel["completedAttempts"]) == ("unknown", 2, 2)
    assert [e["type"] for e in out["events"]] == ["RELEASE_INTENT", "RELEASE_SENT", "RELEASE_SENT"]
    assert out["counts"] == {"releaseIntentCount": "1", "releaseSentCount": "2"}
    assert out["deploymentFingerprint"] and len(out["deploymentFingerprint"]) == 64


def test_log_export_of_a_missing_or_foreign_directory_is_an_error(tmp_path):
    p = subprocess.run([sys.executable, "-m", "hmbc_protocol.worker_log", "--state-dir", str(tmp_path / "nope")], cwd=ROOT,
                       env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True, timeout=60)
    assert p.returncode != 0 and "worker.sqlite" in p.stderr


def test_the_export_accepts_the_adapters_own_state_directory(world, tmp_path):
    """The documented evidence command is `--state-dir <the adapter's state directory>`; the adapter keeps its worker under <dir>/worker, so that layout must work.
    (A2-0014 shipped the command but only ever pointed it at a directory a Worker had been created in directly.)"""
    from hmbc_protocol.worker import Worker
    led, ctx = world
    signed, grant_id = grant(led, ctx)
    w = Worker(led, tmp_path / "adapter-state" / "worker", clock=led.dbc.now)                                # the layout adapter.configure() uses
    w.encrypt_record(P1_RECORD, P1_POLICY, "0")
    w.release(grant_id)
    out, _ = dump(tmp_path / "adapter-state")
    assert out["counts"] == {"releaseIntentCount": "1", "releaseSentCount": "1"} and out["releases"][0]["grantId"] == grant_id


def test_the_export_refuses_an_ambiguous_directory_that_holds_both_layouts(tmp_path):
    for rel in ("worker/worker.sqlite", "worker.sqlite"):
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"")
    p = subprocess.run([sys.executable, "-m", "hmbc_protocol.worker_log", "--state-dir", str(tmp_path)], cwd=ROOT,
                       env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True, timeout=60)
    assert p.returncode != 0 and "ambiguous" in p.stderr and "Traceback" not in p.stderr


# ---- the exporter must open exactly the path it was given (A2-0039) -------------------------------------------------------------------
# The database path used to be interpolated unquoted into a SQLite `file:` URI. `#` and `?` then truncate the URI: the `mode=ro` flag is lost and a
# stray EMPTY database is created next to the directory (or a different database is read); `%xx` is decoded into another path. No live ledger needed.

def _offline_worker_with_one_event(state, request_digest="0x" + "11" * 32):
    """A real Worker on a real deployment manifest (construction makes no chain call) holding exactly one durable event row."""
    from hmbc_protocol.ledger import Ledger
    from hmbc_protocol.worker import Worker
    dep = json.loads((FIXTURES / "deployment-agent1-91add8c-v1-repaired-e.json").read_text())
    w = Worker(Ledger.from_deployment(dep), state, clock=lambda: 0)
    w.db.execute("insert into events(type,request_digest,grant_id,gid,data_id,timestamp) values('RELEASE_INTENT',?,?,?,?,1)",
                 (request_digest, "0x" + "22" * 32, "0x" + "33" * 20, "0x" + "44" * 32))
    w.db.close()


@pytest.mark.parametrize("name", URI_METACHARACTER_NAMES)
def test_the_export_reads_exactly_the_named_directory_and_creates_nothing(name, tmp_path):
    state = tmp_path / name
    _offline_worker_with_one_event(state)
    before = sorted(p.name for p in tmp_path.iterdir())
    out, _ = dump(state)
    assert [e["type"] for e in out["events"]] == ["RELEASE_INTENT"] and out["counts"] == {"releaseIntentCount": "1", "releaseSentCount": "0"}
    assert sorted(p.name for p in tmp_path.iterdir()) == before                 # a read-only export must not create a file beside the directory


def test_the_export_never_reads_a_sibling_database_at_a_truncated_path(tmp_path):
    """Truncated at `#`, the path of `run#1/worker.sqlite` is the sibling FILE `run`. A different, valid worker database there must not be read instead."""
    import shutil
    _offline_worker_with_one_event(tmp_path / "other", request_digest="0x" + "55" * 32)
    shutil.copyfile(tmp_path / "other" / "worker.sqlite", tmp_path / "run")      # a valid worker database sitting at the truncated path
    _offline_worker_with_one_event(tmp_path / "run#1")                           # the database that was actually asked for
    out, _ = dump(tmp_path / "run#1")
    assert [e["requestDigest"] for e in out["events"]] == ["0x" + "11" * 32]


def test_the_export_accepts_a_relative_state_directory(tmp_path, monkeypatch):
    from hmbc_protocol import worker_log
    _offline_worker_with_one_event(tmp_path / "rel dir#1")
    monkeypatch.chdir(tmp_path)
    assert len(worker_log.export("rel dir#1")["events"]) == 1
