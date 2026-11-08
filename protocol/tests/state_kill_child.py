"""Child process for the RANDOM-SIGKILL durability test (TEST-ONLY; agent 2). Not a test file.

`python -B state_kill_child.py <dir> <mode> <seed> <cfg-json>`; modes: `sign` (open the store, print READY, sign forever), `sign-early-reply` (a deliberately BROKEN control: it prints each reply from inside
the signer callback, i.e. BEFORE the transaction commits, and pauses there to widen the window; the harness must flag it), `init` (print READY, initialise the store once, print DONE).
The parent kills the process with SIGKILL at a random moment: unlike `state_child.py` (an `os._exit` at a NAMED crash point) the death can land anywhere, including inside SQLite's own writes.
Every reply is one complete line `REPLY <tag> <digest> <signature>` printed only after `sign` returned; a refusal prints `REFUSED <tag> <code>`. The request sequence is a pure function of the
seed (`plan`), so the parent can regenerate exactly what the child asked for."""
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


def request(st, req, signer_fn=signer):
    i, key, variant, expires, tag, ts = req
    return st.sign(type="StateCheckpoint", domain=DOM_S, wsv="2", key=key, effect=cp_effect(138 + variant), expires_at=str(expires), digest=h(tag), signer=signer_fn,
                   observe=lambda: obs(DBC, 160 + i, ts))


def main():
    d, mode, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    if mode == "init":
        print("READY", flush=True)
        ws.init_store(d, BIND, B, OWNER, anchor=json.loads(sys.argv[4])["anchor"])
        print("DONE", flush=True)
        return
    st = ws.open_store(d, BIND, OWNER)
    print("READY", flush=True)
    for req in plan(seed):
        tag = req[4]
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
