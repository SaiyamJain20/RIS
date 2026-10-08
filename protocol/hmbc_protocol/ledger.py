"""Typed view of one ledger deployment: two chains and six contracts bound to a deployment manifest.

The manifest is per-instance data (RPC URLs, addresses) handed in by the runner; the ABIs are bundled (protocol/abi) and pinned by hash,
so a deployment whose `abi.<Contract>.abiSha256` differs from the bundled ABI is refused. Only http(s) RPC URLs on the loopback host
are accepted: the adapter must not be steerable at arbitrary network targets by a request.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from urllib.parse import urlsplit

from . import eip712
from .abi import Contract
from .chain import Chain

ABI_DIR = pathlib.Path(__file__).resolve().parents[1] / "abi"
CONTRACTS = (("PSC", "pbc"), ("RSC", "pbc"), ("TMSC", "pbc"), ("LSC", "pbc"), ("ACSC", "dbc"), ("KSSC", "dbc"))


class LedgerError(ValueError):
    pass


def _url(u: object) -> str:
    parts = urlsplit(u) if isinstance(u, str) else None
    if not parts or parts.scheme not in ("http", "https") or parts.hostname not in ("127.0.0.1", "localhost", "::1") or not parts.port:
        raise LedgerError("rpcUrl must be an http(s) loopback URL with an explicit port")
    return u


class Ledger:
    def __init__(self, pbc: Chain, dbc: Chain, contracts: dict[str, Contract], deployment: dict):
        self.pbc, self.dbc, self.deployment = pbc, dbc, deployment
        for name, c in contracts.items():
            setattr(self, name, c)

    @classmethod
    def from_deployment(cls, dep: dict) -> "Ledger":
        try:
            chains = {s: Chain(_url(dep["chains"][s]["rpcUrl"]), eip712._uint(dep["chains"][s]["chainId"], 256)) for s in ("pbc", "dbc")}
            contracts = {}
            for name, side in CONTRACTS:
                addr = dep["chains"][side]["contracts"][name]
                if not isinstance(addr, str) or not eip712._ADDR.fullmatch(addr):
                    raise LedgerError(f"{name} address must be lowercase 0x + 40 hex")
                raw = (ABI_DIR / f"{name}.json").read_bytes()
                if hashlib.sha256(raw).hexdigest() != dep["abi"][name]["abiSha256"]:
                    raise LedgerError(f"{name}: deployment abiSha256 differs from the bundled ABI (different ledger build)")
                contracts[name] = Contract(json.loads(raw), addr)
        except (KeyError, TypeError, eip712.EncodingError) as e:
            raise LedgerError(f"deployment manifest unusable: {type(e).__name__}") from None
        return cls(chains["pbc"], chains["dbc"], contracts, dep)
