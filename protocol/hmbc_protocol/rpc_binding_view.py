"""D50 chain view over JSON-RPC (HMBC2020 successor, F task 2 slice 8a): the REAL implementation of the view `binding_open.reconstruct` reads through.

PAPER-DERIVED RECONSTRUCTION. `RpcBindingView` offers the five methods the open-time reads use, ONE JSON-RPC request each (so the request counts of D50 section 3, 48 for E and 55 for F, are the node's
request counts):
  chain_id(chain) -> decimal str      `eth_chainId`; returned as the node reports it (the stage checks compare it with the manifest; the carried `Chain._check_chain` is NOT used, it would raise);
  latest(chain)   -> {"number", "hash"}   `eth_getBlockByNumber("latest")`;
  block(chain, n) -> {"number", "hash"} or None   `eth_getBlockByNumber(hex(n))`, None when the node has no such block;
  code(chain, address, at) -> lowercase 0x hex   `eth_getCode(address, hex(at))`;
  call(chain, address, fn, args, at) -> str | bool | list of str   `eth_call` at block number `at`, ABI encoded and decoded with `eth_abi` against the contract's ABI.
Every read is pinned to a block NUMBER (the anchor's); pinning by block HASH (EIP-1898) and the detection of a reorg between reads are NOT done here (the caller holds the anchor hash and the whole read set is
bound to it by the binding document); a node that cannot be pinned this way is a limit, not a feature.

The ABI files are pinned: `from_manifest` loads `<abi_dir>/<Contract>.json` and refuses any whose sha256 differs from the manifest's `abi.<Contract>.abiSha256`. A function is callable only when it is a
`view` or `pure` function with exactly ONE output of type bool, uintN, address or address[] and its name and argument count select exactly one ABI entry; inputs may be uintN, address or bool. Anything else
is a ValueError (a caller or ABI problem), never sent to the node.

FAULT MODEL. A transport failure, a JSON-RPC error, a revert, a malformed or short or non-canonical reply (not lowercase hex, wrong block number, bad hash) is `binding_open.LedgerUnreachable`, stage 1: the
view never turns a node's garbage into a value. A caller bug (unknown chain, address that is not a contract of that chain, unknown or ambiguous function, bad argument, negative block) is a ValueError.
The same address on the two chains is two different contracts (the key is chain and address). No clock, thread, socket or environment here: the injected `Chain` clients own the transport.
"""
from __future__ import annotations

import hashlib
import json
import os
import re

from eth_abi import decode, encode
from eth_utils import function_signature_to_4byte_selector

from .binding_open import LedgerUnreachable
from .chain import ChainError

_ADDR = re.compile(r"0x[0-9a-f]{40}")
_HASH = re.compile(r"0x[0-9a-f]{64}")
_HEX = re.compile(r"0x([0-9a-f]{2})*")
_DEC = re.compile(r"(0|[1-9][0-9]*)")
_UINT = re.compile(r"uint(8|16|32|64|128|256)")
SIDES = ("pbc", "dbc")


def _unreachable(what):
    return LedgerUnreachable(what)


def _supported_output(t):
    return t in ("bool", "address", "address[]") or _UINT.fullmatch(t) is not None


def _supported_input(t):
    return t in ("bool", "address") or _UINT.fullmatch(t) is not None


