"""ABI codec between the interface wire form and EVM calldata/outputs.

Wire form: unsigned integers are canonical decimal strings, addresses/bytes are lowercase 0x hex, structs are dicts with
exactly the ABI component names, arrays are lists. Anything else raises AbiError; nothing is coerced or "fixed up".
"""
from __future__ import annotations

import re
from typing import Any

from eth_abi import decode as _decode
from eth_abi import encode as _encode
from eth_utils import keccak

from . import eip712

_BYTESN = re.compile(r"bytes([1-9]|[12][0-9]|3[0-2])")
_UINT = re.compile(r"uint(8|16|32|64|128|256)")
_HEX_BYTES = re.compile(r"0x([0-9a-f]{2})*")
_ARRAY = re.compile(r"(.*)\[\]")


class AbiError(ValueError):
    pass


def _canonical(t: dict) -> str:
    typ = t["type"]
    if typ.startswith("tuple"):
        return "(" + ",".join(_canonical(c) for c in t["components"]) + ")" + typ[len("tuple"):]
    return typ


def _to_py(t: dict, v: Any):
    typ = t["type"]
    if typ.startswith("tuple") and typ[len("tuple"):] == "":
        names = [c["name"] for c in t["components"]]
        if not isinstance(v, dict) or set(v) != set(names):
            raise AbiError(f"struct {t.get('name')!r}: expected exactly {names}")
        return tuple(_to_py(c, v[c["name"]]) for c in t["components"])
    if (m := _ARRAY.fullmatch(typ)):
        if not isinstance(v, list):
            raise AbiError("array expected")
        inner = {**t, "type": m.group(1)}
        return [_to_py(inner, x) for x in v]
    try:
        if typ == "address":
            if not isinstance(v, str) or not eip712._ADDR.fullmatch(v):
                raise AbiError("address must be lowercase 0x + 40 hex")
            return v
        if (m := _UINT.fullmatch(typ)):
            return eip712._uint(v, int(m.group(1)))
        if typ == "bool":
            if not isinstance(v, bool):
                raise AbiError("bool expected")
            return v
        if (m := _BYTESN.fullmatch(typ)):
            n = int(m.group(1))
            if not isinstance(v, str) or not re.fullmatch(f"0x[0-9a-f]{{{2 * n}}}", v):
                raise AbiError(f"{typ} must be lowercase 0x + {2 * n} hex")
            return bytes.fromhex(v[2:])
        if typ == "bytes":
            if not isinstance(v, str) or not _HEX_BYTES.fullmatch(v):
                raise AbiError("bytes must be lowercase 0x hex of whole bytes")
            return bytes.fromhex(v[2:])
        if typ == "string":
            if not isinstance(v, str):
                raise AbiError("string expected")
            return v
    except eip712.EncodingError as e:
        raise AbiError(str(e)) from None
    raise AbiError(f"unsupported ABI type {typ}")


def _from_py(t: dict, v: Any):
    typ = t["type"]
    if typ.startswith("tuple") and typ[len("tuple"):] == "":
        return {c["name"]: _from_py(c, x) for c, x in zip(t["components"], v)}
    if (m := _ARRAY.fullmatch(typ)):
        return [_from_py({**t, "type": m.group(1)}, x) for x in v]
    if typ == "address":
        return v.lower()
    if _UINT.fullmatch(typ):
        return str(int(v))
    if typ == "bool":
        return bool(v)
    if _BYTESN.fullmatch(typ) or typ == "bytes":
        return "0x" + bytes(v).hex()
    return v


class Contract:
    def __init__(self, abi_json: list, address: str | None = None):
        self.address = address
        self._fn: dict[str, dict] = {}
        self._ev: dict[str, dict] = {}      # topic0 (lowercase 0x hex) -> event ABI entry
        for e in abi_json:
            if e.get("type") == "event":
                self._ev["0x" + keccak(text=f"{e['name']}(" + ",".join(_canonical(i) for i in e["inputs"]) + ")").hex()] = e
            if e.get("type") == "function":
                if e["name"] in self._fn:
                    raise AbiError(f"overloaded function {e['name']} is not supported")
                self._fn[e["name"]] = e

    def _f(self, name: str) -> dict:
        try:
            return self._fn[name]
        except KeyError:
            raise AbiError(f"unknown function {name!r}") from None

    def signature(self, name: str) -> str:
        f = self._f(name)
        return f"{name}(" + ",".join(_canonical(i) for i in f["inputs"]) + ")"

    def selector(self, name: str) -> bytes:
        return keccak(text=self.signature(name))[:4]

    def calldata(self, name: str, *args: Any) -> bytes:
        f = self._f(name)
        if len(args) != len(f["inputs"]):
            raise AbiError(f"{name} takes {len(f['inputs'])} arguments")
        values = [_to_py(t, a) for t, a in zip(f["inputs"], args)]
        return self.selector(name) + _encode([_canonical(t) for t in f["inputs"]], values)

    def decode_output(self, name: str, data: bytes):
        f = self._f(name)
        try:
            values = _decode([_canonical(t) for t in f["outputs"]], data)
        except Exception as e:  # eth_abi raises several unrelated exception types for short/garbled data
            raise AbiError(f"cannot decode {name} output: {type(e).__name__}") from None
        out = [_from_py(t, v) for t, v in zip(f["outputs"], values)]
        return out[0] if len(out) == 1 else out

    def decode_input(self, data: bytes) -> tuple[str, list]:
        """Inverse of calldata(): (function name, wire-form arguments). Unknown selectors and malformed data raise AbiError."""
        if len(data) < 4:
            raise AbiError("calldata shorter than a selector")
        for name, f in self._fn.items():
            if self.selector(name) == data[:4]:
                try:
                    values = _decode([_canonical(t) for t in f["inputs"]], data[4:])
                except Exception as e:  # eth_abi raises several unrelated exception types
                    raise AbiError(f"cannot decode {name} input: {type(e).__name__}") from None
                return name, [_from_py(t, v) for t, v in zip(f["inputs"], values)]
        raise AbiError("selector matches no function of this contract")

    def event_signature(self, name: str) -> str:
        for e in self._ev.values():
            if e["name"] == name:
                return f"{name}(" + ",".join(_canonical(i) for i in e["inputs"]) + ")"
        raise AbiError(f"unknown event {name!r}")

    def decode_log(self, log: dict) -> tuple[str, dict]:
        """Decode one log (topics + data) into (event name, wire-form args). Indexed args must be value types."""
        try:
            topics, data = log["topics"], bytes.fromhex(log["data"][2:])
            ev = self._ev[topics[0]]
        except (KeyError, IndexError, TypeError, ValueError):
            raise AbiError("log does not match any event of this contract") from None
        indexed = [i for i in ev["inputs"] if i["indexed"]]
        plain = [i for i in ev["inputs"] if not i["indexed"]]
        if len(topics) != 1 + len(indexed):
            raise AbiError("wrong number of indexed topics")
        out: dict = {}
        try:
            for i, t in zip(indexed, topics[1:]):
                if i["type"] in ("string", "bytes") or i["type"].startswith("tuple") or i["type"].endswith("]"):
                    raise AbiError("indexed dynamic types are not supported")
                out[i["name"]] = _from_py(i, _decode([_canonical(i)], bytes.fromhex(t[2:]))[0])
            if plain:
                for i, v in zip(plain, _decode([_canonical(i) for i in plain], data)):
                    out[i["name"]] = _from_py(i, v)
        except AbiError:
            raise
        except Exception as e:  # eth_abi raises several unrelated exception types
            raise AbiError(f"cannot decode log: {type(e).__name__}") from None
        return ev["name"], out
