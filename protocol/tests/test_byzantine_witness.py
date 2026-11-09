"""TEST-ONLY real-PROCESS Byzantine witness (H1 as a supervised child; agent 2, F phase; gap G1 of protocol/evidence/af-case-hook-inventory). Written BEFORE testtools/byzantine_witness.py existed.
PAPER-DERIVED RECONSTRUCTION; synthetic TEST-ONLY keys; deliberate adversary, not an observed behaviour.

The Byzantine variants of `testtools/byzantine.py` (Repeater, Equivocator, Impersonator, Poisoner, Garbage, withhold) are endpoints of the VIRTUAL transport. This module is the same adversary as a process that
speaks `hmbc-witness-rpc/v1` on stdin/stdout exactly like `hmbc_protocol.witness_main`, so the real supervisor, the real pool and the real ledger can be run against it (rows FL-4, FL-5, FL-7, F-12, F-17, F-22):

    python -m testtools.byzantine_witness --behavior SPEC <the production witness's own arguments>
    SPEC  withhold | garbage | repeat:N (2..8) | equivocate | impersonate:J (0..3) | poison:FIELD

  withhold        reads every request and never answers (alive but silent: not a SIGSTOP, so the pool sees a live process);
  garbage         answers every well-formed request with a reply of an unknown type;
  impersonate:J   signs the ASKED message with witness J's key: a valid signature that does not recover to the replying witness;
  poison:FIELD    signs a message that differs from the asked one in FIELD (if the message carries it) with its OWN key and replies with that message;
  repeat:N        the HONEST reply (the production service, store and view) written N times;
  equivocate      the HONEST reply, then a second signed value from the same key (the asked message with its most telling field changed).
The first four need only the deployment (strict, TEST-ONLY key derivation, the label must name the witness at the index) and make NO RPC call and touch NO state; `repeat` and `equivocate` start the production
service (the full production start-up). A start-up failure is ONE closed JSON line on stderr, exit 2, nothing on stdout. A malformed request line is answered MALFORMED, as the production witness does.
Not claimed: that any oracle accepts what these produce; anything about consensus, clocks or a real network."""
import io
import json
import os
import subprocess
import sys

import pytest

from hmbc_protocol import eip712
from hmbc_protocol import witness_main as wm

PROTO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FX = os.path.join(PROTO, "tests", "fixtures")
F2 = os.path.join(FX, "agent1-85c59f5-f-base-deployment.json")
E1 = os.path.join(FX, "deployment-agent1-91add8c-v1-repaired-e.json")
ABI_DIR = os.path.join(FX, "agent1-85c59f5-abi")
DEP = json.load(open(F2))
WITNESSES = DEP["fixture"]["witnessSet"]["witnesses"]
PBC = DEP["chains"]["pbc"]["chainId"]
H = "0x" + "ab" * 32
CP = {"sequence": "4", "authEpoch": "3", "policyVersion": "1", "keyEpoch": "0", "witnessSetVersion": "2", "sourceChainId": PBC, "psc": "0x" + "bb" * 20, "sourceBlockNumber": "138", "sourceBlockHash": H,
      "expiresAt": "1791521610"}
SIG = "0x" + "cd" * 65


def bw():
    if PROTO not in sys.path:
        sys.path.insert(0, PROTO)
    from testtools import byzantine_witness
    return byzantine_witness


def digest(name, message):
    """The EIP-712 digest (bytes) of `message` for the signed type `name`, by the same encoders the witness uses."""
    from testtools import byzantine as bz
    d = bz._digest(name, message, DEP)
    return d if isinstance(d, bytes) else bytes.fromhex(d[2:])


def args(spec, index=1, label=None, deployment=F2):
    return ["--behavior", spec, "--deployment", deployment, "--abi-dir", ABI_DIR, "--index", str(index), "--key-label", label or f"witness-{index + 1}", "--state-dir", "/nonexistent/state"]


