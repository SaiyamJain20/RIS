"""TEST-ONLY deterministic crash hook for the E2/E3 crash schedules (design: communication/agent-2/outbox/drafts/E2-crash-hook-rfc-DRAFT.md, requested by A3-0031).

`python -m testtools.faulty_adapter --crash-at after_intent|after_send --state-dir D --deployment F` serves the SAME eight operations as the production adapter (it serves
that module) but the first `release` that reaches the named point kills the process with `os._exit(86)`: nothing further is written, nothing is cleaned up. The runner then
restarts the PRODUCTION command on the same state directory. Everything here runs through real processes against the live pinned ledger; the runner role is played by the test.

CANDIDATE code, not integrated, not a research result, and not power-loss durability: a simulated crash at two logical points after durable commits.
"""
import json
import pathlib
import subprocess
import sys

import pytest

from hmbc_protocol import wire
import ledger_setup as setup
from test_paper_profile import paper_grant
from test_worker import P1_POLICY, P1_RECORD, grant

PROTOCOL = pathlib.Path(__file__).resolve().parents[1]
ENV = {"PYTHONPATH": str(PROTOCOL), "PATH": "/usr/bin:/bin"}
CRASH_EXIT = 86
P1 = {"record": P1_RECORD, "policy": P1_POLICY, "keyEpoch": "0"}


