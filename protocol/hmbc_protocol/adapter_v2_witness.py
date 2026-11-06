"""Successor adapter handlers, part 2 (HMBC2020 successor, F task 2 slice 6b-2): `collect_checkpoint`, `collect_decision`, `attest_grant` and `collect_governance` behind `adapter_v2`.

PAPER-DERIVED RECONSTRUCTION. Each operation derives the PROPOSAL from the proposer's own reads (the injected ledger `view`; for a governance action the operator's whole action is the proposal and nothing
is derived), then runs in one of two modes:
  * POOL MODE (no `witnessIndex`): one `witness_pool.Collection` driven by `witness_pool_driver.run_collection` over a fresh transport from the injected `transport_factory(kind)`. Success returns exactly
    three signatures (each recovered to a distinct witness of the injected four addresses by the collection itself) and the published `collection` evidence. A pool that cannot reach three signatures is
    ADAPTER_UNAVAILABLE / QUORUM_UNAVAILABLE carrying that evidence; one that cannot even start (2 s or less of validity) is EXPIRED and contacts nobody.
  * SINGLE-WITNESS MODE (`witnessIndex` given): one write to that witness in round 1 and one reply, 5 s timeout (the pool's reply timeout). The signature is returned only when it recovers to that
    witness's address over the digest of the proposal the proposer sent; the result has one signature and no `collection`. Any other reply is a refusal or a failure, never a signature.
The pool -> witness channel carries a proposal and is internal (the public v2 inputs have no proposal field), which is why the transport is abstract: the real transport (supervised channels to four witness
processes, a host-monotonic clock) belongs to the integrated run. Nothing here reads a clock, starts a thread or opens a socket or a file.

EXPLICIT CHOICES where F0 and the published schema are silent (reconstruction choices, not findings):
  * only the `repaired-f` profile is wired; any other manifest answers ADAPTER_UNAVAILABLE "not wired for this deployment profile" (E collection is the carried E adapter's business);
  * a declared `witnessSetVersion` other than "2" is STALE_STATE / WITNESS_SET_MISMATCH and nobody is contacted (the F witness set is version 2);
  * the pool window is the proposal's own `expiresAt` (checkpoint, decision, governance) and, for a receipt, which has no expiry of its own, the DBC's latest block timestamp + 60 s;
  * the ledger time for the window is the DBC's latest block timestamp, the PBC's for a governance action (the target ledger of the action, as the witness checks it);
  * `recorded` is returned only from a single-witness CONFLICT_PINNED refusal of a checkpoint whose recorded value verifies (the published decision/receipt/governance responses forbid it); a refusal
    with an unknown code, an inconsistent reason or a `recorded` anywhere else is an INVALID reply and fails as ADAPTER_UNAVAILABLE;
  * a failure of the proposer's own derivation keeps the witness-service error class (`WitnessRefusal`); a transport that raises, or any other defect, propagates and `adapter_v2` turns it into its generic
    failure (no path or traceback leaks).
The four witness addresses come from the caller (the startup wiring reads them from the ledger's witness set; that read is the next slice).
"""
from __future__ import annotations

import re

from . import pool_core as core
from . import witness_pool as wp
from . import witness_service as svc
from .adapter_v2 import CODES, REASON_CODE, OperationError
from .witness_pool_driver import run_collection

_ADDR = re.compile(r"0x[0-9a-f]{40}")
PROFILE = "repaired-f"
SET_VERSION = "2"
RECEIPT_WINDOW_S = 60
RESULT_MEMBER = {"checkpoint": "checkpoint", "decision": "decision", "receipt": "receipt", "governance": "governanceAction"}


def _recover_over(digest_of):
    def recover(message, signature):
        from . import eip712
        try:
            return eip712.recover(digest_of(message), signature)
        except (ValueError, KeyError, TypeError):
            return None
    return recover


def _recover(kind, deployment):
    if kind == "checkpoint":
        return wp.make_recover("StateCheckpoint", deployment)
    if kind == "decision":
        return wp.make_recover("AccessDecision", deployment)
    if kind == "receipt":
        return _recover_over(lambda m: svc._receipt_digest(svc._receipt_shape(m), deployment))
    return _recover_over(lambda m: svc._governance_digest(svc._governance_shape(m), deployment))


def _from_refusal(e):
    return OperationError(e.code, e.message, reason=e.reason)


def _invalid(index):
    return OperationError("ADAPTER_UNAVAILABLE", f"witness {index} sent an invalid reply")