def request(kind="checkpoint", message=None, ident=0, round_no=1):
    return json.dumps({"schemaVersion": "hmbc-witness-rpc/v1", "id": ident, "round": round_no, "kind": kind, "message": CP if message is None else message}, separators=(",", ":")) + "\n"


class StubService:
    """The honest reply of the production service, as a stub: a fixed signature (the Byzantine layer must not alter it)."""

    def sign_checkpoint(self, message):
        return SIG


def run_main(argv, lines, service_factory=None):
    out, err = io.StringIO(), io.StringIO()
    kw = {"service_factory": service_factory} if service_factory is not None else {}
    rc = bw().main(argv, stdin=io.BytesIO("".join(lines).encode()), stdout=out, stderr=err, **kw)
    return rc, [json.loads(ln) for ln in out.getvalue().splitlines()], err.getvalue()


# ---- the behaviour syntax ------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("spec", ["withhold", "garbage", "repeat:2", "repeat:8", "equivocate", "impersonate:0", "impersonate:3", "poison:sourceBlockNumber", "poison:expiresAt", "poison:result"])
def test_a_valid_behaviour_parses(spec):
    assert bw().parse_behavior(spec) == spec


@pytest.mark.parametrize("spec", ["", "Withhold", "withhold:1", "repeat", "repeat:1", "repeat:9", "repeat:02", "repeat:x", "repeat:2:3", "equivocate:1", "impersonate", "impersonate:4", "impersonate:-1", "impersonate:١",
                                  "poison", "poison:", "poison:nope", "poison:sourceBlockNumber:2", "garbage:x", "teleport", " withhold", "withhold "])
def test_a_malformed_behaviour_is_refused(spec):
    with pytest.raises(ValueError):
        bw().parse_behavior(spec)


# ---- the behaviours (no RPC, no state) -------------------------------------------------------------------------------------------------------------------------------------------------------------

def test_withhold_reads_every_request_and_never_answers():
    rc, out, err = run_main(args("withhold"), [request(ident=0), request(ident=1)])
    assert rc == 0 and out == [] and err == ""


def test_garbage_answers_every_well_formed_request_with_a_reply_of_an_unknown_type():
    rc, out, err = run_main(args("garbage"), [request(ident=7), request("decision", ident=8)])
    assert rc == 0 and err == ""
    assert [(r["schemaVersion"], r["id"], r["reply"]["type"]) for r in out] == [("hmbc-witness-rpc/v1", 7, "bogus"), ("hmbc-witness-rpc/v1", 8, "bogus")]


@pytest.mark.parametrize("j", [0, 2, 3])
def test_impersonate_signs_the_asked_message_with_another_witnesss_key(j):
    rc, out, _ = run_main(args(f"impersonate:{j}", index=1), [request(ident=5)])
    assert rc == 0 and len(out) == 1 and out[0]["id"] == 5
    reply = out[0]["reply"]
    assert reply["type"] == "signature" and reply["message"] == CP
    assert eip712.recover(digest("StateCheckpoint", CP), reply["signature"]) == WITNESSES[j]


def test_impersonate_of_its_own_index_is_an_honest_looking_signature_of_its_own_key():
    rc, out, _ = run_main(args("impersonate:1", index=1), [request()])
    d = digest("StateCheckpoint", CP)
    assert eip712.recover(d, out[0]["reply"]["signature"]) == WITNESSES[1]


@pytest.mark.parametrize("field,expected", [("sourceBlockNumber", "139"), ("authEpoch", "4"), ("expiresAt", "1791521611"), ("sourceBlockHash", "0x" + "ab" * 31 + "ac")])
def test_poison_signs_a_message_that_differs_in_exactly_that_field_with_its_own_key(field, expected):
    rc, out, _ = run_main(args(f"poison:{field}", index=1), [request()])
    assert rc == 0 and len(out) == 1
    reply = out[0]["reply"]
    assert reply["type"] == "signature" and reply["message"] == dict(CP, **{field: expected}) and reply["message"] != CP
    d = digest("StateCheckpoint", reply["message"])
    assert eip712.recover(d, reply["signature"]) == WITNESSES[1]


