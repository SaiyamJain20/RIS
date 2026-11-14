"""Validate a caller-sealed RPC capture before the synthetic signing/history join.

The receipt detects later edits and omissions relative to a separately supplied
event count. Both the receipt and count are caller-supplied; neither authenticates
the capture source or proves that the source counter is complete.
"""
import hashlib
import json
import re

from evaluation.signing_event_join_v2 import join_signing_events

_DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)\Z")
_RECEIPT_FIELDS = {"schemaVersion", "eventCount", "sourceEventCount", "captureSha256"}


def _require(condition, message):
    if not condition:
        raise ValueError("Invalid sealed signing capture: " + message)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal_capture(capture, *, observed_event_count):
    """Create a reproducibility receipt using a separately observed event count."""
    _require(isinstance(capture, dict) and isinstance(capture.get("events"), list), "capture shape")
    _require(type(observed_event_count) is int and observed_event_count >= 0, "source event count")
    return {
        "schemaVersion": "hmbc-witness-rpc-receipt/v1",
        "eventCount": str(len(capture["events"])),
        "sourceEventCount": str(observed_event_count),
        "captureSha256": hashlib.sha256(_canonical(capture)).hexdigest(),
    }


def join_sealed_capture(capture, receipt, evidence, *, manifest, observations,
                        expected_owner, compiled_max_admins=None):
    """Check count and digest, then join all captured replies.

    A receipt can expose accidental truncation only when its count came from an
    independent observation. It is not a trusted or cryptographic source proof.
    """
    _require(isinstance(receipt, dict) and set(receipt) == _RECEIPT_FIELDS, "receipt fields")
    _require(receipt["schemaVersion"] == "hmbc-witness-rpc-receipt/v1", "receipt version")
    for field in ("eventCount", "sourceEventCount"):
        _require(isinstance(receipt[field], str) and _DECIMAL.fullmatch(receipt[field]) is not None,
                 field + " format")
    _require(isinstance(capture, dict) and isinstance(capture.get("events"), list), "capture shape")
    _require(receipt["eventCount"] == str(len(capture["events"]))
             and receipt["sourceEventCount"] == receipt["eventCount"], "source event count mismatch")
    _require(isinstance(receipt["captureSha256"], str)
             and re.fullmatch(r"[0-9a-f]{64}", receipt["captureSha256"]) is not None,
             "capture digest format")
    _require(hashlib.sha256(_canonical(capture)).hexdigest() == receipt["captureSha256"], "capture digest mismatch")

    result = join_signing_events(capture, evidence, manifest=manifest,
                                 observations=observations, expected_owner=expected_owner,
                                 compiled_max_admins=compiled_max_admins)
    result["captureReceipt"] = dict(receipt)
    # These properties are intentionally false even after the local digest checks.
    result["captureAuthenticated"] = False
    result["transcriptCompletenessEstablished"] = False
    return result
