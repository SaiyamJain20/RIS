"""Independent EIP-712 typed-data encoder for the HMBC interface types.

Deliberately does not call eth_account's encoder for hashing: digests are computed here from the
EIP-712 specification (keccak256 of encodeType / encodeData) so that tests can compare this module,
eth_account and agent 1's Solidity/cast vectors as three independent implementations. eth_account
is used only for secp256k1 signing/recovery. Uints are decimal strings in JSON and rejected if
negative, non-canonical or out of range.
"""
from __future__ import annotations

import re
from typing import Any

from eth_account import Account
from eth_account.messages import _hash_eip191_message
from eth_utils import keccak, to_checksum_address

# All wire patterns are applied with fullmatch(): a `$` anchor would accept a trailing "\n".
_ADDR = re.compile(r"0x[0-9a-f]{40}")
_HASH = re.compile(r"0x[0-9a-f]{64}")
_SIG = re.compile(r"0x[0-9a-f]{130}")
_DEC = re.compile(r"(0|[1-9][0-9]*)")
_ARRAY = re.compile(r"(.*)\[\]", re.DOTALL)
SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


class EncodingError(ValueError):
    """Malformed typed data (unknown field, bad format, overflow)."""


def _uint(value: Any, bits: int) -> int:
    # interfaces v0: unsigned integers are canonical decimal STRINGS on the wire; JSON numbers reject.
    if not isinstance(value, str) or not _DEC.fullmatch(value):
        raise EncodingError(f"uint{bits}: expected a canonical decimal string, got {value!r}")
    if len(value) > 78:                       # 2**256 has 78 digits; also avoids int()'s 4300-digit ValueError on absurd inputs
        raise EncodingError(f"uint{bits}: out of range")
    value = int(value)
    if value >= 1 << bits:
        raise EncodingError(f"uint{bits}: out of range")
    return value


def _atomic(type_name: str, value: Any) -> bytes:
    if type_name == "address":
        if not isinstance(value, str) or not _ADDR.fullmatch(value):
            raise EncodingError(f"address: expected lowercase 0x+40 hex, got {value!r}")
        return bytes(12) + bytes.fromhex(value[2:])
    if type_name == "bytes32":
        if not isinstance(value, str) or not _HASH.fullmatch(value):
            raise EncodingError(f"bytes32: expected lowercase 0x+64 hex, got {value!r}")
        return bytes.fromhex(value[2:])
    if type_name.startswith("uint"):
        bits = int(type_name[4:])
        return _uint(value, bits).to_bytes(32, "big")
    if type_name == "string":
        if not isinstance(value, str):
            raise EncodingError("string expected")
        return keccak(text=value)
    raise EncodingError(f"unsupported atomic type {type_name}")


def _deps(primary: str, types: dict, found: set | None = None) -> set:
    found = found if found is not None else set()
    base = primary[:-2] if primary.endswith("[]") else primary
    if base in found or base not in types:
        return found
    found.add(base)
    for field in types[base]:
        _deps(field["type"], types, found)
    return found


def encode_type(primary: str, types: dict) -> str:
    deps = _deps(primary, types)
    deps.discard(primary)
    out = []
    for name in [primary] + sorted(deps):
        out.append(name + "(" + ",".join(f"{f['type']} {f['name']}" for f in types[name]) + ")")
    return "".join(out)


def type_hash(primary: str, types: dict) -> bytes:
    return keccak(text=encode_type(primary, types))


def _encode_value(type_name: str, value: Any, types: dict) -> bytes:
    arr = _ARRAY.fullmatch(type_name)
    if arr:
        if not isinstance(value, list):
            raise EncodingError("array expected")
        return keccak(b"".join(_encode_value(arr.group(1), v, types) for v in value))
    if type_name in types:
        return hash_struct(type_name, value, types)
    return _atomic(type_name, value)


def hash_struct(primary: str, message: dict, types: dict) -> bytes:
    fields = types[primary]
    if not isinstance(message, dict):
        raise EncodingError(f"{primary}: object expected")
    if set(message) != {f["name"] for f in fields}:
        raise EncodingError(f"{primary}: unknown or missing fields {sorted(set(message) ^ {f['name'] for f in fields})}")
    body = b"".join(_encode_value(f["type"], message[f["name"]], types) for f in fields)
    return keccak(type_hash(primary, types) + body)


DOMAIN_TYPE = [
    {"name": "name", "type": "string"},
    {"name": "version", "type": "string"},
    {"name": "chainId", "type": "uint256"},
    {"name": "verifyingContract", "type": "address"},
]


def domain_separator(domain: dict) -> bytes:
    return hash_struct("EIP712Domain", domain, {"EIP712Domain": DOMAIN_TYPE})


def struct_hash(typed: dict) -> bytes:
    types = {k: v for k, v in typed["types"].items() if k != "EIP712Domain"}
    return hash_struct(typed["primaryType"], typed["message"], types)


def digest(typed: dict) -> bytes:
    """EIP-712 digest keccak256(0x1901 || domainSeparator || hashStruct(message))."""
    return keccak(b"\x19\x01" + domain_separator(typed["domain"]) + struct_hash(typed))


def credential_digest(records: list[dict]) -> bytes:
    """credentialDigest = keccak256(concat(hashStruct(CredentialRecord_i))) (A1-0003 section 3)."""
    types = {"CredentialRecord": [
        {"name": "issuer", "type": "address"}, {"name": "role", "type": "bytes32"},
        {"name": "kind", "type": "uint8"}, {"name": "serial", "type": "uint64"},
        {"name": "anchorVersion", "type": "uint64"}, {"name": "validUntil", "type": "uint64"}]}
    return keccak(b"".join(hash_struct("CredentialRecord", r, types) for r in records))


def grant_id(request_digest: bytes, kssc: str, destination_chain_id: int) -> bytes:
    """grantId = keccak256(abi.encode(requestDigest, kssc, destinationChainId)) (interfaces v0)."""
    return keccak(request_digest + _atomic("address", kssc) + destination_chain_id.to_bytes(32, "big"))


def sign_digest(private_key: str, dig: bytes) -> str:
    """Sign a 32-byte digest, no EIP-191 prefix. Returns 65-byte r||s||v, v in {27,28}, low-s."""
    signed = Account._sign_hash(dig, private_key) if hasattr(Account, "_sign_hash") else Account.unsafe_sign_hash(dig, private_key)
    sig = signed.signature.hex()
    return sig if sig.startswith("0x") else "0x" + sig


def recover(dig: bytes, signature: str) -> str:
    """Recover the lowercase signer address, enforcing the contract-side canonical form."""
    if not isinstance(signature, str) or not _SIG.fullmatch(signature):
        raise EncodingError("signature must be lowercase 0x + 130 hex digits (65 bytes r||s||v)")
    raw = bytes.fromhex(signature[2:])
    r, s, v = int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:64], "big"), raw[64]
    if v not in (27, 28) or r == 0 or s == 0 or s > SECP256K1_N // 2:
        raise EncodingError("non-canonical signature (v in {27,28}, 0<r, 0<s<=n/2 required)")
    return Account._recover_hash(dig, vrs=(v, r, s)).lower()


__all__ = ["EncodingError", "encode_type", "type_hash", "hash_struct", "domain_separator", "struct_hash",
           "digest", "credential_digest", "grant_id", "sign_digest", "recover", "to_checksum_address"]
