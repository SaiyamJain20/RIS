"""Strict JSON wire validation for the HMBC interface types (agent-2 boundary).

Written from interfaces/README.md v0 and A1-0003/A1-0008 (agent 1) plus the A3-0006/A3-0009 notes on
canonical order, NOT from agent 3's schema code, so the two can be compared as independent
implementations. Raises WireError (reason class MALFORMED) on any violation; unknown or missing fields
reject; unsigned integers are canonical decimal strings; hex is lowercase; nothing is "fixed up".
"""
from __future__ import annotations

from typing import Any, Callable

from . import eip712

SECP256K1_N = eip712.SECP256K1_N
ZERO_ADDRESS = "0x" + "00" * 20


class WireError(ValueError):
    """MALFORMED wire value."""


def _fail(msg: str):
    raise WireError("MALFORMED: " + msg)


def address(v: Any) -> str:
    if not isinstance(v, str) or not eip712._ADDR.fullmatch(v):
        _fail(f"address {v!r}")
    return v


def hash32(v: Any) -> str:
    if not isinstance(v, str) or not eip712._HASH.fullmatch(v):
        _fail(f"bytes32 {v!r}")
    return v


def uint(v: Any, bits: int) -> int:
    try:
        return eip712._uint(v, bits)
    except eip712.EncodingError as e:
        raise WireError("MALFORMED: " + str(e)) from None