class Proc:
    def __init__(self, module, state, dep_file, *extra):
        self.p = subprocess.Popen([sys.executable, "-m", module, *extra, "--state-dir", str(state), "--deployment", str(dep_file)], cwd=PROTOCOL, env=ENV,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.dep = None

    def send(self, dep, op, inp):
        self.p.stdin.write(json.dumps(dict(schemaVersion="v1", operation=op, input=inp, deploymentManifest=dep)) + "\n")
        self.p.stdin.flush()
        return self.p.stdout.readline()

    def call(self, dep, op, inp):
        line = self.send(dep, op, inp)
        assert line, "the process closed stdout without answering"
        resp = json.loads(line)
        wire.adapter_response(resp, op)
        return resp

    def finish(self):
        self.p.stdin.close()
        err = self.p.stderr.read()
        self.p.wait(timeout=20)
        return self.p.returncode, err


def worker_log(state):
    p = subprocess.run([sys.executable, "-m", "hmbc_protocol.worker_log", "--state-dir", str(state)], cwd=PROTOCOL, env=ENV, capture_output=True, text=True, timeout=30)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def setup_case(request, fixture_name, tmp_path):
    led, ctx = request.getfixturevalue(fixture_name)
    _, grant_id = paper_grant(led, ctx) if fixture_name != "world" else grant(led, ctx)
    dep_file = tmp_path / "deployment.json"
    dep_file.write_text(json.dumps(led.deployment))
    return led, grant_id, dep_file, tmp_path / "state"


PROFILES = ["world", "world_paper", "world_paper_minimal"]


@pytest.mark.parametrize("fixture_name", PROFILES)
def test_crash_after_intent_kills_the_process_and_a_production_restart_completes_the_same_release(request, fixture_name, tmp_path):
    led, grant_id, dep_file, state = setup_case(request, fixture_name, tmp_path)
    dep = led.deployment
    faulty = Proc("testtools.faulty_adapter", state, dep_file, "--crash-at", "after_intent")
    assert faulty.call(dep, "encrypt_record", P1)["ok"]
    assert faulty.send(dep, "release", {"grantId": grant_id}) == ""                          # no response line: the process died first
    code, err = faulty.finish()
    assert code == CRASH_EXIT and err == ""
    log = worker_log(state)
    assert [e["type"] for e in log["events"]] == ["RELEASE_INTENT"]                          # the intent is durable, no send was recorded
    assert (log["releases"][0]["sendAttempts"], log["releases"][0]["completedAttempts"]) == (0, 0)
    prod = Proc("hmbc_protocol.adapter", state, dep_file)
    resp = prod.call(dep, "release", {"grantId": grant_id})
    assert resp["ok"], resp
    assert prod.finish() == (0, "")
    log = worker_log(state)
    assert [e["type"] for e in log["events"]] == ["RELEASE_INTENT", "RELEASE_SENT"] and log["counts"] == {"releaseIntentCount": "1", "releaseSentCount": "1"}
    assert (log["releases"][0]["sendAttempts"], log["releases"][0]["completedAttempts"], log["releases"][0]["delivery"]) == (1, 1, "unknown")


@pytest.mark.parametrize("fixture_name", PROFILES)
def test_crash_after_send_delivers_the_response_then_kills_and_the_restart_returns_the_same_one(request, fixture_name, tmp_path):
    led, grant_id, dep_file, state = setup_case(request, fixture_name, tmp_path)
    dep = led.deployment
    faulty = Proc("testtools.faulty_adapter", state, dep_file, "--crash-at", "after_send")
    assert faulty.call(dep, "encrypt_record", P1)["ok"]
    first = faulty.call(dep, "release", {"grantId": grant_id})                                # the response WAS sent, and is a valid adapter response
    assert first["ok"] and first["result"]["grantId"] == grant_id
    code, err = faulty.finish()
    assert code == CRASH_EXIT and err == ""
    log = worker_log(state)
    assert [e["type"] for e in log["events"]] == ["RELEASE_INTENT", "RELEASE_SENT"]
    assert (log["releases"][0]["sendAttempts"], log["releases"][0]["completedAttempts"]) == (1, 0)      # the attempt was never recorded as completed
    prod = Proc("hmbc_protocol.adapter", state, dep_file)
    second = prod.call(dep, "release", {"grantId": grant_id})
    assert second["ok"] and second["result"] == first["result"]                              # the identical cached response, same token
    assert prod.finish() == (0, "")
    log = worker_log(state)
    assert [e["type"] for e in log["events"]] == ["RELEASE_INTENT", "RELEASE_SENT", "RELEASE_SENT"]
    assert log["counts"] == {"releaseIntentCount": "1", "releaseSentCount": "2"}
    assert (log["releases"][0]["sendAttempts"], log["releases"][0]["completedAttempts"], log["releases"][0]["delivery"]) == (2, 1, "unknown")


def test_a_release_that_does_not_reach_the_point_does_not_crash_the_process(world, tmp_path):
    """The hook fires only at the named point: an error before the intent is an ordinary response and the process lives on."""
    led, ctx = world
    _, grant_id = grant(led, ctx)
    dep_file = tmp_path / "deployment.json"
    dep_file.write_text(json.dumps(led.deployment))
    faulty = Proc("testtools.faulty_adapter", tmp_path / "state", dep_file, "--crash-at", "after_intent")
    dep = led.deployment
    assert faulty.call(dep, "encrypt_record", P1)["ok"]
    nowhere = faulty.call(dep, "release", {"grantId": "0x" + "ee" * 32})                      # no such grant: refused before any intent
    assert nowhere["ok"] is False and nowhere["error"]["code"] == "NOT_COMMITTED"
    assert faulty.p.poll() is None                                                            # still alive
    assert faulty.send(dep, "release", {"grantId": grant_id}) == ""                          # the real one reaches the point and dies
    assert faulty.finish()[0] == CRASH_EXIT


def test_the_hook_refuses_bad_input_cleanly(world, tmp_path):
    led, ctx = world
    dep = json.loads(json.dumps(led.deployment))
    dep_file = tmp_path / "d.json"
    dep_file.write_text(json.dumps(dep))

    def run(*args):
        return subprocess.run([sys.executable, "-m", "testtools.faulty_adapter", *args], cwd=PROTOCOL, env=ENV, capture_output=True, text=True, timeout=30, input="")
    for args in (["--state-dir", str(tmp_path / "s1"), "--deployment", str(dep_file)],                                    # no --crash-at
                 ["--crash-at", "during_send", "--state-dir", str(tmp_path / "s2"), "--deployment", str(dep_file)]):    # unknown point
        p = run(*args)
        assert p.returncode != 0 and p.stdout == "" and "refusing" in p.stderr and "Traceback" not in p.stderr, args
    dep["fixture"]["keyDerivation"] = "production keys"
    prod_file = tmp_path / "prod.json"
    prod_file.write_text(json.dumps(dep))
    p = run("--crash-at", "after_send", "--state-dir", str(tmp_path / "s3"), "--deployment", str(prod_file))
    assert p.returncode != 0 and p.stdout == "" and "TEST-ONLY" in p.stderr and "Traceback" not in p.stderr
    assert not (tmp_path / "s3").exists()                                                                                # refused before touching the disk


def test_the_hook_is_not_part_of_the_production_adapter_boundary():
    code = "import sys, hmbc_protocol.adapter, hmbc_protocol.export, hmbc_protocol.worker; print(any('testtools' in m for m in sys.modules))"
    p = subprocess.run([sys.executable, "-c", code], cwd=PROTOCOL, env=ENV, capture_output=True, text=True)
    assert p.stdout.strip() == "False", p.stderr
    manifest = (PROTOCOL / "exports" / "adapter.json").read_text()
    assert "faulty" not in manifest and "crash-at" not in manifest and "testtools" not in manifest
    assert not any("testtools" in f.read_text() or "faulty_adapter" in f.read_text() for f in (PROTOCOL / "hmbc_protocol").glob("*.py"))


@pytest.mark.parametrize("point", ["after_intent", "after_send"])
@pytest.mark.parametrize("fixture_name", PROFILES)
def test_first_production_restart_after_the_original_expiry_answers_expired_with_no_new_event(request, fixture_name, point, tmp_path):
    """S2-0001 T3, closing the open qualification "first restart at expiry" of A3-0038 in owner evidence. The hook crashes the FIRST release; both chains then
    pass the ORIGINAL grant expiry BEFORE any restart; the first production release after the restart must answer EXPIRED, emit no worker event and mint no
    token, so the whole exported worker log equals the post-crash log. after_intent: the token was never transmitted (0 send attempts) and it never will be;
    after_send: one attempted send, delivery unknown. Same rules in paper-strict, paper-minimal and repaired-e. A retry never extends a grant (A21/A37)."""
    led, grant_id, dep_file, state = setup_case(request, fixture_name, tmp_path)
    dep = led.deployment
    faulty = Proc("testtools.faulty_adapter", state, dep_file, "--crash-at", point)
    assert faulty.call(dep, "encrypt_record", P1)["ok"]
    if point == "after_intent":
        assert faulty.send(dep, "release", {"grantId": grant_id}) == ""                      # died before any response
    else:
        assert faulty.call(dep, "release", {"grantId": grant_id})["ok"]                       # the one response that left before the crash
    code, err = faulty.finish()
    assert code == CRASH_EXIT and err == ""
    at_crash = worker_log(state)
    sent_before = 0 if point == "after_intent" else 1
    assert [e["type"] for e in at_crash["events"]] == ["RELEASE_INTENT", "RELEASE_SENT"][:1 + sent_before]
    row = at_crash["releases"][0]
    assert (row["sendAttempts"], row["completedAttempts"], row["delivery"]) == (sent_before, 0, "unknown")

    expires = int(led.dbc.call(led.KSSC, "grantDetails", grant_id)["expiresAt"])
    assert led.dbc.now() < expires                                                            # the crash happened inside the grant's lifetime
    setup.advance(led, 40)                                                                    # every grant here lives <= 30 s: both chains pass it, no restart yet
    assert led.dbc.now() >= expires

    prod = Proc("hmbc_protocol.adapter", state, dep_file)                                     # the FIRST restart happens after the original expiry
    late = prod.call(dep, "release", {"grantId": grant_id})
    assert late["ok"] is False and late["error"]["code"] == "EXPIRED"
    assert prod.finish() == (0, "")
    assert worker_log(state) == at_crash                                                      # no event, no attempt, no new token, delivery still unknown
