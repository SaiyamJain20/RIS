"""Symbolic-mode commitments from candidate revision 4 (BOUNDARY.md), implemented independently with eth_abi.

policyDigest     = keccak256(abi.encode(Requirement[][])),  Requirement = (bytes32 role, uint8 kind, uint8 issuerMode)
ciphertextDigest = keccak256(abi.encode(keccak256(bytes("HMBCSymbolicRecord/v1")), dataId, owner, payloadDigest, policyDigest, uint64(0)))
These are deterministic record identifiers, NOT ciphertext and NOT an ABE construction (adapterMode "symbolic").
"""
from __future__ import annotations

from eth_abi import encode
from eth_utils import keccak

from . import wire

RECORD_DOMAIN = keccak(text="HMBCSymbolicRecord/v1")


def _b32(h: str) -> bytes:
    return bytes.fromhex(h[2:])


def policy_digest(policy: dict) -> str:
    wire.symbolic_policy(policy)
    clauses = [[(_b32(r["role"]), int(r["kind"]), int(r["issuerMode"])) for r in clause] for clause in policy["clauses"]]
    return "0x" + keccak(encode(["(bytes32,uint8,uint8)[][]"], [clauses])).hex()


def ciphertext_digest(record: dict, policy: dict, key_epoch: str = "0") -> str:
    wire.symbolic_record(record)
    if key_epoch != "0":
        raise wire.WireError("MALFORMED: E fixes keyEpoch=0")
    pd = _b32(policy_digest(policy))
    body = encode(["bytes32", "bytes32", "address", "bytes32", "bytes32", "uint64"],
                  [RECORD_DOMAIN, _b32(record["dataId"]), record["owner"], _b32(record["payloadDigest"]), pd, 0])
    return "0x" + keccak(body).hex()
