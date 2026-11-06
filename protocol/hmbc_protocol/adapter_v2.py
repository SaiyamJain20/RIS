"""Successor adapter front-end (HMBC2020 successor, F task 2 slice 6a): the BOUNDARY of the v2 JSON-lines adapter.

PAPER-DERIVED RECONSTRUCTION. One request object per input line, exactly one response object per request line:
  request : {schemaVersion:"v2", operation, input, deploymentManifest}
  response: {schemaVersion:"v2", ok, result, error}   exactly one of result/error is non-null; error = {code, message, reason?, collection?, recorded?}
This module owns strict parsing, the closed envelope, EXPLICIT schema-revision selection, whole-manifest equality with the pinned manifest, the v2 input validators, the reason table, one total `handle_line` and the
serve loop. Operation HANDLERS are INJECTED (`Context.handlers`): wiring the pool, the witness service, the worker store and the open-time checks behind them is the next slice. The carried E adapter
(`adapter.py`, v1) is untouched.

Schema selection is explicit and never guessed: `Context` takes the revision ("v2" or "v2.1") as a REQUIRED argument and checks it against the pinned carrier's marker (`hmbc-ledger-deployment/v2` is valid under
both revisions, `.../v2.1` only under "v2.1"). When the caller also passes the parsed schema, the pinned manifest is validated against the carrier branches OF THAT REVISION (v2: LedgerDeploymentE and
LedgerDeploymentF; v2.1: also LedgerDeploymentEComplete, which the schema must define). A request's manifest is never re-interpreted: it must EQUAL the pinned manifest (any difference is WRONG_DESTINATION).

Input validators follow the published schema (differentially tested against it). Changes from the carried v1 validators: `collect_decision`/`collect_checkpoint` take `witnessSetVersion` "1" or "2" and an optional
`witnessIndex` "0".."3", `attest_grant` an optional `witnessIndex`, `collect_governance` is new (the whole proposed action, never a sequence, timestamp or block), and `finish_decryption` carries a v2 ReleaseResult
(`schemaVersion` "v2"; the carried E validator demands "v1"). Stricter than the schema in one place, on purpose: governance admins must be strictly ascending (BOUNDARY; the schema only says unique).

No handler output is trusted to be well formed beyond being an object; a handler that raises anything but `OperationError`, or returns a non-object, becomes a generic ADAPTER_UNAVAILABLE ("internal adapter failure")
so that no key material or path leaks. No clock, no network, no subprocess.
"""
from __future__ import annotations

import copy
import json
from typing import Any, Callable, TextIO

from . import adapter as _e
from . import wire
from .witness_service import _governance_shape

SCHEMA_VERSION = "v2"
ADAPTER_MODE = "symbolic"
MAX_LINE_BYTES = 1 << 20
REQUEST_FIELDS = {"schemaVersion", "operation", "input", "deploymentManifest"}
OPERATIONS = ("prepare_request", "collect_decision", "collect_checkpoint", "attest_grant", "collect_governance", "release", "encrypt_record", "finish_decryption", "rotate_epoch")
CODES = ("BAD_SIGNATURE", "WRONG_SUBJECT", "WRONG_DESTINATION", "UNKNOWN_AUTHORITY", "STALE_ANCHOR", "STALE_STATE", "EXPIRED", "REPLAY", "POLICY_DENIED", "INSUFFICIENT_QUORUM", "DUPLICATE_SIGNER",
         "WRONG_EPOCH", "NOT_COMMITTED", "ADAPTER_UNAVAILABLE", "NOT_IMPLEMENTED_IN_PHASE", "UNAUTHORIZED_CALLER", "NOT_REGISTERED", "ALREADY_REGISTERED", "REVOKED", "MALFORMED", "WRONG_PROFILE")
