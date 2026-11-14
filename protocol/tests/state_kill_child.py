"""Child process for the RANDOM-SIGKILL durability test (TEST-ONLY; agent 2). Not a test file.

`python -B state_kill_child.py <dir> <mode> <seed> <cfg-json>`; modes: `sign` (open the store, print READY, sign forever), `sign-stage` (open the store with the crash_hook that prints each STAGE line, sign forever: a controlled signing kill), `sign-early-reply` (a deliberately BROKEN control: it prints each reply from inside
the signer callback, i.e. BEFORE the transaction commits, and pauses there to widen the window; the harness must flag it), `init` (print READY, initialise the store once, print DONE),
`sign-pause` (S2-0025: like `sign-stage`, but the hook BLOCKS at the nth occurrence of the named store point given in the cfg `{"pause": {"stage": ..., "nth": ..., "supersede": bool}}`
(with `supersede`, only occurrences inside a transaction that superseded a dead pin count), after printing `PAUSED <stage> <nth> <superseded rows visible inside the open transaction>
<superseded rows committed before it>`; the parent kills it there, so the death lands exactly AT that point on any host; after PAUSE_MAX_REQUESTS requests without reaching it the child
prints END and exits).
The parent kills the process with SIGKILL at a random moment: unlike `state_child.py` (an `os._exit` at a NAMED crash point) the death can land anywhere, including inside SQLite's own writes.
Every reply is one complete line `REPLY <tag> <digest> <signature>` printed only after `sign` returned; a refusal prints `REFUSED <tag> <code>`. The request sequence is a pure function of the
seed (`plan`), so the parent can regenerate exactly what the child asked for."""
import itertools
import json
import os
import random
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..")]
from hmbc_protocol import witness_state as ws  # noqa: E402
from test_witness_state import BIND, DBC, DOM_S, OWNER, B, cp_effect, h, obs, signer  # noqa: E402

KEYS, T0 = 6, 1791521600
PAUSE_MAX_REQUESTS = 60


def plan(seed):
    """Yield (i, key, variant, expires, tag, ts) forever: six keys, two effects each (a second effect for a live key is refused, for a dead key it supersedes), lifetimes of 2, 6 or 100000 seconds
    on a clock that advances 3 s per request (so short-lived digests die), and now and then an exact repeat of an earlier request (the idempotent path)."""
    rng, prev, i = random.Random(seed), [], 0
    while True:
        i += 1
        ts = T0 + 3 * i
        if prev and rng.random() < 0.2:
            _, key, variant, expires, tag, _ = rng.choice(prev)
        else:
            key, variant, expires = str(rng.randint(1, KEYS)), rng.randint(0, 1), ts + rng.choice([2, 6, 100000])
            tag = "%s|%d|%d" % (key, variant, expires)
        req = (i, key, variant, expires, tag, ts)
        prev.append(req)
        yield req


def stage(point):
    print("STAGE", point, flush=True)          # the parent may SIGKILL on reading this: a controlled interruption at a NAMED point (inside a real init_store or signing transaction)


def pausing_hook(holder, stage_name, nth, supersede=False):
    """`sign-pause`: print every STAGE line; at the nth occurrence of `stage_name` print PAUSED and wait for the parent's SIGKILL. The pause is what makes the kill land AT the named point:
    a print-only hook lets the child run on until the signal arrives, so the death lands at a host-dependent later point (A3-0110: K1 then escaped in 11 of 40 runs, A3-0122).
    With `supersede`, an occurrence counts only when the open transaction already holds one more `superseded` row than was committed before it (the request replaces a dead pin)."""
    seen, base = [0], [0]

    def count():
        return holder[0]._con.execute("SELECT COUNT(*) FROM superseded").fetchone()[0]           # the store's own connection: inside an open transaction it sees that transaction's rows

    def hook(point):
        print("STAGE", point, flush=True)
        if point == "after_commit":
            base[0] = count()
        if point == stage_name:
            sup = count()
            if supersede and sup <= base[0]:
                return
            seen[0] += 1
            if seen[0] == nth:
                print("PAUSED", point, nth, sup, base[0], flush=True)
                while True:
                    time.sleep(60)
    return hook


def request(st, req, signer_fn=signer):
    i, key, variant, expires, tag, ts = req
    return st.sign(type="StateCheckpoint", domain=DOM_S, wsv="2", key=key, effect=cp_effect(138 + variant), expires_at=str(expires), digest=h(tag), signer=signer_fn,
                   observe=lambda: obs(DBC, 160 + i, ts))


def main():
    d, mode, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    if mode == "init":
        print("READY", flush=True)
        ws.init_store(d, BIND, B, OWNER, anchor=json.loads(sys.argv[4])["anchor"], crash_hook=stage)
        print("DONE", flush=True)
        return
    if mode == "sign-pause":
        cfg = json.loads(sys.argv[4])["pause"]
        holder = []
        st = ws.open_store(d, BIND, OWNER, crash_hook=pausing_hook(holder, cfg["stage"], int(cfg["nth"]), bool(cfg.get("supersede"))))
        holder.append(st)
        print("READY", flush=True)
        for req in itertools.islice(plan(seed), PAUSE_MAX_REQUESTS):
            try:
                sig = request(st, req)
            except ws.StoreError as e:
                print("REFUSED", req[4], e.code, flush=True)
                continue
            print("REPLY", req[4], h(req[4]), sig, flush=True)
        print("END", flush=True)                   # the named point was never reached (no such point in the store, or nth too large)
        return
    hook = stage if mode == "sign-stage" else None
    st = ws.open_store(d, BIND, OWNER, crash_hook=hook)
    print("READY", flush=True)
    for req in plan(seed):
        tag = req[4]
        if mode == "sign-stage":
            try:
                sig = request(st, req)
            except ws.StoreError as e:
                print("REFUSED", tag, e.code, flush=True)
                continue
            print("REPLY", tag, h(tag), sig, flush=True)
            continue
        if mode == "sign-early-reply":
            def early(digest, tag=tag):
                sig = signer(digest)
                print("REPLY", tag, digest, sig, flush=True)            # BROKEN ON PURPOSE: the reply leaves before the commit
                time.sleep(0.004)
                return sig
            try:
                request(st, req, early)
            except ws.StoreError as e:
                print("REFUSED", tag, e.code, flush=True)
            continue
        try:
            sig = request(st, req)
        except ws.StoreError as e:
            print("REFUSED", tag, e.code, flush=True)
            continue
        print("REPLY", tag, h(tag), sig, flush=True)


if __name__ == "__main__":
    main()
