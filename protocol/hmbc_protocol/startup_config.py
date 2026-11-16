"""Strict readers for LOCAL startup configuration (HMBC2020 successor, F task 2; answer to A3-0096 and A3-0097).

PAPER-DERIVED RECONSTRUCTION. Two command lines (`adapter_v2_main`, `witness_main`) and two RPC views read local files and manifest numbers before any chain is asked. Python's `int()` and a bare `json.loads` are
too lenient or too fragile for that job: `int(float('inf'))` raises OverflowError; `int("1_0")`, `int(" 5")`, `int("+5")`, `int(12.7)`, `int(True)` and `int("\\u0663")` all succeed with a value nobody wrote; and
`json.loads` raises RecursionError (not ValueError) on a deeply nested file. Each of those used to escape as a traceback or let startup go on with a number that is not the manifest's. This module decides, once:
  * an unsigned integer in a manifest is a CANONICAL decimal string within its width (the interface's encoding; `wire.uint` is the existing rule and is reused here, not a second one);
  * a local JSON file is parsed so that every parse failure, nesting depth included, is one `ConfigError`.
`ConfigError` is a ValueError, so every existing `except ValueError` refusal in the callers maps it to MALFORMED. Nothing here reads a file, a clock, the environment or the network.
"""
from __future__ import annotations

import json

from . import wire


class ConfigError(ValueError):
    """A local configuration input is not what the startup contract allows."""


class Refusal(Exception):
    """A startup refusal with its closed code. It lives HERE, in a module that is never run as `__main__`, on purpose: run as `python -m hmbc_protocol.adapter_v2_main`, that module is `__main__` and a lazy import of
    `witness_main` (which imports it by its package name) creates a SECOND copy of it, so a Refusal class defined there would be two different classes and `main()` would miss the one `_allow` raises (found live, A2-0075)."""

    def __init__(self, code, message, reason=None):
        super().__init__(message)
        self.code, self.message, self.reason = code, message, reason


def loads(raw, what):
    """Parse `raw` (bytes or str) as JSON; any failure, RecursionError included, is a ConfigError naming `what`."""
    try:
        return json.loads(raw)
    except (ValueError, RecursionError):                       # UnicodeDecodeError is a ValueError; RecursionError is not
        raise ConfigError(f"the {what} is not JSON") from None


def uint_text(value, bits, what):
    """The integer of a canonical unsigned decimal STRING of at most `bits` bits, else ConfigError. A JSON number, a float, a bool, a sign, a separator, a leading zero or a non-ASCII digit is refused."""
    try:
        return wire.uint(value, bits)
    except wire.WireError:
        raise ConfigError(f"{what} must be a canonical unsigned decimal string") from None


def manifest_numbers(manifest):
    """{side: {"chainId": int, "deployBlock": int}} for both chains of a deployment manifest, or ConfigError. chainId is a uint256 and deployBlock a uint64."""
    try:
        chains = manifest["chains"]
        return {side: {"chainId": uint_text(chains[side]["chainId"], 256, f"{side} chainId"), "deployBlock": uint_text(chains[side]["deployBlock"], 64, f"{side} deployBlock")} for side in ("pbc", "dbc")}
    except (KeyError, TypeError):
        raise ConfigError("the deployment declares no chains with a chainId and a deployBlock") from None