REASON_CODE = {"CONFLICT_PINNED": "STALE_STATE", "PROPOSAL_MISMATCH": "STALE_STATE", "WITNESS_SET_MISMATCH": "STALE_STATE", "QUORUM_UNAVAILABLE": "ADAPTER_UNAVAILABLE",
               "WITNESS_FAULTED": "ADAPTER_UNAVAILABLE", "LEDGER_UNREACHABLE": "ADAPTER_UNAVAILABLE", "STORE_MISSING": "ADAPTER_UNAVAILABLE", "STORE_CORRUPT": "ADAPTER_UNAVAILABLE",
               "PROFILE_MISMATCH": "WRONG_PROFILE", "UNSEALED": "WRONG_DESTINATION", "WIRING_MISMATCH": "WRONG_DESTINATION", "GENESIS_MISMATCH": "WRONG_DESTINATION",
               "CODE_MISMATCH": "WRONG_DESTINATION", "MUTATIONS_MISMATCH": "WRONG_DESTINATION", "BUILD_MISMATCH": "WRONG_DESTINATION", "LEGACY_STATE": "WRONG_DESTINATION",
               "BINDING_MISMATCH": "WRONG_DESTINATION", "OWNER_MISMATCH": "WRONG_DESTINATION", "BUILD_PIN_INVALID": "MALFORMED"}
MARKER = {"v2": "hmbc-ledger-deployment/v2", "v2.1": "hmbc-ledger-deployment/v2.1"}
BRANCHES = {"v2": ("LedgerDeploymentE", "LedgerDeploymentF"), "v2.1": ("LedgerDeploymentE", "LedgerDeploymentF", "LedgerDeploymentEComplete")}
GENERIC_FAILURE = ("ADAPTER_UNAVAILABLE", "internal adapter failure")
RESPONSE_TYPE = {"prepare_request": "PrepareRequestResponse", "collect_decision": "CollectDecisionResponse", "collect_checkpoint": "CollectCheckpointResponse", "attest_grant": "AttestGrantResponse",
                 "collect_governance": "CollectGovernanceResponse", "release": "ReleaseResponse", "encrypt_record": "EncryptRecordResponse", "finish_decryption": "FinishDecryptionResponse",
                 "rotate_epoch": "RotateEpochResponse"}


class OperationError(Exception):
    """A refusal with its closed v1 code, an optional reason (consistent with the code), a message, and the two evidence members the schema allows: `recorded` (CONFLICT_PINNED only) and `collection`
    (QUORUM_UNAVAILABLE only)."""

    def __init__(self, code, message, *, reason=None, collection=None, recorded=None):
        if code not in CODES:
            raise ValueError("unknown error code")
        if not isinstance(message, str) or not message:
            raise ValueError("an error needs a non-empty message")
        if reason is not None and (reason not in REASON_CODE or REASON_CODE[reason] != code):
            raise ValueError("the reason is unknown or belongs to another code")
        if recorded is not None and reason != "CONFLICT_PINNED":
            raise ValueError("`recorded` belongs to CONFLICT_PINNED only")
        if collection is not None and reason != "QUORUM_UNAVAILABLE":
            raise ValueError("`collection` belongs to QUORUM_UNAVAILABLE only")
        super().__init__(message)
        self.code, self.message, self.reason, self.collection, self.recorded = code, message, reason, collection, recorded


def _malformed(text):
    return OperationError("MALFORMED", text)


# ---- inputs ---------------------------------------------------------------------------------------------------------------------------------------------------------------
def _release_result_v2(v):
    """The v2 ReleaseResult (the carried E validator demands schemaVersion "v1")."""
    return wire._obj(v, dict(schemaVersion=wire._e_const("v2"), adapterMode=wire._e_const("symbolic"), requestDigest=wire.hash32, grantId=wire.hash32, dataId=wire.hash32, ciphertextDigest=wire.hash32,
                             recipientKeyHash=wire.hash32, keyEpoch=wire._e_const("0"), responseEnvelope=wire.symbolic_envelope), "ReleaseResult")


