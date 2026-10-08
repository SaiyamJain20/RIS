"""JSON-lines service boundary (interfaces/README.md section 2/3).

One request object per input line, exactly one response object per request line:
  request : {schemaVersion:"v1", operation, input, deploymentManifest}
  response: {schemaVersion:"v1", ok, result, error}   exactly one of result/error is non-null
No request can carry code or shell commands; unknown operations/fields fail explicitly; keys are handles only.

STATUS (E0): only `prepare_request` has behaviour. collect_decision/release/encrypt_record/finish_decryption belong
to B-E1, which is locked until E0 unlocks, and answer ADAPTER_UNAVAILABLE. rotate_epoch answers
NOT_IMPLEMENTED_IN_PHASE as the interface requires. Nothing here fabricates a success.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from typing import Any, TextIO

from . import chain, eip712, keys, messages, wire
from .ledger import Ledger, LedgerError
from .witness import Witness, WitnessError
from .worker import Worker, WorkerError

SCHEMA_VERSION = "v1"
ADAPTER_MODE = "symbolic"
MAX_LINE_BYTES = 1 << 20
REQUEST_FIELDS = {"schemaVersion", "operation", "input", "deploymentManifest"}


class AdapterError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def _reject_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise AdapterError("MALFORMED", f"duplicate JSON key {k!r}")
        out[k] = v
    return out


def _reject_constant(name):
    raise AdapterError("MALFORMED", f"non-standard JSON constant {name}")


def strict_loads(line: str) -> Any:
    try:
        return json.loads(line, object_pairs_hook=_reject_duplicates, parse_constant=_reject_constant)
    except AdapterError:
        raise
    except (ValueError, RecursionError) as e:
        raise AdapterError("MALFORMED", f"invalid JSON: {type(e).__name__}") from None


def _exact(obj: Any, fields: set[str], what: str) -> dict:
    if not isinstance(obj, dict) or set(obj) != fields:
        got = sorted(obj) if isinstance(obj, dict) else type(obj).__name__
        raise AdapterError("MALFORMED", f"{what}: expected exactly {sorted(fields)}, got {got}")
    return obj


def _deployment(dep: Any) -> dict:
    """Structural minimum the signer needs. Full LedgerDeployment validation is agent 3's candidate schema."""
    try:
        pbc, dbc = dep["chains"]["pbc"], dep["chains"]["dbc"]
        wire.uint(pbc["chainId"], 256), wire.uint(dbc["chainId"], 256)
        wire.address(pbc["contracts"]["PSC"]), wire.address(pbc["contracts"]["RSC"]), wire.address(dbc["contracts"]["KSSC"])
        wire.uint(dep["fixture"]["keyEpoch"], 64), wire.uint(dep["fixture"]["policyVersion"], 64)
    except (KeyError, TypeError, wire.WireError):
        raise AdapterError("MALFORMED", "deploymentManifest lacks the chains/contracts/fixture fields required to bind a request") from None
    return dep


def prepare_request(inp: Any, dep: dict) -> dict:
    inp = _exact(inp, {"request", "signingKeyRef"}, "prepare_request input")
    try:
        req = messages.VALIDATE["AccessRequest"](inp["request"])
    except wire.WireError as e:
        raise AdapterError("MALFORMED", str(e)) from None
    try:
        private_key, signer = keys.resolve(inp["signingKeyRef"], ("user",))
    except keys.KeyRefError as e:
        raise AdapterError("MALFORMED", str(e)) from None
    pbc, dbc = dep["chains"]["pbc"], dep["chains"]["dbc"]
    # The signing client refuses to sign for any other identity, or against any deployment but the configured one.
    if req["gid"] != signer:
        raise AdapterError("WRONG_SUBJECT", "request.gid is not the address of the referenced user key")
    if (req["sourceChainId"], req["psc"], req["destinationChainId"], req["kssc"]) != (
            pbc["chainId"], pbc["contracts"]["PSC"], dbc["chainId"], dbc["contracts"]["KSSC"]):
        raise AdapterError("WRONG_DESTINATION", "request chains/contracts differ from the deployment manifest")
    if req["keyEpoch"] != dep["fixture"]["keyEpoch"] or req["policyVersion"] != dep["fixture"]["policyVersion"]:
        raise AdapterError("WRONG_EPOCH", "request keyEpoch/policyVersion differ from the deployment's fixed values")
    domain = messages.domain_for("AccessRequest", req, dep)
    digest = messages.digest_of("AccessRequest", req, domain)
    signature = eip712.sign_digest(private_key, digest)
    if eip712.recover(digest, signature) != signer:           # never emit a signature that does not verify (explicit: `assert` is stripped by -O)
        raise AdapterError("ADAPTER_UNAVAILABLE", "internal signing self-check failed")
    return {"schemaVersion": SCHEMA_VERSION, "adapterMode": ADAPTER_MODE, "request": req,
            "requestDigest": "0x" + digest.hex(), "signature": signature, "signer": signer}


