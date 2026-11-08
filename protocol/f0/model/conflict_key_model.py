"""Bounded explicit-state check of ONE witness conflict key (agent 2, F0 planning evidence).

Design check only: NOT agent 3's TLA+ model, NOT the protocol implementation, NOT a consensus or cryptographic claim.
Expectations: PREDICTIONS.md (hashed before the first run). Standard library only; run with `python3 -I conflict_key_model.py`.

State: ledger clock t; per honest witness (durable signed-digest bitmask, last observation o) plus an APPEND-ONLY emitted-signature
bitmask. A signature once emitted stays valid forever, so certificates are counted from `emitted`; only the durable bitmask can be
wiped by the rollback control (revision 2: run 1 counted the durable mask and so wrongly erased emitted signatures, see
evidence/model-run1-initial.json). Byzantine witnesses are worst case (they have signed every digest). A certificate for digest d is
formed when (#honest who emitted d) + n_byz >= q, and live while t < expiry(d).
Invariant I1: no reachable state has two formed AND live certificates carrying different values.
"""
from __future__ import annotations

import json
import sys
from collections import deque
from dataclasses import dataclass

VALUES = ("A", "B")


@dataclass(frozen=True)
class Cfg:
    name: str
    rule: str                 # N0 | N1 | R-new | N2
    n: int = 4
    f: int = 1                # Byzantine witnesses (worst case: signed everything)
    q: int = 3
    horizon: int = 5          # ledger clock runs 0..horizon
    expiries: tuple = (2, 4)
    skew: int = 0             # N2 only: how far a local clock may run ahead of the ledger clock
    rollback: bool = False    # one honest durable record may be wiped (assumption violation control)
    regress: bool = False     # the ledger clock may move backwards once (assumption violation control)


def digests(cfg: Cfg):
    return [(v, e) for v in VALUES for e in cfg.expiries]


def allowed(cfg: Cfg, signed: int, d_idx: int, o: int, ds) -> bool:
    v, e = ds[d_idx]
    if cfg.rule == "N0":
        return True
    if cfg.rule == "N1":
        return all(ds[i][0] == v for i in range(len(ds)) if signed >> i & 1)
    if o >= e:                                   # the witness itself already observes the digest as expired: signing it is useless
        return False
    # R-new and N2: a different-value digest must be dead at the observation o
    return all(ds[i][0] == v or ds[i][1] <= o for i in range(len(ds)) if signed >> i & 1)


def violated(cfg: Cfg, t: int, emitted, ds) -> bool:
    live_values = set()
    for i, (v, e) in enumerate(ds):
        cnt = cfg.f + sum(1 for m in emitted if m >> i & 1)
        if cnt >= cfg.q and e > t:
            live_values.add(v)
    return len(live_values) > 1


def explore(cfg: Cfg, collect_prefix_upto: int | None = None):
    ds = digests(cfg)
    n_h = cfg.n - cfg.f
    start = (0, (0,) * n_h, (0,) * n_h, (0,) * n_h, 0)   # t, durable masks, obs, emitted masks, regressed/rolled-back flags
    seen = {start}
    queue = deque([start])
    prefix = []
    while queue:
        t, masks, obs, emitted, used = queue.popleft()
        if violated(cfg, t, emitted, ds):
            return {"violated": True, "states": len(seen), "witnessState": {"t": t, "masks": masks, "obs": obs, "emitted": emitted}, "digests": ds}, prefix
        if collect_prefix_upto is not None and t <= collect_prefix_upto:
            prefix.append((t, masks, obs))
        succ = []
        if t < cfg.horizon:
            succ.append((t + 1, masks, obs, emitted, used))
        if cfg.regress and not used & 1 and t > 0:
            for t2 in range(t):
                succ.append((t2, masks, obs, emitted, used | 1))     # ledger clock moves backwards (assumption violation)
        for w in range(n_h):
            if cfg.rollback and not used & 2 and masks[w]:
                m2 = list(masks); o2 = list(obs); m2[w] = 0; o2[w] = 0
                succ.append((t, tuple(m2), tuple(o2), emitted, used | 2))   # durable record wiped; emitted signatures stay valid
            lo = obs[w]
            hi = t + (cfg.skew if cfg.rule == "N2" else 0)
            for o in range(lo, hi + 1):
                for di in range(len(ds)):
                    if masks[w] >> di & 1 and cfg.rule != "N0":
                        continue
                    if not allowed(cfg, masks[w], di, o, ds):
                        continue
                    m2 = list(masks); o2 = list(obs); e2 = list(emitted); m2[w] |= 1 << di; o2[w] = o; e2[w] |= 1 << di
                    succ.append((t, tuple(m2), tuple(o2), tuple(e2), used))
        for s in succ:
            if s not in seen:
                seen.add(s)
                queue.append(s)
    return {"violated": False, "states": len(seen), "digests": ds}, prefix


def recovery_check(cfg: Cfg, prefix) -> dict:
    """From every reachable prefix state (t <= 3), can the honest witnesses later agree on a fresh digest?

    All old digests are dead at t = 5 (expiries 2, 4); a fresh digest has expiry 6. They need a common value for which every honest
    witness's rule still allows signing at observation o = 5. A state where no value works is a stall.
    """
    ds = digests(cfg)
    n_h = cfg.n - cfg.f
    fresh_e, o_now = max(cfg.expiries) + 2, max(cfg.expiries) + 1
    stalled = None
    ok = 0
    for t, masks, obs in prefix:
        recoverable = False
        for v in VALUES:
            good = True
            for w in range(n_h):
                if cfg.rule == "N1":
                    good = good and all(ds[i][0] == v for i in range(len(ds)) if masks[w] >> i & 1)
                else:
                    good = good and all(ds[i][0] == v or ds[i][1] <= o_now for i in range(len(ds)) if masks[w] >> i & 1)
            if good and o_now < fresh_e:
                recoverable = True
        if recoverable:
            ok += 1
        elif stalled is None:
            stalled = {"t": t, "masks": masks, "obs": obs}
    return {"prefixStates": len(prefix), "recoverable": ok, "stallExample": stalled}


RUNS = [
    ("P1", Cfg("N0 f=1", "N0")),
    ("P2", Cfg("N1 f=1", "N1")),
    ("P3", Cfg("N2 skew=0 f=1", "N2", skew=0)),
    ("P4", Cfg("N2 skew=1 f=1", "N2", skew=1)),
    ("P5", Cfg("R-new f=1", "R-new")),
    ("P6", Cfg("R-new f=0", "R-new", f=0, horizon=4)),
    ("P7", Cfg("R-new f=2", "R-new", f=2)),
    ("P8", Cfg("R-new q=2 f=1 (mutant-f-q2)", "R-new", q=2)),
    ("P9", Cfg("R-new f=1 + durable rollback", "R-new", rollback=True)),
    ("P10", Cfg("R-new f=1 + ledger clock regression", "R-new", regress=True)),
]


def main() -> int:
    out = []
    for pid, cfg in RUNS:
        res, prefix = explore(cfg, collect_prefix_upto=3 if pid in ("P2", "P5") else None)
        row = {"id": pid, "config": cfg.__dict__ | {"expiries": list(cfg.expiries)}, **res}
        if pid in ("P2", "P5") and not res["violated"]:
            row["recovery"] = recovery_check(cfg, prefix)
        out.append(row)
        print(json.dumps({k: v for k, v in row.items() if k not in ("config", "digests")}, sort_keys=True), file=sys.stderr, flush=True)
    json.dump(out, sys.stdout, indent=1, sort_keys=True)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
