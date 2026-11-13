"""Byzantine sweep over agent 2's pool state machine and its scripted-witness harness (tests/test_witness_pool.py
helpers). Honest witnesses are agent 2's MODEL of the F signing rule (not the durable store); signatures are real
EIP-712. f=1: one Byzantine position x 9 behaviours x 27 honest pin patterns (972 cases). f=2: every pair of
Byzantine positions x 9x9 behaviours x 9 honest pin patterns (4374 cases), a CONTROL outside the fault bound.
Per run: ok / certificate; every certificate is checked for 3 distinct valid signers; and an AGREEMENT HAZARD
is flagged when, after the run, two different values could EACH gather >= q=3 signers: (honest witnesses whose
store holds that value) + (all Byzantine witnesses). NOT a consensus measurement; virtual time.
Usage: python3 -I byzantine_sweep.py <protocol-root> <out.json>"""
import itertools, json, os, sys
root = os.path.abspath(sys.argv[1]); out = sys.argv[2]
sys.dont_write_bytecode = True
sys.path[:0] = [os.path.join(root, "tests"), root]
import test_witness_pool as T                                    # noqa: E402  (helpers only)
from hmbc_protocol import eip712, messages                        # noqa: E402

def run(byz_set, pins, behaviours):
    honest_ix = [i for i in range(4) if i not in byz_set]
    ws = [None] * 4
    for i, pin in zip(honest_ix, pins):
        ws[i] = T.Wit(i)
        if pin is not None: ws[i].preload(pin)
    for b, name in zip(sorted(byz_set), behaviours):
        ws[b] = T.Scripted(b, T.byz_menu(b)[name])
    c = T.make(proposal=T.C); T.drive(c, ws)
    r = c.result
    cert_ok = None
    if r["ok"]:
        m = r["message"]
        d = messages.digest_of("StateCheckpoint", m, messages.domain_for("StateCheckpoint", m, T.DEPLOY))
        addrs = [eip712.recover(d, sg) for sg in r["signatures"]]
        cert_ok = len(addrs) == 3 and len(set(addrs)) == 3 and addrs == sorted(addrs) and set(addrs) <= set(T.ADDR)
    held = {}
    for i in honest_ix:
        for seq, v in ws[i].store.items():
            held.setdefault(T.canon(v[0]), set()).add(i)
    nb = len(byz_set)
    potential = {k: len(h) + nb for k, h in held.items()}
    hazard = sum(1 for k in potential if potential[k] >= 3) >= 2
    return r["ok"], cert_ok, hazard

menu = list(T.byz_menu(0).keys())
res = {}
# f=1
tot = ok = badcert = haz = 0; per = {n: [0, 0] for n in menu}
for byz in range(4):
    for pins in itertools.product([None, T.A, T.B], repeat=3):
        for n in menu:
            o, cok, h = run({byz}, pins, [n]); tot += 1; ok += o; badcert += (cok is False); haz += h
            per[n][0] += 1; per[n][1] += o
res["f1"] = {"cases": tot, "certificates": ok, "no_certificate": tot - ok, "invalid_certificates": badcert, "agreement_hazard_cases": haz,
             "certificates_by_byzantine_behaviour": {n: "%d/%d" % (v[1], v[0]) for n, v in per.items()}}
# f=2 control
tot = ok = badcert = haz = 0
for pair in itertools.combinations(range(4), 2):
    for pins in itertools.product([None, T.A, T.B], repeat=2):
        for n1, n2 in itertools.product(menu, repeat=2):
            o, cok, h = run(set(pair), pins, [n1, n2]); tot += 1; ok += o; badcert += (cok is False); haz += h
res["f2_control"] = {"cases": tot, "certificates": ok, "no_certificate": tot - ok, "invalid_certificates": badcert, "agreement_hazard_cases": haz}
json.dump(res, open(out, "w"), indent=1); print(json.dumps(res, indent=1))