_STATE_DIR: str | None = None
_PINNED: dict | None = None
_LEDGER: Ledger | None = None


def configure(state_dir: str | None, deployment: dict | None = None) -> None:
    """Set (or clear) the private worker-state directory and the PINNED deployment. Called once at startup by main().

    The pinned deployment is the trust root for every ledger-backed operation: RPC URLs, contract addresses and the witness key label come
    from it, never from a request. A request whose deploymentManifest differs from it is refused before any connection is made (A2-0009)."""
    global _STATE_DIR, _PINNED, _LEDGER
    _STATE_DIR, _PINNED, _LEDGER = state_dir, None, None
    if deployment is not None:
        try:
            _LEDGER = Ledger.from_deployment(deployment)
        except LedgerError as e:
            raise ValueError(f"pinned deployment unusable: {e}") from None
        _PINNED = json.loads(json.dumps(deployment))


def _ledger(dep: dict) -> Ledger:
    if _LEDGER is None:
        raise AdapterError("ADAPTER_UNAVAILABLE", "no deployment is pinned (start the adapter with --deployment)")
    return _LEDGER                                               # `dep` was already checked equal to the pinned manifest in handle_line


def _worker(led: Ledger) -> Worker:
    if _STATE_DIR is None:
        raise AdapterError("ADAPTER_UNAVAILABLE", "no worker state directory is configured (start with --state-dir)")
    return Worker(led, os.path.join(_STATE_DIR, "worker"), clock=led.dbc.now)


def _ledger_op(fn):
    """Run a ledger-backed operation and map every failure onto the interface's closed error classes (never leak internals)."""
    def handler(inp: Any, dep: dict) -> dict:
        try:
            return fn(inp, _ledger(dep))
        except (WorkerError, WitnessError) as e:
            raise AdapterError(e.code, e.message) from None
        except chain.Rejected as e:
            raise AdapterError(e.code if e.code in wire.ERROR_CODES else "ADAPTER_UNAVAILABLE", f"the ledger rejected the call: {e.code}") from None
        except chain.ChainError:
            raise AdapterError("ADAPTER_UNAVAILABLE", "the ledger is unreachable or returned an error") from None
    return handler


@_ledger_op
def collect_decision(inp: Any, led: Ledger) -> dict:
    w = Witness(led)
    if "witnessSetVersion" in inp and inp["witnessSetVersion"] != w.witness_set_version:
        raise AdapterError("STALE_STATE", "witnessSetVersion differs from the configured witness set")
    d = w.decide(inp["requestDigest"])
    return {"schemaVersion": SCHEMA_VERSION, "adapterMode": ADAPTER_MODE, "decision": d["decision"],
            "signatures": d["signatures"], "credentialRecords": d["credentialRecords"]}


@_ledger_op
def release(inp: Any, led: Ledger) -> dict:
    return _worker(led).release(inp["grantId"])


@_ledger_op
def encrypt_record(inp: Any, led: Ledger) -> dict:
    return _worker(led).encrypt_record(inp["record"], inp["policy"], inp["keyEpoch"])


@_ledger_op
def finish_decryption(inp: Any, led: Ledger) -> dict:
    return _worker(led).finish_decryption(inp["response"], inp["userKeyRef"])


def rotate_epoch(inp: Any, dep: dict) -> dict:
    raise AdapterError("NOT_IMPLEMENTED_IN_PHASE", "rotate_epoch is G-phase work; no rotation is performed or simulated")


