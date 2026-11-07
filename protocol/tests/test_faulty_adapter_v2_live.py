"""The TEST-ONLY alternate successor adapter entry against a real ledger with real supervised children (agent 2, proposal P3 of A2-0074; rows F-13, F-20 and F-19 of the F matrix).

`python -m testtools.faulty_adapter_v2 ... --witness-variant I=... --worker-variant compromised --claims FILE` is started as a REAL long-running process on a real Anvil pair with agent 1's F ledger (85c59f5); the
adapter spawns four real witness_main (or hook) children and every response is validated against the published schema. Symbolic mode, synthetic TEST-ONLY keys, one host, process death and real-time holds only.
  (a) F-13  `1=crash:after_commit`: the pool still certifies a checkpoint from the other three, witness 1 is `silent`, its pin is DURABLE (read with `witness_state --evidence`), the process is gone; the production
            entry restarted on the same state directory has witness 1 answer with the RECORDED checkpoint (the same proposal) and never a second value (a different proposal is CONFLICT_PINNED with the recorded value).
  (b) F-20  `2=delay:6000`: witness 2 misses the 5 s reply timeout (`silent` in the pool; `ADAPTER_UNAVAILABLE` after about 5 s in single-witness mode), the other three certify.
  (c) F-19  `--worker-variant compromised`: `release` for a CLAIMED request digest succeeds although the real ledger has no grant and the PBC never forwarded the request; the production entry answers NOT_COMMITTED
            for the same call. SYMBOLIC ONLY: no secrecy conclusion; it shows where authorisation is enforced.
The live fixture is the one of test_rpc_binding_view_live.py (a module-scoped Anvil pair, honouring HMBC_FOUNDRY_DIR). Real-time thresholds are generous; a heavily loaded host can still flake (b).
"""
import json
import os
import select
import subprocess
import sys
import time

import pytest

from hmbc_protocol import eip712, keys
from test_rpc_binding_view_live import f_ledger, live_f, mine, schema_validator, v2_line  # noqa: F401  (live_f is a fixture)

