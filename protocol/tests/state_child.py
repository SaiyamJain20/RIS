"""Child process for crash tests (TEST-ONLY, hook H4): runs one store action and dies with os._exit(77) at the named crash point. Arguments: <dir> <point> <action> [...]."""
import json
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from hmbc_protocol import witness_state as ws  # noqa: E402

d, point, action = sys.argv[1], sys.argv[2], sys.argv[3]
cfg = json.loads(sys.argv[4])


def hook(p):
    if p == point:
        os._exit(77)


def signer(digest):
    import hashlib
    return "0x" + (hashlib.sha256(digest.encode()).hexdigest() * 3)[:130]


if action == "init":
    ws.init_store(d, cfg["binding_v2"], cfg["document"], cfg["owner"], crash_hook=hook)
    print("init-complete")
else:
    st = ws.open_store(d, cfg["binding_v2"], cfg["owner"], crash_hook=hook)
    sig = st.sign(type=cfg["type"], domain=cfg["domain"], wsv="2", key=cfg["key"], effect=cfg["effect"], expires_at=cfg["expires_at"], digest=cfg["digest"],
                  signer=signer, observe=lambda: cfg["obs"])
    print("signature-returned " + sig)          # reached only when no crash point fired: a crash BEFORE the commit must never print this
