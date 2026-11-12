"""TEST-ONLY alternate successor adapter entry for the F fault schedules (HMBC2020 successor, F task 3; proposal P3 of A2-0074). PAPER-DERIVED RECONSTRUCTION; synthetic TEST-ONLY keys only.

    python -m testtools.faulty_adapter_v2 <the six adapter flags> [--allow-governance FILE]
        [--witness-variant I=crash:before_commit|crash:after_commit|delay:MS[:kind[:before|after]]|mutant:ID|byz:SPEC|view:SPEC]...  [--mutant-tree ID=ABSOLUTE_DIR]...  [--worker-variant compromised --claims FILE]

It serves `hmbc_protocol.adapter_v2_main` (the production module, byte for byte) and changes two things IN THIS PROCESS ONLY:
  * `--witness-variant I=...` (repeatable, once per index 0..3): the supervisor's keyword-only `command_for` seam makes witness I run `testtools.faulty_witness --crash-at POINT` (H4, exit 86 at the named
    store point) or `testtools.delayed_witness --delay-ms MS [--only-kind K] [--when W]` (H6, real-time hold, MS in 0..60000) instead of `hmbc_protocol.witness_main`, with EXACTLY the production witness's own
    arguments after the hook's flags (deployment, ABI directory, index, key label, state directory, `--allow-governance`). The other witnesses keep the production command byte for byte.
  * `--worker-variant compromised --claims FILE`: the adapter's worker is the TEST-ONLY `CompromisedWorker` (H5) with the claims of FILE (a JSON array of {requestDigest, dataId, gid, recipientKeyRef}); it releases for
    a claimed request digest without a ledger-committed grant and is honest for everything else. Symbolic mode: no secrecy conclusion.
  * `I=byz:SPEC` (SPEC withhold | garbage | repeat:N | equivocate | impersonate:J | poison:FIELD, the grammar of `testtools.byzantine_witness`): witness I is the real-PROCESS Byzantine witness (H1) with the
  * `I=view:SPEC` (SPEC authEpoch:N | policyVersion:N | witnessSetVersion:N | headLag:N, the grammar of `testtools.divergent_witness`): witness I is the real production witness whose chain view DIVERGES from the real ledger (H3, gap G2); a malformed SPEC is the one closed refusal.
    production witness's own arguments after `--behavior SPEC`; it needs no tree and no state of its own (withhold, garbage, impersonate and poison make no RPC call).
  * `I=mutant:ID` (ID one of the WITNESS-role F-plan source mutants M1 M2 M3 M4 M6 M7 of `testtools.mutant_tree`) with `--mutant-tree ID=DIR` (an absolute directory built by `python -m testtools.mutant_tree build`): witness I starts
    through `testtools.mutant_run` from that tree (exec, same pid) with the production witness's own arguments after `--`. Each such variant needs its tree and each tree its variant; every tree is verified (an untampered
    build of that very mutant) before anything is created. M5 is an ADAPTER-role mutant: it is not a witness variant (run this whole entry from its tree with `testtools.mutant_run --module testtools.faulty_adapter_v2`).
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
import os
import re
import sys
from typing import NamedTuple

from hmbc_protocol import adapter
from hmbc_protocol import adapter_v2_main as am
from hmbc_protocol import witness_process_transport as wpt

from testtools import compromised_worker as cw
from testtools import delayed_witness as dw
from testtools import divergent_witness as dvw
from testtools import byzantine_witness as bw
from testtools import faulty_witness as fw
from testtools import mutant_tree as mt
from testtools.bootstrap_fixture import require_test_only

WITNESS_COUNT = wpt.WITNESS_COUNT
MAX_DELAY_MS = dw.MAX_DELAY_MS
WORKER_VARIANTS = ("compromised",)
WITNESS_MUTANTS = tuple(m.id for m in mt.MUTANTS.values() if m.role == "witness")             # M5 runs in the adapter process: not a witness variant
_INDEX = re.compile(r"[0-3]")
_DELAY = re.compile(r"0|[1-9][0-9]{0,4}")
SYNTAX = "I=crash:before_commit|crash:after_commit|delay:MS[:kind[:before|after]]|mutant:ID|byz:SPEC|view:SPEC"

MSG_VARIANT = f"refusing: --witness-variant must be {SYNTAX} with I in 0..3 and MS in 0..{MAX_DELAY_MS}"
MSG_REPEATED = "refusing: a witness index may carry only one --witness-variant"
MSG_FLAGS = "refusing: --witness-variant, --worker-variant and --claims each take exactly one value"
MSG_MUTANT = "refusing: each --witness-variant I=mutant:ID needs exactly one --mutant-tree ID=ABSOLUTE_DIR that is an untampered build of that mutant, and each --mutant-tree needs its variant"
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


class TreeFlagError(ValueError):
    """`--mutant-tree` is malformed (not ID=ABSOLUTE_DIR for a witness-role mutant, or an id given twice)."""


class Variant(NamedTuple):
    index: int
    name: str                    # "crash", "delay", "mutant" or "byz"
    point: str | None            # crash: before_commit | after_commit
    delay_ms: int | None         # delay: 0..60000
    only_kind: str | None        # delay: checkpoint | decision | receipt | governance
    when: str | None             # delay: before | after
    mutant: str | None = None    # mutant: M1 M2 M3 M4 M6 M7
    behavior: str | None = None  # byz: the testtools.byzantine_witness behaviour SPEC
    view: str | None = None      # view: the testtools.divergent_witness view SPEC


class Arguments(NamedTuple):
    variants: list
    worker: str | None
    claims: str | None
    base: list                   # the adapter's own flags, verbatim and in order
    trees: tuple = ()            # ((mutant id, absolute directory), ...) in the order given


def parse_variant(text):
    """`I=crash:POINT`, `I=delay:MS[:kind[:when]]`, `I=mutant:ID` (ID a witness-role mutant) or `I=byz:SPEC` (SPEC a byzantine_witness behaviour), exactly; anything else is a ValueError."""
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
    if parts[0] == "mutant":
        if len(parts) != 2 or parts[1] not in WITNESS_MUTANTS:
            raise ValueError("mutant needs one of " + ", ".join(WITNESS_MUTANTS))
        return Variant(int(left), "mutant", None, None, None, None, parts[1])
    if parts[0] == "byz":
        spec = right.partition(":")[2]
        return Variant(int(left), "byz", None, None, None, None, None, bw.parse_behavior(spec))      # ValueError for a malformed SPEC
    if parts[0] == "view":
        spec = right.partition(":")[2]
        return Variant(int(left), "view", None, None, None, None, None, None, dvw.parse_spec(spec))      # ValueError for a malformed SPEC
    raise ValueError("variant must be crash, delay, mutant, byz or view")


def parse_tree(text):
    """`ID=ABSOLUTE_DIR` for a witness-role mutant id; anything else is a TreeFlagError."""
    mid, sep, directory = text.partition("=") if isinstance(text, str) else ("", "", "")
    if not sep or mid not in WITNESS_MUTANTS or not directory or "=" in directory or not os.path.isabs(directory):
        raise TreeFlagError("malformed --mutant-tree")
    return mid, directory


def split_arguments(argv):
    """Separate this entry's flags from the adapter's. The adapter's flags come back verbatim and in order (they are handed to the production main unchanged); a syntax problem is a ValueError."""
    ap = _Parser(add_help=False, allow_abbrev=False)
    ap.add_argument("--witness-variant", action="append", default=[])
    ap.add_argument("--worker-variant")
    ap.add_argument("--claims")
    ap.add_argument("--mutant-tree", action="append", default=[])
    ns, base = ap.parse_known_args(list(argv))
    variants = [parse_variant(t) for t in ns.witness_variant]
    if len({v.index for v in variants}) != len(variants):
        raise ValueError("repeated index")
    trees = [parse_tree(t) for t in ns.mutant_tree]
    if len({m for m, _ in trees}) != len(trees):
        raise TreeFlagError("a mutant tree is given twice")
    return Arguments(variants, ns.worker_variant, ns.claims, base, tuple(trees))


