"""TEST-ONLY alternate successor adapter entry for the F fault schedules (HMBC2020 successor, F task 3; proposal P3 of A2-0074). PAPER-DERIVED RECONSTRUCTION; synthetic TEST-ONLY keys only.

    python -m testtools.faulty_adapter_v2 <the six adapter flags> [--allow-governance FILE]
        [--witness-variant I=crash:before_commit|crash:after_commit|delay:MS[:kind[:before|after]]]...  [--worker-variant compromised --claims FILE]

It serves `hmbc_protocol.adapter_v2_main` (the production module, byte for byte) and changes two things IN THIS PROCESS ONLY:
  * `--witness-variant I=...` (repeatable, once per index 0..3): the supervisor's keyword-only `command_for` seam makes witness I run `testtools.faulty_witness --crash-at POINT` (H4, exit 86 at the named
    store point) or `testtools.delayed_witness --delay-ms MS [--only-kind K] [--when W]` (H6, real-time hold, MS in 0..60000) instead of `hmbc_protocol.witness_main`, with EXACTLY the production witness's own
    arguments after the hook's flags (deployment, ABI directory, index, key label, state directory, `--allow-governance`). The other witnesses keep the production command byte for byte.
  * `--worker-variant compromised --claims FILE`: the adapter's worker is the TEST-ONLY `CompromisedWorker` (H5) with the claims of FILE (a JSON array of {requestDigest, dataId, gid, recipientKeyRef}); it releases for
    a claimed request digest without a ledger-committed grant and is honest for everything else. Symbolic mode: no secrecy conclusion.
A run with NO variant flag patches nothing and ends exactly as `python -m hmbc_protocol.adapter_v2_main` would: same startup, same refusals, same exit codes.

Refuses, BEFORE any state, process or chain exists (exit 2, ONE JSON line `{"error": {"code": "MALFORMED", "message": "refusing: ..."}}` on stderr, nothing on stdout, no child, no pid file; the messages are fixed
text: no path, no key, no argument is echoed): a deployment that is unusable or does not declare TEST-ONLY synthetic keys (even with no variant: this entry is TEST-ONLY by definition), a variant that is not
exactly the syntax above, an index outside 0..3, a delay outside 0..60000, a repeated index, `--worker-variant` other than `compromised`, `--worker-variant` without `--claims` and `--claims` without it, an unusable
claims file (validated by the CompromisedWorker's own rules, not re-implemented). A missing or malformed ADAPTER flag is refused by the production parser exactly as the production command refuses it.
NOT part of the production adapter, not one of its operations, not imported by any production module and not in exports/adapter.json. Logical process death and real-time holds only: no power-loss claim.
"""
from __future__ import annotations

import argparse
import functools
import json
import re
import sys
from typing import NamedTuple

from hmbc_protocol import adapter
from hmbc_protocol import adapter_v2_main as am
from hmbc_protocol import witness_process_transport as wpt

from testtools import compromised_worker as cw
from testtools import delayed_witness as dw
from testtools import faulty_witness as fw
from testtools.bootstrap_fixture import require_test_only

WITNESS_COUNT = wpt.WITNESS_COUNT
MAX_DELAY_MS = dw.MAX_DELAY_MS
WORKER_VARIANTS = ("compromised",)
_INDEX = re.compile(r"[0-3]")
_DELAY = re.compile(r"0|[1-9][0-9]{0,4}")
SYNTAX = "I=crash:before_commit|crash:after_commit|delay:MS[:kind[:before|after]]"

MSG_VARIANT = f"refusing: --witness-variant must be {SYNTAX} with I in 0..3 and MS in 0..{MAX_DELAY_MS}"
MSG_REPEATED = "refusing: a witness index may carry only one --witness-variant"
MSG_FLAGS = "refusing: --witness-variant, --worker-variant and --claims each take exactly one value"
MSG_WORKER = "refusing: --worker-variant must be 'compromised'"
MSG_NEEDS_CLAIMS = "refusing: --worker-variant needs --claims FILE"
MSG_NEEDS_WORKER = "refusing: --claims needs --worker-variant compromised"
MSG_CLAIMS = "refusing: the claims file is unusable (a JSON array of {requestDigest, dataId, gid, recipientKeyRef})"
MSG_DEPLOYMENT = "refusing: the deployment is unusable or does not declare TEST-ONLY synthetic keys"


class FlagError(ValueError):
    """This entry's own flags are malformed (argparse would have printed a usage text and exited: a value that starts with '-' such as `-1=crash:after_commit`, or a flag without its value)."""


class _Parser(argparse.ArgumentParser):
    def error(self, message):                                                        # never print or exit: the caller turns it into the one closed refusal
        raise FlagError("malformed flag")


class Variant(NamedTuple):
    index: int
    name: str                    # "crash" or "delay"
    point: str | None            # crash: before_commit | after_commit
    delay_ms: int | None         # delay: 0..60000
    only_kind: str | None        # delay: checkpoint | decision | receipt | governance
    when: str | None             # delay: before | after


class Arguments(NamedTuple):
    variants: list
    worker: str | None
    claims: str | None
    base: list                   # the adapter's own flags, verbatim and in order