def _selector(v):
    if not isinstance(v, str) or v not in ("0", "1", "2", "3"):
        raise wire.WireError("MALFORMED: witnessIndex must be one of '0'..'3'")


def _version(v):
    if not isinstance(v, str) or v not in ("1", "2"):
        raise wire.WireError("MALFORMED: witnessSetVersion must be '1' or '2'")


def _closed(v, fields, what):
    return wire._obj(v, fields, what)


def _with_optionals(v, core, optionals, what):
    """Validate `v` as the closed object `core` plus any subset of `optionals` ({name: validator})."""
    if not isinstance(v, dict):
        raise wire.WireError(f"MALFORMED: {what}: object expected")
    present = {k: optionals[k] for k in v if k in optionals}
    return _closed(v, {**core, **present}, what)


def _decision(v):
    return _with_optionals(v, dict(requestDigest=wire.hash32), dict(witnessSetVersion=_version, witnessIndex=_selector), "CollectDecisionInput")


def _checkpoint(v):
    return _with_optionals(v, {}, dict(witnessSetVersion=_version, witnessIndex=_selector), "CollectCheckpointInput")


def _attest(v):
    return _with_optionals(v, dict(grantId=wire.hash32), dict(witnessIndex=_selector), "AttestGrantInput")


def _governance(v):
    if not isinstance(v, dict):
        raise wire.WireError("MALFORMED: CollectGovernanceInput: object expected")
    core = {k: x for k, x in v.items() if k != "witnessIndex"}
    if "witnessIndex" in v:
        _selector(v["witnessIndex"])
    _governance_shape(core)
    if core["witnessSetVersion"] != "2":
        raise wire.WireError("MALFORMED: governance needs witnessSetVersion '2'")
    return v


def _finish(v):
    return _closed(v, dict(response=_release_result_v2, userKeyRef=wire.user_key_ref), "FinishDecryptionInput")


VALIDATORS: dict[str, Callable[[Any], Any]] = {
    "prepare_request": wire.prepare_request_input, "collect_decision": _decision, "collect_checkpoint": _checkpoint, "attest_grant": _attest, "collect_governance": _governance,
    "release": wire.release_input, "encrypt_record": wire.encrypt_record_input, "finish_decryption": _finish, "rotate_epoch": wire.rotate_epoch_input}


def validate_input(op, inp):
    """Raises OperationError(MALFORMED) for anything the operation's closed input type does not accept."""
    try:
        VALIDATORS[op](inp)
    except (wire.WireError, TypeError, KeyError, ValueError, AttributeError) as e:
        raise _malformed(str(e) if isinstance(e, wire.WireError) else "input is not a well-formed " + op + " input") from None


# ---- the pinned context ---------------------------------------------------------------------------------------------------------------------------------------------
def published_format_checker():
    """A jsonschema FormatChecker that KNOWS the published custom formats. Without this a `format` keyword the checker does not know is silently ignored (an annotation), and a value such as 2**64 passes the
    pattern and the length of `Uint64`. Registered, with the carried wire validators as the single source of the rule: uint8, uint32, uint64, uint256 (canonical decimal within the width) and
    canonical-signature (lowercase 0x + 130 hex, 0 < r < n, 0 < s <= n/2, v in 27/28). NOT registered (still annotations, stated limit): user-key-ref, evidence-path, uri and date-time handled by the
    library's own checkers only when their optional packages exist."""
    import jsonschema
    formats = jsonschema.FormatChecker()

    def width(bits):
        def check(v):
            if not isinstance(v, str):
                return True                                   # `type` decides non-strings, not the format
            try:
                wire.uint(v, bits)
            except wire.WireError:
                return False
            return True
        return check

    for name, bits in (("uint8", 8), ("uint32", 32), ("uint64", 64), ("uint256", 256)):
        formats.checks(name)(width(bits))

    @formats.checks("canonical-signature")
    def _signature(v):
        if not isinstance(v, str):
            return True
        try:
            wire.signature(v)
        except wire.WireError:
            return False
        return True
    return formats