def command_for_variants(variants, trees=None):
    """`command_for(index, default_command)` for the supervisor: the hook's command for a variant index, the default command (unchanged) for every other index. `trees` maps a mutant id to its built tree."""
    table = {v.index: v for v in variants.values()} if isinstance(variants, dict) else {v.index: v for v in variants}
    tree_of = dict(trees or {})

    def command_for(index, default_command):
        v = table.get(index)
        if v is None:
            return default_command
        i = default_command.index("hmbc_protocol.witness_main")                    # ValueError (reported by the supervisor) if the production command ever changes shape
        head, tail = default_command[:i], default_command[i + 1:]
        if v.name == "byz":
            return [*head, "testtools.byzantine_witness", "--behavior", v.behavior, *tail]
        if v.name == "view":
            return [*head, "testtools.divergent_witness", "--view", v.view, *tail]
        if v.name == "mutant":
            if v.mutant not in tree_of:
                raise ValueError("no tree for the mutant")
            return [*head, "testtools.mutant_run", "--tree", tree_of[v.mutant], "--mutant", v.mutant, "--module", "hmbc_protocol.witness_main", "--", *tail]
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


def install(variants, claims=None, trees=None):
    """Patch `adapter_v2_main` in THIS process: `build_runtime` gains the `command_for` seam when there are witness variants; `Worker` becomes the CompromisedWorker when there are claims."""
    table = dict(variants)
    if table:
        original = am.build_runtime
        factory = functools.partial(wpt.WitnessSupervisor.for_deployment, command_for=command_for_variants(table, trees))

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
    except TreeFlagError:
        return _refuse(stderr, MSG_MUTANT)
    except ValueError as e:
        return _refuse(stderr, MSG_REPEATED if str(e) == "repeated index" else MSG_VARIANT)
    if parsed.worker is not None and parsed.worker not in WORKER_VARIANTS:
        return _refuse(stderr, MSG_WORKER)
    if parsed.worker is not None and parsed.claims is None:
        return _refuse(stderr, MSG_NEEDS_CLAIMS)
    if parsed.worker is None and parsed.claims is not None:
        return _refuse(stderr, MSG_NEEDS_WORKER)
    trees = dict(parsed.trees)
    if set(trees) != {v.mutant for v in parsed.variants if v.mutant is not None}:
        return _refuse(stderr, MSG_MUTANT)
    for mid, directory in trees.items():
        try:
            mt.verify_tree(directory, mid)                                           # an untampered build of THAT mutant, before anything is created or spawned
        except mt.MutantError:
            return _refuse(stderr, MSG_MUTANT)
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
    install({v.index: v for v in parsed.variants}, claims, trees)
    return am.main(parsed.base, stdin=stdin, stdout=stdout, stderr=stderr)


if __name__ == "__main__":
    sys.exit(main())
