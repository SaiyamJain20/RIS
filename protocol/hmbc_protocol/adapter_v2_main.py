"""The successor adapter's command line (HMBC2020 successor, F task 2 slice 10a).

PAPER-DERIVED RECONSTRUCTION.   python -m hmbc_protocol.adapter_v2_main --deployment F --abi-dir D --schema S --schema-sha256 H --schema-revision v2|v2.1 --state-dir D

EVERY argument is required and nothing is defaulted: the deployment manifest to pin (strict JSON), the directory of ABI files (each must hash to the manifest's `abi.<Name>.abiSha256`), the exact PUBLISHED
schema file with its pinned SHA-256 (a different file is refused before anything else), the explicit schema revision, and the private state directory. The process then (1) loads and checks all of that
without touching the network, (2) opens the loopback JSON-RPC clients named by the manifest (non-loopback URLs are refused by the carried client), (3) runs the startup order of `adapter_v2_start` against the
REAL chains through `RpcBindingView` (D50 stages 1 to 8, then the worker directory binding), and (4) serves JSON lines on stdin/stdout. The key-worker operations (`prepare_request`, `encrypt_record`,
`release`, `finish_decryption`) are backed by the carried `Worker` on the real ledger (chain clock `dbc.now`); EVERY response is checked against the published schema (`check_responses` stays on). The four
witness operations are wired for a `repaired-f` deployment by `build_runtime` (A2-0074 proposals P1/P2): the proposer's own `RpcWitnessView`, the four witness addresses of the pinned manifest and the supervisor's
`transport_factory`; four `witness_main` children are spawned by `main` ONLY after every startup validation has passed and are closed when it returns. For any other profile (the carried E successor) they stay
ADAPTER_UNAVAILABLE "<operation> is not wired in this process" (no witness handler is installed for them; the "not wired for this deployment profile" text belongs to the F handlers when they meet a non-F manifest). `--allow-governance FILE` is the optional TEST-ONLY local approval list handed to every witness unchanged.
A startup failure prints ONE JSON object `{"error": {"code", "message", "reason"?}}` on stderr, nothing on stdout, exits 2 and leaves no state behind (files are created with umask 077; an existing state
directory reachable by group or other is refused). No traceback, no secret and no node text reaches the output. This module reads no environment variable and has no clock, thread or socket of its own.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys

from . import adapter as _e
from . import adapter_v2 as av2
from . import adapter_v2_witness as aw
from . import adapter_v2_start as st
from . import binding as bd
from . import binding_open as bo
from . import rpc_binding_view as rv
from . import rpc_witness_view as rwv
from . import startup_config as sc
from . import witness_process_transport as wpt
from . import witness_state as ws
from .abi import Contract
from .chain import Chain, ChainError
from .ledger import Ledger
from .worker import Worker

_SHA = re.compile(r"[0-9a-f]{64}")


Refusal = sc.Refusal                                              # ONE class for every copy of this module (see startup_config.Refusal)


def _sha_arg(v):
    if _SHA.fullmatch(v) is None:
        raise argparse.ArgumentTypeError("must be 64 lowercase hex characters")
    return v


def _parser():
    ap = argparse.ArgumentParser(prog="hmbc_protocol.adapter_v2_main", description="HMBC successor JSON-lines adapter (symbolic mode), key-worker operations on a real ledger")
    ap.add_argument("--deployment", required=True, help="the deployment manifest to PIN (strict JSON)")
    ap.add_argument("--abi-dir", required=True, help="directory of <Contract>.json ABI files, each hashing to the manifest's abiSha256")
    ap.add_argument("--schema", required=True, help="the exact published schema file")
    ap.add_argument("--schema-sha256", required=True, type=_sha_arg, help="the pinned SHA-256 of that schema file")
    ap.add_argument("--schema-revision", required=True, choices=("v2", "v2.1"), help="the explicitly selected schema revision")
    ap.add_argument("--state-dir", required=True, help="private directory (mode 0700) for durable state")
    ap.add_argument("--allow-governance", help="TEST-ONLY, optional: local approval list (JSON array of [action, root, [admins]]) handed to every witness; repaired-f only")
    return ap


def _read(path, what):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        raise Refusal("MALFORMED", f"the {what} file cannot be read") from None


def _schema(path, pinned):
    raw = _read(path, "schema")
    if hashlib.sha256(raw).hexdigest() != pinned:
        raise Refusal("MALFORMED", "the schema file does not hash to --schema-sha256")
    try:
        return sc.loads(raw, "schema file")
    except sc.ConfigError:
        raise Refusal("MALFORMED", "the schema file is not JSON") from None


def _manifest(path):
    raw = _read(path, "deployment")
    try:
        m = _e.strict_loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        raise Refusal("MALFORMED", "the deployment file is not valid UTF-8") from None
    except _e.AdapterError as e:
        raise Refusal("MALFORMED", f"the deployment file: {e.message}") from None
    if not isinstance(m, dict):
        raise Refusal("MALFORMED", "the deployment file is not a JSON object")
    return m


def _state_dir(path):
    if os.path.lexists(path):
        if not os.path.isdir(path):
            raise Refusal("MALFORMED", "the state path is not a directory")
        if stat.S_IMODE(os.stat(path).st_mode) & 0o077:
            raise Refusal("MALFORMED", "the state directory must not be accessible to group or other (chmod 700)")
    return os.path.abspath(path)


def build_context(args, *, start=st.start):
    """Everything up to the Context, raising `Refusal` for every startup failure. The only I/O before the chains are opened is reading the three named files."""
    schema = _schema(args.schema, args.schema_sha256)
    problem = av2.schema_problem(schema, args.schema_revision)                 # before anything else: a wrong-shaped schema must never reach the startup order or switch response checking off
    if problem is not None:
        raise Refusal("MALFORMED", f"the schema file is unusable: {problem}")
    manifest = _manifest(args.deployment)
    try:
        numbers = sc.manifest_numbers(manifest)                                 # canonical decimal strings only: no OverflowError, no int("1_0")
    except sc.ConfigError as e:
        raise Refusal("MALFORMED", f"the deployment file: {e}") from None
    state = _state_dir(args.state_dir)
    try:
        chains = {s: Chain(manifest["chains"][s]["rpcUrl"], numbers[s]["chainId"]) for s in ("pbc", "dbc")}
        abis = rv.load_pinned_abis(manifest, args.abi_dir)
        contracts = {s: manifest["chains"][s]["contracts"] for s in ("pbc", "dbc")}
        view = rv.RpcBindingView(chains=chains, contracts=contracts, abis=abis)
        ledger = Ledger(chains["pbc"], chains["dbc"], {n: Contract(abis[n], a) for s in ("pbc", "dbc") for n, a in contracts[s].items()}, manifest)
    except (KeyError, TypeError, ValueError, AttributeError, ChainError) as e:
        raise Refusal("MALFORMED", f"the deployment, its URLs or its ABI files are unusable: {type(e).__name__}: {e}") from None
    worker_dir = os.path.join(state, st.WORKER_SUBDIR)
    try:
        return start(manifest=manifest, schema_revision=args.schema_revision, chain_view=view, state_dir=state,
                        worker_factory=lambda ctx: Worker(ledger, worker_dir, clock=ledger.dbc.now), schema=schema)
    except bd.OpenRefusal as e:
        raise Refusal(bo.OPEN_REASON_CODE.get(e.reason, "ADAPTER_UNAVAILABLE"), str(e), e.reason) from None
    except ws.StoreError as e:
        raise Refusal(e.code, e.message, e.reason) from None
    except ValueError as e:
        raise Refusal("MALFORMED", f"startup refused: {e}") from None


def build_runtime(args, *, start=st.start, supervisor_factory=wpt.WitnessSupervisor.for_deployment):
    """`(context, supervisor_or_None)`. For a `repaired-f` deployment `start` also receives the witness wiring and the supervisor (UNSTARTED) is returned: `main` spawns it only after every startup validation passed, so a
    refused startup spawns nothing and writes no pid file. Any other profile gets no wiring and no supervisor. `--allow-governance` is validated before the supervisor, any state or any chain is touched."""
    holder = []

    def wired_start(**kw):
        manifest, allow = kw["manifest"], getattr(args, "allow_governance", None)
        if manifest.get("profile") != aw.PROFILE:
            if allow is not None:
                raise Refusal("MALFORMED", "--allow-governance needs a repaired-f deployment")
            return start(**kw)
        if allow is not None:
            from . import witness_main as _wm                              # the allow-list's own validator; imported here because witness_main imports this module
            _wm._allow(allow)                                              # Refusal(MALFORMED) before the supervisor, any state or any chain
        numbers = sc.manifest_numbers(manifest)
        chains = {s: Chain(manifest["chains"][s]["rpcUrl"], numbers[s]["chainId"]) for s in ("pbc", "dbc")}
        view = rwv.RpcWitnessView.from_manifest(manifest, chains, args.abi_dir)
        try:
            supervisor = supervisor_factory(manifest=manifest, deployment_path=args.deployment, abi_dir=args.abi_dir, state_dir=kw["state_dir"], allow_governance=allow)
        except wpt.SupervisorError as e:                                   # a RuntimeError, not a ValueError: corrupt witness-set configuration is MALFORMED, not "internal"
            raise Refusal("MALFORMED", f"the deployment's witness set cannot be supervised: {e}") from None
        holder.append(supervisor)
        return start(**kw, witness_view=view, witnesses=list(manifest["fixture"]["witnessSet"]["witnesses"]), transport_factory=supervisor.transport_factory)

    ctx = build_context(args, start=wired_start)
    return ctx, (holder[0] if holder else None)


def main(argv=None, stdin=None, stdout=None, stderr=None):
    stdin, stdout, stderr = stdin or sys.stdin.buffer, stdout or sys.stdout, stderr or sys.stderr
    args = _parser().parse_args(argv)
    os.umask(0o077)                                                   # every file and directory this process creates is private
    try:
        ctx, supervisor = build_runtime(args)
    except Refusal as e:
        err = {"code": e.code, "message": e.message}
        if e.reason:
            err["reason"] = e.reason
        stderr.write(json.dumps({"error": err}, separators=(",", ":")) + "\n")
        return 2
    except Exception:  # noqa: BLE001 - the last resort: a startup defect nobody anticipated is still ONE closed refusal, never a traceback, a path or a node text (the specific refusals above stay tested)
        stderr.write(json.dumps({"error": {"code": "ADAPTER_UNAVAILABLE", "message": "internal startup failure"}}, separators=(",", ":")) + "\n")
        return 2
    try:
        if supervisor is not None:
            try:
                supervisor.start()                                          # only now, after every startup validation: four witness_main children, pid and stderr files
            except Exception:  # noqa: BLE001 - one closed refusal; the message names no path
                stderr.write(json.dumps({"error": {"code": "ADAPTER_UNAVAILABLE", "message": "the witness supervisor failed to start"}}, separators=(",", ":")) + "\n")
                return 2
        return av2.serve(stdin, stdout, ctx)
    finally:
        if supervisor is not None:
            supervisor.close()                                              # idempotent; closes the children's stdin, waits a bounded grace, kills what is left; the pid files stay


if __name__ == "__main__":
    sys.exit(main())
