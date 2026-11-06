"""Successor adapter handlers, part 1 (HMBC2020 successor, F task 2 slice 6b-1): `prepare_request` and the key worker's three operations behind `adapter_v2`.

PAPER-DERIVED RECONSTRUCTION. These handlers REUSE the carried E code unchanged (`adapter.prepare_request`, `worker.Worker`) and add exactly two things:
  * D-4, the RELABEL of the result from schemaVersion "v1" to "v2". The published v2 result types carry const "v2"; the carried E validators and handlers produce "v1". The E result is first checked with
    the carried E result validator, so a worker that returns anything else is an internal failure, never relabelled garbage. A `finish_decryption` response arrives as a v2 ReleaseResult and is relabelled back
    to v1 for the carried worker, which validates a v1 one.
  * the mapping of every E failure onto the closed v2 errors without leaking internals: an E error keeps its closed code and message; a ledger rejection keeps its code when it is one of the closed codes
    (otherwise ADAPTER_UNAVAILABLE); a chain failure is ADAPTER_UNAVAILABLE with a fixed message (the E text names a URL); anything else propagates and `adapter_v2` turns it into the generic failure.
The worker is created per call by an injected factory `factory(ctx) -> Worker`: how it is opened (the D50 binding of its directory, the E `Ledger`) is the startup wiring of the next slice.
The witness operations (collect_*, attest_grant, collect_governance) are not here.
"""
from __future__ import annotations

from . import adapter as _e
from . import chain, wire
from .adapter_v2 import CODES, OperationError
from .worker import WorkerError

LEDGER_UNAVAILABLE = "the ledger is unreachable or returned an error"


def _relabel(result, validator):
    """The carried E result, checked with its E validator, with schemaVersion "v2"."""
    validator(result)
    return dict(result, schemaVersion="v2")


def _guard(fn):
    try:
        return fn()
    except (_e.AdapterError, WorkerError) as e:
        if e.code not in CODES:
            raise RuntimeError("unknown error code") from None
        raise OperationError(e.code, e.message) from None
    except chain.Rejected as e:
        raise OperationError(e.code if e.code in wire.ERROR_CODES else "ADAPTER_UNAVAILABLE", f"the ledger rejected the call: {e.code}") from None
    except chain.ChainError:
        raise OperationError("ADAPTER_UNAVAILABLE", LEDGER_UNAVAILABLE) from None


def prepare_request(inp, ctx):
    """The user's signing client. It signs only for the referenced user key and only against the pinned deployment (the carried E checks)."""
    return _guard(lambda: _relabel(_e.prepare_request(inp, ctx.manifest), wire.prepare_request_result))


def worker_handlers(factory):
    """{encrypt_record, release, finish_decryption} handlers over a worker made by `factory(ctx)` for each call."""
    def encrypt_record(inp, ctx):
        return _guard(lambda: _relabel(factory(ctx).encrypt_record(inp["record"], inp["policy"], inp["keyEpoch"]), wire.encrypt_record_result))

    def release(inp, ctx):
        return _guard(lambda: _relabel(factory(ctx).release(inp["grantId"]), wire.release_result))

    def finish_decryption(inp, ctx):
        response = dict(inp["response"], schemaVersion="v1")             # the carried worker validates a v1 ReleaseResult
        return _guard(lambda: _relabel(factory(ctx).finish_decryption(response, inp["userKeyRef"]), wire.finish_decryption_result))

    return {"encrypt_record": encrypt_record, "release": release, "finish_decryption": finish_decryption}