class Context:
    """The pinned deployment manifest, the EXPLICITLY selected schema revision and the injected handlers. `schema` (the parsed published schema, optional) lets the pinned manifest be validated against the
    carrier branches of the selected revision; without it only the marker rule and the structural minimum apply. With `schema` every response is also checked against the published response type of its
    operation (`checked`), unless `check_responses=False` (TEST use only: a stub handler that returns a deliberately small dict); without `schema` nothing is checked."""

    def __init__(self, *, manifest, schema_revision, handlers, schema=None, check_responses=True):
        if schema_revision not in MARKER or not isinstance(schema_revision, str):
            raise ValueError("schema_revision must be 'v2' or 'v2.1'")
        if not isinstance(manifest, dict):
            raise ValueError("the pinned manifest must be an object")
        marker = manifest.get("schemaVersion")
        if marker not in MARKER.values():
            raise ValueError("the pinned manifest names no known carrier marker")
        if marker == MARKER["v2.1"] and schema_revision != "v2.1":
            raise ValueError("the v2.1 carrier marker needs schema revision v2.1")
        try:
            _e._deployment(manifest)
        except _e.AdapterError as e:
            raise ValueError("the pinned manifest lacks what binds a request: " + e.message) from None
        if schema is not None:
            self._validate_against(schema, manifest, schema_revision)
        if not isinstance(check_responses, bool):
            raise ValueError("check_responses must be a boolean")
        self._response_validators = self._build_response_validators(schema) if schema is not None and check_responses else None
        if not isinstance(handlers, dict) or not set(handlers) <= set(OPERATIONS) or not all(callable(h) for h in handlers.values()):
            raise ValueError("handlers must map known operation names to callables")
        self.manifest, self.schema_revision, self.handlers = copy.deepcopy(manifest), schema_revision, dict(handlers)

    @staticmethod
    def _build_response_validators(schema):
        """One validator per published response type, built ONCE: `AdapterResponse` (any operation, also for a line that fails before its operation is known) and the nine `<Op>Response` types."""
        import jsonschema
        defs = schema.get("$defs", {})
        names = ("AdapterResponse",) + tuple(RESPONSE_TYPE.values())
        missing = [n for n in names if n not in defs]
        if missing:
            raise ValueError(f"the supplied schema does not define {missing}: it cannot validate responses")
        formats = published_format_checker()
        return {n: jsonschema.Draft202012Validator({"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": "#/$defs/" + n, "$defs": defs}, format_checker=formats) for n in names}

    def checked(self, op, response):
        """With the published schema supplied: the response if it is valid for the operation's published response type, else the generic internal failure (nothing of the invalid value leaks). Without the
        schema (an explicit, tested limit) the response is returned unchecked."""
        if self._response_validators is None:
            return response
        try:
            if self._response_validators[RESPONSE_TYPE.get(op, "AdapterResponse")].is_valid(response):
                return response
        except Exception:  # noqa: BLE001 - a validator that cannot decide (for example a pathological value) is a refusal to emit
            pass
        return _generic()

    @staticmethod
    def _validate_against(schema, manifest, revision):
        import jsonschema
        defs = schema.get("$defs", {})
        missing = [b for b in BRANCHES[revision] if b not in defs]
        if missing:
            raise ValueError(f"the supplied schema does not define {missing}: it cannot serve revision {revision}")
        doc = {"$schema": "https://json-schema.org/draft/2020-12/schema", "oneOf": [{"$ref": "#/$defs/" + b} for b in BRANCHES[revision]], "$defs": defs}
        if not jsonschema.Draft202012Validator(doc).is_valid(manifest):
            raise ValueError(f"the pinned manifest is not a valid {revision} carrier")


