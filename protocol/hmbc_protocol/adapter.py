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

from . import eip712, keys, messages, wire

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
    assert eip712.recover(digest, signature) == signer  # never emit a signature that does not verify
    return {"schemaVersion": SCHEMA_VERSION, "adapterMode": ADAPTER_MODE, "request": req,
            "requestDigest": "0x" + digest.hex(), "signature": signature, "signer": signer}


def _unavailable(name: str):
    def handler(inp: Any, dep: dict) -> dict:
        raise AdapterError("ADAPTER_UNAVAILABLE", f"{name} is B-E1 work and is not implemented before E0 unlocks E1")
    return handler


def rotate_epoch(inp: Any, dep: dict) -> dict:
    raise AdapterError("NOT_IMPLEMENTED_IN_PHASE", "rotate_epoch is G-phase work; no rotation is performed or simulated")


OPERATIONS = {
    "prepare_request": {"handler": prepare_request, "status": "implemented-e0"},
    "collect_decision": {"handler": _unavailable("collect_decision"), "status": "planned-b-e1"},
    "release": {"handler": _unavailable("release"), "status": "planned-b-e1"},
    "encrypt_record": {"handler": _unavailable("encrypt_record"), "status": "planned-b-e1"},
    "finish_decryption": {"handler": _unavailable("finish_decryption"), "status": "planned-b-e1"},
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


def serve(stdin: TextIO, stdout: TextIO) -> int:
    for line in stdin:
        if not line.strip():
            stdout.write(json.dumps(_response(error=AdapterError("MALFORMED", "empty request line")), separators=(",", ":")) + "\n")
        else:
            stdout.write(json.dumps(handle_line(line.rstrip("\n")), separators=(",", ":")) + "\n")
        stdout.flush()
    return 0


def _private_state_dir(path: str) -> str:
    os.makedirs(path, mode=0o700, exist_ok=True)
    if stat.S_IMODE(os.stat(path).st_mode) & 0o077:
        raise SystemExit(f"state dir {path} must not be accessible to group/other (chmod 700)")
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="HMBC agent-2 JSON-lines adapter (symbolic mode)")
    ap.add_argument("--state-dir", required=True, help="private directory for durable worker state (unused at E0)")
    args = ap.parse_args(argv)
    _private_state_dir(args.state_dir)
    return serve(sys.stdin, sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
