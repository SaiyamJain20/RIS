"""TEST-ONLY delay injection H6 for a witness PROCESS (HMBC2020 successor, F task 3; INVENTORY section 4 row F-20). PAPER-DERIVED RECONSTRUCTION; synthetic TEST-ONLY keys only.

    python -m testtools.delayed_witness --delay-ms N [--only-kind checkpoint|decision|receipt|governance] [--when before|after]  <the arguments of hmbc_protocol.witness_main>

Serves the PRODUCTION witness process (`hmbc_protocol.witness_main`: same arguments, wire, startup and exit codes) and holds the answer to a matching request for N milliseconds of REAL time:
  --when after   (default) the request is processed at once and the REPLY is held: the durable record already exists while the caller still waits (a slow reply path);
  --when before  the REQUEST is held and processed afterwards: nothing is recorded while it is held (a slow request path: the "delivery hold" of the pool schedules).
A request matches when the strict parse of its line is an object whose `kind` is the `--only-kind` kind (default: any of the four signing kinds). A line that does not parse, or has no such kind, is never
delayed. `N` is a canonical decimal integer from 0 to 60000 (0 is a plain pass-through). The production witness is unchanged: every reply is byte for byte the production reply, only later.

How, without editing any existing file: `install()` replaces `witness_main.handle_line` IN THIS PROCESS ONLY with a wrapper that sleeps before or after calling the original; `witness_main.serve` looks that
name up at every line. The wrapper holds the one serve loop, so the whole process answers later (one witness, one request at a time), exactly like a slow real witness.

Refuses (non-zero exit, empty stdout, `refusing:` on stderr, the state directory untouched) unless the delay, the kind and the position are valid and the deployment declares TEST-ONLY synthetic keys. It is
NOT part of the production witness process, not one of its operations, not imported by any production module and not in any export. Real time on a loaded host is approximate: a hold is at least N ms.
"""
from __future__ import annotations

import argparse
import re
import sys
import time

from hmbc_protocol import adapter
from hmbc_protocol import witness_main

from testtools.bootstrap_fixture import require_test_only

KINDS = tuple(witness_main.KINDS)                  # checkpoint, decision, receipt, governance
WHEN = ("before", "after")
MAX_DELAY_MS = 60000
_DELAY = re.compile(r"0|[1-9][0-9]{0,4}")


def install(delay_ms, only_kind=None, when="after", sleep=time.sleep):
    """Hold the answer to every matching request for `delay_ms` milliseconds (before or after the production handler runs); call once per process, before `witness_main.serve`."""
    if not isinstance(delay_ms, int) or isinstance(delay_ms, bool) or not 0 <= delay_ms <= MAX_DELAY_MS:
        raise ValueError(f"delay_ms must be an integer from 0 to {MAX_DELAY_MS}")
    if only_kind is not None and only_kind not in KINDS:
        raise ValueError(f"only_kind must be one of {KINDS}")
    if when not in WHEN:
        raise ValueError(f"when must be one of {WHEN}")
    original = witness_main.handle_line

    def matches(line):
        try:
            obj = adapter.strict_loads(line)
        except adapter.AdapterError:
            return False
        kind = obj.get("kind") if isinstance(obj, dict) else None
        return isinstance(kind, str) and (kind == only_kind if only_kind is not None else kind in KINDS)

    def delayed(line, service):
        hold = delay_ms > 0 and matches(line)
        if hold and when == "before":
            sleep(delay_ms / 1000)
        reply = original(line, service)
        if hold and when == "after":
            sleep(delay_ms / 1000)
        return reply
    witness_main.handle_line = delayed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    ap.add_argument("--delay-ms")
    ap.add_argument("--only-kind")
    ap.add_argument("--when")
    ap.add_argument("--deployment")
    args, rest = ap.parse_known_args(argv)
    if args.delay_ms is None or _DELAY.fullmatch(args.delay_ms) is None or int(args.delay_ms) > MAX_DELAY_MS:
        raise SystemExit(f"refusing: --delay-ms must be a canonical decimal integer from 0 to {MAX_DELAY_MS}")
    if args.only_kind is not None and args.only_kind not in KINDS:
        raise SystemExit(f"refusing: --only-kind must be one of {KINDS}")
    if args.when is not None and args.when not in WHEN:
        raise SystemExit(f"refusing: --when must be one of {WHEN}")
    if args.deployment is None:
        raise SystemExit("refusing: --deployment is required")
    try:
        with open(args.deployment, "rb") as f:
            deployment = adapter.strict_loads(f.read().decode("utf-8"))
        require_test_only(deployment)
    except (OSError, ValueError, adapter.AdapterError) as e:
        raise SystemExit(f"refusing: {type(e).__name__}: {e}") from None
    install(int(args.delay_ms), args.only_kind, args.when or "after")
    return witness_main.main(["--deployment", args.deployment, *rest])


if __name__ == "__main__":
    sys.exit(main())
