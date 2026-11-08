"""LIVE tests of the process transport (agent 2, F task 3, Step 2): FOUR REAL `witness_main` processes, started by `WitnessSupervisor.for_deployment`, against two real Anvil nodes and agent 1's real F
ledger (commit 85c59f5, the deployment of test_rpc_binding_view_live.py, whose helpers this file reuses). The pool collects through the real transport and the real contracts check what comes out.

What this shows: q = 3 of 4 over real pipes with a host-monotonic clock; three signatures from separate processes accepted by the real KSSC; the pid files name the real witness processes; two stopped
witnesses give a classified timeout that really takes the pool's time (no fast-forward); one killed witness still leaves a q = 3 certificate; a SIGKILLed witness restarted by a FRESH supervisor keeps
its durable pin (CONFLICT_PINNED with the recorded value). What it does NOT show: a second host, power loss, a consensus ledger, witness_main readiness before the first request, anything for the
decision, receipt or governance kinds (the transport is kind-agnostic; those collections are the adapter wiring's tests), or timing under load. Skipped when Foundry or the pinned commit is missing
(READ THE SKIP COUNT: a machine without them still reports green). Single host, synthetic TEST-ONLY keys.
"""
import json
import os
import signal
import time

import pytest

from hmbc_protocol import eip712, messages
from hmbc_protocol import witness_pool as wp
from hmbc_protocol import witness_pool_driver as drv
from hmbc_protocol import witness_process_transport as wpt
from hmbc_protocol import witness_service as svc
from test_rpc_binding_view_live import ANVIL_KEY0, f_ledger, live_f, mine, witness_view  # noqa: F401  (live_f is a fixture)


def supervisor(live, tmp_path, name="state", **kw):
    state = tmp_path / name
    if not state.exists():
        state.mkdir(mode=0o700)
        os.chmod(state, 0o700)
    dep = tmp_path / "dep.json"
    dep.write_text(json.dumps(live.dep))
    return wpt.WitnessSupervisor.for_deployment(manifest=live.dep, deployment_path=str(dep), abi_dir=live.abi_dir, state_dir=str(state), **kw)


def collection(live, wview, proposal):
    return wp.Collection(witnesses=live.dep["fixture"]["witnessSet"]["witnesses"], recover=wp.make_recover("StateCheckpoint", live.dep), proposal=proposal,
                         ledger_now_at_start=int(wview.observe("dbc")["timestamp"]), proposal_expires_at=int(proposal["expiresAt"]), adoption=True, witness_set_version="2")


def pid_of(sup, i):
    return int(open(sup.pid_path(i)).read())


def signer(cp, sig, live):
    return eip712.recover(messages.digest_of("StateCheckpoint", cp, messages.domain_for("StateCheckpoint", cp, live.dep)), sig)


def test_four_real_witness_processes_collect_a_checkpoint_with_q3_and_the_real_kssc_accepts_it(live_f, tmp_path):
    led, (wview, _) = f_ledger(live_f), witness_view(live_f)
    with supervisor(live_f, tmp_path) as sup:
        for i in range(4):                                                         # the pid file names the real witness process of that index
            cmd = open(f"/proc/{pid_of(sup, i)}/cmdline", "rb").read().split(b"\0")
            assert b"hmbc_protocol.witness_main" in cmd and cmd[cmd.index(b"--index") + 1] == str(i).encode() and cmd[cmd.index(b"--key-label") + 1] == f"witness-{i + 1}".encode()
        mine(live_f, "dbc")
        cp = svc.derive_checkpoint(wview, live_f.dep)
        coll = collection(live_f, wview, cp)
        result = drv.run_collection(coll, sup.transport_factory("checkpoint"))
        assert result["ok"] is True and result["message"] == cp, result
        sigs = result["signatures"]
        assert len(sigs) == 3 and len({signer(cp, s, live_f) for s in sigs}) == 3
        assert result["collection"]["submittedSigners"] == sorted(signer(cp, s, live_f) for s in sigs)
        assert [o["witnessIndex"] for o in result["collection"]["outcomes"]] == ["0", "1", "2", "3"]
        led.dbc.send(ANVIL_KEY0, led.KSSC, "acceptState", cp, sigs)                # three separate processes, three real signatures, one real contract
        assert wview.dbc_current_checkpoint()["sequence"] == cp["sequence"]
        assert all(s["alive"] for s in sup.status())
        state = tmp_path / "state"                                                 # the pid and stderr files sit NEXT TO the real stores, which are directories made by the witnesses themselves
        assert sorted(os.listdir(state)) == sorted([f"witness-{i}{ext}" for i in range(4) for ext in (".pid", ".stderr", "")])
        for i in range(4):
            assert os.path.isdir(state / f"witness-{i}") and not os.path.isdir(sup.pid_path(i)) and not os.path.isdir(sup.stderr_path(i))
            assert (os.stat(sup.stderr_path(i)).st_mode & 0o777) == 0o600
            assert open(sup.stderr_path(i), "rb").read() == b""                    # a healthy witness_main writes nothing to stderr
        assert [s["stderrFirstLine"] for s in sup.status()] == [""] * 4


