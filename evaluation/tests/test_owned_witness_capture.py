"""Owned-pipe acquisition probes, using synthetic children only; no F cases."""
import importlib
import json
import os
import sys

import pytest

from evaluation.sealed_signing_capture_v1 import join_sealed_capture
from evaluation.tests.test_signing_event_join_v2 import event_for
from evaluation.tests.test_witness_history_v2 import fixture


ECHO = """import sys,json
for line in sys.stdin:
 request=json.loads(line)
 print(json.dumps({'schemaVersion':'hmbc-witness-rpc/v1','id':request['id'],
  'reply':{'type':'error','code':'POLICY_DENIED','reason':'synthetic','recorded':None}}),flush=True)
"""


def request(request_id=1):
    _, _, evidence = fixture()
    row = next(row for row in evidence["conflicts"] if row["type"] == "AccessDecision")
    return json.loads(event_for(row, request_id=request_id)["requestLine"])


def child(tmp_path, program=ECHO, **kwargs):
    try:
        module = importlib.import_module("evaluation.owned_witness_capture")
    except ModuleNotFoundError:
        pytest.fail("Owned witness RPC acquisition is not implemented")
    return module.CapturedWitnessProcess(
        [sys.executable, "-u", "-c", program], cwd=tmp_path,
        output=tmp_path / "capture-process", timeout=0.5, stop_grace=0.3, **kwargs)


def test_parent_acquires_two_exchanges_with_reused_id_and_finishes_owned_child(tmp_path):
    proc = child(tmp_path)
    with proc:
        pid = proc.pid
        first = proc.exchange(request())
        proc.exchange(request())
        with pytest.raises(RuntimeError, match="finished"):
            proc.completed_capture()
    capture, receipt, acquisition = proc.completed_capture()
    assert [row["sequence"] for row in capture["events"]] == ["1", "2"]
    assert json.loads(capture["events"][0]["responseLine"]) == first
    assert receipt["eventCount"] == receipt["sourceEventCount"] == "2"
    assert acquisition["attemptCount"] == acquisition["eventCount"] == 2
    assert acquisition["pid"] == pid
    assert acquisition["transportComplete"] is True
    assert acquisition["stdoutEof"] is True
    assert acquisition["captureAuthenticated"] is False
    assert acquisition["transcriptCompletenessEstablished"] is False
    assert acquisition["exitCode"] == 0
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
    saved = json.loads((proc.output / "acquisition.json").read_text())
    assert saved == acquisition


@pytest.mark.parametrize("name", ["AccessDecision", "StateCheckpoint", "GrantReceipt", "GovernanceAction"])
def test_pipe_acquired_signature_joins_exact_existing_history(tmp_path, name):
    manifest, observations, evidence = fixture()
    row = next(row for row in evidence["conflicts"] if row["type"] == name)
    event = event_for(row)
    # The synthetic child supplies a real fixture signature; no protocol service.
    program = "import sys\nfor line in sys.stdin:\n print(" + repr(event["responseLine"]) + ",flush=True)\n"
    with child(tmp_path, program) as proc:
        proc.exchange(json.loads(event["requestLine"]))
    capture, receipt, _ = proc.completed_capture()
    joined = join_sealed_capture(capture, receipt, evidence, manifest=manifest,
                                 observations=observations, expected_owner=evidence["owner"],
                                 compiled_max_admins="8")
    assert joined["joined"][0]["digest"] == row["digests"][0]["digest"]
    assert joined["captureAuthenticated"] is False
    assert joined["transcriptCompletenessEstablished"] is False


def test_wire_journal_preserves_original_response_whitespace(tmp_path):
    line = '{ "schemaVersion": "hmbc-witness-rpc/v1", "id":1, "reply":{"type":"error"} }'
    program = "import sys\nfor _ in sys.stdin:\n print(" + repr(line) + ",flush=True)\n"
    with child(tmp_path, program) as proc:
        proc.exchange(request())
    capture, _, acquisition = proc.completed_capture()
    assert capture["events"][0]["responseLine"] == line
    journal = [json.loads(row) for row in (proc.output / "wire.jsonl").read_text().splitlines()]
    assert [row["direction"] for row in journal] == ["request", "response"]
    assert bytes.fromhex(journal[1]["hex"]) == line.encode() + b"\n"
    assert len(acquisition["wireJournalSha256"]) == 64


def test_worker_operation_rejected_before_any_request_then_session_still_works(tmp_path):
    with child(tmp_path) as proc:
        with pytest.raises(ValueError, match="witness RPC"):
            proc.exchange({"operation": "decrypt", "token": "never-write-this"})
        proc.exchange(request())
    _, _, acquisition = proc.completed_capture()
    assert acquisition["attemptCount"] == 1
    assert "never-write-this" not in (proc.output / "wire.jsonl").read_text()


