"""Test support: locate Foundry binaries (cast/anvil/forge) without assuming a PATH."""
import os
import pathlib
import shutil

DEFAULT_DIR = pathlib.Path.home() / ".local/share/hmbc-tools/foundry-1.8.5"


def foundry(name: str) -> str | None:
    for d in (os.environ.get("HMBC_FOUNDRY_DIR"), str(DEFAULT_DIR)):
        if d and (pathlib.Path(d) / name).is_file():
            return str(pathlib.Path(d) / name)
    return shutil.which(name)


import json
import urllib.request


def rpc(url: str, method: str, params: list | None = None):
    """Raw JSON-RPC for test infrastructure only (production code uses hmbc_protocol.chain)."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode()
    req = urllib.request.Request(url, data=body, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.loads(r.read())
    if "error" in out:
        raise RuntimeError(f"{method}: {out['error']}")
    return out["result"]
