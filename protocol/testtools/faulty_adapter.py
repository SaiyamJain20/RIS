"""TEST-ONLY deterministic crash hook for the E2/E3 crash schedules (candidate; requested by A3-0031, design in the agent-2 crash-hook draft).

    python -m testtools.faulty_adapter --crash-at after_intent|after_send --state-dir DIR --deployment deployment.json

Serves the SAME eight operations, transport and pinned-deployment rules as `python -m hmbc_protocol.adapter` (it imports and serves that module), with one difference: the
first `release` that REACHES the named point ends the process with `os._exit(86)` - nothing more is written, nothing is cleaned up.
  after_intent  the release intent is durable (WAL, synchronous=FULL); no send was recorded; no response line is ever written.
  after_send    the send attempt is durable AND the adapter's response line has been written and flushed to stdout (that is the "send" in this process); the process dies
                before the attempt is recorded as completed.
A release that does not reach the point (an error before the intent, e.g. NOT_COMMITTED/EXPIRED/WRONG_SUBJECT) is an ordinary response and the process lives on. The
runner restarts the PRODUCTION command on the same state directory; this command has no marker file and is one-shot by construction (the process dies).

Refuses (non-zero exit, empty stdout, `refusing:` on stderr, state directory untouched) unless the deployment declares TEST-ONLY synthetic keys and `--crash-at` names one
of the two points. It is NOT part of the production adapter, not one of its operations, and not in exports/adapter.json. A simulated crash at two logical points after durable
commits, never power-loss durability.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from hmbc_protocol import adapter
from hmbc_protocol.worker import SimulatedCrash, Worker

from testtools.bootstrap_fixture import require_test_only

POINTS = ("after_intent", "after_send")
CRASH_EXIT = 86


class CrashingWorker(Worker):
    def __init__(self, led, state_dir, clock, point: str):
        super().__init__(led, state_dir, clock=clock, faults={"crash_" + point})
        self.point = point

    def release(self, grant_id, transmit=None):
        def send(response):                                  # the adapter's "send": the same response line the production adapter writes
            sys.stdout.write(json.dumps(adapter._response(result=response), separators=(",", ":")) + "\n")
            sys.stdout.flush()
        try:
            return super().release(grant_id, transmit=send if self.point == "after_send" else transmit)
        except SimulatedCrash:
            os._exit(CRASH_EXIT)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--crash-at")
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--deployment", required=True)
    args = ap.parse_args(argv)
    if args.crash_at not in POINTS:
        raise SystemExit(f"refusing: --crash-at must be one of {POINTS}")
    try:
        with open(args.deployment, "rb") as f:
            deployment = adapter.strict_loads(f.read().decode("utf-8"))
        require_test_only(deployment)
    except (OSError, ValueError) as e:
        raise SystemExit(f"refusing: {type(e).__name__}: {e}") from None
    point = args.crash_at
    adapter.configure(adapter._private_state_dir(args.state_dir), deployment)
    adapter._worker = lambda led: CrashingWorker(led, os.path.join(adapter._STATE_DIR, "worker"), led.dbc.now, point)
    return adapter.serve(sys.stdin.buffer, sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
