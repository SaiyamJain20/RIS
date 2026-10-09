"""Read-only export of the key worker's durable log for the evidence collector.

`python -m hmbc_protocol.worker_log --state-dir DIR` prints JSON: the append-only event log, one row per release with counts, and the
per-event counts the scenario catalog's `expected.worker` record asks for. The response token (the symbolic capability) is NEVER printed:
only keccak256(token) is, so a collector can check "same cached response" without holding the capability. Opens the database read-only.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys

from eth_utils import keccak


def _database(state_dir: str) -> str:
    """The adapter keeps its worker under <state-dir>/worker; a Worker created directly keeps worker.sqlite in the directory itself. Accept both."""
    nested, direct = os.path.join(state_dir, "worker", "worker.sqlite"), os.path.join(state_dir, "worker.sqlite")
    found = [p for p in (nested, direct) if os.path.isfile(p)]
    if len(found) == 2:
        raise SystemExit(f"ambiguous state directory: both {nested} and {direct} exist")
    if not found:
        raise SystemExit(f"no worker.sqlite in {state_dir} (looked in <dir>/worker/ and in <dir>)")
    return found[0]


def export(state_dir: str) -> dict:
    path = _database(state_dir)
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=15)
    try:
        events = [{"type": t, "requestDigest": rd, "timestamp": str(ts), "grantId": gi, "gid": gid, "dataId": did}
                  for t, rd, gi, gid, did, ts in db.execute("select type,request_digest,grant_id,gid,data_id,timestamp from events order by id")]
        releases = [{"grantId": gi, "requestDigest": rd, "dataId": did, "gid": gid, "ciphertextDigest": cd, "recipientKeyHash": rk, "keyEpoch": ke,
                     "tokenDigest": "0x" + keccak(bytes.fromhex(tok[2:])).hex(), "grantExpiresAt": str(ge), "createdAt": str(ca),
                     "delivery": dl, "sendAttempts": sc, "completedAttempts": cc}
                    for gi, rd, did, gid, rk, ke, cd, tok, ge, ca, dl, sc, cc in db.execute(
                        "select grant_id,request_digest,data_id,gid,recipient_key_hash,key_epoch,ciphertext_digest,token,grant_expires_at,created_at,"
                        "delivery,sent_count,completed_count from releases order by created_at, grant_id")]
        fp = db.execute("select value from meta where key='deployment'").fetchone()
    finally:
        db.close()
    return {"schemaVersion": "hmbc-worker-log/v0", "adapterMode": "symbolic", "deploymentFingerprint": fp[0] if fp else None, "events": events,
            "releases": releases,
            "counts": {"releaseIntentCount": str(sum(e["type"] == "RELEASE_INTENT" for e in events)),
                       "releaseSentCount": str(sum(e["type"] == "RELEASE_SENT" for e in events))},
            "note": "RELEASE_SENT records an ATTEMPTED send (write-ahead); delivery is never acknowledged, so it stays 'unknown'. Tokens are redacted to digests."}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state-dir", required=True)
    print(json.dumps(export(ap.parse_args(argv).state_dir), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