def test_poison_of_a_field_the_message_does_not_carry_leaves_the_message_unchanged():
    rc, out, _ = run_main(args("poison:result", index=1), [request()])
    assert out[0]["reply"]["message"] == CP


@pytest.mark.parametrize("kind", ["decision", "receipt", "governance"])
def test_the_light_behaviours_refuse_a_request_that_is_not_well_formed_exactly_like_the_production_witness(kind):
    lines = ["not json\n", json.dumps({"schemaVersion": "hmbc-witness-rpc/v1", "id": 3, "round": 1, "kind": "checkpoint"}) + "\n", json.dumps({"schemaVersion": "hmbc-witness-rpc/v1", "id": 4, "round": 3, "kind": kind,
             "message": {}}) + "\n"]
    rc, out, _ = run_main(args("garbage"), lines)
    assert [(r["id"], r["reply"]["code"]) for r in out] == [(None, "MALFORMED"), (3, "MALFORMED"), (4, "MALFORMED")]


# ---- the behaviours that wrap the honest production reply ----------------------------------------------------------------------------------------------------------------------------------------

def test_repeat_writes_the_honest_reply_n_times():
    rc, out, _ = run_main(args("repeat:3"), [request(ident=2)], service_factory=lambda a: StubService())
    assert rc == 0 and len(out) == 3 and all(r == out[0] for r in out)
    assert out[0] == {"schemaVersion": "hmbc-witness-rpc/v1", "id": 2, "reply": {"type": "signature", "message": CP, "signature": SIG}}


def test_repeat_does_not_repeat_an_error_reply_into_n_different_things():
    rc, out, _ = run_main(args("repeat:2"), ["not json\n"], service_factory=lambda a: StubService())
    assert len(out) == 2 and out[0] == out[1] and out[0]["reply"]["code"] == "MALFORMED"


def test_equivocate_writes_the_honest_reply_then_a_second_signed_value_from_the_same_key():
    rc, out, _ = run_main(args("equivocate", index=1), [request(ident=9)], service_factory=lambda a: StubService())
    assert rc == 0 and len(out) == 2 and out[0]["id"] == out[1]["id"] == 9
    assert out[0]["reply"] == {"type": "signature", "message": CP, "signature": SIG}
    second = out[1]["reply"]
    assert second["type"] == "signature" and second["message"] != CP and second["message"]["sequence"] == CP["sequence"]
    d = digest("StateCheckpoint", second["message"])
    assert eip712.recover(d, second["signature"]) == WITNESSES[1]


def test_equivocate_does_not_add_a_second_value_to_an_error_reply():
    rc, out, _ = run_main(args("equivocate"), ["not json\n"], service_factory=lambda a: StubService())
    assert len(out) == 1 and out[0]["reply"]["code"] == "MALFORMED"


def test_the_light_behaviours_never_start_the_production_service():
    def boom(a):
        raise AssertionError("the production service must not be started")
    for spec in ("withhold", "garbage", "impersonate:2", "poison:authEpoch"):
        rc, _, _ = run_main(args(spec), [request()], service_factory=boom)
        assert rc == 0


# ---- start-up refusals -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def refusal_args():
    return {
        "malformed-behaviour": args("teleport"),
        "wrong-label-for-the-index": args("garbage", index=1, label="witness-1"),
        "label-for-no-witness": args("garbage", index=1, label="nobody"),
        "deployment-without-an-f-witness-set": args("garbage", deployment=E1),
        "missing-deployment-file": args("garbage", deployment="/nonexistent/dep.json"),
        "index-out-of-range": ["--behavior", "garbage", "--deployment", F2, "--abi-dir", ABI_DIR, "--index", "4", "--key-label", "witness-5", "--state-dir", "/x"],
        "missing-flag": ["--behavior", "garbage", "--deployment", F2],
    }


