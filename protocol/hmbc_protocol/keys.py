"""Opaque key handles for the adapter boundary.

`keyref:<role>:<label>` is a handle, never key material. In E0/E1 every key is a TEST-ONLY synthetic key derived
exactly like agent 1's fixtures (keccak256("hmbc-e0-synthetic-key:" || label)); it is resolved only inside this
process and its value must never appear in a response, log or error message.
"""
from __future__ import annotations

import re

from eth_account import Account
from eth_utils import keccak

_REF = re.compile(r"keyref:(user|witness|worker|authority):([a-z0-9][a-z0-9-]{0,63})")


class KeyRefError(ValueError):
    pass


def parse(ref: object) -> tuple[str, str]:
    if not isinstance(ref, str) or not (m := _REF.fullmatch(ref)):
        raise KeyRefError("key reference must look like keyref:<user|witness|worker|authority>:<label>")
    return m.group(1), m.group(2)


def synthetic_private_key(label: str) -> str:
    return "0x" + keccak(b"hmbc-e0-synthetic-key:" + label.encode()).hex()


def resolve(ref: object, allowed_roles: tuple[str, ...]) -> tuple[str, str]:
    """Return (private_key_hex, lowercase address). The private key never leaves the calling process."""
    role, label = parse(ref)
    if role not in allowed_roles:
        raise KeyRefError(f"a {role} key cannot be used for this operation")
    key = synthetic_private_key(label)
    return key, Account.from_key(key).address.lower()
