"""Offline capture receipt checks; receipt claims are caller-supplied, not authenticated."""
import copy
import hashlib
import json

import pytest

from evaluation.sealed_signing_capture_v1 import join_sealed_capture, seal_capture
from evaluation.tests.test_signing_event_join_v2 import capture, event_for
from evaluation.tests.test_witness_history_v2 import fixture


def test_sealed_capture_joins_when_count_and_capture_digest_match():
    manifest, observations, evidence = fixture()
    row = next(r for r in evidence["conflicts"] if r["type"] == "AccessDecision")
    source_capture = capture(event_for(row))
    receipt = seal_capture(source_capture, observed_event_count=1)

    result = join_sealed_capture(source_capture, receipt, evidence,
                                 manifest=manifest, observations=observations,
                                 expected_owner=evidence["owner"],
                                 compiled_max_admins="8" if manifest["profileEnum"] == "3" else None)

    assert result["captureReceipt"]["eventCount"] == "1"
    assert result["captureReceipt"]["captureSha256"] == hashlib.sha256(
        json.dumps(source_capture, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert result["joined"][0]["digest"] == row["digests"][0]["digest"]
    assert result["captureAuthenticated"] is False


def test_sealed_capture_rejects_missing_event_against_independent_source_count():
    manifest, observations, evidence = fixture()
    row = next(r for r in evidence["conflicts"] if r["type"] == "AccessDecision")
    source_capture = capture(event_for(row))
    receipt = seal_capture(source_capture, observed_event_count=2)

    with pytest.raises(ValueError, match="source event count"):
        join_sealed_capture(source_capture, receipt, evidence, manifest=manifest,
                            observations=observations, expected_owner=evidence["owner"])


def test_sealed_capture_rejects_changed_transcript_after_receipt_creation():
    manifest, observations, evidence = fixture()
    row = next(r for r in evidence["conflicts"] if r["type"] == "AccessDecision")
    source_capture = capture(event_for(row))
    receipt = seal_capture(source_capture, observed_event_count=1)
    changed = copy.deepcopy(source_capture)
    changed["events"][0]["requestLine"] += " "

    with pytest.raises(ValueError, match="capture digest"):
        join_sealed_capture(changed, receipt, evidence, manifest=manifest,
                            observations=observations, expected_owner=evidence["owner"])


def test_sealed_capture_allows_reused_rpc_id_for_sequential_events():
    manifest, observations, evidence = fixture()
    row = next(r for r in evidence["conflicts"] if r["type"] == "AccessDecision")
    event = event_for(row)
    second = copy.deepcopy(event)
    second["sequence"] = "2"
    source_capture = capture(event, second)
    receipt = seal_capture(source_capture, observed_event_count=2)

    result = join_sealed_capture(source_capture, receipt, evidence, manifest=manifest,
                                 observations=observations, expected_owner=evidence["owner"],
                                 compiled_max_admins="8" if manifest["profileEnum"] == "3" else None)

    assert [item["digest"] for item in result["joined"]] == [row["digests"][0]["digest"]] * 2


def test_capture_digest_uses_stable_ascii_json_escaping():
    manifest, observations, evidence = fixture()
    request = {"schemaVersion": "hmbc-witness-rpc/v1", "id": 10, "round": 1,
               "kind": "decision", "message": {"requestDigest": "0x" + "11" * 32}}
    response = {"schemaVersion": "hmbc-witness-rpc/v1", "id": 10,
                "reply": {"type": "error", "code": "POLICY_DENIED", "reason": "réfused", "recorded": None}}
    source_capture = {"schemaVersion": "hmbc-witness-rpc-capture/v1", "events": [{
        "sequence": "1",
        "requestLine": json.dumps(request, separators=(",", ":"), ensure_ascii=False),
        "responseLine": json.dumps(response, separators=(",", ":"), ensure_ascii=False),
    }]}
    receipt = seal_capture(source_capture, observed_event_count=1)
    expected_digest = hashlib.sha256(
        json.dumps(source_capture, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    assert receipt["captureSha256"] == expected_digest
    result = join_sealed_capture(source_capture, receipt, evidence, manifest=manifest,
                                 observations=observations, expected_owner=evidence["owner"],
                                 compiled_max_admins="8" if manifest["profileEnum"] == "3" else None)
    assert result["refusalReplies"] == 1
