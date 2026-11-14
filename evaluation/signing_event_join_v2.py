"""Join captured witness RPC signature replies to declared signed generations.

Paper-derived HMBC2020 reconstruction, internal evaluator API. The caller
supplies captured JSON-lines plus a separately verified signed-history export.
This joins each captured successful reply to one exact history digest and its
store-reported ledger observation. It does not authenticate the capture, prove
that the transcript or store export is complete, or establish persistence or
native source-state truth; use witness_native_v2 for supplied raw block/call
checks, with those same limits.
"""
import json
import re

from evaluation.signing_context_v2 import verify_bound_signature
from evaluation.witness_history_v2 import verify_signed_history

_KINDS = {
    "decision": "AccessDecision",
    "checkpoint": "StateCheckpoint",
    "receipt": "GrantReceipt",
    "governance": "GovernanceAction",
}
_KEYS = {
    "AccessDecision": "requestDigest",
    "StateCheckpoint": "sequence",
    "GrantReceipt": "requestDigest",
    "GovernanceAction": "nonce",
}
_SIGNATURE = re.compile(r"0x[0-9a-f]{130}\Z")
_DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)\Z")


def _require(condition, message):
    if not condition:
        raise ValueError("Invalid witness signing-event capture: " + message)


def _closed(value, fields, label):
    _require(isinstance(value, dict) and set(value) == set(fields), label + " fields")


def _pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def _constant(_value):
    raise ValueError("Invalid witness signing-event capture: non-finite JSON value")


def _line(value, label):
    _require(isinstance(value, str) and value and len(value.encode("utf-8")) <= 1 << 20,
             label + " line size/type")
    _require("\n" not in value and "\r" not in value, label + " must contain one JSON line")
    try:
        decoded = json.loads(value, object_pairs_hook=_pairs, parse_constant=_constant)
    except (json.JSONDecodeError, RecursionError) as error:
        raise ValueError("Invalid witness signing-event capture: malformed " + label) from error
    return decoded


def _record_index(evidence):
    index = {}
    for row in evidence["superseded"] + evidence["conflicts"]:
        for signed in row["digests"]:
            index[(row["type"], signed["digest"])] = (row, signed)
    return index


def join_signing_events(capture, evidence, *, manifest, observations, expected_owner,
                        compiled_max_admins=None):
    """Join captured process RPC lines to an exact digest/generation in history.

    Capture format is ``hmbc-witness-rpc-capture/v1`` with ordered events. Each
    event stores its one-based decimal sequence and the raw JSON request/response
    lines without line terminators. Successful replies must verify under the
    caller-pinned witness and match a digest, signature, effect, key, domain and
    witness-set version in the separately verified evidence. Error replies are
    counted but do not establish signing or a history join.
    """
    _closed(capture, ("schemaVersion", "events"), "capture")
    _require(capture["schemaVersion"] == "hmbc-witness-rpc-capture/v1", "capture schema version")
    _require(isinstance(capture["events"], list), "events array")

    history = verify_signed_history(
        evidence,
        manifest=manifest,
        observations=observations,
        expected_owner=expected_owner,
        compiled_max_admins=compiled_max_admins,
    )
    owner = expected_owner.removeprefix("witness:")
    by_digest = _record_index(evidence)
    joined = []
    refusal_replies = 0
    seen_digests = set()

    for expected_sequence, event in enumerate(capture["events"], 1):
        _closed(event, ("sequence", "requestLine", "responseLine"), "event")
        sequence = event["sequence"]
        _require(isinstance(sequence, str) and _DECIMAL.fullmatch(sequence) is not None
                 and int(sequence) == expected_sequence, "event sequence must be contiguous from 1")
        request = _line(event["requestLine"], "request")
        response = _line(event["responseLine"], "response")
        _closed(request, ("schemaVersion", "id", "round", "kind", "message"), "request")
        _closed(response, ("schemaVersion", "id", "reply"), "response")
        _require(request["schemaVersion"] == "hmbc-witness-rpc/v1"
                 and response["schemaVersion"] == "hmbc-witness-rpc/v1", "RPC schema version")
        request_id = request["id"]
        _require(isinstance(request_id, int) and not isinstance(request_id, bool) and request_id >= 0,
                 "request id")
        _require(type(response["id"]) is int and response["id"] == request_id,
                 "request/response id mismatch")
        _require(type(request["round"]) is int and request["round"] in (1, 2), "request round")
        _require(isinstance(request["kind"], str) and request["kind"] in _KINDS
                 and isinstance(request["message"], dict), "request kind/message")

        reply = response["reply"]
        _require(isinstance(reply, dict) and isinstance(reply.get("type"), str), "reply shape")
        if reply["type"] == "error":
            _closed(reply, ("type", "code", "reason", "recorded"), "error reply")
            _require(isinstance(reply["code"], str) and reply["code"], "error code")
            _require(reply["reason"] is None or isinstance(reply["reason"], str), "error reason")
            refusal_replies += 1
            continue

        _closed(reply, ("type", "message", "signature"), "signature reply")
        _require(reply["type"] == "signature" and isinstance(reply["message"], dict), "signature reply type/message")
        _require(reply["message"] == request["message"], "request/response message mismatch")
        signature = reply["signature"]
        _require(isinstance(signature, str) and _SIGNATURE.fullmatch(signature) is not None,
                 "signature encoding")
        name = _KINDS[request["kind"]]
        message = reply["message"]
        checked = verify_bound_signature(
            name,
            message,
            signature,
            owner=owner,
            manifest=manifest,
            observations=observations,
            compiled_max_admins=compiled_max_admins,
        )
        digest = checked["digest"]
        indexed = by_digest.get((name, digest))
        _require(indexed is not None, "signature reply has no matching history digest")
        row, stored = indexed
        key = message[_KEYS[name]]
        effect = {field: value for field, value in message.items()
                  if field not in (_KEYS[name], "expiresAt")}
        _require(row["domainSeparator"] == checked["domainSeparator"], "history domain mismatch")
        _require(row["witnessSetVersion"] == message["witnessSetVersion"], "history witness-set version mismatch")
        _require(row["keyField"] == key and row["effect"] == effect, "history generation/effect mismatch")
        _require(stored["signature"] == signature, "history signature mismatch")
        seen_digests.add(digest)
        joined.append({
            "sequence": sequence,
            "type": name,
            "digest": digest,
            "witness": expected_owner,
            "domainSeparator": row["domainSeparator"],
            "witnessSetVersion": row["witnessSetVersion"],
            "keyField": row["keyField"],
            "generationSeq": row.get("seq"),
            "observation": stored["observation"],
        })

    return {
        "capturedEvents": len(capture["events"]),
        "signatureReplies": len(joined),
        "refusalReplies": refusal_replies,
        "joined": joined,
        "history": history,
        "unjoinedHistoryDigests": sum(len(row["digests"]) for row in evidence["superseded"] + evidence["conflicts"])
        - len(seen_digests),
        "transcriptCompletenessEstablished": False,
        "captureAuthenticated": False,
    }