def signature(v: Any) -> str:
    if not isinstance(v, str) or not eip712._SIG.fullmatch(v):
        _fail("signature must be lowercase 0x + 130 hex")
    raw = bytes.fromhex(v[2:])
    r, s = int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:64], "big")
    if not (0 < r < SECP256K1_N and 0 < s <= SECP256K1_N // 2 and raw[64] in (27, 28)):
        _fail("non-canonical signature")
    return v


def _obj(v: Any, fields: dict[str, Callable[[Any], Any]], name: str) -> dict:
    if not isinstance(v, dict):
        _fail(f"{name}: object expected")
    if set(v) != set(fields):
        _fail(f"{name}: fields differ by {sorted(set(v) ^ set(fields))}")
    for k, check in fields.items():
        check(v[k])
    return v


def _strict_ascending(items: list, key: Callable[[Any], Any], what: str) -> None:
    keys = [key(i) for i in items]
    if any(a >= b for a, b in zip(keys, keys[1:])):
        _fail(f"{what} must be strictly ascending and unique")


def _list(v: Any, name: str) -> list:
    if not isinstance(v, list):
        _fail(f"{name}: array expected")
    return v


U8 = lambda v: uint(v, 8)    # noqa: E731
U64 = lambda v: uint(v, 64)  # noqa: E731
U256 = lambda v: uint(v, 256)  # noqa: E731


def access_request(v):
    return _obj(v, dict(sourceChainId=U256, destinationChainId=U256, psc=address, kssc=address, gid=address,
                        dataId=hash32, action=U8, policyVersion=U64, authEpoch=U64, keyEpoch=U64, nonce=U256,
                        expiresAt=U64, recipientKeyHash=hash32), "AccessRequest")


def access_decision(v):
    return _obj(v, dict(requestDigest=hash32, result=U8, credentialDigest=hash32, stateSequence=U64,
                        witnessSetVersion=U64, sourceBlockNumber=U256, sourceBlockHash=hash32, expiresAt=U64),
                "AccessDecision")


def state_checkpoint(v):
    return _obj(v, dict(sequence=U64, authEpoch=U64, policyVersion=U64, keyEpoch=U64, witnessSetVersion=U64,
                        sourceChainId=U256, psc=address, sourceBlockNumber=U256, sourceBlockHash=hash32,
                        expiresAt=U64), "StateCheckpoint")


def registration(v):
    return _obj(v, dict(gid=address, certDigest=hash32, recipientKeyHash=hash32, expiresAt=U64), "Registration")


def role_certificate(v):
    _obj(v, dict(issuer=address, gid=address, roles=lambda r: [hash32(x) for x in _list(r, "roles")],
                 serial=U64, validFrom=U64, validUntil=U64), "RoleCertificate")
    _strict_ascending(v["roles"], lambda r: r, "roles")
    if int(v["validFrom"]) >= int(v["validUntil"]):
        _fail("certificate interval requires validFrom < validUntil")
    return v


def signed_role_certificate(v):
    _obj(v, dict(cert=role_certificate, signature=signature), "SignedRoleCertificate")
    return v


def revocation_list(v):
    _obj(v, dict(authority=address, version=U64, validUntil=U64,
                 revokedSerials=lambda r: [U64(x) for x in _list(r, "revokedSerials")]), "RevocationList")
    _strict_ascending(v["revokedSerials"], int, "revokedSerials")
    return v


def temp_acl_entry(v):
    _obj(v, dict(gid=address, role=hash32, validFrom=U64, validUntil=U64), "TempAclEntry")
    if v["gid"] == ZERO_ADDRESS:
        _fail("zero temporal subject")
    if int(v["validFrom"]) >= int(v["validUntil"]):
        _fail("temporal interval requires validFrom < validUntil")
    return v


def temporal_acl(v):
    _obj(v, dict(authority=address, version=U64, validUntil=U64,
                 entries=lambda e: [temp_acl_entry(x) for x in _list(e, "entries")]), "TemporalAcl")
    _strict_ascending(v["entries"], lambda e: (e["gid"], e["role"]), "entries by (gid, role)")
    return v


def temporal_claim(v):
    return _obj(v, dict(authority=address, role=hash32), "TemporalClaim")


def credential_bundle(v):
    _obj(v, dict(certificates=lambda c: [signed_role_certificate(x) for x in _list(c, "certificates")],
                 temporalClaims=lambda c: [temporal_claim(x) for x in _list(c, "temporalClaims")]),
         "CredentialBundle")
    if not v["certificates"] and not v["temporalClaims"]:
        _fail("empty credential bundle")
    _strict_ascending(v["certificates"], lambda c: c["cert"]["issuer"], "certificates by issuer")
    _strict_ascending(v["temporalClaims"], lambda t: (t["authority"], t["role"]), "temporalClaims by (authority, role)")
    return v


def credential_record(v):
    _obj(v, dict(issuer=address, role=hash32, kind=U8, serial=U64, anchorVersion=U64, validUntil=U64),
         "CredentialRecord")
    if v["kind"] not in ("1", "2"):
        _fail("kind must be 1 (long-term) or 2 (temporal)")
    if v["kind"] == "2" and v["serial"] != "0":
        _fail("temporal record serial must be 0")
    return v


def credential_records(v):
    recs = [credential_record(x) for x in _list(v, "CredentialRecords")]
    _strict_ascending(recs, lambda r: (int(r["kind"]), r["issuer"], r["role"]), "records by (kind, issuer, role)")
    return recs


def grant_receipt(v):
    _obj(v, dict(requestDigest=hash32, grantId=hash32, gid=address, dataId=hash32, keyEpoch=U64,
                 grantExpiresAt=U64, witnessSetVersion=U64, dbcChainId=U256, kssc=address,
                 dbcBlockNumber=U256, dbcBlockHash=hash32), "GrantReceipt")
    if int(v["grantExpiresAt"]) == 0:
        _fail("grantExpiresAt must be positive")
    if v["keyEpoch"] != "0" or v["witnessSetVersion"] != "1":
        _fail("E fixes keyEpoch=0 and witnessSetVersion=1")
    return v


VALIDATORS: dict[str, Callable[[Any], Any]] = {
    "AccessRequest": access_request, "AccessDecision": access_decision, "StateCheckpoint": state_checkpoint,
    "Registration": registration, "RoleCertificate": role_certificate, "SignedRoleCertificate": signed_role_certificate,
    "RevocationList": revocation_list, "TempAclEntry": temp_acl_entry, "TemporalAcl": temporal_acl,
    "TemporalClaim": temporal_claim, "CredentialBundle": credential_bundle, "CredentialRecord": credential_record,
    "CredentialRecords": credential_records, "GrantReceipt": grant_receipt, "Address": address, "Hash": hash32,
    "Signature": signature,
}


def validate(name: str, value: Any) -> Any:
    try:
        check = VALIDATORS[name]
    except KeyError:
        raise WireError(f"unknown wire type {name!r}") from None
    return check(value)


# --- revision-4 boundary types (A3-0011 / BOUNDARY.md), written from that prose, not from agent 3's schema ------------------

import re as _re

ERROR_CODES = frozenset({
    "BAD_SIGNATURE", "WRONG_SUBJECT", "WRONG_DESTINATION", "UNKNOWN_AUTHORITY", "STALE_ANCHOR", "STALE_STATE", "EXPIRED",
    "REPLAY", "POLICY_DENIED", "INSUFFICIENT_QUORUM", "DUPLICATE_SIGNER", "WRONG_EPOCH", "NOT_COMMITTED",
    "ADAPTER_UNAVAILABLE", "NOT_IMPLEMENTED_IN_PHASE", "UNAUTHORIZED_CALLER", "NOT_REGISTERED", "ALREADY_REGISTERED",
    "REVOKED", "MALFORMED", "WRONG_PROFILE"})
_USER_KEY_REF = _re.compile(r"keyref:user:[a-z0-9][a-z0-9-]{0,63}")
SYMBOLIC_ENVELOPE_KIND = "symbolic-partial/v1"


def _const(value: Any, expected: Any, what: str) -> None:
    if value != expected or type(value) is not type(expected):
        _fail(f"{what} must be {expected!r}")


def user_key_ref(v):
    if not isinstance(v, str) or not _USER_KEY_REF.fullmatch(v):
        _fail("key reference must be keyref:user:<label>")
    return v


def symbolic_record(v):
    return _obj(v, dict(dataId=hash32, owner=address, payloadDigest=hash32), "SymbolicRecord")


def policy_requirement(v):
    _obj(v, dict(role=hash32, kind=lambda x: _enum(x, ("1", "2"), "kind"),
                 issuerMode=lambda x: _enum(x, ("0", "1", "2"), "issuerMode")), "PolicyRequirement")
    return v


def _enum(x: Any, allowed: tuple, what: str):
    if not isinstance(x, str) or x not in allowed:
        _fail(f"{what} must be one of {allowed}")
    return x


def symbolic_policy(v):
    _obj(v, dict(clauses=lambda c: None), "SymbolicPolicy")
    clauses = _list(v["clauses"], "clauses")
    if not clauses:
        _fail("policy needs at least one clause")
    for clause in clauses:
        reqs = _list(clause, "clause")
        if not reqs:
            _fail("empty clause")
        for r in reqs:
            policy_requirement(r)
        if reqs[0]["issuerMode"] == "2":      # SAME_AS_FIRST needs an anchor; first requirement of ANY clause (A32, ledger A1-0014)
            _fail("SAME_AS_FIRST cannot be a clause's first requirement")
    return v


def symbolic_envelope(v):
    _obj(v, dict(kind=lambda x: _const(x, SYMBOLIC_ENVELOPE_KIND, "kind"), token=hash32), "SymbolicEnvelope")
    return v


def _e_const(expected):
    return lambda x: _const(x, expected, "value")


def release_result(v):
    return _obj(v, dict(schemaVersion=_e_const("v1"), adapterMode=_e_const("symbolic"), requestDigest=hash32, grantId=hash32,
                        dataId=hash32, ciphertextDigest=hash32, recipientKeyHash=hash32, keyEpoch=_e_const("0"),
                        responseEnvelope=symbolic_envelope), "ReleaseResult")


def prepare_request_input(v):
    return _obj(v, dict(request=access_request, signingKeyRef=user_key_ref), "PrepareRequestInput")


def collect_checkpoint_input(v):
    """{} or {witnessSetVersion: "1"} (A3-0012). Never a relay-supplied sequence, timestamp or source block: unknown fields reject."""
    if isinstance(v, dict) and "witnessSetVersion" in v:
        return _obj(v, dict(witnessSetVersion=_e_const("1")), "CollectCheckpointInput")
    return _obj(v, {}, "CollectCheckpointInput")


def attest_grant_input(v):
    return _obj(v, dict(grantId=hash32), "AttestGrantInput")


def collect_decision_input(v):
    if isinstance(v, dict) and "witnessSetVersion" in v:
        return _obj(v, dict(requestDigest=hash32, witnessSetVersion=_e_const("1")), "CollectDecisionInput")
    return _obj(v, dict(requestDigest=hash32), "CollectDecisionInput")


def release_input(v):
    return _obj(v, dict(grantId=hash32), "ReleaseInput")


def encrypt_record_input(v):
    return _obj(v, dict(record=symbolic_record, policy=symbolic_policy, keyEpoch=_e_const("0")), "EncryptRecordInput")


def finish_decryption_input(v):
    return _obj(v, dict(response=release_result, userKeyRef=user_key_ref), "FinishDecryptionInput")


def rotate_epoch_input(v):
    return _obj(v, dict(targetEpoch=U64), "RotateEpochInput")


def prepare_request_result(v):
    return _obj(v, dict(schemaVersion=_e_const("v1"), adapterMode=_e_const("symbolic"), request=access_request,
                        requestDigest=hash32, signature=signature, signer=address), "PrepareRequestResult")


def collect_decision_result(v):
    def sigs(x):
        if len(_list(x, "signatures")) != 1:     # E: q = 1 of 1
            _fail("E carries exactly one witness signature")
        for s in x:
            signature(s)
    _obj(v, dict(schemaVersion=_e_const("v1"), adapterMode=_e_const("symbolic"), decision=access_decision,
                 signatures=sigs, credentialRecords=credential_records), "CollectDecisionResult")
    return v


def _one_signature(x):
    if len(_list(x, "signatures")) != 1:                     # E: q = 1 of 1
        _fail("E carries exactly one witness signature")
    for sig in x:
        signature(sig)


def collect_checkpoint_result(v):
    return _obj(v, dict(schemaVersion=_e_const("v1"), adapterMode=_e_const("symbolic"), checkpoint=state_checkpoint,
                        signatures=_one_signature), "CollectCheckpointResult")


def attest_grant_result(v):
    return _obj(v, dict(schemaVersion=_e_const("v1"), adapterMode=_e_const("symbolic"), receipt=grant_receipt,
                        signatures=_one_signature), "AttestGrantResult")


def encrypt_record_result(v):
    return _obj(v, dict(schemaVersion=_e_const("v1"), adapterMode=_e_const("symbolic"), dataId=hash32,
                        keyEpoch=_e_const("0"), ciphertextDigest=hash32, policyDigest=hash32), "EncryptRecordResult")


def finish_decryption_result(v):
    def boolean(x):
        if not isinstance(x, bool):
            _fail("decryptable must be a JSON boolean")
    return _obj(v, dict(schemaVersion=_e_const("v1"), adapterMode=_e_const("symbolic"), decryptable=boolean,
                        dataId=hash32, ciphertextDigest=hash32), "FinishDecryptionResult")


def error_obj(v):
    _obj(v, dict(code=lambda c: _enum(c, tuple(ERROR_CODES), "code"), message=lambda m: None if isinstance(m, str) else _fail("message must be a string")), "Error")
    return v


INPUTS = {"prepare_request": prepare_request_input, "collect_decision": collect_decision_input,
          "collect_checkpoint": collect_checkpoint_input, "attest_grant": attest_grant_input, "release": release_input,
          "encrypt_record": encrypt_record_input, "finish_decryption": finish_decryption_input, "rotate_epoch": rotate_epoch_input}
RESULTS = {"prepare_request": prepare_request_result, "collect_decision": collect_decision_result,
           "collect_checkpoint": collect_checkpoint_result, "attest_grant": attest_grant_result,
           "release": release_result, "encrypt_record": encrypt_record_result, "finish_decryption": finish_decryption_result}


def adapter_request(v, deployment_check: Callable[[Any], Any] | None = None):
    """Envelope + operation-selected closed input. The deployment is only checked by `deployment_check` (agent 3's/agent 1's schema)."""
    _obj(v, dict(schemaVersion=_e_const("v1"), operation=lambda o: _enum(o, tuple(INPUTS), "operation"),
                 input=lambda i: None, deploymentManifest=deployment_check or (lambda d: None if isinstance(d, dict) else _fail("deploymentManifest must be an object"))),
         "AdapterRequest")
    INPUTS[v["operation"]](v["input"])
    return v


def adapter_response(v, operation: str | None = None):
    """Generic response when `operation` is None (any of the five results); bound to the pending operation otherwise."""
    if not isinstance(v, dict) or set(v) != {"schemaVersion", "ok", "result", "error"}:
        _fail("response must have exactly schemaVersion, ok, result, error")
    _const(v["schemaVersion"], "v1", "schemaVersion")
    if v["ok"] is True:
        if v["error"] is not None:
            _fail("success must have a null error")
        if operation == "rotate_epoch":
            _fail("rotate_epoch has no success result in E")
        if operation is not None:
            RESULTS[operation](v["result"])
        else:
            for check in RESULTS.values():
                try:
                    check(v["result"])
                    break
                except WireError:
                    continue
            else:
                _fail("result matches none of the five closed E results")
    elif v["ok"] is False:
        if v["result"] is not None:
            _fail("failure must have a null result")
        error_obj(v["error"])
    else:
        _fail("ok must be a boolean")
    return v


OBSERVED_EVENT_FIELDS = {
    "REQUEST_LOGGED": dict(requestDigest=hash32, timestamp=U64),
    "PBC_DECIDED": dict(requestDigest=hash32, timestamp=U64),
    "DBC_AUTHORIZED": dict(requestDigest=hash32, timestamp=U64, grantId=hash32, gid=address, dataId=hash32, kssc=address,
                           destinationChainId=U256, recipientKeyHash=hash32, keyEpoch=_e_const("0")),
    "RELEASE_INTENT": dict(requestDigest=hash32, timestamp=U64, grantId=hash32, gid=address, dataId=hash32),
    "RELEASE_SENT": dict(requestDigest=hash32, timestamp=U64, grantId=hash32, gid=address, dataId=hash32),
    "OUTCOME_RECORDED": dict(requestDigest=hash32, timestamp=U64, grantId=hash32, gid=address, dataId=hash32),
}


def observed_event(v):
    if not isinstance(v, dict) or v.get("type") not in OBSERVED_EVENT_FIELDS:
        _fail("unknown observed event type")
    fields = {"type": lambda t: None, **OBSERVED_EVENT_FIELDS[v["type"]]}
    return _obj(v, fields, "ObservedEvent")


VALIDATORS.update({
    "UserKeyRef": user_key_ref, "SymbolicRecord": symbolic_record, "PolicyRequirement": policy_requirement,
    "SymbolicPolicy": symbolic_policy, "SymbolicEnvelope": symbolic_envelope, "ReleaseResult": release_result,
    "PrepareRequestInput": prepare_request_input, "CollectDecisionInput": collect_decision_input, "ReleaseInput": release_input,
    "CollectCheckpointInput": collect_checkpoint_input, "AttestGrantInput": attest_grant_input,
    "CollectCheckpointResult": collect_checkpoint_result, "AttestGrantResult": attest_grant_result,
    "EncryptRecordInput": encrypt_record_input, "FinishDecryptionInput": finish_decryption_input, "RotateEpochInput": rotate_epoch_input,
    "PrepareRequestResult": prepare_request_result, "CollectDecisionResult": collect_decision_result,
    "EncryptRecordResult": encrypt_record_result, "FinishDecryptionResult": finish_decryption_result,
    "AdapterRequest": adapter_request, "AdapterResponse": adapter_response, "ObservedEvent": observed_event,
    **{f"{n}Request": (lambda v, _op=op: (adapter_request(v), v["operation"] == _op or _fail("operation does not match request type")))
       for n, op in (("PrepareRequest", "prepare_request"), ("CollectDecision", "collect_decision"), ("CollectCheckpoint", "collect_checkpoint"),
                     ("AttestGrant", "attest_grant"), ("Release", "release"),
                     ("EncryptRecord", "encrypt_record"), ("FinishDecryption", "finish_decryption"), ("RotateEpoch", "rotate_epoch"))},
    **{f"{n}Response": (lambda v, _op=op: adapter_response(v, _op))
       for n, op in (("PrepareRequest", "prepare_request"), ("CollectDecision", "collect_decision"), ("CollectCheckpoint", "collect_checkpoint"),
                     ("AttestGrant", "attest_grant"), ("Release", "release"),
                     ("EncryptRecord", "encrypt_record"), ("FinishDecryption", "finish_decryption"), ("RotateEpoch", "rotate_epoch"))},
})