PROTO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FX = os.path.join(PROTO, "tests", "fixtures")
SCHEMA = os.path.join(FX, "agent3-v2.1-hmbc.schema.json")
SCHEMA_SHA = "d43c3a9a4cbb10214135afb767a2adc109da462f88bd11a81a8c8955d44fd1f3"
ENV = {"PYTHONPATH": PROTO, "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}
FAULTY = "testtools.faulty_adapter_v2"
PRODUCTION = "hmbc_protocol.adapter_v2_main"


class Adapter:
    """A long-running adapter process: one request line in, one response line out, with a read timeout; stderr goes to a file so a chatty child can never block it."""

    def __init__(self, live, tmp_path, module, extra=(), state="state"):
        dep_file = tmp_path / "dep.json"
        if not dep_file.exists():
            dep_file.write_text(json.dumps(live.dep))
        self.live, self.state_dir = live, str(tmp_path / state)
        self.err_path = tmp_path / f"{state}.stderr"
        args = ["--deployment", str(dep_file), "--abi-dir", live.abi_dir, "--schema", SCHEMA, "--schema-sha256", SCHEMA_SHA, "--schema-revision", "v2", "--state-dir", self.state_dir]
        self._err = open(self.err_path, "wb")
        self.p = subprocess.Popen([sys.executable, "-B", "-m", module, *extra, *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._err, cwd=PROTO, env=ENV, bufsize=0)
        self.buf = b""
        self.valid = schema_validator()

    def _line(self, timeout):
        deadline = time.monotonic() + timeout
        while b"\n" not in self.buf:
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError("no response line")
            if select.select([self.p.stdout], [], [], left)[0]:
                chunk = os.read(self.p.stdout.fileno(), 65536)
                if not chunk:
                    raise EOFError("the adapter closed its stdout: " + self.err_path.read_text()[:300])
                self.buf += chunk
        line, _, self.buf = self.buf.partition(b"\n")
        return line

    def ask(self, op, inp, timeout=90):
        self.p.stdin.write((v2_line(op, inp, self.live.dep) + "\n").encode())
        self.p.stdin.flush()
        r = json.loads(self._line(timeout))
        assert self.valid.is_valid(r), r                                                  # every response is valid against the published schema
        return r

    def pid(self, index):
        text = open(os.path.join(self.state_dir, f"witness-{index}.pid")).read()
        assert text.endswith("\n") and text[:-1].isdigit()
        return int(text[:-1])

    def close(self, timeout=60):
        try:
            self.p.stdin.close()
        except OSError:
            pass
        try:
            rc = self.p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.p.kill()
            rc = self.p.wait(timeout=30)
        self.p.stdout.close()
        self._err.close()
        return rc, self.err_path.read_text()


def proc_state(pid):
    """The kernel state letter of a process, or None when it no longer exists."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[0]
    except OSError:
        return None


def wait_dead(pid, seconds=15):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if proc_state(pid) in (None, "Z"):
            return True
        time.sleep(0.1)
    return False


def evidence(state_dir, index):
    p = subprocess.run([sys.executable, "-B", "-m", "hmbc_protocol.witness_state", "--state-dir", state_dir, "--witness-index", str(index), "--evidence"],
                       capture_output=True, text=True, cwd=PROTO, env=ENV, timeout=60)
    assert p.returncode == 0 and p.stderr == "", (p.returncode, p.stderr)
    return json.loads(p.stdout)


def fresh_blocks(live):
    mine(live, "pbc")
    mine(live, "dbc")


def statuses(result):
    return [o["status"] for o in result["collection"]["outcomes"]]


# ---- (a) F-13 --------------------------------------------------------------------------------------------------------------------------------------------

def test_row_f13_a_witness_killed_after_its_commit_is_silent_and_pinned_and_the_restart_replies_with_the_recorded_value(live_f, tmp_path):
    fresh_blocks(live_f)
    a = Adapter(live_f, tmp_path, FAULTY, ["--witness-variant", "1=crash:after_commit"])
    try:
        first = a.ask("collect_checkpoint", {})
        assert first["ok"] is True, first
        res = first["result"]
        assert len(set(res["signatures"])) == 3 and [o["witnessIndex"] for o in res["collection"]["outcomes"]] == ["0", "1", "2", "3"]
        assert statuses(res) == ["signed", "silent", "signed", "signed"], statuses(res)                  # the pool certified without witness 1, which never replied
        pid1 = a.pid(1)
        assert wait_dead(pid1), "the crash variant did not end witness 1"
        assert [proc_state(a.pid(i)) not in (None, "Z") for i in (0, 2, 3)] == [True, True, True]         # the other three are alive
        assert len(evidence(a.state_dir, 1)["conflicts"]) == 1                                           # the pin is DURABLE although no reply left the process
        assert all(len(evidence(a.state_dir, i)["conflicts"]) == 1 for i in (0, 2, 3))
    finally:
        rc, err = a.close()
    assert rc == 0 and err == "", (rc, err)
    assert os.path.exists(os.path.join(a.state_dir, "witness-1.pid"))                                    # the pid file stays after the process died

    prod = Adapter(live_f, tmp_path, PRODUCTION)                                                         # the PRODUCTION entry on the same state directory (the witnesses are restarted)
    try:
        again = prod.ask("collect_checkpoint", {"witnessIndex": "1"})
        assert again["ok"] is True and len(again["result"]["signatures"]) == 1 and "collection" not in again["result"], again
        assert again["result"]["checkpoint"] == res["checkpoint"]                                        # the SAME proposal: witness 1 answers with the value it recorded before it died
        assert len(evidence(prod.state_dir, 1)["conflicts"]) == 1                                        # and recorded no second one
        mine(live_f, "pbc")                                                                              # a DIFFERENT proposal for the same sequence (a newer source block)
        other = prod.ask("collect_checkpoint", {"witnessIndex": "1"})
        assert other["ok"] is False and other["error"]["code"] == "STALE_STATE" and other["error"]["reason"] == "CONFLICT_PINNED", other
        assert other["error"]["recorded"] == {"message": res["checkpoint"], "signature": again["result"]["signatures"][0]}
        assert len(evidence(prod.state_dir, 1)["conflicts"]) == 1
    finally:
        rc, err = prod.close()
    assert rc == 0 and err == "", (rc, err)


# ---- (b) F-20 --------------------------------------------------------------------------------------------------------------------------------------------

def test_row_f20_a_witness_held_for_six_seconds_misses_the_five_second_timeout_and_the_others_still_certify(live_f, tmp_path):
    fresh_blocks(live_f)
    a = Adapter(live_f, tmp_path, FAULTY, ["--witness-variant", "2=delay:6000"])
    try:
        t0 = time.monotonic()
        pool = a.ask("collect_checkpoint", {})
        assert pool["ok"] is True, pool
        assert statuses(pool["result"]) == ["signed", "signed", "silent", "signed"], statuses(pool["result"])
        assert len(set(pool["result"]["signatures"])) == 3
        pool_s = time.monotonic() - t0
        assert pool_s < 5.0                                                                              # the quorum did not wait for the held witness
        print(f"MEASURED F-20 pool collection with witness 2 held 6000 ms: {pool_s:.2f} s")
        t1 = time.monotonic()
        single = a.ask("collect_checkpoint", {"witnessIndex": "2"})
        waited = time.monotonic() - t1
        assert single["ok"] is False and single["error"]["code"] == "ADAPTER_UNAVAILABLE" and "did not answer within 5 s" in single["error"]["message"], single
        assert 4.5 <= waited <= 12.0, waited                                                              # about the 5 s reply timeout (generous upper bound for a loaded host)
        print(f"MEASURED F-20 single-witness call to the held witness: {waited:.2f} s then ADAPTER_UNAVAILABLE")
        ok = a.ask("collect_checkpoint", {"witnessIndex": "0"})                                          # an unheld witness still answers at once
        assert ok["ok"] is True and len(ok["result"]["signatures"]) == 1
    finally:
        rc, err = a.close()
    assert rc == 0 and err == "", (rc, err)


# ---- (c) F-19 --------------------------------------------------------------------------------------------------------------------------------------------

def test_row_f19_a_compromised_worker_releases_a_claimed_request_with_no_ledger_grant_where_the_production_entry_refuses(live_f, tmp_path):
    import ledger_setup as setup
    led = f_ledger(live_f)
    request = "0x" + "e1" * 32
    ungranted = "0x" + eip712.grant_id(bytes.fromhex(request[2:]), led.KSSC.address, led.dbc.chain_id).hex()
    assert led.dbc.call(led.KSSC, "grantDetails", ungranted)["exists"] is False
    assert led.pbc.call(led.PSC, "getRequest", request)["status"] == "0"                                 # the PBC never forwarded it either
    claims = tmp_path / "claims.json"
    claims.write_text(json.dumps([{"requestDigest": request, "dataId": setup.DATA_P1, "gid": keys.resolve("keyref:user:alice", ("user",))[1], "recipientKeyRef": "keyref:user:alice"}]))
    record = {"dataId": setup.DATA_P1, "owner": setup.addr("H2-root"), "payloadDigest": "0x" + __import__("eth_utils").keccak(text="synthetic payload P1").hex()}
    policy = {"clauses": [[{"role": setup.ROLE_DOCTOR, "kind": "1", "issuerMode": "0"}, {"role": setup.ROLE_ON_DUTY, "kind": "2", "issuerMode": "2"}]]}
    enc = {"record": record, "policy": policy, "keyEpoch": "0"}

    bad = Adapter(live_f, tmp_path, FAULTY, ["--worker-variant", "compromised", "--claims", str(claims)], state="state-bad")
    try:
        assert bad.ask("encrypt_record", enc)["ok"] is True                                              # the worker legitimately holds the record
        rel = bad.ask("release", {"grantId": ungranted})
        assert rel["ok"] is True and rel["result"]["grantId"] == ungranted, rel
        assert rel["result"]["recipientKeyHash"] == keys.recipient_key_hash("keyref:user:alice")
        fin = bad.ask("finish_decryption", {"response": rel["result"], "userKeyRef": "keyref:user:alice"})
        assert fin["ok"] is True and fin["result"]["decryptable"] is True
        other = bad.ask("release", {"grantId": "0x" + "ab" * 32})                                        # an UNCLAIMED grant id: still the honest worker's answer
        assert other["ok"] is False and other["error"]["code"] == "NOT_COMMITTED", other
    finally:
        rc, err = bad.close()
    assert rc == 0 and err == "", (rc, err)

    honest = Adapter(live_f, tmp_path, PRODUCTION, state="state-honest")                                  # the production entry, same ledger, same call
    try:
        assert honest.ask("encrypt_record", enc)["ok"] is True
        refused = honest.ask("release", {"grantId": ungranted})
        assert refused["ok"] is False and refused["error"]["code"] == "NOT_COMMITTED", refused
    finally:
        rc, err = honest.close()
    assert rc == 0 and err == "", (rc, err)
    assert led.dbc.call(led.KSSC, "grantDetails", ungranted)["exists"] is False                          # the ledger STILL has no such grant and never will
    assert led.pbc.call(led.PSC, "getRequest", request)["status"] == "0"
