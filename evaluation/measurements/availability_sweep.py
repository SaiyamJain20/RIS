"""Availability/safety sweep over agent 2's real witnesses (real durable stores, real EIP-712 signatures,
synthetic keys) behind agent 2's TEST-ONLY virtual transport and the real pool state machine.
Reuses helpers from protocol/tests/test_witness_pool_driver.py of an extracted snapshot.
NOT measured: any real network, clock, process or ledger; virtual ms are the transport's schedule.
Usage: python3 -I availability_sweep.py <protocol-root> <out.json> [--runs N]"""
import itertools, json, os, sys, tempfile, time, statistics, pathlib

root = os.path.abspath(sys.argv[1]); out = sys.argv[2]
runs = int(sys.argv[sys.argv.index("--runs") + 1]) if "--runs" in sys.argv else 5
sys.dont_write_bytecode = True
sys.path[:0] = [os.path.join(root, "tests"), root]
import test_witness_pool_driver as T                      # noqa: E402  (helpers only; no test is run)
from hmbc_protocol import witness_pool_driver as drv      # noqa: E402
from hmbc_protocol import witness_service as svc          # noqa: E402
from testtools.virtual_transport import ServiceEndpoint, VirtualTransport  # noqa: E402

def one(muted, delays, tmp):
    view = T.PoolView(); ws_ = T.make_witnesses(pathlib.Path(tmp), view)
    proposal = svc.derive_checkpoint(view, T.DEPLOY)
    eps = [ServiceEndpoint(w.sign_checkpoint, muted=(i in muted), reply_delay=delays[i]) for i, w in enumerate(ws_)]
    coll = T.collection(view, proposal)
    t0 = time.perf_counter(); r = drv.run_collection(coll, VirtualTransport(eps)); wall = (time.perf_counter() - t0) * 1000
    return r, coll, wall

rows = []
for m in range(0, 5):
    for muted in itertools.combinations(range(4), m):
        res = []
        for k in range(runs):
            with tempfile.TemporaryDirectory() as tmp:
                r, coll, wall = one(set(muted), [0, 0, 0, 0], tmp)
            res.append((bool(r["ok"]), coll.finished_at_ms, wall, len(r.get("signatures", []))))
        oks = {x[0] for x in res}
        rows.append({"muted": list(muted), "ok": sorted(oks), "virtual_finish_ms": sorted({x[1] for x in res}),
                     "signatures": sorted({x[3] for x in res}), "wall_ms_median": round(statistics.median(x[2] for x in res), 2),
                     "wall_ms_max": round(max(x[2] for x in res), 2), "runs": runs})
# latency ordering: with reply delays, the three fastest signatures are used, the slowest is not waited for
delays = [400, 300, 200, 100]
with tempfile.TemporaryDirectory() as tmp:
    r, coll, wall = one(set(), delays, tmp)
order = {"reply_delays_ms": delays, "ok": bool(r["ok"]), "signatures": len(r["signatures"]), "virtual_finish_ms": coll.finished_at_ms}
json.dump({"muted_sweep": rows, "delay_order": order}, open(out, "w"), indent=1)
for x in rows: print(x)
print(order)