def parse_variant(text):
    """`I=crash:POINT` or `I=delay:MS[:kind[:when]]`, exactly; anything else is a ValueError."""
    if not isinstance(text, str) or "=" not in text:
        raise ValueError("not I=variant")
    left, _, right = text.partition("=")
    if _INDEX.fullmatch(left) is None:
        raise ValueError("index must be 0, 1, 2 or 3")
    parts = right.split(":")
    if parts[0] == "crash":
        if len(parts) != 2 or parts[1] not in fw.POINTS:
            raise ValueError("crash needs one of " + ", ".join(fw.POINTS))
        return Variant(int(left), "crash", parts[1], None, None, None)
    if parts[0] == "delay":
        if not 2 <= len(parts) <= 4 or _DELAY.fullmatch(parts[1]) is None or int(parts[1]) > MAX_DELAY_MS:
            raise ValueError(f"delay needs MS in 0..{MAX_DELAY_MS}")
        kind = parts[2] if len(parts) >= 3 else None
        when = parts[3] if len(parts) == 4 else None
        if kind is not None and kind not in dw.KINDS:
            raise ValueError("delay kind must be one of " + ", ".join(dw.KINDS))
        if when is not None and when not in dw.WHEN:
            raise ValueError("delay when must be before or after")
        return Variant(int(left), "delay", None, int(parts[1]), kind, when)
    raise ValueError("variant must be crash or delay")


def split_arguments(argv):
    """Separate this entry's flags from the adapter's. The adapter's flags come back verbatim and in order (they are handed to the production main unchanged); a syntax problem is a ValueError."""
    ap = _Parser(add_help=False, allow_abbrev=False)
    ap.add_argument("--witness-variant", action="append", default=[])
    ap.add_argument("--worker-variant")
    ap.add_argument("--claims")
    ns, base = ap.parse_known_args(list(argv))
    variants = [parse_variant(t) for t in ns.witness_variant]
    if len({v.index for v in variants}) != len(variants):
        raise ValueError("repeated index")
    return Arguments(variants, ns.worker_variant, ns.claims, base)


def command_for_variants(variants):
    """`command_for(index, default_command)` for the supervisor: the hook's command for a variant index, the default command (unchanged) for every other index."""
    table = {v.index: v for v in variants.values()} if isinstance(variants, dict) else {v.index: v for v in variants}

    def command_for(index, default_command):
        v = table.get(index)
        if v is None:
            return default_command
        i = default_command.index("hmbc_protocol.witness_main")                    # ValueError (reported by the supervisor) if the production command ever changes shape
        head, tail = default_command[:i], default_command[i + 1:]
        if v.name == "crash":
            return [*head, "testtools.faulty_witness", "--crash-at", v.point, *tail]
        flags = ["--delay-ms", str(v.delay_ms)]
        if v.only_kind is not None:
            flags += ["--only-kind", v.only_kind]
        if v.when is not None:
            flags += ["--when", v.when]
        return [*head, "testtools.delayed_witness", *flags, *tail]
    return command_for


def load_claims(path):
    """The claims of FILE, validated by CompromisedWorker's own rules; ValueError for anything unusable."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
        data = adapter.strict_loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, adapter.AdapterError):
        raise ValueError("unreadable claims file") from None
    return cw._validated(data)                                                       # raises ValueError (WireError and KeyRefError are ValueErrors) before anything is created


def install(variants, claims=None):
    """Patch `adapter_v2_main` in THIS process: `build_runtime` gains the `command_for` seam when there are witness variants; `Worker` becomes the CompromisedWorker when there are claims."""
    table = dict(variants)
    if table:
        original = am.build_runtime
        factory = functools.partial(wpt.WitnessSupervisor.for_deployment, command_for=command_for_variants(table))

        def build_runtime(args, **kwargs):
            kwargs.setdefault("supervisor_factory", factory)
            return original(args, **kwargs)
        am.build_runtime = build_runtime
    if claims is not None:
        am.Worker = lambda led, state_dir, *, clock: cw.CompromisedWorker(led, state_dir, clock, claims)


def _refuse(stderr, message):
    stderr.write(json.dumps({"error": {"code": "MALFORMED", "message": message}}, separators=(",", ":")) + "\n")
    return 2


def main(argv=None, stdin=None, stdout=None, stderr=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    stderr = stderr or sys.stderr
    try:
        parsed = split_arguments(argv)
    except FlagError:
        return _refuse(stderr, MSG_FLAGS)
    except ValueError as e:
        return _refuse(stderr, MSG_REPEATED if str(e) == "repeated index" else MSG_VARIANT)
    if parsed.worker is not None and parsed.worker not in WORKER_VARIANTS:
        return _refuse(stderr, MSG_WORKER)
    if parsed.worker is not None and parsed.claims is None:
        return _refuse(stderr, MSG_NEEDS_CLAIMS)
    if parsed.worker is None and parsed.claims is not None:
        return _refuse(stderr, MSG_NEEDS_WORKER)
    base = am._parser().parse_args(parsed.base)                                      # a missing or malformed ADAPTER flag: the production parser's own refusal (exit 2, usage on stderr)
    try:
        with open(base.deployment, "rb") as f:
            deployment = adapter.strict_loads(f.read().decode("utf-8"))
        require_test_only(deployment)
    except (OSError, UnicodeDecodeError, adapter.AdapterError, SystemExit):
        return _refuse(stderr, MSG_DEPLOYMENT)
    claims = None
    if parsed.worker is not None:
        try:
            claims = load_claims(parsed.claims)
        except ValueError:
            return _refuse(stderr, MSG_CLAIMS)
    install({v.index: v for v in parsed.variants}, claims)
    return am.main(parsed.base, stdin=stdin, stdout=stdout, stderr=stderr)


if __name__ == "__main__":
    sys.exit(main())