def witness_handlers(*, view, witnesses, transport_factory, proposer_ttl=svc.DEFAULT_PROPOSER_TTL):
    """{collect_checkpoint, collect_decision, attest_grant, collect_governance} handlers. `view` is the proposer's own ledger view, `witnesses` the four distinct lowercase witness addresses in index
    order and `transport_factory(kind)` makes a fresh transport (send, cancel, next_event) for one call."""
    if not (isinstance(witnesses, list) and len(witnesses) == core.WITNESS_COUNT and all(isinstance(a, str) and _ADDR.fullmatch(a) for a in witnesses) and len(set(witnesses)) == len(witnesses)):
        raise ValueError("witnesses must be four distinct lowercase addresses in index order")
    if not callable(transport_factory):
        raise ValueError("transport_factory must be callable")
    witnesses = list(witnesses)

    def derive(kind, inp, deployment):
        """(proposal, ledger_now, proposal_expires_at, extra result members)"""
        try:
            if kind == "governance":
                proposal = {k: (list(v) if isinstance(v, list) else v) for k, v in inp.items() if k != "witnessIndex"}
                return proposal, int(view.observe("pbc")["timestamp"]), int(proposal["expiresAt"]), {}
            if kind == "checkpoint":
                proposal = svc.derive_checkpoint(view, deployment, ttl=proposer_ttl)
                return proposal, int(view.observe("dbc")["timestamp"]), int(proposal["expiresAt"]), {}
            if kind == "decision":
                proposal, records = svc.derive_decision(view, deployment, inp["requestDigest"], witness_set_version=SET_VERSION)
                return proposal, int(view.observe("dbc")["timestamp"]), int(proposal["expiresAt"]), {"credentialRecords": records}
            proposal = svc.derive_receipt(view, deployment, inp["grantId"], witness_set_version=SET_VERSION)
            now = int(view.observe("dbc")["timestamp"])
            return proposal, now, now + RECEIPT_WINDOW_S, {}
        except svc.WitnessRefusal as e:
            raise _from_refusal(e) from None
        except svc.LedgerUnreachable as e:
            raise _from_refusal(svc._unreachable(e)) from None

    def single(kind, index, proposal, deployment):
        transport = transport_factory(kind)
        transport.send(index, 1, dict(proposal))
        event = transport.next_event(core.REPLY_TIMEOUT_MS)
        if event is None:
            transport.cancel(index, 1)
            raise OperationError("ADAPTER_UNAVAILABLE", f"witness {index} did not answer within {core.REPLY_TIMEOUT_MS // 1000} s")
        _, witness, round_no, reply = event
        if witness != index or round_no != 1 or not isinstance(reply, dict):
            raise _invalid(index)
        recover = _recover(kind, deployment)
        if reply.get("type") == "signature":
            if set(reply) != {"type", "message", "signature"} or not isinstance(reply["signature"], str) or not isinstance(reply["message"], dict):
                raise _invalid(index)
            if core.canonical_message(reply["message"]) != core.canonical_message(proposal) or recover(reply["message"], reply["signature"]) != witnesses[index]:
                raise _invalid(index)
            return [reply["signature"]]
        if reply.get("type") == "error":
            _refusal_of_witness(kind, index, reply, deployment)
        raise _invalid(index)

    def _refusal_of_witness(kind, index, reply, deployment):
        if not set(reply) <= {"type", "code", "reason", "recorded"} or reply.get("code") not in CODES:
            raise _invalid(index)
        code, reason, recorded = reply["code"], reply.get("reason"), reply.get("recorded")
        if reason is not None and REASON_CODE.get(reason) != code:
            raise _invalid(index)
        if recorded is not None:
            if not (kind == "checkpoint" and code == "STALE_STATE" and reason == "CONFLICT_PINNED" and isinstance(recorded, dict) and set(recorded) == {"message", "signature"}
                    and isinstance(recorded["signature"], str) and isinstance(recorded["message"], dict)
                    and all(isinstance(k, str) and isinstance(v, str) for k, v in recorded["message"].items())
                    and _recover("checkpoint", deployment)(recorded["message"], recorded["signature"]) == witnesses[index]):
                raise _invalid(index)
        text = f"witness {index} refused: {code}" + (f" ({reason})" if reason else "")
        raise OperationError(code, text, reason=reason, recorded=recorded)

    def pool(kind, proposal, now, expires, deployment):
        try:
            collection = wp.Collection(witnesses=witnesses, recover=_recover(kind, deployment), proposal=proposal, ledger_now_at_start=now, proposal_expires_at=expires,
                                       adoption=(kind == "checkpoint"), witness_set_version=SET_VERSION)
        except wp.CollectionRefused as e:
            raise OperationError(e.code, e.message, reason=e.reason) from None
        result = run_collection(collection, transport_factory(kind))
        if not result["ok"]:
            raise OperationError("ADAPTER_UNAVAILABLE", result["failure"], reason="QUORUM_UNAVAILABLE", collection=result["collection"])
        return result["message"], result["signatures"], result["collection"]

    def make(kind, op):
        def handler(inp, ctx):
            deployment = ctx.manifest
            if deployment.get("profile") != PROFILE:
                raise OperationError("ADAPTER_UNAVAILABLE", f"{op} is not wired for this deployment profile")
            if inp.get("witnessSetVersion", SET_VERSION) != SET_VERSION:
                raise OperationError("STALE_STATE", "the witness set version of this deployment is 2", reason="WITNESS_SET_MISMATCH")
            proposal, now, expires, extra = derive(kind, inp, deployment)
            result = {"schemaVersion": "v2", "adapterMode": "symbolic"}
            if "witnessIndex" in inp:
                index = int(inp["witnessIndex"])
                result[RESULT_MEMBER[kind]] = dict(proposal)
                result["signatures"] = single(kind, index, proposal, deployment)
            else:
                message, signatures, coll = pool(kind, proposal, now, expires, deployment)
                result[RESULT_MEMBER[kind]] = message
                result["signatures"] = signatures
                result["collection"] = coll
            result.update(extra)
            return result
        return handler

    return {"collect_checkpoint": make("checkpoint", "collect_checkpoint"), "collect_decision": make("decision", "collect_decision"), "attest_grant": make("receipt", "attest_grant"),
            "collect_governance": make("governance", "collect_governance")}
