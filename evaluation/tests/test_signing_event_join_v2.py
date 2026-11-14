"""Synthetic joins from captured witness RPC replies to durable history records."""
import copy
import importlib
import json

import pytest

from evaluation.tests.test_witness_history_v2 import fixture, supersede


KEY_FIELDS = {
    "AccessDecision": "requestDigest",
    "StateCheckpoint": "sequence",
    "GrantReceipt": "requestDigest",
    "GovernanceAction": "nonce",
}
KINDS = {
    "AccessDecision": "decision",
    "StateCheckpoint": "checkpoint",
    "GrantReceipt": "receipt",
    "GovernanceAction": "governance",
}


def event_for(row, *, sequence=1, request_id=10):
    message = dict(row["effect"])
    message[KEY_FIELDS[row["type"]]] = row["keyField"]
    digest_row = row["digests"][0]
    if row["type"] != "GrantReceipt":
        message["expiresAt"] = digest_row["expiresAt"]
    request = {
        "schemaVersion": "hmbc-witness-rpc/v1",
        "id": request_id,
        "round": 1,
        "kind": KINDS[row["type"]],
        "message": message,
    }
    response = {
        "schemaVersion": "hmbc-witness-rpc/v1",
        "id": request_id,
        "reply": {"type": "signature", "message": message, "signature": digest_row["signature"]},
    }
    return {
        "sequence": str(sequence),
        "requestLine": json.dumps(request, separators=(",", ":")),
        "responseLine": json.dumps(response, separators=(",", ":")),
    }


def capture(*events):
    return {"schemaVersion": "hmbc-witness-rpc-capture/v1", "events": list(events)}


def join(capture_doc, manifest, observations, evidence):
    return importlib.import_module("evaluation.signing_event_join_v2").join_signing_events(
        capture_doc,
        evidence,
        manifest=manifest,
        observations=observations,
        expected_owner=evidence["owner"],
        compiled_max_admins="8" if manifest["profileEnum"] == "3" else None,
    )


def test_signature_reply_joins_to_exact_store_digest_and_sign_observation():
    manifest, observations, evidence = fixture()
    row = next(r for r in evidence["conflicts"] if r["type"] == "AccessDecision")
    result = join(capture(event_for(row)), manifest, observations, evidence)

    assert result["capturedEvents"] == 1
    assert result["signatureReplies"] == 1
    assert result["refusalReplies"] == 0
    assert result["joined"] == [
        {
            "sequence": "1",
            "type": "AccessDecision",
            "digest": row["digests"][0]["digest"],
            "witness": evidence["owner"],
            "domainSeparator": row["domainSeparator"],
            "witnessSetVersion": row["witnessSetVersion"],
            "keyField": row["keyField"],
            "generationSeq": None,
            "observation": row["digests"][0]["observation"],
        }
    ]


@pytest.mark.parametrize("name", list(KEY_FIELDS))
def test_each_published_signing_kind_joins_its_exact_typed_digest(name):
    manifest, observations, evidence = fixture()
    row = next(r for r in evidence["conflicts"] if r["type"] == name)

    result = join(capture(event_for(row)), manifest, observations, evidence)

    assert result["signatureReplies"] == 1
    assert result["joined"][0]["type"] == name
    assert result["joined"][0]["digest"] == row["digests"][0]["digest"]


def test_error_reply_is_counted_without_claiming_a_signing_join():
    manifest, observations, evidence = fixture()
    request = {
        "schemaVersion": "hmbc-witness-rpc/v1", "id": 10, "round": 1,
        "kind": "decision", "message": {"requestDigest": "0x" + "11" * 32},
    }
    response = {
        "schemaVersion": "hmbc-witness-rpc/v1", "id": 10,
        "reply": {"type": "error", "code": "REPLAY", "reason": None, "recorded": None},
    }
    event = {"sequence": "1",
             "requestLine": json.dumps(request, separators=(",", ":")),
             "responseLine": json.dumps(response, separators=(",", ":"))}

    result = join(capture(event), manifest, observations, evidence)

    assert result["capturedEvents"] == 1
    assert result["signatureReplies"] == 0
    assert result["refusalReplies"] == 1
    assert result["joined"] == []
    assert result["transcriptCompletenessEstablished"] is False