def test_two_stopped_witnesses_give_a_classified_timeout_that_really_takes_the_pools_time(live_f, tmp_path):
    wview, _ = witness_view(live_f)
    pids = []
    with supervisor(live_f, tmp_path, close_grace_s=0.5) as sup:
        try:
            for i in (2, 3):                                                       # found through the pid files, as a runner would
                pids.append(pid_of(sup, i))
                os.kill(pids[-1], signal.SIGSTOP)
            mine(live_f, "dbc")
            cp = svc.derive_checkpoint(wview, live_f.dep)
            coll = collection(live_f, wview, cp)
            t0 = time.monotonic()
            result = drv.run_collection(coll, sup.transport_factory("checkpoint"))
            real_s = time.monotonic() - t0
            assert result["ok"] is False
            by = {o["witnessIndex"]: o["status"] for o in result["collection"]["outcomes"]}
            assert by == {"0": "signed", "1": "signed", "2": "silent", "3": "silent"}, by
            assert result["collection"]["submittedSigners"] == []
            assert coll.finished_at_ms >= 5000                                     # the pool's reply timeout had to pass
            assert real_s >= coll.finished_at_ms / 1000 - 0.3                      # and it passed in REAL time: nothing was fast-forwarded
            assert all(s["alive"] for s in sup.status())                           # stopped is not dead
        finally:
            for pid in pids:
                os.kill(pid, signal.SIGCONT)


def test_one_killed_witness_leaves_three_signers_and_the_certificate_is_still_accepted(live_f, tmp_path):
    led, (wview, _) = f_ledger(live_f), witness_view(live_f)
    with supervisor(live_f, tmp_path) as sup:
        os.kill(pid_of(sup, 3), signal.SIGKILL)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and sup.status()[3]["alive"]:
            time.sleep(0.05)
        assert sup.status()[3]["alive"] is False and sup.status()[3]["returncode"] == -signal.SIGKILL
        mine(live_f, "dbc")
        cp = svc.derive_checkpoint(wview, live_f.dep)
        result = drv.run_collection(collection(live_f, wview, cp), sup.transport_factory("checkpoint"))
        assert result["ok"] is True and len(result["signatures"]) == 3
        assert {o["witnessIndex"]: o["status"] for o in result["collection"]["outcomes"]} == {"0": "signed", "1": "signed", "2": "signed", "3": "silent"}
        assert sorted(signer(cp, s, live_f) for s in result["signatures"]) == sorted(live_f.dep["fixture"]["witnessSet"]["witnesses"][:3])
        led.dbc.send(ANVIL_KEY0, led.KSSC, "acceptState", cp, result["signatures"])
        assert wview.dbc_current_checkpoint()["sequence"] == cp["sequence"]


def test_a_sigkilled_witness_restarted_by_a_fresh_supervisor_keeps_its_durable_pin(live_f, tmp_path):
    wview, chains = witness_view(live_f)
    mine(live_f, "pbc")                                                            # the PBC head must move past the accepted checkpoint's block (as in the single-process live test)
    mine(live_f, "pbc")
    mine(live_f, "dbc")
    a = svc.derive_checkpoint(wview, live_f.dep)
    n = int(a["sourceBlockNumber"])
    b = dict(a, sourceBlockNumber=str(n - 1), sourceBlockHash=chains["pbc"].get_block(n - 1)["hash"])      # a different valid value for the SAME sequence
    sig = {}
    with supervisor(live_f, tmp_path) as first:
        tr = first.transport_factory("checkpoint")
        for w in range(4):
            tr.send(w, 1, a)
        for t, w, rnd, reply in [tr.next_event(20000) for _ in range(4)]:
            assert reply["type"] == "signature" and reply["message"] == a, reply
            sig[w] = reply["signature"]
        pid0 = pid_of(first, 0)
        os.kill(pid0, signal.SIGKILL)                                              # no goodbye: whatever is durable is all there is
    with supervisor(live_f, tmp_path) as second:                                   # a FRESH adapter start on the same state directory
        assert pid_of(second, 0) != pid0 and open(second.pid_path(0)).read() == f"{second.status()[0]['pid']}\n"
        tr = second.transport_factory("checkpoint")
        tr.send(0, 1, b)
        tr.send(1, 1, b)
        got = {w: reply for t, w, rnd, reply in [tr.next_event(20000) for _ in range(2)]}
        for w in (0, 1):
            r = got[w]
            assert r["type"] == "error" and r["code"] == "STALE_STATE" and r["reason"] == "CONFLICT_PINNED", r
            assert r["recorded"] == {"message": a, "signature": sig[w]}, w
        tr.send(0, 1, a)
        again = tr.next_event(20000)
        assert again[3]["type"] == "signature" and again[3]["signature"] == sig[0]  # the same value signs again to the same bytes