# ---- the line handler -----------------------------------------------------------------------------------------------------------------------------------------------
def _response(result=None, error=None):
    if error is None:
        return {"schemaVersion": SCHEMA_VERSION, "ok": True, "result": result, "error": None}
    err = {"code": error.code, "message": error.message}
    if error.reason is not None:
        err["reason"] = error.reason
    if error.collection is not None:
        err["collection"] = error.collection
    if error.recorded is not None:
        err["recorded"] = error.recorded
    return {"schemaVersion": SCHEMA_VERSION, "ok": False, "result": None, "error": err}


def _generic():
    return _response(error=OperationError(*GENERIC_FAILURE))


def _strict_loads(line):
    try:
        return _e.strict_loads(line)
    except _e.AdapterError as e:
        raise _malformed(e.message) from None


def handle_line(line: str, ctx: Context) -> dict:
    """Total function: every input line yields one well-formed response, never an exception. With the published schema in the Context, each response is checked against its operation's published response
    type before it is returned (`Context.checked`)."""
    known = None                                   # the operation once the envelope names a known one
    try:
        if len(line.encode("utf-8", "replace")) > MAX_LINE_BYTES:
            raise _malformed("request line exceeds 1 MiB")
        obj = _strict_loads(line)
        if not isinstance(obj, dict) or set(obj) != REQUEST_FIELDS:
            raise _malformed("request: expected exactly " + str(sorted(REQUEST_FIELDS)))
        if obj["schemaVersion"] != SCHEMA_VERSION:
            raise _malformed(f"schemaVersion must be {SCHEMA_VERSION!r}")
        op = obj["operation"]
        if not isinstance(op, str) or op not in OPERATIONS:
            raise _malformed("unknown operation")
        known = op
        try:
            _e._deployment(obj["deploymentManifest"])
        except _e.AdapterError as e:
            raise _malformed(e.message) from None
        if obj["deploymentManifest"] != ctx.manifest:
            raise OperationError("WRONG_DESTINATION", "deploymentManifest differs from the deployment this adapter was started with")
        validate_input(op, obj["input"])
        if op == "rotate_epoch":
            raise OperationError("NOT_IMPLEMENTED_IN_PHASE", "rotate_epoch is G-phase work; no rotation is performed or simulated")
        handler = ctx.handlers.get(op)
        if handler is None:
            raise OperationError("ADAPTER_UNAVAILABLE", f"{op} is not wired in this process")
        result = handler(copy.deepcopy(obj["input"]), ctx)
        if not isinstance(result, dict):
            return _generic()
        return ctx.checked(known, _response(result=result))
    except OperationError as e:
        return ctx.checked(known, _response(error=e))
    except Exception:  # noqa: BLE001 - the boundary must not leak internals (key material, paths) through a traceback or a message
        return _generic()


def _emit(stdout: TextIO, resp: dict) -> None:
    stdout.write(json.dumps(resp, separators=(",", ":")) + "\n")      # ensure_ascii: the output is always plain ASCII
    stdout.flush()


def serve(stdin, stdout: TextIO, ctx: Context) -> int:
    """Serve JSON lines. `stdin` is a BINARY stream: lines are read with a bounded readline and decoded here, so invalid UTF-8 or a giant line yields one MALFORMED response instead of killing the process."""
    while True:
        chunk = stdin.readline(MAX_LINE_BYTES + 2)
        if not chunk:
            return 0
        if not chunk.endswith(b"\n") and len(chunk) > MAX_LINE_BYTES:
            while chunk and not chunk.endswith(b"\n"):                # discard the rest of the oversized line without buffering it
                chunk = stdin.readline(1 << 16)
            _emit(stdout, _response(error=_malformed("request line exceeds 1 MiB")))
            continue
        try:
            text = chunk.decode("utf-8")
        except UnicodeDecodeError:
            _emit(stdout, _response(error=_malformed("request is not valid UTF-8")))
            continue
        if not text.strip():
            _emit(stdout, _response(error=_malformed("empty request line")))
        else:
            _emit(stdout, handle_line(text.rstrip("\n"), ctx))
