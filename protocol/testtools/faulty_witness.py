"""TEST-ONLY crash hook H4 for a witness PROCESS (HMBC2020 successor, F task 3; INVENTORY section 4 row F-13). PAPER-DERIVED RECONSTRUCTION; synthetic TEST-ONLY keys only.

    python -m testtools.faulty_witness --crash-at before_commit|after_commit  <the arguments of hmbc_protocol.witness_main>

Serves the PRODUCTION witness process (`hmbc_protocol.witness_main`, same arguments, same wire, same startup, same exit codes) with ONE difference: the first signing request that REACHES the named point of
the durable store ends the process with `os._exit(86)`; nothing more is written, nothing is cleaned up.
  before_commit  the signing transaction is open and nothing is committed: nothing is signed and no reply is written; the restart finds no record (an uncommitted SQLite transaction dies with the process).
  after_commit   the record is durable (WAL, synchronous=FULL) and no reply was written: the restart replies with the RECORDED value (CONFLICT_PINNED for any other value) and never signs a second one.
A request that does not reach the point (a malformed line, a refusal before the commit, an idempotent re-sign that is a pure read) is an ordinary reply and the process lives on. The runner restarts the
PRODUCTION command on the same state directory; this command has no marker file and is one-shot by construction (the process dies).

How, without editing any existing file: the store already takes a `crash_hook` argument (`witness_state.init_store`/`open_store`). `install()` replaces those two module functions, IN THIS PROCESS ONLY, with
wrappers that pass the hook; `witness_main` then opens its store through the wrapped functions. The hook is an exact-name comparison against the store's own point names; the store's initialisation points
(`after_dir`, `after_db_commit`, ...) never match.

Refuses (non-zero exit, empty stdout, `refusing:` on stderr, the state directory untouched) unless `--crash-at` names one of the two points and the deployment declares TEST-ONLY synthetic keys. It is NOT part of
the production adapter or the witness process, not one of their operations, not imported by any production module and not in any export. A simulated crash at two logical points around a durable commit:
process death only, never power-loss or OS-crash durability.
"""
from __future__ import annotations

import argparse
import os
import sys

from hmbc_protocol import adapter
from hmbc_protocol import witness_main
from hmbc_protocol import witness_state as ws

from testtools.bootstrap_fixture import require_test_only

POINTS = ("before_commit", "after_commit")
CRASH_EXIT = 86


def make_hook(point):
    def hook(p):
        if p == point:
            os._exit(CRASH_EXIT)
    return hook


def install(point):
    """Make every store this process creates or opens carry the crash hook for `point` (idempotent per process: call once, before the store is opened)."""
    if point not in POINTS:
        raise ValueError(f"point must be one of {POINTS}")
    hook = make_hook(point)
    init_store, open_store = ws.init_store, ws.open_store

    def hooked_init_store(*args, **kwargs):
        kwargs["crash_hook"] = hook
        return init_store(*args, **kwargs)

    def hooked_open_store(*args, **kwargs):
        kwargs["crash_hook"] = hook
        return open_store(*args, **kwargs)
    ws.init_store, ws.open_store = hooked_init_store, hooked_open_store


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    ap.add_argument("--crash-at")
    ap.add_argument("--deployment")
    args, rest = ap.parse_known_args(argv)
    if args.crash_at not in POINTS:
        raise SystemExit(f"refusing: --crash-at must be one of {POINTS}")
    if args.deployment is None:
        raise SystemExit("refusing: --deployment is required")
    try:
        with open(args.deployment, "rb") as f:
            deployment = adapter.strict_loads(f.read().decode("utf-8"))
        require_test_only(deployment)
    except (OSError, ValueError, adapter.AdapterError) as e:
        raise SystemExit(f"refusing: {type(e).__name__}: {e}") from None
    install(args.crash_at)
    return witness_main.main(["--deployment", args.deployment, *rest])


if __name__ == "__main__":
    sys.exit(main())