def test_secret_field_inside_message_is_rejected_before_journaling(tmp_path):
    bad = request()
    bad["message"]["token"] = "never-write-this"
    with child(tmp_path) as proc:
        with pytest.raises(ValueError, match="witness RPC"):
            proc.exchange(bad)
        proc.exchange(request())
    _, _, acquisition = proc.completed_capture()
    assert acquisition["attemptCount"] == 1
    assert "never-write-this".encode().hex() not in (proc.output / "wire.jsonl").read_text()


def test_returned_documents_cannot_mutate_the_saved_capture(tmp_path):
    with child(tmp_path) as proc:
        proc.exchange(request())
    capture, receipt, acquisition = proc.completed_capture()
    capture["events"].clear()
    receipt["sourceEventCount"] = "0"
    acquisition["captureAuthenticated"] = True
    fresh_capture, fresh_receipt, fresh_acquisition = proc.completed_capture()
    assert len(fresh_capture["events"]) == 1
    assert fresh_receipt["sourceEventCount"] == "1"
    assert fresh_acquisition["captureAuthenticated"] is False


def test_caller_failure_also_prevents_completed_capture(tmp_path):
    proc = child(tmp_path)
    with pytest.raises(ValueError, match="caller failure"):
        with proc:
            proc.exchange(request())
            raise ValueError("caller failure")
    with pytest.raises(RuntimeError, match="incomplete"):
        proc.completed_capture()


def test_unbounded_tail_is_capped_and_never_treated_as_complete(tmp_path):
    program = ECHO + "sys.stdout.buffer.write(b'x' * (2 << 20)); sys.stdout.flush()\n"
    with child(tmp_path, program) as proc:
        proc.exchange(request())
    with pytest.raises(RuntimeError, match="incomplete"):
        proc.completed_capture()
    acquisition = json.loads((proc.output / "acquisition.json").read_text())
    assert acquisition["stdoutEof"] is False
    assert acquisition["retainedTailBytes"] == 1 << 20
    assert (proc.output / "stdout-tail.bin").stat().st_size == 1 << 20
    assert proc.returncode is not None


def test_worker_crash_api_cannot_send_to_witness_child(tmp_path):
    with child(tmp_path) as proc:
        with pytest.raises(ValueError, match="worker crash"):
            proc.exchange_crash({"token": "never-write-this"}, point="after_intent",
                                validate_response=lambda value: None)
        proc.exchange(request())
    assert proc.completed_capture()[2]["attemptCount"] == 1


def test_zero_exchange_session_does_not_establish_a_positive_control(tmp_path):
    with child(tmp_path) as proc:
        pass
    with pytest.raises(RuntimeError, match="incomplete"):
        proc.completed_capture()


@pytest.mark.parametrize("program,error", [
    ("import sys\nsys.stdin.readline()\n", ChildProcessError),
    ('import sys\nsys.stdin.readline()\nprint("not-json",flush=True)\n', ValueError),
    ('import sys\nsys.stdin.readline()\nprint(\'{"id":1,"id":1}\',flush=True)\n', ValueError),
    (ECHO.replace("request['id']", "request['id']+1"), ValueError),
    ("import sys,time\nsys.stdin.readline()\ntime.sleep(30)\n", TimeoutError),
])
def test_failed_exchange_never_yields_usable_capture_and_child_is_reaped(tmp_path, program, error):
    proc = child(tmp_path, program)
    with pytest.raises(error):
        with proc:
            proc.exchange(request())
    assert proc.returncode is not None
    with pytest.raises(RuntimeError, match="incomplete"):
        proc.completed_capture()
    saved = json.loads((proc.output / "acquisition.json").read_text())
    assert saved["transportComplete"] is False
    assert saved["attemptCount"] == 1


@pytest.mark.parametrize("tail", [
    "print('extra-frame',flush=True)",
    "print('noise',file=sys.stderr,flush=True)",
    "sys.exit(7)",
    "import time; time.sleep(30)",
])
def test_shutdown_detects_tail_stderr_nonzero_exit_or_forced_termination(tmp_path, tail):
    with child(tmp_path, ECHO + tail + "\n") as proc:
        proc.exchange(request())
    with pytest.raises(RuntimeError, match="incomplete"):
        proc.completed_capture()
    saved = json.loads((proc.output / "acquisition.json").read_text())
    assert saved["transportComplete"] is False
    assert proc.returncode is not None


def test_existing_output_is_preserved(tmp_path):
    output = tmp_path / "capture-process"
    output.mkdir()
    (output / "sentinel").write_text("preserve")
    with pytest.raises(FileExistsError):
        child(tmp_path).start()
    assert (output / "sentinel").read_text() == "preserve"