def test_superseded_and_live_signatures_join_to_distinct_generations():
    manifest, observations, evidence = fixture()
    supersede(manifest, evidence, "AccessDecision", kind="expiry")
    old = evidence["superseded"][0]
    live = next(r for r in evidence["conflicts"] if r["type"] == "AccessDecision")

    result = join(capture(event_for(old, sequence=1), event_for(live, sequence=2, request_id=11)),
                  manifest, observations, evidence)

    assert [(row["digest"], row["generationSeq"]) for row in result["joined"]] == [
        (old["digests"][0]["digest"], "1"),
        (live["digests"][0]["digest"], None),
    ]


def test_idempotent_repeat_can_join_to_the_same_stored_digest():
    manifest, observations, evidence = fixture()
    row = next(r for r in evidence["conflicts"] if r["type"] == "StateCheckpoint")

    result = join(capture(event_for(row, sequence=1), event_for(row, sequence=2, request_id=11)),
                  manifest, observations, evidence)

    assert [event["digest"] for event in result["joined"]] == [row["digests"][0]["digest"]] * 2
    assert [event["observation"] for event in result["joined"]] == [row["digests"][0]["observation"]] * 2


def test_reply_with_message_different_from_request_is_rejected():
    manifest, observations, evidence = fixture()
    row = next(r for r in evidence["conflicts"] if r["type"] == "GrantReceipt")
    ev = event_for(row)
    response = json.loads(ev["responseLine"])
    response["reply"]["message"]["gid"] = "0x" + "99" * 20
    ev["responseLine"] = json.dumps(response, separators=(",", ":"))

    with pytest.raises(ValueError, match="request/response message mismatch"):
        join(capture(ev), manifest, observations, evidence)


def test_unmatched_or_invalid_signature_cannot_be_associated_with_history():
    manifest, observations, evidence = fixture()
    row = next(r for r in evidence["conflicts"] if r["type"] == "GovernanceAction")
    ev = event_for(row)
    response = json.loads(ev["responseLine"])
    signature = response["reply"]["signature"]
    response["reply"]["signature"] = "0x" + ("0" if signature[2] != "0" else "1") + signature[3:]
    ev["responseLine"] = json.dumps(response, separators=(",", ":"))

    with pytest.raises(ValueError):
        join(capture(ev), manifest, observations, evidence)


def test_capture_sequence_and_request_ids_are_correlated():
    manifest, observations, evidence = fixture()
    row = next(r for r in evidence["conflicts"] if r["type"] == "AccessDecision")
    ev = event_for(row)
    response = json.loads(ev["responseLine"])
    response["id"] += 1
    ev["responseLine"] = json.dumps(response, separators=(",", ":"))

    with pytest.raises(ValueError, match="request/response id mismatch"):
        join(capture(ev), manifest, observations, evidence)


def test_boolean_response_id_is_not_accepted_as_an_integer_id():
    manifest, observations, evidence = fixture()
    row = next(r for r in evidence["conflicts"] if r["type"] == "AccessDecision")
    ev = event_for(row, request_id=1)
    response = json.loads(ev["responseLine"])
    response["id"] = True
    ev["responseLine"] = json.dumps(response, separators=(",", ":"))

    with pytest.raises(ValueError, match="request/response id mismatch"):
        join(capture(ev), manifest, observations, evidence)


def test_unhashable_request_kind_is_a_closed_input_error():
    manifest, observations, evidence = fixture()
    row = next(r for r in evidence["conflicts"] if r["type"] == "AccessDecision")
    ev = event_for(row)
    request = json.loads(ev["requestLine"])
    request["kind"] = []
    ev["requestLine"] = json.dumps(request, separators=(",", ":"))

    with pytest.raises(ValueError, match="request kind/message"):
        join(capture(ev), manifest, observations, evidence)


def test_duplicate_json_keys_are_rejected():
    manifest, observations, evidence = fixture()
    row = next(r for r in evidence["conflicts"] if r["type"] == "AccessDecision")
    ev = event_for(row)
    ev["requestLine"] = ev["requestLine"].replace('"id":10', '"id":10,"id":10')

    with pytest.raises(ValueError, match="duplicate JSON key"):
        join(capture(ev), manifest, observations, evidence)


def test_capture_rejects_mutated_history_instead_of_joining_it():
    manifest, observations, evidence = fixture()
    row = next(r for r in evidence["conflicts"] if r["type"] == "AccessDecision")
    ev = event_for(row)
    changed = copy.deepcopy(evidence)
    changed["conflicts"][0]["effect"]["stateSequence"] = "9"

    with pytest.raises(ValueError):
        join(capture(ev), manifest, observations, changed)
