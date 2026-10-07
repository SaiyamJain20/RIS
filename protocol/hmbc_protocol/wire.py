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
