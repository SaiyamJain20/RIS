"""Random-SIGKILL durability of the witness store (agent 2, F phase). PAPER-DERIVED RECONSTRUCTION; synthetic signer; one host.

The older crash tests stop the process at NAMED points (`os._exit(77)` through the `crash_hook`). This file kills a real child process with SIGKILL at a RANDOM moment, so the death can land
anywhere: inside the database write, between the commit and the reply, in the middle of initialisation. After every death the parent takes the real restart path (`init_store` / `open_store`)
and checks the contract of SIGNING-RULES section 2/6 and SUCCESSOR-WIRE section 5:
  I1 every reply the child had printed (a complete line, printed only after `sign` returned) is in the store with the SAME signature (a reply is never ahead of the commit);
  I2 at most ONE record is committed without its reply (the request in flight when the process died);
  I3 each key is pinned to ONE effect: its live digests all carry the effect of its single `conflict` row;
  I4 the store reopens (integrity check, identity, no fault) and every stored digest re-signs to the SAME signature (the retry replies the recorded value);
  I5 an interrupted initialisation is either completed or refused with a closed reason by the next `init_store`, and the completed store signs.
What this does NOT show: power loss or OS crash (SIGKILL leaves the kernel's page cache intact, so `synchronous=FULL` is not exercised: see run_state_kill_mutants.py, K3), disk errors, or
any property across more than one process at once. Trial counts: HMBC_KILL_TRIALS (default 25 per test); the evidence run used far more."""
import itertools
import json
import os
import random
import signal
import sqlite3
import subprocess
import sys
import time

import pytest

import state_kill_child as kc
from hmbc_protocol import witness_state as ws
from test_witness_state import B, BIND, DBC, OWNER, h, obs

CHILD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state_kill_child.py")
TRIALS = int(os.environ.get("HMBC_KILL_TRIALS", "25"))
ANCHOR = {"pbc": {"number": "18", "hash": h("anchor:pbc")}, "dbc": {"number": "9", "hash": h("anchor:dbc")}}


