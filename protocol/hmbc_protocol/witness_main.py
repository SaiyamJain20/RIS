"""One witness as one OS process (HMBC2020 successor, F task 3 slice 11a).

PAPER-DERIVED RECONSTRUCTION.   python -m hmbc_protocol.witness_main --deployment F --abi-dir D --index I --key-label witness-N --state-dir D [--allow-governance FILE]

Startup (every failure: ONE JSON object `{"error": {...}}` on stderr, nothing on stdout, exit 2, nothing left behind): the manifest is strict JSON and must declare a TEST-ONLY synthetic key derivation (KEY
CUSTODY IS TEST-ONLY: the key is derived from `--key-label`; no production key loading exists); the derived address must be the manifest's witness at `--index`; the state directory must be private; the D50
stages 1 to 8 run as the WITNESS role against the real chains (`binding_open.open_witness_store`, which also creates or opens the durable store `<state>/witness-<I>/` and refuses a store bound to another
deployment); the real `RpcWitnessView` and a `WitnessService` are built; then JSON lines are served on stdin/stdout:
  request   {"schemaVersion": "hmbc-witness-rpc/v1", "id": int >= 0, "round": 1|2, "kind": "checkpoint|decision|receipt|governance", "message": {...}}   (exactly these members)
  response  {"schemaVersion": "hmbc-witness-rpc/v1", "id": int|null, "reply": {"type": "signature", "message", "signature"} | {"type": "error", "code", "reason", "recorded"}}
The reply is the pool's reply shape. A malformed line is a MALFORMED error reply (id null when none could be read); a refusal carries the service's code, reason and `recorded`; any other exception is a generic
ADAPTER_UNAVAILABLE error that leaks nothing. `--allow-governance` is the TEST-ONLY local approval list (a JSON array of [action, root, [admins]]); without it the witness signs no governance action. The
`round` is accepted and ignored here (the pool tracks rounds). This module reads no environment variable and has no clock, thread or socket of its own.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

from . import adapter as _e
from . import adapter_v2_main as am
from . import binding as bd
from . import binding_open as bo
from . import keys
from . import rpc_binding_view as rv
from . import rpc_witness_view as rwv
from . import startup_config as sc
from . import witness_service as svc
from . import witness_state as ws
from .chain import Chain, ChainError
from eth_account import Account

SCHEMA = "hmbc-witness-rpc/v1"
MAX_LINE_BYTES = 1 << 20
KINDS = {"checkpoint": "sign_checkpoint", "decision": "sign_decision", "receipt": "sign_receipt", "governance": "sign_governance"}
_ADDR = re.compile(r"0x[0-9a-f]{40}")
_INDEX = re.compile(r"[0-3]")
REQUEST_FIELDS = {"schemaVersion", "id", "round", "kind", "message"}
GENERIC = {"type": "error", "code": "ADAPTER_UNAVAILABLE", "reason": None, "recorded": None}
MALFORMED = {"type": "error", "code": "MALFORMED", "reason": None, "recorded": None}


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _answer(i, reply):
    return {"schemaVersion": SCHEMA, "id": i, "reply": reply}


def handle_line(line, service):
    """Total function: one well-formed response for any input line."""
    ident = None
    try:
        try:
            obj = _e.strict_loads(line)
        except _e.AdapterError:
            return _answer(None, dict(MALFORMED))
        if isinstance(obj, dict) and _is_int(obj.get("id")) and obj["id"] >= 0:
            ident = obj["id"]
        if (not isinstance(obj, dict) or set(obj) != REQUEST_FIELDS or obj["schemaVersion"] != SCHEMA or ident is None or not _is_int(obj["round"]) or obj["round"] not in (1, 2)
                or not isinstance(obj["kind"], str) or obj["kind"] not in KINDS or not isinstance(obj["message"], dict)):
            return _answer(ident, dict(MALFORMED))
        message = dict(obj["message"])
        try:
            signature = getattr(service, KINDS[obj["kind"]])(message)
        except svc.WitnessRefusal as e:
            return _answer(ident, {"type": "error", "code": e.code, "reason": e.reason, "recorded": e.recorded})
        return _answer(ident, {"type": "signature", "message": dict(obj["message"]), "signature": signature})
    except Exception:  # noqa: BLE001 - the boundary must not leak internals (key material, paths, node text) through a traceback or a message
        return _answer(ident, dict(GENERIC))


def serve(stdin, stdout, service):
    """JSON lines in, one line out per line in. `stdin` is a BINARY stream read with a bounded readline: invalid UTF-8 or an oversized line is a MALFORMED reply, never a crash."""
    def emit(r):
        stdout.write(json.dumps(r, separators=(",", ":")) + "\n")
        stdout.flush()

    while True:
        chunk = stdin.readline(MAX_LINE_BYTES + 2)
        if not chunk:
            return 0
        if not chunk.endswith(b"\n") and len(chunk) > MAX_LINE_BYTES:
            while chunk and not chunk.endswith(b"\n"):
                chunk = stdin.readline(1 << 16)
            emit(_answer(None, dict(MALFORMED)))
            continue
        try:
            text = chunk.decode("utf-8")
        except UnicodeDecodeError:
            emit(_answer(None, dict(MALFORMED)))
            continue
        emit(handle_line(text.rstrip("\n"), service))


def _index_arg(v):
    if _INDEX.fullmatch(v) is None:
        raise argparse.ArgumentTypeError("must be 0, 1, 2 or 3")
    return v


def _parser():
    ap = argparse.ArgumentParser(prog="hmbc_protocol.witness_main", description="One HMBC successor witness as one process (TEST-ONLY key custody)")
    ap.add_argument("--deployment", required=True)
    ap.add_argument("--abi-dir", required=True)
    ap.add_argument("--index", required=True, type=_index_arg)
    ap.add_argument("--key-label", required=True, help="TEST-ONLY: the synthetic key label, e.g. witness-1")
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--allow-governance", help="TEST-ONLY local approval list: JSON array of [action, root, [admins]]")
    return ap


def _allow(path):
    if path is None:
        return None
    raw = am._read(path, "allow-governance")
    try:
        data = sc.loads(raw, "allow-governance file")
        if not isinstance(data, list):                                       # `{}` and `""` used to iterate as empty and silently mean "no approvals"
            raise ValueError
        out = []
        for action, root, admins in data:
            if action not in ("1", "2", "3") or not isinstance(root, str) or _ADDR.fullmatch(root) is None or not isinstance(admins, list) or not all(isinstance(a, str) and _ADDR.fullmatch(a) for a in admins):
                raise ValueError
            out.append((action, root, tuple(admins)))
        return out
    except (ValueError, TypeError):
        raise am.Refusal("MALFORMED", "the allow-governance file is not a JSON array of [action, root, [admins]]") from None


def build_service(args):
    manifest = am._manifest(args.deployment)
    state = am._state_dir(args.state_dir)
    try:
        fixture = manifest["fixture"]
        derivation, witnesses, wsv = fixture["keyDerivation"], list(fixture["witnessSet"]["witnesses"]), fixture["witnessSet"]["version"]
    except (KeyError, TypeError):
        raise am.Refusal("MALFORMED", "the deployment declares no key derivation and witness set") from None
    if not isinstance(derivation, str) or not derivation.startswith("TEST-ONLY"):
        raise am.Refusal("MALFORMED", "the deployment must declare a TEST-ONLY synthetic key derivation: key custody here is TEST-ONLY")
    key = keys.synthetic_private_key(args.key_label)
    address = Account.from_key(key).address.lower()
    index = int(args.index)
    if index >= len(witnesses) or witnesses[index] != address:
        raise am.Refusal("UNKNOWN_AUTHORITY", "the key label does not name the witness at this index of the deployment's witness set")
    allowed = _allow(args.allow_governance)
    try:
        numbers = sc.manifest_numbers(manifest)                               # canonical decimal strings only: no OverflowError, no int("1_0")
    except sc.ConfigError as e:
        raise am.Refusal("MALFORMED", f"the deployment file: {e}") from None
    try:
        chains = {s: Chain(manifest["chains"][s]["rpcUrl"], numbers[s]["chainId"]) for s in ("pbc", "dbc")}
        abis = rv.load_pinned_abis(manifest, args.abi_dir)
        binding_view = rv.RpcBindingView(chains=chains, contracts={s: manifest["chains"][s]["contracts"] for s in ("pbc", "dbc")}, abis=abis)
        witness_view = rwv.RpcWitnessView.from_manifest(manifest, chains, args.abi_dir)
    except (KeyError, TypeError, ValueError, AttributeError, ChainError) as e:
        raise am.Refusal("MALFORMED", f"the deployment, its URLs or its ABI files are unusable: {type(e).__name__}: {e}") from None
    try:
        store = bo.open_witness_store(manifest, binding_view, os.path.join(state, f"witness-{index}"), address, init=True)
    except bd.OpenRefusal as e:
        raise am.Refusal(bo.OPEN_REASON_CODE.get(e.reason, "ADAPTER_UNAVAILABLE"), str(e), e.reason) from None
    except ws.StoreError as e:
        raise am.Refusal(e.code, e.message, e.reason) from None
    except ValueError as e:
        raise am.Refusal("MALFORMED", f"startup refused: {e}") from None
    return svc.WitnessService(store=store, key=key, view=witness_view, deployment=manifest, witness_set_version=wsv, allowed_governance=allowed)


def main(argv=None, stdin=None, stdout=None, stderr=None):
    stdin, stdout, stderr = stdin or sys.stdin.buffer, stdout or sys.stdout, stderr or sys.stderr
    args = _parser().parse_args(argv)
    os.umask(0o077)
    try:
        service = build_service(args)
    except am.Refusal as e:
        err = {"code": e.code, "message": e.message}
        if e.reason:
            err["reason"] = e.reason
        stderr.write(json.dumps({"error": err}, separators=(",", ":")) + "\n")
        return 2
    except Exception:  # noqa: BLE001 - the last resort: a startup defect nobody anticipated is still ONE closed refusal, never a traceback, a path or a node text (the specific refusals above stay tested)
        stderr.write(json.dumps({"error": {"code": "ADAPTER_UNAVAILABLE", "message": "internal startup failure"}}, separators=(",", ":")) + "\n")
        return 2
    return serve(stdin, stdout, service)


if __name__ == "__main__":
    sys.exit(main())