@pytest.mark.parametrize("name", sorted(refusal_args()))
def test_a_bad_start_is_one_closed_json_line_exit_2_and_nothing_on_stdout(name):
    out, err = io.StringIO(), io.StringIO()
    rc = bw().main(refusal_args()[name], stdin=io.BytesIO(b""), stdout=out, stderr=err)
    assert rc == 2 and out.getvalue() == "", name
    lines = err.getvalue().splitlines()
    assert len(lines) == 1 and set(json.loads(lines[0])) == {"error"} and json.loads(lines[0])["error"]["code"] in ("MALFORMED", "UNKNOWN_AUTHORITY"), (name, lines)
    assert "/nonexistent" not in err.getvalue() and ABI_DIR not in err.getvalue()


def test_a_deployment_without_a_test_only_key_derivation_is_refused_even_with_a_valid_witness_set(tmp_path):
    """Sensitivity case of mutant B10 (found by tools/run_byzantine_witness_mutants.py): the refusal list above used an E deployment, which fails for another reason (no F witness set)."""
    dep = json.loads(json.dumps(DEP))
    dep["fixture"]["keyDerivation"] = "production keys loaded from a vault"
    path = tmp_path / "dep.json"
    path.write_text(json.dumps(dep))
    out, err = io.StringIO(), io.StringIO()
    rc = bw().main(args("garbage", deployment=str(path)), stdin=io.BytesIO(b""), stdout=out, stderr=err)
    assert rc == 2 and out.getvalue() == "" and json.loads(err.getvalue())["error"]["message"] == bw().MSG_DEPLOYMENT and str(tmp_path) not in err.getvalue()


@pytest.mark.parametrize("argv", [["--behavior", "garbage", "--deployment", F2], ["--behavior", "garbage", "--deployment", F2, "--abi-dir", ABI_DIR, "--index", "4", "--key-label", "witness-5", "--state-dir", "/x"],
                                  ["--behavior"], ["--deployment", F2], ["--behavior", "teleport", "--deployment", F2]], ids=["missing-flags", "index-out-of-range", "behavior-without-value", "no-behavior", "bad-behavior"])
def test_a_bad_start_as_a_real_process_is_one_closed_line_on_the_real_stderr_and_no_usage_text(argv):
    """Sensitivity case of mutant B19: the in-process refusal tests inject their own stderr, so a usage text written to the REAL stderr was invisible to them."""
    p = subprocess.run([sys.executable, "-B", "-m", "testtools.byzantine_witness", *argv], input=b"", capture_output=True, cwd=PROTO, env={"PYTHONPATH": PROTO, "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}, timeout=60)
    assert p.returncode == 2 and p.stdout == b""
    lines = p.stderr.decode().splitlines()
    assert len(lines) == 1 and set(json.loads(lines[0])) == {"error"} and "usage" not in p.stderr.decode().lower(), p.stderr


# ---- as a real process, and the production boundary ------------------------------------------------------------------------------------------------------------------------------------------

def test_as_a_real_process_it_serves_stdin_to_stdout_and_exits_zero_at_eof():
    p = subprocess.run([sys.executable, "-B", "-m", "testtools.byzantine_witness", *args("garbage")], input=request(ident=11), capture_output=True, text=True, cwd=PROTO,
                       env={"PYTHONPATH": PROTO, "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}, timeout=60)
    assert p.returncode == 0 and p.stderr == ""
    assert [json.loads(ln)["reply"]["type"] for ln in p.stdout.splitlines()] == ["bogus"]


def test_no_production_module_imports_the_byzantine_process_and_it_has_no_clock_thread_or_socket():
    for f in os.listdir(os.path.join(PROTO, "hmbc_protocol")):
        if f.endswith(".py"):
            assert "byzantine_witness" not in open(os.path.join(PROTO, "hmbc_protocol", f)).read(), f
    src = open(os.path.join(PROTO, "testtools", "byzantine_witness.py")).read()
    for banned in ("import socket", "import threading", "import time", "import random", "datetime", "os.environ"):
        assert banned not in src, banned
    assert wm.SCHEMA == "hmbc-witness-rpc/v1"