def spawn(d, mode, seed):
    return subprocess.Popen([sys.executable, "-B", CHILD, d, mode, str(seed), json.dumps({"anchor": ANCHOR})], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def kill_after(p, delay, may_finish=False):
    assert p.stdout.readline().strip() == "READY", p.stderr.read()[-800:]
    time.sleep(delay)
    p.send_signal(signal.SIGKILL)
    out = p.stdout.read()
    err = p.stderr.read()
    p.wait()
    assert p.returncode == -signal.SIGKILL or (may_finish and p.returncode == 0 and "DONE" in out), (p.returncode, err[-800:])            # a short job may end before the kill lands
    assert err == "", err[-800:]            # SIGKILL leaves no traceback: anything on stderr means the child failed on its own first
    return out


def replies_of(out):
    """The COMPLETE reply lines (a line without its newline was cut by the kill and is not a reply) and the refusals."""
    lines = out.split("\n")[:-1]
    reps = {}
    for ln in lines:
        parts = ln.split(" ")
        if parts[0] == "REPLY" and len(parts) == 4:
            reps[parts[2]] = (parts[1], parts[3])
    return reps, [ln for ln in lines if ln.startswith("REFUSED")]


def violations(d, reps, seed, n_lines):
    """Reopen through the real restart path and return a list of contract violations (empty = the contract held). `n_lines` is how many complete lines the child printed: the request that was
    in flight when it died is at most one beyond them."""
    bad = []
    try:
        st = ws.open_store(d, BIND, OWNER)
    except ws.StoreError as e:
        return ["I4 the store did not reopen: %s" % e]
    try:
        con = sqlite3.connect(os.path.join(d, "signing.sqlite"))
        stored = {r[0]: r for r in con.execute("SELECT digest, type, domain, wsv, key, expires_at, signature, observation, sup_seq FROM digests")}
        for dg, (tag, sig) in reps.items():
            if dg not in stored:
                bad.append("I1 a replied digest is missing from the store: %s" % tag)
            elif stored[dg][6] != sig:
                bad.append("I1 a replied digest is stored with another signature: %s" % tag)
        if len(stored) - len(reps) > 1 or len(stored) < len(reps):
            bad.append("I2 %d records stored for %d replies" % (len(stored), len(reps)))
        reqs = {h(r[4]): r for r in itertools.islice(kc.plan(seed), n_lines + 3)}
        conflicts = {r[0]: json.loads(r[1]) for r in con.execute("SELECT key, effect FROM conflict")}
        for dg, row in stored.items():
            if dg not in reqs:
                bad.append("I3 a stored digest was never requested: %s" % dg[:12])
                continue
            req = reqs[dg]
            if row[8] is None and (row[4] not in conflicts or conflicts[row[4]] != kc.cp_effect(138 + req[2])):
                bad.append("I3 key %s is live under an effect other than its pin (variant %d)" % (row[4], req[2]))
        if con.execute("SELECT COUNT(*) FROM fault").fetchone()[0]:
            bad.append("I4 a fault row appeared")
        if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            bad.append("I4 integrity_check failed")
        con.close()
        far = obs(DBC, 10 ** 6, kc.T0 + 10 ** 7)
        for dg, req in ((d_, reqs[d_]) for d_ in stored if d_ in reqs and stored[d_][8] is None):            # a SUPERSEDED digest is refused by design (its effect is no longer the pin)
            try:
                again = st.sign(type="StateCheckpoint", domain=kc.DOM_S, wsv="2", key=req[1], effect=kc.cp_effect(138 + req[2]), expires_at=str(req[3]), digest=dg, signer=kc.signer,
                                observe=lambda: far)
            except ws.StoreError as e:
                bad.append("I4 the stored request %s no longer re-signs: %s" % (req[4], e.reason))
                continue
            if again != stored[dg][6]:
                bad.append("I4 the stored request %s re-signs to another signature" % req[4])
    finally:
        st.close()
    return bad


def run_signing_trials(tmp_path, mode, trials, seed0):
    rng = random.Random(seed0)
    stats = {"trials": 0, "replies": 0, "unreplied": 0, "refusals": 0, "superseded": 0, "bad": []}
    for t in range(trials):
        d = str(tmp_path / ("w%d" % t))
        ws.init_store(d, BIND, B, OWNER).close()
        seed = seed0 * 1000 + t
        out = kill_after(spawn(d, mode, seed), rng.uniform(0.005, 0.15))
        reps, refused = replies_of(out)
        bad = violations(d, reps, seed, len(out.split("\n")) - 1)
        con = sqlite3.connect(os.path.join(d, "signing.sqlite"))
        n_digests = con.execute("SELECT COUNT(*) FROM digests").fetchone()[0]
        stats["superseded"] += con.execute("SELECT COUNT(*) FROM superseded").fetchone()[0]
        con.close()
        stats["trials"] += 1
        stats["replies"] += len(reps)
        stats["unreplied"] += n_digests - len(reps)
        stats["refusals"] += len(refused)
        stats["bad"] += ["trial %d (seed %d): %s" % (t, seed, b) for b in bad]
    return stats


def test_random_sigkill_during_signing_never_loses_a_reply(tmp_path):
    stats = run_signing_trials(tmp_path, "sign", TRIALS, 1)
    assert stats["bad"] == []
    assert stats["replies"] >= TRIALS, "the harness barely exercised signing: %r" % stats            # a vacuous pass (the child dying at once) must fail


def test_random_sigkill_during_initialisation_leaves_a_recoverable_directory(tmp_path):
    rng, done, interrupted = random.Random(2), 0, 0
    for t in range(TRIALS):
        d = str(tmp_path / ("i%d" % t))
        out = kill_after(spawn(d, "init", t), rng.uniform(0.0, 0.05), may_finish=True)
        done += "DONE" in out
        interrupted += "DONE" not in out
        try:
            st = ws.init_store(d, BIND, B, OWNER, anchor=ANCHOR)           # the restart: completes an interrupted initialisation or opens a finished one
        except ws.StoreError as e:
            pytest.fail("trial %d: the next init_store refused a directory the kill left behind: %s" % (t, e))
        assert (st.binding_v2, st.owner, st.document, st.anchor) == (BIND, OWNER, B, ANCHOR)
        st.sign(type="StateCheckpoint", domain=kc.DOM_S, wsv="2", key="1", effect=kc.cp_effect(138), expires_at="1791600000", digest=h("after-init-%d" % t), signer=kc.signer,
                observe=lambda: obs(DBC, 160, kc.T0))
        st.close()
    assert interrupted >= 1, "no kill landed inside initialisation: the harness did not test it (%d finished before the kill)" % done


def test_the_harness_flags_a_reply_that_leaves_before_the_commit(tmp_path):
    """Positive control: a child that replies from inside the transaction (a deliberately broken ordering) must be caught. If this passes without a violation the harness is blind."""
    stats = run_signing_trials(tmp_path, "sign-early-reply", 40, 3)
    assert any(b.split(": ", 1)[1].startswith("I1 a replied digest is missing") for b in stats["bad"]), stats
