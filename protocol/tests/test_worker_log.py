"""Evidence export for the collector: the worker's durable log as JSON, with capabilities REDACTED to digests (live ledger)."""
import json
import pathlib
import subprocess
import sys

from eth_utils import keccak

from test_worker import P1_POLICY, P1_RECORD, grant, worker

ROOT = pathlib.Path(__file__).resolve().parents[1]


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
