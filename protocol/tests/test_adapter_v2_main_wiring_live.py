"""LIVE tests of the wired successor command line (agent 2, Fork G; proposals P1 and P2 of A2-0074). Written BEFORE any run against the wiring, from the contract in A2-0074 and the published schema.

`python -m hmbc_protocol.adapter_v2_main` is started as a LONG-RUNNING subprocess (JSON lines in and out, interactively) on a real Anvil pair with agent 1's real F ledger (commit 85c59f5) and, for a
`repaired-f` deployment, four REAL `witness_main` children that the adapter supervises. Every response is validated against the PUBLISHED schema (agent3-v2.1-hmbc.schema.json) by the test as well as
by the process. What is shown: the supervised layout of A2-0074 section 2 (pid files, stderr files, ownership, no respawn, children die with the adapter), the four witness operations on the real
contracts through ONE adapter command, the process-control rows FL-2/FL-3 and the durable pin across an adapter restart. What is NOT shown: power loss, an OS crash, a second host, consensus (Anvil
is not Byzantine consensus), anything about timing under load beyond the generous bounds below, or any secrecy (symbolic mode, TEST-ONLY keys derivable from labels).

Real-time bounds are GENEROUS on purpose (a loaded host must not flake them); the observed numbers are appended as JSON lines to $FG_OBS_FILE when that variable is set (the parent's report).
Skipped when Foundry or the pinned ledger commit is missing (the shared fixture of test_rpc_binding_view_live.py): READ THE SKIP COUNT, not only "passed".
"""
import hashlib
import json
import os
import re
import select
import signal
import stat
import subprocess
import sys
import time

import pytest

from hmbc_protocol import eip712, messages, witness_service as svc
from test_rpc_binding_view_live import ANVIL_KEY0, _deploy, f_ledger, live_e, live_f, mine, schema_validator, v2_line, witness_view  # noqa: F401  (live_e, live_f are fixtures)

PROTO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FXD = os.path.join(PROTO, "tests", "fixtures")
SCHEMA = os.path.join(FXD, "agent3-v2.1-hmbc.schema.json")
SCHEMA_SHA = "d43c3a9a4cbb10214135afb767a2adc109da462f88bd11a81a8c8955d44fd1f3"
CAP_S = 10                                        # the documented collection cap
CAP_BOUND_S = 25                                  # generous: the cap plus start-up/scheduling slack on a loaded host
WAIT_S = float(os.environ.get("FG_WAIT_S", "120"))   # how long start-up/readiness may take; the RED run against the pre-wiring tree shortens it (default unchanged)


def observe(name, **kw):
    path = os.environ.get("FG_OBS_FILE")
    if path:
        with open(path, "a") as f:
            f.write(json.dumps({"test": name, **kw}) + "\n")


@pytest.fixture(scope="module")
def live_flow(tmp_path_factory):
    """A third real F deployment for the decision/receipt flow (it registers users and consumes a nonce: no other test here may share it)."""
    yield from _deploy(tmp_path_factory, "repaired-f", False)


# ---- /proc helpers ------------------------------------------------------------------------------------------------------------------------------------------
def proc_stat(pid):
    """(state letter, ppid) or None when the process does not exist."""
    try:
        data = open(f"/proc/{pid}/stat").read()
    except OSError:
        return None
    rest = data[data.rindex(")") + 2:].split()
    return rest[0], int(rest[1])


def alive(pid):
    st = proc_stat(pid)
    return st is not None and st[0] not in ("Z", "X")          # a killed child the adapter has not reaped yet is a zombie: dead for every purpose here


def cmdline(pid):
    try:
        return open(f"/proc/{pid}/cmdline", "rb").read().decode().split("\0")[:-1]
    except OSError:
        return None


def wait_gone(pid, timeout):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if not alive(pid):
            return True
        time.sleep(0.05)
    return not alive(pid)


def witness_procs(state=None):
    """pids of live witness_main processes, restricted to those whose command line names `state` when given."""
    out = []
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        cl = cmdline(int(name))
        if cl and "hmbc_protocol.witness_main" in cl and (state is None or str(state) in cl) and alive(int(name)):
            out.append(int(name))
    return out