OPERATIONS = {
    "prepare_request": {"handler": prepare_request, "status": "implemented-e0"},
    "collect_decision": {"handler": collect_decision, "status": "candidate-b-e1-not-unlocked"},
    "release": {"handler": release, "status": "candidate-b-e1-not-unlocked"},
    "encrypt_record": {"handler": encrypt_record, "status": "candidate-b-e1-not-unlocked"},
    "finish_decryption": {"handler": finish_decryption, "status": "candidate-b-e1-not-unlocked"},
    "rotate_epoch": {"handler": rotate_epoch, "status": "not-implemented-in-phase"},
}


def _response(result=None, error=None) -> dict:
    return {"schemaVersion": SCHEMA_VERSION, "ok": error is None, "result": result,
            "error": None if error is None else {"code": error.code, "message": error.message}}


def handle_line(line: str) -> dict:
    """Total function: every input line yields one well-formed response, never an exception."""
    try:
        if len(line.encode("utf-8", "replace")) > MAX_LINE_BYTES:
            raise AdapterError("MALFORMED", "request line exceeds 1 MiB")
        req = _exact(strict_loads(line), REQUEST_FIELDS, "request")
        if req["schemaVersion"] != SCHEMA_VERSION:
            raise AdapterError("MALFORMED", f"schemaVersion must be {SCHEMA_VERSION!r}")
        op = req["operation"]
        if not isinstance(op, str) or op not in OPERATIONS:
            raise AdapterError("MALFORMED", "unknown operation")
        dep = _deployment(req["deploymentManifest"])
        if _PINNED is not None and dep != _PINNED:
            raise AdapterError("WRONG_DESTINATION", "deploymentManifest differs from the deployment this adapter was started with")
        # Revision 4: every operation's input is a closed, canonical type, validated before dispatch; a bad request is
        # MALFORMED, never "unavailable". Unbuilt operations only answer ADAPTER_UNAVAILABLE for a well-formed request.
        try:
            wire.INPUTS[op](req["input"])
        except wire.WireError as e:
            raise AdapterError("MALFORMED", str(e)) from None
        return _response(result=OPERATIONS[op]["handler"](req["input"], dep))
    except AdapterError as e:
        return _response(error=e)
    except Exception:  # noqa: BLE001 - boundary must not leak internals (e.g. key material in a traceback)
        return _response(error=AdapterError("ADAPTER_UNAVAILABLE", "internal adapter failure"))


def _emit(stdout: TextIO, resp: dict) -> None:
    stdout.write(json.dumps(resp, separators=(",", ":")) + "\n")      # ensure_ascii: the output is always plain ASCII
    stdout.flush()


def serve(stdin, stdout: TextIO) -> int:
    """Serve JSON lines. `stdin` is a BINARY stream: lines are read with a bounded readline and decoded here, so invalid UTF-8 or a giant
    line yields one MALFORMED response instead of killing the process (one response per request line always holds)."""
    while True:
        chunk = stdin.readline(MAX_LINE_BYTES + 2)
        if not chunk:
            return 0
        if not chunk.endswith(b"\n") and len(chunk) > MAX_LINE_BYTES:
            while chunk and not chunk.endswith(b"\n"):                # discard the rest of the oversized line without buffering it
                chunk = stdin.readline(1 << 16)
            _emit(stdout, _response(error=AdapterError("MALFORMED", "request line exceeds 1 MiB")))
            continue
        try:
            text = chunk.decode("utf-8")
        except UnicodeDecodeError:
            _emit(stdout, _response(error=AdapterError("MALFORMED", "request is not valid UTF-8")))
            continue
        if not text.strip():
            _emit(stdout, _response(error=AdapterError("MALFORMED", "empty request line")))
        else:
            _emit(stdout, handle_line(text.rstrip("\n")))


def _private_state_dir(path: str) -> str:
    os.makedirs(path, mode=0o700, exist_ok=True)
    if stat.S_IMODE(os.stat(path).st_mode) & 0o077:
        raise SystemExit(f"state dir {path} must not be accessible to group/other (chmod 700)")
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="HMBC agent-2 JSON-lines adapter (symbolic mode)")
    ap.add_argument("--state-dir", required=True, help="private directory (mode 0700) for durable worker state")
    ap.add_argument("--deployment", help="JSON deployment manifest to PIN: the only ledger this process will talk to (required for ledger-backed operations)")
    args = ap.parse_args(argv)
    deployment = None
    if args.deployment:
        with open(args.deployment, "rb") as f:
            deployment = strict_loads(f.read().decode("utf-8"))
    configure(_private_state_dir(args.state_dir), deployment)
    return serve(sys.stdin.buffer, sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