class RpcBindingView:
    def __init__(self, *, chains, contracts, abis):
        if not isinstance(chains, dict) or set(chains) != set(SIDES):
            raise ValueError("chains must be exactly {'pbc': client, 'dbc': client}")
        if not isinstance(contracts, dict) or set(contracts) != set(SIDES):
            raise ValueError("contracts must be exactly {'pbc': {...}, 'dbc': {...}}")
        if not isinstance(abis, dict):
            raise ValueError("abis must map contract names to ABI lists")
        names = {}
        for side in SIDES:
            if not isinstance(contracts[side], dict):
                raise ValueError("contracts of a chain must be a {name: address} object")
            for name, address in contracts[side].items():
                if not isinstance(address, str) or _ADDR.fullmatch(address) is None:
                    raise ValueError("a contract address must be lowercase 0x + 40 hex")
                if not isinstance(abis.get(name), list):
                    raise ValueError(f"no ABI list for {name}")
                names[(side, address)] = name
        self._chains, self._names, self._abis = dict(chains), names, dict(abis)

    @classmethod
    def from_manifest(cls, manifest, chains, abi_dir):
        """The view for a pinned deployment manifest: the chain clients must be for the manifest's chain ids and every ABI file must hash to the manifest's `abiSha256`."""
        if not isinstance(manifest, dict) or not isinstance(chains, dict) or set(chains) != set(SIDES):
            raise ValueError("a manifest and chain clients for pbc and dbc are required")
        contracts, abis = {}, {}
        for side in SIDES:
            try:
                if int(manifest["chains"][side]["chainId"]) != chains[side].chain_id:
                    raise ValueError(f"the {side} client is for another chain id than the manifest's")
                contracts[side] = dict(manifest["chains"][side]["contracts"])
            except (KeyError, TypeError, ValueError, AttributeError) as e:
                raise ValueError(f"the manifest or the {side} client is malformed: {type(e).__name__}") from None
        for name in {n for side in SIDES for n in contracts[side]}:
            try:
                pinned = manifest["abi"][name]["abiSha256"]
            except (KeyError, TypeError):
                raise ValueError(f"the manifest pins no ABI hash for {name}") from None
            path = os.path.join(abi_dir, name + ".json")
            try:
                with open(path, "rb") as f:
                    raw = f.read()
            except OSError:
                raise ValueError(f"the ABI file for {name} cannot be read") from None
            if hashlib.sha256(raw).hexdigest() != pinned:
                raise ValueError(f"the ABI file for {name} does not hash to the manifest's abiSha256")
            try:
                abis[name] = json.loads(raw)
            except ValueError:
                raise ValueError(f"the ABI file for {name} is not JSON") from None
        return cls(chains=chains, contracts=contracts, abis=abis)

    # ---- transport ---------------------------------------------------------------------------------------------------------------------------------------------
    def _rpc(self, side, method, params):
        if side not in SIDES:
            raise ValueError("chain must be 'pbc' or 'dbc'")
        try:
            return self._chains[side].rpc(method, params)
        except ChainError as e:
            raise _unreachable(f"{side} {method}: {e}") from None

    @staticmethod
    def _int(v, what):
        if not isinstance(v, str) or not v.startswith("0x") or len(v) < 3:
            raise _unreachable(f"{what}: not a hex quantity")
        try:
            return int(v, 16)
        except ValueError:
            raise _unreachable(f"{what}: not a hex quantity") from None

    @staticmethod
    def _at(at):
        if isinstance(at, bool) or not isinstance(at, int) or at < 0:
            raise ValueError("a block number must be a non-negative integer")
        return hex(at)

    def _block(self, side, tag, expect=None):
        b = self._rpc(side, "eth_getBlockByNumber", [tag, False])
        if b is None:
            return None
        if not isinstance(b, dict) or not isinstance(b.get("hash"), str) or _HASH.fullmatch(b["hash"]) is None:
            raise _unreachable(f"{side}: malformed block")
        number = self._int(b.get("number"), f"{side} block number")
        if expect is not None and number != expect:
            raise _unreachable(f"{side}: the node answered another block than the one asked")
        return {"number": str(number), "hash": b["hash"]}

    # ---- the view ------------------------------------------------------------------------------------------------------------------------------------------------
    def chain_id(self, chain):
        return str(self._int(self._rpc(chain, "eth_chainId", []), f"{chain} chain id"))

    def latest(self, chain):
        b = self._block(chain, "latest")
        if b is None:
            raise _unreachable(f"{chain}: no latest block")
        return b

    def block(self, chain, number):
        return self._block(chain, self._at(number), expect=number)

    def code(self, chain, address, at):
        if (chain, address) not in self._names:
            raise ValueError("not a contract of that chain")
        out = self._rpc(chain, "eth_getCode", [address, self._at(at)])
        if not isinstance(out, str) or _HEX.fullmatch(out) is None:
            raise _unreachable(f"{chain}: eth_getCode did not return lowercase hex")
        return out

    def _function(self, chain, address, fn, args):
        """(ABI entry, name) of the ONE view function `fn` with len(args) inputs; ValueError otherwise."""
        name = self._names.get((chain, address))
        if name is None:
            raise ValueError("not a contract of that chain")
        if not isinstance(fn, str) or not isinstance(args, list):
            raise ValueError("a function name and an argument list are required")
        hits = [f for f in self._abis[name] if isinstance(f, dict) and f.get("type") == "function" and f.get("name") == fn and len(f.get("inputs", [])) == len(args)]
        if len(hits) != 1:
            raise ValueError(f"{name}.{fn} with {len(args)} argument(s) is unknown or ambiguous")
        f = hits[0]
        if f.get("stateMutability") not in ("view", "pure") or len(f.get("outputs", [])) != 1 or not _supported_output(f["outputs"][0]["type"]):
            raise ValueError(f"{name}.{fn} is not a view function with one supported output")
        if not all(_supported_input(i["type"]) for i in f["inputs"]):
            raise ValueError(f"{name}.{fn} has an unsupported input type")
        return f, name

    @staticmethod
    def _arg(t, v):
        if t == "bool":
            if not isinstance(v, bool):
                raise ValueError("a bool argument must be a bool")
            return v
        if t == "address":
            if not isinstance(v, str) or _ADDR.fullmatch(v) is None:
                raise ValueError("an address argument must be lowercase 0x + 40 hex")
            return v
        if not isinstance(v, str) or _DEC.fullmatch(v) is None or int(v) >= 1 << int(t[4:]):
            raise ValueError(f"a {t} argument must be a canonical decimal string in range")
        return int(v)

    def call(self, chain, address, fn, args, at):
        f, _ = self._function(chain, address, fn, args)
        block = self._at(at)
        types = [i["type"] for i in f["inputs"]]
        data = "0x" + (function_signature_to_4byte_selector(f"{fn}({','.join(types)})") + encode(types, [self._arg(t, v) for t, v in zip(types, args)])).hex()
        out = self._rpc(chain, "eth_call", [{"to": address, "data": data}, block])
        if not isinstance(out, str) or _HEX.fullmatch(out) is None:
            raise _unreachable(f"{chain}: eth_call did not return lowercase hex")
        t = f["outputs"][0]["type"]
        try:
            (v,) = decode([t], bytes.fromhex(out[2:]))
        except Exception:  # noqa: BLE001 - eth_abi raises several types for short, padded or out-of-range data; all mean the node did not answer this getter
            raise _unreachable(f"{chain}: {fn} returned data that does not decode as {t}") from None
        if t == "bool":
            return bool(v)
        if t == "address":
            return v.lower()
        if t == "address[]":
            return [a.lower() for a in v]
        return str(v)