# ---- the interactive adapter ----------------------------------------------------------------------------------------------------------------------------------
class Adapter:
    def __init__(self, live, tmp_path, *, name="a", state="state", revision="v2", allow=None, dep=None):
        self.live, self.tmp_path, self.dep = live, tmp_path, dep or live.dep
        self.state = tmp_path / state
        dep_file = tmp_path / f"dep-{name}.json"
        dep_file.write_text(json.dumps(self.dep))
        args = ["--deployment", str(dep_file), "--abi-dir", live.abi_dir, "--schema", SCHEMA, "--schema-sha256", SCHEMA_SHA, "--schema-revision", revision, "--state-dir", str(self.state)]
        if allow is not None:
            allow_file = tmp_path / f"allow-{name}.json"
            allow_file.write_text(json.dumps(allow))
            args += ["--allow-governance", str(allow_file)]
        self.err_path = tmp_path / f"adapter-{name}.stderr"
        self.err = open(self.err_path, "wb")                    # a file, not a pipe: a chatty adapter can never block on an unread pipe
        self.p = subprocess.Popen([sys.executable, "-B", "-m", "hmbc_protocol.adapter_v2_main", *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.err, cwd=PROTO,
                                  env={"PYTHONPATH": PROTO, "PATH": "/usr/bin:/bin"})
        self.buf = b""
        self.valid = schema_validator()
        self.rc = self.stderr = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def stderr_text(self):
        self.err.flush()
        return open(self.err_path).read()

    def _readline(self, timeout):
        end = time.monotonic() + timeout
        fd = self.p.stdout.fileno()
        while b"\n" not in self.buf:
            left = end - time.monotonic()
            if left <= 0:
                raise AssertionError(f"no reply within {timeout} s; adapter stderr: {self.stderr_text()[-400:]}")
            ready, _, _ = select.select([fd], [], [], min(left, 1.0))
            if ready:
                chunk = os.read(fd, 65536)
                if not chunk:
                    raise AssertionError(f"the adapter closed stdout (rc={self.p.poll()}); stderr: {self.stderr_text()[-400:]}")
                self.buf += chunk
        line, self.buf = self.buf.split(b"\n", 1)
        return line.decode()

    def ask(self, op, inp, *, timeout=120):
        self.p.stdin.write((v2_line(op, inp, self.dep) + "\n").encode())
        self.p.stdin.flush()
        r = json.loads(self._readline(timeout))
        assert self.valid.is_valid(r), r                         # every response against the PUBLISHED schema
        return r

    def pid_path(self, i):
        return self.state / f"witness-{i}.pid"

    def stderr_path(self, i):
        return self.state / f"witness-{i}.stderr"

    def pids(self):
        return {i: int(self.pid_path(i).read_text()) for i in range(4) if self.pid_path(i).exists()}

    def wait_started(self, timeout=None):
        timeout = WAIT_S if timeout is None else timeout
        end = time.monotonic() + timeout
        while len(self.pids()) < 4:
            if self.p.poll() is not None:
                raise AssertionError(f"the adapter exited (rc={self.p.returncode}) before spawning four witnesses; stderr: {self.stderr_text()[-400:]}")
            if time.monotonic() > end:
                raise AssertionError("the four pid files did not appear")
            time.sleep(0.1)

    def wait_ready(self, indices=(0, 1, 2, 3), timeout=None):
        timeout = WAIT_S + 30 if timeout is None else timeout
        """A witness child that is still starting (python import, D50 stages 1-8, store open) answers late, not never; this probes each wanted index with a single-witness governance proposal the
        witness REFUSES (it is in no allow-list) until it answers at all. A refusal records nothing and proves the child is serving."""
        self.wait_started(timeout)
        wview, _ = witness_view(self.live)
        end = time.monotonic() + timeout
        pending = list(indices)
        while pending:
            if time.monotonic() > end:
                raise AssertionError(f"witnesses {pending} never answered a probe; adapter stderr: {self.stderr_text()[-300:]}")
            for i in list(pending):
                ts = int(wview.observe("pbc")["timestamp"])
                action = {"action": "1", "root": "0x" + "9d" * 20, "admins": ["0x" + "9e" * 20], "nonce": str(int(wview.governance_nonce()) + 1), "witnessSetVersion": "2",
                          "expiresAt": str(ts + 60), "witnessIndex": str(i)}
                r = self.ask("collect_governance", action)
                assert r["ok"] is False, "a probe the witness should refuse was signed"
                if "did not answer" not in r["error"]["message"]:
                    pending.remove(i)

    def close(self):
        for pid in self.pids().values():
            try:
                os.kill(pid, signal.SIGCONT)                      # a SIGSTOPped child never sees the EOF
            except OSError:
                pass
        if self.p.poll() is None:
            try:
                self.p.stdin.close()
            except OSError:
                pass
            try:
                self.p.wait(timeout=40)
            except subprocess.TimeoutExpired:
                self.p.kill()
                self.p.wait()
        self.rc, self.stderr = self.p.returncode, self.stderr_text()
        for pid in self.pids().values():                          # children must be gone; a straggler of THIS state directory is killed so the next test starts clean
            if not wait_gone(pid, 20):
                cl = cmdline(pid)
                if cl and "hmbc_protocol.witness_main" in cl and str(self.state) in cl:
                    os.kill(pid, signal.SIGKILL)
        try:
            self.p.stdout.close()
        except OSError:
            pass
        self.err.close()


# ---- shared checks --------------------------------------------------------------------------------------------------------------------------------------------
def digest_of(name, message, dep):
    if name == "GovernanceAction":
        return svc._governance_digest(message, dep)
    if name == "GrantReceipt":
        return svc._receipt_digest(message, dep)
    return messages.digest_of(name, message, messages.domain_for(name, message, dep))


def recovered(name, message, sigs, dep):
    d = digest_of(name, message, dep)
    return [eip712.recover(d, s) for s in sigs]


def fresh(live):
    """Both chains must carry the current time in their latest block (an idle automine chain does not): an operator's block producer would do this."""
    mine(live, "pbc")
    mine(live, "dbc")


def check_pool_success(r, member, name, dep, silent=()):
    assert r["ok"] is True, r
    res = r["result"]
    sigs, msg = res["signatures"], res[member]
    addrs = recovered(name, msg, sigs, dep)
    assert len(sigs) == 3 and len(set(addrs)) == 3 and addrs == sorted(addrs), addrs               # exactly three DISTINCT signatures, sorted by recovered address
    witnesses = dep["fixture"]["witnessSet"]["witnesses"]
    assert set(addrs) <= set(witnesses)
    coll = res["collection"]
    assert coll["quorum"] == "3" and coll["witnessSetVersion"] == "2"
    assert [o["witnessIndex"] for o in coll["outcomes"]] == ["0", "1", "2", "3"] and [o["witness"] for o in coll["outcomes"]] == witnesses       # four outcomes in index order
    assert coll["submittedSigners"] == addrs
    for i in silent:
        assert coll["outcomes"][i]["status"] == "silent" and coll["outcomes"][i]["replies"] == "0", coll["outcomes"]
    return res


def check_pool_failure(r, dep, silent=(), status=None):
    assert r["ok"] is False, r
    err = r["error"]
    assert err["code"] == "ADAPTER_UNAVAILABLE" and err.get("reason") == "QUORUM_UNAVAILABLE", err         # classified, never a denial
    coll = err["collection"]
    assert [o["witnessIndex"] for o in coll["outcomes"]] == ["0", "1", "2", "3"] and coll["submittedSigners"] == []
    for i in silent:
        assert coll["outcomes"][i]["status"] == "silent" and coll["outcomes"][i]["replies"] == "0", coll["outcomes"]
    if status is not None:
        assert [o["status"] for o in coll["outcomes"]] == status, coll["outcomes"]
    return err


def accept(live, res):
    led = f_ledger(live)
    wview, _ = witness_view(live)
    led.dbc.send(ANVIL_KEY0, led.KSSC, "acceptState", res["checkpoint"], res["signatures"])
    assert wview.dbc_current_checkpoint()["sequence"] == res["checkpoint"]["sequence"]


# ---- (1) start-up, ownership, files, a pool checkpoint the REAL KSSC accepts ------------------------------------------------------------------------------
def test_the_adapter_spawns_four_supervised_witnesses_and_a_pool_checkpoint_is_accepted_by_the_real_kssc(live_f, tmp_path):
    with Adapter(live_f, tmp_path) as a:
        a.wait_ready()
        pids = a.pids()
        assert set(pids) == {0, 1, 2, 3}
        for i, pid in pids.items():
            pf = a.pid_path(i)
            assert re.fullmatch(r"[0-9]+\n", pf.read_text()) and stat.S_IMODE(os.stat(pf).st_mode) == 0o600
            assert not (a.state / f"witness-{i}" / "pid").exists() and list((a.state / f"witness-{i}").glob("*.pid")) == []       # the pid file is NOT inside the store directory
            cl = cmdline(pid)
            assert "hmbc_protocol.witness_main" in cl and cl[cl.index("--index") + 1] == str(i) and cl[cl.index("--key-label") + 1] == f"witness-{i + 1}", cl
            assert alive(pid) and proc_stat(pid)[1] == a.p.pid                                  # a live child of THE ADAPTER
            ef = a.stderr_path(i)
            assert ef.is_file() and stat.S_IMODE(os.stat(ef).st_mode) == 0o600 and ef.stat().st_size <= 4096
        fresh(live_f)
        t0 = time.monotonic()
        r = a.ask("collect_checkpoint", {})
        observe("pool-checkpoint", seconds=round(time.monotonic() - t0, 2), statuses=[o["status"] for o in r["result"]["collection"]["outcomes"]] if r["ok"] else None)
        res = check_pool_success(r, "checkpoint", "StateCheckpoint", live_f.dep)
        accept(live_f, res)                                                                       # three REAL signatures from four REAL processes, accepted by the REAL contract
    assert a.rc == 0 and a.stderr == ""                                                          # E semantics: empty adapter stderr on a clean run
    assert witness_procs(a.state) == []                                                          # every child ended with the adapter
    assert all(a.pid_path(i).exists() for i in range(4))                                         # the pid files stay


# ---- (2) decision, receipt and governance on the real ledger, through the adapter ---------------------------------------------------------------------------
def test_decision_and_receipt_collected_through_the_adapter_are_accepted_by_the_real_acsc_and_psc(live_flow, tmp_path):
    import ledger_setup as setup
    from hmbc_protocol.client import UserClient
    from hmbc_protocol.relay import Relay
    live = live_flow
    led = f_ledger(live)
    ctx = setup.setup_pbc(led)                                                                   # users and credentials first: the TTL below starts after the adapter is ready
    with Adapter(live, tmp_path) as a:
        a.wait_ready()
        client, relay = UserClient("alice", live.dep), Relay(led, "relay")
        t_start = time.monotonic()
        signed = client.sign_request(setup.make_request(led, ctx, client, nonce="1", ttl=30))
        assert relay.forward(signed, ctx.bundle).code == "NONE"                                  # the real PSC allowed and forwarded
        fresh(live)
        accept(live, check_pool_success(a.ask("collect_checkpoint", {}), "checkpoint", "StateCheckpoint", live.dep))
        digest = signed["requestDigest"]
        r = a.ask("collect_decision", {"requestDigest": digest})
        res = check_pool_success(r, "decision", "AccessDecision", live.dep)
        assert res["decision"]["result"] == "1" and res["credentialRecords"]                    # real credentials, real policy: ALLOW
        cert = {"decision": res["decision"], "signatures": res["signatures"]}
        led.dbc.send(setup.key("relay"), led.ACSC, "consumeDecision", signed["request"], cert, res["credentialRecords"])    # the real ACSC verifies the certificate
        observe("decision-flow", seconds_from_request_to_consume=round(time.monotonic() - t_start, 2))
        grant_id = "0x" + eip712.grant_id(bytes.fromhex(digest[2:]), led.KSSC.address, led.dbc.chain_id).hex()
        assert led.dbc.call(led.KSSC, "getGrant", grant_id)[5] is True
        mine(live, "dbc")
        r = a.ask("attest_grant", {"grantId": grant_id})
        rres = check_pool_success(r, "receipt", "GrantReceipt", live.dep)
        assert rres["receipt"]["requestDigest"] == digest and rres["receipt"]["grantId"] == grant_id
        led.pbc.send(setup.key("relay"), led.PSC, "reportAttestedOutcome", digest, "0x" + "5e" * 32, rres["receipt"], rres["signatures"])       # the real PSC verifies the receipt certificate
        assert led.pbc.call(led.PSC, "getRequest", digest)["status"] == "2"
    assert a.rc == 0 and a.stderr == ""


def test_governance_through_the_adapter_needs_the_local_approval_list_and_the_real_contract_executes_it(live_f, tmp_path):
    led = f_ledger(live_f)
    wview, _ = witness_view(live_f)
    approved_root, admin, other_root = "0x" + "e5" * 20, "0x" + "f6" * 20, "0x" + "c7" * 20

    def action(root):
        mine(live_f, "pbc")
        return {"action": "1", "root": root, "admins": [admin], "nonce": str(int(wview.governance_nonce()) + 1), "witnessSetVersion": "2", "expiresAt": str(int(wview.observe("pbc")["timestamp"]) + 60)}

    with Adapter(live_f, tmp_path, name="gov", state="gov", allow=[["1", approved_root, [admin]]]) as a:                  # --allow-governance FILE (TEST-ONLY, P2)
        a.wait_ready()
        act = action(approved_root)
        res = check_pool_success(a.ask("collect_governance", act), "governanceAction", "GovernanceAction", live_f.dep)
        assert res["governanceAction"] == act
        assert wview.is_authority(approved_root) is False
        led.pbc.send(ANVIL_KEY0, led.Governance, "execute", act, res["signatures"])
        assert wview.is_authority(approved_root) is True                                          # the real Governance contract executed what the witnesses certified
        r = a.ask("collect_governance", action(other_root))                                       # an action NOT in the allow-list: every witness refuses
        err = check_pool_failure(r, live_f.dep)
        assert [o["status"] for o in err["collection"]["outcomes"]] == ["refused"] * 4 and {o["code"] for o in err["collection"]["outcomes"]} == {"POLICY_DENIED"}
    assert a.rc == 0 and a.stderr == ""
    with Adapter(live_f, tmp_path, name="nogov", state="nogov") as b:                              # WITHOUT --allow-governance: no witness signs any governance action
        b.wait_ready()
        err = check_pool_failure(b.ask("collect_governance", action("0x" + "d8" * 20)), live_f.dep)
        assert [o["status"] for o in err["collection"]["outcomes"]] == ["refused"] * 4 and {o["code"] for o in err["collection"]["outcomes"]} == {"POLICY_DENIED"}
    assert b.rc == 0 and b.stderr == ""


# ---- `silent` is not "faulty" -----------------------------------------------------------------------------------------------------------------------------
def test_silent_in_a_pool_result_means_not_heard_before_quorum_and_occurs_in_healthy_runs_too(live_f, tmp_path):
    """CHARACTERIZATION (found while writing the FL-2 test): the pool ENDS as soon as three matching signatures arrive ("an early success takes no snapshot", witness_pool.py), and a witness not heard
    from by then is reported `silent` (zero replies RECEIVED). So with four healthy witnesses the unheard one is `silent` without any fault. A runner or oracle must not read `silent` as "stopped"."""
    seen = []
    with Adapter(live_f, tmp_path) as a:
        a.wait_ready()
        for _ in range(5):
            fresh(live_f)
            res = check_pool_success(a.ask("collect_checkpoint", {}), "checkpoint", "StateCheckpoint", live_f.dep)
            statuses = [o["status"] for o in res["collection"]["outcomes"]]
            assert set(statuses) <= {"signed", "silent"} and statuses.count("signed") >= 3, statuses           # no fault was injected: only `signed` and `silent` occur
            seen.append(statuses)
            accept(live_f, res)
    observe("healthy-statuses", runs=seen, silent_without_any_fault=any("silent" in s for s in seen))
    assert a.rc == 0 and a.stderr == ""


# ---- (3) FL-2: one stopped witness --------------------------------------------------------------------------------------------------------------------------
def test_fl2_one_stopped_witness_leaves_three_honest_signatures_and_is_reported_silent(live_f, tmp_path):
    with Adapter(live_f, tmp_path) as a:
        a.wait_ready()
        pid = a.pids()[1]
        os.kill(pid, signal.SIGSTOP)
        try:
            deadline = time.monotonic() + 5
            while proc_stat(pid)[0] != "T" and time.monotonic() < deadline:
                time.sleep(0.05)
            assert proc_stat(pid)[0] == "T"                                                       # alive but stopped
            fresh(live_f)
            t0 = time.monotonic()
            r = a.ask("collect_checkpoint", {})
            dt = time.monotonic() - t0
            observe("fl2-one-stopped", seconds=round(dt, 2), statuses=[o["status"] for o in r["result"]["collection"]["outcomes"]] if r["ok"] else None)
            res = check_pool_success(r, "checkpoint", "StateCheckpoint", live_f.dep, silent=(1,))
            assert dt < CAP_BOUND_S
            accept(live_f, res)
        finally:
            os.kill(pid, signal.SIGCONT)
        assert alive(pid) and a.pids()[1] == pid                                                  # continued, not respawned
    assert a.rc == 0 and a.stderr == ""


# ---- (4) FL-3: two unavailable witnesses ----------------------------------------------------------------------------------------------------------------------
def test_fl3_two_stopped_witnesses_end_as_a_classified_quorum_unavailable_within_the_cap_never_a_denial(live_f, tmp_path):
    with Adapter(live_f, tmp_path) as a:
        a.wait_ready()
        pids = a.pids()
        stopped = (0, 3)
        for i in stopped:
            os.kill(pids[i], signal.SIGSTOP)
        try:
            fresh(live_f)
            t0 = time.monotonic()
            r = a.ask("collect_checkpoint", {}, timeout=60)
            dt = time.monotonic() - t0
            err = check_pool_failure(r, live_f.dep, silent=stopped)
            statuses = [o["status"] for o in err["collection"]["outcomes"]]
            observe("fl3-two-stopped", seconds=round(dt, 2), cap_s=CAP_S, statuses=statuses, message=err["message"])
            assert statuses[1] == statuses[2] == "signed", statuses                               # the two live witnesses did sign: only the quorum is missing
            assert dt < CAP_BOUND_S, dt
        finally:
            for i in stopped:
                os.kill(pids[i], signal.SIGCONT)
    assert a.rc == 0 and a.stderr == ""


def test_fl3_killed_witnesses_stay_dead_their_pid_files_stay_and_there_is_no_respawn(live_f, tmp_path):
    with Adapter(live_f, tmp_path) as a:
        a.wait_ready()
        pids = a.pids()
        os.kill(pids[2], signal.SIGKILL)
        assert wait_gone(pids[2], 10)
        fresh(live_f)
        res = check_pool_success(a.ask("collect_checkpoint", {}), "checkpoint", "StateCheckpoint", live_f.dep, silent=(2,))      # one dead witness: still three signatures
        accept(live_f, res)
        os.kill(pids[0], signal.SIGKILL)
        assert wait_gone(pids[0], 10)
        fresh(live_f)
        t0 = time.monotonic()
        err = check_pool_failure(a.ask("collect_checkpoint", {}, timeout=60), live_f.dep, silent=(0, 2))                      # two dead: classified QUORUM_UNAVAILABLE
        observe("fl3-two-killed", seconds=round(time.monotonic() - t0, 2), statuses=[o["status"] for o in err["collection"]["outcomes"]])
        end = time.monotonic() + 6                                                                # a bounded window in which an automatic respawn would show
        while time.monotonic() < end:
            assert not alive(pids[0]) and not alive(pids[2])
            assert len(witness_procs(a.state)) == 2                                               # exactly the two survivors
            time.sleep(0.5)
        assert a.pids() == pids and all(a.pid_path(i).exists() for i in range(4))                 # pid files unchanged and left in place
    assert a.rc == 0 and a.stderr == ""


# ---- (5) single-witness mode (hook H2) ------------------------------------------------------------------------------------------------------------------------
def test_single_witness_mode_returns_exactly_one_signature_and_no_collection(live_f, tmp_path):
    with Adapter(live_f, tmp_path) as a:
        a.wait_ready()
        fresh(live_f)
        r = a.ask("collect_checkpoint", {"witnessIndex": "2"})
        assert r["ok"] is True, r
        res = r["result"]
        assert "collection" not in res and len(res["signatures"]) == 1
        assert recovered("StateCheckpoint", res["checkpoint"], res["signatures"], live_f.dep) == [live_f.dep["fixture"]["witnessSet"]["witnesses"][2]]
    assert a.rc == 0 and a.stderr == ""


# ---- (6) the adapter dies, the children follow, a restart keeps the durable pin ------------------------------------------------------------------------
def test_killing_the_adapter_ends_all_children_and_a_restart_on_the_same_state_keeps_the_durable_pin(live_f, tmp_path):
    witnesses = live_f.dep["fixture"]["witnessSet"]["witnesses"]
    a1 = Adapter(live_f, tmp_path, name="r1")
    try:
        a1.wait_ready()
        fresh(live_f)
        r = a1.ask("collect_checkpoint", {"witnessIndex": "1"})                                   # witness 1 signs value A, durably, and nothing is accepted
        assert r["ok"] is True, r
        value_a, sig_a = r["result"]["checkpoint"], r["result"]["signatures"][0]
        old = a1.pids()
        a1.p.kill()
        a1.p.wait()
        t0 = time.monotonic()
        assert all(wait_gone(pid, 30) for pid in old.values()), [alive(p) for p in old.values()]       # stdin EOF ended every child although nobody closed them
        observe("adapter-sigkill", seconds_until_all_children_gone=round(time.monotonic() - t0, 2))
        assert a1.pids() == old and all(a1.pid_path(i).exists() for i in range(4))               # the pid files remain
    finally:
        a1.close()
    assert witness_procs(a1.state) == []
    with Adapter(live_f, tmp_path, name="r2") as a2:                                              # the SAME command on the SAME state directory
        a2.wait_ready()
        assert set(a2.pids()) == {0, 1, 2, 3} and all(a2.pids()[i] != old[i] for i in range(4))       # four NEW processes, the pid files replaced
        fresh(live_f)                                                                             # the next proposal is a different value B for the same sequence
        r2 = a2.ask("collect_checkpoint", {"witnessIndex": "1"})
        assert r2["ok"] is False and r2["error"]["code"] == "STALE_STATE" and r2["error"].get("reason") == "CONFLICT_PINNED", r2
        rec = r2["error"]["recorded"]
        assert rec["message"] == value_a and rec["signature"] == sig_a                            # the restarted witness answers with the RECORDED value A
        assert recovered("StateCheckpoint", rec["message"], [rec["signature"]], live_f.dep) == [witnesses[1]]
        r3 = a2.ask("collect_checkpoint", {})                                                     # and the pool still serves: the other three certify B
        res = check_pool_success(r3, "checkpoint", "StateCheckpoint", live_f.dep)
        observe("restart-pool", statuses=[o["status"] for o in res["collection"]["outcomes"]], pinned_witness_signed=res["collection"]["outcomes"][1]["status"] == "signed")
        accept(live_f, res)
    assert a2.rc == 0 and a2.stderr == ""


# ---- (7) a child that cannot start ----------------------------------------------------------------------------------------------------------------------------
def test_a_witness_that_cannot_start_is_silent_the_adapter_still_serves_and_its_stderr_file_names_why(live_f, tmp_path):
    with Adapter(live_f, tmp_path, name="s1") as a1:
        a1.wait_ready()
    assert a1.rc == 0
    db = a1.state / "witness-1" / "signing.sqlite"
    for side in ("-wal", "-shm"):
        if os.path.exists(str(db) + side):
            os.remove(str(db) + side)
    db.write_bytes(b"this is not a database " * 200)                                              # honest corruption: the store must refuse it, not repair it
    with Adapter(live_f, tmp_path, name="s2") as a2:
        a2.wait_ready(indices=(0, 2, 3))                                                           # the adapter STARTED and serves; witness 1 never will
        pid1 = a2.pids()[1]
        assert wait_gone(pid1, 30)                                                                # its child exited
        fresh(live_f)
        res = check_pool_success(a2.ask("collect_checkpoint", {}), "checkpoint", "StateCheckpoint", live_f.dep, silent=(1,))
        accept(live_f, res)
        end = time.monotonic() + 15
        text = ""
        while time.monotonic() < end and not text.strip():
            text = open(a2.stderr_path(1)).read()
            time.sleep(0.1)
        lines = [ln for ln in text.splitlines() if ln.strip()]
        assert len(lines) == 1 and "Traceback" not in text and len(text.encode()) <= 4096, text    # the single closed JSON refusal line, bounded
        obj = json.loads(lines[0])
        assert set(obj) == {"error"} and obj["error"]["code"] == "ADAPTER_UNAVAILABLE" and obj["error"]["reason"] == "STORE_CORRUPT", obj
        assert a2.pid_path(1).exists() and not alive(pid1)                                        # the pid file of a dead witness stays
        observe("child-cannot-start", stderr_line=lines[0][:200])
    assert a2.rc == 0 and a2.stderr == ""                                                         # the adapter's own stderr stays empty


# ---- (8) a refused startup spawns nothing ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("what", ["schema", "allow-governance"])
def test_a_refused_startup_spawns_no_witness_and_writes_no_pid_file(live_f, tmp_path, what):
    dep_file = tmp_path / "dep.json"
    dep_file.write_text(json.dumps(live_f.dep))
    state = tmp_path / "state"
    schema, sha, extra = SCHEMA, SCHEMA_SHA, []
    if what == "schema":
        bad = tmp_path / "schema.json"
        bad.write_bytes(b"[]")
        schema, sha = str(bad), hashlib.sha256(b"[]").hexdigest()
    else:
        bad = tmp_path / "allow.json"
        bad.write_bytes(b"{}")
        extra = ["--allow-governance", str(bad)]
    p = subprocess.run([sys.executable, "-B", "-m", "hmbc_protocol.adapter_v2_main", "--deployment", str(dep_file), "--abi-dir", live_f.abi_dir, "--schema", schema, "--schema-sha256", sha,
                        "--schema-revision", "v2", "--state-dir", str(state), *extra], input="", capture_output=True, text=True, cwd=PROTO, env={"PYTHONPATH": PROTO, "PATH": "/usr/bin:/bin"}, timeout=120)
    assert p.returncode == 2 and p.stdout == "" and "Traceback" not in p.stderr, (p.returncode, p.stderr[-300:])
    lines = p.stderr.strip().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["error"]["code"] == "MALFORMED"
    assert not state.exists() and witness_procs(state) == []                                      # no state, no pid file, no child


# ---- (9) the carried E successor deployment: no witnesses at all ---------------------------------------------------------------------------------------------
def test_the_e_successor_deployment_spawns_no_witness_and_the_witness_operations_stay_unwired(live_e, tmp_path):
    with Adapter(live_e, tmp_path, revision="v2.1") as a:
        r = a.ask("collect_checkpoint", {})                                                       # the first line also proves the adapter is serving
        time.sleep(2)                                                                             # a supervisor, if there were one, would have spawned by now
        assert list(a.state.glob("witness-*.pid")) == [] and list(a.state.glob("witness-*.stderr")) == []
        assert witness_procs(a.state) == []
        assert not [n for n in os.listdir("/proc") if n.isdigit() and (proc_stat(int(n)) or ("", -1))[1] == a.p.pid]       # the adapter has no child process at all
        observe("e-profile-witness-op", ok=r["ok"], code=r["error"]["code"] if not r["ok"] else None, message=r["error"]["message"] if not r["ok"] else None)
        assert r["ok"] is False and r["error"]["code"] == "ADAPTER_UNAVAILABLE" and "not wired" in r["error"]["message"], r
    assert a.rc == 0 and a.stderr == ""


def test_the_e_profile_answer_is_not_wired_in_this_process_because_no_witness_handler_is_installed(live_e, tmp_path):
    """Fork G finding F3, resolved by correcting the documentation (the code was right): for the carried E successor deployment no witness handler exists, so the message is the generic one."""
    with Adapter(live_e, tmp_path, name="emsg", state="emsg", revision="v2.1") as a:
        r = a.ask("collect_checkpoint", {})
        assert r["ok"] is False and r["error"]["code"] == "ADAPTER_UNAVAILABLE" and "is not wired in this process" in r["error"]["message"], r["error"]


def test_zz_no_witness_process_of_these_tests_is_left_behind():
    """Defined last, so it runs last in a file run: every witness child the module started is gone."""
    assert witness_procs() == [], witness_procs()
